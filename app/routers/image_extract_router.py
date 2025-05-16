from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
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
from app.services.DungChung import convert_currency_to_float
from app.core.auth import get_current_user
from app.schemas.user import User

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
            "TenNguoiKy": data_json.get("NguoiKy", ""),
            "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "TenLoaiVanBan": loaiVanBan,
            "DuAnID": duAnID,
            "JsonAI": json.dumps(data_json, ensure_ascii=False),
            "DataOCR": response_text,
            "TenFile": file.filename
        }

        db_service = DatabaseService()
        result = await db_service.insert_van_ban_ai(db, van_ban_data)
        
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
                    # Convert all numeric values based on required columns
                    for col in required_columns:
                        if col.startswith('GiaTri') and item.get(col):
                            try:
                                item[col] = convert_currency_to_float(str(item[col]))
                            except:
                                item[col] = 0
            
            van_ban_data = {
                "VanBanAIID": van_ban_id,
                "SoVanBan": data_json.get("SoVanBan", ""),
                "NgayKy": data_json.get("NgayKy", ""),
                "TrichYeu": data_json.get("TrichYeu", ""),
                "ChucDanhNguoiKy": data_json.get("ChucDanhNguoiKy", ""),
                "TenNguoiKy": data_json.get("NguoiKy", ""),
                "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "TenLoaiVanBan": loaiVanBan,
                "DuAnID": duAnID,
                "JsonAI": json.dumps(data_json, ensure_ascii=False),
                "DataOCR": response_text,
                "TenFile": "*".join([d['filename'] for d in all_data])
            }

            db_service = DatabaseService()
            result = await db_service.insert_van_ban_ai(db, van_ban_data)
            
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