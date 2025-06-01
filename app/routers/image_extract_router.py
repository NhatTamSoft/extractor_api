from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends, Form, Header
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel
import os
import base64
from io import BytesIO
from PIL import Image
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv
from app.services.database_service import DatabaseService
from app.services.prompt_service import PromptService
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
import shutil
from fastapi.responses import JSONResponse
from app.services.DungChung import convert_currency_to_int, lay_du_lieu_tu_sql_server, thuc_thi_truy_van, decode_jwt_token, LayMaDoiTuong, pdf_to_images
from app.services.anh_xa_tuong_dong import tim_kiem_tuong_dong
from app.core.auth import get_current_user
from app.schemas.user import User
import pandas as pd
import httpx
import re
from app.services.DungChung import encode_image_to_base64 
from openai import OpenAI
from unidecode import unidecode
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import tempfile
import fitz  # PyMuPDF for PDF processing
import traceback
import PIL
import openpyxl
from fastapi import UploadFile, File, HTTPException, Query, Depends, Form, Header
import logging
from tempfile import SpooledTemporaryFile
from app.services.extract_document_azure import process_multiple_documents

# Load biến môi trường từ file .env
load_dotenv()

router = APIRouter()

model_openai = os.getenv('MODEL_API_OPENAI')

# Khởi tạo PromptService
prompt_service = PromptService()

# Định nghĩa IMAGE_STORAGE_PATH
IMAGE_STORAGE_PATH = os.getenv('IMAGE_STORAGE_PATH', 'image_storage')
os.makedirs(IMAGE_STORAGE_PATH, exist_ok=True)

# Định nghĩa các định dạng ảnh được chấp nhận
ALLOWED_IMAGE_TYPES = {
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/bmp',
    'image/webp'
}

# Azure Form Recognizer configuration
AZURE_ENDPOINT = os.getenv('AZURE_FORM_RECOGNIZER_ENDPOINT')
AZURE_KEY = os.getenv('AZURE_FORM_RECOGNIZER_KEY')

# Initialize Azure client
azure_client = DocumentAnalysisClient(AZURE_ENDPOINT, AzureKeyCredential(AZURE_KEY))

class MultiImageExtractRequest(BaseModel):
    pages: Optional[List[int]] = None

class DocumentExtractRequest(BaseModel):
    file_type: str  # 'image' or 'pdf'
    pages: Optional[List[int]] = None  # For PDF, specify which pages to process

def custom_sort_key(path):
    try:
        # Trích xuất phần cuối cùng của đường dẫn (tên thư mục/tập tin)
        base_name = path.split('\\')[-1]

        # Tìm kiếm số ở đầu chuỗi (nếu có)
        match = re.match(r'(\d+)\. (.*)', base_name)
        if match:
            number = int(match.group(1))
            text_part = match.group(2)
            return (number, text_part)
        else:
            # Nếu không có số, coi như số rất lớn để nó xuống cuối
            # hoặc có thể xử lý đặc biệt nếu có nhiều trường hợp không có số
            return (float('inf'), base_name)
    except Exception as e:
        print(f"Lỗi khi xử lý đường dẫn: {str(e)}")
        # Trả về giá trị mặc định nếu có lỗi
        return (float('inf'), path)
    


