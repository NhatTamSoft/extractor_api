# Danh sách các trường thông tin cần trích xuất

## Hướng dẫn chung
**Quy tắc xử lý:**
- Trả về JSON object chứa các trường thông tin được định nghĩa bên dưới
- Đối với các trường có bảng ánh xạ, PHẢI trả về MÃ (không phải giá trị)
- Định dạng ngày tháng: DD/MM/YYYY
- Định dạng số: loại bỏ dấu phân cách hàng nghìn
- Nếu không tìm thấy thông tin, trả về null
- Không bao gồm bất kỳ giải thích hay văn bản nào khác trong kết quả

**Cấu trúc JSON trả về:**
```json
{
    "docId": "string or null",
    "arcDocCode": "string or null",
    "maintenance": "string or null",
    "typeName": "string or null",
    "codeNumber": "string or null",
    "codeNotation": "string or null",
    "issuedDate": "string or null",
    "organName": "string or null",
    "subject": "string or null",
    "language": "string or null",
    "numberOfPage": "string or null",
    "inforSign": "string or null",
    "keyword": "string or null",
    "mode": "string or null",
    "confidenceLevel": "string or null",
    "autograph": "string or null",
    "format": "string or null",
    "process": "string or null",
    "riskRecovery": "string or null",
    "riskRecoveryStatus": "string or null",
    "description": "string or null",
    "SignerTitle": "string or null",
    "SignerName": "string or null"
}
```

**Hướng dẫn về mã hóa:**
Đối với các trường có bảng ánh xạ, trả về mã tương ứng:
- Language: '01' cho 'Tiếng Việt', '02' cho 'Tiếng Anh'
- Maintenance: '01' cho 'Vĩnh viễn', '02' cho '70 năm'
- TypeName: '01' cho 'Nghị quyết', '02' cho 'Quyết định'
- Mode: '01' cho 'Công khai', '02' cho 'Sử dụng có điều kiện'
- ConfidenceLevel: '01' cho 'Gốc điện tử', '02' cho 'Số hóa'
- Format: '01' cho 'Tốt', '02' cho 'Bình thường'
- Process: '0' cho 'Không có quy trình xử lý đi kèm', '1' cho 'Có quy trình xử lý đi kèm'
- RiskRecovery: '0' cho 'Không', '1' cho 'Có'
- RiskRecoveryStatus: '01' cho 'Đã dự phòng', '02' cho 'Chưa dự phòng'

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
**Mô tả:** Thời hạn lưu trữ. Khi tìm thấy giá trị trong tài liệu, trả về mã tương ứng từ bảng ánh xạ.

**Quy tắc trích xuất:**
- **Vị trí:** Thường xuất hiện ở cuối văn bản
- **Từ khóa:** Lưu trữ, Thời hạn bảo quản
- **Bảng ánh xạ:** (Giá trị tìm thấy trong tài liệu -> Mã trả về)
  | Mã | Giá trị |
  |----|---------|
  | 01 | Vĩnh viễn |
  | 02 | 70 năm |
  | 03 | 50 năm |
  | 04 | 30 năm |
  | 05 | 20 năm |
  | 06 | 10 năm |
  | 07 | Khác |

## 4. typeName
**Mô tả:** Tên loại tài liệu. Khi tìm thấy giá trị trong tài liệu, trả về mã tương ứng từ bảng ánh xạ.

**Quy tắc trích xuất:**
- **Vị trí:** Thường xuất hiện ở đầu văn bản
- **Từ khóa:** QUYẾT ĐỊNH, NGHỊ QUYẾT, HỢP ĐỒNG, BIÊN BẢN
- **Bảng ánh xạ:** (Giá trị tìm thấy trong tài liệu -> Mã trả về)
  | Mã | Giá trị |
  |----|---------|
  | 01 | Nghị quyết |
  | 02 | Quyết định |
  | 03 | Hợp đồng |
  | 04 | Biên bản |

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
**Mô tả:** Ngôn ngữ của tài liệu. Khi tìm thấy giá trị trong tài liệu, trả về mã tương ứng từ bảng ánh xạ.

