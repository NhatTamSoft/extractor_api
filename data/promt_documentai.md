{{CHUCNANG02}} Chức năng `Quyết định phê duyệt chủ trương đầu tư`
### Văn bản để nhận dạng thông tin là: "Quyết định phê duyệt chủ trương đầu tư hoặc phê duyệt điều chỉnh chủ trương đầu tư"
### Thông tin chung của văn bản, tên đối tượng (object) "ThongTinChung":
`KyHieu`: "QDPD_CT"
`SoVanBan`: Trích số hiệu văn bản ghi ở đầu văn bản, sau chữ "Số:"
`NgayKy`: Trích thông tin ngày ký ở đầu văn bản, sau dòng địa danh "..., ngày ..." định dạng (dd/MM/yyyy)
`SoVanBanCanCu`: Trích "số hiệu văn bản" Báo cáo thẩm định báo cáo đề xuất chủ trương đầu tư, tại dòng "Căn cứ Báo cáo thẩm định số..." hoặc "Căn cứ Báo cáo số ..." có chứa cụm từ "báo cáo đề xuất chủ trương đầu tư..."
`NgayKyCanCu`: Trích "ngày...tháng...năm ... Báo cáo thẩm định" báo cáo đề xuất chủ trương đầu tư, tại dòng "Căn cứ Báo cáo thẩm định số..." hoặc "Căn cứ Báo cáo số ..." có chứa cụm từ "báo cáo đề xuất chủ trương đầu tư..."  định dạng (dd/MM/yyyy)
`NguoiKy`: Trích tên người ký văn bản ở phần cuối văn bản, ngay dưới dòng "KT. CHỦ TỊCH" hoặc "CHỦ TỊCH".
`ChucDanhNguoiKy`: Trích phần ghi rõ chức vụ người ký văn bản (VD: "CHỦ TỊCH", "PHÓ CHỦ TỊCH", "KT. CHỦ TỊCH – PHÓ CHỦ TỊCH").
`CoQuanBanHanh`: Trích xuất chính xác tên cơ quan ban hành văn bản theo đúng quy định tại Nghị định 30/2020/NĐ-CP về công tác văn thư. Nếu dòng đầu là tên cơ quan chủ quản và dòng thứ hai là đơn vị trực thuộc thì chỉ lấy dòng thứ hai làm cơ quan ban hành.
`TrichYeu`: Trích nguyên văn phần tiêu đề nằm ngay sau chữ "QUYẾT ĐỊNH", thường bắt đầu bằng "Về việc..." hoặc "V/v..." hoặc "Về chủ trương...".
`TenNguonVon`: Trích tên nguồn vốn sau cụm từ "nguồn vốn: ...", nếu không có để ""
`GiaTri`: Trích thông tin số tiền ngay sau cụm từ "tổng mức đầu tư", thường bắt đầu bằng "tổng mức đầu tư..." hoặc "... kinh phí" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`DieuChinh`: Gán giá trị `1` nếu nội dung phần tiêu đề văn bản có cụm từ chứa "điều chỉnh". Nếu không có, gán `0`.
### Bảng số liệu tổng mức đầu tư, mỗi dòng là một bản ghi với các cột sau, tên đối tượng (object): "BangDuLieu":
`TenKMCP`: Tên khoản mục chi phí, giữ nguyên tên khoản mục chi phí theo văn bản
`GiaTriTMDTKMCP`: Giá trị thành tiền hoặc giá trị cột **"Sau thuế"**, không lấy cột "Trước thuế" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`GiaTriTMDTKMCPTang`: Nếu `DieuChinh` bằng `1` thì trích "Giá trị tổng mức đầu tư tăng" ngược lại gán `0` (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`GiaTriTMDTKMCPGiam`: Nếu `DieuChinh` bằng `1` thì trích "Giá trị tổng mức đầu tư giảm" ngược lại gán `0` (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
### 🚫 **Quy tắc loại bỏ khoản mục chi phí**:
Nếu một dòng **thuộc "Danh sách khoản mục chi phí"** dưới đây thì:
❌ **Không xuất dòng không thuộc "Danh sách Khoản mục chi phí"**
✅ **Chỉ xuất các dòng thuộc "Danh sách Khoản mục chi phí"**
**Danh sách Khoản mục chi phí**
| Mã  |Tên khoản mục chi phí                         |
|-----|----------------------------------------------|
|`CP1`|Chi phí bồi thường, hỗ trợ, tái định cư       |
|`CP2`|Chi phí xây dựng                              |
|`CP3`|Chi phí thiết bị                              |
|`CP4`|Chi phí quản lý dự án                         |
|`CP5`|Chi phí tư vấn đầu tư xây dựng                |
|`CP6`|Chi phí khác                                  |
|`CP7`|Chi phí dự phòng                              |

### Yêu cầu xử lý:
🚫 **Không lấy giá trị trong cột "Trước thuế"**
✅ Chỉ lấy giá trị tại đúng cột có tiêu đề "Sau thuế"
- Gộp toàn bộ bảng trong tất cả ảnh thành một danh sách duy nhất, đúng thứ tự
- Giữ nguyên tên gọi và định dạng số tiền như trong ảnh, không tự ý chuẩn hóa
- Không suy diễn hoặc bổ sung thông tin không có trong văn bản
- Tự động loại bỏ dấu chấm phân cách hàng nghìn trong số tiền
- Hãy trích xuất chính xác chuỗi ký tự trước chữ ‘đồng’, bao gồm cả dấu chấm như trong bản gốc



{{CHUCNANG03}} Chức năng `Quyết định phê duyệt dự toán giai đoạn chuẩn bị đầu tư`
Bạn phải thực hiện theo các bước sau và trả về **duy nhất một chuỗi JSON hợp lệ** với cấu trúc:
{
  "ThongTinChung": {
    "KyHieu": "...",
    "SoVanBan": "...",
    "NgayKy": "...",
    "SoVanBanCanCu": "...",
    "NgayKyCanCu": "...",
    "NguoiKy": "...",
    "ChucDanhNguoiKy": "...",
    "CoQuanBanHanh": "...",
    "TrichYeu": "...",
    "TenNguonVon": "...",
    "GiaTri": ...,
    "DieuChinh": 0 hoặc 1
  },
  "BangDuLieu": [
    {
      "TenKMCP": "...",
      "GiaTriDuToanKMCP": ...,
      "GiaTriDuToanKMCPTang": ...,
      "GiaTriDuToanKMCPGiam": ...
    }
  ]
}
## 🔹 BƯỚC 1: Trích ThongTinChung từ nội dung dưới đây
### Thông tin chung của văn bản, tên đối tượng (object) "ThongTinChung":
Quy tắc bắt buộc:
- Chỉ lấy các dòng là khoản mục chi phí con, có số tiền ở cột "Sau thuế" hoặc cột giá trị. Nếu không có chi phí con thì lấy chi phí cha
- Không lấy dòng cha (trường hợp có dòng con), dòng nhóm, dòng mô tả, dòng tổng, dòng tiêu đề, dòng trống
- Tuyệt đối không được bỏ sót bất kỳ dòng khoản mục con nào nếu có số tiền
- Không được gộp, không tự suy diễn, không sửa tên khoản mục hay số tiền
- Duyệt từng dòng, kiểm tra kỹ cột số tiền
- Đối với "Bảng tổng hợp chi phí"
+ Chỉ lấy các khoản mục nếu chưa xuất hiện trong bảng chi tiết ở trên và thêm vào cuối bảng chi tiết.
+ Không lấy dòng mô tả, chỉ lấy dòng có giá trị tiền.
- Chỉ trả về danh sách các khoản mục hợp lệ dạng JSON (không thêm text giải thích).
`KyHieu`: "QDPDDT_CBDT"
`SoVanBan`: Trích số hiệu văn bản ghi ở đầu văn bản, sau chữ "Số:"
`NgayKy`: Trích thông tin ngày ký ở đầu văn bản, sau dòng địa danh "..., ngày ...", định dạng (dd/MM/yyyy)
`SoVanBanCanCu`: Trích "số hiệu văn bản" Báo cáo thẩm định dự toán..., tại dòng "Căn cứ Báo cáo thẩm định dự toán..." có chứa cụm từ "Báo cáo thẩm định dự toán..."
`NgayKyCanCu`: Trích "ngày...tháng...năm ..." Báo cáo thẩm định dự toán..., tại dòng "Căn cứ Báo cáo thẩm định dự toán..." có chứa cụm từ "Báo cáo thẩm định dự toán..." định dạng (dd/MM/yyyy)
`NguoiKy`: Trích tên người ký văn bản ở phần cuối văn bản, ngay dưới dòng "KT. CHỦ TỊCH" hoặc "CHỦ TỊCH" hoặc "KT. GIÁM ĐỐC" hoặc "GIÁM ĐỐC".
`ChucDanhNguoiKy`: Trích phần ghi rõ chức vụ người ký văn bản (VD: "CHỦ TỊCH", "PHÓ CHỦ TỊCH", "KT. CHỦ TỊCH – PHÓ CHỦ TỊCH").
`CoQuanBanHanh`: Trích xuất chính xác tên cơ quan ban hành văn bản theo đúng quy định tại Nghị định 30/2020/NĐ-CP về công tác văn thư. Nếu dòng đầu là tên cơ quan chủ quản và dòng thứ hai là đơn vị trực thuộc thì chỉ lấy dòng thứ hai làm cơ quan ban hành.
`TrichYeu`: Trích nguyên văn phần tiêu đề nằm ngay sau chữ "QUYẾT ĐỊNH", thường bắt đầu bằng "Về việc..." hoặc "V/v..." hoặc "Về việc phê duyệt Báo cáo..."
`TenNguonVon`: Trích tên nguồn vốn sau cụm từ "nguồn vốn: ...", nếu không có để ""
`GiaTri`: Trích thông tin số tiền ngay sau cụm từ "giá trị dự toán", thường tại dòng "Bằng chữ: ..." (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`DieuChinh`: Gán `1` nếu "trích yếu văn bản" có chứa nội dung "điều chỉnh...", ngược lại gán `0`
## 🔷 BƯỚC 2: Trích `BangDuLieu`
Bạn PHẢI xử lý theo đúng trình tự sau:
### ▶️ 1. Phần `START_BANG_CHI_TIET`:
Đây là **bảng chi tiết**, gồm nhiều dòng chi phí con. Dạng bảng gồm các cột:
**STT | Tên khoản mục chi phí | Cách tính | Trước thuế | Sau thuế | Ký hiệu**
**Yêu cầu xử lý:**
- Chỉ lấy các dòng có **giá trị ở cột "Sau thuế"**.
- **KHÔNG lấy dòng mô tả hoặc nhóm**, cụ thể như: "Công trình dân dụng", "Công trình công nghiệp", "Công trình giao thông", "Công trình nông nghiệp và phát triển nông thôn", "Công trình hạ tầng kỹ thuật".
- Nếu khoản mục là dòng con thuộc nhóm lớn (vd: “Chi phí lập báo cáo…” nằm trong “Chi phí tư vấn đầu tư xây dựng”) → vẫn PHẢI lấy dòng con, **KHÔNG lấy dòng cha**.
**Trường dữ liệu cần trích từ mỗi dòng:**
- `TenKMCP`: tên khoản mục chi phí (giữ nguyên)
- `GiaTriDuToanKMCP`: lấy cột “Sau thuế”
- `GiaTriDuToanKMCPTang`: nếu "DieuChinh" = 1 → lấy “Giá trị tăng”, nếu không thì = 0
- `GiaTriDuToanKMCPGiam`: nếu "DieuChinh" = 1 → lấy “Giá trị giảm”, nếu không thì = 0

### ▶️ 2. Phần `START_BANG_TONG_HOP`:
Đây là **bảng tổng hợp chi phí**.

**Yêu cầu xử lý:**
- Chỉ lấy các khoản mục nếu **chưa xuất hiện trong bảng chi tiết** ở trên.
- Không lấy dòng mô tả, chỉ lấy dòng có giá trị tiền.

### ▶️ 3. ĐẶC BIỆT: Trường hợp ngắt dòng do OCR không có Phần `START_BANG_TONG_HOP`:
Nếu khoản mục chi phí nằm ở một dòng, còn số tiền nằm ở dòng kế tiếp, ví dụ:
- Chi phí giải phóng mặt bằng  
:  
9.999 đồng

→ Vẫn phải gộp lại và trích như sau:
{
  "TenKMCP": "Chi phí giải phóng mặt bằng",
  "GiaTriDuToanKMCP": 9999,
  "GiaTriDuToanKMCPTang": 0,
  "GiaTriDuToanKMCPGiam": 0
}

## ⚠️ CHỈ TRẢ VỀ MỘT ĐỐI TƯỢNG JSON DUY NHẤT
- Không trả lời thêm giải thích
- Không ghi chữ “Dưới đây là kết quả” hay mô tả nào khác

## 🔁 Ví dụ mẫu (để API học đúng format):

```json
{
  "TenKMCP": "Chi phí lập báo cáo kinh tế kỹ thuật",
  "GiaTriDuToanKMCP": 888,
  "GiaTriDuToanKMCPTang": 0,
  "GiaTriDuToanKMCPGiam": 0
}




{{CHUCNANG04}} Chức năng `Quyết định phê duyệt kế hoạch lựa chọn nhà thầu (viết tắt: "KHLCNT") giai đoạn chuẩn bị đầu tư`
### Văn bản để nhận dạng thông tin là`: "Quyết định phê duyệt KHLCNT giai đoạn chuẩn bị đầu tư, quyết định điều chỉnh KHLCNT giai đoạn chuẩn bị đầu tư"
### Thông tin chung của văn bản, tên đối tượng (object) "ThongTinChung":
`KyHieu`: "QDPD_KHLCNT_CBDT"
`SoVanBan`: Trích số hiệu văn bản ghi ở đầu văn bản, sau chữ "Số:"
`NgayKy`: Trích thông tin ngày ký ở đầu văn bản, sau dòng địa danh "..., ngày ...", định dạng (dd/MM/yyyy)
`SoVanBanCanCu`: Trích "số hiệu văn bản" quyết định phê duyệt dự toán nhiệm vụ, tại dòng "Căn cứ Quyết định số..." có chứa cụm từ "phê duyệt dự toán nhiệm vụ..."
`NgayKyCanCu`: Trích "ngày...tháng...năm ..." quyết định phê duyệt dự toán nhiệm vụ, tại dòng "Căn cứ Quyết định số..." có chứa cụm từ "phê duyệt dự toán nhiệm vụ..." định dạng (dd/MM/yyyy)
`NguoiKy`: Trích tên người ký văn bản ở phần cuối văn bản, ngay dưới dòng "KT. CHỦ TỊCH" hoặc "CHỦ TỊCH".
`ChucDanhNguoiKy`: Trích phần ghi rõ chức vụ người ký văn bản (VD: "CHỦ TỊCH", "PHÓ CHỦ TỊCH", "KT. CHỦ TỊCH – PHÓ CHỦ TỊCH").
`CoQuanBanHanh`: Trích xuất chính xác tên cơ quan ban hành văn bản theo đúng quy định tại Nghị định 30/2020/NĐ-CP về công tác văn thư. Nếu dòng đầu là tên cơ quan chủ quản và dòng thứ hai là đơn vị trực thuộc thì chỉ lấy dòng thứ hai làm cơ quan ban hành.
`TrichYeu`: Trích nguyên văn phần tiêu đề nằm ngay sau chữ "QUYẾT ĐỊNH", thường bắt đầu bằng "Về việc..." hoặc "V/v..." hoặc "Về việc phê duyệt Báo cáo...".
`GiaTri`: Trích cột giá gói thầu, thường tại dòng "Tổng cộng..." (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`DieuChinh`: Gán giá trị `1` nếu nội dung phần tiêu đề văn bản có cụm từ chứa "điều chỉnh". Nếu không có, gán `0`.
### Bảng Phụ lục gói thầu, mỗi dòng là một bản ghi với các cột sau, tên đối tượng (object): "BangDuLieu":
`TenDauThau`: Trích tên đầy đủ của gói thầu
`TenKMCP`: Nếu `TenDauThau` có chứa cụm từ "bảo hiểm" thì `TenKMCP` = "Chi phí bảo hiểm", nếu `TenDauThau` có chứa cụm từ "thi công xây dựng" hoặc "thi công xây lắp" thì `TenKMCP` = "Chi phí xây dựng" ngược lại gán `TenDauThau` vào cột `TenKMCP`
`GiaTriGoiThau`: Trích cột giá gói thầu (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`TenNguonVon`: Trích cột nguồn vốn, nếu không có để ""
`HinhThucLCNT`: Trích cột hình thức lựa chọn nhà thầu
`PhuongThucLCNT`: Trích cột phương thức lựa chọn nhà thầu
`ThoiGianTCLCNT`: Trích cột thời gian bắt đầu tổ chức lựa chọn nhà thầu
`LoaiHopDong`: Trích cột loại hợp đồng
`ThoiGianTHHopDong`: Trích cột thời gian thực hiện hợp đồng
### Yêu cầu xử lý:
- Không suy diễn hoặc bổ sung thông tin không có trong văn bản
- Tự động loại bỏ dấu chấm phân cách hàng nghìn trong số tiền
- Tách từng dòng con trong phần "Trong đó" ra như một gói thầu độc lập (nếu có)



{{CHUCNANG05}} Chức năng `Quyết định phê duyệt kết quả lựa chọn nhà thầu (viết tắt: "KQLCNT") giai đoạn chuẩn bị đầu tư`
### Văn bản để nhận dạng thông tin là`: "Quyết định phê duyệt KQLCNT giai đoạn chuẩn bị đầu tư, quyết định điều chỉnh KQLCNT giai đoạn chuẩn bị đầu tư"
### Thông tin chung của văn bản, tên đối tượng (object) "ThongTinChung":
`KyHieu`: "QDPD_KQLCNT_CBDT"
`SoVanBan`: Trích số hiệu văn bản ghi ở đầu văn bản, sau chữ "Số:"
`SoVanBanCanCuQD`: Trích `số hiệu quyết định phê duyệt kế hoạch lựa chọn nhà thầu`, tại dòng "Căn cứ Quyết định ... phê duyệt kế hoạch lựa chọn nhà thầu"
`SoVanBanCanCuDC`: Trích `số hiệu quyết định phê duyệt kế hoạch lựa chọn nhà thầu`, tại dòng "Căn cứ Quyết định ... phê duyệt điều chỉnh kế hoạch lựa chọn nhà thầu"
`SoVanBanCanCu`: Kết hợp tất cả các số hiệu từ `SoVanBanCanCuQD` và `SoVanBanCanCuDC` thành một chuỗi, các số hiệu cách nhau bằng dấu ;. Nếu không có số hiệu nào thì để trống.
`NgayKyCanCu`: Trích "ngày...tháng...năm ..." Quyết định phê duyệt kế hoạch lựa chọn nhà thầu, tại dòng "Căn cứ Quyết định ... phê duyệt kế hoạch lựa chọn nhà thầu" định dạng (dd/MM/yyyy)
`NgayKy`: Trích thông tin ngày ký ở đầu văn bản, sau dòng địa danh "..., ngày ...", định dạng "dd/MM/yyyy"
`NguoiKy`: Trích tên người ký văn bản ở phần cuối văn bản.
`ChucDanhNguoiKy`: Trích phần ghi rõ chức vụ người ký văn bản.
`CoQuanBanHanh`: Trích xuất chính xác tên cơ quan ban hành văn bản theo đúng quy định tại Nghị định 30/2020/NĐ-CP về công tác văn thư. Nếu dòng đầu là tên cơ quan chủ quản và dòng thứ hai là đơn vị trực thuộc thì chỉ lấy dòng thứ hai làm cơ quan ban hành.
`TrichYeu`: Trích nguyên văn tiêu đề ngay dưới dòng "QUYẾT ĐỊNH" (thường bắt đầu bằng "Về việc...")
`TenNhaThau`: Trích từ dòng "đơn vị chỉ định thầu" hoặc "đơn vị trúng thầu"
`GiaTri`: Trích thông tin số tiền ngay sau cụm từ "giá chỉ định thầu" hoặc "giá trị trúng thầu", thường tại dòng "Bằng chữ: ..." (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`DieuChinh`: Gán giá trị `1` nếu nội dung phần tiêu đề văn bản có cụm từ chứa "điều chỉnh". Nếu không có, gán `0`.
### Bảng dữ liệu gói thầu, mỗi dòng là một bản ghi với các cột sau, tên đối tượng (object): "BangDuLieu":
`TenDauThau`: Trích `tên gói thầu`, sau cụm từ "Nội dung gói thầu:..." hoặc "Tên gói thầu:..."
`TenKMCP`: Nếu `TenDauThau` có chứa cụm từ "bảo hiểm" thì `TenKMCP` = "Chi phí bảo hiểm", nếu `TenDauThau` có chứa cụm từ "thi công xây dựng" hoặc "thi công xây lắp" thì `TenKMCP` = "Chi phí xây dựng" ngược lại gán `TenDauThau` vào cột `TenKMCP`
`TenNhaThau`: Trích từ dòng "đơn vị chỉ định thầu" hoặc "đơn vị trúng thầu"
`ThoiGianTHHopDong`: Trích từ dòng "Thời gian thực hiện hợp đồng: ... ngày"
`LoaiHopDong`: Trích từ dòng "Loại hợp đồng: ..."
`GiaTrungThau`: Trích thông tin số tiền ngay sau cụm từ "giá chỉ định thầu" hoặc "giá trị trúng thầu", thường tại dòng "Bằng chữ: ..." (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
### Yêu cầu xử lý:
- Không suy diễn hoặc bổ sung thông tin không có trong văn bản
- Tự động loại bỏ dấu chấm phân cách hàng nghìn trong số tiền
- Tách từng dòng con trong phần "Trong đó" ra như một gói thầu độc lập (nếu có)


{{CHUCNANG06}} Chức năng "Quyết định phê duyệt dự án"
`Văn bản để nhận dạng thông tin là`: "Quyết định phê duyệt dự án hoặc phê duyệt điều chỉnh phê duyệt dự án"
### Thông tin chung của văn bản, tên đối tượng (object) "ThongTinChung":
`KyHieu`: "QDPD_DA"
`Thông tin chung của văn bản`:
`SoVanBan`: Trích số hiệu văn bản ghi ở đầu văn bản, sau chữ "Số:"
`NgayKy`: Trích thông tin ngày ký ở đầu văn bản, sau dòng địa danh "..., ngày ...", định dạng (dd/MM/yyyy)
`SoVanBanCanCu`: Trích "số hiệu văn bản" phê duyệt chủ trương đầu tư hoặc phê duyệt điều chỉnh chủ trương đầu tư, tại dòng "Căn cứ Quyết định số..." có chứa cụm từ "phê duyệt chủ trương đầu tư..."
`NgayKyCanCu`: Trích "ngày...tháng...năm ..." phê duyệt chủ trương đầu tư hoặc phê duyệt điều chỉnh chủ trương đầu tư, tại dòng "Căn cứ Quyết định số..." có chứa cụm từ "phê duyệt chủ trương đầu tư..." định dạng (dd/MM/yyyy)
`NguoiKy`: Trích tên người ký văn bản ở phần cuối văn bản, ngay dưới dòng "KT. CHỦ TỊCH" hoặc "CHỦ TỊCH".
`ChucDanhNguoiKy`: Trích phần ghi rõ chức vụ người ký văn bản (VD: "CHỦ TỊCH", "PHÓ CHỦ TỊCH", "KT. CHỦ TỊCH – PHÓ CHỦ TỊCH").
`CoQuanBanHanh`: Trích xuất chính xác tên cơ quan ban hành văn bản theo đúng quy định tại Nghị định 30/2020/NĐ-CP về công tác văn thư. Nếu dòng đầu là tên cơ quan chủ quản và dòng thứ hai là đơn vị trực thuộc thì chỉ lấy dòng thứ hai làm cơ quan ban hành.
`TrichYeu`: Trích nguyên văn phần tiêu đề nằm ngay sau chữ "QUYẾT ĐỊNH", thường bắt đầu bằng "Về việc..." hoặc "V/v..." hoặc "Về việc phê duyệt...".
`TenNguonVon`: Trích tên nguồn vốn sau cụm từ "nguồn vốn: ...", nếu không có để ""
`GiaTri`: Trích thông tin số tiền ngay sau cụm từ "tổng mức đầu tư", thường bắt đầu bằng "tổng mức đầu tư..." hoặc "... kinh phí" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`DieuChinh`: Gán giá trị `1` nếu nội dung phần tiêu đề văn bản có cụm từ chứa "điều chỉnh". Nếu không có, gán `0`.
### Bảng số liệu tổng mức đầu tư, mỗi dòng là một bản ghi với các cột sau, tên đối tượng (object): "BangDuLieu":
`TenKMCP`: Tên khoản mục chi phí, giữ nguyên tên khoản mục chi phí theo văn bản
`GiaTriTMDTKMCP`: Giá trị thành tiền hoặc giá trị cột **"Sau thuế"**, không lấy cột "Trước thuế" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`GiaTriTMDTKMCPTang`: Nếu `DieuChinh` bằng `1` thì trích "Giá trị tổng mức đầu tư tăng" ngược lại gán `0` (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`GiaTriTMDTKMCPGiam`: Nếu `DieuChinh` bằng `1` thì trích "Giá trị tổng mức đầu tư giảm" ngược lại gán `0` (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
### 🚫 **Quy tắc loại bỏ khoản mục chi phí**:
Nếu một dòng **thuộc "Danh sách khoản mục chi phí"** dưới đây thì:
❌ **Không xuất dòng không thuộc "Danh sách Khoản mục chi phí"**
✅ **Chỉ xuất các dòng thuộc "Danh sách Khoản mục chi phí"**
**Danh sách Khoản mục chi phí**
| Mã  |Tên khoản mục chi phí                         |
|-----|----------------------------------------------|
|`CP1`|Chi phí bồi thường, hỗ trợ, tái định cư       |
|`CP2`|Chi phí xây dựng                              |
|`CP3`|Chi phí thiết bị                              |
|`CP4`|Chi phí quản lý dự án                         |
|`CP5`|Chi phí tư vấn đầu tư xây dựng                |
|`CP6`|Chi phí khác                                  |
|`CP7`|Chi phí dự phòng                              |

### Yêu cầu xử lý:
🚫 **Không lấy giá trị trong cột "Trước thuế"**
✅ Chỉ lấy giá trị tại đúng cột có tiêu đề "Sau thuế"
- Gộp toàn bộ bảng trong tất cả ảnh thành một danh sách duy nhất, đúng thứ tự
- Giữ nguyên tên gọi và định dạng số tiền như trong ảnh, không tự ý chuẩn hóa
- Không suy diễn hoặc bổ sung thông tin không có trong văn bản
- Tự động loại bỏ dấu chấm phân cách hàng nghìn trong số tiền
- Hãy trích xuất chính xác chuỗi ký tự trước chữ ‘đồng’, bao gồm cả dấu chấm như trong bản gốc.

{{CHUCNANG07}} Chức năng `Quyết định phê duyệt dự toán giai đoạn thực hiện đầu tư`
Bạn phải thực hiện theo các bước sau và trả về **duy nhất một chuỗi JSON hợp lệ** với cấu trúc:
{
  "ThongTinChung": {
    "KyHieu": "...",
    "SoVanBan": "...",
    "NgayKy": "...",
    "SoVanBanCanCu": "...",
    "NgayKyCanCu": "...",
    "NguoiKy": "...",
    "ChucDanhNguoiKy": "...",
    "CoQuanBanHanh": "...",
    "TrichYeu": "...",
    "TenNguonVon": "...",
    "GiaTri": ...,
    "DieuChinh": 0 hoặc 1
  },
  "BangDuLieu": [
    {
      "TenKMCP": "...",
      "GiaTriDuToanKMCP": ...,
      "GiaTriDuToanKMCPTang": ...,
      "GiaTriDuToanKMCPGiam": ...
    }
  ]
}
## 🔹 BƯỚC 1: Trích ThongTinChung từ nội dung dưới đây
### Thông tin chung của văn bản, tên đối tượng (object) "ThongTinChung":
Quy tắc bắt buộc:
- Chỉ lấy các dòng là khoản mục chi phí con, có số tiền ở cột "Sau thuế" hoặc cột giá trị. Nếu không có chi phí con thì lấy chi phí cha
- Không lấy dòng cha (trường hợp có dòng con), dòng nhóm, dòng mô tả, dòng tổng, dòng tiêu đề, dòng trống
- Tuyệt đối không được bỏ sót bất kỳ dòng khoản mục con nào nếu có số tiền
- Không được gộp, không tự suy diễn, không sửa tên khoản mục hay số tiền
- Duyệt từng dòng, kiểm tra kỹ cột số tiền
- Đối với "Bảng tổng hợp chi phí"
+ Chỉ lấy các khoản mục nếu chưa xuất hiện trong bảng chi tiết ở trên và thêm vào cuối bảng chi tiết.
+ Không lấy dòng mô tả, chỉ lấy dòng có giá trị tiền.
- Chỉ trả về danh sách các khoản mục hợp lệ dạng JSON (không thêm text giải thích).
`KyHieu`: "QDPD_DT_THDT"
`SoVanBan`: Trích số hiệu văn bản ghi ở đầu văn bản, sau chữ "Số:"
`NgayKy`: Trích thông tin ngày ký ở đầu văn bản, sau dòng địa danh "..., ngày ...", định dạng (dd/MM/yyyy)
`SoVanBanCanCu`: Trích "số hiệu văn bản" quyết định chủ trương đầu tư hoặc điều chỉnh chủ trương đầu tư, tại dòng "Căn cứ Quyết định ..." có chứa cụm từ "chủ trương đầu tư..."
`NgayKyCanCu`: Trích "ngày...tháng...năm ..." quyết định chủ trương đầu tư hoặc điều chỉnh chủ trương đầu tư, tại dòng "Căn cứ Quyết định ..." có chứa cụm từ "chủ trương đầu tư..." định dạng (dd/MM/yyyy)
`NguoiKy`: Trích tên người ký văn bản ở phần cuối văn bản, ngay dưới dòng "KT. CHỦ TỊCH" hoặc "CHỦ TỊCH" hoặc "KT. GIÁM ĐỐC" hoặc "GIÁM ĐỐC".
`ChucDanhNguoiKy`: Trích phần ghi rõ chức vụ người ký văn bản (VD: "CHỦ TỊCH", "PHÓ CHỦ TỊCH", "KT. CHỦ TỊCH – PHÓ CHỦ TỊCH").
`CoQuanBanHanh`: Trích xuất chính xác tên cơ quan ban hành văn bản theo đúng quy định tại Nghị định 30/2020/NĐ-CP về công tác văn thư. Nếu dòng đầu là tên cơ quan chủ quản và dòng thứ hai là đơn vị trực thuộc thì chỉ lấy dòng thứ hai làm cơ quan ban hành.
`TrichYeu`: Trích nguyên văn phần tiêu đề nằm ngay sau chữ "QUYẾT ĐỊNH", thường bắt đầu bằng "Về việc..." hoặc "V/v..." hoặc "Về việc phê duyệt Báo cáo..."
`TenNguonVon`: Trích tên nguồn vốn sau cụm từ "nguồn vốn: ...", nếu không có để ""
`GiaTri`: Trích thông tin số tiền ngay sau cụm từ "giá trị dự toán", thường tại dòng "Bằng chữ: ..." (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`DieuChinh`: Gán `1` nếu "trích yếu văn bản" có chứa nội dung "điều chỉnh...", ngược lại gán `0`
## 🔷 BƯỚC 2: Trích `BangDuLieu`
Bạn PHẢI xử lý theo đúng trình tự sau:
### ▶️ 1. Phần `START_BANG_CHI_TIET`:
Đây là **bảng chi tiết**, gồm nhiều dòng chi phí con. Dạng bảng gồm các cột:
**STT | Tên khoản mục chi phí | Cách tính | Trước thuế | Sau thuế | Ký hiệu**
**Yêu cầu xử lý:**
- Chỉ lấy các dòng có **giá trị ở cột "Sau thuế"**.
- **KHÔNG lấy dòng mô tả hoặc nhóm**, cụ thể như: "Công trình dân dụng", "Công trình công nghiệp", "Công trình giao thông", "Công trình nông nghiệp và phát triển nông thôn", "Công trình hạ tầng kỹ thuật".
- Nếu khoản mục là dòng con thuộc nhóm lớn (vd: “Chi phí lập báo cáo…” nằm trong “Chi phí tư vấn đầu tư xây dựng”) → vẫn PHẢI lấy dòng con, **KHÔNG lấy dòng cha**.
**Trường dữ liệu cần trích từ mỗi dòng:**
- `TenKMCP`: tên khoản mục chi phí (giữ nguyên)
- `GiaTriDuToanKMCP`: lấy cột “Sau thuế”
- `GiaTriDuToanKMCPTang`: nếu "DieuChinh" = 1 → lấy “Giá trị tăng”, nếu không thì = 0
- `GiaTriDuToanKMCPGiam`: nếu "DieuChinh" = 1 → lấy “Giá trị giảm”, nếu không thì = 0

### ▶️ 2. Phần `START_BANG_TONG_HOP`:
Đây là **bảng tổng hợp chi phí**.

**Yêu cầu xử lý:**
- Chỉ lấy các khoản mục nếu **chưa xuất hiện trong bảng chi tiết** ở trên.
- Không lấy dòng mô tả, chỉ lấy dòng có giá trị tiền.

### ▶️ 3. ĐẶC BIỆT: Trường hợp ngắt dòng do OCR không có Phần `START_BANG_TONG_HOP`:
Nếu khoản mục chi phí nằm ở một dòng, còn số tiền nằm ở dòng kế tiếp, ví dụ:
- Chi phí giải phóng mặt bằng  
:  
9.999 đồng

→ Vẫn phải gộp lại và trích như sau:
{
  "TenKMCP": "Chi phí giải phóng mặt bằng",
  "GiaTriDuToanKMCP": 9999,
  "GiaTriDuToanKMCPTang": 0,
  "GiaTriDuToanKMCPGiam": 0
}

## ⚠️ CHỈ TRẢ VỀ MỘT ĐỐI TƯỢNG JSON DUY NHẤT
- Không trả lời thêm giải thích
- Không ghi chữ “Dưới đây là kết quả” hay mô tả nào khác

## 🔁 Ví dụ mẫu (để API học đúng format):

```json
{
  "TenKMCP": "Chi phí lập báo cáo kinh tế kỹ thuật",
  "GiaTriDuToanKMCP": 888,
  "GiaTriDuToanKMCPTang": 0,
  "GiaTriDuToanKMCPGiam": 0
}


{{CHUCNANG08}} Chức năng "Quyết định phê duyệt kế hoạch lựa chọn nhà thầu (viết tắt: "KHLCNT") giai đoạn chuẩn bị đầu tư"
### Văn bản để nhận dạng thông tin là: "Quyết định phê duyệt KHLCNT giai đoạn thực hiện đầu tư, quyết định điều chỉnh KHLCNT giai đoạn thực hiện đầu tư"
### Thông tin chung của văn bản, tên đối tượng (object) "ThongTinChung":
`KyHieu`: "QDPD_KHLCNT_THDT"
`SoVanBan`: Trích số hiệu văn bản ghi ở đầu văn bản, sau chữ "Số:"
`NgayKy`: Trích thông tin ngày ký ở đầu văn bản, sau dòng địa danh "..., ngày ...", định dạng dd/MM/yyyy
`SoVanBanCanCu`: Trích "số hiệu văn bản" kế hoạch đầu tư công, tại dòng "Căn cứ Quyết định số..." có chứa cụm từ "kế hoạch đầu tư công..."
`NgayKyCanCu`: Trích "ngày...tháng...năm ..." kế hoạch đầu tư công, tại dòng "Căn cứ Quyết định số..." có chứa cụm từ "kế hoạch đầu tư công..." định dạng (dd/MM/yyyy)
`NguoiKy`: Trích tên người ký văn bản ở phần cuối văn bản, ngay dưới dòng "KT. CHỦ TỊCH" hoặc "CHỦ TỊCH".
`ChucDanhNguoiKy`: Trích phần ghi rõ chức vụ người ký văn bản.
`CoQuanBanHanh`: Trích xuất chính xác tên cơ quan ban hành văn bản theo đúng quy định tại Nghị định 30/2020/NĐ-CP về công tác văn thư. Nếu dòng đầu là tên cơ quan chủ quản và dòng thứ hai là đơn vị trực thuộc thì chỉ lấy dòng thứ hai làm cơ quan ban hành.
`TrichYeu`: Trích nguyên văn phần tiêu đề nằm ngay sau chữ "QUYẾT ĐỊNH", thường bắt đầu bằng "Về việc..." hoặc "V/v..." hoặc "Về việc phê duyệt Báo cáo...".
`GiaTri`: Trích cột giá gói thầu, thường tại dòng "Tổng cộng..." (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`DieuChinh`: Gán `1` nếu trích yếu văn bản có chứa nội dung "điều chỉnh...", ngược lại gán `0`.
**Bảng Phụ lục gói thầu, mỗi dòng là một bản ghi với các cột sau, tên đối tượng (object): `BangDuLieu`:
`TenDauThau`: Trích tên đầy đủ của gói thầu
`TenKMCP`: Nếu `TenDauThau` có chứa cụm từ "bảo hiểm" thì `TenKMCP` = "Chi phí bảo hiểm", nếu `TenDauThau` có chứa cụm từ "thi công xây dựng" hoặc "thi công xây lắp" thì `TenKMCP` = "Chi phí xây dựng" ngược lại gán `TenDauThau` vào cột `TenKMCP`
`GiaTriGoiThau`: Trích cột giá gói thầu (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`TenNguonVon`: Trích cột nguồn vốn
`HinhThucLCNT`: Trích cột hình thức lựa chọn nhà thầu
`PhuongThucLCNT`: Trích cột phương thức lựa chọn nhà thầu
`ThoiGianTCLCNT`: Trích cột thời gian bắt đầu tổ chức lựa chọn nhà thầu
`LoaiHopDong`: Trích cột loại hợp đồng
`ThoiGianTHHopDong`: Trích cột thời gian thực hiện hợp đồng
### Yêu cầu xử lý:
- Không suy diễn hoặc bổ sung thông tin không có trong văn bản
- Tự động loại bỏ dấu chấm phân cách hàng nghìn trong số tiền
- Tách từng dòng con trong phần "Trong đó" ra như một gói thầu độc lập (nếu có)



{{CHUCNANG09}} Chức năng `Quyết định phê duyệt kết quả lựa chọn nhà thầu (viết tắt: "KQLCNT") giai đoạn thực hiện đầu tư`
### Văn bản để nhận dạng thông tin là`: "Quyết định phê duyệt KQLCNT giai đoạn thực hiện đầu tư, quyết định điều chỉnh KQLCNT giai đoạn thực hiện đầu tư"
### Thông tin chung của văn bản, tên đối tượng (object) "ThongTinChung":
`KyHieu`: "QDPD_KQLCNT_THDT"
`SoVanBan`: Trích số hiệu văn bản ghi ở đầu văn bản, sau chữ "Số:"
`SoVanBanCanCuQD`: Trích `số hiệu quyết định phê duyệt kế hoạch lựa chọn nhà thầu`, tại dòng "Căn cứ Quyết định ... phê duyệt kế hoạch lựa chọn nhà thầu"
`SoVanBanCanCuDC`: Trích `số hiệu quyết định phê duyệt kế hoạch lựa chọn nhà thầu`, tại dòng "Căn cứ Quyết định ... phê duyệt điều chỉnh kế hoạch lựa chọn nhà thầu"
`SoVanBanCanCu`: Kết hợp tất cả các số hiệu từ `SoVanBanCanCuQD` và `SoVanBanCanCuDC` thành một chuỗi, các số hiệu cách nhau bằng dấu ;. Nếu không có số hiệu nào thì để trống.
`NgayKyCanCu`: Trích "ngày...tháng...năm ..." Quyết định phê duyệt kế hoạch lựa chọn nhà thầu, tại dòng "Căn cứ Quyết định ... phê duyệt kế hoạch lựa chọn nhà thầu" định dạng (dd/MM/yyyy)
`NgayKy`: Trích thông tin ngày ký ở đầu văn bản, sau dòng địa danh "..., ngày ...", định dạng (dd/MM/yyyy)
`NguoiKy`: Trích tên người ký văn bản ở phần cuối văn bản.
`ChucDanhNguoiKy`: Trích phần ghi rõ chức vụ người ký văn bản.
`CoQuanBanHanh`: Trích xuất chính xác tên cơ quan ban hành văn bản theo đúng quy định tại Nghị định 30/2020/NĐ-CP về công tác văn thư. Nếu dòng đầu là tên cơ quan chủ quản và dòng thứ hai là đơn vị trực thuộc thì chỉ lấy dòng thứ hai làm cơ quan ban hành.
`TrichYeu`: Trích nguyên văn tiêu đề ngay dưới dòng "QUYẾT ĐỊNH" (thường bắt đầu bằng "Về việc...")
`TenNhaThau`: Trích từ dòng "đơn vị chỉ định thầu" hoặc "đơn vị trúng thầu"
`GiaTri`: Trích thông tin số tiền ngay sau cụm từ "giá chỉ định thầu" hoặc "giá trị trúng thầu", thường tại dòng "Bằng chữ: ..." (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`DieuChinh`: Gán giá trị `1` nếu nội dung phần tiêu đề văn bản có cụm từ chứa "điều chỉnh". Nếu không có, gán `0`.
### Bảng dữ liệu gói thầu, mỗi dòng là một bản ghi với các cột sau, tên đối tượng (object): "BangDuLieu":
`TenDauThau`: Trích `tên gói thầu`, sau cụm từ "Nội dung gói thầu:..." hoặc "Tên gói thầu:..."
`TenKMCP`: Nếu `TenDauThau` có chứa cụm từ "bảo hiểm" thì `TenKMCP` = "Chi phí bảo hiểm", nếu `TenDauThau` có chứa cụm từ "thi công xây dựng" hoặc "thi công xây lắp" thì `TenKMCP` = "Chi phí xây dựng" ngược lại gán `TenDauThau` vào cột `TenKMCP`
`TenNhaThau`: Trích từ dòng "đơn vị chỉ định thầu" hoặc "đơn vị trúng thầu"
`ThoiGianTHHopDong`: Trích từ dòng "Thời gian thực hiện hợp đồng: ... ngày"
`LoaiHopDong`: Trích từ dòng "Loại hợp đồng: ..."
`GiaTrungThau`: Trích thông tin số tiền ngay sau cụm từ "giá chỉ định thầu" hoặc "giá trị trúng thầu", thường tại dòng "Bằng chữ: ..."
### Yêu cầu xử lý:
- Không suy diễn hoặc bổ sung thông tin không có trong văn bản
- Tự động loại bỏ dấu chấm phân cách hàng nghìn trong số tiền
- Tách từng dòng con trong phần "Trong đó" ra như một gói thầu độc lập (nếu có)


{{CHUCNANG10}} Chức năng `Hợp đồng`
### Văn bản để nhận dạng thông tin là: "Hợp đồng"
### Thông tin chung của văn bản, tên đối tượng (object) "ThongTinChung":
`KyHieu`: "HOP_DONG"
`SoVanBan`: Trích số hợp đồng
`SoVanBanCanCu`: Trích `số hiệu quyết định phê duyệt kết quả lựa chọn nhà thầu`, tại dòng "Căn cứ Quyết định ... phê duyệt kết quả lựa chọn nhà thầu"
`NgayKyCanCu`: Trích "ngày...tháng...năm ..." quyết định phê duyệt kết quả lựa chọn nhà thầu, tại dòng "Căn cứ Quyết định ... phê duyệt kết quả lựa chọn nhà thầu"
`NgayKy`: Trích thông tin ngày ký, sau dòng "Hôm nay ..., ngày ..." định dạng (dd/MM/yyyy)
`NgayHieuLuc`: Trích ngày "hiệu lực" hoặc "ngày có hiệu lực" hợp đồng, ngay dưới dòng "Điều khoản chung" định dạng (dd/MM/yyyy)
`NgayKetThuc`: Trích ngày "hết hạn" hoặc ngày "kết thúc hợp đồng", định dạng (dd/MM/yyyy)
`CoQuanBanHanh`: Trích tên đơn vị chủ đầu tư, tại dòng "Tên giao dịch (Chủ đầu tư): ..." hoặc "Bên A: ..." hoặc "Tên đơn vị giao thầu:..."
`NguoiKy`: Trích tên người đại diện "Chủ đầu tư" hoặc "Bên A: ..." hoặc "Đơn vị giao thầu:..."
`ChucDanhNguoiKy`: Trích tên chức vụ người đại diện "Chủ đầu tư" hoặc "Bên A: ..." hoặc "Đơn vị giao thầu:..."
`TenNhaThau`: Trích từ dòng "tên nhà thầu", tại dòng "Tên giao dịch (Nhà thầu): ..." hoặc "Nhà thầu: ..." hoặc "Bên B: ..." hoặc "Tên đơn vị nhận thầu:..."
`NguoiKy_NhaThau`: Trích tên người đại diện "Nhà thầu" hoặc "Bên B: ..." hoặc "Đơn vị nhận thầu:..."
`ChucDanhNguoiKy_NhaThau`: Trích tên chức vụ người đại diện "Nhà thầu" hoặc "Bên B: ..." hoặc "Đơn vị nhận thầu:..."
`TrichYeu`: Lấy trích yếu hợp đồng, thường bắt đầu bằng "Về việc..." hoặc "V/v..."
`GiaTri`: Bạn PHẢI xử lý theo đúng theo yêu cầu sau:
- Nếu sau cụm từ "Hợp đồng ... " tại trang 1 có chứa cụm từ "bảo hiểm" thì `GiaTriHopDong` trích số tiền tại dòng có cụm từ "phí bảo hiểm làm tròn:"
- Nếu có bảng chi tiết thì trích cột "Thành tiền" hoặc cột "Số tiền" của bảng chi tiết gán vào `GiaTriHopDong`, ngược lại thì lấy bằng "0".
### Bảng khối lượng công việc của hợp đồng, mỗi dòng là một bản ghi với các cột sau, tên đối tượng (object): "BangDuLieu":
`TenKMCP`: Bạn PHẢI xử lý theo đúng theo yêu cầu sau:
- Nếu sau cụm từ "Hợp đồng ... " tại trang 1 có chứa cụm từ "bảo hiểm" thì `TenKMCP` = "Chi phí bảo hiểm", nếu trang 1 có chứa cụm từ "thi công xây dựng" hoặc "thi công xây lắp" thì `TenKMCP` = "Chi phí xây dựng".
- Nếu sau cụm từ "Gói thầu ... " tại trang 1 có chứa cụm từ "bảo hiểm" thì `TenKMCP` = "Chi phí bảo hiểm", nếu trang 1 có chứa cụm từ "thi công xây dựng" hoặc "thi công xây lắp" thì `TenKMCP` = "Chi phí xây dựng".
- Nếu sau cụm từ "Căn cứ Quyết định số ... kết quả lựa chọn nhà thầu ..." có chứa cụm từ "xây dựng" hoặc "xây lắp" thì `TenKMCP` = "Chi phí xây dựng".
- Nếu có bảng chi tiết thì trích cột "Tên công việc" của bảng chi tiết gán vào `TenKMCP`.
- Nếu "Tên công việc" có chứa cụm từ sau: "Tổng số", "Thuế GTGT", "Thuế VAT" thì không lấy dòng thông tin này
- Nếu "Tên công việc" có chứa cụm từ "làm tròn" hoặc "(làm tròn)", hãy loại bỏ phần "làm tròn", chỉ giữ lại phần gốc. Ví dụ: "Tên chi phí (làm tròn)" ➜ "Tên chi phí". Dòng "Tên công việc" vẫn phải được đưa vào danh sách, ngay cả khi nội dung có ghi "(làm tròn)" hoặc các biến thể tương tự.
`GiaTriHopDong`:  Bạn PHẢI xử lý theo đúng theo yêu cầu sau:
- Nếu sau cụm từ "Hợp đồng ... " tại trang 1 có chứa cụm từ "bảo hiểm" thì `GiaTriHopDong` trích số tiền tại dòng có cụm từ "phí bảo hiểm làm tròn:"
- Nếu có bảng chi tiết thì trích cột "Thành tiền" hoặc cột "Số tiền" của bảng chi tiết gán vào `GiaTriHopDong`, ngược lại thì lấy bằng "0".
### Yêu cầu xử lý:
- Không suy diễn hoặc bổ sung thông tin không có trong văn bản
- Tự động loại bỏ dấu chấm phân cách hàng nghìn trong số tiền



{{CHUCNANG11}} Chức năng `Phụ lục hợp đồng`
### Thông tin chung của văn bản, tên đối tượng (object) "ThongTinChung":
`KyHieu`: "PL_HOP_DONG"
`SoVanBan`: Trích số phụ lục hợp đồng, thường bắt đầu bằng "Phụ lục hợp đồng số:..." hoặc "Số phụ lục:..." hoặc "Phụ lục số:...", chỉ lấy sau dấu ":"
`SoPLHopDong`: Giống cột `SoVanBan`
`NgayKy`: Lấy ngày ký phụ lục hợp đồng, sau dòng "Hôm nay ..., ngày ..." định dạng (dd/MM/yyyy)
`SoVanBanCanCu`: Trích `số hợp đồng`, tại dòng "Căn cứ Hợp đồng..."
`NgayKyCanCu`: Trích "ngày...tháng...năm ..." hợp đồng, tại dòng "Căn cứ Hợp đồng..." định dạng (dd/MM/yyyy)
`CoQuanBanHanh`: Trích tên đơn vị chủ đầu tư, tại dòng "Tên giao dịch (Chủ đầu tư): ..." hoặc "Bên A: ..." hoặc "Tên đơn vị giao thầu:..."
`NguoiKy`: Trích tên người đại diện "Chủ đầu tư" hoặc "Bên A: ..." hoặc "Đơn vị giao thầu:..."
`ChucDanhNguoiKy`: Trích tên chức vụ người đại diện "Chủ đầu tư" hoặc "Bên A: ..." hoặc "Đơn vị giao thầu:..."
`TenNhaThau`: Trích từ dòng "tên nhà thầu", tại dòng "Tên giao dịch (Nhà thầu): ..." hoặc "Nhà thầu: ..." hoặc "Bên B: ..." hoặc "Tên đơn vị nhận thầu:..."
`NguoiKy_NhaThau`: Trích tên người đại diện "Nhà thầu" hoặc "Bên B: ..." hoặc "Đơn vị nhận thầu:..."
`ChucDanhNguoiKy_NhaThau`: Trích tên chức vụ người đại diện "Nhà thầu" hoặc "Bên B: ..." hoặc "Đơn vị nhận thầu:..."
`TrichYeu`: Lấy trích yếu phụ lục hợp đồng, thường bắt đầu bằng "Về việc..." hoặc "V/v..."
`GiaTri`: Bạn PHẢI xử lý theo đúng theo yêu cầu sau:
- Nếu sau cụm từ "Gói thầu... " tại trang 1 có chứa cụm từ "bảo hiểm" thì `GiaTriHopDong` trích số tiền tại dòng có cụm từ "phí bảo hiểm làm tròn:"
- Nếu có bảng chi tiết thì trích cột "Thành tiền" hoặc cột "Số tiền" của bảng chi tiết gán vào `GiaTriHopDong`, ngược lại thì lấy bằng "0".
### Bảng khối lượng công việc của phụ lục hợp đồng, mỗi dòng là một bản ghi với các cột sau, tên đối tượng (object): "BangDuLieu":
`TenKMCP`: Bạn PHẢI xử lý theo đúng theo yêu cầu sau:
- Nếu sau cum từ "Gói thầu... " tại trang 1 có chứa cụm từ "bảo hiểm" thì `TenKMCP` = "Chi phí bảo hiểm", nếu trang 1 có chứa cụm từ "thi công xây dựng" hoặc "thi công xây lắp" thì `TenKMCP` = "Chi phí xây dựng".
- Nếu sau cum từ "Căn cứ Hợp đồng số ..." có chứa cụm từ "bảo hiểm" thì `TenKMCP` = "Chi phí bảo hiểm", nếu trang 1 có chứa cụm từ "thi công xây dựng" hoặc "thi công xây lắp" thì `TenKMCP` = "Chi phí xây dựng".
- Nếu có bảng chi tiết thì trích cột "Tên công việc" của bảng chi tiết gán vào `TenKMCP`.
- Nếu "Tên công việc" có chứa cụm từ sau: "Tổng số", "Thuế GTGT", "Thuế VAT" thì không lấy dòng thông tin này.
- Nếu "Tên công việc" có chứa cụm từ "làm tròn" hoặc "(làm tròn)", hãy loại bỏ phần "làm tròn", chỉ giữ lại phần gốc. Ví dụ: "Tên chi phí (làm tròn)" ➜ "Tên chi phí". Dòng "Tên công việc" vẫn phải được đưa vào danh sách, ngay cả khi nội dung có ghi "(làm tròn)" hoặc các biến thể tương tự.
`GiaTriHopDong`:  Bạn PHẢI xử lý theo đúng theo yêu cầu sau:
- Nếu sau cụm từ "Gói thầu... " tại trang 1 có chứa cụm từ "bảo hiểm" thì `GiaTriHopDong` trích số tiền tại dòng có cụm từ "phí bảo hiểm làm tròn:"
- Nếu có bảng chi tiết thì trích cột "Thành tiền" hoặc cột "Số tiền" của bảng chi tiết gán vào `GiaTriHopDong`, ngược lại thì lấy bằng "0".
### Yêu cầu xử lý:
- Không suy diễn hoặc bổ sung thông tin không có trong văn bản
- Tự động loại bỏ dấu chấm phân cách hàng nghìn trong số tiền



{{CHUCNANG12}} Chức năng `Khối lượng công việc hoàn thành (viết tắt KLCVHT) thông qua hợp đồng`
### Văn bản để nhận dạng thông tin là: "Bảng xác định giá trị khối lượng công việc hoàn thành, mẫu số 03.a/TT"
### Thông tin chung của văn bản, tên đối tượng (object) "ThongTinChung":
`KyHieu`: "KLCVHT_THD"
`SoVanBan`: Trích số biên bản nghiệm thu sau dòng "Biên bản nghiệm thu số..." hoặc trích sau cụm từ "Giấy chứng nhận bảo hiểm...:"
`NgayKy`: Ngày ký chứng từ trích sau dòng "Biên bản nghiệm thu số ..., ngày ... tháng ... năm ..." hoặc trích sau cụm từ "Giấy chứng nhận bảo hiểm số ..., ngày ... tháng ... năm ...") định dạng (dd/MM/yyyy)
`SoVanBanCanCu`: Trích số hợp đồng chính sau cụm từ "Hợp đồng số..." hoặc trích sau cụm từ "Giấy chứng nhận bảo hiểm...:"
`NgayKyCanCu`: Trích "ngày...tháng...năm ..." hợp đồng, trích sau cụm từ "Hợp đồng số..." định dạng (dd/MM/yyyy)
`SoHopDong`: Giống cột `SoVanBanCanCu`
`SoPLHopDong`: Trích số phụ lục hợp đồng sau cụm từ "Phụ lục số..." hoặc "Phụ lục bổ sung số..."
`LanThanhToan`: Trích lần thanh toán sau cụm từ "Thanh toán lần thứ...". Ví dụ: "01", "02", "03". 
`TenNhaThau`: Trích tên nhà thầu sau dòng "Nhà thầu:" hoặc "Đơn vị thi công..."
`NguoiKy`: Trích tên người ký văn bản:
            - Tìm tại phần cuối trang, thường ngay dưới dòng "ĐẠI DIỆN CHỦ ĐẦU TƯ" hoặc "ĐẠI DIỆN NHÀ THẦU"
            - Là dòng chữ `in hoa hoặc in thường có họ tên đầy đủ`, nằm trên chữ ký tay
            - Nếu có đóng dấu, tên người ký nằm bên dưới
`ChucDanhNguoiKy`: Trích dòng nằm "ngay phía trên tên người ký", ví dụ: "Giám đốc", "Phó giám đốc", "Kế toán trưởng", "Chủ tịch", "KT. Chủ tịch – Phó Chủ tịch".
`CoQuanBanHanh`: Trích tên chủ đầu tư sau dòng có cụm từ "Chủ đầu tư:" hoặc "Đại diện chủ đầu tư"
`TrichYeu`: Gán "Bảng xác định khối lượng công việc hoàn thành theo Hợp đồng số: ", kết hợp tất cả các số hiệu từ `SoVanBanCanCu` và `NgayKyCanCu` thành một chuỗi.
`GiaTri`: Trích `giá trị đề nghị giải ngân kỳ này` tại dòng "6. giá trị đề nghị giải ngân kỳ này" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`GiaTriHopDong`: Trích `giá trị hợp đồng` tại dòng "`1. Giá trị hợp đồng (giá trị dự toán được duyệt...)" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`TamUngChuaThuaHoi`: Trích `giá trị tạm ứng còn lại chưa thu hồi đến cuối kỳ trước` tại dòng "2. Giá trị tạm ứng còn lại chưa thu hồi đến cuối kỳ trước" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`ThanhToanDenCuoiKyTruoc`: Trích `số tiền đã thanh toán khối lượng hoàn thành đến cuối kỳ trước` tại dòng "3. Số tiền đã thanh toán khối lượng hoàn thành đến cuối kỳ trước" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`LuyKeDenCuoiKy`: Trích `luỹ kế giá trị khối lượng thực hiện đến cuối kỳ này` tại dòng "4. Luỹ kế giá trị khối lượng thực hiện đến cuối kỳ này" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`ThanhToanThuHoiTamUng`: Trích `thanh toán để thu hồi tạm ứng` tại dòng "5. Thanh toán để thu hồi tạm ứng" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`GiaiNganKyNay`: Lấy giá trị cột `GiaTri`
`TamUngGiaiNganKyNayKyTruoc`: Trích `số tiền tạm ứng` ngay dưới dòng "số tiền bằng chữ..." (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`ThanhToanKLHTKyTruoc`: Trích `số tiền thanh toán khối lượng hoàn thành` ngay dưới dòng "số tiền bằng chữ..." (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`LuyKeGiaiNgan`: Trích `số tiền` ngay dưới dòng "7. Luỹ kế giá trị giải ngân:" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`TamUngThanhToan`: Trích `số tiền tạm ứng` ngay dưới dòng "7. Luỹ kế giá trị giải ngân:" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`ThanhToanKLHT`: Trích `số tiền thanh toán khối lượng hoàn thành` ngay dưới dòng "7. Luỹ kế giá trị giải ngân:" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`LoaiGiaiNgan`: Nếu `SoVanBanCanCu` có giá trị thì gán "1" ngược lại gán "2"
### Bảng khối lượng công việc hoàn thành, mỗi dòng là một bản ghi với các cột sau, tên đối tượng (object): "BangDuLieu":
`TenKMCP`: Bạn PHẢI xử lý theo đúng theo yêu cầu sau:
- Nếu sau cum từ "Gói thầu... " tại trạng 1 có chứa cụm từ "thi công xây dựng" hoặc "thi công xây lắp" thì `TenKMCP` = "Chi phí xây dựng", nếu trang 1 có chứa cụm từ "bảo hiểm" thì `TenKMCP` = "Chi phí bảo hiểm".
- Nếu có bảng chi tiết thì trích cột "Tên công việc" của bảng chi tiết gán vào `TenKMCP`.
- Nếu "Tên công việc" có chứa cụm từ sau: "Tổng số", "Thuế GTGT", "Thuế VAT" thì không lấy dòng thông tin này.
`GiaTriNTVAT`: Nếu giá trị `thực hiện kỳ này` có dòng "làm tròn" thì lấy giá trị `làm tròn` ngược lại trích giá trị `thực hiện kỳ này` trong bảng dữ liệu (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn). 
`GiaTriNTTruVAT`: Nếu giá trị `thực hiện kỳ này` có dòng "Giảm thuế" hoặc "thuế VAT" thì lấy giá trị "Giảm thuế" hoặc "thuế VAT" ngược lại gán "0"
`GiaTriNghiemThu`: Tính bằng công thức `GiaTriNTVAT` trừ `GiaTriNTTruVAT`
### Yêu cầu xử lý:
- Không suy diễn hoặc bổ sung thông tin không có trong văn bản
- Tự động loại bỏ dấu chấm phân cách hàng nghìn trong số tiền


{{CHUCNANG13}} Chức năng `Khối lượng công việc hoàn thành (viết tắt KLCVHT) không thông qua hợp đồng`
### Văn bản để nhận dạng thông tin là: "Bảng xác định giá trị khối lượng công việc hoàn thành, mẫu số 03.b/TT"
### Thông tin chung của văn bản, tên đối tượng (object) "ThongTinChung":
`KyHieu`: "KLCVHT_NHD"
`SoVanBan`: Số biên bản nghiệm thu (trích sau dòng "Biên bản nghiệm thu số..." hoặc dòng tương đương)
`NgayKy`: Ngày ký chứng từ trích sau dòng "Biên bản nghiệm thu số ..., ngày ... tháng ... năm ..." định dạng (dd/MM/yyyy)
`SoVanBanCanCu`: Số hợp đồng chính (trích sau cụm từ "Hợp đồng số...")
`NgayKyCanCu`: Trích "ngày...tháng...năm ..." hợp đồng, trích sau cụm từ "Hợp đồng số..." định dạng (dd/MM/yyyy)
`SoHopDong`: Giống cột `SoVanBanCanCu`
`SoPLHopDong`: Trích số phụ lục hợp đồng sau cụm từ "Phụ lục số..." hoặc "Phụ lục bổ sung số..."
`LanThanhToan`: Lần thanh toán (trích sau cụm từ "Thanh toán lần thứ...")
`TenNhaThau`: Tên nhà thầu (trích sau dòng "Nhà thầu:" hoặc "Đơn vị thi công...")
`NguoiKy`: Trích tên người ký văn bản:
- Tìm tại phần cuối trang, thường ngay dưới dòng "ĐẠI DIỆN CHỦ ĐẦU TƯ" hoặc "ĐẠI DIỆN NHÀ THẦU".
- Là dòng chữ `in hoa hoặc in thường có họ tên đầy đủ`, nằm trên chữ ký tay.
- Nếu có đóng dấu, tên người ký nằm bên dưới.
`ChucDanhNguoiKy`: Trích dòng nằm "ngay phía trên tên người ký", ví dụ: "Giám đốc", "Phó giám đốc", "Kế toán trưởng", "Chủ tịch", "KT. Chủ tịch – Phó Chủ tịch".
`CoQuanBanHanh`: Tên chủ đầu tư (trích sau dòng có cụm từ "Chủ đầu tư:" hoặc "Đại diện chủ đầu tư")
`TrichYeu`: Trích cụm từ "Khối lượng công việc hoàn thành theo Hợp đồng số: ..." Trích sau cụm từ "Thanh toán lần thứ:"
`GiaTri`: Trích `giá trị đề nghị giải ngân kỳ này` tại dòng "6. giá trị đề nghị giải ngân kỳ này"
`GiaTriHopDong`: Trích `giá trị hợp đồng` tại dòng "`1. Giá trị hợp đồng (giá trị dự toán được duyệt...)" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`TamUngChuaThuaHoi`: Trích `giá trị tạm ứng còn lại chưa thu hồi đến cuối kỳ trước` tại dòng "2. Giá trị tạm ứng còn lại chưa thu hồi đến cuối kỳ trước"
`ThanhToanDenCuoiKyTruoc`: Trích `số tiền đã thanh toán khối lượng hoàn thành đến cuối kỳ trước` tại dòng "3. Số tiền đã thanh toán khối lượng hoàn thành đến cuối kỳ trước"
`LuyKeDenCuoiKy`: Trích `luỹ kế giá trị khối lượng thực hiện đến cuối kỳ này` tại dòng "4. Luỹ kế giá trị khối lượng thực hiện đến cuối kỳ này"
`ThanhToanThuHoiTamUng`: Trích `thanh toán để thu hồi tạm ứng` tại dòng "5. Thanh toán để thu hồi tạm ứng"
`GiaiNganKyNay`: Lấy giá trị cột `GiaTri`
`TamUngGiaiNganKyNayKyTruoc`: Trích `số tiền tạm ứng` ngay dưới dòng "số tiền bằng chữ..."
`ThanhToanKLHTKyTruoc`: Trích `số tiền thanh toán khối lượng hoàn thành` ngay dưới dòng "số tiền bằng chữ..."
`LuyKeGiaiNgan`: Trích `số tiền` ngay dưới dòng "7. Luỹ kế giá trị giải ngân:"
`TamUngThanhToan`: Trích `số tiền tạm ứng` ngay dưới dòng "7. Luỹ kế giá trị giải ngân:"
`ThanhToanKLHT`: Trích `số tiền thanh toán khối lượng hoàn thành` ngay dưới dòng "7. Luỹ kế giá trị giải ngân:"
`LoaiGiaiNgan`: Nếu `SoVanBanCanCu` có giá trị thì gán "1" ngược lại gán "2"
### Bảng khối lượng công việc hoàn thành, mỗi dòng là một bản ghi với các cột sau, tên đối tượng (object): "BangDuLieu":
`TenKMCP`: Tên công việc được ghi trong cột "Tên công việc"
`GiaTriNghiemThu`: Đơn vị tính (ví dụ: m2, đồng...) (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`KLTheoHopDong`: Khối lượng theo hợp đồng hoặc dự toán (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`KLLuyKeDenHetKyTruoc`: Lũy kế đến hết kỳ trước (cột 5) (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`KLThucHienKyNay`: Khối lượng thực hiện kỳ này (cột 6) (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`KLLuyKeDenHetKyNay`: Lũy kế đến hết kỳ này (cột 7) (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`DonGiaThanhToan`: Đơn giá thanh toán theo hợp đồng hoặc dự toán (cột 8) (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`TTTheoHopDong`: Thành tiền theo hợp đồng hoặc dự toán (cột 9) (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`TTLuyKeTruoc`: Thành tiền lũy kế đến hết kỳ trước (cột 10) (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`TTKyNay`: Thành tiền thực hiện kỳ này (cột 11) (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`TTLuyKeDenHetKyNay`: Thành tiền lũy kế đến hết kỳ này (cột 12) (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`GhiChu`: Thông tin ghi chú (cột 13), nếu có
### Yêu cầu xử lý:
- Không suy diễn hoặc bổ sung thông tin không có trong văn bản
- Tự động loại bỏ dấu chấm phân cách hàng nghìn trong số tiền



{{CHUCNANG14}} Chức năng `Giải ngân vốn đầu tư`
### Chứng từ để nhận dạng thông tin là `GIẤY ĐỀ NGHỊ THANH TOÁN VỐN`, mẫu số 04.a/TT
### Thông tin chung của văn bản, tên đối tượng (object) "ThongTinChung":
`KyHieu`: "GIAI_NGAN_DNTT"
`SoVanBan`: Trích số hiệu ở đầu văn bản sau chữ "Số:"
`NgayKy`: Trích ngày ở góc trên bên phải văn bản (dưới dòng "Độc lập - Tự do - Hạnh phúc"), định dạng (dd/MM/yyyy)
`SoHopDong`: Trích số hợp đồng sau cụm từ "Căn cứ hợp đồng số:..."
`SoVanBanCanCu`: Trích số hợp đồng sau cụm từ "Căn cứ hợp đồng số:..." hoặc trích sau cụm từ "Căn cứ quyết định phê duyệt dự toán..."
`NgayKyCanCu`: Trích "ngày...tháng...năm ..." cùng dòng `SoVanBanCanCu` định dạng (dd/MM/yyyy)
`SoPLHopDong`: Trích số phụ lục hợp đồng sau cụm từ "Phụ lục số..." hoặc "Phụ lục bổ sung số..."
`TenNguonVon`: Trích sau dòng "Thuộc nguồn vốn:"
`NienDo`: Trích sau dòng "Năm:", phía trên dòng tiêu đề của bảng số liệu
`LoaiKHVonID`: Trích sau dòng "Thuộc kế hoạch:", nếu `NienDo` bằng `LoaiKHVonID` thì gán `2`, nếu `NienDo` lơn hơn `LoaiKHVonID`  thì gán `1` ngược lại gán `3`
`GiaTri`: Lấy giá trị tổng số tiền đề nghị tạm ứng, thanh toán bằng số, tại dòng "Tổng số tiền đề nghị tạm ứng, thanh toán bằng số:"
`NguoiKy`: Trích tên người ký tại mục "LÃNH ĐẠO ĐƠN VỊ" hoặc "BAN QUẢN LÝ DỰ ÁN", dưới chữ ký
`ChucDanhNguoiKy`: Trích dòng nằm ngay phía trên tên người ký
`CoQuanBanHanh`: Trích sau dòng có cụm từ "Chủ đầu tư:" hoặc "Chủ đầu tư/Ban QLDA:"
`TrichYeu`: Lấy nội dung thanh toán của bảng dữ liệu (nếu nhiều nội dung thì nối chuỗi lại cách nhau dấu chấm phẩy `; `)
`LoaiGiaiNgan`: Nếu `SoHopDong` hoặc `SoPLHopDong` có giá trị thì gán "1" ngược lại gán "2"
### Bảng khối lượng công việc hoàn thành, mỗi dòng là một bản ghi với các cột sau, tên đối tượng (object): "BangDuLieu":
`NoiDung`: Trích từ cột "Nội dung thanh toán"
`TenKMCP`: Trích khoản mục chi phí tại `NoiDung` gán vào cột `TenKMCP` và loại bỏ cụm từ "Thanh toán" hoặc "Tạm ứng" hoặc "hoàn thành" hoặc "giai đoạn...", viết hoa chữ cái đầu của từ đầu tiên sau khi loại bỏ cụm từ "Thanh toán" hoặc "Tạm ứng" hoặc "hoàn thành" hoặc "giai đoạn..."
`SoTien`: Trích từ cột "Số đề nghị tạm ứng, thanh toán khối lượng hoàn thành kỳ này (Vốn trong nước)" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
### Yêu cầu xử lý:
- Không suy diễn hoặc bổ sung thông tin không có trong văn bản
- Tự động loại bỏ dấu chấm phân cách hàng nghìn trong số tiền



{{CHUCNANG15}} Chức năng `Giải ngân vốn đầu tư`
### Chứng từ để nhận dạng thông tin là `GIẤY RÚT VỐN`, mẫu số 05/TT
### Thông tin chung của văn bản, tên đối tượng (object) "ThongTinChung":
`KyHieu`: "GIAI_NGAN_GRV"
`SoVanBan`: Trích số hiệu ở đầu văn bản sau chữ "Số:"
`NgayKy`: Ngày ký văn bản (thường là cùng ngày chứng từ), trích từ dòng "Ngày ... tháng ... năm ..." gần khu chữ ký, định dạng (dd/MM/yyyy)
`SoVanBanCanCu`: Trích từ dòng "Căn cứ Giấy đề nghị thanh toán vốn đầu tư số: ..."
`NgayKyCanCu`: Trích "ngày .../.../..." của "Căn cứ Giấy đề nghị thanh toán vốn đầu tư", cùng dòng `SoVanBanCanCu` định dạng (dd/MM/yyyy)
`NienDo`: Trích từ dòng “Năm NS: ...” (Năm ngân sách)
`NghiepVuID`: Nếu checkbox [x] nằm ở mục “Thực chi” ghi `010`, nếu checkbox [x] nằm ở mục “Tạm ứng” ghi `011`, nếu checkbox [x] nằm ở mục “Ứng trước đủ điều kiện thanh toán” ghi `013`, nếu checkbox [x] nằm ở mục “Ứng trước chưa đủ điều kiện thanh toán” ghi `014`, ngược lại ghi `""`
`LoaiKHVonID`: Trích Năm kế hoạch vốn (cột 6), nếu `NienDo` bằng `LoaiKHVonID` thì gán `2`, nếu `NienDo` lơn hơn `LoaiKHVonID`  thì gán `1` ngược lại gán `3`
`GiaTri`: Lấy giá trị tổng số tiền đề nghị tạm ứng, thanh toán bằng số, tại dòng "Tổng số tiền đề nghị tạm ứng, thanh toán bằng số:" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`TenNhaThau`: Trích từ dòng “Đơn vị nhận tiền” hoặc “THANH TOÁN CHO ĐƠN VỊ HƯỞNG”.
`NguoiKy`: Trích tên người ký tại mục "LÃNH ĐẠO ĐƠN VỊ" hoặc “BAN QUẢN LÝ DỰ ÁN”, dưới chữ ký
`ChucDanhNguoiKy`: Trích dòng nằm `ngay phía trên tên người ký`
`CoQuanBanHanh`: Tên chủ đầu tư (trích sau dòng có cụm từ “Chủ đầu tư:” hoặc “Đại diện chủ đầu tư”)	
`TrichYeu`: Lấy nội dung thanh toán của bảng dữ liệu (nếu nhiều nội dung thì nối chuỗi lại cách nhau dấu chấm phẩy `; `)
### Bảng khối lượng công việc hoàn thành, mỗi dòng là một bản ghi với các cột sau, tên đối tượng (object): "BangDuLieu":
`NoiDung`: Tên nội dung chi, trích từ (cột 1)
`TenKMCP`: Bạn PHẢI xử lý theo đúng theo yêu cầu sau:
- Nếu `NoiDung` có chứa cụm từ "Bảo hành công trình" thì `TenKMCP` = "Chi phí xây dựng" ngược lại trích khoản mục chi phí tại `NoiDung` gán vào cột `TenKMCP`. 
- Nếu `TenKMCP` có chứa cụm từ "Thanh toán" hoặc "Tạm ứng" hoặc "hoàn thành" hoặc "giai đoạn..." thì loại bỏ cụm từ "Thanh toán" hoặc "Tạm ứng" hoặc "hoàn thành" hoặc "giai đoạn...".
- Viết hoa chữ cái đầu của từ đầu tiên sau khi loại bỏ cụm từ "Thanh toán" hoặc "Tạm ứng" hoặc "hoàn thành" hoặc "giai đoạn...".
`MaNDKT`: Mã nội dung kinh tế (cột 2)
`MaChuong`: Mã chương (cột 3)
`MaNganhKT`: Mã ngành kinh tế (cột 4)
`MaNguonNSNN`: Mã nguồn ngân sách nhà nước (cột 5)
`NienDo`: Năm kế hoạch vốn (cột 6)
`SoTien`: Tổng số tiền (cột 7) (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
### Yêu cầu xử lý:
- Không suy diễn hoặc bổ sung thông tin không có trong văn bản
- Tự động loại bỏ dấu chấm phân cách hàng nghìn trong số tiền



{{CHUCNANG16}} Chức năng `Giải ngân vốn đầu tư`
### Chứng từ để nhận dạng thông tin là `GIẤY ĐỀ NGHỊ THU HỒI VỐN`, mẫu số 04.b/TT
### Thông tin chung của văn bản, tên đối tượng (object) "ThongTinChung":
`KyHieu`: "GIAI_NGAN_THV"
`SoVanBan`: Trích số hiệu ở đầu văn bản sau chữ "Số:"
`NgayKy`: Ngày ký văn bản (thường là cùng ngày chứng từ), trích từ dòng "Ngày ... tháng ... năm ..." gần khu chữ ký, định dạng (dd/MM/yyyy)
`SoVanBanCanCu`: Trích từ dòng "Căn cứ Giấy đề nghị thanh toán vốn: ..."
`NgayKyCanCu`: Trích "ngày .../.../..." của "Căn cứ Giấy đề nghị thanh toán vốn đầu tư", cùng dòng `SoVanBanCanCu` định dạng (dd/MM/yyyy)
`NienDo`: Trích từ dòng “Năm NS: ...” (Năm ngân sách)
`NghiepVuID`: Nếu checkbox [x] nằm ở mục “Tạm ứng sang thực chi” ghi `012`, nếu checkbox [x] nằm ở mục “Ứng trước chưa đủ ĐKTT sang ứng trước đủ ĐKTT” ghi `015`, ngược lại ghi `""`
`GiaTri`: Lấy số tiền tổng cộng tại cột "Số cơ quan kiểm soát, thanh toán duyệt thanh toán" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`NguoiKy`: Trích tên người ký tại mục "LÃNH ĐẠO ĐƠN VỊ" hoặc "BAN QUẢN LÝ DỰ ÁN", dưới chữ ký
`ChucDanhNguoiKy`: Trích dòng nằm `ngay phía trên tên người ký`
`CoQuanBanHanh`: Tên chủ đầu tư (trích sau dòng có cụm từ "Chủ đầu tư:" hoặc "Đại diện chủ đầu tư")	
`TrichYeu`: Lấy nội dung thanh toán của bảng dữ liệu (nếu nhiều nội dung thì nối chuỗi lại cách nhau dấu chấm phẩy `; `)
### Bảng khối lượng công việc hoàn thành, mỗi dòng là một bản ghi với các cột sau, tên đối tượng (object): "BangDuLieu":
`NoiDung`: Trích từ cột "Nội dung"
`TenKMCP`: Trích khoản mục chi phí tại `NoiDung` gán vào cột `TenKMCP` và loại bỏ cụm từ "Thanh toán" hoặc "Tạm ứng" hoặc "hoàn thành" hoặc "giai đoạn...", viết hoa chữ cái đầu của từ đầu tiên sau khi loại bỏ cụm từ "Thanh toán" hoặc "Tạm ứng" hoặc "hoàn thành" hoặc "giai đoạn..."
`MaNDKT`: Trích từ cột "Mã nội dung kinh tế (Mã NDKT)"
`MaChuong`: Trích từ cột "Mã chương"
`MaNganhKT`: Trích từ cột "Mã ngành kinh tế (Mã ngành KT)"
`MaNguonNSNN`: Trích từ cột "Mã nguồn ngân sách nhà nước (Mã NSNN)"
`NienDo`: Trích từ cột "Năm kế hoạch vốn (Năm KHV)" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`SoTien`: Trích từ cột "Số cơ quan kiểm soát, thanh toán duyệt thanh toán" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
### Yêu cầu xử lý:
- Không suy diễn hoặc bổ sung thông tin không có trong văn bản
- Tự động loại bỏ dấu chấm phân cách hàng nghìn trong số tiền