@router.post("/document_extract")
async def document_extract(
    thuMuc: str = Form(...),
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    # 1. Xác thực token (giữ nguyên logic cũ)
    try:
        if not authorization.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={
                    "status": "error",
                    "code": 401,
                    "message": "Token không hợp lệ",
                    "detail": "Token phải bắt đầu bằng 'Bearer '"
                }
            )
        token = authorization.split(" ")[1]
        token_data = decode_jwt_token(token)
        user_id = token_data["userID"]
        don_vi_id = token_data["donViID"]
        print(f"Token validated for userID: {user_id}, donViID: {don_vi_id}")
    except Exception as e:
        return JSONResponse(
            status_code=401,
            content={
                "status": "error",
                "code": 401,
                "message": "Lỗi xác thực",
                "detail": str(e)
            }
        )
    # DANH SÁCH ĐƯỜNG DẪN DỰ ÁN CỦA THƯ MỤC
    listThuMuc = []
    # 2. Kiểm tra xem có file nào được tải lên không
    # Kiểm tra xem đường dẫn có tồn tại không
    if not os.path.exists(thuMuc):
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "code": 400,
                "message": "Đường dẫn không tồn tại",
                "detail": f"Không tìm thấy đường dẫn: {thuMuc}"
            }
        )

    try:
        # Lấy danh sách thư mục con
        for item in os.listdir(thuMuc):
            item_path = os.path.join(thuMuc, item)
            if os.path.isdir(item_path):
                listThuMuc.append({
                    'path': item_path,
                    'duAnID': '',
                    'maDuAn': item,
                    'ghiChu': ''
                })
        
        if not listThuMuc:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "code": 400,
                    "message": "Không tìm thấy thư mục con nào trong đường dẫn đã cung cấp.",
                    "detail": f"Đường dẫn: {thuMuc}"
                }
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "code": 500,
                "message": "Lỗi khi đọc thư mục",
                "detail": str(e)
            }
        )
    listFinalPath = [] #Danh sách file pdf đã xử lý
    error_pdf = []
    try: 
        for item in listThuMuc:
            ma_du_an = item['maDuAn']
            try:
                query = text(f"""
                    SELECT DuAnID 
                    FROM dbo.DuAn 
                    WHERE (DonViID = '{don_vi_id}' OR DonViID_chudautu = '{don_vi_id}')
                    AND MaDuAn = N'{ma_du_an}'
                """)
                
                result = db.execute(query).fetchone()
                if not result:
                    item['ghiChu'] = f"Không tìm thấy dự án với mã {ma_du_an}"
                else:
                    item['duAnID'] = result[0]
            except Exception as e:
                item['ghiChu'] = f"Có lỗi tuy vấn khi tìm mã dự án với mã {ma_du_an}"

            # XỬ LÝ TỪNG THƯ MỤC

            for item in listThuMuc:
                if item['duAnID'] == "":
                    continue
                
                path = item['path']
                duAnID = item['duAnID']
                
                # B1: Duyệt tìm thư mục con và file
                listThuMucCon = []
                listPDF = []
                listIndexTxt = []
                try:
                    #print("Đang xử lý path: ", path)
                    for item_path in os.listdir(path):
                        full_path = os.path.join(path, item_path)
                        if os.path.isdir(full_path):
                            listThuMucCon.append(full_path)
                        elif item_path.lower().endswith('.pdf'):
                            listPDF.append(full_path)
                        elif item_path.lower().endswith('.txt'):
                            listIndexTxt.append(full_path)
                except Exception as e:
                    print(f"Lỗi khi đọc thư mục {path}: {str(e)}")
                    print(f"Chi tiết lỗi: {type(e).__name__}")
                    print(f"Stack trace: {traceback.format_exc()}")
                listThuMucCon_sorted = sorted(listThuMucCon, key=custom_sort_key)
                listThuMucCon = listThuMucCon_sorted
                print("================================")
                print("Danh sách thư mục con:", listThuMucCon)
                print("Danh sách file PDF:", listPDF) 
                print("Danh sách file txt:", listIndexTxt)
                print("================================")
                listKichBanXuLy = []
                # C1: Xử lý file PDF
                dfRangPage = pd.DataFrame(columns=['Path', 'RangePage'])
                
                # Đọc các file txt
                for txt_file in listIndexTxt:
                    try:
                        df_temp = pd.read_csv(txt_file, sep='\t')
                        dfRangPage = pd.concat([dfRangPage, df_temp], ignore_index=True)
                    except Exception as e:
                        print(f"Lỗi đọc file {txt_file}: {str(e)}")

                for pdf_path in listPDF:
                    listKichBanXuLy.append({
                        'Path': pdf_path,
                        'RangePage': ''
                    })
                    # print("=======ĐI TÌM PDF")
                    # print(pdf_path)
                # Duyệt qua từng dòng trong listKichBanXuLy
                for item in listKichBanXuLy:
                    # Lấy tên file từ đường dẫn đầy đủ
                    pdf_name = os.path.basename(item['Path'])
                    # Loại bỏ đuôi .pdf nếu có
                    while pdf_name.endswith('.pdf'):
                        pdf_name = pdf_name.replace('.pdf', '')
                    
                    # Duyệt qua từng dòng trong dfRangPage
                    for _, row in dfRangPage.iterrows():
                        # Lấy danh sách các file từ cột Path
                        path_files = row['Path'].split(';')
                        # Lấy file đầu tiên để so sánh
                        first_file = path_files[0]
                        
                        # Nếu tìm thấy file trong dfRangPage
                        if pdf_name == first_file:
                            # Gán RangePage từ dfRangPage
                            item['RangePage'] = row['RangePage']
                            # Nếu có nhiều file trong Path của dfRangPage
                            if len(path_files) > 1:
                                # Tạo đường dẫn đầy đủ cho tất cả các file
                                full_paths = []
                                for path_file in path_files:
                                    # Tìm đường dẫn đầy đủ trong listPDF
                                    for full_pdf_path in listPDF:
                                        full_pdf_name = os.path.basename(full_pdf_path)
                                        while full_pdf_name.endswith('.pdf'):
                                            full_pdf_name = full_pdf_name.replace('.pdf', '')
                                        if path_file == full_pdf_name:
                                            full_paths.append(full_pdf_path)
                                            break
                                # Gán lại Path với đường dẫn đầy đủ
                                if full_paths:
                                    item['Path'] = ';'.join(full_paths)
                            break
                # Tạo danh sách tạm để lưu các phần tử cần xóa
                items_to_remove = []
                
                # Duyệt qua từng phần tử trong listKichBanXuLy
                for i, item in enumerate(listKichBanXuLy):
                    # Kiểm tra nếu Path có chứa dấu ';' (nhiều đường dẫn)
                    if ';' in item['Path']:
                        # Tách các đường dẫn
                        paths = item['Path'].split(';')
                        
                        # Lấy các đường dẫn từ phần tử thứ 1 trở đi
                        additional_paths = paths[1:]
                        
                        # Duyệt qua các phần tử còn lại trong listKichBanXuLy
                        for j, other_item in enumerate(listKichBanXuLy):
                            # Bỏ qua phần tử hiện tại
                            if i != j:
                                # Kiểm tra nếu Path của other_item không chứa dấu ';' (chỉ có 1 đường dẫn)
                                if ';' not in other_item['Path']:
                                    # Kiểm tra nếu đường dẫn của other_item trùng với một trong các đường dẫn bổ sung
                                    if other_item['Path'] in additional_paths:
                                        # Thêm vào danh sách cần xóa
                                        items_to_remove.append(j)
                
                # Xóa các phần tử theo thứ tự giảm dần để tránh ảnh hưởng đến chỉ số
                for index in sorted(items_to_remove, reverse=True):
                    listKichBanXuLy.pop(index)
                print("=" * 10 + "CHI TIẾT LIST KỊCH BẢN XỬ LÝ" + "=" * 10)
                print(listKichBanXuLy)
                for idx, item in enumerate(listKichBanXuLy, 1):
                    print(f"\033[1mKỊCH BẢN {idx}\033[0m")
                    print(f"Path: {item['Path']}")
                    print(f"RangePage: {item['RangePage']}")
                print("=" * 10 + "KẾT THÚC DANH SÁCH" + "=" * 10)
                
                # return
                # Xử lý từng file PDF
                for itemKichBan in listKichBanXuLy:
                    pathPDF = str(itemKichBan['Path']).strip().split(';')[0] # Lấy file đầu tiên để dành lưu trữ // Các file ở phần tử 1 trở đi chỉ để ghép lấy số liệu
                    # pathPDF là đường dẫn file pdf
                    pdf_name = os.path.basename(pathPDF)
                    pdfRangPage = ""
                    
                    # Tách đường dẫn PDF và RangePage thành các phần
                    pdf_paths = itemKichBan['Path'].split(';')
                    range_pages = itemKichBan['RangePage'].split(';')
                    
                    # Danh sách chứa tất cả các ảnh PIL
                    all_images = []
                    
                    # Xử lý từng cặp PDF và RangePage tương ứng
                    for pdf_path, page_range in zip(pdf_paths, range_pages):
                        # Kiểm tra nếu page_range rỗng thì chuyển tất cả trang
                        # print(f"\n=== 888 Thông tin chi tiết PDF và Range Page 888 ===")
                        # print(f"PDF Path: {pdf_path}")
                        # print(f"Range Page: {page_range}")
                        # print("=======================================\n")
                        if page_range.strip() == "":
                            images = pdf_to_images(pdf_path, 2.0, "")
                        else:
                            # Chuyển PDF thành ảnh với các trang được chỉ định
                            images = pdf_to_images(pdf_path, 2.0, page_range)
                        
                        # print("\n=== Thông tin chi tiết biến images ===")
                        # print(f"Số lượng ảnh: {len(images)}")
                        # print("\nChi tiết từng ảnh:")
                        # for idx, img in enumerate(images):
                        #     print(f"\nẢnh thứ {idx + 1}:")
                        #     print(f"Kích thước: {img.size}")
                        #     print(f"Mode: {img.mode}")
                        #     print(f"Format: {img.format if hasattr(img, 'format') else 'N/A'}")
                        # print("=======================================\n")
                        # Thêm các ảnh vào danh sách kết quả
                        all_images.extend(images)
                    
                    if len(all_images) == 0:
                        print('KẾT QUẢ CẮT PDF SANG ẢNH LÀ 0 TRANG: ', pdf_path)
                        error_pdf.append({
                            'Path': pdf_path,
                            'status': "Kết quả cắt pdf sang ảnh là 0"
                        })
                        continue

                    image_PIL = all_images

                    print("\n=== Chi tiết biến image_PIL và itemKichBan ===")
                    print(f"Số lượng ảnh: {len(image_PIL)}")
                    print("\nThông tin itemKichBan:")
                    print(f"Path: {itemKichBan['Path']}")
                    print(f"RangePage: {itemKichBan['RangePage']}")
                    print("\nChi tiết từng ảnh:")
                    for idx, img in enumerate(image_PIL):
                        print(f"\nẢnh thứ {idx + 1}:")
                        print(f"Kích thước: {img.size}")
                        print(f"Mode: {img.mode}")
                        print(f"Format: {img.format if hasattr(img, 'format') else 'N/A'}")
                    print("=======================================\n")

                    # Chuyển PDF thành ảnh
                    try:
                        all_data = []
                        loaiVanBan = None
                        path = pathPDF.lower()
                        print("\n=== Thông tin chi tiết đường dẫn đang xử lý ===")
                        print(f"Đường dẫn: {pathPDF}")
                        print("=======================================\n")
                        if 'qd_phe_duyet_chu_truong\\' in path:
                            loaiVanBan = 'QDPD_CT'
                        elif 'qd_phe_duyet_du_toan_cbdt\\' in path:
                            loaiVanBan = 'QDPDDT_CBDT'
                        elif 'qd_phe_duyet_khlcnt_cbdt\\' in path:
                            loaiVanBan = 'QDPD_KHLCNT_CBDT'
                        elif 'qd_phe_duyet_kqlcnt_cbdt\\' in path:
                            loaiVanBan = 'QDPD_KQLCNT_CBDT'
                        elif 'qd_phe_duyet_du_an\\' in path:
                            loaiVanBan = 'QDPD_DA'
                        elif 'qd_phe_duyet_du_toan_thdt\\' in path:
                            loaiVanBan = 'QDPD_DT_THDT'
                        elif 'qd_phe_duyet_khlcnt_thdt\\' in path:
                            loaiVanBan = 'QDPD_KHLCNT_THDT'
                        elif 'qd_phe_duyet_kqlcnt_thdt\\' in path:
                            loaiVanBan = 'QDPD_KQLCNT_THDT'
                        elif 'phu_luc_hop_dong\\' in path:
                            loaiVanBan = 'PL_HOP_DONG'
                        elif 'hop_dong\\' in path:
                            loaiVanBan = 'HOP_DONG'                        
                        elif 'xac_nhan_klcv_hoan_thanh\\' in path:
                            loaiVanBan = 'KLCVHT_THD'
                        elif 'de_nghi_thanh_toan\\' in path:
                            loaiVanBan = 'GIAI_NGAN_DNTT'
                        elif 'giay_rut_von\\' in path:
                            loaiVanBan = 'GIAI_NGAN_GRV'
                        elif 'giay_de_nghi_thu_hoi_von\\' in path:
                            loaiVanBan = 'GIAI_NGAN_THV'
                        else:
                            continue
                        # elif 'nghiem_thu_ban_giao\\' in path:
                        #     loaiVanBan = 'QDPDDT_CBDT'
                        # elif 'bc_quyet_toan_daht\\' in path:
                        #     loaiVanBan = 'BC_QTDAHT'
                        # elif 'vb_khac\\' in path:
                        #     loaiVanBan = 'VanBanKhac'
                        prompt, required_columns = prompt_service.get_prompt(loaiVanBan)
                        van_ban_id = str(uuid.uuid4())
                        bang_du_lieu_chi_tiet_id = str(uuid.uuid4())
                        # print("*"*30)
                        # print(prompt)
                        # print("*"*30)
                        # CHUYỂN PDF SANG DANH SÁCH ẢNH
                        
                        # print(f"\n{'='*50}")
                        # print(f"Đang xử lý kịch bản: {itemKichBan}")
                        # print(f"Thời gian bắt đầu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                        # print(f"Đường dẫn file: {itemKichBan['Path']}")
                        # print(f"Đường dẫn file CHÍNH: {pathPDF}")
                        # print(f"{'='*50}\n")
                        try:
                            # Process each file with Azure Form Recognizer
                            combined_text = ""
                            for temp_file in image_PIL:
                                try:
                                    # Chuyển đổi PIL Image thành bytes
                                    img_byte_arr = BytesIO()
                                    temp_file.save(img_byte_arr, format='PNG')
                                    img_byte_arr = img_byte_arr.getvalue()
                                    # print(img_byte_arr)
                                    # Extract data with Azure Form Recognizer
                                    poller = azure_client.begin_analyze_document("prebuilt-layout", document=img_byte_arr)
                                    result = poller.result()

                                    # Collect text and tables
                                    for page in result.pages:
                                        for line in page.lines:
                                            combined_text += line.content + "\n"

                                    # Process tables if any
                                    for table in result.tables:
                                        combined_text += "\nBảng:\n"
                                        for row_index in range(table.row_count):
                                            row_cells = [cell.content if cell.content else "" for cell in table.cells if cell.row_index == row_index]
                                            combined_text += " | ".join(row_cells) + "\n"

                                except Exception as e:
                                    item['ghiChu'] = f"Error processing file {temp_file}: {str(e)}"
                                    print(f"Error processing file {temp_file}: {str(e)}")
                            # print("&"*30)
                            # print(combined_text)
                            # print("&"*30)
                            # break
                            # try:
                            #     # Tạo tên file text dựa trên tên file PDF
                            #     text_file_path = os.path.splitext(pathPDF)[0] + '.txt'
                                
                            #     # Ghi nội dung combined_text vào file
                            #     with open(text_file_path, 'w', encoding='utf-8') as f:
                            #         f.write(combined_text)
                                    
                            #     print(f"Đã ghi nội dung text vào file: {text_file_path}")
                                
                            # except Exception as e:
                            #     print(f"Lỗi khi ghi file text: {str(e)}")
                            #     item['ghiChu'] = f"Lỗi khi ghi file text: {str(e)}"
                            
                        # Ghi combined_text ra file text
                        except Exception as e:
                            item['ghiChu'] = f"Error processing file {temp_file}: {str(e)}\nDòng lỗi: {e.__traceback__.tb_lineno}\nNội dung lỗi: {e.__dict__ if hasattr(e, '__dict__') else 'Không có thông tin chi tiết'}"
                            return JSONResponse(
                                status_code=500,
                                content={
                                    "status": "error",
                                    "code": 500,
                                    "message": "Lỗi khi xử lý file",
                                    "detail": f"Error processing file {temp_file}: {str(e)}\nDòng lỗi: {e.__traceback__.tb_lineno}\nNội dung lỗi: {e.__dict__ if hasattr(e, '__dict__') else 'Không có thông tin chi tiết'}"
                                }
                            )
                      
                        messages = [
                            {
                                "role": "system",
                                "content": "You are an AI assistant that extracts information from documents. You MUST return a valid JSON object containing the mapped fields. Do not include any other text or explanation in your response."
                            },
                            {
                                "role": "user",
                                "content": f"""
                                {prompt}

                                Data extracted from images:
                                {combined_text}

                                Remember: Return ONLY the JSON object, no other text or explanation.
                                """
                            }
                        ]

                        # Call OpenAI API
                        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                        response = client.chat.completions.create(
                            model="gpt-4o",
                            messages=messages,
                            max_tokens=4096,
                            temperature=0,
                            response_format={"type": "json_object"}
                        )

                        # Process response
                        response_text = response.choices[0].message.content.strip()
                        
                        # Clean up response text
                        if response_text.strip().startswith("```json"):
                            response_text = response_text.strip()[7:-3].strip()
                        elif response_text.strip().startswith("```"):
                            response_text = response_text.strip()[3:-3].strip()

                        # print("+"*20)
                        # print(response_text)
                        # print("+"*20)

                        # Xử lý response
                        if "error" in response_text.lower() or "không thể" in response_text.lower():
                            print("AI không thể nhận diện văn bản từ ảnh\n" + response_text)
                            item['ghiChu'] = "AI không thể nhận diện văn bản từ ảnh\n" + response_text
                        try:
                            data_json = json.loads(response_text)
                            #data_json = data_json["results"]
                            #print(data_json)
                        except json.JSONDecodeError as e:
                            if response_text.strip().startswith("<"):
                                msg = "AI trả về HTML hoặc file không phải là ảnh văn bản."
                            elif len(response_text.strip()) < 30:
                                msg = "Ảnh không chứa đủ thông tin văn bản hoặc quá mờ."
                            else:
                                msg = "Kết quả trả về không đúng định dạng."
                            return JSONResponse(
                                status_code=400,
                                content={
                                    "status": "error",
                                    "code": 400,
                                    "message": msg,
                                    "detail": str(e),
                                    "raw_response": response_text
                                }
                            )
                        # Validate required fields in the response
                        query = """select NghiepVuID=ChucNangAIID, ThongTinChung from ChucNangAI where ChucNangAIID='"""+loaiVanBan+"""' order by STT"""
                        dfChucNang = lay_du_lieu_tu_sql_server(query)
                        # Lấy động các cột của bảng Thông tin chung cần lưu vào bản VanBanAI
                        required_fields = []
                        for _, row in dfChucNang.iterrows():
                            bang_du_lieu = row['ThongTinChung']
                            required_fields = bang_du_lieu.split(';')

                        # Kiểm tra trong json có đầy đủ các cột cần lưu hay chưa
                        missing_fields = [field for field in required_fields if field not in data_json["ThongTinChung"]]
                        if missing_fields:
                            print("\033[31mKhông thể trích xuất đầy đủ thông tin từ ảnh\033[0m")
                            print(f"Thiếu các trường: {', '.join(missing_fields)}")

                        # Set UUIDs in the response data
                        data_json["BangDuLieuID"] = bang_du_lieu_chi_tiet_id
                        data_json["VanBanID"] = van_ban_id

                        # Kiểm tra và chuyển đổi các giá trị tiền tệ trong ThongTinChung
                        for col in data_json["ThongTinChung"]:
                            #print("ThongTinChung: cột >>> ", col)
                            if (col.startswith('GiaTri') or col.startswith('SoTien') or col.startswith('ThanhToanDenCuoiKyTruoc') or col.startswith('LuyKeDenCuoiKy')
                                            or col.startswith('GiaTriNghiemThu') or col.startswith('TamUngChuaThuaHoi') or col.startswith('TamUngGiaiNganKyNayKyTruoc') or col.startswith('GiaTrungThau')
                                            or col.startswith('ThanhToanThuHoiTamUng') or col.startswith('GiaiNganKyNay') or col.startswith('TamUngGiaiNganKyTruoc')
                                            or col.startswith('LuyKe') or col.startswith('TamUngThanhToan') or col.startswith('ThanhToanKLHT')):
                                try:
                                    data_json["ThongTinChung"][col] = convert_currency_to_int(str(data_json["ThongTinChung"][col]))
                                except Exception as e:
                                    print(f"\033[31m[ERROR] Lỗi khi chuyển đổi giá trị tiền tệ cho cột {col}:\033[0m")
                                    print(f"\033[31m- Chi tiết lỗi: {str(e)}\033[0m")
                                    print(f"\033[31m- Giá trị gốc: {data_json['ThongTinChung'][col]}\033[0m")
                        #print("ThongTinChung >>> ", col)
                        #print(data_json["ThongTinChung"]);
                        # Convert currency values in the response
                        if "BangDuLieu" in data_json:
                            for item in data_json["BangDuLieu"]:
                                try:
                                    # print("Kiểm tra van_ban_id: ", van_ban_id)
                                    item["VanBanID"] = van_ban_id
                                    # Convert all numeric values based on required columns
                                    for col in required_columns:
                                        # print("Cột kiểm tra:", col)
                                        if (col.startswith('GiaTri') or col.startswith('SoTien') or col.startswith('ThanhToanDenCuoiKyTruoc') or col.startswith('LuyKeDenCuoiKy')
                                            or col.startswith('GiaTriNghiemThu') or col.startswith('TamUngChuaThuaHoi') or col.startswith('TamUngGiaiNganKyNayKyTruoc') or col.startswith('GiaTrungThau')
                                            or col.startswith('ThanhToanThuHoiTamUng') or col.startswith('GiaiNganKyNay') or col.startswith('TamUngGiaiNganKyTruoc')
                                            or col.startswith('LuyKe') or col.startswith('TamUngThanhToan') or col.startswith('ThanhToanKLHT')):
                                            item[col] = convert_currency_to_int(str(item[col]))
                                except Exception as e:
                                    print(f"\033[31m[ERROR] Lỗi khi xử lý item trong BangDuLieu:\033[0m")
                                    print(f"\033[31m- Chi tiết lỗi: {str(e)}\033[0m")
                                    print(f"\033[31m- Loại lỗi: {type(e).__name__}\033[0m")
                                    print(f"\033[31m- Item gây lỗi: {json.dumps(item, ensure_ascii=False, indent=2)}\033[0m")
                        # dữ liệu mặc định
                        van_ban_data = {
                            "VanBanAIID": van_ban_id,
                            "SoVanBan": data_json["ThongTinChung"].get("SoVanBan", ""),
                            "NgayKy": data_json["ThongTinChung"].get("NgayKy", ""),
                            "TrichYeu": data_json["ThongTinChung"].get("TrichYeu", ""),
                            "ChucDanhNguoiKy": data_json["ThongTinChung"].get("ChucDanhNguoiKy", ""),
                            "CoQuanBanHanh": data_json["ThongTinChung"].get("CoQuanBanHanh", ""),
                            "NguoiKy": data_json["ThongTinChung"].get("NguoiKy", ""),
                            "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "TenLoaiVanBan": loaiVanBan,
                            "DuAnID": duAnID,
                            "DieuChinh": data_json["ThongTinChung"].get("DieuChinh", "0"),
                            "JsonAI": json.dumps(data_json, ensure_ascii=False),
                            "DataOCR": combined_text,
                            "TenFile": "*".join([d['filename'] for d in all_data])
                        }
                        if  f"[{loaiVanBan}]" in "[BCDX_CT];[QDPD_CT];[QDPDDT_CBDT];[QDPD_DT_THDT];[QDPD_DA]":
                            van_ban_data = {
                                "VanBanAIID": van_ban_id,
                                "SoVanBan": data_json["ThongTinChung"].get("SoVanBan", ""),
                                "SoVanBanCanCu": data_json["ThongTinChung"].get("SoVanBanCanCu", ""),
                                "NgayKy": data_json["ThongTinChung"].get("NgayKy", ""),
                                "NgayKyCanCu": data_json["ThongTinChung"].get("NgayKyCanCu", ""),
                                "TrichYeu": data_json["ThongTinChung"].get("TrichYeu", ""),
                                "TenNguonVon": data_json["ThongTinChung"].get("TenNguonVon", ""),
                                "GiaTri": data_json["ThongTinChung"].get("GiaTri", "0"),
                                "ChucDanhNguoiKy": data_json["ThongTinChung"].get("ChucDanhNguoiKy", ""),
                                "CoQuanBanHanh": data_json["ThongTinChung"].get("CoQuanBanHanh", ""),
                                "NguoiKy": data_json["ThongTinChung"].get("NguoiKy", ""),
                                "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "TenLoaiVanBan": loaiVanBan,
                                "DuAnID": duAnID,
                                "DieuChinh": data_json["ThongTinChung"].get("DieuChinh", "0"),
                                "JsonAI": json.dumps(data_json, ensure_ascii=False),
                                "DataOCR": combined_text,
                                "TenFile": "*".join([d['filename'] for d in all_data])
                            }
                        elif  f"[{loaiVanBan}]" in "[QDPD_KHLCNT_CBDT];[QDPD_KHLCNT_THDT]":
                            van_ban_data = {
                                "VanBanAIID": van_ban_id,
                                "SoVanBan": data_json["ThongTinChung"].get("SoVanBan", ""),
                                "SoVanBanCanCu": data_json["ThongTinChung"].get("SoVanBanCanCu", ""),
                                "NgayKy": data_json["ThongTinChung"].get("NgayKy", ""),
                                "NgayKyCanCu": data_json["ThongTinChung"].get("NgayKyCanCu", ""),
                                "TrichYeu": data_json["ThongTinChung"].get("TrichYeu", ""),
                                "ChucDanhNguoiKy": data_json["ThongTinChung"].get("ChucDanhNguoiKy", ""),
                                "CoQuanBanHanh": data_json["ThongTinChung"].get("CoQuanBanHanh", ""),
                                "NguoiKy": data_json["ThongTinChung"].get("NguoiKy", ""),
                                "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "TenLoaiVanBan": loaiVanBan,
                                "DuAnID": duAnID,
                                "DieuChinh": data_json["ThongTinChung"].get("DieuChinh", "0"),
                                "JsonAI": json.dumps(data_json, ensure_ascii=False),
                                "DataOCR": combined_text,
                                "TenFile": "*".join([d['filename'] for d in all_data])
                            }
                        elif  f"[{loaiVanBan}]" in "[QDPD_KQLCNT_CBDT];[QDPD_KQLCNT_THDT]":
                            van_ban_data = {
                                "VanBanAIID": van_ban_id,
                                "SoVanBan": data_json["ThongTinChung"].get("SoVanBan", ""),
                                "SoVanBanCanCu": data_json["ThongTinChung"].get("SoVanBanCanCu", ""),
                                "NgayKy": data_json["ThongTinChung"].get("NgayKy", ""),
                                "NgayKyCanCu": data_json["ThongTinChung"].get("NgayKyCanCu", ""),
                                "TrichYeu": data_json["ThongTinChung"].get("TrichYeu", ""),
                                "ChucDanhNguoiKy": data_json["ThongTinChung"].get("ChucDanhNguoiKy", ""),
                                "CoQuanBanHanh": data_json["ThongTinChung"].get("CoQuanBanHanh", ""),
                                "TenNhaThau": data_json["ThongTinChung"].get("TenNhaThau", ""),
                                "GiaTri": data_json["ThongTinChung"].get("GiaTri", "0"),
                                "NguoiKy": data_json["ThongTinChung"].get("NguoiKy", ""),
                                "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "TenLoaiVanBan": loaiVanBan,
                                "DuAnID": duAnID,
                                "DieuChinh": data_json["ThongTinChung"].get("DieuChinh", "0"),
                                "JsonAI": json.dumps(data_json, ensure_ascii=False),
                                "DataOCR": combined_text,
                                "TenFile": "*".join([d['filename'] for d in all_data])
                            }
                        elif  f"[{loaiVanBan}]" in "[HOP_DONG]":
                            van_ban_data = {
                                "VanBanAIID": van_ban_id,
                                "SoVanBan": data_json["ThongTinChung"].get("SoVanBan", ""),
                                "NgayKy": data_json["ThongTinChung"].get("NgayKy", ""),
                                "NgayHieuLuc": data_json["ThongTinChung"].get("NgayHieuLuc", ""),
                                "NgayKetThuc": data_json["ThongTinChung"].get("NgayKetThuc", ""),
                                "NguoiKy": data_json["ThongTinChung"].get("NguoiKy", ""),
                                "SoVanBanCanCu": data_json["ThongTinChung"].get("SoVanBanCanCu", ""),
                                "NgayKyCanCu": data_json["ThongTinChung"].get("NgayKyCanCu", ""),
                                "ChucDanhNguoiKy": data_json["ThongTinChung"].get("ChucDanhNguoiKy", ""),
                                "NguoiKy_NhaThau": data_json["ThongTinChung"].get("NguoiKy_NhaThau", ""),
                                "ChucDanhNguoiKy_NhaThau": data_json["ThongTinChung"].get("ChucDanhNguoiKy_NhaThau", ""),
                                "TenNhaThau": data_json["ThongTinChung"].get("TenNhaThau", ""),
                                "TrichYeu": data_json["ThongTinChung"].get("TrichYeu", ""),
                                "CoQuanBanHanh": data_json["ThongTinChung"].get("CoQuanBanHanh", ""),
                                "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "TenLoaiVanBan": loaiVanBan,
                                "GiaiDoanID": "",
                                "DuAnID": duAnID,
                                "DieuChinh": "0",
                                "JsonAI": json.dumps(data_json, ensure_ascii=False),
                                "DataOCR": combined_text,
                                "TenFile": "*".join([d['filename'] for d in all_data]),
                                "UserID": user_id,
                                "DonViID": don_vi_id
                            }
                        elif  f"[{loaiVanBan}]" in "[PL_HOP_DONG]":
                            van_ban_data = {
                                "VanBanAIID": van_ban_id,
                                "SoVanBan": data_json["ThongTinChung"].get("SoVanBan", ""), # Tương đương Số phụ lục hợp đồng
                                "SoPLHopDong": data_json["ThongTinChung"].get("SoPLHopDong", ""),
                                "NgayKy": data_json["ThongTinChung"].get("NgayKy", ""),
                                "NgayHieuLuc": data_json["ThongTinChung"].get("NgayHieuLuc", ""),
                                "NgayKetThuc": data_json["ThongTinChung"].get("NgayKetThuc", ""),
                                "NguoiKy": data_json["ThongTinChung"].get("NguoiKy", ""),
                                "SoVanBanCanCu": data_json["ThongTinChung"].get("SoVanBanCanCu", ""), # Tương đương Số hợp đồng (gốc)
                                "NgayKyCanCu": data_json["ThongTinChung"].get("NgayKyCanCu", ""),
                                "ChucDanhNguoiKy": data_json["ThongTinChung"].get("ChucDanhNguoiKy", ""),
                                "NguoiKy_NhaThau": data_json["ThongTinChung"].get("NguoiKy_NhaThau", ""),
                                "ChucDanhNguoiKy_NhaThau": data_json["ThongTinChung"].get("ChucDanhNguoiKy_NhaThau", ""),
                                "TenNhaThau": data_json["ThongTinChung"].get("TenNhaThau", ""),
                                "TrichYeu": data_json["ThongTinChung"].get("TrichYeu", ""),
                                "CoQuanBanHanh": data_json["ThongTinChung"].get("CoQuanBanHanh", ""),
                                "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "TenLoaiVanBan": loaiVanBan,
                                "GiaiDoanID": "",
                                "DuAnID": duAnID,
                                "DieuChinh": "0",
                                "JsonAI": json.dumps(data_json, ensure_ascii=False),
                                "DataOCR": combined_text,
                                "TenFile": "*".join([d['filename'] for d in all_data]),
                                "UserID": user_id,
                                "DonViID": don_vi_id
                            }
                        elif  f"[{loaiVanBan}]" in "[KLCVHT_THD]":
                            van_ban_data = {
                                "VanBanAIID": van_ban_id,
                                "SoVanBan": data_json["ThongTinChung"].get("SoVanBan", ""),
                                "NgayKy": data_json["ThongTinChung"].get("NgayKy", ""),
                                "NguoiKy": data_json["ThongTinChung"].get("NguoiKy", ""),
                                "SoVanBanCanCu": data_json["ThongTinChung"].get("SoVanBanCanCu", ""),
                                "SoHopDong": data_json["ThongTinChung"].get("SoHopDong", ""),
                                "SoPLHopDong": data_json["ThongTinChung"].get("SoPLHopDong", ""),
                                "LanThanhToan": data_json["ThongTinChung"].get("LanThanhToan", ""),
                                "TenNhaThau": data_json["ThongTinChung"].get("TenNhaThau", ""),
                                "NgayKyCanCu": data_json["ThongTinChung"].get("NgayKyCanCu", ""),
                                "ChucDanhNguoiKy": data_json["ThongTinChung"].get("ChucDanhNguoiKy", ""),
                                "NguoiKy_NhaThau": data_json["ThongTinChung"].get("NguoiKy_NhaThau", ""),
                                "ChucDanhNguoiKy_NhaThau": data_json["ThongTinChung"].get("ChucDanhNguoiKy_NhaThau", ""),
                                "TrichYeu": data_json["ThongTinChung"].get("TrichYeu", ""),
                                "GiaTriHopDong": data_json["ThongTinChung"].get("GiaTriHopDong", "0"),
                                "TamUngChuaThuaHoi": data_json["ThongTinChung"].get("TamUngChuaThuaHoi", "0"),
                                "ThanhToanDenCuoiKyTruoc": data_json["ThongTinChung"].get("ThanhToanDenCuoiKyTruoc", "0"),
                                "LuyKeDenCuoiKy": data_json["ThongTinChung"].get("LuyKeDenCuoiKy", "0"),
                                "ThanhToanThuHoiTamUng": data_json["ThongTinChung"].get("ThanhToanThuHoiTamUng", "0"),
                                "GiaiNganKyNay": data_json["ThongTinChung"].get("GiaiNganKyNay", "0"),
                                "TamUngGiaiNganKyNayKyTruoc": data_json["ThongTinChung"].get("TamUngGiaiNganKyNayKyTruoc", "0"),
                                "ThanhToanKLHTKyTruoc": data_json["ThongTinChung"].get("ThanhToanKLHTKyTruoc", "0"),
                                "LuyKeGiaiNgan": data_json["ThongTinChung"].get("LuyKeGiaiNgan", "0"),
                                "TamUngThanhToan": data_json["ThongTinChung"].get("TamUngThanhToan", "0"),
                                "ThanhToanKLHT": data_json["ThongTinChung"].get("ThanhToanKLHT", "0"),
                                "CoQuanBanHanh": data_json["ThongTinChung"].get("CoQuanBanHanh", ""),
                                "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "TenLoaiVanBan": loaiVanBan,
                                "GiaiDoanID": "",
                                "DuAnID": duAnID,
                                "DieuChinh": "0",
                                "JsonAI": json.dumps(data_json, ensure_ascii=False),
                                "DataOCR": combined_text,
                                "TenFile": "*".join([d['filename'] for d in all_data]),
                                "UserID": user_id,
                                "DonViID": don_vi_id
                            }
                        elif  f"[{loaiVanBan}]" in "[GIAI_NGAN_DNTT];[GIAI_NGAN_GRV];[GIAI_NGAN_THV]":
                            print("van_ban_data>>>>>>>>>>>>>>>>>>>>")
                            van_ban_data = {
                                "VanBanAIID": van_ban_id,
                                "SoVanBan": data_json["ThongTinChung"].get("SoVanBan", ""),
                                "NgayKy": data_json["ThongTinChung"].get("NgayKy", ""),
                                "SoHopDong": data_json["ThongTinChung"].get("SoHopDong", ""),
                                "SoPLHopDong": data_json["ThongTinChung"].get("SoPLHopDong", ""),
                                "SoVanBanCanCu": data_json["ThongTinChung"].get("SoVanBanCanCu", ""),
                                "NgayKyCanCu": data_json["ThongTinChung"].get("NgayKyCanCu", ""),
                                "TenNguonVon": data_json["ThongTinChung"].get("TenNguonVon", ""),
                                "NienDo": data_json["ThongTinChung"].get("NienDo", ""),
                                "LoaiKHVonID": data_json["ThongTinChung"].get("NienDo", "2"), # mặc định là 2 (năm nay)
                                "SoTien": data_json["ThongTinChung"].get("NienDo", "0"),
                                "NguoiKy": data_json["ThongTinChung"].get("NguoiKy", ""),
                                "ChucDanhNguoiKy": data_json["ThongTinChung"].get("ChucDanhNguoiKy", ""),
                                "CoQuanBanHanh": data_json["ThongTinChung"].get("CoQuanBanHanh", ""),
                                "TrichYeu": data_json["ThongTinChung"].get("TrichYeu", ""),
                                "NghiepVuID": data_json["ThongTinChung"].get("NghiepVuID", ""),
                                "TenNhaThau": data_json["ThongTinChung"].get("TenNhaThau", ""),
                                "GiaTri": data_json["ThongTinChung"].get("GiaTri", "0"),
                                "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "TenLoaiVanBan": loaiVanBan,
                                "DuAnID": duAnID,
                                "DieuChinh": data_json["ThongTinChung"].get("DieuChinh", "0"),
                                "JsonAI": json.dumps(data_json, ensure_ascii=False),
                                "DataOCR": combined_text,
                                "TenFile": "*".join([d['filename'] for d in all_data])
                            }
                        van_ban_data["UserID"] = user_id
                        van_ban_data["DonViID"] = don_vi_id
                        van_ban_data["TenFilePDF"] = pathPDF
                        db_service = DatabaseService()
                        result = await db_service.insert_van_ban_ai(db, van_ban_data, loaiVanBan)
                        
                        if not result.get("success", False):
                            print("Lỗi khi lưu dữ liệu vào database\n" + result.get("error", "Unknown error"))
                            item['ghiChu'] = "Lỗi khi lưu dữ liệu vào database\n" + result.get("error", "Unknown error")

                        # Insert BangDuLieu data if it exists
                        if "BangDuLieu" in data_json and data_json["BangDuLieu"] and len(data_json["BangDuLieu"]) > 0:
                            bang_du_lieu_data = []
                            for item in data_json["BangDuLieu"]:
                                bang_du_lieu_data.append({
                                    "VanBanAIID": van_ban_id,
                                    **{col: item.get(col, 0) for col in required_columns}
                                })
                            bang_du_lieu_result = await db_service.insert_bang_du_lieu_chi_tiet_ai(
                                db, 
                                bang_du_lieu_data,
                                required_columns
                            )
                            if not bang_du_lieu_result.get("success", False):
                                print("Lỗi khi lưu dữ liệu vào database\n" + bang_du_lieu_result.get("error", "Unknown error"))
                                item['ghiChu'] = "Lỗi khi lưu dữ liệu vào database\n" + bang_du_lieu_result.get("error", "Unknown error")
                        else:
                            print("Văn bản này không có chi tiết bảng dữ liệu")
                        # After successful processing and database operations
                        try:
                            # Get QLDA upload URL from environment
                            qlda_upload_url = os.getenv("API_URL_UPLOAD_QLDA")
                            # if not qlda_upload_url:
                            #     raise ValueError("Không tìm thấy API_URL_UPLOAD_QLDA trong file .env")

                            # Prepare files for upload to QLDA
                            files_data = []
                            # Chuyển đổi các ảnh PIL thành file để upload
                            for idx, img in enumerate(image_PIL):
                                # Tạo tên file tạm thời
                                temp_file = SpooledTemporaryFile()
                                # Lưu ảnh vào file tạm
                                img.save(temp_file, format='PNG')
                                temp_file.seek(0)
                                
                                # Tạo tên file với số thứ tự
                                file_name = f"page_{idx + 1}.png"
                                
                                # Tạo đối tượng UploadFile
                                file_obj = UploadFile(
                                    filename=file_name,
                                    file=temp_file,
                                    headers={"content-type": "image/png"}
                                )
                                
                                # Thêm vào danh sách files_data
                                files_data.append(
                                    ("files", (file_name, file_obj.file, "image/png"))
                                )
                            
                            # print(">>>>>>>>>>>> files_data chi tiết:")
                            # for file_data in files_data:
                            #     print(f"- Tên file: {file_data[1][0]}")
                            #     print(f"- Loại file: {file_data[1][2]}")
                            #     print("-" * 50)
                            # Upload files to QLDA system
                            async with httpx.AsyncClient() as client:
                                response = await client.post(
                                    f"{qlda_upload_url}/api/v1/Uploads/uploadMultipleFiles",
                                    files=files_data,
                                    headers={"Authorization": authorization}
                                )
                                # print("Response status code:", response.status_code)
                                # print("Response headers:", response.headers)
                                # print("Response content:", response.text)
                                # print("Response URL:", response.url)
                                # print("Response encoding:", response.encoding)
                                # print("Response cookies:", response.cookies)
                                # print("Response elapsed time:", response.elapsed)
                                if response.status_code != 200:
                                    print(f"Lỗi file {path} khi upload file lên hệ thống QLDA\n" + response.text)
                                    item['ghiChu'] = f"Lỗi file {path} khi upload file lên hệ thống QLDA\n" + response.text
                                
                                # Lấy response JSON từ API QLDA
                                qlda_response = response.json()
                                
                                try:
                                    # Nối các đường dẫn file trong data thành 1 chuỗi, phân cách bằng dấu *
                                    string_url_qlda_response = '*'.join(qlda_response['data'])
                                    # Thực thi câu lệnh SQL để cập nhật tên file trong bảng VanBanAI
                                    update_query = text(f"""
                                        UPDATE dbo.VanBanAI 
                                        SET tenFile = N'{string_url_qlda_response}'
                                        WHERE VanBanAIID = N'{van_ban_id}'
                                    """)
                                    db.execute(update_query)
                                    db.commit()
                                except Exception as e:
                                    db.rollback()
                                    print(f"Lỗi file {path} khi cập nhật tên file trong bảng VanBanAI: {str(e)}")
                                    item['ghiChu'] = f"Lỗi file {path} khi cập nhật tên file trong bảng VanBanAI: {str(e)}"
                            print(f"Tệp {path} upload và xử lý nhiều file ảnh thành công")
                            item['ghiChu'] = "Upload và xử lý nhiều file ảnh thành công"

                        except Exception as e:
                            # CHỔ NÀY XỬ LÝ FILE DỰ ÁN CHƯA ĐÍNH KÈM ĐƯỢC
                            nhat_ky_loi_upload_file = "Lỗi khi upload file lên hệ thống QLDA"
                            print(f"\033[31m[ERROR] Chi tiết lỗi khi upload file:\033[0m")
                            print(f"\033[31m- Loại lỗi: {type(e).__name__}\033[0m")
                            print(f"\033[31m- Chi tiết lỗi: {str(e)}\033[0m")
                            print(f"\033[31m- Thông tin chi tiết: {e.__dict__ if hasattr(e, '__dict__') else 'Không có thông tin chi tiết'}\033[0m")
                            print(f"\033[31m- Dòng lỗi: {e.__traceback__.tb_lineno if hasattr(e, '__traceback__') else 'Không có thông tin dòng lỗi'}\033[0m")
                            item['ghiChu'] = f"Lỗi {path} khi upload file lên hệ thống QLDA"

                        # XOÁ FILE SAU KHI CHẠY
                        try:
                            # Xóa từng file PDF trong danh sách
                            pdf_pathsX = str(itemKichBan['Path']).strip().split(';')
                            for pdf_pathX in pdf_pathsX:
                                if os.path.exists(pdf_pathX):
                                    os.remove(pdf_pathX)
                                    print(f"Đã xóa file {pdf_pathX} thành công")
                        except Exception as e:
                            print(f"Lỗi khi xóa file {pathPDF}: {str(e)}")
                        # KẾT THÚC XOÁ FILE SAU KHI CHẠY
                    except Exception as e:
                        print(f"Lỗi xử lý file {pathPDF}: {str(e)}")
                        listFinalPath.append({
                            'pathPDF': pathPDF,
                            'pdf_name': pdf_name,
                            'pdfRangPage': pdfRangPage,
                            'status': f"Lỗi xử lý file: {type(e).__name__} - {str(e)} - Dòng lỗi: {e.__traceback__.tb_lineno if hasattr(e, '__traceback__') else 'Không có thông tin dòng lỗi'}"
                        })
                    # Bổ sung thông tin file PDF đã xử lý
                    listFinalPath.append({
                        'pathPDF': pathPDF,
                        'pdf_name': pdf_name,
                        'pdfRangPage': pdfRangPage,
                        'status': 'Xử lý thành công'
                    })
                # C2: Xử lý đệ quy các thư mục con
                for thuMucCon in listThuMucCon:
                    # Tạo item mới cho thư mục con
                    item_con = {
                        'path': thuMucCon,
                        'duAnID': duAnID,
                        'maDuAn': os.path.basename(thuMucCon),
                        'ghiChu': ''
                    }
                    listThuMuc.append(item_con)

            # Trả về kết quả là 2 DataFrame dưới dạng JSON
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "Trích xuất dữ liệu từ file Excel thành công.",
                    "data": {
                        "info_pdf": listFinalPath,
                        "error_pdf": error_pdf
                    }
                }
            )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error", 
                "code": 500, 
                "message": "Lỗi khi xử lý file Excel", 
                "detail": f"Lỗi: {str(e)}\nLoại lỗi: {type(e).__name__}\nChi tiết: {e.__dict__ if hasattr(e, '__dict__') else 'Không có thông tin chi tiết'}\nDòng lỗi: {e.__traceback__.tb_lineno if hasattr(e, '__traceback__') else 'Không có thông tin dòng lỗi'}"
                }
        )