**Quy tắc trích xuất:**
- **Giá trị mặc định:** 01
- **Bảng ánh xạ:** (Giá trị tìm thấy trong tài liệu -> Mã trả về)
  | Mã | Giá trị |
  |----|---------|
  | 01 | Tiếng Việt |
  | 02 | Tiếng Anh |
  | 11 | Khác |

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
**Mô tả:** Chế độ sử dụng. Khi tìm thấy giá trị trong tài liệu, trả về mã tương ứng từ bảng ánh xạ.

**Quy tắc trích xuất:**
- **Vị trí:** Thường xuất hiện ở đầu văn bản
- **Bảng ánh xạ:** (Giá trị tìm thấy trong tài liệu -> Mã trả về)
  | Mã | Giá trị |
  |----|---------|
  | 01 | Công khai |
  | 02 | Sử dụng có điều kiện |
  | 03 | Mật |

## 15. confidenceLevel
**Mô tả:** Mức độ tin cậy. Khi tìm thấy giá trị trong tài liệu, trả về mã tương ứng từ bảng ánh xạ.

**Quy tắc trích xuất:**
- **Giá trị mặc định:** 02
- **Bảng ánh xạ:** (Giá trị tìm thấy trong tài liệu -> Mã trả về)
  | Mã | Giá trị |
  |----|---------|
  | 01 | Gốc điện tử |
  | 02 | Số hóa |
  | 03 | Hỗn hợp |

## 16. autograph
**Mô tả:** Bút tích

**Quy tắc trích xuất:**
- **Vị trí:** Thường xuất hiện ở cuối văn bản
- **Từ khóa:** Có chữ ký số, Có chữ ký tay

## 17. format
**Mô tả:** Tình trạng vật lý. Khi tìm thấy giá trị trong tài liệu, trả về mã tương ứng từ bảng ánh xạ.

**Quy tắc trích xuất:**
- **Giá trị mặc định:** 01
- **Bảng ánh xạ:** (Giá trị tìm thấy trong tài liệu -> Mã trả về)
  | Mã | Giá trị |
  |----|---------|
  | 01 | Tốt |
  | 02 | Bình thường |
  | 03 | Hỏng |

## 18. process
**Mô tả:** Quy trình xử lý. Khi tìm thấy giá trị trong tài liệu, trả về mã tương ứng từ bảng ánh xạ.

**Quy tắc trích xuất:**
- **Bảng ánh xạ:** (Giá trị tìm thấy trong tài liệu -> Mã trả về)
  | Mã | Giá trị |
  |----|---------|
  | 0 | Không có quy trình xử lý đi kèm |
  | 1 | Có quy trình xử lý đi kèm |

## 19. riskRecovery
**Mô tả:** Chế độ dự phòng. Khi tìm thấy giá trị trong tài liệu, trả về mã tương ứng từ bảng ánh xạ.

**Quy tắc trích xuất:**
- **Bảng ánh xạ:** (Giá trị tìm thấy trong tài liệu -> Mã trả về)
  | Mã | Giá trị |
  |----|---------|
  | 0 | Không |
  | 1 | Có |

## 20. riskRecoveryStatus
**Mô tả:** Tình trạng dự phòng. Khi tìm thấy giá trị trong tài liệu, trả về mã tương ứng từ bảng ánh xạ.

**Quy tắc trích xuất:**
- **Bảng ánh xạ:** (Giá trị tìm thấy trong tài liệu -> Mã trả về)
  | Mã | Giá trị |
  |----|---------|
  | 01 | Đã dự phòng |
  | 02 | Chưa dự phòng |

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
- **Từ khóa:** Tên người ký thường nằm dưới chữ ký tay, vị trí cuối cùng trên trang
- **Định dạng:** Chuỗi ký tự (họ tên đầy đủ)