from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends, Form
from typing import List, Dict, Any, Optional
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
from app.core.database import get_db
import shutil
from fastapi.responses import JSONResponse
from app.services.DungChung import convert_currency_to_float, lay_du_lieu_tu_sql_server, thuc_thi_truy_van
from app.core.auth import get_current_user
from app.schemas.user import User
import pandas as pd

# Load biến môi trường từ file .env
load_dotenv()

router = APIRouter()

# Cấu hình API keys từ biến môi trường
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

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

@router.post("/image_extract")
async def extract_image(
    file: UploadFile = File(...),
    loaiVanBan: Optional[str] = None,
    duAnID: Optional[str] = None,
    db: Session = Depends(get_db)
):
    if not file.content_type.startswith('image/'):
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "code": 400,
                "message": "File không đúng định dạng ảnh",
                "detail": f"File {file.filename} có content_type {file.content_type} không phải là ảnh hợp lệ."
            }
        )
    try:
        # Generate UUID only once and use it consistently
        van_ban_id = str(uuid.uuid4())
        bang_du_lieu_chi_tiet_id = str(uuid.uuid4())

        # Tạo tên file mới với UUID để tránh trùng lặp
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(IMAGE_STORAGE_PATH, unique_filename)

        # Lưu file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        try:
            with Image.open(file_path) as img:
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
        except Exception as e:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "code": 400,
                    "message": "File ảnh bị hỏng hoặc không thể đọc",
                    "detail": str(e)
                }
            )
        promptText = """Dựa vào tài liệu đã được cung cấp, hãy trích xuất các thông tin sau và định dạng toàn bộ kết quả thành một đối tượng JSON duy nhất.
Yêu cầu trích xuất:
1.  **Thông tin chung của văn bản:**
    * `SoVanBan`: Số hiệu văn bản.
    * `NgayKy`: Ngày ký văn bản, chuyển đổi sang định dạng `dd/mm/yyyy`.
    * `NguoiKy`: Người ký văn bản.
    * `ChucDanhNguoiKy`: Chức danh của người ký (ví dụ: "Chủ tịch", "Phó Chủ tịch").
    * `CoQuanBanHanh`: Cơ quan ban hành văn bản.
    * `TrichYeu`: Trích yếu nội dung văn bản.
    * `LaVanBanDieuChinh`: Đặt giá trị là `1` nếu văn bản này là văn bản điều chỉnh, sửa đổi hoặc bổ sung một văn bản khác. Ngược lại, đặt giá trị là `0`.
    * `LoaiVanBan`: Loại văn bản (ví dụ: "Quyết định", "Nghị định").
2.  **Chi tiết Tổng mức đầu tư:**
    * Trích xuất các khoản mục chi phí chi tiết trong phần "Tổng mức đầu tư" (thường ở mục 9 của văn bản).
    * KHÔNG lấy dòng "Tổng mức đầu tư" hoặc "Tổng cộng".
    * Thông tin này cần được đặt trong một mảng (array) có tên là `TongMucDauTuChiTiet`.
    * Mỗi phần tử trong mảng `TongMucDauTuChiTiet` là một đối tượng (object) chứa các cặp key-value:
        * `TenKMCP`: Tên của khoản mục chi phí (ví dụ: "Chi phí xây dựng").
        * `GiaTriTMDTKMCP`: Giá trị tổng mức đầu tư khoản mục chi phí.
        * `GiaTriTMDTKMCP_DC`: Giá trị tổng mức đầu tư khoản mục chi phí sau điều chỉnh.
        * `GiaTriTMDTKMCPTang`: Giá trị tổng mức đầu tư khoản mục chi phí tăng (nếu có).
        * `GiaTriTMDTKMCPGiam`: Giá trị tổng mức đầu tư khoản mục chi phí giảm (nếu có).

**Định dạng JSON đầu ra mong muốn:**
```json
{
   "VanBanID":"ID ngẫu nhiên kiểu uniqueidentifier",
   "SoVanBan":"Số văn bản",
   "NgayKy":"dd/mm/yyyy",
   "NguoiKy":"Tên người ký",
   "ChucDanhNguoiKy":"Chức danh người ký",
   "CoQuanBanHanh":"Tên cơ quan ban hành",
   "TrichYeu":"Nội dung trích yếu",
   "LaVanBanDieuChinh":"Nếu là văn bản điều chỉnh `1` ngược lại `0`",
   "LoaiVanBan":"Loại văn bản, nêu rõ loại văn bản không nói chung chung",
   "TongMucDauTuChiTiet":[
      {
         "VanBanID":"Lấy `VanBanID` ở phía trên",
         "TenKMCP":"Chi phí xây dựng",
         "GiaTriTMDTKMCP": "Giá trị tổng mức đầu tư",
         "GiaTriTMDTKMCP_DC": "Giá trị sau điều chỉnh",
         "GiaTriTMDTKMCPTang": "Giá trị tăng (nếu có)",
         "GiaTriTMDTKMCPGiam": "Giá trị giảm (nếu có)"
      }
   ]
}
```
**Lưu ý:** Chỉ trả về đối tượng JSON theo định dạng yêu cầu, không giải thích gì thêm"""

        response = model.generate_content([
            {'mime_type': 'image/png', 'data': img_str},
            promptText
        ])

        # Xử lý response từ Gemini
        response_text = response.text
        if response_text.strip().startswith("```json"):
            response_text = response_text.strip()[7:-3].strip()
        elif response_text.strip().startswith("```"):
            response_text = response_text.strip()[3:-3].strip()
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
        except json.JSONDecodeError as e:
            # Nếu response_text có vẻ là HTML hoặc text không phải JSON
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
        required_fields = ["SoVanBan", "NgayKy", "NguoiKy", "ChucDanhNguoiKy", "TrichYeu"]
        missing_fields = [field for field in required_fields if field not in data_json]
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
                item["GiaTriTMDTKMCP"] = convert_currency_to_float(str(item.get("GiaTriTMDTKMCP", "0")))
                item["GiaTriTMDTKMCP_DC"] = convert_currency_to_float(str(item.get("GiaTriTMDTKMCP_DC", "0")))
                item["GiaTriTMDTKMCPTang"] = convert_currency_to_float(str(item.get("GiaTriTMDTKMCPTang", "0")))
                item["GiaTriTMDTKMCPGiam"] = convert_currency_to_float(str(item.get("GiaTriTMDTKMCPGiam", "0")))
        
        van_ban_data = {
            "VanBanAIID": van_ban_id,
            "SoVanBan": data_json.get("SoVanBan", ""),
            "NgayKy": data_json.get("NgayKy", ""),
            "TrichYeu": data_json.get("TrichYeu", ""),
            "ChucDanhNguoiKy": data_json.get("ChucDanhNguoiKy", ""),
            "CoQuanBanHanh": data_json.get("CoQuanBanHanh", ""),
            "NguoiKy": data_json.get("NguoiKy", ""),
            "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "TenLoaiVanBan": loaiVanBan,
            "DuAnID": duAnID,
            "JsonAI": json.dumps(data_json, ensure_ascii=False),
            "DataOCR": response_text,
            "TenFile": file.filename
        }

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
                    "BangDuLieuChiTietAIID": bang_du_lieu_chi_tiet_id,
                    "VanBanAIID": van_ban_id,
                    "TenKMCP": item.get("TenKMCP", ""),
                    "GiaTriTMDTKMCP": item["GiaTriTMDTKMCP"],
                    "GiaTriTMDTKMCP_DC": item["GiaTriTMDTKMCP_DC"],
                    "GiaTriTMDTKMCPTang": item["GiaTriTMDTKMCPTang"],
                    "GiaTriTMDTKMCPGiam": item["GiaTriTMDTKMCPGiam"]
                })
            
            bang_du_lieu_result = await db_service.insert_bang_du_lieu_chi_tiet_ai(db, bang_du_lieu_data)
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

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "code": 200,
                "message": "Upload file ảnh thành công",
                "data": {
                    "original_filename": file.filename,
                    "unique_filename": unique_filename,
                    "file_path": file_path,
                    "van_ban": data_json,
                    "db_status": result.get("success", False),
                    "db_message": result.get("message", "")
                }
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
        # Clean up temporary file
        if os.path.exists(file_path):
            os.remove(file_path)

