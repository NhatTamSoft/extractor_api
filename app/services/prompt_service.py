from typing import Dict, Optional, Tuple, List
import re
from app.services.database_service import DatabaseService
from app.services.DungChung import lay_du_lieu_tu_sql_server

class PromptService:
    def __init__(self):
        self.prompts: Dict[str, Tuple[str, List[str]]] = {}
        self._load_prompts()

    def _load_prompts(self):
        """Tải các prompt từ file prompt"""
        try:
            with open('data/promt_documentai.md', 'r', encoding='utf-8') as file:
                content = file.read()
                # Phân tách nội dung theo {{CHUCNANG01}}
                sections = re.split(r'{{CHUCNANG\d+}}', content)
                #print(sections)
                for section in sections:
                    if not section.strip():
                        continue
                    # Trích xuất KyHieu từ phần
                    ky_hieu_match = re.search(r'\`KyHieu\`:\s*"([^"]+)"', section)
                    if not ky_hieu_match:
                        continue
                        
                    ky_hieu = ky_hieu_match.group(1)
                    prompt = section.strip()
                    prompt = prompt + """
🎯 Lưu ý: 
1. Trích **chính xác tên cơ quan trực tiếp ban hành văn bản** theo các quy tắc sau:
* Nếu văn bản có:
  * Dòng 1 là cơ quan chủ quản (VD: “UBND TỈNH...”)
  * Dòng 2 là tên địa phương (VD: “HUYỆN...”)
  * Dòng 3 là đơn vị trực thuộc (VD: “BAN QLDA...”)
    → **Chỉ lấy dòng 3** làm cơ quan ban hành.
* Nếu chỉ có 1 dòng hoặc 2 dòng mà không có đơn vị trực thuộc → có thể ghép lại (VD: “ỦY BAN NHÂN DÂN HUYỆN ...”).
✅ Không bao giờ lấy cơ quan chủ quản nếu có đơn vị cấp dưới trực tiếp ký văn bản.

2. Trích **SoVanBan**, **SoVanBanCanCu** hoặc **TrichYeu** đúng chính xác, giữ nguyên ký hiệu đầy đủ, bao gồm dấu tiếng Việt. Đặc biệt:
🔒 Bắt buộc giữ nguyên các chữ viết tắt có dấu trong số hiệu văn bản, gồm:
- **"QĐ"** - viết tắt của "Quyết định"
- **"HĐND"** - viết tắt của "Hội đồng nhân dân"
- **"HĐ"** - viết tắt của "Hợp đồng" hoặc "Hội đồng"
- **"TĐ"** - viết tắt của "Thẩm định"
- **"HĐTĐ"** - viết tắt của "Hội đồng thẩm định"
- Các từ viết tắt khác có chữ **"Đ"**, **không được chuyển thành "D"**

3. Trong quá trình nhận dạng, nếu có sự mờ, nhiễu hoặc khó đọc, hãy ưu tiên dự đoán các ký tự theo nguyên tắc sau:
- 1 dễ nhầm với 7, 4, I, l → ưu tiên chọn 1 nếu toàn bộ chuỗi khớp mẫu.
- 0 dễ nhầm với O, D, Q → nếu đi kèm văn bản hành chính thì chọn 0.
- 2 dễ nhầm với Z, S → nếu xuất hiện ở đầu chuỗi thì ưu tiên là 2.
- 5 dễ nhầm với S → nếu nằm trong số hiệu thì ưu tiên là 5.
- 8 dễ nhầm với B, 3 → nếu ký tự đi kèm là “Công văn” thì chọn B, ngược lại chọn 8.
- 9 dễ nhầm với g, q, 4 → nếu trong cụm số hiệu thì chọn 9.
- Chỉ chấp nhận kết quả nếu thỏa mãn regex định dạng chuẩn: ^\d{1,6}(/[A-Z0-9]{1,6})?/QĐ-UBND(\.\w+|-?\w+)?$
- Trả về duy nhất chuỗi số hiệu văn bản hợp lệ. Nếu không nhận diện được đúng mẫu, trả về chuỗi rỗng ""

4. Bạn PHẢI trả về **duy nhất một chuỗi JSON hợp lệ**, KHÔNG thêm văn bản, giải thích hoặc định dạng khác
```
{
    "ThongTinChung": {
        "tên cột": "giá trị"
    },
    "BangDuLieu": [
        {
            "tên cột": "giá trị"
        }
        ...
    ]
}
```
"""
                    # Trích xuất các cột bắt buộc dựa trên ky_hieu
                    required_columns = self._get_required_columns(ky_hieu)
                    # print("=====required_columns=====")
                    # print(required_columns)
                    self.prompts[ky_hieu] = (prompt, required_columns)
        except Exception as e:
            print(f"Lỗi khi tải prompts: {str(e)}")
            # Khởi tạo với prompts rỗng nếu việc tải file thất bại
            self.prompts = {}

    def _get_required_columns(self, loai_van_ban: str) -> List[str]:
        """Lấy các cột bắt buộc dựa trên loaiVanBan"""
        # Các cột mặc định luôn bắt buộc
        default_columns = ["TenKMCP"]
        try:
            # Thực hiện truy vấn SQL để lấy dữ liệu
            query = """select NghiepVuID=ChucNangAIID, BangDuLieu from ChucNangAI order by STT"""
            result = lay_du_lieu_tu_sql_server(query)
            # Khởi tạo dictionary để lưu kết quả
            column_mapping = {}
            
            # Duyệt qua từng dòng kết quả
            for _, row in result.iterrows():
                # Lấy NghiepVuID và BangDuLieu
                nghiep_vu_id = row['NghiepVuID']
                bang_du_lieu = row['BangDuLieu']
                # Tách BangDuLieu thành mảng các cột bằng dấu ;
                columns = bang_du_lieu.split(';')
                # Thêm vào dictionary
                column_mapping[nghiep_vu_id] = columns
            # print("--------------------------------")
            # print(column_mapping.get(loai_van_ban, default_columns))
            return column_mapping.get(loai_van_ban, default_columns)
            
        except Exception as e:
            print(f"Lỗi khi lấy dữ liệu từ CSDL: {str(e)}")
            return default_columns

    def get_prompt(self, loai_van_ban: Optional[str]) -> Tuple[str, List[str]]:
        """
        Lấy prompt và các cột bắt buộc cho một loaiVanBan cụ thể
        Nếu loaiVanBan là None hoặc không tìm thấy, trả về prompt và các cột mặc định
        """
        if loai_van_ban and loai_van_ban in self.prompts:
            return self.prompts[loai_van_ban]
        # Trả về prompt và các cột mặc định nếu không tìm thấy loaiVanBan
        return "", []