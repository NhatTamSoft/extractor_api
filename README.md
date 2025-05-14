# NTSOFT API Document AI (extractor_api)

## Giới thiệu

NTSOFT API Document AI (tên repository: `extractor_api`) là một giải pháp mạnh mẽ được xây dựng bằng FastAPI, chuyên dùng để xử lý và chuyển đổi văn bản từ tài liệu giấy (hoặc hình ảnh/PDF của tài liệu giấy) thành các tài liệu thông minh, có cấu trúc và dễ dàng khai thác. API này giúp tự động hóa quy trình nhập liệu, trích xuất thông tin quan trọng và số hóa tài liệu một cách hiệu quả.

Dự án này được phát triển nhằm mục đích:

* Giảm thiểu thời gian và công sức xử lý tài liệu thủ công.
* Nâng cao độ chính xác trong việc trích xuất dữ liệu.
* Tạo ra các tài liệu số có khả năng tìm kiếm, phân tích và tích hợp vào các hệ thống khác.
* Cung cấp một giải pháp linh hoạt và dễ dàng mở rộng cho các nhu vực xử lý tài liệu đa dạng.

## Công nghệ sử dụng

* **Framework:** FastAPI
* **Ngôn ngữ:** Python
* **Cơ sở dữ liệu:** MS SQL SERVER
* **Xử lý ảnh & OCR:** Google Cloud Vision
* **Xử lý ngôn ngữ tự nhiên (NLP):** Google Gemini

## Tính năng chính

* **Nhận dạng ký tự quang học (OCR):** Chuyển đổi hình ảnh tài liệu (JPG, PNG, TIFF, PDF...) thành văn bản có thể chỉnh sửa.
* **Trích xuất thông tin thông minh:**
    * Nhận diện và trích xuất các thực thể quan trọng (ví dụ: tên, ngày tháng, địa chỉ, số tiền, mã số thuế, số hợp đồng,...).
    * Trích xuất dữ liệu dạng bảng.
    * Phân loại tài liệu (ví dụ: hóa đơn, hợp đồng, CV,...). (*Nếu có*)
* **Tiền xử lý ảnh:** Tự động xoay, cắt, khử nhiễu ảnh để cải thiện chất lượng OCR. (*Nếu có*)
* **Định dạng đầu ra linh hoạt:** Trả về dữ liệu dưới dạng JSON, text, hoặc các định dạng có cấu trúc khác.
* **API endpoints dễ sử dụng:** Cung cấp các API rõ ràng, tài liệu hóa tốt (Swagger UI/ReDoc tự động bởi FastAPI).

## Cài đặt và Chạy dự án

**Yêu cầu:**

* Python 3.11+
* PIP (Python package installer)
* (Các yêu cầu khác như Tesseract OCR engine nếu bạn dùng,...)

**Các bước cài đặt:**

1.  **Clone repository:**
    ```bash
    git clone [https://github.com/lebatung/extractor_api.git](https://github.com/lebatung/extractor_api.git)
    cd extractor_api
    ```

2.  **Tạo và kích hoạt môi trường ảo (khuyến nghị):**
    ```bash
    python -m venv venv
    # Trên Windows
    venv\Scripts\activate
    # Trên macOS/Linux
    source venv/bin/activate
    ```

3.  **Cài đặt các thư viện cần thiết:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Cấu hình (nếu cần):**
    * Nếu có file `.env.example`, tạo file `.env` và cập nhật các biến môi trường.
    * Kiểm tra cấu hình cơ sở dữ liệu trong code nếu cần thiết (hiện tại có vẻ đang dùng `app.db` là SQLite).

5.  **Chạy API server:**
    ```bash
    uvicorn main:app --reload
    ```
    *(Giả sử đối tượng FastAPI trong `main.py` của bạn tên là `app`)*

Sau khi chạy, API sẽ có sẵn tại `http://127.0.0.1:8000` và tài liệu API tự động (Swagger UI) tại `http://127.0.0.1:8000/docs`.

## Cấu trúc thư mục
