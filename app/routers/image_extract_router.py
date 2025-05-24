from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends, Form, Header
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel
import os
import google.generativeai as genai
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
from app.services.DungChung import convert_currency_to_int, lay_du_lieu_tu_sql_server, thuc_thi_truy_van, decode_jwt_token, LayMaDoiTuong
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


# Load biến môi trường từ file .env
load_dotenv()

router = APIRouter()

# Cấu hình API keys từ biến môi trường
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

model_openai = os.getenv('MODEL_API_OPENAI')

# Khởi tạo models
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

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

ALLOWED_PDF_TYPE = 'application/pdf'

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

@router.post("/image_extract_multi")
async def extract_multiple_images(
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
                    "role": "user",
                    "content": content_parts
                }
            ]
            # Gọi OpenAI API
            client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            response = client.chat.completions.create(
                model="gpt-4o",  # Hoặc mô hình hỗ trợ xử lý nhiều ảnh khác
                messages=messages,
                max_tokens=4000  # Tăng max_tokens nếu cần cho kết quả dài hơn
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
            print("\033[31mKẾT QUẢ NHẬN DẠNG HÌNH ẢNH\033[0m")
            print(response_text)
            #return
            # Nếu AI trả về lỗi rõ ràng
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
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "code": 400,
                        "message": "Không thể trích xuất đầy đủ thông tin từ ảnh",
                        "detail": f"Thiếu các trường: {', '.join(missing_fields)}",
                        "missing_fields": missing_fields
                    }
                )

            # Set UUIDs in the response data
            data_json["BangDuLieuID"] = bang_du_lieu_chi_tiet_id
            data_json["VanBanID"] = van_ban_id

            # Convert currency values in the response
            if "BangDuLieu" in data_json:
                for item in data_json["BangDuLieu"]:
                    item["VanBanID"] = van_ban_id
                    # Convert all numeric values based on required columns
                    for col in required_columns:
                        if (col.startswith('GiaTri') or col.startswith('SoTien')) and item.get(col):
                            try:
                                item[col] = convert_currency_to_int(str(item[col]))
                            except:
                                item[col] = 0
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
                "JsonAI": json.dumps(data_json["ThongTinChung"], ensure_ascii=False),
                "DataOCR": response_text,
                "TenFile": "*".join([d['filename'] for d in all_data])
            }
            if  f"[{loaiVanBan}]" in "[BCDX_CT];[QDPD_CT];[QDPD_DA];[QDPD_KHLCNT_CBDT];[QDPD_KHLCNT_THDT]":
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
                    "JsonAI": json.dumps(data_json["ThongTinChung"], ensure_ascii=False),
                    "DataOCR": response_text,
                    "TenFile": "*".join([d['filename'] for d in all_data])
                }
            if  f"[{loaiVanBan}]" in "[HOP_DONG]":
                _LoaiVanBanID = "3F278B7B-6E81-4480-BFC6-80885DAEAFF1"
                _GiaiDoan = "3"
                van_ban_data = {
                    "VanBanAIID": van_ban_id,
                    "SoVanBan": data_json["ThongTinChung"].get("SoVanBan", ""),
                    "NgayKy": data_json["ThongTinChung"].get("NgayKy", ""),
                    "NgayHieuLuc": data_json["ThongTinChung"].get("NgayHieuLuc", ""),
                    "NgayKetThuc": data_json["ThongTinChung"].get("NgayKetThuc", ""),
                    "NguoiKy": data_json["ThongTinChung"].get("NguoiKy", ""),
                    "ChucDanhNguoiKy": data_json["ThongTinChung"].get("ChucDanhNguoiKy", ""),
                    "TrichYeu": data_json["ThongTinChung"].get("TrichYeu", ""),
                    "CoQuanBanHanh": data_json["ThongTinChung"].get("CoQuanBanHanh", ""),
                    "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "TenLoaiVanBan": loaiVanBan,
                    "LoaiVanBanID": _LoaiVanBanID,
                    "GiaiDoanID": "",
                    "GiaiDoan": _GiaiDoan,
                    "DuAnID": duAnID,
                    "DieuChinh": "0",
                    "JsonAI": json.dumps(data_json["ThongTinChung"], ensure_ascii=False),
                    "DataOCR": response_text,
                    "TenFile": "*".join([d['filename'] for d in all_data]),
                    "UserID": user_id,
                    "DonViID": don_vi_id
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
            if "BangDuLieu" in data_json and data_json["BangDuLieu"]:
                bang_du_lieu_data = []
                for item in data_json["BangDuLieu"]:
                    bang_du_lieu_data.append({
                        "VanBanAIID": van_ban_id,
                        **{col: item.get(col, 0) for col in required_columns}
                    })
                #print("insert_bang_du_lieu_chi_tiet_ai=============")
                #print(bang_du_lieu_data)
                # Danh sách các khoản mục chi phí cần kiểm tra
                # kmcp_list = [
                #     "Chi phí bồi thường, hỗ trợ, tái định cư",
                #     "Chi phí xây dựng hoặc xây lắp",
                #     "Chi phí thiết bị", 
                #     "Chi phí quản lý dự án",
                #     "Chi phí tư vấn đầu tư xây dựng",
                #     "Chi phí khác",
                #     "Chi phí dự phòng"
                # ]

                # Lọc và xóa các dòng thỏa mãn điều kiện
                # filtered_data = []
                # for i in range(len(bang_du_lieu_data)):
                #     current_row = bang_du_lieu_data[i]
                #     current_kmcp = current_row.get("TenKMCP", "")
                    
                #     # Kiểm tra nếu TenKMCP chứa trong danh sách kmcp_list
                #     if any(kmcp in current_kmcp for kmcp in kmcp_list):
                #         # Kiểm tra dòng tiếp theo
                #         if i < len(bang_du_lieu_data) - 1:
                #             next_row = bang_du_lieu_data[i + 1]
                #             next_kmcp = next_row.get("TenKMCP", "")
                            
                #             # Nếu TenKMCP của dòng tiếp theo khác với dòng hiện tại
                #             if next_kmcp != current_kmcp:
                #                 continue  # Bỏ qua dòng hiện tại
                    
                #     filtered_data.append(current_row)

                # # Cập nhật lại bang_du_lieu_data với dữ liệu đã lọc
                # bang_du_lieu_data = filtered_data
                # print("insert_bang_du_lieu_chi_tiet_ai=============")
                # print(bang_du_lieu_data)
                # print(required_columns)
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
                    "detail": str(e)
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

@router.post("/image_extract_multi_azure")
async def extract_multiple_images_azure(
    files: List[UploadFile] = File(...),
    authorization: str = Header(...)
):
    # Load require_fields from Markdown file
    try:
        with open('data/require_fields.md', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Parse markdown content to extract field information
        require_fields = []
        current_field = None
        
        for line in content.split('\n'):
            # Check for field headers (## number. fieldName)
            if line.startswith('## '):
                if current_field:
                    require_fields.append(current_field)
                field_name = line.split('. ')[1].strip()
                current_field = {
                    "tenTruong": field_name,
                    "moTa": "",
                    "extractionRules": {}
                }
            # Check for description
            elif line.startswith('**Mô tả:**'):
                if current_field:
                    current_field["moTa"] = line.replace('**Mô tả:**', '').strip()
            # Check for extraction rules
            elif line.startswith('**Quy tắc trích xuất:**'):
                continue
            # Check for rule items
            elif line.startswith('- **'):
                if current_field:
                    key = line.split('**')[1].replace(':**', '').strip()
                    value = line.split(':**')[1].strip()
                    current_field["extractionRules"][key] = value
            # Check for mapping tables
            elif '| Mã | Giá trị |' in line:
                if current_field:
                    mapping = {}
                    # Skip header and separator lines
                    continue
            elif line.startswith('  | '):
                if current_field and 'mapping' not in current_field["extractionRules"]:
                    current_field["extractionRules"]["mapping"] = {}
                parts = line.strip().split('|')
                if len(parts) >= 3:
                    code = parts[1].strip()
                    value = parts[2].strip()
                    current_field["extractionRules"]["mapping"][code] = value
                    
        # Add the last field
        if current_field:
            require_fields.append(current_field)
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "code": 500,
                "message": "Lỗi đọc file require_fields.md",
                "detail": str(e)
            }
        )

    # Print raw file data
    print("\n=== Raw File Data ===")
    for file in files:
        print(f"\nFile: {file.filename}")
        print(f"Content Type: {file.content_type}")
        content = await file.read()
        print(f"Size: {len(content)} bytes")
        await file.seek(0)  # Reset file pointer
    print("\n=== End Raw File Data ===\n")

    # Initialize combined data
    combined_data = {}

    # Process each file
    for file in files:
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
                content = await file.read()
                temp_file.write(content)
                temp_file.flush()

                # Initialize the client
                endpoint = os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT")
                key = os.getenv("AZURE_FORM_RECOGNIZER_KEY")
                document_analysis_client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))

                # Start the document analysis
                with open(temp_file.name, "rb") as f:
                    poller = document_analysis_client.begin_analyze_document(
                        "prebuilt-layout", document=f
                    )
                result = poller.result()

                # Print OCR text content
                print("\n=== Azure Form Recognizer OCR Text ===")
                print(f"\nDocument: {temp_file.name}")
                
                # Collect all text content
                full_text = ""
                for page in result.pages:
                    full_text += f"\nPage {page.page_number}:\n"
                    for line in page.lines:
                        full_text += line.content + "\n"
                
                print(full_text)
                print("\n=== End OCR Text ===\n")

                # Use OpenAI to map text to required fields
                try:
                    # Prepare the prompt for OpenAI
                    messages = [
                        {
                            "role": "system",
                            "content": "You are an AI assistant that extracts information from documents. You MUST return a valid JSON object containing the mapped fields. Do not include any other text or explanation in your response."
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"""
                                    Extract and map information from the following OCR text to the specified fields.
                                    Return ONLY a JSON object with the following structure:
                                    {{
                                        "docId": "string or null",
                                        "arcDocCode": "string or null",
                                        "maintenance": "string or null",
                                        "typeName": "string or null",
                                        "codeNumber": "string or null",
                                        "codeNotation": "string or null",
                                        "issuedDate": "string or null",
                                        "organName": "string or null",
                                        "subject": "string or null",
                                        "language": "string or null",
                                        "numberOfPage": "string or null",
                                        "inforSign": "string or null",
                                        "keyword": "string or null",
                                        "mode": "string or null",
                                        "confidenceLevel": "string or null",
                                        "autograph": "string or null",
                                        "format": "string or null",
                                        "process": "string or null",
                                        "riskRecovery": "string or null",
                                        "riskRecoveryStatus": "string or null",
                                        "description": "string or null",
                                        "SignerTitle": "string or null",
                                        "SignerName": "string or null"
                                    }}

                                    Field definitions and extraction rules:
                                    {json.dumps(require_fields, ensure_ascii=False, indent=2)}

                                    General rules:
                                    1. Look for information based on the extraction rules specified in the field definition
                                    2. Pay attention to the location hints in the rules
                                    3. Use the provided keywords to identify relevant information
                                    4. Follow the specified format requirements
                                    5. Use the mapping tables when provided
                                    6. Use default values when specified
                                    7. Set to null if information cannot be found
                                    8. For dates, use DD/MM/YYYY format
                                    9. For numbers, remove thousand separators

                                    OCR Text:
                                    {full_text}

                                    Remember: Return ONLY the JSON object, no other text or explanation.
                                    """
                                }
                            ]
                        }
                    ]

                    # Call OpenAI API
                    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=messages,
                        max_tokens=4000,
                        temperature=0,  # Set temperature to 0 for more consistent output
                        response_format={"type": "json_object"}  # Force JSON response
                    )

                    # Process response from OpenAI
                    response_text = response.choices[0].message.content.strip()
                    
                    # Clean up response text
                    if response_text.strip().startswith("```json"):
                        response_text = response_text.strip()[7:-3].strip()
                    elif response_text.strip().startswith("```"):
                        response_text = response_text.strip()[3:-3].strip()

                    print("\n=== Mapped Fields ===")
                    print(response_text)
                    print("=== End Mapped Fields ===\n")

                    try:
                        # Parse the response
                        mapped_data = json.loads(response_text)
                        
                        # Validate required fields
                        required_fields_list = [field["tenTruong"] for field in require_fields]
                        for field in required_fields_list:
                            if field not in mapped_data:
                                mapped_data[field] = None
                        
                        # Update combined data with mapped fields
                        for field, value in mapped_data.items():
                            if field not in combined_data or combined_data[field] is None:
                                combined_data[field] = value
                            elif value is not None:
                                combined_data[field] = value

                    except json.JSONDecodeError as e:
                        print(f"Error parsing JSON response: {str(e)}")
                        print(f"Raw response: {response_text}")
                        raise Exception("Invalid JSON response from OpenAI")

                except Exception as e:
                    print(f"Error in OpenAI mapping: {str(e)}")

        except Exception as e:
            print(f"Error processing file {file.filename}: {str(e)}")

    # Return combined data
    return {
        "status": "success",
        "data": combined_data
    }

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
        # print(query_van_ban)
        # B3: Lấy dữ liệu từ BangDuLieuChiTietAI
        chuoi_markdown_tenkmcp = ""
        chuoi_markdown_tenkmcp += "| STT | TenKMCP |\n"
        chuoi_markdown_tenkmcp += "|-----|----------|\n"
        if not dfVanBanAI.empty:
            for index, row in dfVanBanAI.iterrows():
                van_ban_id = row['VanBanAIID']
                query = f"select STT=convert(int, STT), TenKMCP from dbo.BangDuLieuChiTietAI where VanBanAIID='{van_ban_id}'"
                df_temp = lay_du_lieu_tu_sql_server(query)
                if not df_temp.empty:
                    for _, row in df_temp.iterrows():
                        chuoi_markdown_tenkmcp += f"| {row['STT']} | {row['TenKMCP']} |\n"
        else:
            dfBangDuLieuChiTietAI = pd.DataFrame()

        # Xử lý ghép TenKMCP trong chuoi_markdown_tenkmcp với TenKMCP trong bảng KMCP
        promt_anh_xa_noi_dung_tuong_dong = """
### Bạn là một hệ thống phân tích và ánh xạ từ ngữ thông minh. Hãy thực hiện so sánh và ánh xạ ý nghĩa giữa các khoản mục chi phí bảng `DuLieuChiTiet` được liệt kê theo bảng sau với danh mục chi phí chuẩn trong hệ thống bảng `KMCP`
#### Bảng DuLieuChiTiet 
"""+chuoi_markdown_tenkmcp+"""
#### Bảng KMCP 
MaKMCP  TenKMCP
CP1 Chi phí bồi thường, hỗ trợ, tái định cư
CP101   Chi phí bồi thường về đất, nhà, công trình trên đất, các tài sản gắn liền với đất, trên mặt nước và chi phí bồi thường khác
CP102   Chi phí các khoản hỗ trợ khi nhà nước thu hồi đất
CP103   Chi phí tái định cư
CP104   Chi phí tổ chức bồi thường, hỗ trợ và tái định cư
CP105   Chi phí sử dụng đất, thuê đất tính trong thời gian xây dựng
CP106   Chi phí di dời, hoàn trả cho phần hạ tầng kỹ thuật đã được đầu tư xây dựng phục vụ giải phóng mặt bằng
CP107   Chi phí đầu tư vào đất
CP199   Chi phí khác có liên quan đến công tác bồi thường, hỗ trợ và tái định cư
CP2 Chi phí xây dựng hoặc xây lắp
CP202   Chi phí xây dựng hoặc xây lắp công trình chính
CP203   Chi phí xây dựng hoặc xây lắp công trình chính và phụ
CP204   Chi phí xây dựng hoặc xây lắp điều chỉnh
CP205   Chi phí xây dựng hoặc xây lắp trước thuế
CP206   Chi phí xây dựng hoặc xây lắp sau thuế
CP207   Chi phí xây dựng hoặc xây lắp công trình phụ
CP250   Chi phí xây dựng hoặc xây lắp khác
CP3 Chi phí thiết bị
CP4 Chi phí quản lý dự án
CP5 Chi phí tư vấn đầu tư xây dựng
CP501   Chi phí lập báo cáo nghiên cứu tiền khả thi
CP502   Chi phí lập báo cáo nghiên cứu khả thi
CP503   Chi phí lập báo cáo kinh tế - kỹ thuật
CP50301 Chi phí lập dự án đầu tư
CP504   Chi phí thiết kế xây dựng
CP5041  Chi phí thiết kế kỹ thuật
CP505   Chi phí thiết kế bản vẽ thi công
CP50530 Chi phí lập thiết kế bản vẽ thi công - dự toán
CP506   Chi phí lập nhiệm vụ khảo sát xây dựng
CP507   Chi phí thẩm tra báo cáo kinh tế - kỹ thuật
CP508   Chi phí thẩm tra báo cáo nghiên cứu khả thi
CP509   Chi phí thẩm tra thiết kế xây dựng
CP510   Chi phí thẩm tra dự toán xây dựng
CP511   Chi phí lập hồ sơ mời thầu, đánh giá hồ sơ dự thầu tư vấn
CP512   Chi phí lập hồ sơ mời thầu tư vấn
CP513   Chi phí đánh giá hồ sơ dự thầu tư vấn
CP514   Chi phí lập hồ sơ mời thầu, đánh giá hồ sơ dự thầu thi công xây dựng
CP515   Chi phí lập hồ sơ mời thầu thi công xây dựng
CP516   Chi phí đánh giá hồ sơ dự thầu thi công xây dựng
CP517   Chi phí lập hồ sơ mời thầu, đánh giá hồ sơ dự thầu mua sắm vật tư, thiết bị
CP518   Chi phí lập hồ sơ mời thầu mua sắm vật tư, thiết bị
CP519   Chi phí đánh giá hồ sơ dự thầu mua sắm vật tư, thiết bị
CP520   Chi phí giám sát thi công xây dựng
CP521   Chi phí giám sát lắp đặt thiết bị
CP522   Chi phí giám sát công tác khảo sát xây dựng
CP523   Chi phí quy đổi vốn đầu tư xây dựng
CP526   Phí thẩm định hồ sơ mời thầu
CP527   Chi phí thẩm tra báo cáo nghiên cứu tiền khả thi
CP528   Chi phí khảo sát xây dựng
CP532   Phí thẩm định hồ sơ mời thầu gói thầu thi công xây dựng
CP533   Phí thẩm định hồ sơ mời thầu gói thầu lắp đặt thiết bị
CP534   Phí thẩm định hồ sơ mời thầu gói thầu tư vấn đầu tư xây dựng
CP535   Phí thẩm định kết quả lựa chọn nhà thầu thi công xây dựng
CP536   Phí thẩm định kết quả lựa chọn nhà thầu lắp đặt thiết bị
CP537   Phí thẩm định kết quả lựa chọn nhà thầu tư vấn đầu tư xây dựng
CP538   Phí thẩm định hồ sơ mời thầu, đánh giá kết quả lựa chọn nhà thầu xây lắp
CP539   Phí thẩm định hồ sơ mời thầu, đánh giá kết quả lựa chọn nhà thầu lắp đặt thiết bị
CP540   Phí thẩm định hồ sơ mời thầu, đánh giá kết quả lựa chọn nhà thầu tư vấn đầu tư xây dựng
CP541   Phí thẩm định hồ sơ mời thầu, đánh giá kết quả lựa chọn nhà thầu
CP551   Chi phí khảo sát, thiết kế BVTC - DT
CP552   Chi phí nhiệm vụ thử tỉnh cọc
CP553   Công tác điều tra, đo đạt và thu thập số liệu
CP554   Chi phí kiểm tra và chứng nhận sự phù hợp về chất lượng công trình xây dựng
CP556   Chi phí thẩm tra an toàn giao thông
CP557   Chi phí thử tĩnh
CP558   Chi phí công bố quy hoạch
CP559   Chi phí thử tải cừ tràm
CP560   Chi phí kiểm định chất lượng phục vụ công tác nghiệm thu
CP561   Chi phí cắm mốc ranh giải phóng mặt bằng
CP562   Chi phí lập đồ án quy hoạch
CP56201 Chi phí khảo sát địa chất
CP563   Chi phí thẩm tra tính hiệu quả, tính khả thi của dự án
CP56301 Chi phí khảo sát địa hình
CP564   Tư vấn lập văn kiện dự án và các báo cáo thành phần của dự án
CP56401 Chi phí khảo sát địa, địa hình
CP565   Chi phí lập kế hoạch bảo vệ môi trường
CP566   Chi phí lập báo cáo đánh giá tác động môi trường
CP567   Chi phí thí nghiệm chuyên ngành xây dựng
CP568   Chi phí chuẩn bị đầu tư ban đầu sáng tác thi tuyển mẫu phác thảo bước 1
CP569   Chi phí chỉ đạo thể hiện phần mỹ thuật
CP570   Chi phí nội đồng nghệ thuật
CP571   Chi phí sáng tác mẫu phác thảo tượng đài
CP572   Chi phí hoạt động của Hội đồng nghệ thuật
CP57301 Chi phí kiểm định theo yêu cầu chủ đầu tư
CP574   Chi phí tư vấn thẩm tra dự toán
CP575   Chi phí thẩm định dự toán giá gói thầu
CP577   Chi phí lập hồ sơ điều chỉnh dự toán
CP578   Chi phí chuyển giao công nghệ
CP579   Chi phí thẩm định giá
CP580   Chi phí tư vấn giám sát
CP58001 Chi phí tư vấn giám sát di dời điện
CP58002 Chi phí tư vấn giám sát di dời cáp quang
CP58003 Chi phí tư vấn giám sát di dời đường ống nước
CP58004 Chi phí tư vấn giám sát khảo sát địa chất
CP58005 Chi phí tư vấn giám sát khảo sát địa hình
CP58006 Chi phí tư vấn giám sát khảo sát và cắm mốc
CP58007 Chi phí tư vấn giám sát khoan địa chất
CP58008 Chi phí tư vấn giám sát rà phá bom mìn, vật nổ
CP58009 Chi phí tư vấn giám sát, đánh giá đầu tư
CP581   Chi phí báo cáo giám sát đánh giá đầu tư
CP582   Chi phí thẩm tra thiết kế BVTC-DT
CP58220 Chi phí thẩm tra thiết kế BVTC
CP583   Tư vấn đầu tư xây dựng
CP584   Chi phí đăng báo đấu thầu
CP599   Chi phí đo đạc thu hồi đất
CP6 Chi phí khác
CP601   Phí thẩm định dự án đầu tư xây dựng
CP602   Phí thẩm định dự toán xây dựng
CP603   Chi phí rà phá bom mìn, vật nổ
CP604   Phí thẩm định phê duyệt thiết kế về phòng cháy và chữa cháy
CP605   Chi phí thẩm định giá thiết bị
CP606   Phí thẩm định thiết kế xây dựng triển khai sau thiết kế cơ sở
CP607   Chi phí thẩm tra, phê duyệt quyết toán
CP608   Chi phí kiểm tra công tác nghiệm thu
CP609   Chi phí kiểm toán độc lập
CP60902 Chi phí kiểm toán công trình
CP610   Chi phí bảo hiểm
CP611   Chi phí thẩm định báo cáo đánh giá tác động môi trường
CP612   Chi phí bảo hành, bảo trì
CP613   Phí bảo vệ môi trường
CP614   Chi phí di dời điện
CP61401 Chi phí di dời hệ thống điện chiếu sáng
CP61402 Chi phí di dời đường dây hạ thế
CP61403 Chi phí di dời nhà
CP61404 Chi phí di dời nước
CP61405 Chi phí di dời trụ điện trong trường
CP615   Phí thẩm tra di dời điện
CP617   Chi phí đo đạc địa chính
CP61701 Chi phí đo đạc bản đồ địa chính
CP61702 Chi phí đo đạc lập bản đồ địa chính GPMB
CP61703 Chi phí đo đạc, đền bù GPMB
CP61704 Chi phí đo đạc thu hồi đất
CP61820 Chi phí tổ chức kiểm tra công tác nghiệm thu
CP619   Chi phí lán trại
CP620   Chi phí đảm bảo giao thông
CP621   Chi phí điều tiết giao thông
CP62101 Chi phí điều tiết giao thông khác
CP622   Chi phí một số công tác không xác định số lượng từ thiết kế
CP623   Chi phí thẩm định thiết kế bản vẽ thi công
CP624   Chi phí nhà tạm
CP62501 Chi phí giám sát đánh giá đầu tư
CP626   Chi phí thẩm định kết quả lựa chọn nhà thầu
CP62701 Chi phí khoan địa chất
CP628   Chi phí thẩm định đồ án quy hoạch
CP629   Chi phí thẩm định HSMT, HSYC
CP630   Lệ phí thẩm tra thiết kế
CP631   Phí thẩm định lựa chọn nhà thầu
CP632   Chi phí thẩm tra quyết toán
CP633   Chi phí thẩm định phê duyệt quyết toán
CP634   Chi phí thẩm định báo cáo nghiên cứu khả thi
CP699   Chi phí khác
CP7 Chi phí dự phòng
CP702   Chi phí dự phòng cho yếu tố trược giá

### Yêu cầu nhiệm vụ:
1. Tìm kiếm trong danh sách chi phí chuẩn (gồm cả tên nhóm và tên con chi tiết) mục có ý nghĩa tương đồng cao nhất với từng dòng chi phí trên.
2. Kết quả đầu ra chuỗi json duy nhất với các trường thông tin
- STT: STT của bảng DuLieuChiTiet
- TenKMCP: Tên khoản mục gốc trước khi ánh xạ
- TenKMCP_Moi: Tên khoản mục sau khi ánh xạ
- MaKMCP: Mã KMCP dược ánh xạ giữa 2 bảng
- GhiChu: Giải thích vì sao lại ánh xạ như vậy (trong ghi chú không chứa ký tự đặc biệt)
**ĐIỀU KIỆN BẮT BUỘC:**
- Chỉ chọn một MaKMCP có ý nghĩa gần nhất và phù hợp nhất cho mỗi khoản mục
- Không được chọn nhiều hơn một mã KMCP cho một dòng
- Không được suy diễn vượt quá ý nghĩa của cụm từ gốc
- Ưu tiên nhóm chính trước, nếu không khớp thì tìm trong nhóm con
- Các trường thông tin trong json KHÔNG gán ký tự đặc biệt
"""
        
        # Gọi OpenAI API để xử lý
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        response = client.chat.completions.create(
            model=model_openai,
            messages=[
                {
                    "role": "system",
                    "content": """Bạn là một trợ lý AI chuyên nghiệp trong việc ánh xạ và phân loại thông tin.
                    Kết quả trả về PHẢI là một JSON"""
                },
                {
                    "role": "user",
                    "content": promt_anh_xa_noi_dung_tuong_dong
                }
            ],
            temperature=0,
            #response_format={"type": "json_object"},
            seed=42  # Thêm seed để đảm bảo tính nhất quán
        )
        #print(promt_anh_xa_noi_dung_tuong_dong)
        try:
            # Xử lý response từ OpenAI
            response_text = response.choices[0].message.content
            if response_text.strip().startswith("```json"):
                response_text = response_text.strip()[7:-3].strip()
            elif response_text.strip().startswith("```"):
                response_text = response_text.strip()[3:-3].strip()
            #print(response_text)
            # Phân tích chuỗi JSON thành một đối tượng Python (dictionary)
            dataJson = json.loads(response_text)

            # Lấy ra list từ key "results"
            result_list = dataJson
            # print("result_list>>>>>>>>")
            # print(result_list)
            # Chuyển đổi list trở lại thành chuỗi JSON
            new_response_text = json.dumps(result_list, indent=4, ensure_ascii=False)
            #print(new_response_text)
            # Chuyển đổi response thành DataFrame
            dfBangDuLieuChiTietAI = pd.read_json(new_response_text)
            # print("\nDữ liệu BangDuLieuChiTietAI:")
            # print("=" * 80)
            # for index, row in dfBangDuLieuChiTietAI.iterrows():
            #     print(f"\nDòng {index + 1}:")
            #     for column in dfBangDuLieuChiTietAI.columns:
            #         print(f"{column}: {row[column]}")
            #     print("-" * 40)
            # print("=" * 80)
            # Thực hiện cập nhật dữ liệu vào database
            for index, row in dfBangDuLieuChiTietAI.iterrows():
                query_insert = "Update dbo.BangDuLieuChiTietAi set TenKMCP_AI=N'{}', KMCPID=(select top 1 KMCPID from dbo.KMCP Km where replace(Km.MaKMCP, '.', '')=replace(N'{}', '.', '')), GhiChuAI=N'{}' where STT=N'{}'".format(
                    row['TenKMCP_Moi'],
                    row['MaKMCP'].replace("'", ""),
                    row['GhiChu'].replace("'", ""),
                    row['STT']
                )

                print(f"Executing SQL query: {query_insert}")
                thuc_thi_truy_van(query_insert)
                
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "code": 500,
                    "message": "Lỗi khi xử lý kết quả ánh xạ từ AI",
                    "detail": str(e)
                }
            )
        # print("\nDữ liệu VanBanAI:")
        # print("=" * 80)
        # for index, row in dfVanBanAI.iterrows():
        #     print(f"\nDòng {index + 1}:")
        #     for column in dfVanBanAI.columns:
        #         print(f"{column}: {row[column]}")
        #     print("-" * 40)
        # print("=" * 80)
        if not dfVanBanAI.empty:
            for index, row in dfVanBanAI.iterrows():
                van_ban_id = row['VanBanAIID']
                ten_loai_van_ban = row['TenLoaiVanBan']
                query_bangct = f"select BangDuLieuChiTietAIID=convert(nvarchar(36), BangDuLieuChiTietAIID), KMCPID=convert(nvarchar(36), KMCPID), TenKMCP_AI from dbo.BangDuLieuChiTietAI where VanBanAIID='{van_ban_id}'"
                df_bang_ct = lay_du_lieu_tu_sql_server(query_bangct)
                # Xử lý thêm dữ liệu vào NTsoftDocumentAI
                # print("=================ten_loai_van_ban===============")
                # print(ten_loai_van_ban)

                # Xử lý LayMaDoiTuong -> Cho Cơ quan ban hành
                ten_toi_tuong = row['CoQuanBanHanh']
                la_ca_nhan = "0"
                doi_tuong_id = LayMaDoiTuong(don_vi_id, user_id, ten_toi_tuong, la_ca_nhan)
                try:
                    query_update_doi_tuong = f"update dbo.VanBanAI set DoiTuongID_ToChuc=N'{doi_tuong_id}' where VanBanAIID=N'{van_ban_id}'"
                    thuc_thi_truy_van(query_update_doi_tuong)
                except Exception as e:
                    print(f"Lỗi khi cập nhật DoiTuongID_ToChuc: {str(e)}")
                # Xử lý LayMaDoiTuong -> Cho Người ký
                ten_toi_tuong = row['NguoiKy']
                la_ca_nhan = "1"
                doi_tuong_id = LayMaDoiTuong(don_vi_id, user_id, ten_toi_tuong, la_ca_nhan)
                try:
                    query_update_doi_tuong = f"update dbo.VanBanAI set DoiTuongID_CaNhan=N'{doi_tuong_id}' where VanBanAIID=N'{van_ban_id}'"
                    thuc_thi_truy_van(query_update_doi_tuong)
                except Exception as e:
                    print(f"Lỗi khi cập nhật DoiTuongID_CaNhan: {str(e)}")

                if f"[{ten_loai_van_ban}]" in "[QDPD_CT];[QDPD_DA]":    
                    if not df_bang_ct.empty:
                        for _, row2 in df_bang_ct.iterrows():
                            query_insert = f"""
                            delete from dbo.NTSoftDocumentAI where BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}'
                            ----------
                            insert into dbo.NTSoftDocumentAI (BangDuLieuChiTietAIID, TongMucDauTuKMCPID, KMCPID,CoCauVonID,VanBanAIID,TenKMCP,GiaTriTMDTKMCP,GiaTriTMDTKMCP_DC,GiaTriTMDTKMCPTang,GiaTriTMDTKMCPGiam,TongMucDauTuKMCPID_goc)
                            select 
                              BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}', TongMucDauTuKMCPID=newid()
                            , KMCPID=N'{row2['KMCPID']}'
                            , CoCauVonID=(select CoCauVonID from dbo.KMCP km where km.KMCPID=N'{row2['KMCPID']}')
                            , N'{van_ban_id}'
                            , TenKMCP=N'{row2['TenKMCP_AI']}'
                            , GiaTriTMDTKMCP=(select GiaTriTMDTKMCP from dbo.BangDuLieuChiTietAI ai where ai.BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}')
                            , GiaTriTMDTKMCP_DC=(select GiaTriTMDTKMCP_DC from dbo.BangDuLieuChiTietAI ai where ai.BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}')
                            , GiaTriTMDTKMCPTang=(select GiaTriTMDTKMCPTang from dbo.BangDuLieuChiTietAI ai where ai.BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}')
                            , GiaTriTMDTKMCPGiam=(select GiaTriTMDTKMCPGiam from dbo.BangDuLieuChiTietAI ai where ai.BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}')
                            , TongMucDauTuKMCPID_goc='00000000-0000-0000-0000-000000000000'
                            ---------- Cập nhật giá trị văn bản
                            update dbo.VanBanAI 
                            set 
                            GiaTri = (select GiaTriTMDTKMCP=isnull(sum(GiaTriTMDTKMCP), 0) from dbo.BangDuLieuChiTietAI ai where ai.VanBanAIID='{van_ban_id}') 
                            where VanBanAIID='{van_ban_id}'
                            """
                            #print(f"Executing SQL query: {query_insert}")
                            if thuc_thi_truy_van(query_insert) == False:
                                print(f"Executing SQL query: {query_insert}")
                if f"[{ten_loai_van_ban}]" in "[QDPDDT_CBDT];[QDPD_DT_THDT]":    
                    if not df_bang_ct.empty:
                        for _, row2 in df_bang_ct.iterrows():
                            query_insert = f"""
                            delete from dbo.NTSoftDocumentAI where BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}'
                            ----------
                            insert into dbo.NTSoftDocumentAI (BangDuLieuChiTietAIID, DuToanKMCPID, KMCPID,CoCauVonID,VanBanAIID,TenKMCP,GiaTriDuToanKMCP,GiaTriDuToanKMCP_DC,GiaTriDuToanKMCPTang,GiaTriDuToanKMCPGiam,TongMucDauTuKMCPID_goc)
                            select 
                              BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}', DuToanKMCPID=newid()
                            , KMCPID=N'{row2['KMCPID']}'
                            , CoCauVonID=(select CoCauVonID from dbo.KMCP km where km.KMCPID=N'{row2['KMCPID']}')
                            , N'{van_ban_id}'
                            , TenKMCP=N'{row2['TenKMCP_AI']}'
                            , GiaTriDuToanKMCP=(select GiaTriDuToanKMCP from dbo.BangDuLieuChiTietAI ai where ai.BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}')
                            , GiaTriDuToanKMCP_DC=(select GiaTriDuToanKMCP_DC from dbo.BangDuLieuChiTietAI ai where ai.BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}')
                            , GiaTriDuToanKMCPTang=(select GiaTriDuToanKMCPTang from dbo.BangDuLieuChiTietAI ai where ai.BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}')
                            , GiaTriDuToanKMCPGiam=(select GiaTriDuToanKMCPGiam from dbo.BangDuLieuChiTietAI ai where ai.BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}')
                            , TongMucDauTuKMCPID_goc='00000000-0000-0000-0000-000000000000'
                            """
                            print(f"Executing SQL query: {query_insert}")
                            thuc_thi_truy_van(query_insert)

                if f"[{ten_loai_van_ban}]" in "[QDPD_KHLCNT_CBDT];[QDPD_KHLCNT_THDT]": # sử dụng cho 2 giai đoạn CB và TH
                    if not df_bang_ct.empty:
                        for _, row2 in df_bang_ct.iterrows():
                            query_insert = f"""
                            delete from dbo.NTSoftDocumentAI where BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}'
                            ----------
                            insert into dbo.NTSoftDocumentAI(BangDuLieuChiTietAIID,VanBanAIID, TenKMCP, DauThauID, DauThauCTID,TenDauThau, GiaTriGoiThau, TenNguonVon, CoCauVonID
                                ,LoaiGoiThauID,HinhThucDThID,PhuongThucDThID,LoaiHopDongID,ThoiGianToChuc,KeHoachThoiGianHopDong)
                            SELECT
                            BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}', N'{van_ban_id}', TenKMCP=N'{row2['TenKMCP_AI']}', DauThauID=newid(),
                            DauThauCTID=newid(),
                            TenDauThau,
                            GiaTriGoiThau,
                            TenNguonVon,
                            CoCauVonID=(select CoCauVonID from dbo.KMCP km where km.KMCPID=N'{row2['KMCPID']}'),
                            LoaiGoiThauID=NULL, -- chưa xử lý
                            HinhThucDThID=NULL, -- chưa xử lý
                            PhuongThucDThID=NULL, -- chưa xử lý
                            LoaiHopDongID=NULL, -- chưa xử lý
                            ThoiGianToChuc=ThoiGianTCLCNT, -- chưa xử lý
                            KeHoachThoiGianHopDong=ThoiGianTHHopDong
                            FROM BangDuLieuChiTietAI ai where BangDuLieuChiTietAIID='{row2['BangDuLieuChiTietAIID']}'
                            """
                            print(f"Executing SQL query: {query_insert}")
                            thuc_thi_truy_van(query_insert)
                if f"[{ten_loai_van_ban}]" in "[QDPD_KQLCNT_CBDT];[QDPD_KQLCNT_THDT]": # sử dụng cho 2 giai đoạn CB và TH
                    if not df_bang_ct.empty:
                        for _, row2 in df_bang_ct.iterrows():
                            query_insert = f"""
                            delete from dbo.NTSoftDocumentAI where BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}'
                            ----------
                            insert into dbo.NTSoftDocumentAI(BangDuLieuChiTietAIID,VanBanAIID,TenKMCP,TenDauThau,KeHoachThoiGianHopDong,LoaiHopDongID,GiaTrungThau, CoCauVonID)
                            SELECT
                            BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}', N'{van_ban_id}', TenKMCP=N'{row2['TenKMCP_AI']}',TenDauThau,
                            KeHoachThoiGianHopDong=ThoiGianTHHopDong,
                            LoaiHopDongID=NULL, -- chưa xử lý
                            GiaTrungThau, 
                            CoCauVonID=(select CoCauVonID from dbo.KMCP km where km.KMCPID=N'{row2['KMCPID']}')
                            FROM BangDuLieuChiTietAI ai where BangDuLieuChiTietAIID='{row2['BangDuLieuChiTietAIID']}'
                            """
                            print(f"Executing SQL query: {query_insert}")
                            thuc_thi_truy_van(query_insert)
                if f"[{ten_loai_van_ban}]" in "[HOP_DONG]": # Hợp đồng mặc định là giai đoạn thực hiện
                    if not df_bang_ct.empty:
                        for _, row2 in df_bang_ct.iterrows():
                            query_insert = f"""
                            delete from dbo.NTSoftDocumentAI where BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}'
                            ----------
                            insert into dbo.NTSoftDocumentAI(BangDuLieuChiTietAIID, VanBanAIID, TenKMCP, HopDongCTID, DauThauCTID,GiaTriHopDong,CoCauVonID
                                ,GiaTriHopDongTang,GiaTriHopDongGiam,DuToanKMCPID,KMCPID)
                            SELECT
                            BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}', N'{van_ban_id}', TenKMCP=N'{row2['TenKMCP_AI']}',HopDongCTID=newid(),
                            DauThauCTID=NULL, -- khoá ngoại chưa xử lý
                            GiaTriHopDong,
                            CoCauVonID=(select CoCauVonID from dbo.KMCP km where km.KMCPID=N'{row2['KMCPID']}'),
                            GiaTriHopDongTang, -- khoá ngoại chưa xử lý
                            GiaTriHopDongGiam, -- khoá ngoại chưa xử lý
                            DuToanKMCPID=NULL, -- khoá ngoại chưa xử lý
                            KMCPID -- chưa xử lý
                            FROM BangDuLieuChiTietAI ai where BangDuLieuChiTietAIID='{row2['BangDuLieuChiTietAIID']}'
                            """
                            print(f"Executing SQL query: {query_insert}")
                            thuc_thi_truy_van(query_insert)
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "code": 200,
                "message": "Đã làm đẹp dữ liệu văn bản",
                "detail": ""
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

