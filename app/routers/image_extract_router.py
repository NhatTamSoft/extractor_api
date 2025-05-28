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
@router.post("/document_extract")
async def document_extract(
    files: List[UploadFile] = File(...),
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

    # 2. Kiểm tra xem có file nào được tải lên không
    if not files:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "code": 400, "message": "Chưa có file nào được tải lên."}
        )

    # 3. Xử lý file Excel đầu tiên được tải lên
    file = files[0]
    if not file.filename.endswith('.xlsx'):
        return JSONResponse(
            status_code=400,
            content={"status": "error", "code": 400, "message": "Định dạng file không hợp lệ.", "detail": "Yêu cầu file có định dạng .xlsx"}
        )

    # 4. Đọc file Excel và tạo các DataFrame
    try:
        # Kiểm tra xem đã cài đặt openpyxl chưa

        # Đọc toàn bộ sheet 'Data' mà không dùng hàng đầu tiên làm header để dễ dàng truy cập bằng chỉ số
        df_raw = pd.read_excel(file.file, sheet_name='Data', header=None, engine='openpyxl')

        # --- Tạo DataFrame Thông tin dự án ---
        # Trích xuất dữ liệu từ các ô cụ thể dựa trên hình ảnh
        # MaDuAn từ ô B2 (hàng 1, cột 1), TenDuAn từ B3 (hàng 2, cột 1), Path từ B4 (hàng 3, cột 1)
        project_info_data = {
            'MaDuAn': [str(df_raw.iloc[1, 1]) if pd.notna(df_raw.iloc[1, 1]) else ""],
            'TenDuAn': [str(df_raw.iloc[2, 1]) if pd.notna(df_raw.iloc[2, 1]) else ""],
            'Path': [str(df_raw.iloc[3, 1]) if pd.notna(df_raw.iloc[3, 1]) else ""]
        }
        df_thong_tin_du_an = pd.DataFrame(project_info_data)
        # Lấy MaDuAn từ project_info_data
        ma_du_an = project_info_data['MaDuAn'][0]
        
        # Truy vấn SQL để lấy DuAnID
        query = text(f"""
            SELECT DuAnID 
            FROM dbo.DuAn 
            WHERE (DonViID = '{don_vi_id}' OR DonViID_chudautu = '{don_vi_id}')
            AND MaDuAn = N'{ma_du_an}'
        """)
        
        result = db.execute(query).fetchone()
        duAnID = result[0] if result else None
        if not duAnID:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "code": 400,
                    "message": "Không tìm thấy dự án với mã " + ma_du_an + " dự án đã cung cấp.",
                    "detail": f"MaDuAn: {ma_du_an}"
                }
            )
        # --- Tạo DataFrame Danh sách đường dẫn ---
        # Đọc lại file excel, bỏ qua 4 hàng đầu để lấy header từ hàng thứ 5
        df_danh_sach_duong_dan = pd.read_excel(file.file, sheet_name='Data', skiprows=4, engine='openpyxl')
        # Chuyển đổi giá trị NaN trong cột RangePage thành chuỗi rỗng
        df_danh_sach_duong_dan['RangePage'] = df_danh_sach_duong_dan['RangePage'].fillna('')

        print("===df_danh_sach_duong_dan===")
        print(df_danh_sach_duong_dan)

        # Loại bỏ các hàng trống (nếu có) dựa trên cột 'STT'
        df_danh_sach_duong_dan.dropna(subset=['STT'], inplace=True)
        
        # Chuyển đổi kiểu dữ liệu của cột STT sang số nguyên và xử lý các giá trị không hợp lệ
        df_danh_sach_duong_dan['STT'] = pd.to_numeric(df_danh_sach_duong_dan['STT'], errors='coerce').fillna(0).astype(int)

        # Khởi tạo danh sách đường dẫn
        list_duong_dan = []
        list_duong_dan_khong_ton_tai = []

        # Duyệt từng dòng trong DataFrame
        for index, row in df_danh_sach_duong_dan.iterrows():
            path = row['Path']
            rangePage = row['RangePage']
            
            # Kiểm tra nếu path là thư mục
            if os.path.isdir(path):
                # Tìm tất cả file PDF trong thư mục và thư mục con
                for root, dirs, files in os.walk(path):
                    for file in files:
                        if file.lower().endswith('.pdf'):
                            full_path = os.path.join(root, file)
                            list_duong_dan.append({'path': full_path, 'rangePage': rangePage})
            
            # Kiểm tra nếu path là file PDF
            elif path.lower().endswith('.pdf'):
                if os.path.exists(path):
                    list_duong_dan.append({'path': path, 'rangePage': rangePage})
                else:
                    list_duong_dan_khong_ton_tai.append(path)
        
        # Bổ sung cột imgBase64 cho list_duong_dan
        # DUYỆT QUA TỪNG ĐƯỜNG DẪN (TỪNG FILE PDF)
        for item in list_duong_dan:
            all_data = []
            loaiVanBan = None
            path = item['path'].lower()
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
            elif 'hop_dong\\' in path:
                loaiVanBan = 'HOP_DONG'
            elif 'phu_luc_hop_dong\\' in path:
                loaiVanBan = 'PL_HOP_DONG'
            elif 'xac_nhan_klcv_hoan_thanh\\' in path:
                loaiVanBan = 'KLCVHT_THD'
            elif 'de_nghi_thanh_toan\\' in path:
                loaiVanBan = 'GIAI_NGAN_DNTT'
            elif 'giay_rut_von\\' in path:
                loaiVanBan = 'GIAI_NGAN_GRV'
            elif 'giay_de_nghi_thu_hoi_von\\' in path:
                loaiVanBan = 'GIAI_NGAN_THV'
            elif 'nghiem_thu_ban_giao\\' in path:
                loaiVanBan = 'QDPDDT_CBDT'
            elif 'bc_quyet_toan_daht\\' in path:
                loaiVanBan = 'BC_QTDAHT'
            elif 'vb_khac\\' in path:
                loaiVanBan = 'VanBanKhac'
            prompt, required_columns = prompt_service.get_prompt(loaiVanBan)
            van_ban_id = str(uuid.uuid4())
            bang_du_lieu_chi_tiet_id = str(uuid.uuid4())
            # print(prompt)
            content_parts = [{"type": "text", "text": prompt}]
            valid_image_paths = []
            # Đọc file PDF và chuyển thành ảnh
            image_PIL = pdf_to_images(item['path'], item['rangePage'])
            try:
                # Process each file with Azure Form Recognizer
                combined_text = ""
                for temp_file in image_PIL:
                    try:
                        # Chuyển đổi PIL Image thành bytes
                        img_byte_arr = BytesIO()
                        temp_file.save(img_byte_arr, format='PNG')
                        img_byte_arr = img_byte_arr.getvalue()

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
                        print(f"Error processing file {temp_file}: {str(e)}")
                # print("&"*30)
                # print(combined_text)
                # print("&"*30)
            except Exception as e:
                print(f"Lỗi khi xử lý file: {str(e)}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "code": 500,
                        "message": "Lỗi khi xử lý file",
                        "detail": f"Lỗi: {str(e)}\nLoại lỗi: {type(e).__name__}\nChi tiết: {e.__dict__ if hasattr(e, '__dict__') else 'Không có thông tin chi tiết'}"
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
                                or col.startswith('GiaTriNghiemThu') or col.startswith('TamUngChuaThuaHoi') or col.startswith('TamUngGiaiNganKyNayKyTruoc')
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
                        print("Kiểm tra van_ban_id: ", van_ban_id)
                        item["VanBanID"] = van_ban_id
                        # Convert all numeric values based on required columns
                        for col in required_columns:
                            print("Cột kiểm tra:", col)
                            if (col.startswith('GiaTri') or col.startswith('SoTien') or col.startswith('ThanhToanDenCuoiKyTruoc') or col.startswith('LuyKeDenCuoiKy')
                                or col.startswith('GiaTriNghiemThu') or col.startswith('TamUngChuaThuaHoi') or col.startswith('TamUngGiaiNganKyNayKyTruoc')
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
                # Chuyển đổi đường dẫn file thành đối tượng File
                file_path = path
                file_name = os.path.basename(file_path)
                
                # Đọc nội dung file
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                
                # Tạo đối tượng UploadFile
                temp_file = SpooledTemporaryFile()
                temp_file.write(file_content)
                temp_file.seek(0)
                
                file_obj = UploadFile(
                    filename=file_name,
                    file=temp_file,
                    headers={"content-type": "application/pdf"}
                )
                
                # Thêm vào danh sách files_data
                files_data.append(
                    ("files", (file_name, file_obj.file, "application/pdf"))
                )
                print(">>>>>>>>>>>> files_data chi tiết:")
                for file_data in files_data:
                    print(f"- Tên file: {file_data[1][0]}")
                    print(f"- Loại file: {file_data[1][2]}")
                    print("-" * 50)
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
                # CHỔ NÀY XỬ LÝ BỎ VÀO BIÊN GHI NHẬT KÝ CÁC FILE ĐÃ ĐÍNH KÈM
                # return JSONResponse(
                #     status_code=200,
                #     content={
                #         "status": "success",
                #         "code": 200,
                #         "message": "Upload và xử lý nhiều file ảnh thành công",
                #         "data": {
                #             "files_processed": [{"filename": d['filename']} for d in all_data],
                #             "van_ban": data_json,
                #             "db_status": result.get("success", False),
                #             "db_message": result.get("message", ""),
                #             "qlda_upload_status": "success",
                #             "qlda_response": qlda_response
                #         }
                #     }
                # )

            except Exception as e:
                # CHỔ NÀY XỬ LÝ FILE DỰ ÁN CHƯA ĐÍNH KÈM ĐƯỢC
                nhat_ky_loi_upload_file = "Lỗi khi upload file lên hệ thống QLDA"
                print(f"\033[31m[ERROR] Chi tiết lỗi khi upload file:\033[0m")
                print(f"\033[31m- Loại lỗi: {type(e).__name__}\033[0m")
                print(f"\033[31m- Chi tiết lỗi: {str(e)}\033[0m")
                print(f"\033[31m- Thông tin chi tiết: {e.__dict__ if hasattr(e, '__dict__') else 'Không có thông tin chi tiết'}\033[0m")
                print(f"\033[31m- Dòng lỗi: {e.__traceback__.tb_lineno if hasattr(e, '__traceback__') else 'Không có thông tin dòng lỗi'}\033[0m")
                print(f"\033[31m- File lỗi: {e.__traceback__.tb_frame.f_code.co_filename if hasattr(e, '__traceback__') else 'Không có thông tin file lỗi'}\033[0m")
                # return JSONResponse(
                #     status_code=500,
                #     content={
                #         "status": "error",
                #         "code": 500,
                #         "message": "Lỗi khi upload file lên hệ thống QLDA",
                #         "detail": str(e)
                #     }
                # )

        print("===Danh sách đường dẫn file PDF===")
        print(list_duong_dan)
        print("===Danh sách đường dẫn file PDF không tồn tại===")
        print(list_duong_dan_khong_ton_tai)
        
        # Trả về kết quả là 2 DataFrame dưới dạng JSON
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Trích xuất dữ liệu từ file Excel thành công.",
                "data": {
                    "thong_tin_du_an": df_thong_tin_du_an.to_dict(orient='records'),
                    "danh_sach_duong_dan": df_danh_sach_duong_dan.to_dict(orient='records')
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
                "detail": f"Lỗi: {str(e)}\nLoại lỗi: {type(e).__name__}\nChi tiết: {e.__dict__ if hasattr(e, '__dict__') else 'Không có thông tin chi tiết'}"
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
                                or col.startswith('GiaTriNghiemThu') or col.startswith('TamUngChuaThuaHoi') or col.startswith('TamUngGiaiNganKyNayKyTruoc')
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
                        print("Kiểm tra van_ban_id: ", van_ban_id)
                        item["VanBanID"] = van_ban_id
                        # Convert all numeric values based on required columns
                        for col in required_columns:
                            #print("Cột kiểm tra:", col)
                            if (col.startswith('GiaTri') or col.startswith('SoTien') or col.startswith('ThanhToanDenCuoiKyTruoc') or col.startswith('LuyKeDenCuoiKy')
                                or col.startswith('GiaTriNghiemThu') or col.startswith('TamUngChuaThuaHoi') or col.startswith('TamUngGiaiNganKyNayKyTruoc') 
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
        # print("="*20)
        # print(chuoi_markdown_tenkmcp)
        # print("="*20)


            promt_anh_xa_noi_dung_tuong_dong = """
Bạn là chuyên gia trong lĩnh vực Đầu tư xây dựng cơ bản.

Tôi cung cấp 2 bảng dữ liệu:

#### Bảng 1 – Danh sách khoản mục chi phí cần ánh xạ (`KMCP_AnhXa`)
- Gồm cột: `TenKMCP` (tên khoản mục thực tế từ hồ sơ dự toán hoặc quyết toán)

"""+chuoi_markdown_tenkmcp+"""

#### Bảng 2 – Danh mục chuẩn chi phí (`KMCP`)
- Gồm các cột:
  - `MaKMCP`: mã khoản mục chuẩn
  - `TenKMCP`: tên khoản mục chi phí chuẩn

| MaKMCP  | TenKMCP                                                                                                                     |
| ------- | --------------------------------------------------------------------------------------------------------------------------- |
| CP01    | Chi phí bồi thường, hỗ trợ, tái định cư                                                                                     |
| CP101   | Chi phí bồi thường về đất, nhà, công trình trên đất, các tài sản gắn liền với đất, trên mặt nước và chi phí bồi thường khác |
| CP102   | Chi phí các khoản hỗ trợ khi nhà nước thu hồi đất                                                                           |
| CP103   | Chi phí tái định cư                                                                                                         |
| CP104   | Chi phí tổ chức bồi thường, hỗ trợ và tái định cư                                                                           |
| CP105   | Chi phí sử dụng đất, thuê đất tính trong thời gian xây dựng                                                                 |
| CP106   | Chi phí di dời, hoàn trả cho phần hạ tầng kỹ thuật đã được đầu tư xây dựng phục vụ giải phóng mặt bằng                      |
| CP107   | Chi phí đầu tư vào đất                                                                                                      |
| CP199   | Chi phí khác có liên quan đến công tác bồi thường, hỗ trợ và tái định cư                                                    |
| CP2     | Chi phí xây dựng                                                                                                            |
| CP221   | Chi phí xây dựng phát sinh                                                                                                  |
| CP222   | Chi phí xây dựng trước thuế                                                                                                 |
| CP223   | Chi phí xây dựng sau thuế                                                                                                   |
| CP224   | Chi phí xây dựng công trình phụ                                                                                             |
| CP225   | Chi phí xây dựng công trình chính                                                                                           |
| CP226   | Chi phí xây dựng điều chỉnh                                                                                                 |
| CP227   | Chi phí xây dựng công trình chính và phụ                                                                                    |
| CP228   | Chi phí xây dựng khác                                                                                                       |
| CP3     | Chi phí thiết bị                                                                                                            |
| CP321   | Chi phí thiết bị phát sinh                                                                                                  |
| CP4     | Chi phí quản lý dự án                                                                                                       |
| CP421   | Chi phí quản lý dự án phát sinh                                                                                             |
| CP5     | Chi phí tư vấn đầu tư xây dựng                                                                                              |
| CP501   | Chi phí lập báo cáo nghiên cứu tiền khả thi                                                                                 |
| CP502   | Chi phí lập báo cáo nghiên cứu khả thi                                                                                      |
| CP503   | Chi phí lập báo cáo kinh tế - kỹ thuật                                                                                      |
| CP50301 | Chi phí lập dự án đầu tư                                                                                                    |
| CP504   | Chi phí thiết kế xây dựng                                                                                                   |
| CP50411 | Chi phí thiết kế xây dựng (Phát sinh)                                                                                       |
| CP50420 | Chi phí thiết kế kỹ thuật                                                                                                   |
| CP50431 | Chi phí thiết kế kỹ thuật (Phát sinh)                                                                                       |
| CP505   | Chi phí thiết kế bản vẽ thi công                                                                                            |
| CP50511 | Chi phí thiết kế bản vẽ thi công (Phát sinh)                                                                                |
| CP50530 | Chi phí lập thiết kế bản vẽ thi công - dự toán                                                                              |
| CP50541 | Chi phí lập thiết kế bản vẽ thi công - dự toán (Phát sinh)                                                                  |
| CP506   | Chi phí lập nhiệm vụ khảo sát xây dựng                                                                                      |
| CP50602 | Chi phí lập nhiệm vụ khảo sát (Bước lập báo cáo nghiên cứu tiền khả thi (NCTKT))                                            |
| CP50603 | Chi phí lập nhiệm vụ khảo sát (Bước lập báo cáo nghiên cứu khả thi (NCKT))                                                  |
| CP50604 | Chi phí lập nhiệm vụ khảo sát (Bước lập thiết kế bản vẽ thi công (TKBVTC))                                                  |
| CP50605 | Chi phí lập nhiệm vụ khảo sát (Bước lập thiết kế bản vẽ thi công - dự toán (TKBVTC-DT))                                     |
| CP507   | Chi phí thẩm tra báo cáo kinh tế - kỹ thuật                                                                                 |
| CP508   | Chi phí thẩm tra báo cáo nghiên cứu khả thi                                                                                 |
| CP509   | Chi phí thẩm tra thiết kế xây dựng                                                                                          |
| CP50911 | Chi phí thẩm tra thiết kế xây dựng (Phát sinh)                                                                              |
| CP510   | Chi phí thẩm tra dự toán xây dựng                                                                                           |
| CP51011 | Chi phí thẩm tra dự toán xây dựng (Phát sinh)                                                                               |
| CP511   | Chi phí lập hồ sơ mời thầu (hồ sơ yêu cầu), đánh giá hồ sơ dự thầu (hồ sơ đề xuât) tư vấn                                   |
| CP512   | Chi phí lập hồ sơ mời thầu (hồ sơ yêu cầu) tư vấn                                                                           |
| CP513   | Chi phí đánh giá hồ sơ dự thầu (hồ sơ đề xuất) tư vấn                                                                       |
| CP51311 | Chi phí đánh giá hồ sơ dự thầu (hồ sơ đề xuất) tư vấn (Phát sinh)                                                           |
| CP514   | Chi phí lập HSMT (HSYC), đánh giá HSDT (HSĐX) thi công xây dựng                                                             |
| CP51411 | Chi phí lập HSMT (HSYC), đánh giá HSDT (HSĐX) thi công xây dựng (Phát sinh)                                                 |
| CP515   | Chi phí lập hồ sơ mời thầu (hồ sơ yêu cầu) thi công xây dựng                                                                |
| CP51511 | Chi phí lập hồ sơ mời thầu (hồ sơ yêu cầu) thi công xây dựng (Phát sinh)                                                    |
| CP516   | Chi phí đánh giá hồ sơ dự thầu (hồ sơ đề xuất) thi công xây dựng                                                            |
| CP51611 | Chi phí đánh giá hồ sơ dự thầu (hồ sơ đề xuất) thi công xây dựng (Phát sinh)                                                |
| CP517   | Chi phí lập HSMT (HSYC), đánh giá HSDT (HSĐX) mua sắm vật tư, thiết bị                                                      |
| CP51711 | Chi phí lập HSMT (HSYC), đánh giá HSDT (HSĐX) mua sắm vật tư, thiết bị (Phát sinh)                                          |
| CP518   | Chi phí lập HSMT (HSYC) mua sắm vật tư, thiết bị                                                                            |
| CP51811 | Chi phí lập HSMT (HSYC) mua sắm vật tư, thiết bị (Phát sinh)                                                                |
| CP519   | Chi phí đánh giá HSDT (HSĐX) mua sắm vật tư, thiết bị                                                                       |
| CP51911 | Chi phí đánh giá HSDT (HSĐX) mua sắm vật tư, thiết bị (Phát sinh)                                                           |
| CP520   | Chi phí giám sát thi công xây dựng                                                                                          |
| CP52099 | Chi phí giám sát thi công xây dựng (Phát sinh)                                                                              |
| CP521   | Chi phí giám sát lắp đặt thiết bị                                                                                           |
| CP52111 | Chi phí giám sát lắp đặt thiết bị (Phát sinh)                                                                               |
| CP522   | Chi phí giám sát công tác khảo sát xây dựng                                                                                 |
| CP523   | Chi phí quy đổi vốn đầu tư xây dựng                                                                                         |
| CP526   | Phí thẩm định hồ sơ mời thầu (hồ sơ yêu cầu)                                                                                |
| CP527   | Chi phí thẩm tra báo cáo nghiên cứu tiền khả thi                                                                            |
| CP528   | Chi phí khảo sát xây dựng                                                                                                   |
| CP52802 | Chi phí khảo sát (Bước lập báo cáo nghiên cứu tiền khả thi (NCTKT))                                                         |
| CP52803 | Chi phí khảo sát (Bước lập báo cáo nghiên cứu khả thi (NCKT))                                                               |
| CP52804 | Chi phí khảo sát (Bước lập báo cáo kinh tế kỹ thuật (KTKT))                                                                 |
| CP52805 | Chi phí khảo sát (Bước lập thiết kế bản vẽ thi công (TKBVTC))                                                               |
| CP52806 | Chi phí khảo sát (Bước lập thiết kế bản vẽ thi công - dự toán (TKBVTC-DT))                                                  |
| CP532   | Phí thẩm định hồ sơ mời thầu (hồ sơ yêu cầu) gói thầu thi công xây dựng                                                     |
| CP533   | Phí thẩm định hồ sơ mời thầu (hồ sơ yêu cầu) gói thầu lắp đặt thiết bị                                                      |
| CP534   | Phí thẩm định hồ sơ mời thầu (hồ sơ yêu cầu) gói thầu tư vấn đầu tư xây dựng                                                |
| CP535   | Phí thẩm định kết quả lựa chọn nhà thầu thi công xây dựng                                                                   |
| CP536   | Phí thẩm định kết quả lựa chọn nhà thầu lắp đặt thiết bị                                                                    |
| CP537   | Phí thẩm định kết quả lựa chọn nhà thầu tư vấn đầu tư xây dựng                                                              |
| CP538   | Phí thẩm định hồ sơ mời thầu (hồ sơ yêu cầu), đánh giá kết quả lựa chọn nhà thầu (hồ sơ đề xuất) xây lắp                    |
| CP539   | Phí thẩm định hồ sơ mời thầu (hồ sơ yêu cầu), đánh giá kết quả lựa chọn nhà thầu (hồ sơ đề xuất) lắp đặt thiết bị           |
| CP540   | Phí thẩm định hồ sơ mời thầu (hồ sơ yêu cầu), đánh giá kết quả lựa chọn nhà thầu (hồ sơ đề xuất) tư vấn đầu tư xây dựng     |
| CP541   | Phí thẩm định hồ sơ mời thầu (hồ sơ yêu cầu), đánh giá kết quả lựa chọn nhà thầu (hồ sơ đề xuất)                            |
| CP551   | Chi phí khảo sát, thiết kế                                                                                                  |
| CP552   | Chi phí nhiệm vụ thử tỉnh cọc                                                                                               |
| CP553   | Công tác điều tra, đo đạt và thu thập số liệu                                                                               |
| CP554   | Chi phí kiểm tra và chứng nhận sự phù hợp về chất lượng công trình xây dựng                                                 |
| CP556   | Chi phí thẩm tra an toàn giao thông                                                                                         |
| CP557   | Chi phí thử tĩnh                                                                                                            |
| CP558   | Chi phí công bố quy hoạch                                                                                                   |
| CP559   | Chi phí thử tải cừ tràm                                                                                                     |
| CP560   | Chi phí kiểm định chất lượng phục vụ công tác nghiệm thu                                                                    |
| CP561   | Chi phí cắm mốc ranh giải phóng mặt bằng                                                                                    |
| CP56111 | Chi phí lập đồ án quy hoạch                                                                                                 |
| CP56201 | Chi phí khảo sát địa chất                                                                                                   |
| CP56202 | Chi phí khảo sát địa chất (Bước lập báo cáo nghiên cứu tiền khả thi (NCTKT))                                                |
| CP56203 | Chi phí khảo sát địa chất (Bước lập báo cáo nghiên cứu khả thi (NCKT))                                                      |
| CP56204 | Chi phí khảo sát địa chất (Bước lập báo cáo kinh tế kỹ thuật (KTKT))                                                        |
| CP56205 | Chi phí khảo sát địa chất (Bước lập thiết kế bản vẽ thi công (BVTC))                                                        |
| CP56206 | Chi phí khảo sát địa chất (Bước lập thiết kế bản vẽ thi công - dự toán (BVTC-DT))                                           |
| CP563   | Chi phí thẩm tra tính hiệu quả, tính khả thi của dự án                                                                      |
| CP56301 | Chi phí khảo sát địa hình                                                                                                   |
| CP56302 | Chi phí khảo sát địa hình (Bước lập báo cáo nghiên cứu tiền khả thi (NCTKT))                                                |
| CP56303 | Chi phí khảo sát địa hình (Bước lập báo cáo nghiên cứu khả thi (NCKT))                                                      |
| CP56304 | Chi phí khảo sát địa hình (Bước lập báo cáo kinh tế kỹ thuật (KTKT))                                                       |
| CP56305 | Chi phí khảo sát địa hình (Bước lập thiết kế bản vẽ thi công (BVTC))                                                       |
| CP56306 | Chi phí khảo sát địa hình (Bước lập thiết kế bản vẽ thi công - dự toán (BVTC-DT))                                          |
| CP564   | Tư vấn lập văn kiện dự án và các báo cáo thành phần của dự án                                                               |
| CP56401 | Chi phí khảo sát địa hình, địa hình                                                                                              |
| CP565   | Chi phí lập kế hoạch bảo vệ môi trường                                                                                      |
| CP566   | Chi phí lập báo cáo đánh giá tác động môi trường                                                                            |
| CP567   | Chi phí thí nghiệm đối chứng, kiểm định xây dựng, thử nghiệm khả năng chịu lực của công trình                               |
| CP568   | Chi phí chuẩn bị đầu tư ban đầu sáng tác thi tuyển mẫu phác thảo bước 1                                                     |
| CP569   | Chi phí chỉ đạo thể hiện phần mỹ thuật                                                                                      |
| CP570   | Chi phí nội đồng nghệ thuật                                                                                                 |
| CP571   | Chi phí sáng tác mẫu phác thảo tượng đài                                                                                    |
| CP572   | Chi phí hoạt động của Hội đồng nghệ thuật                                                                                   |
| CP573   | Chi phí giám sát thi công xây dựng phát sinh                                                                                |
| CP57301 | Chi phí kiểm định theo yêu cầu chủ đầu tư                                                                                   |
| CP574   | Chi phí tư vấn thẩm tra dự toán                                                                                             |
| CP57401 | Chi phí thẩm tra dự toán phát sinh                                                                                          |
| CP575   | Chi phí thẩm định dự toán giá gói thầu                                                                                      |
| CP577   | Chi phí lập hồ sơ điều chỉnh dự toán                                                                                        |
| CP578   | Chi phí chuyển giao công nghệ                                                                                               |
| CP579   | Chi phí thẩm định giá                                                                                                       |
| CP580   | Chi phí tư vấn giám sát                                                                                                     |
| CP581   | Chi phí báo cáo giám sát đánh giá đầu tư                                                                                    |
| CP582   | Chi phí thẩm tra thiết kế bản vẽ thi công - dự toán (BVTC-DT)                                                               |
| CP58211 | Chi phí thẩm tra thiết kế bản vẽ thi công - dự toán (BVTC-DT) (Phát sinh)                                                   |
| CP58220 | Chi phí thẩm tra thiết kế bản vẽ thi công (BVTC)                                                                            |
| CP58231 | Chi phí thẩm tra thiết kế bản vẽ thi công (BVTC) (Phát sinh)                                                                |
| CP583   | Tư vấn đầu tư xây dựng                                                                                                      |
| CP584   | Chi phí đăng báo đấu thầu                                                                                                   |
| CP599   | Chi phí đo đạc thu hồi đất                                                                                                  |
| CP6     | Chi phí khác                                                                                                                |
| CP601   | Phí thẩm định dự án đầu tư xây dựng                                                                                         |
| CP602   | Phí thẩm định dự toán xây dựng                                                                                              |
| CP603   | Chi phí rà phá bom mìn, vật nổ                                                                                              |
| CP604   | Phí thẩm định phê duyệt thiết kế về phòng cháy và chữa cháy                                                                 |
| CP605   | Chi phí thẩm định giá thiết bị                                                                                              |
| CP606   | Phí thẩm định thiết kế xây dựng triển khai sau thiết kế cơ sở                                                               |
| CP607   | Chi phí thẩm tra, phê duyệt quyết toán                                                                                      |
| CP608   | Chi phí kiểm tra công tác nghiệm thu                                                                                        |
| CP609   | Chi phí kiểm toán độc lập                                                                                                   |
| CP60902 | Chi phí kiểm toán công trình                                                                                                |
| CP60999 | Chi phí kiểm toán độc lập (Phát sinh)                                                                                       |
| CP610   | Chi phí bảo hiểm                                                                                                            |
| CP61099 | Chi phí bảo hiểm (Phát sinh)                                                                                                |
| CP611   | Chi phí thẩm định báo cáo đánh giá tác động môi trường                                                                      |
| CP612   | Chi phí bảo hành, bảo trì                                                                                                   |
| CP613   | Phí bảo vệ môi trường                                                                                                       |
| CP614   | Chi phí di dời điện                                                                                                         |
| CP61401 | Chi phí di dời hệ thống điện chiếu sáng                                                                                     |
| CP61402 | Chi phí di dời đường dây hạ thế                                                                                             |
| CP61403 | Chi phí di dời nhà                                                                                                          |
| CP61404 | Chi phí di dời nước                                                                                                         |
| CP61405 | Chi phí di dời trụ điện trong trường                                                                                        |
| CP615   | Phí thẩm tra di dời điện                                                                                                    |
| CP616   | Chi phí hạng mục chung                                                                                                      |
| CP617   | Chi phí đo đạc địa chính                                                                                                    |
| CP61701 | Chi phí đo đạc bản đồ địa chính                                                                                        |
| CP61702 | Chi phí đo đạc lập bản đồ địa chính giải phóng mặt bằng (GPMB)                                                              |
| CP61703 | Chi phí đo đạc, đền bù giải phóng mặt bằng (GPMB)                                                                           |
| CP61704 | Chi phí đo đạc thu hồi đất                                                                                                  |
| CP61820 | Chi phí tổ chức kiểm tra công tác nghiệm thu                                                                                |
| CP619   | Chi phí lán trại                                                                                                            |
| CP620   | Chi phí đảm bảo giao thông                                                                                                  |
| CP621   | Chi phí điều tiết giao thông                                                                                                |
| CP62101 | Chi phí điều tiết giao thông khác                                                                                           |
| CP622   | Chi phí một số công tác không xác định số lượng từ thiết kế                                                                 |
| CP623   | Chi phí thẩm định thiết kế bản vẽ thi công, lệ phí thẩm định báo cáo kinh tế kỹ thuật (KTKT)                                |
| CP624   | Chi phí nhà tạm                                                                                                             |
| CP62501 | Chi phí giám sát đánh giá đầu tư                                                                                            |
| CP626   | Chi phí thẩm định kết quả lựa chọn nhà thầu                                                                                 |
| CP62701 | Chi phí khoan địa chất                                                                                                      |
| CP628   | Chi phí thẩm định đồ án quy hoạch                                                                                           |
| CP629   | Chi phí thẩm định HSMT (HSYC)                                                                                               |
| CP630   | Lệ phí thẩm tra thiết kế                                                                                                    |
| CP631   | Phí thẩm định lựa chọn nhà thầu                                                                                             |
| CP632   | Chi phí thẩm tra quyết toán                                                                                                 |
| CP633   | Chi phí thẩm định phê duyệt quyết toán                                                                                      |
| CP634   | Chi phí thẩm định báo cáo nghiên cứu khả thi                                                                                |
| CP699   | Chi phí khác                                                                                                                |
| CP7     | Chi phí dự phòng                                                                                                            |
| CP701   | Chi phí dự phòng cho khối lượng, công việc phát sinh                                                                        |
| CP702   | Chi phí dự phòng cho yếu tố trược giá                                                                                       |
| CP703   | Chi phí dự phòng phát sinh khối lượng (cho yếu tố khối lượng phát sinh (KLPS))                                              |

### Yêu cầu xử lý:

Thực hiện ánh xạ từng dòng `TenKMCP` trong bảng `KMCP_AnhXa` với mục tương ứng trong bảng chuẩn `KMCP` theo **thứ tự ưu tiên sau**:

#### 1. Ưu tiên so khớp theo **nghĩa chuyên môn nghiệp vụ**:
- Sử dụng hiểu biết chuyên ngành để ánh xạ đúng các từ viết tắt, quy ước phổ biến (VD: KLPS = khối lượng phát sinh).
- So sánh các cụm từ chính như: "thẩm định báo cáo KTKT", "giám sát thi công", "lập hồ sơ yêu cầu", "bảo hiểm công trình", v.v.
- Không phụ thuộc hoàn toàn vào độ giống chuỗi ký tự.

#### 2. Nếu không tìm được theo nghĩa chuyên môn, mới **so khớp theo độ tương đồng chuỗi ký tự** (sử dụng thuật toán so sánh như `difflib` hoặc `fuzz`).
- Chỉ chọn ánh xạ nếu độ tương đồng ≥ 65% (hoặc ≥ 50% nếu muốn mở rộng).
- Trường hợp độ tương đồng < ngưỡng, để giá trị ánh xạ rỗng và ghi chú rõ lý do.
---
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
⚠️ Nếu ánh xạ theo nghiệp vụ (không qua so chuỗi), ghi rõ "Ánh xạ theo nghiệp vụ" trong trường GhiChu.
⚠️ Chỉ ánh xạ 1:1, không ánh xạ nhiều khoản mục về một mã chuẩn.
⚠️ Không tự tạo khoản mục mới ngoài danh mục chuẩn.
"""
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
            max_completion_tokens=5000
        )
        # print("+"*20)
        # print(promt_anh_xa_noi_dung_tuong_dong)
        # print("+"*20)
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
                if row['GhiChu'] == 'Không có thông tin':
                    dfBangGhepKMCP.at[index, 'TenKMCP_Moi'] = ''
                    dfBangGhepKMCP.at[index, 'MaKMCP'] = ''
            
            #print(dfBangGhepKMCP)

            query_van_ban = f"""
            select 
            BangDuLieuChiTietAIID = convert(nvarchar(36), BangDuLieuChiTietAIID)
            , VanBanAIID = convert(nvarchar(36), VanBanAIID)
            , TenKMCP, TenKMCP_AI, MaKMCP='', GhiChuAI=''
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
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success", 
                    "code": 200,
                    "message": "Xử lý kết quả ánh xạ từ AI thành công",
                    "data": [row.to_dict() for row in kmcp_ghep_duoc],
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
                    "detail": f"Lỗi: {str(e)}\nLoại lỗi: {type(e).__name__}\nChi tiết: {e.__dict__ if hasattr(e, '__dict__') else 'Không có thông tin chi tiết'}"
                }
            )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "code": 500,
                "message": "Lỗi hệ thống",
                "detail": f"Lỗi: {str(e)}\nLoại lỗi: {type(e).__name__}\nChi tiết: {e.__dict__ if hasattr(e, '__dict__') else 'Không có thông tin chi tiết'}"
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
                with open(temp_file, "rb") as f:
                    poller = azure_client.begin_analyze_document("prebuilt-layout", document=f)
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
                print(f"Error processing file {temp_file}: {str(e)}")
                continue

        # print("&"*30)
        # print(combined_text)
        # print("&"*30)
        # Process extracted text with OpenAI
        try:
            # Prepare messages for OpenAI
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


            print("+"*20)
            print(response_text)
            print("+"*20)

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
                                or col.startswith('GiaTriNghiemThu') or col.startswith('TamUngChuaThuaHoi') or col.startswith('TamUngGiaiNganKyNayKyTruoc')
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
                        print("Kiểm tra van_ban_id: ", van_ban_id)
                        item["VanBanID"] = van_ban_id
                        # Convert all numeric values based on required columns
                        for col in required_columns:
                            print("Cột kiểm tra:", col)
                            if (col.startswith('GiaTri') or col.startswith('SoTien') or col.startswith('ThanhToanDenCuoiKyTruoc') or col.startswith('LuyKeDenCuoiKy')
                                or col.startswith('GiaTriNghiemThu') or col.startswith('TamUngChuaThuaHoi') or col.startswith('TamUngGiaiNganKyNayKyTruoc')
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
    duLieuCanTim: Optional[str] = None,
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
    if loaiDuLieu.lower() == "kmcp":
        try:
            # Truy vấn lấy danh sách KMCP
            query = """
            select KMCPID, TenKMCP 
            from dbo.KMCP 
            order by TenKMCP
            """
            
            # Thực thi truy vấn
            result = db.execute(text(query))
            kmcp_list = result.fetchall()
            
            # Chuyển đổi kết quả thành list dict
            kmcp_data = {row.KMCPID: row.TenKMCP for row in kmcp_list}
            # VIET_TAT_KMCP = {
            #     "cpxd": "chi phí xây dựng",
            #     "cpxl": "chi phí xây dựng",
            #     "tdc": "tái định cư",
            #     "cpql": "chi phí quản lý dự án",
            #     "qlda": "chi phí quản lý dự án",
            #     "tvtk": "tư vấn đầu tư xây dựng",
            #     "tvgs": "tư vấn đầu tư xây dựng",
            #     "cpdp": "chi phí dự phòng",
            #     "khac": "chi phí khác",
            #     "ktkt": "kinh tế kỹ thuật",
            #     "bc": "báo cáo",
            #     "bvtc": "bản vẽ thi công",
            #     "dt": "dự toán"
            # }
            try:
                ket_qua_tim = tim_kiem_tuong_dong(duLieuCanTim, kmcp_data, 0.50)
                # print(ket_qua_tim)
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "success", 
                        "code": 200,
                        "message": "Lấy danh sách KMCP thành công",
                        "data": ket_qua_tim
                    }
                )
            except Exception as e:
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "code": 500,
                        "message": "Lỗi khi tìm kiếm KMCP",
                        "detail": f"Lỗi chi tiết: {str(e)}\nTraceback: {traceback.format_exc()}"
                    }
                )
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "code": 500,
                    "message": "Lỗi khi lấy danh sách KMCP",
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
            result = db.execute(text(query))
            nguonvon_list = result.fetchall()
            
            # Chuyển đổi kết quả thành list dict
            nguonvon_data = {row.NguonVonID: row.TenNguonVon for row in nguonvon_list}
            # VIET_TAT = {
            #     "xskt": "Xổ số kiến thiết",
            # }
            try:
                ket_qua_tim = tim_kiem_tuong_dong(duLieuCanTim, nguonvon_data, 0.50)
                # print(ket_qua_tim)
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "success", 
                        "code": 200,
                        "message": "Lấy danh sách Nguồn vốn thành công",
                        "data": ket_qua_tim
                    }
                )
            except Exception as e:
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "code": 500,
                        "message": "Lỗi khi tìm kiếm KMCP",
                        "detail": f"Lỗi chi tiết: {str(e)}\nTraceback: {traceback.format_exc()}"
                    }
                )
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "code": 500,
                    "message": "Lỗi khi lấy danh sách KMCP",
                    "detail": str(e)
                }
            )