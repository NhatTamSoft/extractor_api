# System Message
Bạn là một AI trích xuất thông tin từ văn bản hành chính theo các quy tắc và định nghĩa trường được cung cấp. Đối với các trường có bảng ánh xạ, bạn PHẢI trả về một object với các trường id, ma, và ten. Bạn PHẢI trả về một JSON object hợp lệ.

# User Message
Trích xuất thông tin từ văn bản sau theo các định nghĩa và quy tắc trường.

## 1. TenLoaiTaiLieu
**Mô tả:** Tên loại tài liệu

**Quy tắc trích xuất:**
- **Vị trí:** Thường xuất hiện ở đầu văn bản
- **Từ khóa:** QUYẾT ĐỊNH, NGHỊ QUYẾT, HỢP ĐỒNG, BIÊN BẢN
- **Giá trị mặc định:** 
```json
{
  "id": "B5C9432D-2707-4659-AF56-2D63AC5E85B3",
  "mã": "QĐ",
  "tên": "Quyết định"
}
```
- **Bảng ánh xạ:**
```json
[
  {
    "id": "BDFEA00E-7B16-4255-BCFA-0128E508ABD7",
    "mã": "BC",
    "tên": "Báo cáo"
  },
  {
    "id": "2FE8CDD1-3CEF-4E62-B9CA-09A16D272D91",
    "mã": "CV",
    "tên": "Công văn"
  },
  {
    "id": "A6E4DAA0-6875-494D-B41A-11851EE0AC8D",
    "mã": "GGT",
    "tên": "Giấy giới thiệu"
  },
  {
    "id": "8D0C9303-A674-43D6-A8CE-13323B52D0E6",
    "mã": "QyĐ",
    "tên": "Quy định"
  },
  {
    "id": "9137AADF-92D5-4926-86CF-16127E833C91",
    "mã": "GNP",
    "tên": "Giấy nghỉ phép"
  },
  {
    "id": "6C0A6267-ED4E-4142-BD81-25D2CC71C63A",
    "mã": "TB",
    "tên": "Thông báo"
  },
  {
    "id": "D97AF75A-6EED-4995-BD2D-25EF2B61960F",
    "mã": "QC",
    "tên": "Quy chế"
  },
  {
    "id": "B5C9432D-2707-4659-AF56-2D63AC5E85B3",
    "mã": "QĐ",
    "tên": "Quyết định"
  },
  {
    "id": "7373AB32-EF2E-4E92-A9CD-31B9E3183EE8",
    "mã": "KH",
    "tên": "Kế hoạch"
  },
  {
    "id": "8443CDC1-CAD3-4A78-93CF-381E74AF1DD3",
    "mã": "DA",
    "tên": "Dự án"
  },
  {
    "id": "40C9A198-4102-4BB2-A974-4DA48795B6D6",
    "mã": "GM",
    "tên": "Giấy mời"
  },
  {
    "id": "E2F57662-2551-417E-85CC-737951547CE8",
    "mã": "GUQ",
    "tên": "Giấy ủy quyền"
  },
  {
    "id": "82C61CD1-A634-4C61-9CDA-81C5E1E436E7",
    "mã": "CT",
    "tên": "Chỉ thị"
  },
  {
    "id": "D612665A-F0E6-4F70-B64D-89B6DCB09E40",
    "mã": "BTT",
    "tên": "Bản thỏa thuận"
  },
  {
    "id": "819D56E3-DA2C-4069-863D-8BAF00B34B20",
    "mã": "BGN",
    "tên": "Bản ghi nhớ"
  },
  {
    "id": "A56C2E2E-573B-4E8D-8C21-8C145BC1395A",
    "mã": "TTr",
    "tên": "Tờ trình"
  },
  {
    "id": "9BF462C1-5303-407E-B0D2-8F6B9E6D1AF0",
    "mã": "TC",
    "tên": "Thông cáo"
  },
  {
    "id": "F2E1B209-BD3E-4EBF-8DCE-900A0AFD8BCE",
    "mã": "CTr",
    "tên": "Chương trình"
  },
  {
    "id": "6603EA6B-5D0F-4A2B-861A-96661DD89754",
    "mã": "TT",
    "tên": "Thông tư"
  },
  {
    "id": "98409C41-378F-4F5E-BEFB-A5B6165B85B1",
    "mã": "PC",
    "tên": "Phiếu chuyển"
  },
  {
    "id": "12A85372-4A91-49AB-8A9B-B66A8999FD60",
    "mã": "ĐA",
    "tên": "Đề án"
  },
  {
    "id": "2426DC13-FF84-4253-A677-BB481DDC470B",
    "mã": "CĐ",
    "tên": "Công điện"
  },
  {
    "id": "57955C8A-36DF-402E-9EFA-BE6643955E13",
    "mã": "NQ",
    "tên": "Nghị quyết"
  },
  {
    "id": "238B4EEC-E25D-48A3-A767-C0FBF43FA586",
    "mã": "HĐ",
    "tên": "Hợp đồng"
  },
  {
    "id": "4DE9032C-2D29-4F67-802B-C94768C0DD25",
    "mã": "PA",
    "tên": "Phương án"
  },
  {
    "id": "948E34AE-8218-4FEA-9820-C9DF552C9765",
    "mã": "NĐ",
    "tên": "Nghị Định"
  },
  {
    "id": "18098372-C9B0-4D81-84D0-D744CECA7264",
    "mã": "PG",
    "tên": "Phiếu gửi"
  },
  {
    "id": "C230E772-4AC5-4639-8BEA-DAA3347196CA",
    "mã": "HD",
    "tên": "Hướng dẫn"
  },
  {
    "id": "ABFAA963-F282-4D4C-9C21-E0796457AC1E",
    "mã": "BB",
    "tên": "Biên bản"
  },
  {
    "id": "D5FD393B-0352-400C-A565-E714CB6C6881",
    "mã": "PB",
    "tên": "Phiếu báo"
  }
]
```