#MÔ HÌNH OPENAI
@router.post("/image_extract_multi")
async def extract_multiple_images(
    files: List[UploadFile] = File(...),
    loaiVanBan: Optional[str] = None,
    duAnID: Optional[str] = None,
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    # print("===Thông tin files===")
    # for file in files:
    #     print(f"Tên file: {file.filename}")
    #     print(f"Content type: {file.content_type}")
    #     print(f"Headers: {file.headers}")
    #     print("-------------------")
    # Xác thực token
    try:
        #Kiểm tra header Authorization
        if not authorization.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={
                    "status": "error",
                    "code": 401,
                    "message": "Token không hợp lệ",
                    "detail": "Token phải bắt đầu bằng 'Bearer '"
                }
            )
            
        #Lấy token từ header
        token = authorization.split(" ")[1]
        # Giải mã token để lấy userID và donViID
        token_data = decode_jwt_token(token)
        user_id = token_data["userID"]
        don_vi_id = token_data["donViID"]
        
        #Thêm thông tin user vào request
        request_data = {
            "userID": user_id,
            "donViID": don_vi_id
        }
        print(request_data)
    except Exception as e:
        return JSONResponse(
            status_code=401,
            content={
                "status": "error",
                "code": 401,
                "message": "Lỗi xác thực",
                "detail": str(e)
            }
        )

    temp_files = []
    all_data = []
    try:
        # Generate UUID only once and use it consistently
        van_ban_id = str(uuid.uuid4())
        bang_du_lieu_chi_tiet_id = str(uuid.uuid4())
        prompt, required_columns = prompt_service.get_prompt(loaiVanBan)
        # print("======================prompt==================")
        # print(prompt)
        # print("======================end prompt==================")
        #return
        # Process each file
        temp_files = []
        for file in files:
            if file.content_type not in ALLOWED_IMAGE_TYPES:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "code": 400,
                        "message": f"File {file.filename} không đúng định dạng ảnh",
                        "detail": f"File {file.filename} có content_type {file.content_type} không phải là ảnh hợp lệ."
                    }
                )
            # Tạo tên file tạm thời với timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Chuyển đổi tên file sang tiếng Việt không dấu
            filename_no_accent = unidecode(file.filename)
            temp_file_path = os.path.join(IMAGE_STORAGE_PATH, f"temp_{timestamp}_{filename_no_accent}")
            temp_files.append(temp_file_path)
            print(temp_file_path)
            # Lưu file tạm thời
            with open(temp_file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

        content_parts = [{"type": "text", "text": prompt}]
        valid_image_paths = []
        for image_name in temp_files:
            # Trong Colab, files.upload() lưu file vào thư mục hiện tại
            # image_path sẽ chính là image_name
            image_path = image_name
            print(f"  - Đang xử lý: {image_path}")
            base64_image = encode_image_to_base64(image_path)
            if base64_image:
                image_url_object = {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                }
                content_parts.append(image_url_object)
                valid_image_paths.append(image_path)

        # print("valid_image_paths")
        # print(valid_image_paths)
        # Get the appropriate prompt based on loaiVanBan
        try:
            # Chuẩn bị dữ liệu cho OpenAI
            # Thêm hình ảnh vào messages
            messages = [
                {
                    "role": "system",
                    "content": """Bạn là một AI có khả năng trích chính xác văn bản từ hình ảnh hoặc pdf (đa số là tiếng Việt) tuyệt đối không bịa, không suy diễn, không được đoán, không được làm tròn, không điền bất kỳ nội dung nào khác ngoài văn bản. Nhiệm vụ của bạn trích nội dung chính xác 100% của tài liệu được cung cấp và xử lý theo yêu cầu bên dưới"""
                },
                {
                    "role": "user",
                    "content": content_parts
                }
            ]
            # Gọi OpenAI API
            client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            response = client.chat.completions.create(
                model="gpt-4o",  # Hoặc mô hình hỗ trợ xử lý nhiều ảnh khác
                messages=messages,
                temperature=0,
                max_tokens=15000  # Tăng max_tokens nếu cần cho kết quả dài hơn
            )
            #print(response)
            # Xử lý response từ OpenAI
            response_text = response.choices[0].message.content.strip()
            # print("response_text")
            # print(response_text)
            # return
            if response_text.strip().startswith("```json"):
                response_text = response_text.strip()[7:-3].strip()
            elif response_text.strip().startswith("```"):
                response_text = response_text.strip()[3:-3].strip()

            # Xử lý response từ Gemini
            if "error" in response_text.lower() or "không thể" in response_text.lower():
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "code": 400,
                        "message": "AI không thể nhận diện văn bản từ ảnh",
                        "detail": response_text
                    }
                )
            try:
                data_json = json.loads(response_text)
                #data_json = data_json["results"]
                #print(data_json)
            except json.JSONDecodeError as e:
                if response_text.strip().startswith("<"):
                    msg = "AI trả về HTML hoặc file không phải là ảnh văn bản."
                elif len(response_text.strip()) < 30:
                    msg = "Ảnh không chứa đủ thông tin văn bản hoặc quá mờ."
                else:
                    msg = "Kết quả trả về không đúng định dạng."
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "code": 400,
                        "message": msg,
                        "detail": str(e),
                        "raw_response": response_text
                    }
                )
            # Validate required fields in the response
            query = """select NghiepVuID=ChucNangAIID, ThongTinChung from ChucNangAI where ChucNangAIID='"""+loaiVanBan+"""' order by STT"""
            dfChucNang = lay_du_lieu_tu_sql_server(query)
            #required_fields = ["SoVanBan", "NgayKy", "NguoiKy", "ChucDanhNguoiKy", "TrichYeu", "DieuChinh"]
            # Lấy động các cột của bảng Thông tin chung cần lưu vào bản VanBanAI
            required_fields = []
            for _, row in dfChucNang.iterrows():
                bang_du_lieu = row['ThongTinChung']
                required_fields = bang_du_lieu.split(';')

            # Kiểm tra trong json có đầy đủ các cột cần lưu hay chưa
            missing_fields = [field for field in required_fields if field not in data_json["ThongTinChung"]]
            if missing_fields:
                print("\033[31mKhông thể trích xuất đầy đủ thông tin từ ảnh\033[0m")
                print(f"Thiếu các trường: {', '.join(missing_fields)}")

            # Set UUIDs in the response data
            data_json["BangDuLieuID"] = bang_du_lieu_chi_tiet_id
            data_json["VanBanID"] = van_ban_id

            for col in data_json["ThongTinChung"]:
                #print("ThongTinChung: cột >>> ", col)
                if (col.startswith('GiaTri') or col.startswith('SoTien') or col.startswith('ThanhToanDenCuoiKyTruoc') or col.startswith('LuyKeDenCuoiKy')
                                or col.startswith('GiaTriNghiemThu') or col.startswith('TamUngChuaThuaHoi') or col.startswith('TamUngGiaiNganKyNayKyTruoc') or col.startswith('GiaTrungThau')
                                or col.startswith('ThanhToanThuHoiTamUng') or col.startswith('GiaiNganKyNay') or col.startswith('TamUngGiaiNganKyTruoc')
                                or col.startswith('LuyKe') or col.startswith('TamUngThanhToan') or col.startswith('ThanhToanKLHT')):
                    try:
                        data_json["ThongTinChung"][col] = convert_currency_to_int(str(data_json["ThongTinChung"][col]))
                    except Exception as e:
                        print(f"\033[31m[ERROR] Lỗi khi chuyển đổi giá trị tiền tệ cho cột {col}:\033[0m")
                        print(f"\033[31m- Chi tiết lỗi: {str(e)}\033[0m")
                        print(f"\033[31m- Giá trị gốc: {data_json['ThongTinChung'][col]}\033[0m")

            # Convert currency values in the response
            if "BangDuLieu" in data_json:
                for item in data_json["BangDuLieu"]:
                    try:
                        # print("Kiểm tra van_ban_id: ", van_ban_id)
                        item["VanBanID"] = van_ban_id
                        # Convert all numeric values based on required columns
                        for col in required_columns:
                            #print("Cột kiểm tra:", col)
                            if (col.startswith('GiaTri') or col.startswith('SoTien') or col.startswith('ThanhToanDenCuoiKyTruoc') or col.startswith('LuyKeDenCuoiKy')
                                or col.startswith('GiaTriNghiemThu') or col.startswith('TamUngChuaThuaHoi') or col.startswith('TamUngGiaiNganKyNayKyTruoc') or col.startswith('GiaTrungThau')
                                or col.startswith('ThanhToanThuHoiTamUng') or col.startswith('GiaiNganKyNay') or col.startswith('TamUngGiaiNganKyTruoc')
                                or col.startswith('LuyKe') or col.startswith('TamUngThanhToan') or col.startswith('ThanhToanKLHT')):
                                item[col] = convert_currency_to_int(str(item[col]))
                    except Exception as e:
                        print(f"\033[31m[ERROR] Lỗi khi xử lý item trong BangDuLieu:\033[0m")
                        print(f"\033[31m- Chi tiết lỗi: {str(e)}\033[0m")
                        print(f"\033[31m- Loại lỗi: {type(e).__name__}\033[0m")
                        print(f"\033[31m- Item gây lỗi: {json.dumps(item, ensure_ascii=False, indent=2)}\033[0m")
            
            # dữ liệu mặc định
            van_ban_data = {
                "VanBanAIID": van_ban_id,
                "SoVanBan": data_json["ThongTinChung"].get("SoVanBan", ""),
                "NgayKy": data_json["ThongTinChung"].get("NgayKy", ""),
                "TrichYeu": data_json["ThongTinChung"].get("TrichYeu", ""),
                "ChucDanhNguoiKy": data_json["ThongTinChung"].get("ChucDanhNguoiKy", ""),
                "CoQuanBanHanh": data_json["ThongTinChung"].get("CoQuanBanHanh", ""),
                "NguoiKy": data_json["ThongTinChung"].get("NguoiKy", ""),
                "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "TenLoaiVanBan": loaiVanBan,
                "DuAnID": duAnID,
                "DieuChinh": data_json["ThongTinChung"].get("DieuChinh", "0"),
                "JsonAI": json.dumps(data_json, ensure_ascii=False),
                "DataOCR": response_text,
                "TenFile": "*".join([d['filename'] for d in all_data])
            }
            if  f"[{loaiVanBan}]" in "[BCDX_CT];[QDPD_CT];[QDPDDT_CBDT];[QDPD_DT_THDT];[QDPD_DA]":
                van_ban_data = {
                    "VanBanAIID": van_ban_id,
                    "SoVanBan": data_json["ThongTinChung"].get("SoVanBan", ""),
                    "SoVanBanCanCu": data_json["ThongTinChung"].get("SoVanBanCanCu", ""),
                    "NgayKy": data_json["ThongTinChung"].get("NgayKy", ""),
                    "NgayKyCanCu": data_json["ThongTinChung"].get("NgayKyCanCu", ""),
                    "TrichYeu": data_json["ThongTinChung"].get("TrichYeu", ""),
                    "TenNguonVon": data_json["ThongTinChung"].get("TenNguonVon", ""),
                    "GiaTri": data_json["ThongTinChung"].get("GiaTri", "0"),
                    "ChucDanhNguoiKy": data_json["ThongTinChung"].get("ChucDanhNguoiKy", ""),
                    "CoQuanBanHanh": data_json["ThongTinChung"].get("CoQuanBanHanh", ""),
                    "NguoiKy": data_json["ThongTinChung"].get("NguoiKy", ""),
                    "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "TenLoaiVanBan": loaiVanBan,
                    "DuAnID": duAnID,
                    "DieuChinh": data_json["ThongTinChung"].get("DieuChinh", "0"),
                    "JsonAI": json.dumps(data_json, ensure_ascii=False),
                    "DataOCR": response_text,
                    "TenFile": "*".join([d['filename'] for d in all_data])
                }
            elif  f"[{loaiVanBan}]" in "[QDPD_KHLCNT_CBDT];[QDPD_KHLCNT_THDT]":
                van_ban_data = {
                    "VanBanAIID": van_ban_id,
                    "SoVanBan": data_json["ThongTinChung"].get("SoVanBan", ""),
                    "SoVanBanCanCu": data_json["ThongTinChung"].get("SoVanBanCanCu", ""),
                    "NgayKy": data_json["ThongTinChung"].get("NgayKy", ""),
                    "NgayKyCanCu": data_json["ThongTinChung"].get("NgayKyCanCu", ""),
                    "TrichYeu": data_json["ThongTinChung"].get("TrichYeu", ""),
                    "ChucDanhNguoiKy": data_json["ThongTinChung"].get("ChucDanhNguoiKy", ""),
                    "CoQuanBanHanh": data_json["ThongTinChung"].get("CoQuanBanHanh", ""),
                    "NguoiKy": data_json["ThongTinChung"].get("NguoiKy", ""),
                    "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "TenLoaiVanBan": loaiVanBan,
                    "DuAnID": duAnID,
                    "DieuChinh": data_json["ThongTinChung"].get("DieuChinh", "0"),
                    "JsonAI": json.dumps(data_json, ensure_ascii=False),
                    "DataOCR": response_text,
                    "TenFile": "*".join([d['filename'] for d in all_data])
                }
            elif  f"[{loaiVanBan}]" in "[QDPD_KQLCNT_CBDT];[QDPD_KQLCNT_THDT]":
                van_ban_data = {
                    "VanBanAIID": van_ban_id,
                    "SoVanBan": data_json["ThongTinChung"].get("SoVanBan", ""),
                    "SoVanBanCanCu": data_json["ThongTinChung"].get("SoVanBanCanCu", ""),
                    "NgayKy": data_json["ThongTinChung"].get("NgayKy", ""),
                    "NgayKyCanCu": data_json["ThongTinChung"].get("NgayKyCanCu", ""),
                    "TrichYeu": data_json["ThongTinChung"].get("TrichYeu", ""),
                    "ChucDanhNguoiKy": data_json["ThongTinChung"].get("ChucDanhNguoiKy", ""),
                    "CoQuanBanHanh": data_json["ThongTinChung"].get("CoQuanBanHanh", ""),
                    "TenNhaThau": data_json["ThongTinChung"].get("TenNhaThau", ""),
                    "GiaTri": data_json["ThongTinChung"].get("GiaTri", "0"),
                    "NguoiKy": data_json["ThongTinChung"].get("NguoiKy", ""),
                    "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "TenLoaiVanBan": loaiVanBan,
                    "DuAnID": duAnID,
                    "DieuChinh": data_json["ThongTinChung"].get("DieuChinh", "0"),
                    "JsonAI": json.dumps(data_json, ensure_ascii=False),
                    "DataOCR": response_text,
                    "TenFile": "*".join([d['filename'] for d in all_data])
                }
            elif  f"[{loaiVanBan}]" in "[HOP_DONG]":
                van_ban_data = {
                    "VanBanAIID": van_ban_id,
                    "SoVanBan": data_json["ThongTinChung"].get("SoVanBan", ""),
                    "NgayKy": data_json["ThongTinChung"].get("NgayKy", ""),
                    "NgayHieuLuc": data_json["ThongTinChung"].get("NgayHieuLuc", ""),
                    "NgayKetThuc": data_json["ThongTinChung"].get("NgayKetThuc", ""),
                    "NguoiKy": data_json["ThongTinChung"].get("NguoiKy", ""),
                    "SoVanBanCanCu": data_json["ThongTinChung"].get("SoVanBanCanCu", ""),
                    "NgayKyCanCu": data_json["ThongTinChung"].get("NgayKyCanCu", ""),
                    "ChucDanhNguoiKy": data_json["ThongTinChung"].get("ChucDanhNguoiKy", ""),
                    "NguoiKy_NhaThau": data_json["ThongTinChung"].get("NguoiKy_NhaThau", ""),
                    "ChucDanhNguoiKy_NhaThau": data_json["ThongTinChung"].get("ChucDanhNguoiKy_NhaThau", ""),
                    "TenNhaThau": data_json["ThongTinChung"].get("TenNhaThau", ""),
                    "TrichYeu": data_json["ThongTinChung"].get("TrichYeu", ""),
                    "CoQuanBanHanh": data_json["ThongTinChung"].get("CoQuanBanHanh", ""),
                    "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "TenLoaiVanBan": loaiVanBan,
                    "GiaiDoanID": "",
                    "DuAnID": duAnID,
                    "DieuChinh": "0",
                    "JsonAI": json.dumps(data_json, ensure_ascii=False),
                    "DataOCR": response_text,
                    "TenFile": "*".join([d['filename'] for d in all_data]),
                    "UserID": user_id,
                    "DonViID": don_vi_id
                }
            elif  f"[{loaiVanBan}]" in "[PL_HOP_DONG]":
                van_ban_data = {
                    "VanBanAIID": van_ban_id,
                    "SoVanBan": data_json["ThongTinChung"].get("SoVanBan", ""), # Tương đương Số phụ lục hợp đồng
                    "SoPLHopDong": data_json["ThongTinChung"].get("SoPLHopDong", ""),
                    "NgayKy": data_json["ThongTinChung"].get("NgayKy", ""),
                    "NgayHieuLuc": data_json["ThongTinChung"].get("NgayHieuLuc", ""),
                    "NgayKetThuc": data_json["ThongTinChung"].get("NgayKetThuc", ""),
                    "NguoiKy": data_json["ThongTinChung"].get("NguoiKy", ""),
                    "SoVanBanCanCu": data_json["ThongTinChung"].get("SoVanBanCanCu", ""), # Tương đương Số hợp đồng (gốc)
                    "NgayKyCanCu": data_json["ThongTinChung"].get("NgayKyCanCu", ""),
                    "ChucDanhNguoiKy": data_json["ThongTinChung"].get("ChucDanhNguoiKy", ""),
                    "NguoiKy_NhaThau": data_json["ThongTinChung"].get("NguoiKy_NhaThau", ""),
                    "ChucDanhNguoiKy_NhaThau": data_json["ThongTinChung"].get("ChucDanhNguoiKy_NhaThau", ""),
                    "TenNhaThau": data_json["ThongTinChung"].get("TenNhaThau", ""),
                    "TrichYeu": data_json["ThongTinChung"].get("TrichYeu", ""),
                    "CoQuanBanHanh": data_json["ThongTinChung"].get("CoQuanBanHanh", ""),
                    "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "TenLoaiVanBan": loaiVanBan,
                    "GiaiDoanID": "",
                    "DuAnID": duAnID,
                    "DieuChinh": "0",
                    "JsonAI": json.dumps(data_json, ensure_ascii=False),
                    "DataOCR": response_text,
                    "TenFile": "*".join([d['filename'] for d in all_data]),
                    "UserID": user_id,
                    "DonViID": don_vi_id
                }
            elif  f"[{loaiVanBan}]" in "[KLCVHT_THD]":
                van_ban_data = {
                    "VanBanAIID": van_ban_id,
                    "SoVanBan": data_json["ThongTinChung"].get("SoVanBan", ""),
                    "NgayKy": data_json["ThongTinChung"].get("NgayKy", ""),
                    "NguoiKy": data_json["ThongTinChung"].get("NguoiKy", ""),
                    "SoVanBanCanCu": data_json["ThongTinChung"].get("SoVanBanCanCu", ""),
                    "SoHopDong": data_json["ThongTinChung"].get("SoHopDong", ""),
                    "SoPLHopDong": data_json["ThongTinChung"].get("SoPLHopDong", ""),
                    "LanThanhToan": data_json["ThongTinChung"].get("LanThanhToan", ""),
                    "TenNhaThau": data_json["ThongTinChung"].get("TenNhaThau", ""),
                    "NgayKyCanCu": data_json["ThongTinChung"].get("NgayKyCanCu", ""),
                    "ChucDanhNguoiKy": data_json["ThongTinChung"].get("ChucDanhNguoiKy", ""),
                    "NguoiKy_NhaThau": data_json["ThongTinChung"].get("NguoiKy_NhaThau", ""),
                    "ChucDanhNguoiKy_NhaThau": data_json["ThongTinChung"].get("ChucDanhNguoiKy_NhaThau", ""),
                    "TrichYeu": data_json["ThongTinChung"].get("TrichYeu", ""),
                    "GiaTriHopDong": data_json["ThongTinChung"].get("GiaTriHopDong", "0"),
                    "TamUngChuaThuaHoi": data_json["ThongTinChung"].get("TamUngChuaThuaHoi", "0"),
                    "ThanhToanDenCuoiKyTruoc": data_json["ThongTinChung"].get("ThanhToanDenCuoiKyTruoc", "0"),
                    "LuyKeDenCuoiKy": data_json["ThongTinChung"].get("LuyKeDenCuoiKy", "0"),
                    "ThanhToanThuHoiTamUng": data_json["ThongTinChung"].get("ThanhToanThuHoiTamUng", "0"),
                    "GiaiNganKyNay": data_json["ThongTinChung"].get("GiaiNganKyNay", "0"),
                    "TamUngGiaiNganKyNayKyTruoc": data_json["ThongTinChung"].get("TamUngGiaiNganKyNayKyTruoc", "0"),
                    "ThanhToanKLHTKyTruoc": data_json["ThongTinChung"].get("ThanhToanKLHTKyTruoc", "0"),
                    "LuyKeGiaiNgan": data_json["ThongTinChung"].get("LuyKeGiaiNgan", "0"),
                    "TamUngThanhToan": data_json["ThongTinChung"].get("TamUngThanhToan", "0"),
                    "ThanhToanKLHT": data_json["ThongTinChung"].get("ThanhToanKLHT", "0"),
                    "CoQuanBanHanh": data_json["ThongTinChung"].get("CoQuanBanHanh", ""),
                    "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "TenLoaiVanBan": loaiVanBan,
                    "GiaiDoanID": "",
                    "DuAnID": duAnID,
                    "DieuChinh": "0",
                    "JsonAI": json.dumps(data_json, ensure_ascii=False),
                    "DataOCR": response_text,
                    "TenFile": "*".join([d['filename'] for d in all_data]),
                    "UserID": user_id,
                    "DonViID": don_vi_id
                }
            elif  f"[{loaiVanBan}]" in "[GIAI_NGAN_DNTT];[GIAI_NGAN_GRV];[GIAI_NGAN_THV]":
                van_ban_data = {
                    "VanBanAIID": van_ban_id,
                    "SoVanBan": data_json["ThongTinChung"].get("SoVanBan", ""),
                    "NgayKy": data_json["ThongTinChung"].get("NgayKy", ""),
                    "SoHopDong": data_json["ThongTinChung"].get("SoHopDong", ""),
                    "SoPLHopDong": data_json["ThongTinChung"].get("SoPLHopDong", ""),
                    "SoVanBanCanCu": data_json["ThongTinChung"].get("SoVanBanCanCu", ""),
                    "NgayKyCanCu": data_json["ThongTinChung"].get("NgayKyCanCu", ""),
                    "TenNguonVon": data_json["ThongTinChung"].get("TenNguonVon", ""),
                    "NienDo": data_json["ThongTinChung"].get("NienDo", ""),
                    "LoaiKHVonID": data_json["ThongTinChung"].get("NienDo", "2"), # mặc định là 2 (năm nay)
                    "SoTien": data_json["ThongTinChung"].get("NienDo", "0"),
                    "NguoiKy": data_json["ThongTinChung"].get("NguoiKy", ""),
                    "ChucDanhNguoiKy": data_json["ThongTinChung"].get("ChucDanhNguoiKy", ""),
                    "CoQuanBanHanh": data_json["ThongTinChung"].get("CoQuanBanHanh", ""),
                    "TrichYeu": data_json["ThongTinChung"].get("TrichYeu", ""),
                    "NghiepVuID": data_json["ThongTinChung"].get("NghiepVuID", ""),
                    "TenNhaThau": data_json["ThongTinChung"].get("TenNhaThau", ""),
                    "GiaTri": data_json["ThongTinChung"].get("GiaTri", "0"),
                    "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "TenLoaiVanBan": loaiVanBan,
                    "DuAnID": duAnID,
                    "DieuChinh": data_json["ThongTinChung"].get("DieuChinh", "0"),
                    "JsonAI": json.dumps(data_json, ensure_ascii=False),
                    "DataOCR": response_text,
                    "TenFile": "*".join([d['filename'] for d in all_data])
                }
            van_ban_data["UserID"] = user_id
            van_ban_data["DonViID"] = don_vi_id

            

            db_service = DatabaseService()
            result = await db_service.insert_van_ban_ai(db, van_ban_data, loaiVanBan)
            
            if not result.get("success", False):
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "code": 500,
                        "message": "Lỗi khi lưu dữ liệu vào database",
                        "detail": result.get("error", "Unknown error")
                    }
                )

            # Insert BangDuLieu data if it exists
            if "BangDuLieu" in data_json and data_json["BangDuLieu"] and len(data_json["BangDuLieu"]) > 0:
                bang_du_lieu_data = []
                for item in data_json["BangDuLieu"]:
                    bang_du_lieu_data.append({
                        "VanBanAIID": van_ban_id,
                        **{col: item.get(col, 0) for col in required_columns}
                    })
                bang_du_lieu_result = await db_service.insert_bang_du_lieu_chi_tiet_ai(
                    db, 
                    bang_du_lieu_data,
                    required_columns
                )
                if not bang_du_lieu_result.get("success", False):
                    return JSONResponse(
                        status_code=500,
                        content={
                            "status": "error",
                            "code": 500,
                            "message": "Lỗi khi lưu chi tiết bảng dữ liệu",
                            "detail": bang_du_lieu_result.get("error", "Unknown error")
                        }
                    )
            else:
                print("Văn bản này không có chi tiết bảng dữ liệu")
            # After successful processing and database operations
            try:
                # Get QLDA upload URL from environment
                qlda_upload_url = os.getenv("API_URL_UPLOAD_QLDA")
                if not qlda_upload_url:
                    raise ValueError("Không tìm thấy API_URL_UPLOAD_QLDA trong file .env")

                # Prepare files for upload to QLDA
                files_data = []
                for file in files:
                    # Reset file pointer to beginning
                    await file.seek(0)
                    files_data.append(
                        ("files", (file.filename, file.file, file.content_type))
                    )

                # Upload files to QLDA system
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{qlda_upload_url}/api/v1/Uploads/uploadMultipleFiles",
                        files=files_data,
                        headers={"Authorization": authorization}
                    )
                    
                    if response.status_code != 200:
                        return JSONResponse(
                            status_code=500,
                            content={
                                "status": "error",
                                "code": 500,
                                "message": "Lỗi khi upload file lên hệ thống QLDA",
                                "detail": response.text
                            }
                        )
                    
                    # Lấy response JSON từ API QLDA
                    qlda_response = response.json()
                    
                    try:
                        # Nối các đường dẫn file trong data thành 1 chuỗi, phân cách bằng dấu *
                        string_url_qlda_response = '*'.join(qlda_response['data'])
                        # Thực thi câu lệnh SQL để cập nhật tên file trong bảng VanBanAI
                        update_query = text(f"""
                            UPDATE dbo.VanBanAI 
                            SET tenFile = N'{string_url_qlda_response}'
                            WHERE VanBanAIID = N'{van_ban_id}'
                        """)
                        db.execute(update_query)
                        db.commit()
                    except Exception as e:
                        db.rollback()
                        raise Exception(f"Lỗi khi cập nhật tên file trong bảng VanBanAI: {str(e)}")

                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "success",
                        "code": 200,
                        "message": "Upload và xử lý nhiều file ảnh thành công",
                        "data": {
                            "files_processed": [{"filename": d['filename']} for d in all_data],
                            "van_ban": data_json,
                            "db_status": result.get("success", False),
                            "db_message": result.get("message", ""),
                            "qlda_upload_status": "success",
                            "qlda_response": qlda_response
                        }
                    }
                )

            except Exception as e:
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "code": 500,
                        "message": "Lỗi khi upload file lên hệ thống QLDA",
                        "detail": str(e)
                    }
                )

        except Exception as e:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "code": 400,
                    "message": "Lỗi khi xử lý ảnh",
                    "detail": f"Chi tiết lỗi: {str(e)}\nLoại lỗi: {type(e).__name__}\nTraceback: {traceback.format_exc()}"
                }
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "code": 500,
                "message": "Lỗi hệ thống",
                "detail": str(e)
            }
        )
    finally:
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)

