import pytesseract
from PIL import Image
import os
import re

# Cấu hình đường dẫn đến tesseract executable (thay đổi nếu cần)
# Nếu bạn đã thêm tesseract vào biến môi trường PATH, bạn có thể bỏ qua dòng này.
# Ví dụ cho Windows: pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# Ví dụ cho macOS/Linux: pytesseract.pytesseract.tesseract_cmd = '/usr/local/bin/tesseract'

def image_to_text_pytesseract(image_path: str, remove_special_characters: bool = True, lang: str = 'vie') -> str:
    """
    Chuyển đổi hình ảnh (PNG, JPEG) thành văn bản bằng pytesseract.

    Args:
        image_path (str): Đường dẫn đến tệp hình ảnh đầu vào (ví dụ: 'anh_cua_toi.png').
        lang (str, optional): Ngôn ngữ nhận dạng. Mặc định là 'vie' (tiếng Việt).
                              Bạn có thể dùng 'eng' cho tiếng Anh, hoặc 'vie+eng' cho cả hai.
                              Đảm bảo bạn đã cài đặt gói ngôn ngữ tương ứng cho Tesseract.

    Returns:
        str: Văn bản được trích xuất từ hình ảnh. Trả về chuỗi rỗng nếu có lỗi.
    """
    if not os.path.exists(image_path):
        print(f"Lỗi: Tệp hình ảnh không tồn tại tại đường dẫn: {image_path}")
        return ""

    try:
        # Mở hình ảnh bằng Pillow
        img = Image.open(image_path)

        # Chuyển đổi hình ảnh sang văn bản bằng pytesseract
        # Sử dụng config để thêm các tùy chọn cho tesseract
        # --psm: Chế độ phân đoạn trang (Page Segmentation Mode)
        # 0 = Chỉ phát hiện hướng và kiểu chữ (OSD)
        # 1 = Phân đoạn trang tự động với OSD
        # 2 = Phân đoạn trang tự động, không có OSD hoặc OCR
        # 3 = Phân đoạn trang hoàn toàn tự động, không có OSD (Mặc định)
        # 4 = Giả định một cột văn bản có kích thước thay đổi
        # 5 = Giả định một khối văn bản thẳng đứng đồng nhất
        # 6 = Giả định một khối văn bản đồng nhất
        # 7 = Xử lý hình ảnh như một dòng văn bản đơn
        # 8 = Xử lý hình ảnh như một từ đơn
        # 9 = Xử lý hình ảnh như một từ đơn trong vòng tròn
        # 10 = Xử lý hình ảnh như một ký tự đơn
        # 11 = Văn bản thưa. Tìm càng nhiều văn bản càng tốt không theo thứ tự cụ thể
        # 12 = Văn bản thưa với OSD
        # 13 = Dòng thô. Xử lý hình ảnh như một dòng văn bản đơn
        text = pytesseract.image_to_string(img, lang=lang, config='--psm 1')
        if remove_special_characters == True:
            text = re.sub(r'[^\w\s]', '', text)
        return text.strip() # Loại bỏ khoảng trắng thừa ở đầu và cuối
    except pytesseract.TesseractNotFoundError:
        print("Lỗi: Tesseract OCR engine không được tìm thấy.")
        print("Vui lòng đảm bảo Tesseract đã được cài đặt và đường dẫn của nó được cấu hình đúng.")
        print("Hướng dẫn cài đặt Tesseract: https://tesseract-ocr.github.io/tessdoc/Installation.html")
        return ""
    except Exception as e:
        print(f"Đã xảy ra lỗi trong quá trình xử lý hình ảnh: {e}")
        return ""

def image_to_text_pytesseract_from_image(image: Image.Image, remove_special_characters: bool = True, lang: str = 'vie') -> str:
    """
    Chuyển đổi đối tượng hình ảnh PIL.Image.Image thành văn bản bằng pytesseract.

    Args:
        image (PIL.Image.Image): Đối tượng hình ảnh PIL.Image.Image đầu vào.
        remove_special_characters (bool, optional): Xóa ký tự đặc biệt hay không. Mặc định là True.
        lang (str, optional): Ngôn ngữ nhận dạng. Mặc định là 'vie' (tiếng Việt).
                              Bạn có thể dùng 'eng' cho tiếng Anh, hoặc 'vie+eng' cho cả hai.
                              Đảm bảo bạn đã cài đặt gói ngôn ngữ tương ứng cho Tesseract.

    Returns:
        str: Văn bản được trích xuất từ hình ảnh. Trả về chuỗi rỗng nếu có lỗi.
    """
    try:
        # Chuyển đổi hình ảnh sang văn bản bằng pytesseract
        text = pytesseract.image_to_string(image, lang=lang, config='--psm 1')
        if remove_special_characters == True:
            text = re.sub(r'[^\w\s]', '', text)
        return text.strip() # Loại bỏ khoảng trắng thừa ở đầu và cuối
    except pytesseract.TesseractNotFoundError:
        print("Lỗi: Tesseract OCR engine không được tìm thấy.")
        print("Vui lòng đảm bảo Tesseract đã được cài đặt và đường dẫn của nó được cấu hình đúng.")
        print("Hướng dẫn cài đặt Tesseract: https://tesseract-ocr.github.io/tessdoc/Installation.html")
        return ""
    except Exception as e:
        print(f"Đã xảy ra lỗi trong quá trình xử lý hình ảnh: {e}")
        return ""

# --- Ví dụ sử dụng hàm ---
if __name__ == "__main__":
    # Tạo một tệp hình ảnh giả để thử nghiệm (trong thực tế bạn sẽ dùng ảnh thật)
    # Để chạy ví dụ này, bạn cần có một tệp ảnh thực tế
    # Ví dụ: tạo một ảnh tên 'example_vietnamese.png' có chữ tiếng Việt
    # hoặc 'example_english.png' có chữ tiếng Anh.

    # Ví dụ 1: Nhận dạng tiếng Việt
    vietnamese_image_path = 'KHLCNT CBDT 1.jpg' # '80_Im80.jpeg'
    # Để kiểm tra, bạn có thể tạo một ảnh PNG/JPEG với nội dung tiếng Việt
    # Ví dụ: "Chào mừng bạn đến với Việt Nam!"
    # Nếu không có ảnh, hàm sẽ báo lỗi tệp không tồn tại.
    if os.path.exists(vietnamese_image_path):
        print(f"\n--- Đang xử lý ảnh tiếng Việt: {vietnamese_image_path} ---")
        vietnamese_text = image_to_text_pytesseract(vietnamese_image_path, True, lang='vie')
        # Loại bỏ tất cả ký tự đặc biệt bằng regex
        print("Văn bản trích xuất (Tiếng Việt):")
        print(vietnamese_text)
    else:
        print(f"\nLưu ý: Không tìm thấy tệp '{vietnamese_image_path}'. Vui lòng tạo tệp này để thử nghiệm.")
        print("Bạn có thể dùng công cụ chụp màn hình để tạo một ảnh chứa văn bản tiếng Việt.")
    # -----------------
    # Ví dụ 4: Xử lý tệp không tồn tại
    # non_existent_path = 'non_existent_image.png'
    # print(f"\n--- Đang xử lý tệp không tồn tại: {non_existent_path} ---")
    # error_text = image_to_text_pytesseract(non_existent_path)
    # print(f"Kết quả khi tệp không tồn tại: '{error_text}'")
