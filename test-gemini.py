# @title Thiết lập và Chạy Ứng dụng Trích xuất Thông tin Hình ảnh
# Bước 1: Cài đặt các thư viện cần thiết
import google.generativeai as genai
import PIL.Image
import io
import os
import sys
import fitz  # PyMuPDF
from dotenv import load_dotenv
import PIL
from PIL import Image
from io import BytesIO
import base64
from app.services.DungChung import pdf_to_images

load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

genai.configure(api_key=GOOGLE_API_KEY)

# Bước 3: Hàm xử lý và gọi Gemini API
def extract_image_information(prompt_text, image_parts):
    """
    Gửi prompt và danh sách các phần hình ảnh đến Gemini API và trả về phản hồi.

    Args:
        prompt_text (str): Câu lệnh prompt cho Gemini.
        image_parts (list): Danh sách các đối tượng PIL.Image.

    Returns:
        str: Phản hồi từ Gemini API hoặc thông báo lỗi.
    """
    if not image_parts:
        return "Không có hình ảnh nào được cung cấp để xử lý."
    if not GOOGLE_API_KEY: # Kiểm tra lại API Key trước khi gọi model
        return "Không thể gọi Gemini API do thiếu API Key."
    model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')

    # Chuẩn bị nội dung cho API
    # Nội dung bao gồm prompt và tất cả các hình ảnh
    content_for_api = [prompt_text] + image_parts

    try:
        print("Đang gửi yêu cầu đến Gemini API...")
        response = model.generate_content(content_for_api)
        # Kiểm tra xem có lỗi trong phản hồi không
        if not response.parts: # Nếu không có parts, có thể có lỗi hoặc prompt bị chặn
             if response.prompt_feedback and response.prompt_feedback.block_reason:
                 return f"Yêu cầu bị chặn. Lý do: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason}"
             else: # Trường hợp lỗi không xác định rõ
                 return "Không nhận được phản hồi hợp lệ từ Gemini. Vui lòng thử lại hoặc kiểm tra prompt."

        return response.text
    except Exception as e:
        return f"Đã xảy ra lỗi khi gọi Gemini API: {e}"

def process_file(file_path):
    """
    Xử lý file PDF hoặc hình ảnh và trả về danh sách các đối tượng PIL.Image
    """
    image_pil_objects = []
    temp_image_paths = []

    try:
        if file_path.lower().endswith('.pdf'):
            print(f"Đang chuyển đổi PDF: {file_path}...")
            # Sử dụng hàm pdf_to_images để chuyển đổi PDF
            pdf_images = pdf_to_images(file_path, zoom=2.5)
            
            if not pdf_images:
                print(f"Không thể chuyển đổi PDF: {file_path}")
                return [], []

            print(f"Đã chuyển đổi thành công {len(pdf_images)} trang")
            for i, pdf_image in enumerate(pdf_images):
                image_pil_objects.append(pdf_image)
                temp_path = f"temp_pdf_page_{i}_{os.path.basename(file_path)}.png"
                pdf_image.save(temp_path, format='PNG', quality=95)  # Lưu dạng PNG để giữ chất lượng
                temp_image_paths.append(temp_path)
                print(f"  Đã chuyển đổi trang {i+1} của PDF {file_path}.")
        elif file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            print(f"Đang xử lý hình ảnh: {file_path}...")
            img = PIL.Image.open(file_path)
            image_pil_objects.append(img)
            temp_path = f"temp_{os.path.basename(file_path)}"
            img.save(temp_path, quality=95)
            temp_image_paths.append(temp_path)
        else:
            print(f"Bỏ qua tệp không được hỗ trợ: {file_path}")
    except Exception as e:
        print(f"Lỗi khi xử lý tệp {file_path}: {str(e)}")
        import traceback
        print(traceback.format_exc())

    return image_pil_objects, temp_image_paths

