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
from app.services.DungChung import convert_currency_to_int, lay_du_lieu_tu_sql_server, thuc_thi_truy_van, decode_jwt_token, LayMaDoiTuong
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

#MÔ HÌNH OPENAI
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
                max_tokens=4000  # Tăng max_tokens nếu cần cho kết quả dài hơn
            )
            print("\n=== Thông tin client ===")
            print(f"Model: {response.model}")
            print(f"ID: {response.id}")
            print(f"Created: {response.created}")
            print(f"Finish reason: {response.choices[0].finish_reason}")
            print(f"Usage - Prompt tokens: {response.usage.prompt_tokens}")
            print(f"Usage - Completion tokens: {response.usage.completion_tokens}")
            print(f"Usage - Total tokens: {response.usage.total_tokens}")
            print("=======================\n")
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

            # Gọi Gemini API
            # try:
            #     response = model.generate_content(content_parts)
            #     response_text = response.text.strip()
                
            #     if response_text.strip().startswith("```json"):
            #         response_text = response_text.strip()[7:-3].strip()
            #     elif response_text.strip().startswith("```"):
            #         response_text = response_text.strip()[3:-3].strip()
                
            #     print("\033[31mKẾT QUẢ NHẬN DẠNG HÌNH ẢNH\033[0m")
            #     print(response_text)
            # except Exception as e:
            #     return JSONResponse(
            #         status_code=500,
            #         content={
            #             "status": "error",
            #             "code": 500,
            #             "message": "Lỗi khi xử lý ảnh",
            #             "detail": str(e)
            #         }
            #     )
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
        query_kmcp = f"select distinct TenKMCP from dbo.BangDuLieuChiTietAI where isnull(TenKMCP, '')<>'' and VanBanAIID in (select VanBanAIID from dbo.VanBanAI vb where convert(nvarchar(36), DuAnID)='{duAnID}' and vb.TenLoaiVanBan in ('QDPD_CT', 'QDPDDT_CBDT', 'QDPD_DA', 'QDPD_DT_THDT'))"
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

        # Xử lý ghép TenKMCP trong chuoi_markdown_tenkmcp với TenKMCP trong bảng KMCP
        promt_anh_xa_noi_dung_tuong_dong = """
### Bạn là một chuyên gia về lĩnh vực Đầu tư xây dựng cơ bản. Hãy thực hiện ánh xạ nội dung công việc giữa các bảng `DuLieuCanGhep` với danh mục chi phí bảng `TableKMCP`
#### Bảng DuLieuCanGhep 
"""+chuoi_markdown_tenkmcp+"""
#### Bảng TableKMCP
| MaKMCP  | TenKMCP                                                                                                                     |
| ------- | --------------------------------------------------------------------------------------------------------------------------- |
| CP1     | Chi phí bồi thường, hỗ trợ, tái định cư                                                                                     |
| CP101   | Chi phí bồi thường về đất, nhà, công trình trên đất, các tài sản gắn liền với đất, trên mặt nước và chi phí bồi thường khác |
| CP102   | Chi phí các khoản hỗ trợ khi nhà nước thu hồi đất                                                                           |
| CP103   | Chi phí tái định cư                                                                                                         |
| CP104   | Chi phí tổ chức bồi thường, hỗ trợ và tái định cư                                                                           |
| CP105   | Chi phí sử dụng đất, thuê đất tính trong thời gian xây dựng                                                                 |
| CP106   | Chi phí di dời, hoàn trả cho phần hạ tầng kỹ thuật đã được đầu tư xây dựng phục vụ giải phóng mặt bằng                      |
| CP107   | Chi phí đầu tư vào đất                                                                                                      |
| CP199   | Chi phí khác có liên quan đến công tác bồi thường, hỗ trợ và tái định cư                                                    |
| CP2     | Chi phí xây dựng                                                                                                            |
| CP201   | Chi phí xây dựng phát sinh                                                                                                  |
| CP202   | Chi phí xây dựng công trình chính                                                                                           |
| CP203   | Chi phí xây dựng công trình chính và phụ                                                                                    |
| CP204   | Chi phí xây dựng điều chỉnh                                                                                                 |
| CP205   | Chi phí xây dựng trước thuế                                                                                                 |
| CP206   | Chi phí xây dựng sau thuế                                                                                                   |
| CP207   | Chi phí xây dựng công trình phụ                                                                                             |
| CP250   | Chi phí xây dựng khác                                                                                                       |
| CP3     | Chi phí thiết bị                                                                                                            |
| CP301   | Chi phí thiết bị phát sinh                                                                                                  |
| CP4     | Chi phí quản lý dự án                                                                                                       |
| CP401   | Chi phí quản lý dự án phát sinh                                                                                             |
| CP5     | Chi phí tư vấn đầu tư xây dựng                                                                                              |
| CP501   | Chi phí lập báo cáo nghiên cứu tiền khả thi                                                                                 |
| CP502   | Chi phí lập báo cáo nghiên cứu khả thi                                                                                      |
| CP503   | Chi phí lập báo cáo kinh tế - kỹ thuật                                                                                      |
| CP50301 | Chi phí lập dự án đầu tư                                                                                                    |
| CP504   | Chi phí thiết kế xây dựng                                                                                                   |
| CP5041  | Chi phí thiết kế kỹ thuật                                                                                                   |
| CP50411 | Chi phí thiết kế xây dựng (Phát sinh)                                                                                       |
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
| CP514   | Chi phí lập hồ sơ mời thầu (hồ sơ yêu cầu), đánh giá hồ sơ dự thầu (hồ sơ đề xuất) thi công xây dựng                        |
| CP51411 | Chi phí lập HSMT (HSYC), đánh giá HSDT (HSĐX) thi công xây dựng (Phát sinh)                                                 |
| CP515   | Chi phí lập hồ sơ mời thầu (hồ sơ yêu cầu) thi công xây dựng                                                                |
| CP51511 | Chi phí lập hồ sơ mời thầu (hồ sơ yêu cầu) thi công xây dựng (Phát sinh)                                                    |
| CP516   | Chi phí đánh giá hồ sơ dự thầu (hồ sơ đề xuất) thi công xây dựng                                                            |
| CP51611 | Chi phí đánh giá hồ sơ dự thầu (hồ sơ đề xuất) thi công xây dựng (Phát sinh)                                                |
| CP517   | Chi phí lập hồ sơ mời thầu (hồ sơ yêu cầu) , đánh giá hồ sơ dự thầu (hồ sơ đề xuất) mua sắm vật tư, thiết bị                |
| CP51711 | Chi phí lập HSMT (HSYC), đánh giá HSDT (HSĐX) mua sắm vật tư, thiết bị (Phát sinh)                                          |
| CP518   | Chi phí lập hồ sơ mời thầu (hồ sơ yêu cầu) mua sắm vật tư, thiết bị                                                         |
| CP51811 | Chi phí lập HSMT (HSYC) mua sắm vật tư, thiết bị (Phát sinh)                                                                |
| CP519   | Chi phí đánh giá hồ sơ dự thầu (hồ sơ đề xuất) mua sắm vật tư, thiết bị                                                     |
| CP51911 | Chi phí đánh giá HSDT mua sắm vật tư, thiết bị (Phát sinh)                                                                  |
| CP520   | Chi phí giám sát thi công xây dựng                                                                                          |
| CP52099 | Chi phí giám sát thi công xây dựng (Phát sinh)                                                                              |
| CP521   | Chi phí giám sát lắp đặt thiết bị                                                                                           |
| CP52111 | Chi phí giám sát lắp đặt thiết bị (Phát sinh)                                                                               |
| CP522   | Chi phí giám sát công tác khảo sát xây dựng                                                                                 |
| CP52211 | Chi phí giám sát công tác khảo sát xây dựng (Phát sinh)                                                                     |
| CP523   | Chi phí quy đổi vốn đầu tư xây dựng                                                                                         |
| CP526   | Phí thẩm định hồ sơ mời thầu (hồ sơ yêu cầu)                                                                                |
| CP527   | Chi phí thẩm tra báo cáo nghiên cứu tiền khả thi                                                                            |
| CP528   | Chi phí khảo sát xây dựng                                                                                                   |
| CP52802 | Chi phí khảo sát (Bước lập báo cáo nghiên cứu tiền khả thi (NCTKT))                                                         |
| CP52803 | Chi phí khảo sát (Bước lập báo cáo NCKT)                                                                                    |
| CP52804 | Chi phí khảo sát (Bước lập báo cáo KTKT)                                                                                    |
| CP52805 | Chi phí khảo sát (Bước lập TKBVTC)                                                                                          |
| CP52806 | Chi phí khảo sát (Bước lập TKBVTC-DT)                                                                                       |
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
| CP551   | Chi phí khảo sát, thiết kế BVTC - DT                                                                                        |
| CP552   | Chi phí nhiệm vụ thử tỉnh cọc                                                                                               |
| CP553   | Công tác điều tra, đo đạt và thu thập số liệu                                                                               |
| CP554   | Chi phí kiểm tra và chứng nhận sự phù hợp về chất lượng công trình xây dựng                                                 |
| CP556   | Chi phí thẩm tra an toàn giao thông                                                                                         |
| CP557   | Chi phí thử tĩnh                                                                                                            |
| CP558   | Chi phí công bố quy hoạch                                                                                                   |
| CP559   | Chi phí thử tải cừ tràm                                                                                                     |
| CP560   | Chi phí kiểm định chất lượng phục vụ công tác nghiệm thu                                                                    |
| CP561   | Chi phí cắm mốc ranh giải phóng mặt bằng                                                                                    |
| CP562   | Chi phí lập đồ án quy hoạch                                                                                                 |
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
| CP56304 | Chi phí khảo sát địa hình  (Bước lập báo cáo kinh tế kỹ thuật (KTKT))                                                       |
| CP56305 | Chi phí khảo sát địa hình  (Bước lập thiết kế bản vẽ thi công (BVTC))                                                       |
| CP56306 | Chi phí khảo sát địa hình  (Bước lập thiết kế bản vẽ thi công - dự toán (BVTC-DT))                                          |
| CP564   | Tư vấn lập văn kiện dự án và các báo cáo thành phần của dự án                                                               |
| CP56401 | Chi phí khảo sát địa, địa hình                                                                                              |
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
| CP58001 | Chi phí tư vấn giám sát di dời điện                                                                                         |
| CP58002 | Chi phí tư vấn giám sát di dời cáp quang                                                                                    |
| CP58003 | Chi phí tư vấn giám sát di dời đường ống nước                                                                               |
| CP58004 | Chi phí tư vấn giám sát khảo sát địa chất                                                                                   |
| CP58005 | Chi phí tư vấn giám sát khảo sát địa hình                                                                                   |
| CP58006 | Chi phí tư vấn giám sát khảo sát và cắm mốc                                                                                 |
| CP58007 | Chi phí tư vấn giám sát khoan địa chất                                                                                      |
| CP58008 | Chi phí tư vấn giám sát rà phá bom mìn, vật nổ                                                                              |
| CP58009 | Chi phí tư vấn giám sát, đánh giá đầu tư                                                                                    |
| CP581   | Chi phí báo cáo giám sát đánh giá đầu tư                                                                                    |
| CP582   | Chi phí thẩm tra thiết kế BVTC-DT                                                                                           |
| CP58211 | Chi phí thẩm tra thiết kế BVTC-DT (Phát sinh)                                                                               |
| CP58220 | Chi phí thẩm tra thiết kế BVTC                                                                                              |
| CP58231 | Chi phí thẩm tra thiết kế BVTC (Phát sinh)                                                                                  |
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
| CP617   | Chi phí đo đạc địa chính                                                                                                    |
| CP61701 | Chi phí đo đạc bản đồ địa chính                                                                                        |
| CP61702 | Chi phí đo đạc lập bản đồ địa chính GPMB                                                                                    |
| CP61703 | Chi phí đo đạc, đền bù GPMB                                                                                                 |
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

### Yêu cầu nhiệm vụ:
1. Suy luận thật kỹ và ghép TenKMCP trong bảng TableKMCP sang cột TenKMCP trong bảng DuLieuCanGhep, độ tương đồng khoảng 65% trở lên.
2. Kết quả đầu ra chuỗi json duy nhất với các trường thông tin
- TenKMCP: Tên khoản mục gốc trước khi ánh xạ
- TenKMCP_Moi: Tên khoản mục sau khi ánh xạ (Nếu "Không có thông tin để ánh xạ" thì gán rỗng "")
- MaKMCP: Mã KMCP dược ánh xạ giữa 2 bảng (Nếu "Không có thông tin để ánh xạ" thì gán rỗng "")
- GhiChu: Giải thích vì sao lại ánh xạ như vậy (ghi chú không chứa ký tự đặc biệt, chỉ chữ cái). Nếu "Không có thông tin để ánh xạ" thì gán "Không có thông tin"

**Lưu ý:**
- Nếu dữ liệu cột TenKMCP trong DuLieuCanGhep không đúng chính tả hãy sửa lại trước khi ánh xạ nội dung với bảng TableKMCP
- Dữ liệu 2 bảng phải có độ tương đồng về ngữ nghĩa hoặc ý nghĩa . Nếu không chắc chắc thì trả  "Không có thông tin"
- Các trường thông tin trong json (TenKMCP, TenKMCP_Moi, MaKMCP, GhiChu)  KHÔNG gán ký tự đặc biệt như `'`, `"`
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
            where VanBanAIID in (select VanBanAIID from dbo.VanBanAI vb where convert(nvarchar(36), DuAnID)='{duAnID}' and vb.TenLoaiVanBan in ('QDPD_CT', 'QDPDDT_CBDT', 'QDPD_DA', 'QDPD_DT_THDT')
                and isnull(TrangThai, 0) = 0)  -- các văn bản chưa insert vào csdl
            """
            #print(query_van_ban)
            dfBangDuLieuChiTietAI = lay_du_lieu_tu_sql_server(query_van_ban)

            # Duyệt qua từng dòng trong dfBangDuLieuChiTietAI
            for index, row in dfBangDuLieuChiTietAI.iterrows():
                # Tìm dòng tương ứng trong dfBangGhepKMCP có TenKMCP trùng khớp
                matching_row = dfBangGhepKMCP[dfBangGhepKMCP['TenKMCP'] == row['TenKMCP']]
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
                    matching_row = dfBangGhepKMCP[dfBangGhepKMCP['TenKMCP'] == filtered_row['TenKMCP']]
                    
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
                            duplicate_rows = df_filtered[df_filtered['TenKMCP_AI'] == row['TenKMCP_AI']]
                            
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

                    print(f"Executing SQL query: {query_insert}")
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
        # print("\nDữ liệu VanBanAI:")
        # print("=" * 80)
        # for index, row in dfVanBanAI.iterrows():
        #     print(f"\nDòng {index + 1}:")
        #     for column in dfVanBanAI.columns:
        #         print(f"{column}: {row[column]}")
        #     print("-" * 40)
        # print("=" * 80)
        # if not dfVanBanAI.empty:
        #     for index, row in dfVanBanAI.iterrows():
        #         van_ban_id = row['VanBanAIID']
        #         ten_loai_van_ban = row['TenLoaiVanBan']
        #         query_bangct = f"select BangDuLieuChiTietAIID=convert(nvarchar(36), BangDuLieuChiTietAIID), KMCPID=convert(nvarchar(36), KMCPID), TenKMCP_AI from dbo.BangDuLieuChiTietAI where VanBanAIID='{van_ban_id}'"
        #         df_bang_ct = lay_du_lieu_tu_sql_server(query_bangct)
        #         # Xử lý thêm dữ liệu vào NTsoftDocumentAI
        #         # print("=================ten_loai_van_ban===============")
        #         # print(ten_loai_van_ban)

        #         # Xử lý LayMaDoiTuong -> Cho Cơ quan ban hành
        #         ten_toi_tuong = row['CoQuanBanHanh']
        #         la_ca_nhan = "0"
        #         doi_tuong_id = LayMaDoiTuong(don_vi_id, user_id, ten_toi_tuong, la_ca_nhan)
        #         try:
        #             query_update_doi_tuong = f"update dbo.VanBanAI set DoiTuongID_ToChuc=N'{doi_tuong_id}' where VanBanAIID=N'{van_ban_id}'"
        #             thuc_thi_truy_van(query_update_doi_tuong)
        #         except Exception as e:
        #             print(f"Lỗi khi cập nhật DoiTuongID_ToChuc: {str(e)}")
        #         # Xử lý LayMaDoiTuong -> Cho Người ký
        #         ten_toi_tuong = row['NguoiKy']
        #         la_ca_nhan = "1"
        #         doi_tuong_id = LayMaDoiTuong(don_vi_id, user_id, ten_toi_tuong, la_ca_nhan)
        #         try:
        #             query_update_doi_tuong = f"update dbo.VanBanAI set DoiTuongID_CaNhan=N'{doi_tuong_id}' where VanBanAIID=N'{van_ban_id}'"
        #             thuc_thi_truy_van(query_update_doi_tuong)
        #         except Exception as e:
        #             print(f"Lỗi khi cập nhật DoiTuongID_CaNhan: {str(e)}")

        #         if f"[{ten_loai_van_ban}]" in "[QDPD_CT];[QDPD_DA]":    
        #             if not df_bang_ct.empty:
        #                 for _, row2 in df_bang_ct.iterrows():
        #                     query_insert = f"""
        #                     delete from dbo.NTSoftDocumentAI where BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}'
        #                     ----------
        #                     insert into dbo.NTSoftDocumentAI (BangDuLieuChiTietAIID, TongMucDauTuKMCPID, KMCPID,CoCauVonID,VanBanAIID,TenKMCP,GiaTriTMDTKMCP,GiaTriTMDTKMCP_DC,GiaTriTMDTKMCPTang,GiaTriTMDTKMCPGiam,TongMucDauTuKMCPID_goc)
        #                     select 
        #                       BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}', TongMucDauTuKMCPID=newid()
        #                     , KMCPID=N'{row2['KMCPID']}'
        #                     , CoCauVonID=(select CoCauVonID from dbo.KMCP km where km.KMCPID=N'{row2['KMCPID']}')
        #                     , N'{van_ban_id}'
        #                     , TenKMCP=N'{row2['TenKMCP_AI']}'
        #                     , GiaTriTMDTKMCP=(select GiaTriTMDTKMCP from dbo.BangDuLieuChiTietAI ai where ai.BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}')
        #                     , GiaTriTMDTKMCP_DC=(select GiaTriTMDTKMCP_DC from dbo.BangDuLieuChiTietAI ai where ai.BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}')
        #                     , GiaTriTMDTKMCPTang=(select GiaTriTMDTKMCPTang from dbo.BangDuLieuChiTietAI ai where ai.BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}')
        #                     , GiaTriTMDTKMCPGiam=(select GiaTriTMDTKMCPGiam from dbo.BangDuLieuChiTietAI ai where ai.BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}')
        #                     , TongMucDauTuKMCPID_goc='00000000-0000-0000-0000-000000000000'
        #                     ---------- Cập nhật giá trị văn bản
        #                     update dbo.VanBanAI 
        #                     set 
        #                     GiaTri = (select GiaTriTMDTKMCP=isnull(sum(GiaTriTMDTKMCP), 0) from dbo.BangDuLieuChiTietAI ai where ai.VanBanAIID='{van_ban_id}') 
        #                     where VanBanAIID='{van_ban_id}'
        #                     """
        #                     #print(f"Executing SQL query: {query_insert}")
        #                     if thuc_thi_truy_van(query_insert) == False:
        #                         print(f"Executing SQL query: {query_insert}")
        #         if f"[{ten_loai_van_ban}]" in "[QDPDDT_CBDT];[QDPD_DT_THDT]":    
        #             if not df_bang_ct.empty:
        #                 for _, row2 in df_bang_ct.iterrows():
        #                     query_insert = f"""
        #                     delete from dbo.NTSoftDocumentAI where BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}'
        #                     ----------
        #                     insert into dbo.NTSoftDocumentAI (BangDuLieuChiTietAIID, DuToanKMCPID, KMCPID,CoCauVonID,VanBanAIID,TenKMCP,GiaTriDuToanKMCP,GiaTriDuToanKMCP_DC,GiaTriDuToanKMCPTang,GiaTriDuToanKMCPGiam,TongMucDauTuKMCPID_goc)
        #                     select 
        #                       BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}', DuToanKMCPID=newid()
        #                     , KMCPID=N'{row2['KMCPID']}'
        #                     , CoCauVonID=(select CoCauVonID from dbo.KMCP km where km.KMCPID=N'{row2['KMCPID']}')
        #                     , N'{van_ban_id}'
        #                     , TenKMCP=N'{row2['TenKMCP_AI']}'
        #                     , GiaTriDuToanKMCP=(select GiaTriDuToanKMCP from dbo.BangDuLieuChiTietAI ai where ai.BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}')
        #                     , GiaTriDuToanKMCP_DC=(select GiaTriDuToanKMCP_DC from dbo.BangDuLieuChiTietAI ai where ai.BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}')
        #                     , GiaTriDuToanKMCPTang=(select GiaTriDuToanKMCPTang from dbo.BangDuLieuChiTietAI ai where ai.BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}')
        #                     , GiaTriDuToanKMCPGiam=(select GiaTriDuToanKMCPGiam from dbo.BangDuLieuChiTietAI ai where ai.BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}')
        #                     , TongMucDauTuKMCPID_goc='00000000-0000-0000-0000-000000000000'
        #                     """
        #                     print(f"Executing SQL query: {query_insert}")
        #                     thuc_thi_truy_van(query_insert)

        #         if f"[{ten_loai_van_ban}]" in "[QDPD_KHLCNT_CBDT];[QDPD_KHLCNT_THDT]": # sử dụng cho 2 giai đoạn CB và TH
        #             if not df_bang_ct.empty:
        #                 for _, row2 in df_bang_ct.iterrows():
        #                     query_insert = f"""
        #                     delete from dbo.NTSoftDocumentAI where BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}'
        #                     ----------
        #                     insert into dbo.NTSoftDocumentAI(BangDuLieuChiTietAIID,VanBanAIID, TenKMCP, DauThauID, DauThauCTID,TenDauThau, GiaTriGoiThau, TenNguonVon, CoCauVonID
        #                         ,LoaiGoiThauID,HinhThucDThID,PhuongThucDThID,LoaiHopDongID,ThoiGianToChuc,KeHoachThoiGianHopDong)
        #                     SELECT
        #                     BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}', N'{van_ban_id}', TenKMCP=N'{row2['TenKMCP_AI']}', DauThauID=newid(),
        #                     DauThauCTID=newid(),
        #                     TenDauThau,
        #                     GiaTriGoiThau,
        #                     TenNguonVon,
        #                     CoCauVonID=(select CoCauVonID from dbo.KMCP km where km.KMCPID=N'{row2['KMCPID']}'),
        #                     LoaiGoiThauID=NULL, -- chưa xử lý
        #                     HinhThucDThID=NULL, -- chưa xử lý
        #                     PhuongThucDThID=NULL, -- chưa xử lý
        #                     LoaiHopDongID=NULL, -- chưa xử lý
        #                     ThoiGianToChuc=ThoiGianTCLCNT, -- chưa xử lý
        #                     KeHoachThoiGianHopDong=ThoiGianTHHopDong
        #                     FROM BangDuLieuChiTietAI ai where BangDuLieuChiTietAIID='{row2['BangDuLieuChiTietAIID']}'
        #                     """
        #                     print(f"Executing SQL query: {query_insert}")
        #                     thuc_thi_truy_van(query_insert)
        #         if f"[{ten_loai_van_ban}]" in "[QDPD_KQLCNT_CBDT];[QDPD_KQLCNT_THDT]": # sử dụng cho 2 giai đoạn CB và TH
        #             if not df_bang_ct.empty:
        #                 for _, row2 in df_bang_ct.iterrows():
        #                     query_insert = f"""
        #                     delete from dbo.NTSoftDocumentAI where BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}'
        #                     ----------
        #                     insert into dbo.NTSoftDocumentAI(BangDuLieuChiTietAIID,VanBanAIID,TenKMCP,TenDauThau,KeHoachThoiGianHopDong,LoaiHopDongID,GiaTrungThau, CoCauVonID)
        #                     SELECT
        #                     BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}', N'{van_ban_id}', TenKMCP=N'{row2['TenKMCP_AI']}',TenDauThau,
        #                     KeHoachThoiGianHopDong=ThoiGianTHHopDong,
        #                     LoaiHopDongID=NULL, -- chưa xử lý
        #                     GiaTrungThau, 
        #                     CoCauVonID=(select CoCauVonID from dbo.KMCP km where km.KMCPID=N'{row2['KMCPID']}')
        #                     FROM BangDuLieuChiTietAI ai where BangDuLieuChiTietAIID='{row2['BangDuLieuChiTietAIID']}'
        #                     """
        #                     print(f"Executing SQL query: {query_insert}")
        #                     thuc_thi_truy_van(query_insert)
        #         if f"[{ten_loai_van_ban}]" in "[HOP_DONG]": # Hợp đồng mặc định là giai đoạn thực hiện
        #             if not df_bang_ct.empty:
        #                 for _, row2 in df_bang_ct.iterrows():
        #                     query_insert = f"""
        #                     delete from dbo.NTSoftDocumentAI where BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}'
        #                     ----------
        #                     insert into dbo.NTSoftDocumentAI(BangDuLieuChiTietAIID, VanBanAIID, TenKMCP, HopDongCTID, DauThauCTID,GiaTriHopDong,CoCauVonID
        #                         ,GiaTriHopDongTang,GiaTriHopDongGiam,DuToanKMCPID,KMCPID)
        #                     SELECT
        #                     BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}', N'{van_ban_id}', TenKMCP=N'{row2['TenKMCP_AI']}',HopDongCTID=newid(),
        #                     DauThauCTID=NULL, -- khoá ngoại chưa xử lý
        #                     GiaTriHopDong,
        #                     CoCauVonID=(select CoCauVonID from dbo.KMCP km where km.KMCPID=N'{row2['KMCPID']}'),
        #                     GiaTriHopDongTang, -- khoá ngoại chưa xử lý
        #                     GiaTriHopDongGiam, -- khoá ngoại chưa xử lý
        #                     DuToanKMCPID=NULL, -- khoá ngoại chưa xử lý
        #                     KMCPID -- chưa xử lý
        #                     FROM BangDuLieuChiTietAI ai where BangDuLieuChiTietAIID='{row2['BangDuLieuChiTietAIID']}'
        #                     """
        #                     print(f"Executing SQL query: {query_insert}")
        #                     thuc_thi_truy_van(query_insert)
        # return JSONResponse(
        #     status_code=200,
        #     content={
        #         "status": "success",
        #         "code": 200,
        #         "message": "Đã làm đẹp dữ liệu văn bản",
        #         "detail": ""
        #     }
        # )
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


#MÔ HÌNH AZURE
@router.post("/image_extract_multi_azure")
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
                "JsonAI": json.dumps(data_json["ThongTinChung"], ensure_ascii=False),
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
                    "JsonAI": json.dumps(data_json["ThongTinChung"], ensure_ascii=False),
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
                    "JsonAI": json.dumps(data_json["ThongTinChung"], ensure_ascii=False),
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
                    "JsonAI": json.dumps(data_json["ThongTinChung"], ensure_ascii=False),
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
                    "JsonAI": json.dumps(data_json["ThongTinChung"], ensure_ascii=False),
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
                    "JsonAI": json.dumps(data_json["ThongTinChung"], ensure_ascii=False),
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
                    "JsonAI": json.dumps(data_json["ThongTinChung"], ensure_ascii=False),
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
async def extract_multiple_images(
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