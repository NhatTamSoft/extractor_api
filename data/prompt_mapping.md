Chức năng `Quyết định phê duyệt chủ trương đầu tư`
### Văn bản để nhận dạng thông tin là: "Quyết định phê duyệt chủ trương đầu tư hoặc phê duyệt điều chỉnh chủ trương đầu tư"
### Thông tin chung của văn bản, tên đối tượng (object) "ThongTinChung":
`KyHieu`: "QDPD_CT"
`SoVanBan`: Trích số hiệu văn bản ghi ở đầu văn bản, sau chữ "Số:" (tuyệt đối không bịa, không suy diễn, không được đoán, không điền bất kỳ nội dung nào khác ngoài văn bản)
`NgayKy`: Trích thông tin ngày ký ở đầu văn bản, sau dòng địa danh "..., ngày ..." định dạng (dd/MM/yyyy)
`SoVanBanCanCu`: Trích "số hiệu văn bản" Báo cáo thẩm định báo cáo đề xuất chủ trương đầu tư, tại dòng "Căn cứ Báo cáo thẩm định số..." hoặc "Căn cứ Báo cáo số ..." có chứa cụm từ "báo cáo đề xuất chủ trương đầu tư..."
`NgayKyCanCu`: Trích "ngày...tháng...năm ... Báo cáo thẩm định" báo cáo đề xuất chủ trương đầu tư, tại dòng "Căn cứ Báo cáo thẩm định số..." hoặc "Căn cứ Báo cáo số ..." có chứa cụm từ "báo cáo đề xuất chủ trương đầu tư..."  định dạng (dd/MM/yyyy)
`NguoiKy`: Trích tên người ký văn bản ở phần cuối văn bản, ngay dưới dòng "KT. CHỦ TỊCH" hoặc "CHỦ TỊCH".
`ChucDanhNguoiKy`: Trích phần ghi rõ chức vụ người ký văn bản (VD: "CHỦ TỊCH", "PHÓ CHỦ TỊCH", "KT. CHỦ TỊCH – PHÓ CHỦ TỊCH").
`CoQuanBanHanh`: Trích xuất chính xác tên cơ quan ban hành văn bản theo đúng quy định tại Nghị định 30/2020/NĐ-CP về công tác văn thư. Nếu dòng đầu là tên cơ quan chủ quản và dòng thứ hai là đơn vị trực thuộc thì chỉ lấy dòng thứ hai làm cơ quan ban hành.
`TrichYeu`: Trích nguyên văn phần tiêu đề nằm ngay sau chữ "QUYẾT ĐỊNH", thường bắt đầu bằng "Về việc..." hoặc "V/v..." hoặc "Về chủ trương...".
`TenNguonVon`: Trích tên nguồn vốn sau cụm từ "nguồn vốn: ...", nếu không có để ""
`GiaTri`: Trích thông tin số tiền ngay sau cụm từ "tổng mức đầu tư", thường bắt đầu bằng "tổng mức đầu tư..." hoặc "... kinh phí" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`DieuChinh`: Gán `1` nếu "trích yếu văn bản" có chứa nội dung "điều chỉnh...", ngược lại gán `0`.
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

3. Kết quả xuất ra dạng JSON duy nhất có dạng
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