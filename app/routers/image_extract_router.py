from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from typing import Dict, Any, List, Optional
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
from pydantic import BaseModel

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

        ## III. Xử lý dữ liệu dạng bảng:
        Nếu tài liệu có bảng dữ liệu (ví dụ: bảng phân công công việc, bảng dự toán...), hãy trích xuất theo quy tắc sau:
        1. Đọc và xác định chính xác tiêu đề các cột trong bảng
        2. Trích xuất dữ liệu theo từng dòng, mỗi dòng là một object trong mảng DataTable
        3. Đặt tên key theo quy tắc:
           - Chuyển tiêu đề cột thành dạng camelCase
           - Loại bỏ dấu và ký tự đặc biệt
           - Thay thế khoảng trắng bằng chữ cái viết hoa
           - Ví dụ: "Số thứ tự" -> "soThuTu", "Tên công việc" -> "tenCongViec"
        4. Giữ nguyên định dạng và đơn vị của dữ liệu gốc
        5. Nếu có nhiều bảng, trích xuất riêng biệt và đánh số thứ tự

        Ví dụ kết quả:
        {
          "Data": {
            "TieuDeHoSo": "Quyết định phê duyệt dự toán",
            ...
          },
          "DataTable": [
            {
                "soThuTu": "1",
                "noiDung": "Chi phí xây dựng",
                "soTien": "2.411.711.306 đồng",
                "ghiChu": "Theo dự toán"
            },
            {
                "soThuTu": "2",
                "noiDung": "Chi phí thiết bị",
                "soTien": "250.000.000 đồng",
                "ghiChu": "Theo dự toán"
            }
          ]
        }

        Lưu ý:
        - Nếu không có bảng dữ liệu, trả về "DataTable": []
        - Đảm bảo giữ nguyên định dạng số và đơn vị tiền tệ
        - Nếu có dấu phân cách hàng nghìn, giữ nguyên định dạng
        - Nếu có ghi chú hoặc chú thích, thêm vào trường tương ứng
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
            - Bước 2: Suy luận toàn bộ **Dữ liệu hồ sơ quyết toán** và đảm bảo hiểu được nội dung
            - Bước 3: Trích xuất thông tin dưới định dạng JSON theo cấu trúc ở (Bước 4)
            - Bước 4: Chỉ xuất JSON, không giải thích (không định dạng markdown):
            ```
            {
              "Data": {
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
              },
              "DataTable": [
                {
                    "stt": 1,
                    "hangMucChiPhi": "Chi phí xây dựng",
                    "daPheDuyetDong": "2.411.711.306",
                    "sauDieuChinhDong": "2.363.470.000",
                    "tangGiam": "-48.241.306",
                    "ghiChu": ""
                }
              ]
            }
            ```
            **Lưu ý:**
            + Nếu không có bảng dữ liệu, trả về "DataTable": []
            + Nếu các thông tin ở đầu ra tôi yêu cầu mà bạn không tìm thấy cứ việc trả về giá trị là chuỗi rỗng `""`
            + Xác định chính xác bảng dữ liệu trong ảnh.
            + Tự động nhận diện hàng tiêu đề (header) của bảng, sử dụng nguyên văn tiêu đề cột làm key cho JSON.
            + Xác định chính xác số dòng số cột của mỗi bảng biểu để hiển thị Số thứ tự(STT) cho đầy đủ tránh bị mất nội dung.
            + Trích xuất tất cả các hàng trong bảng (kể cả hàng "Tổng cộng" nếu có).
            + Đảm bảo tất cả các bảng số liệu đều được gộp chung một bảng, nếu nội dung cùng ý nghĩa thì gộp lại cùng một dòng(example: chi phí quản lý dự án hay chi phí QLDA đều mang cùng một ý nghĩa) và kèm theo cột ghiChu về nội dung gộp nhé.
            + Trả về kết quả ở dạng danh sách JSON (List<Object>), trong đó mỗi object là một dòng dữ liệu, **key là chính xác nội dung tiêu đề của từng cột** (giữ nguyên cấu trúc example: nguồn vốn -> nguonVon).
            """)

        try:
            data_json = json.loads(duLieuSoHoa)
            thong_tin_chung = data_json.get("Data", {})
            data_table = data_json.get("DataTable", [])
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
            'ChucVuNguoiKy': ('ghiChu', lambda x: ""),
            'NgonNgu': ('maNgonNgupr_sd', lambda x: "01"),
            'MaHoSo': ('sttHoSoLuuTrupr_sd', lambda x: x if x else "HS_" + datetime.now().strftime("%Y%m%d")),
            'TongSoTrang': ('soLuongTrang', lambda x: x if x else "1"), 
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

        # Tạm thời ẩn code lưu database
        """
        db_result = await DatabaseService.insert_ho_so_luu_tru(mapped_data)
        
        if not db_result["success"]:
            error_msg = f"Lỗi khi thêm dữ liệu vào database: {db_result.get('error', 'Unknown error')}"
            if 'error_details' in db_result:
                error_msg += f"\nChi tiết lỗi: {db_result['error_details']}"
            raise HTTPException(status_code=500, detail=error_msg)
        """

        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

        return {
            "success": True,
            "data": mapped_data,
            "dataTable": data_table,
            # "db_result": db_result  # Tạm thời ẩn kết quả lưu database
        }

    except Exception as e:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=500, detail=str(e))

class MultiImageExtractRequest(BaseModel):
    pages: Optional[List[int]] = None

@router.post("/image_extract_multi")
async def extract_multiple_images(
    files: List[UploadFile] = File(...),
    pages: Optional[List[int]] = Query(None, description="Danh sách các trang cần đọc trong file PDF")
):
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="Yêu cầu tối thiểu 2 file ảnh để so sánh")
    
    temp_files = []
    all_data = []
    try:
        temp_dir = os.getenv('TEMP_DIR', 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Process each file
        for file in files:
            if not file.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail=f"File {file.filename} phải là định dạng ảnh")

            temp_file_path = os.path.join(temp_dir, file.filename)
            temp_files.append(temp_file_path)
            
            with open(temp_file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

            with Image.open(temp_file_path) as img:
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()

            response = model.generate_content([
                {'mime_type': 'image/png', 'data': img_str},
                promptText
            ])

            all_data.append({
                "filename": file.filename,
                "content": response.text
            })

        # Combine all data for comparison
        combined_prompt = """
        Bạn là kế toán viên cao cấp có 20 năm kinh nghiệm làm việc tại cơ quan nhà nước. Hãy phân tích và gộp nội dung từ các văn bản sau:

        {}

        Yêu cầu:
        1. Phân tích và gộp thông tin chung:
           - Lấy thông tin mới nhất từ các văn bản (ngày ban hành, số hiệu, người ký...)
           - Tổng hợp nội dung chung của các văn bản
           - Nếu có sự khác biệt về thông tin, ưu tiên thông tin mới nhất

        2. Xử lý bảng biểu chi phí:
           - Gộp tất cả các bảng biểu chi phí từ các văn bản
           - Nếu có cùng hạng mục chi phí, gộp lại thành một dòng
           - Tính toán tổng hợp số liệu:
             + Nếu là chi phí đã phê duyệt: lấy số liệu mới nhất
             + Nếu là chi phí sau điều chỉnh: lấy số liệu mới nhất
             + Tính toán lại số tiền tăng/giảm dựa trên số liệu mới
           - Thêm ghi chú nếu có sự thay đổi về số liệu giữa các văn bản

        3. Quy tắc gộp bảng biểu:
           - Gộp các hạng mục có tên tương tự (ví dụ: "Chi phí quản lý dự án" và "Chi phí QLDA")
           - Giữ nguyên cấu trúc cột của bảng biểu
           - Thêm cột ghi chú để giải thích nguồn gốc số liệu
           - Sắp xếp các hạng mục theo thứ tự logic

        Trả về kết quả theo định dạng JSON sau:
        {{
            "Data": {{
                "TieuDeHoSo": "Tóm tắt nội dung chung của các văn bản",
                "SoVaKyHieu": "Số và ký hiệu của văn bản mới nhất",
                "LoaiVanBan": "Loại văn bản chung",
                "NgayVanBan": "Ngày ban hành mới nhất",
                "CoQuanBanHanh": "Cơ quan ban hành",
                "HoTenNguoiKy": "Người ký văn bản mới nhất",
                "ChucVuNguoiKy": "Chức vụ người ký",
                "NgonNgu": "Ngôn ngữ văn bản",
                "MaHoSo": "Mã hồ sơ",
                "TongSoTrang": "Tổng số trang",
                "GhiChu": "Ghi chú về việc gộp văn bản"
            }},
            "DataTable": [
                {{
                    "stt": 1,
                    "hangMucChiPhi": "Tên hạng mục (đã gộp)",
                    "daPheDuyetDong": "Số tiền đã phê duyệt mới nhất",
                    "sauDieuChinhDong": "Số tiền sau điều chỉnh mới nhất",
                    "tangGiam": "Số tiền tăng/giảm được tính lại",
                    "ghiChu": "Ghi chú về nguồn gốc và thay đổi số liệu"
                }}
            ]
        }}

        Lưu ý quan trọng:
        1. Ưu tiên số liệu mới nhất từ các văn bản
        2. Gộp các hạng mục tương tự để tránh trùng lặp
        3. Tính toán lại số tiền tăng/giảm dựa trên số liệu mới
        4. Thêm ghi chú rõ ràng về nguồn gốc số liệu
        5. Đảm bảo tính nhất quán trong việc gộp dữ liệu
        """.format("\n\n".join([f"Văn bản {i+1} ({data['filename']}):\n{data['content']}" for i, data in enumerate(all_data)]))

        duLieuSoHoa = chat_with_openai_json(combined_prompt)

        try:
            data_json = json.loads(duLieuSoHoa)
            thong_tin_chung = data_json.get("Data", {})
            data_table = data_json.get("DataTable", [])
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
            'ChucVuNguoiKy': ('ghiChu', lambda x: ""),
            'NgonNgu': ('maNgonNgupr_sd', lambda x: "01"),
            'MaHoSo': ('sttHoSoLuuTrupr_sd', lambda x: x if x else "HS_" + datetime.now().strftime("%Y%m%d")),
            'TongSoTrang': ('soLuongTrang', lambda x: x if x else "1"),
            'VanBanID': ('sttHoSoLuuTruCTpr', lambda x: str(uuid.uuid4())),
            'VanBanCode': ('vanBanCode', lambda x: f"VB_{datetime.now().strftime('%Y%m%d%H%M%S')}"),
            'NgayThaoTac': ('ngayThaoTac', lambda x: current_time),
            'NoiDung': ('noiDung', lambda x: ""),
            'DinhKem': ('dinhKem', lambda x: ", ".join(d['filename'] for d in all_data)),
        }

        for ai_field, (db_field, transform_func) in mapping_rules.items():
            if ai_field in thong_tin_chung:
                mapped_data[db_field] = transform_func(thong_tin_chung[ai_field])
            else:
                mapped_data[db_field] = transform_func(None)

        for db_field in FIELD_MAPPING.keys():
            if db_field not in mapped_data:
                mapped_data[db_field] = ""

        return {
            "success": True,
            "data": mapped_data,
            "dataTable": data_table,
            "files_processed": [{"filename": d['filename']} for d in all_data]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file) 