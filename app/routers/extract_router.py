from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List, Dict, Any
import os
import google.generativeai as genai
import base64
from io import BytesIO
from PIL import Image
import fitz  # PyMuPDF
import json
import uuid
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

router = APIRouter()

# Cấu hình API keys từ biến môi trường
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
openai_api_key = os.getenv('OPENAI_API_KEY')

# Khởi tạo models
model = genai.GenerativeModel(model_name="gemini-1.5-flash")
client = OpenAI(api_key=openai_api_key)

FIELD_MAPPING = {
    'VanBanID': 'Khóa chính(pk)',
    'VanBanCode': 'Mã định danh văn bản',
    'HoSoLuuTruID': 'Mã hồ sơ',
    'CoQuanID': 'Mã cơ quan lưu trữ lịch sử',
    'PhongLuuTruID': 'Mã phòng/công trình/sưu tập lưu trữ',
    'MucLucSoNSD': 'Mục lục sổ hoặc năm hình thành hồ sơ',
    'SoVaKyHieuHS': 'Số và ký hiệu hồ sơ',
    'SoTTVBTrongHS': 'Số thứ tự văn bản trong hồ sơ',
    'LoaiVanBanID': 'Tên loại văn bản',
    'ToSo': 'Số của văn bản',
    'KyHieuVanBan': 'Ký hiệu của văn bản',
    'NgayKy': 'Ngày, tháng, năm của văn bản',
    'CoQuanBanHanh': 'Tên cơ quan, tổ chức ban hành văn bản',
    'TrichYeu': 'Trích yếu nội dung',
    'NgonNguID': 'Ngôn ngữ',
    'SoLuongTrang': 'Số lượng trang của văn bản',
    'GhiChu': 'Ghi chú',
    'KyHieuThongTin': 'Ký hiệu thông tin',
    'TuKhoa': 'Từ khóa',
    'CheDoSuDungID': 'Chế độ sử dụng',
    'MucDoTinCayID': 'Mức độ tin cậy',
    'ButTich': 'Bút tích',
    'TinhTrangVatLyID': 'Tình trạng vật lý',
    'DinhKem': 'Tệp đính kèm',
    'UserID': 'User thao tác',
    'DonViID': 'Đơn vị thao tác',
    'NgayThaoTac': 'Thời gian thao tác',
    'NoiDung': '//',
    'NguoiKy': 'Người ký',
    'PhanQuyen': 'Phân quyền',
    'SoHieuVanBan': 'Số hiệu văn bản'
}

def readTextFromPdf(file_path: str, pages: set = None) -> tuple:
    all_text = ""
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

                promptText = """
                # Yêu cầu:
                Bạn sẽ nhận một file PDF chứa văn bản hành chính (có thể là Quyết định, Công văn, Thông tư, ...). Hãy đọc **chính xác 100% nội dung theo từng dòng từ trái sang phải** của tài liệu.

                ## I. Thông tin cần trích xuất (theo từng trường):
                1. TieuDeHoSo: Tóm tắt ngắn gọn nội dung chính
                2. SoVaKyHieu: Số và ký hiệu chính thức
                3. LoaiVanBan: Quyết định, Công văn, Thông tư, Nghị định,...
                4. NgayVanBan: Ngày ban hành (dd/mm/yyyy)
                5. CoQuanBanHanh: Tên cơ quan, tổ chức ban hành
                6. HoTenNguoiKy: Họ và tên đầy đủ người ký
                7. ChucVuNguoiKy: Chức danh người ký (ví dụ: Giám đốc, Trưởng phòng,...).
                Lưu ý: Nếu văn bản có ghi "Chủ đầu tư" thì KHÔNG coi là chức danh, mà là vai trò pháp lý trong dự án.
                Khi đó, ChucVuNguoiKy sẽ là chức vụ theo sau vai trò pháp lý đó.
                8. NgonNgu: Ngôn ngữ chính của văn bản
                9. MaHoSo: Mã hồ sơ chứa văn bản
                10. TongSoTrang: Tổng số trang trong văn bản
                11. GhiChu: Các thông tin bổ sung khác (nếu có)

                ## II. Định dạng kết quả:
                - Trả kết quả dưới dạng **JSON** với các key như trên
                - Nếu không đọc được trường nào, để trống hoặc ghi ""
                - Luôn trả về định dạng với ngôn ngữ là tiếng việt
                """

                response = model.generate_content([
                    {'mime_type': 'image/png', 'data': img_str},
                    promptText
                ])
                all_text += response.text + "\n"

    return all_text, total_pages

