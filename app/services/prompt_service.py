from typing import Dict, Optional, Tuple, List

class PromptService:
    def __init__(self):
        self.prompts: Dict[str, Tuple[str, List[str]]] = {}
        self._load_prompts()

    def _load_prompts(self):
        """Load prompts from the prompt file"""
        try:
            with open('data/promt_quettailieu.txt', 'r', encoding='utf-8') as file:
                content = file.read()
                # Split content by [*********]
                sections = content.split('[*********]')
                
                for section in sections:
                    if not section.strip():
                        continue
                    
                    # Split section into header and prompt
                    parts = section.strip().split('\n', 1)
                    if len(parts) != 2:
                        continue
                    
                    # Extract loaiVanBan from header
                    header = parts[0].strip()
                    if header.startswith('[') and header.endswith(']'):
                        loai_van_ban = header[1:-1]
                        prompt = parts[1].strip()
                        
                        # Extract required columns based on loaiVanBan
                        required_columns = self._get_required_columns(loai_van_ban)
                        self.prompts[loai_van_ban] = (prompt, required_columns)
        except Exception as e:
            print(f"Error loading prompts: {str(e)}")
            # Initialize with empty prompts if file loading fails
            self.prompts = {}

    def _get_required_columns(self, loai_van_ban: str) -> List[str]:
        """Get required columns based on loaiVanBan"""
        # Default columns that are always required
        default_columns = ["TenKMCP"]
        
        # Map loaiVanBan to required columns
        column_mapping = {
            'QDPD_CT': default_columns + ["GiaTriTMDTKMCP", "GiaTriTMDTKMCP_DC", "GiaTriTMDTKMCPTang", "GiaTriTMDTKMCPGiam"],
            'QDPDDT_CBDT': default_columns + ["GiaTriDuToanKMCP", "GiaTriDuToanKMCP_DC", "GiaTriDuToanKMCPTang", "GiaTriDuToanKMCPGiam"],
            'QDPD_KHLCNT_CBDT': default_columns + ["TenDauThau", "GiaTriGoiThau", "TenNguonVon", "HinhThucLCNT", "PhuongThucLCNT", "ThoiGianTCLCNT", "LoaiHopDong", "ThoiGianTHHopDong"],
            'QDPD_DA': default_columns + ["GiaTriTMDTKMCP", "GiaTriTMDTKMCP_DC", "GiaTriTMDTKMCPTang", "GiaTriTMDTKMCPGiam"],
            'QDPD_DT_THDT': default_columns + ["GiaTriDuToanKMCP", "GiaTriDuToanKMCP_DC", "GiaTriDuToanKMCPTang", "GiaTriDuToanKMCPGiam"],
            'QDPD_KHLCNT_THDT': default_columns + ["TenDauThau", "GiaTriGoiThau", "TenNguonVon", "HinhThucLCNT", "PhuongThucLCNT", "ThoiGianTCLCNT", "LoaiHopDong", "ThoiGianTHHopDong"]
        }
        
        return column_mapping.get(loai_van_ban, default_columns)

    def get_prompt(self, loai_van_ban: Optional[str]) -> Tuple[str, List[str]]:
        """
        Get the prompt and required columns for a specific loaiVanBan
        If loaiVanBan is None or not found, return the default prompt and columns
        """
        if loai_van_ban and loai_van_ban in self.prompts:
            return self.prompts[loai_van_ban]
        
        # Return default prompt and columns if loaiVanBan is not found
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
6. Các thông giá trị trong BangDuLieu chỉ hiện số không cần định dạng
""", default_columns 