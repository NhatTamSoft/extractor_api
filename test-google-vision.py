from google.cloud import vision
import os
import io
from pdf2image import convert_from_path
import tempfile

def read_text_from_images_by_google_vision(pdf_path):
    """
    Đọc văn bản từ file PDF sử dụng Google Cloud Vision API
    
    Args:
        pdf_path (str): Đường dẫn đến file PDF cần xử lý
        
    Returns:
        str: Văn bản được trích xuất từ PDF
    """
    # Khởi tạo client Vision API
    client = vision.ImageAnnotatorClient()
    
    # Chuyển đổi PDF thành các ảnh
    images = convert_from_path(pdf_path)
    
    full_text = []
    
    # Xử lý từng trang trong PDF
    for i, image in enumerate(images):
        # Lưu ảnh tạm thời
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            image.save(temp_file.name, 'JPEG')
            
            # Đọc file ảnh
            with io.open(temp_file.name, 'rb') as image_file:
                content = image_file.read()
            
            # Tạo request cho Vision API
            image = vision.Image(content=content)
            
            # Thực hiện nhận dạng văn bản
            response = client.document_text_detection(image=image)
            
            if response.error.message:
                raise Exception(
                    '{}\nFor more info on error messages, check: '
                    'https://cloud.google.com/apis/design/errors'.format(
                        response.error.message))
            
            # Lấy kết quả văn bản
            if response.full_text_annotation:
                full_text.append(response.full_text_annotation.text)
            
            # Xóa file tạm
            os.unlink(temp_file.name)
    
    # Kết hợp tất cả văn bản từ các trang
    return '\n'.join(full_text)

# Ví dụ sử dụng
if __name__ == "__main__":
    # Thay đổi đường dẫn file PDF của bạn
    pdf_path = "path/to/your/document.pdf"
    try:
        text = read_text_from_images_by_google_vision(pdf_path)
        print("Văn bản được trích xuất:")
        print(text)
    except Exception as e:
        print(f"Có lỗi xảy ra: {str(e)}")
