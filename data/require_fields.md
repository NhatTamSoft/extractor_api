# Danh sách các trường thông tin cần trích xuất

## 1. docId
**Mô tả:** Mã định danh tài liệu

**Quy tắc trích xuất:**
- **Vị trí:** Thường xuất hiện ở đầu văn bản
- **Từ khóa:** Mã số, Mã định danh, Số hiệu
- **Định dạng:** Chuỗi ký tự
- **Ví dụ:** VB-2024-001, HD-2024-123

## 2. arcDocCode
**Mô tả:** Mã lưu trữ tài liệu (gồm: mã cơ quan lưu trữ + mã hồ sơ + số thứ tự tài liệu trong hồ sơ)

**Quy tắc trích xuất:**
- **Vị trí:** Thường xuất hiện ở đầu văn bản
- **Định dạng:** [mã cơ quan]-[mã hồ sơ]-[số thứ tự]
- **Ví dụ:** UBND-2024-001, BQL-2024-123

## 3. maintenance
**Mô tả:** Thời hạn lưu trữ

**Quy tắc trích xuất:**
- **Vị trí:** Thường xuất hiện ở cuối văn bản
- **Từ khóa:** Lưu trữ, Thời hạn bảo quản
- **Bảng ánh xạ:**
| ID                                   | Mã | Giá trị   |
| ------------------------------------ | -- | --------- |
| 6D7A48A2-C35B-41B7-A639-DA2DB6319803 | 01 | Vĩnh viễn |
| 553095C0-B820-4094-BF32-EEACDE2320A5 | 02 | 70 năm    |
| 413032D3-4267-4CC5-9F0B-67E51D1A6DBE | 03 | 50 năm    |
| 1C6F3562-84AD-4A21-B9C4-7E8B7625E3A6 | 04 | 30 năm    |
| 3178FF8B-29BF-476D-8EBA-213EE9DB4146 | 04 | 20 năm    |
| CC4894B4-DFCA-41EB-A2E4-03AF80FE4418 | 04 | 10 năm    |
| D5C2C3E2-820B-40C9-98B7-36B68DA02E27 | 04 | khác      |

## 4. typeName
**Mô tả:** Tên loại tài liệu

**Quy tắc trích xuất:**
- **Vị trí:** Thường xuất hiện ở đầu văn bản
- **Từ khóa:** QUYẾT ĐỊNH, NGHỊ QUYẾT, HỢP ĐỒNG, BIÊN BẢN
- **Giá trị mặc định:** B5C9432D-2707-4659-AF56-2D63AC5E85B3
- **Bảng ánh xạ:**
| ID                                   | Mã  | Giá trị         |
| ------------------------------------ | --- | --------------- |
| BDFEA00E-7B16-4255-BCFA-0128E508ABD7 | BC  | Báo cáo         |
| 2FE8CDD1-3CEF-4E62-B9CA-09A16D272D91 | CV  | Công văn        |
| A6E4DAA0-6875-494D-B41A-11851EE0AC8D | GGT | Giấy giới thiệu |
| 8D0C9303-A674-43D6-A8CE-13323B52D0E6 | QyĐ | Quy định        |
| 9137AADF-92D5-4926-86CF-16127E833C91 | GNP | Giấy nghỉ phép  |
| 6C0A6267-ED4E-4142-BD81-25D2CC71C63A | TB  | Thông báo       |
| D97AF75A-6EED-4995-BD2D-25EF2B61960F | QC  | Quy chế         |
| B5C9432D-2707-4659-AF56-2D63AC5E85B3 | QĐ  | Quyết định      |
| 7373AB32-EF2E-4E92-A9CD-31B9E3183EE8 | KH  | Kế hoạch        |
| 8443CDC1-CAD3-4A78-93CF-381E74AF1DD3 | DA  | Dự án           |
| 40C9A198-4102-4BB2-A974-4DA48795B6D6 | GM  | Giấy mời        |
| E2F57662-2551-417E-85CC-737951547CE8 | GUQ | Giấy ủy quyền   |
| 82C61CD1-A634-4C61-9CDA-81C5E1E436E7 | CT  | Chỉ thị         |
| D612665A-F0E6-4F70-B64D-89B6DCB09E40 | BTT | Bản thỏa thuận  |
| 819D56E3-DA2C-4069-863D-8BAF00B34B20 | BGN | Bản ghi nhớ     |
| A56C2E2E-573B-4E8D-8C21-8C145BC1395A | TTr | Tờ trình        |
| 9BF462C1-5303-407E-B0D2-8F6B9E6D1AF0 | TC  | Thông cáo       |
| F2E1B209-BD3E-4EBF-8DCE-900A0AFD8BCE | CTr | Chương trình    |
| 6603EA6B-5D0F-4A2B-861A-96661DD89754 | TT  | Thông tư        |
| 98409C41-378F-4F5E-BEFB-A5B6165B85B1 | PC  | Phiếu chuyển    |
| 12A85372-4A91-49AB-8A9B-B66A8999FD60 | ĐA  | Đề án           |
| 2426DC13-FF84-4253-A677-BB481DDC470B | CĐ  | Công điện       |
| 57955C8A-36DF-402E-9EFA-BE6643955E13 | NQ  | Nghị quyết      |
| 238B4EEC-E25D-48A3-A767-C0FBF43FA586 | HĐ  | Hợp đồng        |
| 4DE9032C-2D29-4F67-802B-C94768C0DD25 | PA  | Phương án       |
| 948E34AE-8218-4FEA-9820-C9DF552C9765 | NĐ  | Nghị Định       |
| 18098372-C9B0-4D81-84D0-D744CECA7264 | PG  | Phiếu gửi       |
| C230E772-4AC5-4639-8BEA-DAA3347196CA | HD  | Hướng dẫn       |
| ABFAA963-F282-4D4C-9C21-E0796457AC1E | BB  | Biên bản        |
| D5FD393B-0352-400C-A565-E714CB6C6881 | PB  | Phiếu báo       |