@router.get("/standardized_data")
async def standardized_data(
    duAnID: str,
    authorization: str = Header(...)

):
    # Xác thực token
    try:
        # Kiểm tra header Authorization
        if not authorization.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={
                    "status": "error",
                    "code": 401,
                    "message": "Token không hợp lệ",
                    "detail": "Token phải bắt đầu bằng 'Bearer '"
                }
            )
            
        # Lấy token từ header
        token = authorization.split(" ")[1]
        
        # Giải mã token để lấy userID và donViID
        token_data = decode_jwt_token(token)
        user_id = token_data["userID"]
        don_vi_id = token_data["donViID"]
        
        # Thêm thông tin user vào request
        request_data = {
            "userID": user_id,
            "donViID": don_vi_id
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=401,
            content={
                "status": "error",
                "code": 401,
                "message": "Lỗi xác thực",
                "detail": str(e)
            }
        )

    try:
        # duAnID = ""
        # query_VanBan = f"select DuAnID from VanBanAI where VanBanAIID='{vanBanAIID}'"
        # _dfVanBanAI = lay_du_lieu_tu_sql_server(query_VanBan)
        # if not _dfVanBanAI.empty:
        #     duAnID = _dfVanBanAI.iloc[0]['DuAnID']
        # B1: Lấy dữ liệu từ ChucNangAI
        query_chuc_nang = "select NghiepVuID=ChucNangAIID, ThongTinChung, BangDuLieu from ChucNangAI order by STT"
        dfChucNangAI = lay_du_lieu_tu_sql_server(query_chuc_nang)
        
        # B2: Lấy dữ liệu từ VanBanAI
        query_van_ban = f"""
        select VanBanAIID = convert(nvarchar(36), VanBanAIID)
        , DuAnID = convert(nvarchar(36), DuAnID)
        , SoVanBan, NgayKy=convert(nvarchar(10), NgayKy, 111), NguoiKy, ChucDanhNguoiKy, CoQuanBanHanh, TrichYeu, DieuChinh=isnull(DieuChinh, 0) 
        , TenLoaiVanBan
        , STT_LoaiVanBan = (select STT from dbo.ChucNangAI cn where cn.ChucNangAIID=TenLoaiVanBan)
        , CoQuanBanHanh
        , NguoiKy
        , ChucDanhNguoiKy
        from dbo.VanBanAI 
        where convert(nvarchar(36), DuAnID)='{duAnID}' and isnull(TrangThai, 0) = 0  -- các văn bản chưa insert vào csdl
        order by NgayKy, (select STT from dbo.ChucNangAI cn where cn.ChucNangAIID=TenLoaiVanBan)"""
        #print(query_van_ban)
        dfVanBanAI = lay_du_lieu_tu_sql_server(query_van_ban)
        #print(query_van_ban)
        # B3: Lấy dữ liệu từ BangDuLieuChiTietAI
        query_kmcp = f"select distinct TenKMCP from dbo.BangDuLieuChiTietAI where isnull(TenKMCP, '')<>'' and VanBanAIID in (select VanBanAIID from dbo.VanBanAI vb where convert(nvarchar(36), DuAnID)='{duAnID}' and vb.TenLoaiVanBan IN ('QDPD_CT', 'QDPDDT_CBDT', 'QDPD_DA', 'QDPD_DT_THDT', 'QDPD_KHLCNT_CBDT','QDPD_KHLCNT_THDT'))"
        df_temp = lay_du_lieu_tu_sql_server(query_kmcp)
        chuoi_markdown_tenkmcp = ""
        chuoi_markdown_tenkmcp += "| TenKMCP |\n"
        chuoi_markdown_tenkmcp += "|----------|\n"
        if not df_temp.empty:
            if not df_temp.empty:
                for _, row in df_temp.iterrows():
                    chuoi_markdown_tenkmcp += f"| {row['TenKMCP']} |\n"
                    # tìm kiếm bằng mô hình offline
                    # ket_qua_tim_offline = await find_content_similarity(loaiDuLieu='kmcp', duLieuCanTim=row['TenKMCP'])
                    # if isinstance(ket_qua_tim_offline, JSONResponse):
                    #     ket_qua_tim_offline = ket_qua_tim_offline.body.decode('utf-8')
                    #     ket_qua_tim_offline = json.loads(ket_qua_tim_offline)
                    #     if ket_qua_tim_offline.get('status') == 'success' and ket_qua_tim_offline['data']['success'] == 1:
                    #         dataTimKiemOffline.append(ket_qua_tim_offline['data']['results'][0])
        # print("="*20)
        # print(chuoi_markdown_tenkmcp)
        # print("="*20)

        # print("="*20)
        # print(str(dataTimKiemOffline))
        # print("="*20)
        # print(dataTimKiemOffline)

        promt_anh_xa_noi_dung_tuong_dong = """
Bạn là chuyên gia AI trong lĩnh vực xây dựng cơ bản. Nhiệm vụ của bạn là ánh xạ từng khoản mục chi phí từ danh sách nhập vào (`DanhSachCanAnhXa`) với danh mục khoản mục chi phí chuẩn (`DanhMucChuan`). Hãy thực hiện theo các quy tắc dưới đây:
### QUY TẮC ÁNH XẠ

1. **Ánh xạ 1:1**: Mỗi dòng trong danh sách cần ánh xạ chỉ được gán cho một dòng duy nhất trong danh mục chuẩn.
2. **So khớp từ khóa gần đúng**: Cho phép sai lệch chính tả, viết hoa/thường, từ dư thừa hoặc thiếu, nhưng phải đảm bảo nghĩa gốc tương đương.
3. **Loại bỏ ký tự nhiễu**: Bỏ dấu chấm cuối câu, dấu cách thừa.
4. **Tự động phát hiện và hợp nhất các trường hợp viết khác nhau** (ví dụ: "Chi phí lập Báo cáo kinh tế - kỹ thuật" và "Chí phí lập báo cáo Kinh tế - kỹ thuật").
5. Nếu không tìm được ánh xạ phù hợp, ghi rõ trong cột `GhiChu` = "KHÔNG TÌM ĐƯỢC"

#### Bảng 1 - Danh mục chuẩn chi phí (`DanhSachCanAnhXa`)
"""+chuoi_markdown_tenkmcp+"""

#### Bảng 2 - Danh mục chuẩn chi phí (`DanhMucChuan`)
- Gồm các cột:
  - `MaKMCP`: mã khoản mục chuẩn
  - `TenKMCP`: tên khoản mục chi phí chuẩn
  - `TuKhoaGoiY`: Từ khoá gợi ý
| MaKMCP  | TenKMCP                                                                                                                     | TuKhoaGoiY                                                                                                                   |
| ------- | --------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| CP101   | Chi phí bồi thường về đất, nhà, công trình trên đất, các tài sản gắn liền với đất, trên mặt nước và chi phí bồi thường khác | mặt, nước, về, chi, đất, liền, bồi, trình, các, gắn, thường, công, sản, Chi, nhà, tài, phí, trên, khác, với, và              |
| CP102   | Chi phí các khoản hỗ trợ khi nhà nước thu hồi đất                                                                           | khi, phí, Chi, trợ, nước, đất, nhà, các, hồi, thu, hỗ, khoản                                                                 |
| CP103   | Chi phí tái định cư                                                                                                         | phí, tái, Chi, định, cư                                                                                                      |
| CP104   | Chi phí tổ chức bồi thường, hỗ trợ, tái định cư                                                                             | thường, phí, tái, Chi, trợ, tổ, bồi, chức, định, cư, hỗ                                                                      |
| CP105   | Chi phí sử dụng đất, thuê đất tính trong thời gian xây dựng                                                                 | sử, phí, gian, dụng, Chi, xây, đất, tính, thời, thuê, trong, dựng                                                            |
| CP106   | Chi phí di dời, hoàn trả cho phần hạ tầng kỹ thuật đã được đầu tư xây dựng phục vụ giải phóng mặt bằng                      | mặt, phần, di, bằng, xây, hoàn, cho, hạ, tư, trả, Chi, phóng, giải, được, kỹ, dời, dựng, phí, thuật, tầng, phục, đã, vụ, đầu |
| CP107   | Chi phí đầu tư vào đất                                                                                                      | phí, Chi, đất, vào, tư, đầu                                                                                                  |
| CP199   | Chi phí khác có liên quan đến công tác bồi thường, hỗ trợ, tái định cư                                                      | thường, công, phí, tái, Chi, đến, trợ, khác, tác, quan, bồi, định, có, cư, hỗ, liên                                          |
| CP2     | Chi phí xây dựng                                                                                                            | phí, Chi, xây, dựng                                                                                                          |
| CP221   | Chi phí xây dựng phát sinh                                                                                                  | phí, Chi, phát, xây, sinh, dựng                                                                                              |
| CP222   | Chi phí xây dựng trước thuế                                                                                                 | thuế, phí, Chi, xây, dựng, trước                                                                                             |
| CP223   | Chi phí xây dựng sau thuế                                                                                                   | thuế, phí, Chi, sau, xây, dựng                                                                                               |
| CP224   | Chi phí xây dựng công trình phụ                                                                                             | công, phí, Chi, xây, phụ, trình, dựng                                                                                        |
| CP225   | Chi phí xây dựng công trình chính                                                                                           | công, phí, Chi, xây, trình, chính, dựng                                                                                      |
| CP226   | Chi phí xây dựng điều chỉnh                                                                                                 | phí, Chi, xây, điều, dựng, chỉnh                                                                                             |
| CP227   | Chi phí xây dựng công trình chính và phụ                                                                                    | công, phí, Chi, xây, phụ, trình, và, chính, dựng                                                                             |
| CP228   | Chi phí xây dựng khác                                                                                                       | phí, Chi, xây, khác, dựng                                                                                                    |
| CP3     | Chi phí thiết bị                                                                                                            | phí, bị, Chi, thiết                                                                                                          |
| CP321   | Chi phí thiết bị phát sinh                                                                                                  | phí, Chi, phát, sinh, bị, thiết                                                                                              |
| CP4     | Chi phí quản lý dự án                                                                                                       | quản, phí, án, Chi, dự, lý                                                                                                   |
| CP421   | Chi phí quản lý dự án phát sinh                                                                                             | quản, phí, án, Chi, phát, dự, sinh, lý                                                                                       |
| CP5     | Chi phí tư vấn đầu tư xây dựng                                                                                              | phí, Chi, xây, vấn, tư, dựng, đầu                                                                                            |
| CP501   | Chi phí lập báo cáo nghiên cứu tiền khả thi                                                                                 | lập, cáo, phí, Chi, khả, nghiên, tiền, thi, cứu, báo                                                                         |
| CP502   | Chi phí lập báo cáo nghiên cứu khả thi                                                                                      | lập, cáo, phí, Chi, khả, nghiên, thi, cứu, báo                                                                               |
| CP503   | Chi phí lập báo cáo kinh tế - kỹ thuật                                                                                      | lập, cáo, phí, Chi, tế, thuật, kinh, kỹ, báo                                                                                 |
| CP50301 | Chi phí lập dự án đầu tư                                                                                                    | lập, phí, án, Chi, dự, tư, đầu                                                                                               |
| CP504   | Chi phí thiết kế xây dựng                                                                                                   | phí, Chi, xây, kế, dựng, thiết                                                                                               |
| CP50411 | Chi phí thiết kế xây dựng (Phát sinh)                                                                                       | phí, Chi, xây, sinh, kế, Phát, dựng, thiết                                                                                   |
| CP50420 | Chi phí thiết kế kỹ thuật                                                                                                   | phí, Chi, thuật, kế, kỹ, thiết                                                                                               |
| CP50431 | Chi phí thiết kế kỹ thuật (Phát sinh)                                                                                       | phí, Chi, thuật, Phát, sinh, kế, kỹ, thiết                                                                                   |
| CP505   | Chi phí thiết kế bản vẽ thi công                                                                                            | bản, phí, công, Chi, kế, vẽ, thi, thiết                                                                                      |
| CP50511 | Chi phí thiết kế bản vẽ thi công (Phát sinh)                                                                                | bản, phí, công, Chi, Phát, sinh, kế, vẽ, thi, thiết                                                                          |
| CP50530 | Chi phí lập thiết kế bản vẽ thi công - dự toán                                                                              | lập, bản, phí, công, Chi, toán, dự, kế, vẽ, thi, thiết                                                                       |
| CP50541 | Chi phí lập thiết kế bản vẽ thi công - dự toán (Phát sinh)                                                                  | lập, bản, phí, công, Chi, toán, Phát, dự, sinh, kế, vẽ, thi, thiết                                                           |
| CP506   | Chi phí lập nhiệm vụ khảo sát xây dựng                                                                                      | lập, phí, Chi, xây, nhiệm, vụ, khảo, dựng, sát                                                                               |
| CP50602 | Chi phí lập nhiệm vụ khảo sát (Bước lập báo cáo nghiên cứu tiền khả thi (NCTKT))                                            | lập, cáo, phí, Chi, nhiệm, khả, nghiên, vụ, tiền, thi, NCTKT, khảo, cứu, Bước, báo, sát                                      |
| CP50603 | Chi phí lập nhiệm vụ khảo sát (Bước lập báo cáo nghiên cứu khả thi (NCKT))                                                  | lập, cáo, phí, Chi, nhiệm, khả, NCKT, nghiên, vụ, thi, khảo, cứu, Bước, báo, sát                                             |
| CP50604 | Chi phí lập nhiệm vụ khảo sát (Bước lập thiết kế bản vẽ thi công (TKBVTC))                                                  | lập, bản, phí, công, Chi, nhiệm, TKBVTC, kế, vẽ, vụ, thi, khảo, Bước, thiết, sát                                             |
| CP50605 | Chi phí lập nhiệm vụ khảo sát (Bước lập thiết kế bản vẽ thi công - dự toán (TKBVTC-DT))                                     | lập, bản, phí, công, Chi, toán, nhiệm, dự, TKBVTCDT, kế, vẽ, vụ, thi, khảo, Bước, thiết, sát                                 |
| CP507   | Chi phí thẩm tra báo cáo kinh tế - kỹ thuật                                                                                 | cáo, phí, Chi, tế, thuật, thẩm, tra, kinh, kỹ, báo                                                                           |
| CP508   | Chi phí thẩm tra báo cáo nghiên cứu khả thi                                                                                 | cáo, phí, Chi, thẩm, tra, khả, nghiên, thi, cứu, báo                                                                         |
| CP509   | Chi phí thẩm tra thiết kế xây dựng                                                                                          | phí, Chi, xây, thẩm, tra, kế, dựng, thiết                                                                                    |
| CP50911 | Chi phí thẩm tra thiết kế xây dựng (Phát sinh)                                                                              | phí, Chi, xây, thẩm, tra, sinh, kế, Phát, dựng, thiết                                                                        |
| CP510   | Chi phí thẩm tra dự toán xây dựng                                                                                           | phí, Chi, xây, toán, dự, thẩm, tra, dựng                                                                                     |
| CP51011 | Chi phí thẩm tra dự toán xây dựng (Phát sinh)                                                                               | phí, Chi, xây, toán, dự, thẩm, tra, sinh, Phát, dựng                                                                         |
| CP511   | Chi phí lập hồ sơ mời thầu (hồ sơ yêu cầu), đánh giá hồ sơ dự thầu (hồ sơ đề xuât) tư vấn                                   | lập, đề, phí, Chi, sơ, giá, xuât, hồ, thầu, mời, dự, vấn, tư, yêu, đánh, cầu                                                 |
| CP512   | Chi phí lập hồ sơ mời thầu (hồ sơ yêu cầu) tư vấn                                                                           | lập, phí, Chi, sơ, vấn, hồ, thầu, mời, tư, yêu, cầu                                                                          |
| CP513   | Chi phí đánh giá hồ sơ dự thầu (hồ sơ đề xuất) tư vấn                                                                       | đề, phí, xuất, Chi, sơ, giá, vấn, hồ, thầu, dự, tư, đánh                                                                     |
| CP51311 | Chi phí đánh giá hồ sơ dự thầu (hồ sơ đề xuất) tư vấn (Phát sinh)                                                           | đề, phí, xuất, Chi, sơ, giá, vấn, hồ, thầu, dự, sinh, tư, đánh, Phát                                                         |
| CP514   | Chi phí lập HSMT (HSYC), đánh giá HSDT (HSĐX) thi công xây dựng                                                             | lập, công, phí, Chi, xây, giá, HSYC, HSĐX, HSMT, đánh, thi, dựng, HSDT                                                       |
| CP51411 | Chi phí lập HSMT (HSYC), đánh giá HSDT (HSĐX) thi công xây dựng (Phát sinh)                                                 | lập, công, phí, Chi, xây, giá, HSYC, Phát, HSĐX, sinh, HSMT, đánh, thi, dựng, HSDT                                           |
| CP515   | Chi phí lập hồ sơ mời thầu (hồ sơ yêu cầu) thi công xây dựng                                                                | lập, công, phí, Chi, sơ, xây, hồ, thầu, mời, yêu, thi, cầu, dựng                                                             |
| CP51511 | Chi phí lập hồ sơ mời thầu (hồ sơ yêu cầu) thi công xây dựng (Phát sinh)                                                    | lập, công, phí, Chi, sơ, xây, hồ, thầu, mời, Phát, sinh, yêu, thi, cầu, dựng                                                 |
| CP516   | Chi phí đánh giá hồ sơ dự thầu (hồ sơ đề xuất) thi công xây dựng                                                            | đề, phí, xuất, Chi, sơ, công, giá, xây, hồ, thầu, dự, đánh, thi, dựng                                                        |
| CP51611 | Chi phí đánh giá hồ sơ dự thầu (hồ sơ đề xuất) thi công xây dựng (Phát sinh)                                                | đề, phí, xuất, Chi, sơ, công, giá, xây, hồ, thầu, Phát, dự, sinh, đánh, thi, dựng                                            |
| CP517   | Chi phí lập HSMT (HSYC), đánh giá HSDT (HSĐX) mua sắm vật tư, thiết bị                                                      | lập, phí, Chi, giá, HSYC, sắm, vật, mua, HSĐX, HSMT, tư, đánh, bị, HSDT, thiết                                               |
| CP51711 | Chi phí lập HSMT (HSYC), đánh giá HSDT (HSĐX) mua sắm vật tư, thiết bị (Phát sinh)                                          | lập, phí, Chi, giá, HSYC, sắm, vật, mua, HSĐX, sinh, HSMT, tư, đánh, Phát, bị, HSDT, thiết                                   |
| CP518   | Chi phí lập HSMT (HSYC) mua sắm vật tư, thiết bị                                                                            | lập, phí, Chi, sắm, HSYC, vật, mua, HSMT, tư, bị, thiết                                                                      |
| CP51811 | Chi phí lập HSMT (HSYC) mua sắm vật tư, thiết bị (Phát sinh)                                                                | lập, phí, Chi, sắm, HSYC, vật, mua, sinh, HSMT, tư, Phát, bị, thiết                                                          |
| CP519   | Chi phí đánh giá HSDT (HSĐX) mua sắm vật tư, thiết bị                                                                       | phí, Chi, giá, sắm, vật, mua, HSĐX, tư, đánh, bị, HSDT, thiết                                                                |
| CP51911 | Chi phí đánh giá HSDT (HSĐX) mua sắm vật tư, thiết bị (Phát sinh)                                                           | phí, Chi, giá, sắm, vật, mua, HSĐX, sinh, tư, đánh, Phát, bị, HSDT, thiết                                                    |
| CP520   | Chi phí giám sát thi công xây dựng                                                                                          | công, phí, Chi, xây, thi, dựng, giám, sát                                                                                    |
| CP52099 | Chi phí giám sát thi công xây dựng (Phát sinh)                                                                              | công, phí, Chi, xây, Phát, sinh, thi, dựng, giám, sát                                                                        |
| CP521   | Chi phí giám sát lắp đặt thiết bị                                                                                           | phí, Chi, lắp, đặt, bị, giám, thiết, sát                                                                                     |
| CP52111 | Chi phí giám sát lắp đặt thiết bị (Phát sinh)                                                                               | phí, Chi, lắp, đặt, sinh, Phát, bị, giám, thiết, sát                                                                         |
| CP522   | Chi phí giám sát công tác khảo sát xây dựng                                                                                 | công, phí, Chi, xây, tác, khảo, dựng, giám, sát                                                                              |
| CP523   | Chi phí quy đổi vốn đầu tư xây dựng                                                                                         | phí, Chi, xây, đổi, quy, tư, vốn, dựng, đầu                                                                                  |
| CP526   | Phí thẩm định hồ sơ mời thầu (hồ sơ yêu cầu)                                                                                | sơ, Phí, hồ, thầu, mời, thẩm, định, yêu, cầu                                                                                 |
| CP527   | Chi phí thẩm tra báo cáo nghiên cứu tiền khả thi                                                                            | cáo, phí, Chi, thẩm, tra, khả, nghiên, tiền, thi, cứu, báo                                                                   |
| CP528   | Chi phí khảo sát xây dựng                                                                                                   | phí, Chi, xây, khảo, dựng, sát                                                                                               |
| CP52802 | Chi phí khảo sát (Bước lập báo cáo nghiên cứu tiền khả thi (NCTKT))                                                         | lập, cáo, phí, Chi, khả, nghiên, tiền, thi, NCTKT, khảo, cứu, Bước, báo, sát                                                 |
| CP52803 | Chi phí khảo sát (Bước lập báo cáo nghiên cứu khả thi (NCKT))                                                               | lập, cáo, phí, Chi, khả, NCKT, nghiên, thi, khảo, cứu, Bước, báo, sát                                                        |
| CP52804 | Chi phí khảo sát (Bước lập báo cáo kinh tế kỹ thuật (KTKT))                                                                 | lập, cáo, phí, Chi, tế, thuật, kinh, kỹ, KTKT, khảo, Bước, báo, sát                                                          |
| CP52805 | Chi phí khảo sát (Bước lập thiết kế bản vẽ thi công (TKBVTC))                                                               | lập, bản, phí, công, Chi, TKBVTC, kế, vẽ, thi, khảo, Bước, thiết, sát                                                        |
| CP52806 | Chi phí khảo sát (Bước lập thiết kế bản vẽ thi công - dự toán (TKBVTC-DT))                                                  | lập, bản, phí, công, Chi, toán, dự, TKBVTCDT, kế, vẽ, thi, khảo, Bước, thiết, sát                                            |
| CP532   | Phí thẩm định hồ sơ mời thầu (hồ sơ yêu cầu) gói thầu thi công xây dựng                                                     | công, sơ, xây, Phí, hồ, thầu, mời, thẩm, định, yêu, thi, cầu, gói, dựng                                                      |
| CP533   | Phí thẩm định hồ sơ mời thầu (hồ sơ yêu cầu) gói thầu lắp đặt thiết bị                                                      | sơ, Phí, hồ, thầu, mời, lắp, đặt, thẩm, định, thiết, yêu, bị, cầu, gói                                                       |
| CP534   | Phí thẩm định hồ sơ mời thầu (hồ sơ yêu cầu) gói thầu tư vấn đầu tư xây dựng                                                | sơ, xây, vấn, Phí, hồ, thầu, mời, thẩm, định, tư, yêu, cầu, đầu, gói, dựng                                                   |
| CP535   | Phí thẩm định kết quả lựa chọn nhà thầu thi công xây dựng                                                                   | công, lựa, xây, Phí, thầu, nhà, thẩm, định, chọn, kết, thi, quả, dựng                                                        |
| CP536   | Phí thẩm định kết quả lựa chọn nhà thầu lắp đặt thiết bị                                                                    | lựa, Phí, thầu, nhà, lắp, đặt, thẩm, định, chọn, bị, kết, quả, thiết                                                         |
| CP537   | Phí thẩm định kết quả lựa chọn nhà thầu tư vấn đầu tư xây dựng                                                              | lựa, xây, vấn, Phí, thầu, nhà, thẩm, định, chọn, tư, kết, quả, dựng, đầu                                                     |
| CP538   | Phí thẩm định hồ sơ mời thầu (hồ sơ yêu cầu), đánh giá kết quả lựa chọn nhà thầu (hồ sơ đề xuất) xây lắp                    | giá, mời, lắp, xuất, lựa, sơ, xây, định, quả, đề, hồ, nhà, đánh, kết, Phí, thầu, thẩm, chọn, yêu, cầu                        |
| CP539   | Phí thẩm định hồ sơ mời thầu (hồ sơ yêu cầu), đánh giá kết quả lựa chọn nhà thầu (hồ sơ đề xuất) lắp đặt thiết bị           | giá, mời, lắp, xuất, lựa, sơ, đặt, định, quả, bị, thiết, đề, hồ, nhà, đánh, kết, Phí, thầu, thẩm, chọn, yêu, cầu             |
| CP540   | Phí thẩm định hồ sơ mời thầu (hồ sơ yêu cầu), đánh giá kết quả lựa chọn nhà thầu (hồ sơ đề xuất) tư vấn đầu tư xây dựng     | giá, mời, xuất, lựa, sơ, xây, vấn, định, tư, quả, đề, hồ, nhà, đánh, kết, dựng, Phí, thầu, thẩm, chọn, yêu, cầu, đầu         |
| CP541   | Phí thẩm định hồ sơ mời thầu (hồ sơ yêu cầu), đánh giá kết quả lựa chọn nhà thầu (hồ sơ đề xuất)                            | đề, lựa, xuất, sơ, giá, Phí, hồ, thầu, mời, nhà, thẩm, định, chọn, yêu, đánh, kết, quả, cầu                                  |
| CP551   | Chi phí khảo sát, thiết kế                                                                                                  | phí, Chi, kế, khảo, thiết, sát                                                                                               |
| CP552   | Chi phí nhiệm vụ thử tỉnh cọc                                                                                               | tỉnh, phí, Chi, cọc, nhiệm, thử, vụ                                                                                          |
| CP553   | Công tác điều tra, đo đạt và thu thập số liệu                                                                               | đo, đạt, số, liệu, tác, tra, Công, thập, điều, thu, và                                                                       |
| CP554   | Chi phí kiểm tra và chứng nhận sự phù hợp về chất lượng công trình xây dựng                                                 | phù, phí, công, Chi, xây, sự, hợp, về, chất, nhận, tra, lượng, trình, kiểm, chứng, và, dựng                                  |
| CP556   | Chi phí thẩm tra an toàn giao thông                                                                                         | thông, phí, Chi, an, toàn, thẩm, tra, giao                                                                                   |
| CP557   | Chi phí thử tĩnh                                                                                                            | tĩnh, phí, Chi, thử                                                                                                          |
| CP558   | Chi phí công bố quy hoạch                                                                                                   | công, phí, bố, Chi, hoạch, quy                                                                                               |
| CP559   | Chi phí thử tải cừ tràm                                                                                                     | tràm, phí, Chi, cừ, thử, tải                                                                                                 |
| CP560   | Chi phí kiểm định chất lượng phục vụ công tác nghiệm thu                                                                    | công, phí, nghiệm, Chi, chất, tác, lượng, định, phục, vụ, thu, kiểm                                                          |
| CP561   | Chi phí cắm mốc ranh giải phóng mặt bằng                                                                                    | mặt, phí, mốc, Chi, ranh, giải, phóng, bằng, cắm                                                                             |
| CP56111 | Chi phí lập đồ án quy hoạch                                                                                                 | lập, phí, án, Chi, hoạch, đồ, quy                                                                                            |
| CP56201 | Chi phí khảo sát địa chất                                                                                                   | phí, Chi, chất, địa, khảo, sát                                                                                               |
| CP56202 | Chi phí khảo sát địa chất (Bước lập báo cáo nghiên cứu tiền khả thi (NCTKT))                                                | lập, cáo, phí, Chi, chất, khả, địa, nghiên, tiền, thi, NCTKT, khảo, cứu, Bước, báo, sát                                      |
| CP56203 | Chi phí khảo sát địa chất (Bước lập báo cáo nghiên cứu khả thi (NCKT))                                                      | lập, cáo, phí, Chi, chất, khả, NCKT, địa, nghiên, thi, khảo, cứu, Bước, báo, sát                                             |
| CP56204 | Chi phí khảo sát địa chất (Bước lập báo cáo kinh tế kỹ thuật (KTKT))                                                        | lập, cáo, phí, Chi, tế, chất, thuật, địa, kinh, kỹ, KTKT, khảo, Bước, báo, sát                                               |
| CP56205 | Chi phí khảo sát địa chất (Bước lập thiết kế bản vẽ thi công (BVTC))                                                        | lập, bản, phí, công, Chi, chất, BVTC, địa, kế, vẽ, thi, khảo, Bước, thiết, sát                                               |
| CP56206 | Chi phí khảo sát địa chất (Bước lập thiết kế bản vẽ thi công - dự toán (BVTC-DT))                                           | lập, bản, phí, công, Chi, chất, toán, dự, BVTCDT, địa, kế, vẽ, thi, khảo, Bước, thiết, sát                                   |
| CP563   | Chi phí thẩm tra tính hiệu quả, tính khả thi của dự án                                                                      | phí, án, Chi, dự, tính, thẩm, tra, khả, hiệu, thi, quả, của                                                                  |
| CP56301 | Chi phí khảo sát địa hình                                                                                                   | phí, Chi, hình, địa, khảo, sát                                                                                               |
| CP56302 | Chi phí khảo sát địa hình (Bước lập báo cáo nghiên cứu tiền khả thi (NCTKT))                                                | lập, cáo, phí, Chi, hình, khả, địa, nghiên, tiền, thi, NCTKT, khảo, cứu, Bước, báo, sát                                      |
| CP56303 | Chi phí khảo sát địa hình (Bước lập báo cáo nghiên cứu khả thi (NCKT))                                                      | lập, cáo, phí, Chi, hình, khả, NCKT, địa, nghiên, thi, khảo, cứu, Bước, báo, sát                                             |
| CP56304 | Chi phí khảo sát địa hình (Bước lập báo cáo kinh tế kỹ thuật (KTKT))                                                        | lập, cáo, phí, Chi, hình, tế, thuật, địa, kinh, kỹ, KTKT, khảo, Bước, báo, sát                                               |
| CP56305 | Chi phí khảo sát địa hình (Bước lập thiết kế bản vẽ thi công (BVTC))                                                        | lập, bản, phí, công, Chi, hình, BVTC, địa, kế, vẽ, thi, khảo, Bước, thiết, sát                                               |
| CP56306 | Chi phí khảo sát địa hình (Bước lập thiết kế bản vẽ thi công - dự toán (BVTC-DT))                                           | lập, bản, phí, công, Chi, hình, toán, dự, BVTCDT, địa, kế, vẽ, thi, khảo, Bước, thiết, sát                                   |
| CP564   | Tư vấn lập văn kiện dự án và các báo cáo thành phần của dự án                                                               | lập, cáo, án, kiện, vấn, phần, văn, Tư, dự, các, của, thành, và, báo                                                         |
| CP56401 | Chi phí khảo sát địa hình, địa hình                                                                                         | phí, Chi, hình, địa, khảo, sát                                                                                               |
| CP565   | Chi phí lập kế hoạch bảo vệ môi trường                                                                                      | lập, phí, bảo, Chi, hoạch, môi, kế, trường, vệ                                                                               |
| CP566   | Chi phí lập báo cáo đánh giá tác động môi trường                                                                            | lập, cáo, phí, Chi, giá, tác, động, môi, đánh, trường, báo                                                                   |
| CP567   | Chi phí thí nghiệm đối chứng, kiểm định xây dựng, thử nghiệm khả năng chịu lực của công trình                               | công, phí, nghiệm, Chi, thí, xây, năng, chịu, lực, đối, thử, định, khả, trình, kiểm, chứng, dựng, của                        |
| CP568   | Chi phí chuẩn bị đầu tư ban đầu sáng tác thi tuyển mẫu phác thảo bước 1                                                     | phí, Chi, mẫu, phác, bước, tác, sáng, thảo, 1, tư, ban, thi, tuyển, chuẩn, bị, đầu                                           |
| CP569   | Chi phí chỉ đạo thể hiện phần mỹ thuật                                                                                      | mỹ, phí, đạo, Chi, thuật, hiện, phần, thể, chỉ                                                                               |
| CP570   | Chi phí nội đồng nghệ thuật                                                                                                 | phí, Chi, thuật, đồng, nội, nghệ                                                                                             |
| CP571   | Chi phí sáng tác mẫu phác thảo tượng đài                                                                                    | phí, Chi, mẫu, phác, đài, tác, sáng, thảo, tượng                                                                             |
| CP572   | Chi phí hoạt động của Hội đồng nghệ thuật                                                                                   | phí, Chi, thuật, đồng, động, Hội, hoạt, nghệ, của                                                                            |
| CP573   | Chi phí giám sát thi công xây dựng phát sinh                                                                                | công, phí, Chi, xây, phát, sinh, thi, dựng, giám, sát                                                                        |
| CP57301 | Chi phí kiểm định theo yêu cầu chủ đầu tư                                                                                   | theo, phí, Chi, định, tư, yêu, kiểm, cầu, đầu, chủ                                                                           |
| CP574   | Chi phí tư vấn thẩm tra dự toán                                                                                             | phí, Chi, vấn, toán, dự, thẩm, tra, tư                                                                                       |
| CP57401 | Chi phí thẩm tra dự toán phát sinh                                                                                          | phí, Chi, phát, toán, dự, thẩm, tra, sinh                                                                                    |
| CP575   | Chi phí thẩm định dự toán giá gói thầu                                                                                      | phí, Chi, giá, toán, thầu, dự, thẩm, định, gói                                                                               |
| CP577   | Chi phí lập hồ sơ điều chỉnh dự toán                                                                                        | lập, phí, Chi, sơ, toán, hồ, dự, điều, chỉnh                                                                                 |
| CP578   | Chi phí chuyển giao công nghệ                                                                                               | công, phí, Chi, chuyển, nghệ, giao                                                                                           |
| CP579   | Chi phí thẩm định giá                                                                                                       | phí, Chi, giá, thẩm, định                                                                                                    |
| CP580   | Chi phí tư vấn giám sát                                                                                                     | phí, Chi, vấn, tư, giám, sát                                                                                                 |
| CP581   | Chi phí báo cáo giám sát đánh giá đầu tư                                                                                    | cáo, phí, Chi, đầu, giá, tư, đánh, giám, báo, sát                                                                            |
| CP582   | Chi phí thẩm tra thiết kế bản vẽ thi công - dự toán (BVTC-DT)                                                               | bản, phí, công, Chi, toán, dự, thẩm, tra, BVTCDT, kế, vẽ, thi, thiết                                                         |
| CP58211 | Chi phí thẩm tra thiết kế bản vẽ thi công - dự toán (BVTC-DT) (Phát sinh)                                                   | bản, phí, công, Chi, toán, Phát, dự, thẩm, tra, sinh, BVTCDT, kế, vẽ, thi, thiết                                             |
| CP58220 | Chi phí thẩm tra thiết kế bản vẽ thi công (BVTC)                                                                            | bản, phí, công, Chi, thẩm, tra, BVTC, kế, vẽ, thi, thiết                                                                     |
| CP58231 | Chi phí thẩm tra thiết kế bản vẽ thi công (BVTC) (Phát sinh)                                                                | bản, phí, công, Chi, Phát, thẩm, tra, BVTC, sinh, kế, vẽ, thi, thiết                                                         |
| CP583   | Tư vấn đầu tư xây dựng                                                                                                      | xây, vấn, Tư, tư, dựng, đầu                                                                                                  |
| CP584   | Chi phí đăng báo đấu thầu                                                                                                   | phí, Chi, thầu, đăng, đấu, báo                                                                                               |                                                                                                                                                                                           |
| CP585   | Chi phí đo vẽ hiện trạng                                                                                                    | phí, Chi, vẽ, do, hiện, trạng                                                                                                |                                                                                                                                                                                           |
| CP599   | Chi phí đo đạc thu hồi đất                                                                                                  | đo, phí, Chi, đất, thu, hồi, đạc                                                                                             |
| CP6     | Chi phí khác                                                                                                                | khác, phí, Chi                                                                                                               |
| CP601   | Phí thẩm định dự án đầu tư xây dựng                                                                                         | án, xây, Phí, dự, thẩm, định, tư, dựng, đầu                                                                                  |
| CP602   | Phí thẩm định dự toán xây dựng                                                                                              | xây, Phí, toán, dự, thẩm, định, dựng                                                                                         |
| CP603   | Chi phí rà phá bom mìn, vật nổ                                                                                              | phí, phá, rà, Chi, vật, mìn, nổ, bom                                                                                         |
| CP604   | Phí thẩm định phê duyệt thiết kế về phòng cháy và chữa cháy                                                                 | về, Phí, chữa, phòng, thẩm, phê, định, cháy, kế, duyệt, và, thiết                                                            |
| CP605   | Chi phí thẩm định giá thiết bị                                                                                              | phí, Chi, giá, thẩm, định, bị, thiết                                                                                         |
| CP606   | Phí thẩm định thiết kế xây dựng triển khai sau thiết kế cơ sở                                                               | khai, xây, sau, Phí, sở, thẩm, triển, định, kế, cơ, dựng, thiết                                                              |
| CP607   | Chi phí thẩm tra, phê duyệt quyết toán                                                                                      | phí, Chi, toán, quyết, thẩm, phê, tra, duyệt                                                                                 |
| CP608   | Chi phí kiểm tra công tác nghiệm thu                                                                                        | công, phí, nghiệm, Chi, tác, tra, thu, kiểm                                                                                  |
| CP609   | Chi phí kiểm toán độc lập                                                                                                   | lập, phí, Chi, toán, độc, kiểm                                                                                               |
| CP60902 | Chi phí kiểm toán công trình                                                                                                | công, phí, Chi, toán, trình, kiểm                                                                                            |
| CP60999 | Chi phí kiểm toán độc lập (Phát sinh)                                                                                       | lập, phí, Chi, toán, sinh, Phát, độc, kiểm                                                                                   |
| CP610   | Chi phí bảo hiểm                                                                                                            | hiểm, phí, Chi, bảo                                                                                                          |
| CP61099 | Chi phí bảo hiểm (Phát sinh)                                                                                                | phí, bảo, Chi, Phát, sinh, hiểm                                                                                              |
| CP611   | Chi phí thẩm định báo cáo đánh giá tác động môi trường                                                                      | cáo, phí, Chi, giá, tác, thẩm, động, định, môi, đánh, trường, báo                                                            |
| CP612   | Chi phí bảo hành, bảo trì                                                                                                   | trì, phí, hành, Chi, bảo                                                                                                     |
| CP613   | Phí bảo vệ môi trường                                                                                                       | bảo, Phí, môi, trường, vệ                                                                                                    |
| CP614   | Chi phí di dời điện                                                                                                         | phí, Chi, dời, điện, di                                                                                                      |
| CP61401 | Chi phí di dời hệ thống điện chiếu sáng                                                                                     | phí, thống, Chi, sáng, hệ, chiếu, dời, điện, di                                                                              |
| CP61402 | Chi phí di dời đường dây hạ thế                                                                                             | phí, Chi, đường, thế, dây, hạ, dời, di                                                                                       |
| CP61403 | Chi phí di dời nhà                                                                                                          | phí, Chi, nhà, dời, di                                                                                                       |
| CP61404 | Chi phí di dời nước                                                                                                         | phí, Chi, nước, dời, di                                                                                                      |
| CP61405 | Chi phí di dời trụ điện trong trường                                                                                        | phí, Chi, trụ, trường, dời, điện, di, trong                                                                                  |
| CP615   | Phí thẩm tra di dời điện                                                                                                    | Phí, thẩm, tra, dời, điện, di                                                                                                |
| CP616   | Chi phí hạng mục chung                                                                                                      | mục, phí, Chi, hạng, chung                                                                                                   |
| CP617   | Chi phí đo đạc địa chính                                                                                                    | đo, phí, Chi, địa, chính, đạc                                                                                                |
| CP61701 | Chi phí đo đạc bản đồ địa chính                                                                                        | đo, đô, Chi, chinh, ban, phi, đạc, đia                                                                                       |
| CP61702 | Chi phí đo đạc lập bản đồ địa chính giải phóng mặt bằng (GPMB)                                                              | đo, lập, phí, bản, Chi, phóng, giải, mặt, bằng, GPMB, đồ, địa, chính, đạc                                                    |
| CP61703 | Chi phí đo đạc, đền bù giải phóng mặt bằng (GPMB)                                                                           | đo, mặt, phí, GPMB, Chi, bù, giải, phóng, bằng, đền, đạc                                                                     |
| CP61704 | Chi phí đo đạc thu hồi đất                                                                                                  | đo, phí, Chi, đất, thu, hồi, đạc                                                                                             |
| CP61820 | Chi phí tổ chức kiểm tra công tác nghiệm thu                                                                                | công, phí, nghiệm, Chi, tác, tổ, chức, tra, thu, kiểm                                                                        |
| CP619   | Chi phí lán trại                                                                                                            | lán, phí, trại, Chi                                                                                                          |
| CP620   | Chi phí đảm bảo giao thông                                                                                                  | thông, phí, bảo, Chi, đảm, giao                                                                                              |
| CP621   | Chi phí điều tiết giao thông                                                                                                | thông, phí, Chi, điều, giao, tiết                                                                                            |
| CP62101 | Chi phí điều tiết giao thông khác                                                                                           | thông, phí, Chi, khác, điều, giao, tiết                                                                                      |
| CP622   | Chi phí một số công tác không xác định số lượng từ thiết kế                                                                 | công, phí, số, Chi, tác, từ, lượng, định, xác, kế, một, không, thiết                                                         |
| CP623   | Chi phí thẩm định thiết kế bản vẽ thi công, lệ phí thẩm định báo cáo kinh tế kỹ thuật (KTKT)                                | bản, phí, công, Chi, cáo, tế, kỹ, thuật, thẩm, định, báo, kế, vẽ, kinh, thi, KTKT, lệ, thiết                                 |
| CP624   | Chi phí nhà tạm                                                                                                             | phí, Chi, nhà, tạm                                                                                                           |
| CP62501 | Chi phí giám sát đánh giá đầu tư                                                                                            | phí, Chi, đầu, giá, tư, đánh, giám, sát                                                                                      |
| CP626   | Chi phí thẩm định kết quả lựa chọn nhà thầu                                                                                 | phí, lựa, Chi, thầu, nhà, thẩm, định, chọn, kết, quả                                                                         |
| CP62701 | Chi phí khoan địa chất                                                                                                      | phí, Chi, chất, địa, khoan                                                                                                   |
| CP628   | Chi phí thẩm định đồ án quy hoạch                                                                                           | phí, án, Chi, hoạch, đồ, thẩm, quy, định                                                                                     |
| CP629   | Chi phí thẩm định HSMT (HSYC)                                                                                               | phí, Chi, HSYC, thẩm, HSMT, định                                                                                             |
| CP630   | Lệ phí thẩm tra thiết kế                                                                                                    | phí, Lệ, thẩm, tra, kế, thiết                                                                                                |
| CP631   | Phí thẩm định lựa chọn nhà thầu                                                                                             | lựa, Phí, thầu, nhà, thẩm, định, chọn                                                                                        |
| CP632   | Chi phí thẩm tra quyết toán                                                                                                 | phí, Chi, toán, quyết, thẩm, tra                                                                                             |
| CP633   | Chi phí thẩm định phê duyệt quyết toán                                                                                      | phí, Chi, toán, quyết, thẩm, phê, định, duyệt                                                                                |
| CP634   | Chi phí thẩm định báo cáo nghiên cứu khả thi                                                                                | cáo, phí, Chi, thẩm, định, khả, nghiên, thi, cứu, báo                                                                        |
| CP699   | Chi phí khác                                                                                                                | khác, phí, Chi                                                                                                               |
| CP7     | Chi phí dự phòng                                                                                                            | dự, phí, Chi, phòng                                                                                                          |
| CP701   | Chi phí dự phòng cho khối lượng, công việc phát sinh                                                                        | việc, công, phí, Chi, phát, cho, dự, phòng, sinh, lượng, khối                                                                |
| CP702   | Chi phí dự phòng cho yếu tố trược giá                                                                                       | phí, Chi, giá, cho, dự, phòng, tố, yếu, trược                                                                                |
| CP703   | Chi phí dự phòng phát sinh khối lượng (cho yếu tố khối lượng phát sinh (KLPS))                                              | phí, Chi, KLPS, phát, cho, dự, phòng, sinh, lượng, khối, tố, yếu                                                             |

### Kết quả trả về:
Xuất dạng chuỗi JSON duy nhất, không cần giải thích, gồm các trường sau:
```json
{
  "TenKMCP": "<tên khoản mục thực tế>",
  "TenKMCP_Moi": "<tên khoản mục chuẩn>",
  "MaKMCP": "<mã khoản mục chuẩn>",
  "GhiChu": "<tỷ lệ tương đồng hoặc ghi chú ánh xạ thủ công theo nghiệp vụ>"
}
```

"""
        # print("+"*20+"promt_anh_xa_noi_dung_tuong_dong")
        # print(promt_anh_xa_noi_dung_tuong_dong)
        # print("+"*20)
        # Gọi OpenAI API để xử lý
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        response = client.chat.completions.create(
            model=model_openai,
            messages=[
                {
                    "role": "system",
                    "content": """Bạn là một chuyên gia về lĩnh vực Đầu tư xây dựng cơ bản. Bạn chuyên ánh xạ tương đồng nội dung (từ ngữ tương đồng, ý nghĩa tương đồng)"""
                },
                {
                    "role": "user",
                    "content": promt_anh_xa_noi_dung_tuong_dong
                }
            ],
            temperature=0,
            max_tokens=15000
        )

        try:
            # Xử lý response từ OpenAI
            response_text = response.choices[0].message.content
            print("===response_text anh_xa_noi_dung===")
            print(response_text)
            print("===end response_text anh_xa_noi_dung===")
            if response_text.strip().startswith("```json"):
                response_text = response_text.strip()[7:-3].strip()
            elif response_text.strip().startswith("```"):
                response_text = response_text.strip()[3:-3].strip()
            #print(response_text)
            # Phân tích chuỗi JSON thành một đối tượng Python (dictionary)
            dataJson = json.loads(response_text)

            # Lấy ra list từ key "results"
            result_list = dataJson
            # Chuyển đổi list trở lại thành chuỗi JSON
            new_response_text = json.dumps(result_list, indent=4, ensure_ascii=False)
            # Chuyển đổi response thành DataFrame
            dfBangGhepKMCP = pd.read_json(new_response_text)
            # Thực hiện cập nhật dữ liệu vào database
            # Sắp xếp DataFrame theo cột TenKMCP_Moi tăng dần
            dfBangGhepKMCP = dfBangGhepKMCP.sort_values(by='TenKMCP_Moi', ascending=True)
            
            #print(dfBangGhepKMCP)

            # Duyệt qua từng dòng trong DataFrame để xử lý trường hợp GhiChu='Không có thông tin'
            for index, row in dfBangGhepKMCP.iterrows():
                if row['GhiChu'] == 'KHÔNG TÌM ĐƯỢC':
                    print("+"*20+"tim_kmcp_offline")
                    print(row['TenKMCP'])
                    print("+"*20)
                    ket_qua_tim_offline = await find_content_similarity(loaiDuLieu='kmcp', duLieuCanTim=row['TenKMCP'])
                    if isinstance(ket_qua_tim_offline, JSONResponse):
                        ket_qua_tim_offline = ket_qua_tim_offline.body.decode('utf-8')
                        ket_qua_tim_offline = json.loads(ket_qua_tim_offline)
                        print("+"*20+"ket_qua_tim_offline")
                        print(str(ket_qua_tim_offline))
                        print("+"*20)
                        # Kiểm tra kết quả tìm kiếm offline có thành công không
                        if ket_qua_tim_offline.get('status') == 'success' and ket_qua_tim_offline['data']['success'] == 1:
                            # Kiểm tra có kết quả tìm được không
                            if len(ket_qua_tim_offline['data']['results']) > 0:
                                # Truy vấn lấy mã KMCP từ database dựa trên KMCPID tìm được
                                query_ma_kmcp = f"select MaKMCP=replace(MaKMCP, '.', '') from dbo.KMCP where KMCPID='{ket_qua_tim_offline['data']['results'][0]['KMCPID']}'"
                                df_ma_kmcp = lay_du_lieu_tu_sql_server(query_ma_kmcp)
                                # Lấy mã KMCP từ kết quả truy vấn, nếu không có thì gán chuỗi rỗng
                                chuoiMaKMCP = df_ma_kmcp.iloc[0]['MaKMCP'] if not df_ma_kmcp.empty else ''
                                
                                # Nếu tìm được mã KMCP
                                if chuoiMaKMCP != '':
                                    # Cập nhật thông tin vào DataFrame
                                    dfBangGhepKMCP.at[index, 'MaKMCP'] = chuoiMaKMCP
                                    dfBangGhepKMCP.at[index, 'TenKMCP_Moi'] = ket_qua_tim_offline['data']['results'][0]['TenKMCP']
                                    dfBangGhepKMCP.at[index, 'GhiChu'] = 'Ánh xạ bằng thuật toán'
                                else:
                                    # Nếu không tìm được mã KMCP, cập nhật các trường thành rỗng
                                    dfBangGhepKMCP.at[index, 'MaKMCP'] = ''
                                    dfBangGhepKMCP.at[index, 'TenKMCP_Moi'] = ''
                                    dfBangGhepKMCP.at[index, 'GhiChu'] = 'KHÔNG TÌM ĐƯỢC'
                            else:
                                # Nếu không có kết quả tìm kiếm, cập nhật các trường thành rỗng
                                dfBangGhepKMCP.at[index, 'TenKMCP_Moi'] = ''
                                dfBangGhepKMCP.at[index, 'MaKMCP'] = ''
                        else:                    
                            # Nếu tìm kiếm không thành công, cập nhật các trường thành rỗng
                            dfBangGhepKMCP.at[index, 'TenKMCP_Moi'] = ''
                            dfBangGhepKMCP.at[index, 'MaKMCP'] = ''
            
            #print(dfBangGhepKMCP)

            query_van_ban = f"""
            select 
            BangDuLieuChiTietAIID = convert(nvarchar(36), BangDuLieuChiTietAIID)
            , VanBanAIID = convert(nvarchar(36), VanBanAIID)
            , TenKMCP, TenKMCP_AI, MaKMCP='', GhiChuAI='', 
            HinhThucLCNT=isnull(HinhThucLCNT, ''),
            PhuongThucLCNT=isnull(PhuongThucLCNT, ''),
            LoaiHopDong=isnull(LoaiHopDong, ''),
            HinhThucDThID = convert(nvarchar(36), HinhThucDThID), 
            PhuongThucDThID = convert(nvarchar(36), PhuongThucDThID), 
            LoaiHopDongID = convert(nvarchar(36), LoaiHopDongID)
            from dbo.BangDuLieuChiTietAI ct 
            where VanBanAIID in (select VanBanAIID from dbo.VanBanAI vb where convert(nvarchar(36), DuAnID)='{duAnID}' and vb.TenLoaiVanBan IN ('QDPD_CT', 'QDPDDT_CBDT', 'QDPD_DA', 'QDPD_DT_THDT', 'QDPD_KHLCNT_CBDT','QDPD_KHLCNT_THDT')
                and isnull(TrangThai, 0) = 0)  -- các văn bản chưa insert vào csdl
            """
            #print(query_van_ban)
            dfBangDuLieuChiTietAI = lay_du_lieu_tu_sql_server(query_van_ban)

            # Duyệt qua từng dòng trong dfBangDuLieuChiTietAI
            for index, row in dfBangDuLieuChiTietAI.iterrows():
                # Tìm dòng tương ứng trong dfBangGhepKMCP có TenKMCP trùng khớp
                matching_row = dfBangGhepKMCP[dfBangGhepKMCP['TenKMCP'].str.lower() == row['TenKMCP'].lower()]
                # Nếu tìm thấy dòng tương ứng
                if not matching_row.empty:
                    # Cập nhật TenKMCP_AI trong dfBangDuLieuChiTietAI
                    dfBangDuLieuChiTietAI.at[index, 'TenKMCP_AI'] = matching_row.iloc[0]['TenKMCP_Moi']

            # print("-0"*20)
            # print(dfBangDuLieuChiTietAI)
            # print("-0"*20)

            # Lọc ra danh sách distinct theo VanBanAIID
            dfDistinctVanBanAIID = dfBangDuLieuChiTietAI.drop_duplicates(subset=['VanBanAIID'])
            chuoi_kmcp_khong_ghep_duoc = []
            kmcp_ghep_duoc = []
            # Duyệt qua từng phần tử trong dfDistinctVanBanAIID
            for _, row in dfDistinctVanBanAIID.iterrows():
                van_ban_id = row['VanBanAIID']
                # Lọc dữ liệu từ dfBangDuLieuChiTietAI theo VanBanAIID
                df_filtered = dfBangDuLieuChiTietAI[dfBangDuLieuChiTietAI['VanBanAIID'] == van_ban_id]
                # print(f"\nDữ liệu cho VanBanAIID: {van_ban_id}")
                # print(df_filtered)
                # Duyệt qua từng dòng trong df_filtered
                for idx, filtered_row in df_filtered.iterrows():
                    # Tìm dòng tương ứng trong dfBangGhepKMCP có TenKMCP trùng khớp
                    matching_row = dfBangGhepKMCP[dfBangGhepKMCP['TenKMCP'].str.lower() == filtered_row['TenKMCP'].lower()]
                    # Nếu tìm thấy dòng tương ứng
                    if not matching_row.empty:
                        # Cập nhật TenKMCP_AI trong df_filtered
                        df_filtered.at[idx, 'TenKMCP_AI'] = matching_row.iloc[0]['TenKMCP_Moi']
                        df_filtered.at[idx, 'MaKMCP'] = matching_row.iloc[0]['MaKMCP']
                        df_filtered.at[idx, 'GhiChuAI'] = matching_row.iloc[0]['GhiChu']
                
                # Cập nhật lại dfBangDuLieuChiTietAI với dữ liệu đã được xử lý
                dfBangDuLieuChiTietAI.update(df_filtered)
                # Duyệt qua từng dòng trong df_filtered
                for idx, row in df_filtered.iterrows():
                    # Kiểm tra xem có nhiều hơn 1 dòng có cùng TenKMCP_Moi không
                    if df_filtered[df_filtered['TenKMCP_AI'] == row['TenKMCP_AI']].shape[0] > 1:
                        # Lưu lại BangDuLieuChiTietAIID của dòng hiện tại
                        bang_du_lieu_id = row['BangDuLieuChiTietAIID']
                        if str(row['MaKMCP']).strip() == "":
                            continue
                        # Truy vấn CSDL để tìm các KMCP khác có tên bắt đầu bằng TenKMCP_AI hiện tại
                        query_kmcp = f"""
                        SELECT MaKMCP, TenKMCP 
                        FROM dbo.KMCP 
                        WHERE TenKMCP LIKE N'{row['TenKMCP_AI']}%' 
                        AND TenKMCP <> N'{row['TenKMCP_AI']}'
                        ORDER BY LEN(TenKMCP), TenKMCP
                        """
                        df_kmcp = lay_du_lieu_tu_sql_server(query_kmcp)
                        
                        if not df_kmcp.empty:
                            # Lấy tất cả các dòng có cùng TenKMCP_AI
                            duplicate_rows = df_filtered[df_filtered['TenKMCP_AI'].str.lower() == row['TenKMCP_AI'].lower()]
                            
                            # Duyệt qua từng dòng trùng lặp và gán KMCP khác nhau
                            for i, (_, duplicate_row) in enumerate(duplicate_rows.iterrows()):
                                if i < len(df_kmcp):
                                    # Cập nhật dòng trùng lặp với tên KMCP mới từ CSDL
                                    df_filtered.loc[df_filtered['BangDuLieuChiTietAIID'] == duplicate_row['BangDuLieuChiTietAIID'], 'TenKMCP_AI'] = df_kmcp.iloc[i]['TenKMCP']
                                    df_filtered.loc[df_filtered['BangDuLieuChiTietAIID'] == duplicate_row['BangDuLieuChiTietAIID'], 'MaKMCP'] = df_kmcp.iloc[i]['MaKMCP']
                                else:
                                    # Nếu hết KMCP để gán, thêm số thứ tự vào tên
                                    df_filtered.loc[df_filtered['BangDuLieuChiTietAIID'] == duplicate_row['BangDuLieuChiTietAIID'], 'TenKMCP_AI'] = f"{row['TenKMCP_AI']} ({i+1})"
                                    df_filtered.loc[df_filtered['BangDuLieuChiTietAIID'] == duplicate_row['BangDuLieuChiTietAIID'], 'MaKMCP'] = f"{row['MaKMCP']}_{i+1}"

                #print(f"\nDữ liệu cho VanBanAIID: {van_ban_id}")
                #print(df_filtered)
                
                for index, row in df_filtered.iterrows():
                    #print(row)
                    if str(row['MaKMCP']).strip() == "":
                        chuoi_kmcp_khong_ghep_duoc.append({'TenKMCP': str(row['TenKMCP']).strip()})
                    else:
                        kmcp_ghep_duoc.append(row)
                    query_insert = "Update dbo.BangDuLieuChiTietAi set TenKMCP_AI=N'{}', KMCPID=(select top 1 KMCPID from dbo.KMCP Km where replace(Km.MaKMCP, '.', '')=replace(N'{}', '.', '')), CoCauVonID=(select top 1 CoCauVonID from dbo.KMCP Km where replace(Km.MaKMCP, '.', '')=replace(N'{}', '.', '')), GhiChuAI=N'{}' where BangDuLieuChiTietAIID=N'{}'".format(
                        row['TenKMCP_AI'],
                        row['MaKMCP'].replace("'", ""),
                        row['MaKMCP'].replace("'", ""),
                        row['GhiChuAI'].replace("'", ""),
                        row['BangDuLieuChiTietAIID']
                    )

                    # print(f"Executing SQL query: {query_insert}")
                    thuc_thi_truy_van(query_insert)

            # Duyệt từng dòng trong dfBangDuLieuChiTietAI
            # print("\n=== Chi tiết dữ liệu trong dfBangDuLieuChiTietAI ===")
            # for index, row in dfBangDuLieuChiTietAI.iterrows():
            #     print(f"\nDòng {index + 1}:")
            #     for column in dfBangDuLieuChiTietAI.columns:
            #         print(f"{column}: {row[column]}")
            #     print("-" * 50)
            # print("\n=== Kết thúc chi tiết dữ liệu ===\n")
            for index, row in dfBangDuLieuChiTietAI.iterrows():
                # print(f"Row data: {row}")
                # Xử lý PhuongThucLCNT
                if str(row['PhuongThucLCNT']).strip() != "":
                    result_pt = await find_content_similarity(loaiDuLieu='phuongthucdth', duLieuCanTim=row['PhuongThucLCNT'])
                    # Chuyển đổi JSONResponse thành dict trước khi serialize
                    if isinstance(result_pt, JSONResponse):
                        result_pt = result_pt.body.decode('utf-8')
                        result_pt = json.loads(result_pt)
                    if result_pt.get('status') == 'success' and result_pt['data']['success'] == 1:
                        phuong_thuc_id = result_pt['data']['results'][0]['PhuongThucDThID']
                        query_update = f"UPDATE dbo.BangDuLieuChiTietAI SET PhuongThucDThID = '{phuong_thuc_id}' WHERE BangDuLieuChiTietAIID = '{row['BangDuLieuChiTietAIID']}'"
                        # print(f"Executing SQL query: {query_update}")
                        thuc_thi_truy_van(query_update)

                # Xử lý LoaiHopDong
                if str(row['LoaiHopDong']).strip() != "":
                    result_lhd = await find_content_similarity(loaiDuLieu='loaihopdong', duLieuCanTim=row['LoaiHopDong'])
                    # Chuyển đổi JSONResponse thành dict trước khi serialize
                    if isinstance(result_lhd, JSONResponse):
                        result_lhd = result_lhd.body.decode('utf-8')
                        result_lhd = json.loads(result_lhd)
                    if result_lhd.get('status') == 'success' and result_lhd['data']['success'] == 1:
                        loai_hop_dong_id = result_lhd['data']['results'][0]['LoaiHopDongID']
                        query_update = f"UPDATE dbo.BangDuLieuChiTietAI SET LoaiHopDongID = '{loai_hop_dong_id}' WHERE BangDuLieuChiTietAIID = '{row['BangDuLieuChiTietAIID']}'"
                        # print(f"Executing SQL query: {query_update}")
                        thuc_thi_truy_van(query_update)

                # Xử lý HinhThucLCNT
                if str(row['HinhThucLCNT']).strip() != "":
                    result_ht = await find_content_similarity(loaiDuLieu='hinhthucdth', duLieuCanTim=row['HinhThucLCNT'])
                    # Chuyển đổi JSONResponse thành dict trước khi serialize
                    if isinstance(result_ht, JSONResponse):
                        result_ht = result_ht.body.decode('utf-8')
                        result_ht = json.loads(result_ht)
                    if result_ht.get('status') == 'success' and result_ht['data']['success'] == 1:
                        hinh_thuc_id = result_ht['data']['results'][0]['HinhThucDThID']
                        query_update = f"UPDATE dbo.BangDuLieuChiTietAI SET HinhThucDThID = '{hinh_thuc_id}' WHERE BangDuLieuChiTietAIID = '{row['BangDuLieuChiTietAIID']}'"
                        # print(f"Executing SQL query: {query_update}")
                        thuc_thi_truy_van(query_update)
            # print("=== Danh sách KMCP đã ghép được ===")
            dataKMCP = []
            for item in kmcp_ghep_duoc:
                dataKMCP.append({
                    'BangDuLieuChiTietAIID': str(item['BangDuLieuChiTietAIID']),
                    'TenKMCP': item['TenKMCP'],
                    'TenKMCP_AI': item['TenKMCP_AI'],
                    'GhiChuAI': item['GhiChuAI']
                })

            return JSONResponse(
                status_code=200,
                content={
                    "status": "success", 
                    "code": 200,
                    "message": "Xử lý kết quả ánh xạ từ AI thành công",
                    "data": dataKMCP,
                    "not_standardized": chuoi_kmcp_khong_ghep_duoc
                }
            )
                
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "code": 500,
                    "message": "Lỗi khi xử lý kết quả ánh xạ từ AI",
                    "detail": f"Lỗi: {str(e)}\nLoại lỗi: {type(e).__name__}\nChi tiết: {e.__dict__ if hasattr(e, '__dict__') else 'Không có thông tin chi tiết'}\nDòng bị lỗi: {traceback.format_exc()}"
                }
            )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "code": 500,
                "message": "Lỗi hệ thống",
                "detail": f"Lỗi: {str(e)}\nLoại lỗi: {type(e).__name__}\nChi tiết: {e.__dict__ if hasattr(e, '__dict__') else 'Không có thông tin chi tiết'}\nDòng bị lỗi: {traceback.format_exc()}"
            }
        )

