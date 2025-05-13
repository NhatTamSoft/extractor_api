from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import os
import google.generativeai as genai
import base64
from io import BytesIO
from PIL import Image
import fitz  # PyMuPDF
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv
from app.services.database_service import DatabaseService
from sqlalchemy.orm import Session
from app.core.database import get_db
import shutil
import re
from fastapi.responses import JSONResponse
from app.services.DungChung import read_text_from_pdf_combined, to_slug, convert_currency_to_float

# Load biến môi trường từ file .env
load_dotenv()

router = APIRouter()

# Cấu hình API keys từ biến môi trường
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

# Khởi tạo models
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

class ExtractService:
    def __init__(self):
        self.model = model

    async def extract_text(self, file: UploadFile) -> Dict[str, Any]:
        try:
            # Save uploaded file temporarily
            temp_file_path = f"temp_{file.filename}"
            with open(temp_file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

            # Extract text from PDF
            text, total_pages = readTextFromPdf(temp_file_path)
            
            # Clean up temporary file
            os.remove(temp_file_path)
            
            return {
                "success": True,
                "text": text,
                "total_pages": total_pages
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Lỗi khi trích xuất văn bản: {str(e)}"
            }

    def process_extracted_text(self, text: str) -> Dict[str, Any]:
        try:
            # Parse the JSON response from Gemini
            data = json.loads(text)
            
            # Convert date format
            if data.get("NgayKy"):
                data["NgayKy"] = convert_date_for_sql(data["NgayKy"])
            
            return {
                "SoVanBan": data.get("SoVanBan", ""),
                "NgayKy": data.get("NgayKy", ""),
                "TrichYeu": data.get("TrichYeu", ""),
                "ChucDanhNguoiKy": data.get("ChucDanhNguoiKy", ""),
                "NguoiKy": data.get("NguoiKy", ""),
                "TongMucDauTuChiTiet": data.get("TongMucDauTuChiTiet", [])
            }
        except Exception as e:
            return {
                "SoVanBan": "",
                "NgayKy": "",
                "TrichYeu": "",
                "ChucDanhNguoiKy": "",
                "NguoiKy": "",
                "TongMucDauTuChiTiet": []
            }

def readTextFromPdf(file_path: str, pages: set = None) -> tuple:
    all_text = ""
    doc = None
    try:
        doc = fitz.open(file_path)
        total_pages = len(doc)

        if pages is None:
            pages = {1, 2, 3}

        text_found = False

        for page_num in pages:
            if 1 <= page_num <= total_pages:
                page = doc.load_page(page_num - 1)
                page_text = page.get_text("text")
                if page_text:
                    text_found = True
                    all_text += page_text + "\n"

        if not text_found:
            for page_num in pages:
                if 1 <= page_num <= total_pages:
                    page = doc[page_num - 1]
                    pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72), alpha=False)
                    img = Image.frombuffer("RGB", [pix.width, pix.height], pix.samples, "raw", "RGB", 0, 1)
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
                    all_text += response.text + "\n"

        return all_text, total_pages
    finally:
        if doc:
            doc.close()

def convert_date_for_sql(input_date: str) -> str:
    try:
        parsed_date = datetime.strptime(input_date, "%d/%m/%Y")
        return parsed_date.strftime("%Y/%m/%d")
    except (ValueError, TypeError):
        return ""

class PDFExtractRequest(BaseModel):
    pages: Optional[List[int]] = None

# Định nghĩa PDF_STORAGE_PATH
PDF_STORAGE_PATH = os.getenv('PDF_STORAGE_PATH', 'pdf_storage')
os.makedirs(PDF_STORAGE_PATH, exist_ok=True)

@router.post("/extract")
async def extract_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith('.pdf'):
        return JSONResponse(
            status_code=400,
            content={"message": "Chỉ chấp nhận file PDF"}
        )
    try:
        # Generate UUID only once and use it consistently
        van_ban_id = str(uuid.uuid4())
        bang_du_lieu_chi_tiet_id = str(uuid.uuid4())

        # Tạo tên file mới với slug sử dụng to_slug của DungChung
        file_name_without_ext = os.path.splitext(file.filename)[0]
        file_extension = os.path.splitext(file.filename)[1]
        slug_filename = to_slug(file_name_without_ext) + file_extension
        file_path = os.path.join(PDF_STORAGE_PATH, slug_filename)

        # Lưu file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Đọc text từ PDF bằng hàm chuẩn
        ocr_prompt = """Dựa vào tài liệu đã được cung cấp, hãy trích xuất các thông tin sau và định dạng toàn bộ kết quả thành một đối tượng JSON duy nhất.
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
        specific_ocr_prompt_text_pdf = ocr_prompt
        pdf_text = read_text_from_pdf_combined(
            file_path,
            specific_ocr_prompt_text_pdf,
            ocr_prompt,
            model_name="gemini-1.5-flash",
            output_image_dir="temp_image",
            loai_file="IMAGE"
        )
        if pdf_text.strip().startswith("```json"):
            pdf_text = pdf_text.strip()[7:-3].strip()
        elif pdf_text.strip().startswith("```"):
            pdf_text = pdf_text.strip()[3:-3].strip()
        data_json = json.loads(pdf_text)

        # Set UUIDs in the response data
        data_json["BangDuLieuID"] = bang_du_lieu_chi_tiet_id
        data_json["VanBanID"] = van_ban_id

        # Convert currency values in the response
        if "TongMucDauTuChiTiet" in data_json:
            for item in data_json["TongMucDauTuChiTiet"]:
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
            "NgayThaotac": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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

        # Insert TongMucDauTuChiTiet data if it exists
        if "TongMucDauTuChiTiet" in data_json and data_json["TongMucDauTuChiTiet"]:
            # Prepare the data for TongMucDauTuChiTiet
            tong_muc_dau_tu_data = []
            for item in data_json["TongMucDauTuChiTiet"]:
                tong_muc_dau_tu_data.append({
                    "BangDuLieuChiTietAIID": bang_du_lieu_chi_tiet_id,
                    "VanBanAIID": van_ban_id,
                    "TenKMCP": item.get("TenKMCP", ""),
                    "GiaTriTMDTKMCP": item["GiaTriTMDTKMCP"],
                    "GiaTriTMDTKMCP_DC": item["GiaTriTMDTKMCP_DC"],
                    "GiaTriTMDTKMCPTang": item["GiaTriTMDTKMCPTang"],
                    "GiaTriTMDTKMCPGiam": item["GiaTriTMDTKMCPGiam"]
                })
            
            # Insert TongMucDauTuChiTiet data
            print("tong muc dau tu data:", tong_muc_dau_tu_data)
            tong_muc_result = await db_service.insert_bang_du_lieu_chi_tiet_ai(db, tong_muc_dau_tu_data)
            if not tong_muc_result.get("success", False):
                return JSONResponse(
                    status_code=500,
                    content={
                        "message": "Lỗi khi lưu chi tiết tổng mức đầu tư",
                        "error": tong_muc_result.get("error", "Unknown error"),
                        "data": data_json
                    }
                )

        return JSONResponse(
            status_code=200,
            content={
                "message": "Upload file PDF thành công",
                "original_filename": file.filename,
                "slug_filename": slug_filename,
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