## 5. codeNumber
**Mô tả:** Số của tài liệu

**Quy tắc trích xuất:**
- **Vị trí:** Thường xuất hiện sau 'Số:' ở đầu văn bản
- **Định dạng:** Số nguyên hoặc chuỗi ký tự
- **Ví dụ:** 123, 123/QĐ-UBND

## 6. codeNotation
**Mô tả:** Ký hiệu của tài liệu

**Quy tắc trích xuất:**
- **Vị trí:** Thường xuất hiện cùng với số văn bản
- **Định dạng:** Chuỗi ký tự
- **Ví dụ:** QĐ-UBND, NQ-HĐND

## 7. issuedDate
**Mô tả:** Ngày, tháng, năm tài liệu

**Quy tắc trích xuất:**
- **Vị trí:** Thường xuất hiện sau 'ngày' ở đầu văn bản
- **Định dạng:** DD/MM/YYYY
- **Ví dụ:** 01/01/2024, 31/12/2024

## 8. organName
**Mô tả:** Tên cơ quan, tổ chức, cá nhân ban hành tài liệu

**Quy tắc trích xuất:**
- **Vị trí:** Thường xuất hiện ở đầu văn bản
- **Từ khóa:** ỦY BAN NHÂN DÂN, BAN QUẢN LÝ, SỞ
- **Ví dụ:** ỦY BAN NHÂN DÂN TỈNH, BAN QUẢN LÝ DỰ ÁN

## 9. subject
**Mô tả:** Trích yếu nội dung

**Quy tắc trích xuất:**
- **Vị trí:** Thường xuất hiện sau loại văn bản
- **Từ khóa:** Về việc, V/v
- **Ví dụ:** Về việc phê duyệt dự án...

## 10. language
**Mô tả:** Ngôn ngữ

**Quy tắc trích xuất:**
- **Giá trị mặc định:** 92CD991B-B7DB-4AA6-B217-F345954B91C6
- **Bảng ánh xạ:**
| ID                                   | Mã | Giá trị          |
| ------------------------------------ | -- | ---------------- |
| 56047950-B3D2-493C-804B-1641EA7C595C | 06 | Tiếng Trung Quốc |
| B1FC127B-2D8C-4E19-BB33-4479CE575C8B | 07 | Tiếng Hàn        |
| 669BAD24-7D7E-4129-99F4-8343BD9BB9DA | 04 | Tiếng Nga        |
| 01F423FA-09A9-4EED-BA72-991BF0374D2B | 03 | Tiếng Pháp       |
| 8908A353-3477-4380-B176-A143C3AD070F | 05 | Tiếng Nhật       |
| 6544D793-FBE9-4E90-95EE-E25A046D09F5 | 02 | Tiếng anh        |
| 92CD991B-B7DB-4AA6-B217-F345954B91C6 | 01 | Tiếng việt       |

## 11. numberOfPage
**Mô tả:** Số lượng trang

**Quy tắc trích xuất:**
- **Vị trí:** Thường xuất hiện ở cuối mỗi trang
- **Định dạng:** Số nguyên
- **Ví dụ:** 5, 10

## 12. inforSign
**Mô tả:** Ký hiệu thông tin

**Quy tắc trích xuất:**
- **Vị trí:** Thường xuất hiện ở đầu văn bản
- **Từ khóa:** MẬT, KHẨN, THƯỜNG

## 13. keyword
**Mô tả:** Từ khóa

**Quy tắc trích xuất:**
- **Vị trí:** Có thể xuất hiện ở bất kỳ vị trí nào
- **Loại:** Danh sách các từ khóa quan trọng
- **Ví dụ:** dự án, đầu tư, xây dựng

## 14. mode
**Mô tả:** Chế độ sử dụng

**Quy tắc trích xuất:**
- **Vị trí:** Thường xuất hiện ở đầu văn bản
- **Bảng ánh xạ:**
| ID                                   | Mã | Giá trị       |
| ------------------------------------ | -- | ------------- |
| 7AF46CF8-E1D9-4294-92D8-18D3D7C0D2BA | 01 | Hạn chế       |
| F8808DBE-C5DC-4937-ADC1-714FEAB27AD9 | 02 | Không hạn chế |