# Bước 4: Giao diện tải file lên và xử lý
def main():
    """
    Hàm chính để điều khiển luồng tải file, xử lý và hiển thị kết quả.
    """
    if not GOOGLE_API_KEY: # Kiểm tra API Key ở đầu hàm main
        print("Vui lòng cung cấp API Key ở Bước 2 và chạy lại.")
        return

    if len(sys.argv) < 2:
        print("Vui lòng cung cấp đường dẫn đến file PDF hoặc hình ảnh.")
        print("Cách sử dụng: python test-gemini.py <đường_dẫn_file>")
        return

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"Không tìm thấy file: {file_path}")
        return

    image_pil_objects, temp_image_paths = process_file(file_path)

    if not image_pil_objects:
        print("\nKhông có hình ảnh nào hợp lệ để gửi đến Gemini.")
        for path in temp_image_paths:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    print(f"Lỗi khi dọn dẹp tệp tạm {path}: {e}")
        return
    # Câu prompt cố định (dài, theo yêu cầu của người dùng)
    user_prompt = """
Bạn là AI có khả năng đọc tài liệu dạng ảnh hoặc pdf. Hãy đọc nội dung người dùng gửi
** Danh sách Khoản mục chi phí
------------------------------------------------------
| Mã  |Tên khoản mục chi phí                         |
|-----|----------------------------------------------|
|`CP1`|Chi phí bồi thường, hỗ trợ, tái định cư       |
|`CP2`|Chi phí xây dựng                              |
|`CP3`|Chi phí thiết bị                              |
|`CP4`|Chi phí quản lý dự án                         |
|`CP5`|Chi phí tư vấn đầu tư xây dựng                |
|`CP6`|Chi phí khác                                  |
|`CP7`|Chi phí dự phòng                              |

** Danh sách Loại công trình
------------------------------------------------------
|  Mã |Loại công trình                               |
|-----|----------------------------------------------|
| `1` |Công trình dân dụng                           |
| `2` |Công trình công nghiệp                        |
| `3` |Công trình giao thông                         |
| `4` |Công trình nông nghiệp và phát triển nông thôn|
| `5` |Công trình hạ tầng kỹ thuật                   |

Chức năng `Quyết định phê duyệt dự toán giai đoạn chuẩn bị đầu tư`
### Văn bản để nhận dạng thông tin là: "Quyết định phê duyệt dự toán giai đoạn chuẩn bị đầu tư, quyết định điều chỉnh dự toán giai đoạn chuẩn bị đầu tư"
### Thông tin chung của văn bản, tên đối tượng (object) "ThongTinChung":
`KyHieu`: "QDPDDT_CBDT"
`SoVanBan`: Trích số hiệu văn bản ghi ở đầu văn bản, sau chữ "Số:"
`SoVanBanCanCu`: Trích "số hiệu văn bản" phê duyệt chủ trương đầu tư hoặc phê duyệt điều chỉnh chủ trương đầu tư, tại dòng "Căn cứ Quyết định số..." có chứa cụm từ "phê duyệt chủ trương đầu tư..."
`NgayKyCanCu`: Trích "ngày...tháng...năm ..." phê duyệt chủ trương đầu tư hoặc phê duyệt điều chỉnh chủ trương đầu tư, tại dòng "Căn cứ Quyết định số..." có chứa cụm từ "phê duyệt chủ trương đầu tư..." định dạng (dd/MM/yyyy)
`NgayKy`: Trích thông tin ngày ký ở đầu văn bản, sau dòng địa danh "..., ngày ...", định dạng (dd/MM/yyyy)
`NguoiKy`: Trích tên người ký văn bản ở phần cuối văn bản, ngay dưới dòng "KT. CHỦ TỊCH" hoặc "CHỦ TỊCH".
`ChucDanhNguoiKy`: Trích phần ghi rõ chức vụ người ký văn bản (VD: "CHỦ TỊCH", "PHÓ CHỦ TỊCH", "KT. CHỦ TỊCH – PHÓ CHỦ TỊCH").
`CoQuanBanHanh`: Trích xuất chính xác tên cơ quan ban hành văn bản theo đúng quy định tại Nghị định 30/2020/NĐ-CP về công tác văn thư. Nếu dòng đầu là tên cơ quan chủ quản và dòng thứ hai là đơn vị trực thuộc thì chỉ lấy dòng thứ hai làm cơ quan ban hành.
`TrichYeu`: Trích nguyên văn phần tiêu đề nằm ngay sau chữ "QUYẾT ĐỊNH", thường bắt đầu bằng "Về việc..." hoặc "V/v..." hoặc "Về việc phê duyệt Báo cáo..."
`TenNguonVon`: Trích tên nguồn vốn sau cụm từ "nguồn vốn:", nếu không có để ""
`GiaTri`: Trích thông tin số tiền ngay sau cụm từ "giá trị dự toán", thường bắt đầu bằng "Giá trị báo cáo kinh tế kỹ thật..." (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`DieuChinh`: Gán `1` nếu "trích yếu văn bản" có chứa nội dung "điều chỉnh...", ngược lại gán `0`
### Bảng số liệu dự toán, mỗi dòng là một bản ghi với các cột sau, tên đối tượng (object): "BangDuLieu":
`TenKMCP`: Tên của khoản mục chi phí (không chứa ký tự đặc biệt)
`GiaTriDuToanKMCP`: Giá trị thành tiền hoặc giá trị cột **"Sau thuế"**, không lấy cột "Trước thuế" (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`GiaTriDuToanKMCPTang`: Nếu `DieuChinh` bằng `1` thì trích "Giá trị dự toán tăng" ngược lại gán `0` (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
`GiaTriDuToanKMCPGiam`: Nếu `DieuChinh` bằng `1` thì trích "Giá trị dự toán giảm" ngược lại gán `0` (định dạng dưới dạng số nguyên, không chứa dấu chấm ngăn cách hàng nghìn)
### Yêu cầu xử lý:
🚫 **Không lấy giá trị trong cột "Trước thuế"**
✅ Chỉ lấy giá trị tại đúng cột có tiêu đề "Sau thuế"
- BangDuLieu tôi muốn lấy tất cả chi tiết, không bỏ bất kỳ dòng nào
- Không suy diễn hoặc bổ sung thông tin không có trong văn bản
- Giữ nguyên định dạng và nội dung khi trích xuất, trừ khi cần làm rõ để dễ hiểu hơn
- Trong BangDuLieu nếu các cột giá trị "" thì bắt buộc gán là "0"
- Giữ nguyên đúng tên khoản mục như trên bảng (bao gồm cả chữ in hoa, dấu câu nếu có)
- Giữ nguyên định dạng STT dạng lồng nhau (VD: `1.1`, `3.1`, `4.1`)
- Bỏ qua phần tiêu đề bảng, chỉ lấy dữ liệu từ phần nội dung bảng
- Tự động loại bỏ dấu chấm phân cách hàng nghìn trong số tiền
- Hãy trích xuất chính xác chuỗi ký tự trước chữ 'đồng', bao gồm cả dấu chấm như trong bản gốc.
🎯 Yêu cầu: Trích **chính xác tên cơ quan trực tiếp ban hành văn bản** theo các quy tắc sau:
* Nếu văn bản có:
  * Dòng 1 là cơ quan chủ quản (VD: "UBND TỈNH...")
  * Dòng 2 là tên địa phương (VD: "HUYỆN...")
  * Dòng 3 là đơn vị trực thuộc (VD: "BAN QLDA...")
    → **Chỉ lấy dòng 3** làm cơ quan ban hành.
* Nếu chỉ có 1 dòng hoặc 2 dòng mà không có đơn vị trực thuộc → có thể ghép lại (VD: "ỦY BAN NHÂN DÂN HUYỆN ...").
✅ Không bao giờ lấy cơ quan chủ quản nếu có đơn vị cấp dưới trực tiếp ký văn bản.

🎯 Yêu cầu: Trích **SoVanBan**, **SoVanBanCanCu** hoặc **TrichYeu** đúng chính xác, giữ nguyên ký hiệu đầy đủ, bao gồm dấu tiếng Việt. Đặc biệt:
🔒 Bắt buộc giữ nguyên các chữ viết tắt có dấu trong số hiệu văn bản, gồm:
- **"QĐ"** - viết tắt của "Quyết định"
- **"HĐND"** - viết tắt của "Hội đồng nhân dân"
- **"HĐ"** - viết tắt của "Hợp đồng" hoặc "Hội đồng"
- **"TĐ"** - viết tắt của "Thẩm định"
- **"HĐTĐ"** - viết tắt của "Hội đồng thẩm định"
- Các từ viết tắt khác có chữ **"Đ"**, **không được chuyển thành "D"**

🎯 Yêu cầu: Kết quả xuất ra dạng JSON duy nhất có dạng
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
    """

    # Gọi Gemini API
    gemini_response = extract_image_information(user_prompt, image_pil_objects)

    print("\n--- Phản hồi từ Gemini ---")
    print(gemini_response)

    # Xóa các file ảnh tạm đã tạo
    print("\nĐang dọn dẹp các tệp tạm...")
    for path in temp_image_paths:
        if os.path.exists(path):
            try:
                os.remove(path)
                print(f"  Đã xóa: {path}")
            except Exception as e:
                print(f"  Lỗi khi xóa {path}: {e}")
    print("Hoàn tất.")

# Bước 5: Chạy chương trình
if __name__ == "__main__":
    main()
