from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Dict, Any
import os
import google.generativeai as genai
import base64
from io import BytesIO
from PIL import Image
import json
import uuid
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
from app.services.db_service import DatabaseService

load_dotenv()

router = APIRouter()

genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
openai_api_key = os.getenv('OPENAI_API_KEY')

model = genai.GenerativeModel(model_name="gemini-1.5-flash")
client = OpenAI(api_key=openai_api_key)

FIELD_MAPPING = {
    'sttHoSoLuuTruCTpr': 'Khóa chính(pk)',
    'vanBanCode': 'Mã định danh văn bản',
    'sttHoSoLuuTrupr_sd': 'Mã hồ sơ',
    'sttDuAnpr_sd': 'Mã cơ quan lưu trữ lịch sử',
    'maPhongLuuTru': 'Mã phòng/công trình/sưu tập lưu trữ',
    'mucLucSoNSD': 'Mục lục sổ hoặc năm hình thành hồ sơ',
    'soVaKyHieuHS': 'Số và ký hiệu hồ sơ',
    'soTTVBTrongHS': 'Số thứ tự văn bản trong hồ sơ',
    'maLoaiVBanpr': 'Tên loại văn bản',
    'toSo': 'Số của văn bản',
    'kyHieuVanBan': 'Ký hiệu của văn bản',
    'ngayKy': 'Ngày, tháng, năm của văn bản',
    'coQuanBanHanh': 'Tên cơ quan, tổ chức ban hành văn bản',
    'trichYeu': 'Trích yếu nội dung',
    'maNgonNgupr_sd': 'Ngôn ngữ',
    'soLuongTrang': 'Số lượng trang của văn bản',
    'ghiChu': 'Ghi chú',
    'kyHieuThongTin': 'Ký hiệu thông tin',
    'tuKhoa': 'Từ khóa',
    'maCheDoSuDungpr_sd': 'Chế độ sử dụng',
    'maMucDoTinCaypr_sd': 'Mức độ tin cậy',
    'butTich': 'Bút tích',
    'maTinhTrangVLpr_sd': 'Tình trạng vật lý',
    'dinhKem': 'Tệp đính kèm',
    'nguoiThaoTac': 'User thao tác',
    'maDonVipr_sd': 'Đơn vị thao tác',
    'ngayThaoTac': 'Thời gian thao tác',
    'noiDung': '//',
    'nguoiKy': 'Người ký',
    'phanQuyen': 'Phân quyền'
}

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

@router.post("/image_extract")
async def extract_image(file: UploadFile = File(...)):
    temp_file_path = None
    try:
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File phải là định dạng ảnh")

        temp_dir = os.getenv('TEMP_DIR', 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_file_path = os.path.join(temp_dir, file.filename)
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        with Image.open(temp_file_path) as img:
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()

        promptText = """
        # Yêu cầu:
        Bạn sẽ nhận một hình ảnh chứa văn bản hành chính (có thể là Quyết định, Công văn, Thông tư, ...). Hãy đọc **chính xác 100% nội dung theo từng dòng từ trái sang phải** của tài liệu.

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

        duLieuSoHoa = chat_with_openai_json(
            """Bạn là kế toán viên cao cấp có 20 năm kinh nghiệm làm việc tại cơ quan nhà nước hãy giúp tôi thực hiện nhiệm vụ sau:
            - Bước 1: Đọc toàn bộ **Dữ liệu về hồ sơ quyết toán** bên dưới
            **Dữ liệu hồ sơ quyết toán**
            ```
            """ + response.text + """
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

        try:
            data_json = json.loads(duLieuSoHoa)
            thong_tin_chung = data_json.get("ThongTinChung", {})
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Lỗi parse JSON từ AI: {str(e)}")

        mapped_data = {}
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        mapping_rules = {
            'TieuDeHoSo': ('trichYeu', lambda x: x),
            'SoVaKyHieu': ('soVaKyHieuHS', lambda x: x),
            'LoaiVanBan': ('maLoaiVBanpr', lambda x: x),
            'NgayVanBan': ('ngayKy', lambda x: convert_date_for_sql(x) if x else ""),
            'CoQuanBanHanh': ('coQuanBanHanh', lambda x: x),
            'HoTenNguoiKy': ('nguoiKy', lambda x: x),
            'ChucVuNguoiKy': ('ghiChu', lambda x: x),
            'NgonNgu': ('maNgonNgupr_sd', lambda x: x),
            'MaHoSo': ('sttHoSoLuuTrupr_sd', lambda x: x),
            'TongSoTrang': ('soLuongTrang', lambda x: "1"), 
            'VanBanID': ('sttHoSoLuuTruCTpr', lambda x: str(uuid.uuid4())),
            'VanBanCode': ('vanBanCode', lambda x: f"VB_{datetime.now().strftime('%Y%m%d%H%M%S')}"),
            'NgayThaoTac': ('ngayThaoTac', lambda x: current_time),
            'NoiDung': ('noiDung', lambda x: ""),
            'DinhKem': ('dinhKem', lambda x: file.filename),
        }

        for ai_field, (db_field, transform_func) in mapping_rules.items():
            if ai_field in thong_tin_chung:
                mapped_data[db_field] = transform_func(thong_tin_chung[ai_field])
            else:
                mapped_data[db_field] = transform_func(None)

        for db_field in FIELD_MAPPING.keys():
            if db_field not in mapped_data:
                mapped_data[db_field] = ""

        db_result = await DatabaseService.insert_ho_so_luu_tru(mapped_data)
        
        if not db_result["success"]:
            error_msg = f"Lỗi khi thêm dữ liệu vào database: {db_result.get('error', 'Unknown error')}"
            if 'error_details' in db_result:
                error_msg += f"\nChi tiết lỗi: {db_result['error_details']}"
            raise HTTPException(status_code=500, detail=error_msg)

        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

        return {
            "success": True,
            "data": mapped_data,
            "db_result": db_result
        }

    except Exception as e:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=500, detail=str(e)) 