def chat_with_openai_json(prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": """Bạn là 1 kế toán hành chính chuyên nghiệp, có kinh nghiệm 20 năm trong lĩnh vực kế toán"""},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

def convert_date_for_sql(input_date: str) -> str:
    try:
        parsed_date = datetime.strptime(input_date, "%d/%m/%Y")
        return parsed_date.strftime("%Y/%m/%d")
    except (ValueError, TypeError):
        return ""

@router.post("/extract")
async def extract_pdf(file: UploadFile = File(...)):
    temp_file_path = None
    try:
        # Tạo thư mục tạm nếu chưa tồn tại
        temp_dir = os.getenv('TEMP_DIR', 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Lưu file tạm thời
        temp_file_path = os.path.join(temp_dir, file.filename)
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Đọc dữ liệu từ PDF
        dataORC, total_pages = readTextFromPdf(temp_file_path, pages={1,2,3})

        # Lấy dữ liệu số hóa từ AI
        duLieuSoHoa = chat_with_openai_json(
            """Bạn là kế toán viên cao cấp có 20 năm kinh nghiệm làm việc tại cơ quan nhà nước hãy giúp tôi thực hiện nhiệm vụ sau:
            - Bước 1: Đọc toàn bộ **Dữ liệu về hồ sơ quyết toán** bên dưới
            **Dữ liệu hồ sơ quyết toán**
            ```
            """ + dataORC + """
            ```
            - Bước 2: Suy luận toàn bộ **Dữ liệu hồ sơ quyết toán** và đảm bảo hiểu được chứng từ
            - Bước 3: Trích xuất thông tin dưới định dạng JSON theo cấu trúc ở (Bước 4)
            - Bước 4: Chỉ xuất JSON, không giải thích (không định dạng markdown):
            ```
            {
              "ThongTinChung": {
                "TieuDeHoSo": "Tóm tắt ngắn gọn nội dung chính của văn bản hoặc hồ sơ.",
                "SoVaKyHieu": "Số và ký hiệu chính thức của văn bản.",
                "LoaiVanBan": "Ví dụ: Quyết định, Công văn, Thông tư, Nghị định,...",
                "NgayVanBan": "Ngày ban hành văn bản.",
                "CoQuanBanHanh": "Đơn vị chủ quản ban hành văn bản đó.",
                "HoTenNguoiKy": "Họ và tên đầy đủ của người ký văn bản.",
                "ChucVuNguoiKy": "Chức danh của người ký văn bản.",
                "NgonNgu": "Ngôn ngữ chính của văn bản (ví dụ: Tiếng Việt).",
                "MaHoSo": "Mã của hồ sơ chứa văn bản đó.",
                "TongSoTrang": "Số lượng trang của văn bản gốc.",
                "GhiChu": "Các thông tin bổ sung cần thiết khác."
              }
            }
            ```
            **Lưu ý:**
            + Không định dạng markdown
            + Nếu các thông tin ở đầu ra tôi yêu cầu mà bạn không tìm thấy cứ việc trả về giá trị là chuỗi rỗng `""`
            """)

        # Parse kết quả trả về từ AI
        try:
            data_json = json.loads(duLieuSoHoa)
            thong_tin_chung = data_json.get("ThongTinChung", {})
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Lỗi parse JSON từ AI: {str(e)}")

        # Map dữ liệu vào dict chuẩn theo FIELD_MAPPING
        mapped_data = {}
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Map các trường từ AI và các giá trị mặc định
        mapping_rules = {
            'TieuDeHoSo': ('TrichYeu', lambda x: x),
            'SoVaKyHieu': ('SoVaKyHieuHS', lambda x: x),
            'LoaiVanBan': ('LoaiVanBanID', lambda x: x),
            'NgayVanBan': ('NgayKy', lambda x: convert_date_for_sql(x) if x else ""),
            'CoQuanBanHanh': ('CoQuanBanHanh', lambda x: x),
            'HoTenNguoiKy': ('NguoiKy', lambda x: x),
            'ChucVuNguoiKy': ('GhiChu', lambda x: x),
            'NgonNgu': ('NgonNguID', lambda x: x),
            'MaHoSo': ('HoSoLuuTruID', lambda x: x),
            'TongSoTrang': ('SoLuongTrang', lambda x: str(total_pages)),
            'VanBanID': ('VanBanID', lambda x: str(uuid.uuid4())),
            'VanBanCode': ('VanBanCode', lambda x: f"VB_{datetime.now().strftime('%Y%m%d%H%M%S')}"),
            'NgayThaoTac': ('NgayThaoTac', lambda x: current_time),
            'NoiDung': ('NoiDung', lambda x: ""),
            'DinhKem': ('DinhKem', lambda x: file.filename),
        }

        # Áp dụng các quy tắc mapping
        for ai_field, (db_field, transform_func) in mapping_rules.items():
            if ai_field in thong_tin_chung:
                mapped_data[db_field] = transform_func(thong_tin_chung[ai_field])
            else:
                mapped_data[db_field] = transform_func(None)

        # Đảm bảo tất cả các trường trong FIELD_MAPPING đều có mặt trong dict trả về
        for db_field in FIELD_MAPPING.keys():
            if db_field not in mapped_data:
                mapped_data[db_field] = ""

        # Xóa file tạm
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

        return {
            "success": True,
            "data": mapped_data
        }

    except Exception as e:
        # Xóa file tạm nếu có lỗi
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=500, detail=str(e))