@router.post("/image_extract_multi_azure_gemini")
async def extract_multiple_images_azure_gemini(
    files: List[UploadFile] = File(...)
):
    # Load require_fields from JSON file
    try:
        with open('data/require_fields.json', 'r', encoding='utf-8') as f:
            require_fields = json.load(f)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "code": 500,
                "message": "Lỗi đọc file require_fields.json",
                "detail": str(e)
            }
        )

    # Print raw file data
    print("\n=== Raw File Data ===")
    for file in files:
        print(f"\nFile: {file.filename}")
        print(f"Content Type: {file.content_type}")
        content = await file.read()
        print(f"Size: {len(content)} bytes")
        await file.seek(0)  # Reset file pointer
    print("\n=== End Raw File Data ===\n")

    # Initialize combined data
    combined_data = {}
        
    # Process each file
    for file in files:
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
                content = await file.read()
                temp_file.write(content)
                temp_file.flush()

                # Initialize the client
                endpoint = os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT")
                key = os.getenv("AZURE_FORM_RECOGNIZER_KEY")
                document_analysis_client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))

                # Start the document analysis
                with open(temp_file.name, "rb") as f:
                    poller = document_analysis_client.begin_analyze_document(
                        "prebuilt-layout", document=f
                    )
                result = poller.result()

                # Print OCR text content
                print("\n=== Azure Form Recognizer OCR Text ===")
                print(f"\nDocument: {temp_file.name}")
                
                # Collect all text content
                full_text = ""
                for page in result.pages:
                    full_text += f"\nPage {page.page_number}:\n"
                    for line in page.lines:
                        full_text += line.content + "\n"
                
                print(full_text)
                print("\n=== End OCR Text ===\n")

                # Use Gemini to map text to required fields
                try:
                    # Prepare the prompt for Gemini
                    prompt = f"""
                    Extract and map information from the following OCR text to the specified fields.
                    Return ONLY a JSON object with the following structure:
                    {{
                        "docId": "string or null",
                        "arcDocCode": "string or null",
                        "maintenance": "string or null",
                        "typeName": "string or null",
                        "codeNumber": "string or null",
                        "codeNotation": "string or null",
                        "issuedDate": "string or null",
                        "organName": "string or null",
                        "subject": "string or null",
                        "language": "string or null",
                        "numberOfPage": "string or null",
                        "inforSign": "string or null",
                        "keyword": "string or null",
                        "mode": "string or null",
                        "confidenceLevel": "string or null",
                        "autograph": "string or null",
                        "format": "string or null",
                        "process": "string or null",
                        "riskRecovery": "string or null",
                        "riskRecoveryStatus": "string or null",
                        "description": "string or null",
                        "SignerTitle": "string or null",
                        "SignerName": "string or null"
                    }}

                    Field definitions and extraction rules:
                    {json.dumps(require_fields, ensure_ascii=False, indent=2)}

                    General rules:
                    1. Look for information based on the extraction rules specified in the field definition
                    2. Pay attention to the location hints in the rules
                    3. Use the provided keywords to identify relevant information
                    4. Follow the specified format requirements
                    5. Use the mapping tables when provided
                    6. Use default values when specified
                    7. Set to null if information cannot be found
                    8. For dates, use DD/MM/YYYY format
                    9. For numbers, remove thousand separators

                    OCR Text:
                    {full_text}

                    Remember: Return ONLY the JSON object, no other text or explanation.
                    """

                    # Call Gemini API
                    response = model.generate_content(prompt)
                    response_text = response.text.strip()

                    print("\n=== Mapped Fields ===")
                    print(response_text)
                    print("=== End Mapped Fields ===\n")

                    try:
                        # Clean up response text
                        if response_text.strip().startswith("```json"):
                            response_text = response_text.strip()[7:-3].strip()
                        elif response_text.strip().startswith("```"):
                            response_text = response_text.strip()[3:-3].strip()

                        # Parse the response
                        mapped_data = json.loads(response_text)
                        
                        # Validate required fields
                        required_fields_list = [field["tenTruong"] for field in require_fields]
                        for field in required_fields_list:
                            if field not in mapped_data:
                                mapped_data[field] = None
                        
                        # Update combined data with mapped fields
                        for field, value in mapped_data.items():
                            if field not in combined_data or combined_data[field] is None:
                                combined_data[field] = value
                            elif value is not None:
                                combined_data[field] = value

                    except json.JSONDecodeError as e:
                        print(f"Error parsing JSON response: {str(e)}")
                        print(f"Raw response: {response_text}")
                        raise Exception("Invalid JSON response from Gemini")

                except Exception as e:
                    print(f"Error in Gemini mapping: {str(e)}")

        except Exception as e:
            print(f"Error processing file {file.filename}: {str(e)}")

    # Return combined data
    return {
        "status": "success",
        "data": combined_data
    }