class MultiImageExtractRequest(BaseModel):
    pages: Optional[List[int]] = None

@router.post("/image_extract_multi")
async def extract_multiple_images(
    files: List[UploadFile] = File(...),
    loaiVanBan: Optional[str] = None,
    duAnID: Optional[str] = None,
    db: Session = Depends(get_db)
):
    temp_files = []
    all_data = []
    try:
        # Generate UUID only once and use it consistently
        van_ban_id = str(uuid.uuid4())
        bang_du_lieu_chi_tiet_id = str(uuid.uuid4())

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

            # Tạo tên file tạm thời với timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_file_path = os.path.join(IMAGE_STORAGE_PATH, f"temp_{timestamp}_{file.filename}")
            temp_files.append(temp_file_path)
            
            # Lưu file tạm thời
            with open(temp_file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            try:
                with Image.open(temp_file_path) as img:
                    buffered = BytesIO()
                    img.save(buffered, format="PNG")
                    img_str = base64.b64encode(buffered.getvalue()).decode()
            except Exception as e:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "code": 400,
                        "message": f"File {file.filename} bị hỏng hoặc không thể đọc",
                        "detail": str(e)
                    }
                )
            all_data.append({
                "filename": file.filename,
                "image_data": img_str,
                "temp_path": temp_file_path  # Lưu đường dẫn file tạm để có thể xử lý sau
            })
        if not all_data:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "code": 400,
                    "message": "Không thể xử lý file",
                    "detail": "Không thể xử lý bất kỳ file nào"
                }
            )

        # Get the appropriate prompt based on loaiVanBan
        prompt, required_columns = prompt_service.get_prompt(loaiVanBan)
        # Prepare parts for Gemini API
        parts = [prompt]
        for data in all_data:
            parts.append({
                'mime_type': 'image/png',
                'data': data['image_data']
            })

        try:
            # Call Gemini API with all images at once
            response = model.generate_content(parts)
            response_text = response.text
            if response_text.strip().startswith("```json"):
                response_text = response_text.strip()[7:-3].strip()
            elif response_text.strip().startswith("```"):
                response_text = response_text.strip()[3:-3].strip()
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
                        if col.startswith('GiaTri') and item.get(col):
                            try:
                                item[col] = convert_currency_to_float(str(item[col]))
                            except:
                                item[col] = 0
            # dữ liệu mặc định
            van_ban_data = {
                "VanBanAIID": van_ban_id,
                "SoVanBan": data_json["ThongTinChung"].get("SoVanBan", ""),
                "NgayKy": data_json["ThongTinChung"].get("NgayKy", ""),
                "TrichYeu": data_json["ThongTinChung"].get("TrichYeu", ""),
                "ChucDanhNguoiKy": data_json["ThongTinChung"].get("ChucDanhNguoiKy", ""),
                "NguoiKy": data_json["ThongTinChung"].get("NguoiKy", ""),
                "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "TenLoaiVanBan": loaiVanBan,
                "DuAnID": duAnID,
                "DieuChinh": data_json["ThongTinChung"].get("DieuChinh", "0"),
                "JsonAI": json.dumps(data_json["ThongTinChung"], ensure_ascii=False),
                "DataOCR": response_text,
                "TenFile": "*".join([d['filename'] for d in all_data])
            }
            if  loaiVanBan in "BCDX_CT;QDPD_CT;QDPD_DA":
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
                        "db_message": result.get("message", "")
                    }
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

