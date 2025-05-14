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
from sqlalchemy.orm import Session
from app.core.database import get_db
import shutil
from fastapi.responses import JSONResponse
from app.services.DungChung import convert_currency_to_float

# Load biến môi trường từ file .env
load_dotenv()

router = APIRouter()

# Cấu hình API keys từ biến môi trường
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

# Khởi tạo models
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

# Định nghĩa IMAGE_STORAGE_PATH
IMAGE_STORAGE_PATH = os.getenv('IMAGE_STORAGE_PATH', 'image_storage')
os.makedirs(IMAGE_STORAGE_PATH, exist_ok=True)

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
            content={"message": "Chỉ chấp nhận file ảnh"}
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

        # Đọc và xử lý ảnh
        with Image.open(file_path) as img:
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()

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
        
        data_json = json.loads(response_text)

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
            "DuAnID": duAnID
        }
        print("request body:", van_ban_data)
        db_service = DatabaseService()
        result = await db_service.insert_van_ban_ai(db, van_ban_data)
        
        if not result.get("success", False):
            return JSONResponse(
                status_code=500,
                content={
                    "message": "Lỗi khi lưu dữ liệu vào database",
                    "error": result.get("error", "Unknown error"),
                    "data": data_json
                }
            )

        # Insert BangDuLieu data if it exists
        if "BangDuLieu" in data_json and data_json["BangDuLieu"]:
            # Prepare the data for BangDuLieu
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
            
            # Insert BangDuLieu data
            print("bang du lieu data:", bang_du_lieu_data)
            bang_du_lieu_result = await db_service.insert_bang_du_lieu_chi_tiet_ai(db, bang_du_lieu_data)
            if not bang_du_lieu_result.get("success", False):
                return JSONResponse(
                    status_code=500,
                    content={
                        "message": "Lỗi khi lưu chi tiết bảng dữ liệu",
                        "error": bang_du_lieu_result.get("error", "Unknown error"),
                        "data": data_json
                    }
                )

        return JSONResponse(
            status_code=200,
            content={
                "message": "Upload file ảnh thành công",
                "original_filename": file.filename,
                "unique_filename": unique_filename,
                "file_path": file_path,
                "data": data_json,
                "status": result.get("success", False),
                "db_message": result.get("message", "")
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": f"Lỗi khi upload file: {str(e)}"}
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
    # if len(files) < 2:
    #     raise HTTPException(status_code=400, detail="Yêu cầu tối thiểu 2 file ảnh để so sánh")
    
    temp_files = []
    all_data = []
    try:
        # Generate UUID only once and use it consistently
        van_ban_id = str(uuid.uuid4())
        bang_du_lieu_chi_tiet_id = str(uuid.uuid4())

        # Process each file
        for file in files:
            if not file.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail=f"File {file.filename} phải là định dạng ảnh")

            # Tạo tên file tạm thời
            temp_file_path = os.path.join(IMAGE_STORAGE_PATH, f"temp_{file.filename}")
            temp_files.append(temp_file_path)
            
            # Lưu file tạm thời
            with open(temp_file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

            # Xử lý ảnh
            with Image.open(temp_file_path) as img:
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()

            all_data.append({
                "filename": file.filename,
                "image_data": img_str
            })

        if not all_data:
            raise HTTPException(status_code=400, detail="Không thể xử lý bất kỳ file nào")

        # Combine all data for comparison
        combined_prompt = """
        
Dựa vào các tài liệu đã được cung cấp, hãy phân tích và gộp thông tin thành một đối tượng JSON duy nhất.
Yêu cầu trích xuất:
1.  **Thông tin chung của văn bản:**
    * `SoVanBan`: Số hiệu văn bản mới nhất.
    * `NgayKy`: Ngày ký văn bản mới nhất, chuyển đổi sang định dạng `dd/mm/yyyy`.
    * `NguoiKy`: Người ký văn bản mới nhất.
    * `ChucDanhNguoiKy`: Chức danh của người ký mới nhất (ví dụ: "Chủ tịch", "Phó Chủ tịch").
    * `CoQuanBanHanh`: Cơ quan ban hành văn bản.
    * `TrichYeu`: Trích yếu nội dung văn bản (tổng hợp từ các văn bản).
    * `LaVanBanDieuChinh`: Đặt giá trị là `1` nếu có bất kỳ văn bản nào là văn bản điều chỉnh. Ngược lại, đặt giá trị là `0`.
    * `LoaiVanBan`: Loại văn bản chung (ví dụ: "Quyết định", "Nghị định").
2.  **Chi tiết Tổng mức đầu tư:**
    * Gộp tất cả các khoản mục chi phí từ các văn bản.
    * Nếu có cùng hạng mục chi phí, gộp lại thành một dòng.
    * Lấy giá trị mới nhất cho mỗi hạng mục.
    * Thông tin này cần được đặt trong một mảng (array) có tên là `BangDuLieu`.
    * Mỗi phần tử trong mảng `BangDuLieu` là một đối tượng (object) chứa các cặp key-value:
        * `TenKMCP`: Tên của khoản mục chi phí (ví dụ: "Chi phí xây dựng").
        * `GiaTriTMDTKMCP`: Giá trị tổng mức đầu tư khoản mục chi phí.
        * `GiaTriTMDTKMCP_DC`: Giá trị tổng mức đầu tư khoản mục chi phí sau điều chỉnh.
        * `GiaTriTMDTKMCPTang`: Giá trị tổng mức đầu tư khoản mục chi phí tăng (nếu có).
        * `GiaTriTMDTKMCPGiam`: Giá trị tổng mức đầu tư khoản mục chi phí giảm (nếu có).

**Định dạng JSON đầu ra mong muốn:**
```json
{
   "VanBanID":"AI Tạo một giá trị UUID duy nhất theo định dạng xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
   "SoVanBan":"Số văn bản mới nhất",
   "NgayKy":"dd/mm/yyyy",
   "NguoiKy":"Tên người ký mới nhất",
   "ChucDanhNguoiKy":"Chức danh người ký mới nhất",
   "CoQuanBanHanh":"Tên cơ quan ban hành",
   "TrichYeu":"Nội dung trích yếu tổng hợp",
   "LaVanBanDieuChinh":"1 nếu có văn bản điều chỉnh, 0 nếu không",
   "TenVanBan":"Tên văn bản",
   "BangDuLieu":[
      {
         "TenKMCP":"Tên khoản mục chi phí. Ví dụ: Chi phí xây dựng",
         "GiaTriTMDTKMCP": "Giá trị tổng mức đầu tư",
         "GiaTriTMDTKMCP_DC": "Giá trị sau điều chỉnh, nếu không có để '0'",
         "GiaTriTMDTKMCPTang": "Giá trị tăng, nếu không có để '0'",
         "GiaTriTMDTKMCPGiam": "Giá trị giảm, nếu không có để '0'"
      }
   ]
}
```

**Lưu ý quan trọng:**
1. Ưu tiên thông tin từ văn bản mới nhất
2. Gộp các hạng mục chi phí tương tự
3. Lấy giá trị mới nhất cho mỗi hạng mục
4. Thêm ghi chú nếu có sự thay đổi về số liệu
5. Đảm bảo tính nhất quán trong việc gộp dữ liệu
6. Các thông giá trị trong BangDuLieu chỉ hiện số không cần định dạng"""

        # Prepare parts for Gemini API
        parts = [combined_prompt]
        for data in all_data:
            parts.append({
                'mime_type': 'image/png',
                'data': data['image_data']
            })

        # Call Gemini API with all images at once
        response = model.generate_content(parts)
        response_text = response.text

        # Clean up response text
        if response_text.strip().startswith("```json"):
            response_text = response_text.strip()[7:-3].strip()
        elif response_text.strip().startswith("```"):
            response_text = response_text.strip()[3:-3].strip()

        try:
            data_json = json.loads(response_text)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Lỗi parse JSON từ AI: {str(e)}")

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
            "DuAnID": duAnID
        }
        print("request body:", van_ban_data)
        db_service = DatabaseService()
        result = await db_service.insert_van_ban_ai(db, van_ban_data)
        
        if not result.get("success", False):
            return JSONResponse(
                status_code=500,
                content={
                    "message": "Lỗi khi lưu dữ liệu vào database",
                    "error": result.get("error", "Unknown error"),
                    "data": data_json
                }
            )

        # Insert BangDuLieu data if it exists
        if "BangDuLieu" in data_json and data_json["BangDuLieu"]:
            # Prepare the data for BangDuLieu
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
            
            # Insert BangDuLieu data
            print("bang du lieu data:", bang_du_lieu_data)
            bang_du_lieu_result = await db_service.insert_bang_du_lieu_chi_tiet_ai(db, bang_du_lieu_data)
            if not bang_du_lieu_result.get("success", False):
                return JSONResponse(
                    status_code=500,
                    content={
                        "message": "Lỗi khi lưu chi tiết bảng dữ liệu",
                        "error": bang_du_lieu_result.get("error", "Unknown error"),
                        "data": data_json
                    }
                )

        return JSONResponse(
            status_code=200,
            content={
                "message": "Upload và xử lý nhiều file ảnh thành công",
                "files_processed": [{"filename": d['filename']} for d in all_data],
                "data": data_json,
                "status": result.get("success", False),
                "db_message": result.get("message", "")
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file) 