@router.post("/document_extract")
async def extract_document(
    files: List[UploadFile] = File(...),
    file_type: str = Form(...),  # 'image' or 'pdf'
    pages: Optional[str] = Form(None)  # Comma-separated list of page numbers for PDF
):
    """
    Extract information from documents (images or PDFs) using OpenAI
    
    Parameters:
    - files: List of uploaded files (images or a single PDF)
    - file_type: Type of document ('image' or 'pdf')
    - pages: For PDF files, specify which pages to process (comma-separated numbers)
    """
    # Validate file type
    if file_type not in ['image', 'pdf']:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "code": 400,
                "message": "Invalid file type",
                "detail": "file_type must be either 'image' or 'pdf'"
            }
        )

    # Validate files based on type
    if file_type == 'image':
        for file in files:
            if file.content_type not in ALLOWED_IMAGE_TYPES:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "code": 400,
                        "message": f"Invalid file type for {file.filename}",
                        "detail": f"Expected image file, got {file.content_type}"
                    }
                )
    else:  # PDF
        if len(files) > 1:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "code": 400,
                    "message": "Only one PDF file can be uploaded at a time",
                    "detail": "Multiple files are only allowed for images"
                }
            )
        if files[0].content_type != ALLOWED_PDF_TYPE:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "code": 400,
                    "message": "Invalid file type",
                    "detail": "Expected PDF file"
                }
            )

    # Parse pages parameter for PDF
    selected_pages = None
    if file_type == 'pdf' and pages:
        try:
            selected_pages = [int(p.strip()) for p in pages.split(',')]
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "code": 400,
                    "message": "Invalid pages parameter",
                    "detail": "Pages must be comma-separated numbers"
                }
            )

    # Load require_fields from Markdown file
    try:
        with open('data/require_fields.md', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Parse markdown content to extract field information
        require_fields = []
        current_field = None
        
        for line in content.split('\n'):
            if line.startswith('## '):
                if current_field:
                    require_fields.append(current_field)
                field_name = line.split('. ')[1].strip()
                current_field = {
                    "tenTruong": field_name,
                    "moTa": "",
                    "extractionRules": {}
                }
            elif line.startswith('**Mô tả:**'):
                if current_field:
                    current_field["moTa"] = line.replace('**Mô tả:**', '').strip()
            elif line.startswith('**Quy tắc trích xuất:**'):
                continue
            elif line.startswith('- **'):
                if current_field:
                    key = line.split('**')[1].replace(':**', '').strip()
                    value = line.split(':**')[1].strip()
                    current_field["extractionRules"][key] = value
            elif '| Mã | Giá trị |' in line:
                if current_field:
                    mapping = {}
                    continue
            elif line.startswith('  | '):
                if current_field and 'mapping' not in current_field["extractionRules"]:
                    current_field["extractionRules"]["mapping"] = {}
                parts = line.strip().split('|')
                if len(parts) >= 3:
                    code = parts[1].strip()
                    value = parts[2].strip()
                    current_field["extractionRules"]["mapping"][code] = value
                    
        if current_field:
            require_fields.append(current_field)
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "code": 500,
                "message": "Lỗi đọc file require_fields.md",
                "detail": str(e)
            }
        )

    # Initialize combined data
    combined_data = {}

    try:
        if file_type == 'image':
            # Process each image file
            for file in files:
                await process_image_file(file, require_fields, combined_data)
        else:
            # Process PDF file
            await process_pdf_file(files[0], selected_pages, require_fields, combined_data)

        return {
            "status": "success",
            "data": combined_data
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "code": 500,
                "message": "Error processing document",
                "detail": str(e)
            }
        )