## 2. SoVanBan
**Mô tả:** Số của tài liệu

**Quy tắc trích xuất:**
- **Vị trí:** Thường xuất hiện sau 'Số:' ở đầu văn bản
- **Định dạng:** Số nguyên hoặc chuỗi ký tự
- **Ví dụ:** 123, 123/QĐ-UBND

## 3. KyHieuTaiLieu
**Mô tả:** Ký hiệu của tài liệu

**Quy tắc trích xuất:**
- **Vị trí:** Thường xuất hiện cùng với số văn bản
- **Định dạng:** Chuỗi ký tự
- **Ví dụ:** QĐ-UBND, NQ-HĐND

## 4. NgayThangNam
**Mô tả:** Ngày, tháng, năm tài liệu

**Quy tắc trích xuất:**
- **Vị trí:** Thường xuất hiện sau 'ngày' ở đầu văn bản
- **Định dạng:** DD/MM/YYYY
- **Ví dụ:** 01/01/2024, 31/12/2024

## 5. CoQuanBanHanh
**Mô tả:** Tên cơ quan, tổ chức, cá nhân ban hành tài liệu

**Quy tắc trích xuất:**
- **Vị trí:** Thường xuất hiện ở đầu văn bản
- **Từ khóa:** ỦY BAN NHÂN DÂN, BAN QUẢN LÝ, SỞ
- **Ví dụ:** ỦY BAN NHÂN DÂN TỈNH, BAN QUẢN LÝ DỰ ÁN

## 6. TrichYeu
**Mô tả:** Trích yếu nội dung

**Quy tắc trích xuất:**
- **Vị trí:** Thường xuất hiện sau loại văn bản
- **Từ khóa:** Về việc, V/v
- **Ví dụ:** Về việc phê duyệt dự án...

## 7. NgonNgu
**Mô tả:** Ngôn ngữ

**Quy tắc trích xuất:**
- **Giá trị mặc định:** 
```json
{
  "id": "92CD991B-B7DB-4AA6-B217-F345954B91C6",
  "mã": "01",
  "tên": "Tiếng việt"
}
```
- **Bảng ánh xạ:**
```json
[
  {
    "id": "56047950-B3D2-493C-804B-1641EA7C595C",
    "mã": "06",
    "tên": "Tiếng Trung Quốc"
  },
  {
    "id": "B1FC127B-2D8C-4E19-BB33-4479CE575C8B",
    "mã": "07",
    "tên": "Tiếng Hàn"
  },
  {
    "id": "669BAD24-7D7E-4129-99F4-8343BD9BB9DA",
    "mã": "04",
    "tên": "Tiếng Nga"
  },
  {
    "id": "01F423FA-09A9-4EED-BA72-991BF0374D2B",
    "mã": "03",
    "tên": "Tiếng Pháp"
  },
  {
    "id": "8908A353-3477-4380-B176-A143C3AD070F",
    "mã": "05",
    "tên": "Tiếng Nhật"
  },
  {
    "id": "6544D793-FBE9-4E90-95EE-E25A046D09F5",
    "mã": "02",
    "tên": "Tiếng anh"
  },
  {
    "id": "92CD991B-B7DB-4AA6-B217-F345954B91C6",
    "mã": "01",
    "tên": "Tiếng việt"
  }
]
```

## 8. KyHieuThongTin
**Mô tả:** Ký hiệu thông tin

**Quy tắc trích xuất:**
- **Vị trí:** Thường xuất hiện ở đầu văn bản
- **Từ khóa:** MẬT, KHẨN, THƯỜNG

## 9. TuKhoa
**Mô tả:** Từ khóa

**Quy tắc trích xuất:**
- **Vị trí:** Có thể xuất hiện ở bất kỳ vị trí nào
- **Loại:** Danh sách các từ khóa quan trọng
- **Ví dụ:** dự án, đầu tư, xây dựng

## 10. ButTich
**Mô tả:** Bút tích

**Quy tắc trích xuất:**
- **Vị trí:** Thường xuất hiện ở cuối văn bản
- **Từ khóa:** Có chữ ký số, Có chữ ký tay

QUAN TRỌNG: Đối với các trường có bảng ánh xạ (như TenLoaiTaiLieu, NgonNgu, ...), trả về một object với cấu trúc:
{
    "id": "GUID",
    "ma": "code",
    "ten": "name"
}

Ví dụ:
- Đối với TenLoaiTaiLieu: trả về {"id": "B5C9432D-2707-4659-AF56-2D63AC5E85B3", "ma": "QĐ", "ten": "Quyết định"}
- Đối với NgonNgu: trả về {"id": "92CD991B-B7DB-4AA6-B217-F345954B91C6", "ma": "01", "ten": "Tiếng việt"}

Đối với các trường khác, trả về giá trị dưới dạng chuỗi.

Chỉ trả về một JSON object với cấu trúc sau:
{
    "TenLoaiTaiLieu": object or null,
    "SoVanBan": string or null,
    "KyHieuTaiLieu": string or null,
    "NgayThangNam": string or null,  // Format: dd/MM/yyyy
    "CoQuanBanHanh": string or null,
    "TrichYeu": string or null,
    "NgonNgu": object,  // Must not be null, default to Vietnamese if not specified
    "KyHieuThongTin": string or null,
    "TuKhoa": string or null,
    "ButTich": string or null,
    "OCR": string  // The raw OCR text from the document
} 