# MÔ HÌNH AZURE
@router.post("/image_extract_multi_azure")
async def image_extract_multi_azure(
    files: List[UploadFile] = File(...),
    loaiVanBan: Optional[str] = None,
    duAnID: Optional[str] = None,
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    # Xác thực token
    try:
        #Kiểm tra header Authorization
        if not authorization.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={
                    "status": "error",
                    "code": 401,
                    "message": "Token không hợp lệ",
                    "detail": "Token phải bắt đầu bằng 'Bearer '"
                }
            )
            
        #Lấy token từ header
        token = authorization.split(" ")[1]
        # Giải mã token để lấy userID và donViID
        token_data = decode_jwt_token(token)
        user_id = token_data["userID"]
        don_vi_id = token_data["donViID"]
        
        #Thêm thông tin user vào request
        request_data = {
            "userID": user_id,
            "donViID": don_vi_id
        }
        print(request_data)
    except Exception as e:
        return JSONResponse(
            status_code=401,
            content={
                "status": "error",
                "code": 401,
                "message": "Lỗi xác thực",
                "detail": str(e)
            }
        )

    temp_files = []
    all_data = []
    try:
        # Generate UUID only once and use it consistently
        van_ban_id = str(uuid.uuid4())
        bang_du_lieu_chi_tiet_id = str(uuid.uuid4())
        prompt, required_columns = prompt_service.get_prompt(loaiVanBan)
        print("======================prompt==================")
        print(prompt)
        print("======================end prompt==================")
        #return
        # Process each file
        temp_files = []
        for file in files:
            if file.content_type not in ALLOWED_IMAGE_TYPES:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "code": 400,
                        "message": f"File {file.filename} không đúng định dạng ảnh",
                        "detail": f"File {file.filename} có content_type {file.content_type} không phải là ảnh hợp lệ."
                    }
                )
            # Tạo tên file tạm thời với timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Chuyển đổi tên file sang tiếng Việt không dấu
            filename_no_accent = unidecode(file.filename)
            temp_file_path = os.path.join(IMAGE_STORAGE_PATH, f"temp_{timestamp}_{filename_no_accent}")
            temp_files.append(temp_file_path)
            print(temp_file_path)
            # Lưu file tạm thời
            with open(temp_file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

        content_parts = [{"type": "text", "text": prompt}]

        # Process each file
        for file in files:
            if file.content_type not in ALLOWED_IMAGE_TYPES:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "code": 400,
                        "message": f"File {file.filename} không đúng định dạng ảnh",
                        "detail": f"File {file.filename} có content_type {file.content_type} không phải là ảnh hợp lệ."
                    }
                )

            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
                content = await file.read()
                temp_file.write(content)
                temp_file.flush()
                temp_files.append(temp_file.name)

        # Process each file with Azure Form Recognizer
        combined_text = ""
        for temp_file in temp_files:
            try:
                # Extract data with Azure Form Recognizer
                combined_text += process_multiple_documents([temp_file])
            except Exception as e:
                print(f"Error processing file {temp_file}: {str(e)}")
                continue
        pattern = r"===\s*END_BANG_CHI_TIET===\s*?[\s\n]+?===\s*START_BANG_CHI_TIET==="
        # Thay thế bằng chuỗi rỗng để nối các bảng lại
        combined_text = re.sub(pattern, "", combined_text, flags=re.DOTALL)
        # print("&"*30)
        # print(combined_text)
        # print("&"*30)
        #return
        # Process extracted text with OpenAI
        try:
            # Prepare messages for OpenAI
            messages = [
                {
                    "role": "system",
                    "content": """Bạn là một AI kiểm duyệt dữ liệu bảng chi tiết chi phí trong văn bản hành chính đầu tư xây dựng. """
                },
                {
                    "role": "user",
                    "content": f"""
                    {prompt}
                    ===BẮT ĐẦU_VĂN_BẢN_OCR===
                    {combined_text}
                    ===BẮT ĐẦU_VĂN_BẢN_OCR===
                    """
                }
            ]
            print(messages)
            # Call OpenAI API
            client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=4096,
                temperature=0,
                response_format={"type": "json_object"}
            )

            # Process response
            response_text = response.choices[0].message.content.strip()
            
            # Clean up response text
            if response_text.strip().startswith("```json"):
                response_text = response_text.strip()[7:-3].strip()
            elif response_text.strip().startswith("```"):
                response_text = response_text.strip()[3:-3].strip()


            print("+"*20)
            print(response_text)
            print("+"*20)
            # return
            # Xử lý response
            if "error" in response_text.lower() or "không thể" in response_text.lower():
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "code": 400,
                        "message": "AI không thể nhận diện văn bản từ ảnh",
                        "detail": response_text
                    }
                )
            try:
                data_json = json.loads(response_text)
                #data_json = data_json["results"]
                #print(data_json)
            except json.JSONDecodeError as e:
                if response_text.strip().startswith("<"):
                    msg = "AI trả về HTML hoặc file không phải là ảnh văn bản."
                elif len(response_text.strip()) < 30:
                    msg = "Ảnh không chứa đủ thông tin văn bản hoặc quá mờ."
                else:
                    msg = "Kết quả trả về không đúng định dạng."
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "code": 400,
                        "message": msg,
                        "detail": str(e),
                        "raw_response": response_text
                    }
                )
            # Validate required fields in the response
            query = """select NghiepVuID=ChucNangAIID, ThongTinChung from ChucNangAI where ChucNangAIID='"""+loaiVanBan+"""' order by STT"""
            dfChucNang = lay_du_lieu_tu_sql_server(query)
            # Lấy động các cột của bảng Thông tin chung cần lưu vào bản VanBanAI
            required_fields = []
            for _, row in dfChucNang.iterrows():
                bang_du_lieu = row['ThongTinChung']
                required_fields = bang_du_lieu.split(';')

            # Kiểm tra trong json có đầy đủ các cột cần lưu hay chưa
            missing_fields = [field for field in required_fields if field not in data_json["ThongTinChung"]]
            if missing_fields:
                print("\033[31mKhông thể trích xuất đầy đủ thông tin từ ảnh\033[0m")
                print(f"Thiếu các trường: {', '.join(missing_fields)}")

            # Set UUIDs in the response data
            data_json["BangDuLieuID"] = bang_du_lieu_chi_tiet_id
            data_json["VanBanID"] = van_ban_id

            # Kiểm tra và chuyển đổi các giá trị tiền tệ trong ThongTinChung
            for col in data_json["ThongTinChung"]:
                #print("ThongTinChung: cột >>> ", col)
                if (col.startswith('GiaTri') or col.startswith('SoTien') or col.startswith('ThanhToanDenCuoiKyTruoc') or col.startswith('LuyKeDenCuoiKy')
                                or col.startswith('GiaTriNghiemThu') or col.startswith('TamUngChuaThuaHoi') or col.startswith('TamUngGiaiNganKyNayKyTruoc') or col.startswith('GiaTrungThau')
                                or col.startswith('ThanhToanThuHoiTamUng') or col.startswith('GiaiNganKyNay') or col.startswith('TamUngGiaiNganKyTruoc')
                                or col.startswith('LuyKe') or col.startswith('TamUngThanhToan') or col.startswith('ThanhToanKLHT')):
                    try:
                        data_json["ThongTinChung"][col] = convert_currency_to_int(str(data_json["ThongTinChung"][col]))
                    except Exception as e:
                        print(f"\033[31m[ERROR] Lỗi khi chuyển đổi giá trị tiền tệ cho cột {col}:\033[0m")
                        print(f"\033[31m- Chi tiết lỗi: {str(e)}\033[0m")
                        print(f"\033[31m- Giá trị gốc: {data_json['ThongTinChung'][col]}\033[0m")
            
            #print("ThongTinChung >>> ", col)
            #print(data_json["ThongTinChung"]);
            # Convert currency values in the response

            print("all_data")
            print(all_data)
            if "BangDuLieu" in data_json:
                for item in data_json["BangDuLieu"]:
                    try:
                        # print("Kiểm tra van_ban_id: ", van_ban_id)
                        item["VanBanID"] = van_ban_id
                        # Convert all numeric values based on required columns
                        for col in required_columns:
                            # print("Cột kiểm tra:", col)
                            if (col.startswith('GiaTri') or col.startswith('SoTien') or col.startswith('ThanhToanDenCuoiKyTruoc') or col.startswith('LuyKeDenCuoiKy')
                                or col.startswith('GiaTriNghiemThu') or col.startswith('TamUngChuaThuaHoi') or col.startswith('TamUngGiaiNganKyNayKyTruoc') or col.startswith('GiaTrungThau')
                                or col.startswith('ThanhToanThuHoiTamUng') or col.startswith('GiaiNganKyNay') or col.startswith('TamUngGiaiNganKyTruoc')
                                or col.startswith('LuyKe') or col.startswith('TamUngThanhToan') or col.startswith('ThanhToanKLHT')):
                                item[col] = convert_currency_to_int(str(item[col]))
                    except Exception as e:
                        print(f"\033[31m[ERROR] Lỗi khi xử lý item trong BangDuLieu:\033[0m")
                        print(f"\033[31m- Chi tiết lỗi: {str(e)}\033[0m")
                        print(f"\033[31m- Loại lỗi: {type(e).__name__}\033[0m")
                        print(f"\033[31m- Item gây lỗi: {json.dumps(item, ensure_ascii=False, indent=2)}\033[0m")
            
            # dữ liệu mặc định
            van_ban_data = {
                "VanBanAIID": van_ban_id,
                "SoVanBan": data_json["ThongTinChung"].get("SoVanBan", ""),
                "NgayKy": data_json["ThongTinChung"].get("NgayKy", ""),
                "TrichYeu": data_json["ThongTinChung"].get("TrichYeu", ""),
                "ChucDanhNguoiKy": data_json["ThongTinChung"].get("ChucDanhNguoiKy", ""),
                "CoQuanBanHanh": data_json["ThongTinChung"].get("CoQuanBanHanh", ""),
                "NguoiKy": data_json["ThongTinChung"].get("NguoiKy", ""),
                "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "TenLoaiVanBan": loaiVanBan,
                "DuAnID": duAnID,
                "DieuChinh": data_json["ThongTinChung"].get("DieuChinh", "0"),
                "JsonAI": json.dumps(data_json, ensure_ascii=False),
                "DataOCR": combined_text,
                "TenFile": "*".join([d['filename'] for d in all_data])
            }
            if  f"[{loaiVanBan}]" in "[BCDX_CT];[QDPD_CT];[QDPDDT_CBDT];[QDPD_DT_THDT];[QDPD_DA]":
                van_ban_data = {
                    "VanBanAIID": van_ban_id,
                    "SoVanBan": data_json["ThongTinChung"].get("SoVanBan", ""),
                    "SoVanBanCanCu": data_json["ThongTinChung"].get("SoVanBanCanCu", ""),
                    "NgayKy": data_json["ThongTinChung"].get("NgayKy", ""),
                    "NgayKyCanCu": data_json["ThongTinChung"].get("NgayKyCanCu", ""),
                    "TrichYeu": data_json["ThongTinChung"].get("TrichYeu", ""),
                    "TenNguonVon": data_json["ThongTinChung"].get("TenNguonVon", ""),
                    "GiaTri": data_json["ThongTinChung"].get("GiaTri", "0"),
                    "ChucDanhNguoiKy": data_json["ThongTinChung"].get("ChucDanhNguoiKy", ""),
                    "CoQuanBanHanh": data_json["ThongTinChung"].get("CoQuanBanHanh", ""),
                    "NguoiKy": data_json["ThongTinChung"].get("NguoiKy", ""),
                    "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "TenLoaiVanBan": loaiVanBan,
                    "DuAnID": duAnID,
                    "DieuChinh": data_json["ThongTinChung"].get("DieuChinh", "0"),
                    "JsonAI": json.dumps(data_json, ensure_ascii=False),
                    "DataOCR": combined_text,
                    "TenFile": "*".join([d['filename'] for d in all_data])
                }
            elif  f"[{loaiVanBan}]" in "[QDPD_KHLCNT_CBDT];[QDPD_KHLCNT_THDT]":
                van_ban_data = {
                    "VanBanAIID": van_ban_id,
                    "SoVanBan": data_json["ThongTinChung"].get("SoVanBan", ""),
                    "SoVanBanCanCu": data_json["ThongTinChung"].get("SoVanBanCanCu", ""),
                    "NgayKy": data_json["ThongTinChung"].get("NgayKy", ""),
                    "NgayKyCanCu": data_json["ThongTinChung"].get("NgayKyCanCu", ""),
                    "TrichYeu": data_json["ThongTinChung"].get("TrichYeu", ""),
                    "ChucDanhNguoiKy": data_json["ThongTinChung"].get("ChucDanhNguoiKy", ""),
                    "CoQuanBanHanh": data_json["ThongTinChung"].get("CoQuanBanHanh", ""),
                    "NguoiKy": data_json["ThongTinChung"].get("NguoiKy", ""),
                    "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "TenLoaiVanBan": loaiVanBan,
                    "DuAnID": duAnID,
                    "DieuChinh": data_json["ThongTinChung"].get("DieuChinh", "0"),
                    "JsonAI": json.dumps(data_json, ensure_ascii=False),
                    "DataOCR": combined_text,
                    "TenFile": "*".join([d['filename'] for d in all_data])
                }
            elif  f"[{loaiVanBan}]" in "[QDPD_KQLCNT_CBDT];[QDPD_KQLCNT_THDT]":
                van_ban_data = {
                    "VanBanAIID": van_ban_id,
                    "SoVanBan": data_json["ThongTinChung"].get("SoVanBan", ""),
                    "SoVanBanCanCu": data_json["ThongTinChung"].get("SoVanBanCanCu", ""),
                    "NgayKy": data_json["ThongTinChung"].get("NgayKy", ""),
                    "NgayKyCanCu": data_json["ThongTinChung"].get("NgayKyCanCu", ""),
                    "TrichYeu": data_json["ThongTinChung"].get("TrichYeu", ""),
                    "ChucDanhNguoiKy": data_json["ThongTinChung"].get("ChucDanhNguoiKy", ""),
                    "CoQuanBanHanh": data_json["ThongTinChung"].get("CoQuanBanHanh", ""),
                    "TenNhaThau": data_json["ThongTinChung"].get("TenNhaThau", ""),
                    "GiaTri": data_json["ThongTinChung"].get("GiaTri", "0"),
                    "NguoiKy": data_json["ThongTinChung"].get("NguoiKy", ""),
                    "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "TenLoaiVanBan": loaiVanBan,
                    "DuAnID": duAnID,
                    "DieuChinh": data_json["ThongTinChung"].get("DieuChinh", "0"),
                    "JsonAI": json.dumps(data_json, ensure_ascii=False),
                    "DataOCR": combined_text,
                    "TenFile": "*".join([d['filename'] for d in all_data])
                }
            elif  f"[{loaiVanBan}]" in "[HOP_DONG]":
                van_ban_data = {
                    "VanBanAIID": van_ban_id,
                    "SoVanBan": data_json["ThongTinChung"].get("SoVanBan", ""),
                    "NgayKy": data_json["ThongTinChung"].get("NgayKy", ""),
                    "NgayHieuLuc": data_json["ThongTinChung"].get("NgayHieuLuc", ""),
                    "NgayKetThuc": data_json["ThongTinChung"].get("NgayKetThuc", ""),
                    "NguoiKy": data_json["ThongTinChung"].get("NguoiKy", ""),
                    "SoVanBanCanCu": data_json["ThongTinChung"].get("SoVanBanCanCu", ""),
                    "NgayKyCanCu": data_json["ThongTinChung"].get("NgayKyCanCu", ""),
                    "ChucDanhNguoiKy": data_json["ThongTinChung"].get("ChucDanhNguoiKy", ""),
                    "NguoiKy_NhaThau": data_json["ThongTinChung"].get("NguoiKy_NhaThau", ""),
                    "ChucDanhNguoiKy_NhaThau": data_json["ThongTinChung"].get("ChucDanhNguoiKy_NhaThau", ""),
                    "TenNhaThau": data_json["ThongTinChung"].get("TenNhaThau", ""),
                    "TrichYeu": data_json["ThongTinChung"].get("TrichYeu", ""),
                    "CoQuanBanHanh": data_json["ThongTinChung"].get("CoQuanBanHanh", ""),
                    "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "TenLoaiVanBan": loaiVanBan,
                    "GiaiDoanID": "",
                    "DuAnID": duAnID,
                    "DieuChinh": "0",
                    "JsonAI": json.dumps(data_json, ensure_ascii=False),
                    "DataOCR": combined_text,
                    "TenFile": "*".join([d['filename'] for d in all_data]),
                    "UserID": user_id,
                    "DonViID": don_vi_id
                }
            elif  f"[{loaiVanBan}]" in "[PL_HOP_DONG]":
                van_ban_data = {
                    "VanBanAIID": van_ban_id,
                    "SoVanBan": data_json["ThongTinChung"].get("SoVanBan", ""), # Tương đương Số phụ lục hợp đồng
                    "SoPLHopDong": data_json["ThongTinChung"].get("SoPLHopDong", ""),
                    "NgayKy": data_json["ThongTinChung"].get("NgayKy", ""),
                    "NgayHieuLuc": data_json["ThongTinChung"].get("NgayHieuLuc", ""),
                    "NgayKetThuc": data_json["ThongTinChung"].get("NgayKetThuc", ""),
                    "NguoiKy": data_json["ThongTinChung"].get("NguoiKy", ""),
                    "SoVanBanCanCu": data_json["ThongTinChung"].get("SoVanBanCanCu", ""), # Tương đương Số hợp đồng (gốc)
                    "NgayKyCanCu": data_json["ThongTinChung"].get("NgayKyCanCu", ""),
                    "ChucDanhNguoiKy": data_json["ThongTinChung"].get("ChucDanhNguoiKy", ""),
                    "NguoiKy_NhaThau": data_json["ThongTinChung"].get("NguoiKy_NhaThau", ""),
                    "ChucDanhNguoiKy_NhaThau": data_json["ThongTinChung"].get("ChucDanhNguoiKy_NhaThau", ""),
                    "TenNhaThau": data_json["ThongTinChung"].get("TenNhaThau", ""),
                    "TrichYeu": data_json["ThongTinChung"].get("TrichYeu", ""),
                    "CoQuanBanHanh": data_json["ThongTinChung"].get("CoQuanBanHanh", ""),
                    "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "TenLoaiVanBan": loaiVanBan,
                    "GiaiDoanID": "",
                    "DuAnID": duAnID,
                    "DieuChinh": "0",
                    "JsonAI": json.dumps(data_json, ensure_ascii=False),
                    "DataOCR": combined_text,
                    "TenFile": "*".join([d['filename'] for d in all_data]),
                    "UserID": user_id,
                    "DonViID": don_vi_id
                }
            elif  f"[{loaiVanBan}]" in "[KLCVHT_THD]":
                van_ban_data = {
                    "VanBanAIID": van_ban_id,
                    "SoVanBan": data_json["ThongTinChung"].get("SoVanBan", ""),
                    "NgayKy": data_json["ThongTinChung"].get("NgayKy", ""),
                    "NguoiKy": data_json["ThongTinChung"].get("NguoiKy", ""),
                    "SoVanBanCanCu": data_json["ThongTinChung"].get("SoVanBanCanCu", ""),
                    "SoHopDong": data_json["ThongTinChung"].get("SoHopDong", ""),
                    "SoPLHopDong": data_json["ThongTinChung"].get("SoPLHopDong", ""),
                    "LanThanhToan": data_json["ThongTinChung"].get("LanThanhToan", ""),
                    "TenNhaThau": data_json["ThongTinChung"].get("TenNhaThau", ""),
                    "NgayKyCanCu": data_json["ThongTinChung"].get("NgayKyCanCu", ""),
                    "ChucDanhNguoiKy": data_json["ThongTinChung"].get("ChucDanhNguoiKy", ""),
                    "NguoiKy_NhaThau": data_json["ThongTinChung"].get("NguoiKy_NhaThau", ""),
                    "ChucDanhNguoiKy_NhaThau": data_json["ThongTinChung"].get("ChucDanhNguoiKy_NhaThau", ""),
                    "TrichYeu": data_json["ThongTinChung"].get("TrichYeu", ""),
                    "GiaTriHopDong": data_json["ThongTinChung"].get("GiaTriHopDong", "0"),
                    "TamUngChuaThuaHoi": data_json["ThongTinChung"].get("TamUngChuaThuaHoi", "0"),
                    "ThanhToanDenCuoiKyTruoc": data_json["ThongTinChung"].get("ThanhToanDenCuoiKyTruoc", "0"),
                    "LuyKeDenCuoiKy": data_json["ThongTinChung"].get("LuyKeDenCuoiKy", "0"),
                    "ThanhToanThuHoiTamUng": data_json["ThongTinChung"].get("ThanhToanThuHoiTamUng", "0"),
                    "GiaiNganKyNay": data_json["ThongTinChung"].get("GiaiNganKyNay", "0"),
                    "TamUngGiaiNganKyNayKyTruoc": data_json["ThongTinChung"].get("TamUngGiaiNganKyNayKyTruoc", "0"),
                    "ThanhToanKLHTKyTruoc": data_json["ThongTinChung"].get("ThanhToanKLHTKyTruoc", "0"),
                    "LuyKeGiaiNgan": data_json["ThongTinChung"].get("LuyKeGiaiNgan", "0"),
                    "TamUngThanhToan": data_json["ThongTinChung"].get("TamUngThanhToan", "0"),
                    "ThanhToanKLHT": data_json["ThongTinChung"].get("ThanhToanKLHT", "0"),
                    "CoQuanBanHanh": data_json["ThongTinChung"].get("CoQuanBanHanh", ""),
                    "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "TenLoaiVanBan": loaiVanBan,
                    "GiaiDoanID": "",
                    "DuAnID": duAnID,
                    "DieuChinh": "0",
                    "JsonAI": json.dumps(data_json, ensure_ascii=False),
                    "DataOCR": combined_text,
                    "TenFile": "*".join([d['filename'] for d in all_data]),
                    "UserID": user_id,
                    "DonViID": don_vi_id
                }
            elif  f"[{loaiVanBan}]" in "[GIAI_NGAN_DNTT];[GIAI_NGAN_GRV];[GIAI_NGAN_THV]":
                print("van_ban_data>>>>>>>>>>>>>>>>>>>>")
            
                van_ban_data = {
                    "VanBanAIID": van_ban_id,
                    "SoVanBan": data_json["ThongTinChung"].get("SoVanBan", ""),
                    "NgayKy": data_json["ThongTinChung"].get("NgayKy", ""),
                    "SoHopDong": data_json["ThongTinChung"].get("SoHopDong", ""),
                    "SoPLHopDong": data_json["ThongTinChung"].get("SoPLHopDong", ""),
                    "SoVanBanCanCu": data_json["ThongTinChung"].get("SoVanBanCanCu", ""),
                    "NgayKyCanCu": data_json["ThongTinChung"].get("NgayKyCanCu", ""),
                    "TenNguonVon": data_json["ThongTinChung"].get("TenNguonVon", ""),
                    "NienDo": data_json["ThongTinChung"].get("NienDo", ""),
                    "LoaiKHVonID": data_json["ThongTinChung"].get("NienDo", "2"), # mặc định là 2 (năm nay)
                    "SoTien": data_json["ThongTinChung"].get("NienDo", "0"),
                    "NguoiKy": data_json["ThongTinChung"].get("NguoiKy", ""),
                    "ChucDanhNguoiKy": data_json["ThongTinChung"].get("ChucDanhNguoiKy", ""),
                    "CoQuanBanHanh": data_json["ThongTinChung"].get("CoQuanBanHanh", ""),
                    "TrichYeu": data_json["ThongTinChung"].get("TrichYeu", ""),
                    "NghiepVuID": data_json["ThongTinChung"].get("NghiepVuID", ""),
                    "TenNhaThau": data_json["ThongTinChung"].get("TenNhaThau", ""),
                    "GiaTri": data_json["ThongTinChung"].get("GiaTri", "0"),
                    "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "TenLoaiVanBan": loaiVanBan,
                    "DuAnID": duAnID,
                    "DieuChinh": data_json["ThongTinChung"].get("DieuChinh", "0"),
                    "JsonAI": json.dumps(data_json, ensure_ascii=False),
                    "DataOCR": combined_text,
                    "TenFile": "*".join([d['filename'] for d in all_data])
                }
            van_ban_data["UserID"] = user_id
            van_ban_data["DonViID"] = don_vi_id

            

            db_service = DatabaseService()
            result = await db_service.insert_van_ban_ai(db, van_ban_data, loaiVanBan)
            
            if not result.get("success", False):
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "code": 500,
                        "message": "Lỗi khi lưu dữ liệu vào database",
                        "detail": result.get("error", "Unknown error")
                    }
                )

            # Insert BangDuLieu data if it exists
            if "BangDuLieu" in data_json and data_json["BangDuLieu"] and len(data_json["BangDuLieu"]) > 0:
                bang_du_lieu_data = []
                for item in data_json["BangDuLieu"]:
                    bang_du_lieu_data.append({
                        "VanBanAIID": van_ban_id,
                        **{col: item.get(col, 0) for col in required_columns}
                    })
                bang_du_lieu_result = await db_service.insert_bang_du_lieu_chi_tiet_ai(
                    db, 
                    bang_du_lieu_data,
                    required_columns
                )
                if not bang_du_lieu_result.get("success", False):
                    return JSONResponse(
                        status_code=500,
                        content={
                            "status": "error",
                            "code": 500,
                            "message": "Lỗi khi lưu chi tiết bảng dữ liệu",
                            "detail": bang_du_lieu_result.get("error", "Unknown error")
                        }
                    )
            else:
                print("Văn bản này không có chi tiết bảng dữ liệu")
            # After successful processing and database operations
            try:
                # Get QLDA upload URL from environment
                qlda_upload_url = os.getenv("API_URL_UPLOAD_QLDA")
                if not qlda_upload_url:
                    raise ValueError("Không tìm thấy API_URL_UPLOAD_QLDA trong file .env")

                # Prepare files for upload to QLDA
                files_data = []
                for file in files:
                    # Reset file pointer to beginning
                    await file.seek(0)
                    files_data.append(
                        ("files", (file.filename, file.file, file.content_type))
                    )

                # Upload files to QLDA system
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{qlda_upload_url}/api/v1/Uploads/uploadMultipleFiles",
                        files=files_data,
                        headers={"Authorization": authorization}
                    )
                    
                    if response.status_code != 200:
                        return JSONResponse(
                            status_code=500,
                            content={
                                "status": "error",
                                "code": 500,
                                "message": "Lỗi khi upload file lên hệ thống QLDA",
                                "detail": response.text
                            }
                        )
                    
                    # Lấy response JSON từ API QLDA
                    qlda_response = response.json()
                    
                    try:
                        # Nối các đường dẫn file trong data thành 1 chuỗi, phân cách bằng dấu *
                        string_url_qlda_response = '*'.join(qlda_response['data'])
                        # Thực thi câu lệnh SQL để cập nhật tên file trong bảng VanBanAI
                        update_query = text(f"""
                            UPDATE dbo.VanBanAI 
                            SET tenFile = N'{string_url_qlda_response}'
                            WHERE VanBanAIID = N'{van_ban_id}'
                        """)
                        db.execute(update_query)
                        db.commit()
                    except Exception as e:
                        db.rollback()
                        raise Exception(f"Lỗi khi cập nhật tên file trong bảng VanBanAI: {str(e)}")

                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "success",
                        "code": 200,
                        "message": "Upload và xử lý nhiều file ảnh thành công",
                        "data": {
                            "files_processed": [{"filename": d['filename']} for d in all_data],
                            "van_ban": data_json,
                            "db_status": result.get("success", False),
                            "db_message": result.get("message", ""),
                            "qlda_upload_status": "success",
                            "qlda_response": qlda_response
                        }
                    }
                )

            except Exception as e:
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "code": 500,
                        "message": "Lỗi khi upload file lên hệ thống QLDA",
                        "detail": str(e)
                    }
                )

        except Exception as e:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "code": 400,
                    "message": "Lỗi khi xử lý ảnh",
                    "detail": f"Chi tiết lỗi: {str(e)}\nLoại lỗi: {type(e).__name__}\nTraceback: {traceback.format_exc()}"
                }
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "code": 500,
                "message": "Lỗi hệ thống",
                "detail": str(e)
            }
        )
    finally:
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)