@router.get("/standardized_data")
async def standardized_data(
    duAnID: str
):
    try:
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
        from dbo.VanBanAI 
        where convert(nvarchar(36), DuAnID)='{duAnID}'
        order by NgayKy, (select STT from dbo.ChucNangAI cn where cn.ChucNangAIID=TenLoaiVanBan)"""
        dfVanBanAI = lay_du_lieu_tu_sql_server(query_van_ban)
        
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
### Thực hiện ánh xạ nội dung tương đồng giữa bảng `DuLieuChiTiet` và bảng `KMCP` để gán `MaKMCP` cho mỗi dòng trong bảng `DuLieuChiTiet`. Tuyệt đối tuấn theo `ĐIỀU KIỆN BẮT BUỘC` bên dưới
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
CP2 Chi phí xây dựng
CP202   Chi phí xây dựng công trình chính
CP203   Chi phí xây dựng công trình chính và phụ
CP204   Chi phí xây dựng điều chỉnh
CP205   Chi phí xây dựng trước thuế
CP206   Chi phí xây dựng sau thuế
CP207   Chi phí xây dựng công trình phụ
CP250   Chi phí xây dựng khác
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

### Kết quả đầu ra chuỗi json duy nhất với các trường thông tin
- STT: STT của bảng DuLieuChiTiet
- TenKMCP: Tên khoản mục gốc trước khi ánh xạ
- TenKMCP_Moi: Tên khoản mục sau khi ánh xạ
- MaKMCP: Mã KMCP dược ánh xạ giữa 2 bảng
- GhiChu: Giải thích vì sao lại ánh xạ như vậy

### ĐIỀU KIỆN BẮT BUỘC:
- Bảo toàn DuLieuChiTiet.STT: Cột STT của bảng DuLieuChiTiet là khóa chính, giá trị không được thay đổi.
- Ánh xạ dựa trên TenKMCP: Việc gán MaKMCP phải dựa trên sự tương đồng về ý nghĩa giữa DuLieuChiTiet.TenKMCP (tên khoản mục gốc) và KMCP.TenKMCP.
- Cung cấp GhiChu: Mỗi ánh xạ phải đi kèm một giải thích ngắn gọn trong cột GhiChu về lý do lựa chọn MaKMCP đó.
- Không bỏ trống MaKMCP: TUYỆT ĐỐI không được để trống MaKMCP cho bất kỳ dòng nào trong bảng DuLieuChiTiet sau khi xử lý. Bắt buộc mọi dòng đều phải được ánh xạ.
- Xử lý toàn bộ dữ liệu: Nếu bảng DuLieuChiTiet đầu vào có N dòng, kết quả đầu ra cũng phải có N dòng tương ứng đã được xử lý. Không được ngắt quãng hay bỏ sót.
- Chỉ trả về JSON: Kết quả cuối cùng CHỈ LÀ MỘT CHUỖI JSON DUY NHẤT, không kèm theo bất kỳ giải thích hay văn bản nào khác.
"""
        
        response = model.generate_content([
            promt_anh_xa_noi_dung_tuong_dong
        ])
        
        # Xử lý response từ Gemini
        response_text = response.text
        if response_text.strip().startswith("```json"):
            response_text = response_text.replace("```json", "").replace("```", "").strip()
        
        try:
            df_anh_xa = pd.read_json(response_text)
            for _, row in df_anh_xa.iterrows():
                query_update = f"""
                update BangDuLieuChiTietAI
                set
                TenKMCP_AI=N'{row['TenKMCP_Moi']}',
                KMCPID=(select top 1 KMCPID from dbo.KMCP km where replace(km.MaKMCP, '.', '')='{row['MaKMCP']}'),
                GhiChuAI=N'{row['GhiChu']}'
                where STT=N'{row['STT']}'
                """
                #print(f"Executing SQL query: {query_update}")
                thuc_thi_truy_van(query_update)
        except Exception as e:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error", 
                    "code": 400,
                    "message": "Lỗi khi xử lý kết quả ánh xạ từ AI",
                    "detail": str(e)
                }
            )
        
        if not dfVanBanAI.empty:
            for index, row in dfVanBanAI.iterrows():
                van_ban_id = row['VanBanAIID']
                ten_loai_van_ban = row['TenLoaiVanBan']
                query_bangct = f"select BangDuLieuChiTietAIID=convert(nvarchar(36), BangDuLieuChiTietAIID), KMCPID=convert(nvarchar(36), KMCPID), TenKMCP_AI from dbo.BangDuLieuChiTietAI where VanBanAIID='{van_ban_id}'"
                df_bang_ct = lay_du_lieu_tu_sql_server(query_bangct)
                # Xử lý thêm dữ liệu vào NTsoftDocumentAI
                if ten_loai_van_ban in "QDPD_CT":    
                    if not df_bang_ct.empty:
                        for _, row2 in df_bang_ct.iterrows():
                            query_insert = f"""
                            delete from dbo.NTSoftDocumentAI where BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}'
                            ----------
                            insert into dbo.NTSoftDocumentAI (BangDuLieuChiTietAIID, KMCPID,CoCauVonID,VanBanAIID,TenKMCP,GiaTriTMDTKMCP,GiaTriTMDTKMCP_DC,GiaTriTMDTKMCPTang,GiaTriTMDTKMCPGiam,TongMucDauTuKMCPID_goc)
                            select 
                              BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}'
                            , KMCPID=N'{row2['KMCPID']}'
                            , CoCauVonID=(select CoCauVonID from dbo.KMCP km where km.KMCPID=N'{row2['KMCPID']}')
                            , N'{van_ban_id}'
                            , TenKMCP=N'{row2['TenKMCP_AI']}'
                            , GiaTriTMDTKMCP=(select GiaTriTMDTKMCP from dbo.BangDuLieuChiTietAI ai where ai.BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}')
                            , GiaTriTMDTKMCP_DC=(select GiaTriTMDTKMCP_DC from dbo.BangDuLieuChiTietAI ai where ai.BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}')
                            , GiaTriTMDTKMCPTang=(select GiaTriTMDTKMCPTang from dbo.BangDuLieuChiTietAI ai where ai.BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}')
                            , GiaTriTMDTKMCPGiam=(select GiaTriTMDTKMCPGiam from dbo.BangDuLieuChiTietAI ai where ai.BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}')
                            , TongMucDauTuKMCPID_goc='00000000-0000-0000-0000-000000000000'
                            """
                            #print(f"Executing SQL query: {query_insert}")
                            if thuc_thi_truy_van(query_insert) == False:
                                print(f"Executing SQL query: {query_insert}")
                if ten_loai_van_ban in "QDPDDT_CBDT":    
                    if not df_bang_ct.empty:
                        for _, row2 in df_bang_ct.iterrows():
                            query_insert = f"""
                            delete from dbo.NTSoftDocumentAI where BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}'
                            ----------
                            insert into dbo.NTSoftDocumentAI (BangDuLieuChiTietAIID, KMCPID,CoCauVonID,VanBanAIID,TenKMCP,GiaTriDuToanKMCP,GiaTriDuToanKMCP_DC,GiaTriDuToanKMCPTang,GiaTriDuToanKMCPGiam,TongMucDauTuKMCPID_goc)
                            select 
                              BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}'
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

                if ten_loai_van_ban in "QDPD_KHLCNT_THDT":
                    if not df_bang_ct.empty:
                        for _, row2 in df_bang_ct.iterrows():
                            query_insert = f"""
                            delete from dbo.NTSoftDocumentAI where BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}'
                            ----------
                            insert into dbo.NTSoftDocumentAI (BangDuLieuChiTietAIID, KMCPID,CoCauVonID,VanBanAIID,TenKMCP,GiaTriDuToanKMCP,GiaTriDuToanKMCP_DC,GiaTriDuToanKMCPTang,GiaTriDuToanKMCPGiam,TongMucDauTuKMCPID_goc)
                            select 
                              BangDuLieuChiTietAIID=N'{row2['BangDuLieuChiTietAIID']}'
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
        else:
            dfBangDuLieuChiTietAI = pd.DataFrame()

        # return JSONResponse(
        #     status_code=200,
        #     content={
        #         "status": "success",
        #         "code": 200,
        #         "message": "Lấy dữ liệu thành công",
        #         "data": dfVanBanAI.to_dict('records')
        #     }
        # )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "code": 500,
                "message": "Lỗi khi lấy dữ liệu",
                "detail": str(e)
            }
        )