async def process_image_file(file: UploadFile, require_fields: List[Dict], combined_data: Dict):
    """Process a single image file"""
    try:
        # Read file content
        content = await file.read()
        
        # Convert image to base64
        image_base64 = base64.b64encode(content).decode('utf-8')
        
        # Process with OpenAI
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI assistant that extracts information from documents. You MUST return a valid JSON object containing the mapped fields. Do not include any other text or explanation in your response."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"""
                            Extract and map information from the following image to the specified fields.
                            Return ONLY a JSON object with the following structure:
                            {{
                                "docId": "string or null",
                                "arcDocCode": "string or null",
                                "maintenance": "string or null",
                                "typeName": "string or null",
                                "codeNumber": "string or null",
                                "codeNotation": "string or null",
                                "issuedDate": "string or null",
                                "organName": "string or null",
                                "subject": "string or null",
                                "language": "string or null",
                                "numberOfPage": "string or null",
                                "inforSign": "string or null",
                                "keyword": "string or null",
                                "mode": "string or null",
                                "confidenceLevel": "string or null",
                                "autograph": "string or null",
                                "format": "string or null",
                                "process": "string or null",
                                "riskRecovery": "string or null",
                                "riskRecoveryStatus": "string or null",
                                "description": "string or null",
                                "SignerTitle": "string or null",
                                "SignerName": "string or null"
                            }}

                            Field definitions and extraction rules:
                            {json.dumps(require_fields, ensure_ascii=False, indent=2)}
                            """
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=4000,
            temperature=0,  # Set temperature to 0 for more consistent output
            response_format={"type": "json_object"}  # Force JSON response
        )

        # Parse response
        response_text = response.choices[0].message.content
        
        # Clean up response text
        if response_text.strip().startswith("```json"):
            response_text = response_text.strip()[7:-3].strip()
        elif response_text.strip().startswith("```"):
            response_text = response_text.strip()[3:-3].strip()

        # Parse JSON response
        data = json.loads(response_text)
        
        # Update combined data
        for key, value in data.items():
            if key not in combined_data or not combined_data[key]:
                combined_data[key] = value

    except Exception as e:
        raise Exception(f"Error processing image file {file.filename}: {str(e)}")

async def process_pdf_file(file: UploadFile, selected_pages: Optional[List[int]], require_fields: List[Dict], combined_data: Dict):
    """Process a PDF file"""
    temp_file_path = None
    doc = None
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()
            temp_file_path = temp_file.name

        # Read PDF pages
        doc = fitz.open(temp_file_path)
        total_pages = len(doc)

        if selected_pages is None:
            selected_pages = list(range(1, total_pages + 1))

        # Process each selected page
        for page_num in selected_pages:
            if 1 <= page_num <= total_pages:
                page = doc.load_page(page_num - 1)
                
                # Convert page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72), alpha=False)
                img = Image.frombuffer("RGB", [pix.width, pix.height], pix.samples, "raw", "RGB", 0, 1)
                
                # Convert image to base64
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                image_base64 = base64.b64encode(buffered.getvalue()).decode()

                # Process with OpenAI
                client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an AI assistant that extracts information from documents. You MUST return a valid JSON object containing the mapped fields. Do not include any other text or explanation in your response."
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"""
                                    Extract and map information from the following PDF page to the specified fields.
                                    Return ONLY a JSON object with the following structure:
                                    {{
                                        "docId": "string or null",
                                        "arcDocCode": "string or null",
                                        "maintenance": "string or null",
                                        "typeName": "string or null",
                                        "codeNumber": "string or null",
                                        "codeNotation": "string or null",
                                        "issuedDate": "string or null",
                                        "organName": "string or null",
                                        "subject": "string or null",
                                        "language": "string or null",
                                        "numberOfPage": "string or null",
                                        "inforSign": "string or null",
                                        "keyword": "string or null",
                                        "mode": "string or null",
                                        "confidenceLevel": "string or null",
                                        "autograph": "string or null",
                                        "format": "string or null",
                                        "process": "string or null",
                                        "riskRecovery": "string or null",
                                        "riskRecoveryStatus": "string or null",
                                        "description": "string or null",
                                        "SignerTitle": "string or null",
                                        "SignerName": "string or null"
                                    }}

                                    Field definitions and extraction rules:
                                    {json.dumps(require_fields, ensure_ascii=False, indent=2)}
                                    """
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{image_base64}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=4000,
                    temperature=0,  # Set temperature to 0 for more consistent output
                    response_format={"type": "json_object"}  # Force JSON response
                )

                # Parse response
                response_text = response.choices[0].message.content
                
                # Clean up response text
                if response_text.strip().startswith("```json"):
                    response_text = response_text.strip()[7:-3].strip()
                elif response_text.strip().startswith("```"):
                    response_text = response_text.strip()[3:-3].strip()

                # Parse JSON response
                data = json.loads(response_text)
                
                # Update combined data
                for key, value in data.items():
                    if key not in combined_data or not combined_data[key]:
                        combined_data[key] = value

    except Exception as e:
        raise Exception(f"Error processing PDF file {file.filename}: {str(e)}")
    finally:
        # Close the PDF document if it's open
        if doc:
            doc.close()
        
        # Delete the temporary file if it exists
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                print(f"Warning: Could not delete temporary file {temp_file_path}: {str(e)}")