@router.get("/find_content_similarity")
async def find_content_similarity(
    loaiDuLieu: Optional[str] = None, # KMCP; NguonVon; HinhThucDTh; LoaiHopDong
    duLieuCanTim: Optional[str] = None
):
    # print("loaiDuLieu:", loaiDuLieu)
    # print("duLieuCanTim:", duLieuCanTim)
    if loaiDuLieu.lower() == "kmcp":
        try:
            # Truy vấn lấy danh sách KMCP
            query = """
            select KMCPID=convert(nvarchar(36), KMCPID), TenKMCP 
            from dbo.KMCP 
            order by TenKMCP
            """

            # Thực thi truy vấn
            data_gui = lay_du_lieu_tu_sql_server(query)
            
            try:
                ket_qua_tim = tim_kiem_tuong_dong(duLieuCanTim, data_gui, 0.70)
                # print(ket_qua_tim)
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "success", 
                        "code": 200,
                        "message": "Tìm kiếm thành công",
                        "data": ket_qua_tim
                    }
                )
            except Exception as e:
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "code": 500,
                        "message": "Lỗi khi tìm kiếm",
                        "detail": f"Lỗi chi tiết: {str(e)}\nTraceback: {traceback.format_exc()}"
                    }
                )
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "code": 500,
                    "message": "Lỗi khi tìm kiếm",
                    "detail": str(e)
                }
            )
    if loaiDuLieu.lower() == "nguonvon":
        try:
            # Truy vấn lấy danh sách KMCP
            query = """
            select NguonVonID, TenNguonVon 
            from dbo.NguonVon 
            order by TenNguonVon
            """
            
            # Thực thi truy vấn
            nguonvon_data = lay_du_lieu_tu_sql_server(query)
            
            try:
                ket_qua_tim = tim_kiem_tuong_dong(duLieuCanTim, nguonvon_data, 0.80)
                # print(ket_qua_tim)
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "success", 
                        "code": 200,
                        "message": "Tìm kiếm thành công",
                        "data": ket_qua_tim
                    }
                )
            except Exception as e:
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "code": 500,
                        "message": "Lỗi khi tìm kiếm",
                        "detail": f"Lỗi chi tiết: {str(e)}\nTraceback: {traceback.format_exc()}"
                    }
                )
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "code": 500,
                    "message": "Lỗi khi tìm kiếm",
                    "detail": str(e)
                }
            )
        
    if loaiDuLieu.lower() == "phuongthucdth":
        try:
            # Truy vấn lấy danh sách KMCP
            query = """
            select PhuongThucDThID=convert(nvarchar(36), PhuongThucDThID), TenPhuongThucDTh from PhuongThucDTh
            order by MaPhuongThucDTh
            """
            # Thực thi truy vấn
            data_gui = lay_du_lieu_tu_sql_server(query)
            # VIET_TAT = {
            #     "xskt": "Xổ số kiến thiết",
            # }
            try:
                ket_qua_tim = tim_kiem_tuong_dong(duLieuCanTim, data_gui, 0.70)
                # print(ket_qua_tim)
                print("KẾT QUẢ TÌM KIẾM:  ", duLieuCanTim)
                print(ket_qua_tim)
                print("END KẾT QUẢ TÌM KIẾM")
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "success", 
                        "code": 200,
                        "message": "Tìm kiếm thành công",
                        "data": ket_qua_tim
                    }
                )
            except Exception as e:
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "code": 500,
                        "message": "Lỗi khi tìm kiếm",
                        "detail": f"Lỗi chi tiết: {str(e)}\nTraceback: {traceback.format_exc()}"
                    }
                )
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "code": 500,
                    "message": "Lỗi khi tìm kiếm",
                    "detail": str(e)
                }
            )
    if loaiDuLieu.lower() == "loaigoithau":
        try:
            # Truy vấn lấy danh sách KMCP
            query = """
            select LoaiGoiThauID=convert(nvarchar(36), LoaiGoiThauID), TenLoaiGoiThau from LoaiGoiThau
            order by MaLoaiGoiThau
            """
            
            # Thực thi truy vấn
            data_gui = lay_du_lieu_tu_sql_server(query)
            try:
                ket_qua_tim = tim_kiem_tuong_dong(duLieuCanTim, data_gui, 0.70)
                # print(ket_qua_tim)
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "success", 
                        "code": 200,
                        "message": "Tìm kiếm thành công",
                        "data": ket_qua_tim
                    }
                )
            except Exception as e:
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "code": 500,
                        "message": "Lỗi khi tìm kiếm",
                        "detail": f"Lỗi chi tiết: {str(e)}\nTraceback: {traceback.format_exc()}"
                    }
                )
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "code": 500,
                    "message": "Lỗi khi tìm kiếm",
                    "detail": str(e)
                }
            )
    if loaiDuLieu.lower() == "hinhthucdth":
        try:
            # Truy vấn lấy danh sách KMCP
            query = """
            select HinhThucDThID=convert(nvarchar(36), HinhThucDThID), TenHinhThucDTh from HinhThucDTh
            order by TenHinhThucDTh
            """
            
            # Thực thi truy vấn
            data_gui = lay_du_lieu_tu_sql_server(query)
            
            
            try:
                ket_qua_tim = tim_kiem_tuong_dong(duLieuCanTim, data_gui, 0.70)
                # print(ket_qua_tim)
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "success", 
                        "code": 200,
                        "message": "Tìm kiếm thành công",
                        "data": ket_qua_tim
                    }
                )
            except Exception as e:
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "code": 500,
                        "message": "Lỗi khi tìm kiếm",
                        "detail": f"Lỗi chi tiết: {str(e)}\nTraceback: {traceback.format_exc()}"
                    }
                )
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "code": 500,
                    "message": "Lỗi khi tìm kiếm",
                    "detail": str(e)
                }
            )
    if loaiDuLieu.lower() == "loaihopdong":
        try:
            # Truy vấn lấy danh sách KMCP
            query = """
            select LoaiHopDongID=convert(nvarchar(36), LoaiHopDongID), TenLoaiHopDong from LoaiHopDong order by TenLoaiHopDong
            """
            
            # Thực thi truy vấn
            data_gui = lay_du_lieu_tu_sql_server(query)
            
            # VIET_TAT = {
            #     "xskt": "Xổ số kiến thiết",
            # }
            try:
                ket_qua_tim = tim_kiem_tuong_dong(duLieuCanTim, data_gui, 0.70)
                # print(ket_qua_tim)
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "success", 
                        "code": 200,
                        "message": "Tìm kiếm thành công",
                        "data": ket_qua_tim
                    }
                )
            except Exception as e:
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "code": 500,
                        "message": "Lỗi khi tìm kiếm",
                        "detail": f"Lỗi chi tiết: {str(e)}\nTraceback: {traceback.format_exc()}"
                    }
                )
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "code": 500,
                    "message": "Lỗi khi tìm kiếm",
                    "detail": str(e)
                }
            )