## 15. confidenceLevel
**Mô tả:** Mức độ tin cậy

**Quy tắc trích xuất:**
- **Giá trị mặc định:** 75708AFC-FF3D-438C-B740-04EC014ECF1E
- **Bảng ánh xạ:**
| ID                                   | Mã | Giá trị   |
| ------------------------------------ | -- | --------- |
| 75708AFC-FF3D-438C-B740-04EC014ECF1E | 02 | Bản sao   |
| 4464F593-7189-4784-A7CB-B5D23095D0FC | 01 | Bản chính |

## 16. autograph
**Mô tả:** Bút tích

**Quy tắc trích xuất:**
- **Vị trí:** Thường xuất hiện ở cuối văn bản
- **Từ khóa:** Có chữ ký số, Có chữ ký tay

## 17. format
**Mô tả:** Tình trạng vật lý

**Quy tắc trích xuất:**
- **Giá trị mặc định:** 4FC4186D-393F-4F6A-9DDF-D9F964071430
- **Bảng ánh xạ:**
| ID                                   | Mã | Giá trị                                                                     |
| ------------------------------------ | -- | --------------------------------------------------------------------------- |
| 17FE907A-DA89-4F33-B11A-7860B5C50082 | 05 | Tài liệu bị ố vàng                                                          |
| 3235CF46-02E5-4D7C-82AE-794D4F6F2E10 | 03 | Tài liệu bị mục, dính bết nhẹ                                               |
| D58C7F54-223C-40B7-B61F-88FF34FAFD46 | 04 | Tài liệu bị đóng thành cục, dính bết nặng chỉ đụng nhẹ là có thể bị nát vụn |
| F486C997-C708-46C7-B297-933B2969796E | 06 | Bị rách                                                                     |
| E4860BAF-FEA2-4510-94BF-945051426F72 | 02 | Tài liệu bị mốc nhẹ                                                         |
| 4FC4186D-393F-4F6A-9DDF-D9F964071430 | 01 | Bình thường                                                                 |

## 18. process
**Mô tả:** Quy trình xử lý

**Quy tắc trích xuất:**
- **Giá trị mặc định:** A8670461-25BB-404C-9E2B-C3D871E36605
- **Bảng ánh xạ:**
| ID                                   | Mã | Giá trị |
| ------------------------------------ | -- | ------- |
| 99148241-C26C-4971-A18C-385AF2556606 | 01 | Có      |
| A8670461-25BB-404C-9E2B-C3D871E36605 | 02 | Không   |

## 19. riskRecovery
**Mô tả:** Chế độ dự phòng

**Quy tắc trích xuất:**
- **Giá trị mặc định:** 3D207EDF-3901-48B8-98C8-39ED9E75D0BF
- **Bảng ánh xạ:**
| ID                                   | Mã | Giá trị |
| ------------------------------------ | -- | ------- |
| 61E501D0-D32B-48D6-AECA-45D829574B9D | 01 | Có      |
| 3D207EDF-3901-48B8-98C8-39ED9E75D0BF | 02 | Không   |

## 20. riskRecoveryStatus
**Mô tả:** Tình trạng dự phòng

**Quy tắc trích xuất:**
- **Giá trị mặc định:** 48BBB1D1-FB36-4CC6-9750-D16CEBBDF4FB
- **Bảng ánh xạ:**
| ID                                   | Mã | Giá trị       |
| ------------------------------------ | -- | ------------- |
| 63A03F14-091C-4A1B-A1B6-9E5CB10B5103 | 01 | Đã dự phòng   |
| 48BBB1D1-FB36-4CC6-9750-D16CEBBDF4FB | 02 | Chưa dự phòng |

## 21. description
**Mô tả:** Ghi chú

**Quy tắc trích xuất:**
- **Vị trí:** Thường xuất hiện ở cuối văn bản
- **Loại:** Văn bản tự do 

## 22. SignerTitle
**Mô tả:** Chức danh người ký văn bản

**Quy tắc trích xuất:**
- **Vị trí:** Thường xuất hiện ở cuối văn bản, ngay phía trên tên người ký
- **Từ khóa:** CHỦ TỊCH, PHÓ CHỦ TỊCH, KT. CHỦ TỊCH, GIÁM ĐỐC, PHÓ GIÁM ĐỐC
- **Định dạng:** Chuỗi ký tự
- **Ví dụ:** "CHỦ TỊCH", "PHÓ CHỦ TỊCH", "KT. CHỦ TỊCH – PHÓ CHỦ TỊCH"

## 23. SignerName
**Mô tả:** Tên người ký văn bản

**Quy tắc trích xuất:**
- **Vị trí:** Thường xuất hiện ở cuối văn bản, ngay dưới dòng chức danh
- **Từ khóa:** Tên người ký thường nằm dưới chữ ký tay
- **Định dạng:** Chuỗi ký tự (họ tên đầy đủ)
- **Ví dụ:** "Nguyễn Văn A", "Trần Thị B" 