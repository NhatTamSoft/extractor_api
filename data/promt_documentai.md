{{CHUCNANG02}} Chức năng `Quyết định phê duyệt chủ trương đầu tư`
### Văn bản để nhận dạng thông tin là: "Quyết định phê duyệt chủ trương đầu tư hoặc phê duyệt điều chỉnh chủ trương đầu tư"
### Thông tin chung của văn bản, tên đối tượng (object) "ThongTinChung":
`KyHieu`: "QDPD_CT"
`SoVanBan`: Trích số hiệu văn bản ghi ở đầu văn bản, sau chữ "Số:" theo quy tắc "^\d{1,6}(\/\d{1,4})?(\/)?(QĐ|TTr|BC|TB|CV)-UBND$"
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


{{CHUCNANG03}} Chức năng `Quyết định phê duyệt dự toán giai đoạn chuẩn bị đầu tư`
### Văn bản để nhận dạng thông tin là: "Quyết định phê duyệt dự toán giai đoạn chuẩn bị đầu tư, quyết định điều chỉnh dự toán giai đoạn chuẩn bị đầu tư"
### Thông tin chung của văn bản, tên đối tượng (object) "ThongTinChung":
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
### Bảng số liệu dự toán, mỗi dòng là một bản ghi với các cột sau, tên đối tượng (object): "BangDuLieu":
`TenKMCP`: Tên khoản mục chi phí, giữ nguyên tên khoản mục chi phí theo văn bản
`GiaTriDuToanKMCP`: Giá trị thành tiền hoặc giá trị cột **"Sau thuế"**, không lấy cột "Trước thuế" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`GiaTriDuToanKMCPTang`: Nếu `DieuChinh` bằng `1` thì trích "Giá trị dự toán tăng" ngược lại gán `0` (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`GiaTriDuToanKMCPGiam`: Nếu `DieuChinh` bằng `1` thì trích "Giá trị dự toán giảm" ngược lại gán `0` (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)

### 🚫 **Quy tắc loại bỏ Loại công trình**:
Nếu một dòng **thuộc "Danh sách Loại công trình"** dưới đây thì:
❌ **Không xuất dòng không thuộc "Danh sách Loại công trình"**
✅ **Chỉ xuất các dòng thuộc "Danh sách Loại công trình"**
**Danh sách Loại công trình**
|  Mã |Loại công trình                               |
|-----|----------------------------------------------|
| `1` |Công trình dân dụng                           |
| `2` |Công trình công nghiệp                        |
| `3` |Công trình giao thông                         |
| `4` |Công trình nông nghiệp và phát triển nông thôn|
| `5` |Công trình hạ tầng kỹ thuật                   |

### Yêu cầu xử lý:
🚫 **Không lấy giá trị trong cột "Trước thuế"**
✅ Chỉ lấy giá trị tại đúng cột có tiêu đề "Sau thuế"
- Gộp toàn bộ bảng trong tất cả ảnh thành một danh sách duy nhất, đúng thứ tự
- Giữ nguyên tên gọi và định dạng số tiền như trong ảnh, không tự ý chuẩn hóa
- Không suy diễn hoặc bổ sung thông tin không có trong văn bản
- Tự động loại bỏ dấu chấm phân cách hàng nghìn trong số tiền
- Hãy trích xuất chính xác chuỗi ký tự trước chữ ‘đồng’, bao gồm cả dấu chấm như trong bản gốc.



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
`DieuChinh`: Gán `1` nếu "trích yếu văn bản" có chứa nội dung "điều chỉnh...", ngược lại gán `0`.
### Bảng Phụ lục gói thầu, mỗi dòng là một bản ghi với các cột sau, tên đối tượng (object): "BangDuLieu":
`TenDauThau`: Trích tên gói thầu (không lấy thông tin tại cột tóm tắt, mô tả công việc của gói thầu)
`TenKMCP`: Trích tên gói thầu (không lấy thông tin tại cột tóm tắt, mô tả công việc của gói thầu), loại bỏ các cụm từ ("Gói thầu số xx:", "Gói số xx:", "Gói xx:", "Tên gói thầu số xx:")
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
`SoVanBanCanCu`: Trích `số hiệu quyết định phê duyệt kế hoạch lựa chọn nhà thầu`, tại dòng "Căn cứ Quyết định ... phê duyệt kế hoạch lựa chọn nhà thầu" hoặc `số biên bản thương thảo (hoặc hoàn thiện) hợp đồng`, tại dòng "Căn cứ biên bản thương thảo (hoặc hoàn thiện) hợp đồng ..."
`NgayKyCanCu`: Trích "ngày...tháng...năm ..." Quyết định phê duyệt kế hoạch lựa chọn nhà thầu, tại dòng "Căn cứ Quyết định ... phê duyệt kế hoạch lựa chọn nhà thầu" hoặc "ngày...tháng...năm ..." biên bản thương thảo (hoặc hoàn thiện) hợp đồng`, tại dòng "Căn cứ biên bản thương thảo (hoặc hoàn thiện) hợp đồng ..." định dạng (dd/MM/yyyy)
`NgayKy`: Trích thông tin ngày ký ở đầu văn bản, sau dòng địa danh "..., ngày ...", định dạng "dd/MM/yyyy"
`NguoiKy`: Trích tên người ký văn bản ở phần cuối văn bản.
`ChucDanhNguoiKy`: Trích phần ghi rõ chức vụ người ký văn bản.
`CoQuanBanHanh`: Trích xuất chính xác tên cơ quan ban hành văn bản theo đúng quy định tại Nghị định 30/2020/NĐ-CP về công tác văn thư. Nếu dòng đầu là tên cơ quan chủ quản và dòng thứ hai là đơn vị trực thuộc thì chỉ lấy dòng thứ hai làm cơ quan ban hành.
`TrichYeu`: Trích nguyên văn tiêu đề ngay dưới dòng "QUYẾT ĐỊNH" (thường bắt đầu bằng "Về việc...")
`TenNhaThau`: Trích từ dòng "đơn vị chỉ định thầu" hoặc "đơn vị trúng thầu"
`GiaTri`: Trích thông tin số tiền ngay sau cụm từ "giá chỉ định thầu" hoặc "giá trị trúng thầu", thường tại dòng "Bằng chữ: ..." (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`DieuChinh`: Gán `1` nếu "trích yếu văn bản" có chứa nội dung "điều chỉnh...", ngược lại gán `0`.
### Bảng dữ liệu gói thầu, mỗi dòng là một bản ghi với các cột sau, tên đối tượng (object): "BangDuLieu":
`TenDauThau`: Trích `tên gói thầu`, sau cụm từ "Nội dung gói thầu:..." hoặc "Tên gói thầu:..."
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
`DieuChinh`: Gán `1` nếu "trích yếu văn bản" có chứa nội dung "điều chỉnh...", ngược lại gán `0`
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
### Văn bản để nhận dạng thông tin là: "Quyết định phê duyệt dự toán giai đoạn thực hiện đầu tư, quyết định điều chỉnh dự toán giai đoạn thực hiện đầu tư"
### Thông tin chung của văn bản, tên đối tượng (object) "ThongTinChung":
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
### Bảng số liệu tổng mức đầu tư, mỗi dòng là một bản ghi với các cột sau, tên đối tượng (object): "BangDuLieu":
`TenKMCP`: Tên khoản mục chi phí, giữ nguyên tên khoản mục chi phí theo văn bản
`GiaTriDuToanKMCP`: Giá trị thành tiền hoặc giá trị cột **"Sau thuế"**, không lấy cột "Trước thuế" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`GiaTriDuToanKMCPTang`: Nếu `DieuChinh` bằng `1` thì trích "Giá trị dự toán tăng" ngược lại gán `0` (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`GiaTriDuToanKMCPGiam`: Nếu `DieuChinh` bằng `1` thì trích "Giá trị dự toán giảm" ngược lại gán `0` (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
### 🚫 **Quy tắc loại bỏ Loại công trình**:
Nếu một dòng **thuộc "Danh sách Loại công trình"** dưới đây thì:
❌ **Không xuất dòng không thuộc "Danh sách Loại công trình"**
✅ **Chỉ xuất các dòng thuộc "Danh sách Loại công trình"**
**Danh sách Loại công trình**
|  Mã |Loại công trình                               |
|-----|----------------------------------------------|
| `1` |Công trình dân dụng                           |
| `2` |Công trình công nghiệp                        |
| `3` |Công trình giao thông                         |
| `4` |Công trình nông nghiệp và phát triển nông thôn|
| `5` |Công trình hạ tầng kỹ thuật                   |

### Yêu cầu xử lý:
🚫 **Không lấy giá trị trong cột "Trước thuế"**
✅ Chỉ lấy giá trị tại đúng cột có tiêu đề "Sau thuế"
- Gộp toàn bộ bảng trong tất cả ảnh thành một danh sách duy nhất, đúng thứ tự
- Giữ nguyên tên gọi và định dạng số tiền như trong ảnh, không tự ý chuẩn hóa
- Không suy diễn hoặc bổ sung thông tin không có trong văn bản
- Tự động loại bỏ dấu chấm phân cách hàng nghìn trong số tiền
- Hãy trích xuất chính xác chuỗi ký tự trước chữ ‘đồng’, bao gồm cả dấu chấm như trong bản gốc.


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
`DieuChinh`: Gán `1` nếu trích yếu văn bản có chứa nội dung "điều chỉnh...", ngược lại gán `0`.
**Bảng Phụ lục gói thầu, mỗi dòng là một bản ghi với các cột sau, tên đối tượng (object): `BangDuLieu`:
`TenDauThau`: Trích tên gói thầu (không lấy thông tin tại cột tóm tắt, mô tả công việc của gói thầu)
`TenKMCP`: Trích tên gói thầu (không lấy thông tin tại cột tóm tắt, mô tả công việc của gói thầu), loại bỏ các cụm từ ("Gói thầu số xx:", "Gói số xx:", "Gói xx:", "Tên gói thầu số xx:")
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
`SoVanBanCanCu`: Trích `số hiệu quyết định phê duyệt kế hoạch lựa chọn nhà thầu`, tại dòng "Căn cứ Quyết định ... phê duyệt kế hoạch lựa chọn nhà thầu" hoặc `số biên bản thương thảo (hoặc hoàn thiện) hợp đồng`, tại dòng "Căn cứ biên bản thương thảo (hoặc hoàn thiện) hợp đồng ..."
`NgayKyCanCu`: Trích "ngày...tháng...năm ..." Quyết định phê duyệt kế hoạch lựa chọn nhà thầu, tại dòng "Căn cứ Quyết định ... phê duyệt kế hoạch lựa chọn nhà thầu" hoặc "ngày...tháng...năm ..." biên bản thương thảo (hoặc hoàn thiện) hợp đồng`, tại dòng "Căn cứ biên bản thương thảo (hoặc hoàn thiện) hợp đồng ..." định dạng (dd/MM/yyyy)
`NgayKy`: Trích thông tin ngày ký ở đầu văn bản, sau dòng địa danh "..., ngày ...", định dạng (dd/MM/yyyy)
`NguoiKy`: Trích tên người ký văn bản ở phần cuối văn bản.
`ChucDanhNguoiKy`: Trích phần ghi rõ chức vụ người ký văn bản.
`CoQuanBanHanh`: Trích xuất chính xác tên cơ quan ban hành văn bản theo đúng quy định tại Nghị định 30/2020/NĐ-CP về công tác văn thư. Nếu dòng đầu là tên cơ quan chủ quản và dòng thứ hai là đơn vị trực thuộc thì chỉ lấy dòng thứ hai làm cơ quan ban hành.
`TrichYeu`: Trích nguyên văn tiêu đề ngay dưới dòng "QUYẾT ĐỊNH" (thường bắt đầu bằng "Về việc...")
`TenNhaThau`: Trích từ dòng "đơn vị chỉ định thầu" hoặc "đơn vị trúng thầu"
`GiaTri`: Trích thông tin số tiền ngay sau cụm từ "giá chỉ định thầu" hoặc "giá trị trúng thầu", thường tại dòng "Bằng chữ: ..." (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`DieuChinh`: Gán `1` nếu "trích yếu văn bản" có chứa nội dung "điều chỉnh...", ngược lại gán `0`.
### Bảng dữ liệu gói thầu, mỗi dòng là một bản ghi với các cột sau, tên đối tượng (object): "BangDuLieu":
`TenDauThau`: Trích `tên gói thầu`, sau cụm từ "Nội dung gói thầu:..." hoặc "Tên gói thầu:..."
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
`TrichYeu`: Lấy trích yếu văn bản
### Bảng khối lượng công việc của hợp đồng, mỗi dòng là một bản ghi với các cột sau, tên đối tượng (object): "BangDuLieu":
`GiaTriHopDong`:  Lấy giá trị hợp đồng (Giá trị đã có thuế hoặc Giá trị sau thuế) (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn), nếu không có thì lấy bằng "0"
### Yêu cầu xử lý:
- Không suy diễn hoặc bổ sung thông tin không có trong văn bản
- Tự động loại bỏ dấu chấm phân cách hàng nghìn trong số tiền



{{CHUCNANG11}} Chức năng `Phụ lục hợp đồng`
### Thông tin chung của văn bản, tên đối tượng (object) "ThongTinChung":
`KyHieu`: "PL_HOP_DONG"
`SoVanBan`: Trích số phụ lục hợp đồng, thường bắt đầu bằng "Phụ lục hợp đồng số:..." hoặc "Số phụ lục:..." hoặc "Phụ lục số:..."
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
### Bảng khối lượng công việc của phụ lục hợp đồng, mỗi dòng là một bản ghi với các cột sau, tên đối tượng (object): "BangDuLieu":
`GiaTriHopDong`: Lấy giá trị phụ lục hợp đồng (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn), nếu không có thì lấy bằng 0
### Yêu cầu xử lý:
- Không suy diễn hoặc bổ sung thông tin không có trong văn bản
- Tự động loại bỏ dấu chấm phân cách hàng nghìn trong số tiền



{{CHUCNANG12}} Chức năng `Khối lượng công việc hoàn thành (viết tắt KLCVHT) thông qua hợp đồng`
### Văn bản để nhận dạng thông tin là: "Bảng xác định giá trị khối lượng công việc hoàn thành, mẫu số 03.a/TT"
### Thông tin chung của văn bản, tên đối tượng (object) "ThongTinChung":
`KyHieu`: "KLCVHT_THD"
`SoVanBan`: Số biên bản nghiệm thu (trích sau dòng "Biên bản nghiệm thu số..." hoặc dòng tương đương), nếu có nhiều dòng tương tự nối chuỗi Số biên bản nghiệm thu lại 
`NgayKy`: Ngày ký chứng từ trích sau dòng "Biên bản nghiệm thu số ..., ngày ... tháng ... năm ...") định dạng (dd/MM/yyyy)
`SoVanBanCanCu`: Số hợp đồng chính (trích sau cụm "Hợp đồng số...")
`NgayKyCanCu`: Trích "ngày...tháng...năm ..." hợp đồng, trích sau cụm "Hợp đồng số..." định dạng (dd/MM/yyyy)
`SoHopDong`: Giống cột `SoVanBanCanCu`
`SoPLHopDong`: Số phụ lục hợp đồng (nếu có, trích sau cụm "Phụ lục số..." hoặc "Phụ lục bổ sung số...")
`LanThanhToan`: Lần thanh toán (trích sau cụm từ "Thanh toán lần thứ..."). Ví dụ: "01", "02", "03"
`TenNhaThau`: Tên nhà thầu (trích sau dòng "Nhà thầu:" hoặc "Đơn vị thi công...")
`NguoiKy`: Trích tên người ký văn bản:
            - Tìm tại phần cuối trang, thường ngay dưới dòng "ĐẠI DIỆN CHỦ ĐẦU TƯ" hoặc "ĐẠI DIỆN NHÀ THẦU"
            - Là dòng chữ `in hoa hoặc in thường có họ tên đầy đủ`, nằm trên chữ ký tay
            - Nếu có đóng dấu, tên người ký nằm bên dưới
`ChucDanhNguoiKy`: Trích dòng nằm "ngay phía trên tên người ký", ví dụ: "Giám đốc", "Phó giám đốc", "Kế toán trưởng", "Chủ tịch", "KT. Chủ tịch – Phó Chủ tịch".
`CoQuanBanHanh`: Tên chủ đầu tư (trích sau dòng có cụm từ "Chủ đầu tư:" hoặc "Đại diện chủ đầu tư")
`TrichYeu`: Trích cụm từ "Khối lượng công việc hoàn thành theo Hợp đồng số: ..." Trích sau cụm từ "Thanh toán lần thứ:"
`GiaTriHopDong`: Trích `giá trị hợp đồng` tại dòng "`1. Giá trị hợp đồng (giá trị dự toán được duyệt...)" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`TamUngChuaThuaHoi`: Trích `giá trị tạm ứng còn lại chưa thu hồi đến cuối kỳ trước` tại dòng "2. Giá trị tạm ứng còn lại chưa thu hồi đến cuối kỳ trước" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`ThanhToanDenCuoiKyTruoc`: Trích `số tiền đã thanh toán khối lượng hoàn thành đến cuối kỳ trước` tại dòng "3. Số tiền đã thanh toán khối lượng hoàn thành đến cuối kỳ trước" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`LuyKeDenCuoiKy`: Trích `luỹ kế giá trị khối lượng thực hiện đến cuối kỳ này` tại dòng "4. Luỹ kế giá trị khối lượng thực hiện đến cuối kỳ này" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`ThanhToanThuHoiTamUng`: Trích `thanh toán để thu hồi tạm ứng` tại dòng "5. Thanh toán để thu hồi tạm ứng" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`GiaiNganKyNay`: Trích `giá trị đề nghị giải ngân kỳ này` tại dòng "6. giá trị đề nghị giải ngân kỳ này" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`TamUngGiaiNganKyNayKyTruoc`: Trích `số tiền tạm ứng` ngay dưới dòng "số tiền bằng chữ..." (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`ThanhToanKLHTKyTruoc`: Trích `số tiền thanh toán khối lượng hoàn thành` ngay dưới dòng "số tiền bằng chữ..." (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`LuyKeGiaiNgan`: Trích `số tiền` ngay dưới dòng "7. Luỹ kế giá trị giải ngân:" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`TamUngThanhToan`: Trích `số tiền tạm ứng` ngay dưới dòng "7. Luỹ kế giá trị giải ngân:" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`ThanhToanKLHT`: Trích `số tiền thanh toán khối lượng hoàn thành` ngay dưới dòng "7. Luỹ kế giá trị giải ngân:" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
### Bảng khối lượng công việc hoàn thành, mỗi dòng là một bản ghi với các cột sau, tên đối tượng (object): "BangDuLieu":
`TenKMCP`: Tên công việc được ghi trong cột "Tên công việc"
`GiaTriNghiemThu`: Trích giá trị `thực hiện kỳ này` trong bảng dữ liệu (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
### Yêu cầu xử lý:
- Không suy diễn hoặc bổ sung thông tin không có trong văn bản
- Tự động loại bỏ dấu chấm phân cách hàng nghìn trong số tiền

{{CHUCNANG13}} Chức năng `Khối lượng công việc hoàn thành (viết tắt KLCVHT) không thông qua hợp đồng`
### Văn bản để nhận dạng thông tin là: "Bảng xác định giá trị khối lượng công việc hoàn thành, mẫu số 03.b/TT"
### Thông tin chung của văn bản, tên đối tượng (object) "ThongTinChung":
`KyHieu`: "KLCVHT_NHD"
`SoVanBan`: Số biên bản nghiệm thu (trích sau dòng "Biên bản nghiệm thu số..." hoặc dòng tương đương)
`NgayKy`: Ngày ký chứng từ trích sau dòng "Biên bản nghiệm thu số ..., ngày ... tháng ... năm ..." định dạng (dd/MM/yyyy)
`SoVanBanCanCu`: Số hợp đồng chính (trích sau cụm "Hợp đồng số...")
`NgayKyCanCu`: Trích "ngày...tháng...năm ..." hợp đồng, trích sau cụm "Hợp đồng số..." định dạng (dd/MM/yyyy)
`SoHopDong`: Giống cột `SoVanBanCanCu`
`SoPLHopDong`: Số phụ lục hợp đồng (nếu có, trích sau cụm "Phụ lục số..." hoặc "Phụ lục bổ sung số...")
`LanThanhToan`: Lần thanh toán (trích sau cụm từ "Thanh toán lần thứ...")
`TenNhaThau`: Tên nhà thầu (trích sau dòng "Nhà thầu:" hoặc "Đơn vị thi công...")
`NguoiKy`: Trích tên người ký văn bản:
- Tìm tại phần cuối trang, thường ngay dưới dòng "ĐẠI DIỆN CHỦ ĐẦU TƯ" hoặc "ĐẠI DIỆN NHÀ THẦU".
- Là dòng chữ `in hoa hoặc in thường có họ tên đầy đủ`, nằm trên chữ ký tay.
- Nếu có đóng dấu, tên người ký nằm bên dưới.
`ChucDanhNguoiKy`: Trích dòng nằm "ngay phía trên tên người ký", ví dụ: "Giám đốc", "Phó giám đốc", "Kế toán trưởng", "Chủ tịch", "KT. Chủ tịch – Phó Chủ tịch".
`CoQuanBanHanh`: Tên chủ đầu tư (trích sau dòng có cụm từ "Chủ đầu tư:" hoặc "Đại diện chủ đầu tư")
`TrichYeu`: Trích cụm từ "Khối lượng công việc hoàn thành theo Hợp đồng số: ..." Trích sau cụm từ "Thanh toán lần thứ:"
`GiaTriHopDong`: Trích `giá trị hợp đồng` tại dòng "`1. Giá trị hợp đồng (giá trị dự toán được duyệt...)" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`TamUngChuaThuaHoi`: Trích `giá trị tạm ứng còn lại chưa thu hồi đến cuối kỳ trước` tại dòng "2. Giá trị tạm ứng còn lại chưa thu hồi đến cuối kỳ trước"
`ThanhToanDenCuoiKyTruoc`: Trích `số tiền đã thanh toán khối lượng hoàn thành đến cuối kỳ trước` tại dòng "3. Số tiền đã thanh toán khối lượng hoàn thành đến cuối kỳ trước"
`LuyKeDenCuoiKy`: Trích `luỹ kế giá trị khối lượng thực hiện đến cuối kỳ này` tại dòng "4. Luỹ kế giá trị khối lượng thực hiện đến cuối kỳ này"
`ThanhToanThuHoiTamUng`: Trích `thanh toán để thu hồi tạm ứng` tại dòng "5. Thanh toán để thu hồi tạm ứng"
`GiaiNganKyNay`: Trích `giá trị đề nghị giải ngân kỳ này` tại dòng "6. giá trị đề nghị giải ngân kỳ này"
`TamUngGiaiNganKyNayKyTruoc`: Trích `số tiền tạm ứng` ngay dưới dòng "số tiền bằng chữ..."
`ThanhToanKLHTKyTruoc`: Trích `số tiền thanh toán khối lượng hoàn thành` ngay dưới dòng "số tiền bằng chữ..."
`LuyKeGiaiNgan`: Trích `số tiền` ngay dưới dòng "7. Luỹ kế giá trị giải ngân:"
`TamUngThanhToan`: Trích `số tiền tạm ứng` ngay dưới dòng "7. Luỹ kế giá trị giải ngân:"
`ThanhToanKLHT`: Trích `số tiền thanh toán khối lượng hoàn thành` ngay dưới dòng "7. Luỹ kế giá trị giải ngân:"
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
`SoVanBanCanCu`: Giống cột `SoHopDong`
`NgayKyCanCu`: Trích "ngày...tháng...năm ..." của hợp đồng, cùng dòng `SoHopDong` định dạng (dd/MM/yyyy)
`SoPLHopDong`: Trích số phụ lục hợp đồng sau cụm từ "Phụ lục bổ sung hợp đồng số:..."
`TenNguonVon`: Trích sau dòng "Thuộc nguồn vốn:"
`NienDo`: Trích sau dòng "Năm:", phía trên dòng tiêu đề của bảng số liệu
`LoaiKHVonID`: Trích sau dòng "Thuộc kế hoạch:", nếu `NienDo` bằng `LoaiKHVonID` thì gán `2`, nếu `NienDo` lơn hơn `LoaiKHVonID`  thì gán `1` ngược lại gán `3`
`SoTien`: Lấy giá trị tổng số tiền đề nghị tạm ứng, thanh toán bằng số, tại dòng "Tổng số tiền đề nghị tạm ứng, thanh toán bằng số:"
`NguoiKy`: Trích tên người ký tại mục "LÃNH ĐẠO ĐƠN VỊ" hoặc "BAN QUẢN LÝ DỰ ÁN", dưới chữ ký
`ChucDanhNguoiKy`: Trích dòng nằm ngay phía trên tên người ký
`CoQuanBanHanh`: Trích sau dòng có cụm từ "Chủ đầu tư:" hoặc "Chủ đầu tư/Ban QLDA:"
`TrichYeu`: Lấy nội dung thanh toán của bảng dữ liệu (nếu nhiều nội dung thì nối chuỗi lại cách nhau dấu chấm phẩy `; `)
### Bảng khối lượng công việc hoàn thành, mỗi dòng là một bản ghi với các cột sau, tên đối tượng (object): "BangDuLieu":
`NoiDung`: Trích từ cột "Nội dung thanh toán"
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
`SoTien`: Lấy giá trị tổng số tiền đề nghị tạm ứng, thanh toán bằng số, tại dòng "Tổng số tiền đề nghị tạm ứng, thanh toán bằng số:" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`TenNhaThau`: Trích từ dòng “Đơn vị nhận tiền” hoặc “THANH TOÁN CHO ĐƠN VỊ HƯỞNG”.
`NguoiKy`: Trích tên người ký tại mục "LÃNH ĐẠO ĐƠN VỊ" hoặc “BAN QUẢN LÝ DỰ ÁN”, dưới chữ ký
`ChucDanhNguoiKy`: Trích dòng nằm `ngay phía trên tên người ký`
`CoQuanBanHanh`: Tên chủ đầu tư (trích sau dòng có cụm từ “Chủ đầu tư:” hoặc “Đại diện chủ đầu tư”)	
`TrichYeu`: Lấy nội dung thanh toán của bảng dữ liệu (nếu nhiều nội dung thì nối chuỗi lại cách nhau dấu chấm phẩy `; `)
### Bảng khối lượng công việc hoàn thành, mỗi dòng là một bản ghi với các cột sau, tên đối tượng (object): "BangDuLieu":
`NoiDung`: Tên nội dung chi, trích từ (cột 1)
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
`SoTien`: Lấy số tiền tổng cộng tại cột "Số cơ quan kiểm soát, thanh toán duyệt thanh toán" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`NguoiKy`: Trích tên người ký tại mục "LÃNH ĐẠO ĐƠN VỊ" hoặc "BAN QUẢN LÝ DỰ ÁN", dưới chữ ký
`ChucDanhNguoiKy`: Trích dòng nằm `ngay phía trên tên người ký`
`CoQuanBanHanh`: Tên chủ đầu tư (trích sau dòng có cụm từ "Chủ đầu tư:" hoặc "Đại diện chủ đầu tư")	
`TrichYeu`: Lấy nội dung thanh toán của bảng dữ liệu (nếu nhiều nội dung thì nối chuỗi lại cách nhau dấu chấm phẩy `; `)
### Bảng khối lượng công việc hoàn thành, mỗi dòng là một bản ghi với các cột sau, tên đối tượng (object): "BangDuLieu":
`NoiDung`: Trích từ cột "Nội dung"
`MaNDKT`: Trích từ cột "Mã nội dung kinh tế (Mã NDKT)"
`MaChuong`: Trích từ cột "Mã chương"
`MaNganhKT`: Trích từ cột "Mã ngành kinh tế (Mã ngành KT)"
`MaNguonNSNN`: Trích từ cột "Mã nguồn ngân sách nhà nước (Mã NSNN)"
`NienDo`: Trích từ cột "Năm kế hoạch vốn (Năm KHV)" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`SoTien`: Trích từ cột "Số cơ quan kiểm soát, thanh toán duyệt thanh toán" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
### Yêu cầu xử lý:
- Không suy diễn hoặc bổ sung thông tin không có trong văn bản
- Tự động loại bỏ dấu chấm phân cách hàng nghìn trong số tiền