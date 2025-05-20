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
            with open('data/promt_quettailieu.txt', 'r', encoding='utf-8') as file:
                content = file.read()
                # Phân tách nội dung theo {{CHUCNANG01}}
                sections = re.split(r'{{CHUCNANG\d+}}', content)
                #print(sections)
                for section in sections:
                    if not section.strip():
                        continue
                    # Trích xuất KyHieu từ phần
                    ky_hieu_match = re.search(r'\*\*KyHieu\*\*:\s*"([^"]+)"', section)
                    if not ky_hieu_match:
                        continue
                        
                    ky_hieu = ky_hieu_match.group(1)
                    prompt = section.strip()
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
        default_columns = ["TenKMCP", "GiaTriTMDTKMCP", "GiaTriTMDTKMCP_DC", "GiaTriTMDTKMCPTang", "GiaTriTMDTKMCPGiam"]
        return """
Dựa vào các tài liệu đã được cung cấp, hãy phân tích và gộp thông tin thành một đối tượng JSON duy nhất.
Yêu cầu trích xuất:
1.  **Thông tin chung của văn bản:**
    * `SoVanBan`: Số hiệu văn bản mới nhất.
    * `NgayKy`: Ngày ký văn bản mới nhất, chuyển đổi sang định dạng `dd/mm/yyyy`.
    * `NguoiKy`: Người ký văn bản mới nhất.
    * `ChucDanhNguoiKy`: Chức danh của người ký mới nhất (ví dụ: "Chủ tịch", "Phó Chủ tịch").
    * `CoQuanBanHanh`: Cơ quan ban hành văn bản.
    * `TrichYeu`: Trích yếu nội dung văn bản (tổng hợp từ các văn bản).
    * `DieuChinh`: Đặt giá trị là `1` nếu là văn bản điều chỉnh. Ngược lại giá trị là `0`.
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
   "DieuChinh":"1 nếu có văn bản điều chỉnh, 0 nếu không",
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
6. Các thông giá trị trong BangDuLieu chỉ hiện số không cần định dạng
""", default_columns 