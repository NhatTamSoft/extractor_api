import os
import google.generativeai as genai
import base64
from io import BytesIO
from PIL import Image
import fitz  # PyMuPDF
import pymssql
import json
import uuid
import time
import pandas as pd
from datetime import datetime
import unicodedata
import re
from openai import OpenAI
from dotenv import load_dotenv # Thư viện để đọc file .env
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import jwt
from sentence_transformers import SentenceTransformer, util
import unidecode
from app.services.tesseract import image_to_text_pytesseract_from_image
from typing import List
import google.cloud.vision as vision
import traceback
from azure.core.exceptions import HttpResponseError
# %%
# --- 2. Tải và cấu hình API Keys từ file .env ---
# Tải các biến môi trường từ file .env trong cùng thư mục
load_dotenv()

# Lấy API keys từ biến môi trường
google_api_key = os.getenv("GOOGLE_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY") # Đổi tên biến để tránh trùng

# Kiểm tra xem key có tồn tại không
if not google_api_key:
    raise ValueError("Lỗi: Không tìm thấy GOOGLE_API_KEY trong file .env hoặc biến môi trường.")
if not openai_api_key:
    raise ValueError("Lỗi: Không tìm thấy OPENAI_API_KEY trong file .env hoặc biến môi trường.")

# Cấu hình Google Generative AI
genai.configure(api_key=google_api_key)
model = genai.GenerativeModel(model_name="gemini-2.0-flash") # Hoặc model bạn muốn dùng

def get_gemini_response(prompt):
  """Gửi yêu cầu đến Gemini và trả về text."""
  try:
      response = model.generate_content(prompt)
      # Kiểm tra response có text không
      if hasattr(response, 'text'):
          return response.text
      else:
          print(f"Cảnh báo: Gemini không trả về text. Response: {response.prompt_feedback}")
          return "" # Hoặc xử lý lỗi khác
  except Exception as e:
      print(f"Lỗi khi gọi Gemini API: {e}")
      return "" # Trả về rỗng nếu lỗi
  # %%
# Hàm gọi OpenAI (Sử dụng API Key từ .env)
def chat_with_openai_json(prompt) -> str:
  """Chat với OpenAI và yêu cầu trả về JSON."""
  try:
      client = OpenAI(api_key=openai_api_key) # Sử dụng key từ .env
      response = client.chat.completions.create(
                    model="gpt-4o-mini", # Hoặc model bạn muốn
                    temperature = 0,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": """Bạn là 1 kế toán hành chính chuyên nghiệp, có kinh nghiệm 20 năm trong lĩnh vực kế toán"""},
                        {"role": "user", "content": prompt}
                    ]
                  )
      return response.choices[0].message.content
  except Exception as e:
      print(f"Lỗi khi gọi OpenAI API: {e}")
      return "{}" # Trả về JSON rỗng nếu lỗi

# %%
# --- Hàm chuyển đổi PDF thành ảnh ---
def pdf_to_images(pdf_path, zoom=2.0, pageRange=""):
    """
    Chuyển đổi các trang của tệp PDF thành danh sách các đối tượng ảnh PIL.

    Args:
        pdf_path (str): Đường dẫn đến tệp PDF.
        zoom (float): Hệ số phóng đại ảnh (tăng giá trị để có độ phân giải cao hơn).
        pageRange (str): Chuỗi chỉ định các trang cần xử lý (ví dụ: "1,2,5-8").

    Returns:
        list: Danh sách các đối tượng ảnh PIL, mỗi ảnh là một trang PDF.
              Trả về danh sách rỗng nếu có lỗi hoặc không tìm thấy tệp.
    """
    images = []
    doc = None # Khởi tạo doc là None
    
    # Kiểm tra và xử lý giá trị zoom
    try:
        zoom = float(zoom) if zoom else 2.0
        if zoom <= 0:
            print("Cảnh báo: Giá trị zoom không hợp lệ, sử dụng giá trị mặc định 2.0")
            zoom = 2.0
    except (ValueError, TypeError):
        print("Cảnh báo: Không thể chuyển đổi giá trị zoom, sử dụng giá trị mặc định 2.0")
        zoom = 2.0

    try:
        doc = fitz.open(pdf_path)
        # Xác định danh sách các trang cần xử lý
        if pageRange == "":
            # Nếu pageRange rỗng, xử lý tất cả các trang
            pages_to_process = range(len(doc))
        else:
            # Nếu có pageRange, sử dụng hàm parse_page_string để lấy danh sách trang
            # print("====================> pageRange: ", pageRange)
            pages_to_process = parse_page_string(pageRange)
            # Điều chỉnh index (trừ 1 vì parse_page_string trả về số trang bắt đầu từ 1)
            pages_to_process = [p-1 for p in pages_to_process if p-1 < len(doc)]
        # Kiểm tra số trang của file PDF
        if len(doc) >= 10 and len(pageRange.split(';')) >= 10:
            print(f"\033[91mCảnh báo: File PDF '{os.path.basename(pdf_path)}' có {len(doc)} trang, vượt quá giới hạn 10 trang. Bỏ qua xử lý.\033[0m")
            return []
        # Xử lý từng trang được chỉ định
        for page_num in pages_to_process:
            if page_num >= len(doc) or page_num < 0:
                print(f"\033[91mCảnh báo: Trang {page_num} không tồn tại trong file PDF\033[0m")
                continue
            page = doc.load_page(page_num)
            # Phóng to độ phân giải để cải thiện chất lượng OCR
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False) # alpha=False để bỏ kênh alpha nếu không cần
            img_data = pix.tobytes("png")  # Lấy dữ liệu ảnh dạng bytes (PNG)
            # image là đối tượng PIL.Image.Image
            image = Image.open(BytesIO(img_data))
            # print('=============CHUYỂN ẢNH SANG TEXT=========')
            # print("Kết quả: ", image_to_text_pytesseract_from_image(image))
            # print('=============kết thúc CHUYỂN ẢNH SANG TEXT=========')
            if len(image_to_text_pytesseract_from_image(image)) <= 10: #LOẠI RA CÁC TRANG RỖNG
                continue
            images.append(image)
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy tệp PDF tại '{pdf_path}'")
    except RuntimeError as e_fitz:
         print(f"Lỗi PyMuPDF (RuntimeError) khi xử lý file {os.path.basename(pdf_path)} trong pdf_to_images: {e_fitz}")
    except Exception as e:
        print(f"Lỗi khi chuyển đổi PDF thành ảnh '{os.path.basename(pdf_path)}': {str(e)}")
        print(f"Nguyên nhân lỗi: {type(e).__name__}")
        print(f"Dòng code gây lỗi: {e.__traceback__.tb_lineno}")
    finally:
        if doc:
            doc.close() # Đảm bảo đóng file
    return images

# --- Hàm trích xuất văn bản từ ảnh bằng Gemini với prompt cụ thể ---
def extract_text_from_images_with_prompt(images, prompt, model_name="gemini-2.0-flash", max_retries=2, initial_delay=5):
    """
    Sử dụng mô hình Gemini để trích xuất văn bản từ danh sách ảnh với một prompt cụ thể.
    Bao gồm cơ chế thử lại đơn giản khi gặp lỗi API.

    Args:
        images (list): Danh sách các đối tượng ảnh PIL.
        prompt (str): Prompt hướng dẫn mô hình cách trích xuất thông tin.
        model_name (str): Tên mô hình Gemini muốn sử dụng.
        max_retries (int): Số lần thử lại tối đa nếu gọi API thất bại.
        initial_delay (int): Thời gian chờ ban đầu (giây) trước khi thử lại.

    Returns:
        str: Toàn bộ văn bản được trích xuất từ các ảnh theo yêu cầu của prompt.
             Trả về chuỗi rỗng nếu có lỗi hoặc không có ảnh.
    """
    if not images:
        print("Không có ảnh nào để xử lý OCR.")
        return ""

    full_text = ""
    retries = 0
    delay = initial_delay

    while retries <= max_retries:
        try:
            # Chọn mô hình hỗ trợ xử lý hình ảnh
            model = genai.GenerativeModel(model_name)

            print(f"Đang xử lý {len(images)} ảnh bằng mô hình {model_name} với prompt cụ thể (Lần thử {retries + 1}/{max_retries + 1})...")

            # Chuẩn bị danh sách các phần (prompt + từng ảnh)
            parts = [prompt] # Prompt đặt ở đầu
            for i, img in enumerate(images):
                # Chuyển đổi ảnh PIL thành bytes để gửi cho API
                img_byte_arr = BytesIO()
                # Lưu ảnh với chất lượng tốt hơn nếu cần (ví dụ: PNG không nén)
                img.save(img_byte_arr, format='PNG')
                img_bytes = img_byte_arr.getvalue()
                parts.append({
                    "mime_type": "image/png",
                    "data": img_bytes
                })

            # Gọi API Gemini
            print("Đang gửi yêu cầu OCR đến Gemini API...")
            # Tăng thời gian chờ nếu cần xử lý file lớn
            request_options = {"timeout": 600} # Timeout 10 phút
            response = model.generate_content(parts)
            print("Đã nhận phản hồi OCR từ Gemini API.")

            # Kiểm tra xem có lỗi trong phản hồi không (VD: safety settings)
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                 print(f"Yêu cầu OCR bị chặn: {response.prompt_feedback.block_reason}")
                 return "" # Không thử lại nếu bị chặn

            # Kiểm tra xem có text trả về không
            if not hasattr(response, 'text'):
                 print("Phản hồi OCR không chứa thuộc tính 'text'. Phản hồi đầy đủ:")
                 try:
                     print(response.parts)
                 except Exception:
                     print(response)

                 if hasattr(response, 'parts'):
                     extracted_texts = [part.text for part in response.parts if hasattr(part, 'text')]
                     if extracted_texts:
                         full_text = "\n".join(extracted_texts)
                         print("Đã ghép text từ các parts của phản hồi OCR.")
                         return full_text # Trả về kết quả thành công
                     else:
                         print("Không tìm thấy văn bản trong các phần của phản hồi OCR.")
                         return "" # Không thử lại nếu không có text
                 else:
                     print("Không thể trích xuất văn bản OCR từ phản hồi.")
                     return "" # Không thử lại
            else:
                full_text = response.text
                return full_text # Trả về kết quả thành công

        except genai.types.generation_types.BlockedPromptException as e:
            print(f"Lỗi OCR: Yêu cầu bị chặn bởi bộ lọc an toàn. {e}")
            return "" # Không thử lại nếu bị chặn
        except genai.types.generation_types.StopCandidateException as e:
            print(f"Lỗi OCR: Quá trình tạo nội dung bị dừng. {e}")
            return "" # Có thể không cần thử lại lỗi này
        except TimeoutError:
             print(f"Lỗi OCR: Yêu cầu đến Gemini API bị timeout.")
             retries += 1
             if retries <= max_retries:
                 print(f"Đang thử lại sau {delay} giây...")
                 time.sleep(delay)
                 delay *= 2 # Tăng gấp đôi thời gian chờ (exponential backoff)
             else:
                 print("Đã đạt số lần thử lại tối đa cho lỗi timeout.")
                 return ""
        except Exception as e:
            print(f"Đã xảy ra lỗi trong quá trình gọi Gemini API cho OCR: {e}")
            if hasattr(e, 'response'):
                print("Chi tiết phản hồi lỗi OCR:", e.response)

            # Xem xét thử lại cho các lỗi chung khác
            retries += 1
            if retries <= max_retries:
                 print(f"Đang thử lại sau {delay} giây...")
                 time.sleep(delay)
                 delay *= 2 # Tăng gấp đôi thời gian chờ
            else:
                 print("Đã đạt số lần thử lại tối đa cho lỗi API.")
                 return "" # Trả về rỗng sau khi hết số lần thử lại

    return "" # Trả về rỗng nếu tất cả các lần thử lại đều thất bại

# --- Hàm chính để đọc PDF (kết hợp text và OCR) ---
def read_text_from_pdf_combined(file_path, specific_ocr_prompt_text_pdf, ocr_prompt, model_name="gemini-2.0-flash", output_image_dir="temp_image", loai_file="IMAGE"):
    """
    Đọc nội dung văn bản từ file PDF.
    Ưu tiên trích xuất text trực tiếp, nếu không được sẽ dùng Gemini OCR với prompt cụ thể.
    Nếu dùng OCR, các ảnh trang PDF sẽ được lưu vào thư mục chỉ định.

    Args:
        file_path (str): Đường dẫn đến tệp PDF.
        ocr_prompt (str): Prompt sử dụng cho Gemini khi cần OCR.
        model_name (str): Tên mô hình Gemini.
        output_image_dir (str): Thư mục để lưu ảnh trang PDF khi cần OCR. Mặc định là "temp_image".

    Returns:
        str: Nội dung trích xuất được, hoặc chuỗi rỗng nếu lỗi.
    """
    direct_text = ""
    doc = None # Khởi tạo doc là None
    file_basename = os.path.basename(file_path)
    pdf_base_name_no_ext = os.path.splitext(file_basename)[0] # Lấy tên file không có extension

    try:
        # 1. Thử trích xuất text trực tiếp
        print(f"Đang thử đọc text trực tiếp từ: {file_basename}...")
        doc = fitz.open(file_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_text = page.get_text("text", sort=True) # Thêm sort=True để thử sắp xếp text
            if page_text:
                direct_text += page_text.strip() + "\n" # .strip() để loại bỏ khoảng trắng thừa

        # Kiểm tra kỹ hơn xem có text thực sự không (loại bỏ các trang chỉ có khoảng trắng)
        if direct_text.strip() and loai_file=="IMAGE": # ĐANG TẮT ĐOẠN CODE NÀY DO ĐOC SAI SỐ CHỨNG TỪ
            print(f">>>>>>>> Đã đọc text trực tiếp thành công từ: {file_basename}")
            # Đóng file trước khi trả về
            if doc:
                doc.close()
                doc = None
            direct_text = direct_text.strip()
            all_text = get_gemini_response(specific_ocr_prompt_text_pdf +"\n\n"+direct_text) # Gọi Gemini để xử lý text đã đọc
            return direct_text.strip() # Trả về text đã loại bỏ khoảng trắng thừa ở đầu/cuối
        else:
            # 2. Nếu không có text trực tiếp, thử OCR bằng Gemini
            print(f">>>>>>>> Không có text trực tiếp hoặc chỉ có khoảng trắng, thử OCR bằng Gemini cho: {file_basename}")
            # Đóng file trước khi gọi hàm chuyển ảnh để tránh lỗi file đang mở
            if doc:
                doc.close()
                doc = None # Đặt lại là None sau khi đóng

            pdf_images = pdf_to_images(file_path, zoom=2.5) # Tăng nhẹ zoom cho OCR
            if pdf_images:
                print(f"Đã chuyển đổi thành công {len(pdf_images)} trang PDF thành ảnh để OCR.")

                # --- THÊM LOGIC LƯU ẢNH ---
                if output_image_dir: # Chỉ lưu nếu có tên thư mục được cung cấp
                    try:
                        # Tạo thư mục nếu chưa tồn tại
                        os.makedirs(output_image_dir, exist_ok=True)
                        print(f"\n--- BẮT ĐẦU LƯU ẢNH VÀO '{output_image_dir}' ---")
                        for i, img in enumerate(pdf_images):
                            # Tạo tên file ảnh duy nhất
                            image_filename = f"{pdf_base_name_no_ext}_page_{i+1}.png"
                            image_save_path = os.path.join(output_image_dir, image_filename)
                            try:
                                img.save(image_save_path, format='PNG')
                                print(f"Đã lưu ảnh trang {i+1} vào: {image_save_path}")
                            except Exception as e_save:
                                print(f"Lỗi: Không thể lưu ảnh trang {i+1} vào '{image_save_path}': {e_save}")
                        print("--- KẾT THÚC LƯU ẢNH ---\n")
                    except Exception as e_dir:
                        print(f"Lỗi: Không thể tạo hoặc truy cập thư mục '{output_image_dir}': {e_dir}")
                        # Vẫn tiếp tục OCR dù không lưu được ảnh
                # --- KẾT THÚC LOGIC LƯU ẢNH ---

                # Gọi hàm OCR với prompt cụ thể và cơ chế thử lại
                ocr_text = extract_text_from_images_with_prompt(pdf_images, ocr_prompt, model_name)
                if ocr_text:
                    print(f">>>>>>>> Đã OCR thành công bằng Gemini cho: {file_basename}")
                    return ocr_text.strip() # Trả về text OCR đã chuẩn hóa
                else:
                    print(f"Cảnh báo: OCR bằng Gemini không trả về kết quả cho file {file_basename} sau khi thử lại.")
                    return "" # Trả về rỗng nếu OCR không thành công
            else:
                print(f"Lỗi: Không thể chuyển đổi PDF thành ảnh để OCR cho file {file_basename}.")
                return "" # Trả về rỗng nếu không chuyển được ảnh

    except RuntimeError as e_fitz:
        print(f"Lỗi PyMuPDF (RuntimeError) khi mở hoặc xử lý file {file_basename}: {e_fitz}")
        return ""
    except Exception as e_general:
        print(f"Lỗi không xác định khi đọc file PDF {file_basename}: {e_general}")
        return ""
    finally:
        # Đảm bảo file được đóng nếu có lỗi xảy ra hoặc chưa đóng
        if doc and not doc.is_closed:
            print(f"Đóng file PDF {file_basename} trong finally.")
            doc.close()

# %%
def xoa_file(duong_dan_file):
    """
    Hàm xóa file tại đường dẫn được chỉ định.

    Args:
        duong_dan_file (str): Đường dẫn tuyệt đối hoặc tương đối đến file cần xóa.

    Returns:
        str: Thông báo kết quả xóa file.
    """
    try:
        if os.path.exists(duong_dan_file):
            os.remove(duong_dan_file)
            return f"Đã xóa file: {duong_dan_file}"
        else:
            return f"File không tồn tại: {duong_dan_file}"
    except Exception as e:
        return f"Lỗi khi xóa file: {e}"

def thuc_thi_truy_van(cau_sql):
    """
    Thực thi truy vấn SQL và trả về kết quả.
    
    Args:
        cau_sql (str): Câu lệnh SQL cần thực thi
        
    Returns:
        bool: True nếu thực thi thành công, False nếu có lỗi
    """
    try:
        # Lấy thông tin kết nối từ biến môi trường
        server = os.getenv("DB_SERVER").replace(",", ":")
        database = os.getenv("DB_NAME")
        username = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        
        # Kiểm tra các thông tin kết nối
        if not all([server, database, username, password]):
            print("Thiếu thông tin kết nối SQL Server trong file .env")
            return False
            
        # Kết nối đến SQL Server
        conn = pymssql.connect(
            server=server,
            database=database,
            user=username,
            password=password
        )
        
        # Tạo cursor để thực thi truy vấn
        cursor = conn.cursor()
        
        # Thực thi truy vấn
        cursor.execute(cau_sql)
        
        # Commit thay đổi
        conn.commit()
        
        # Đóng cursor và kết nối
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Lỗi khi thực thi truy vấn SQL: {str(e)}")
        return False


def lay_du_lieu_tu_sql_server(cau_sql):
    """
    Lấy dữ liệu từ SQL Server và trả về DataFrame.
    
    Args:
        cau_sql (str): Câu lệnh SQL để truy vấn dữ liệu
        
    Returns:
        pandas.DataFrame: DataFrame chứa kết quả truy vấn
        
    Raises:
        Exception: Nếu có lỗi xảy ra trong quá trình kết nối hoặc truy vấn
    """
    try:
        # Lấy thông tin kết nối từ biến môi trường
        server = os.getenv("DB_SERVER").replace(",", ":")
        database = os.getenv("DB_NAME")
        username = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        
        # Kiểm tra các thông tin kết nối
        if not all([server, database, username, password]):
            raise ValueError("Thiếu thông tin kết nối SQL Server trong file .env")
            
        # Kết nối đến SQL Server
        conn = pymssql.connect(
            server=server,
            database=database,
            user=username,
            password=password
        )
        
        # Đọc dữ liệu vào DataFrame
        df = pd.read_sql(cau_sql, conn)
        
        # Đóng kết nối
        conn.close()
        
        return df
        
    except Exception as e:
        print(f"Lỗi khi lấy dữ liệu từ SQL Server: {str(e)}")
        raise

def to_slug(text):
    """
    Chuyển đổi chuỗi tiếng Việt có dấu thành không dấu và thay thế khoảng trắng bằng dấu gạch ngang.
    
    Args:
        text (str): Chuỗi cần chuyển đổi
        
    Returns:
        str: Chuỗi đã được chuyển đổi
    """
    # Chuyển đổi tiếng Việt có dấu thành không dấu
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
    
    # Chuyển thành chữ thường
    text = text.lower()
    
    # Thay thế khoảng trắng bằng dấu gạch ngang
    text = re.sub(r'\s+', '-', text)
    
    # Loại bỏ các ký tự đặc biệt
    text = re.sub(r'[^a-z0-9-]', '', text)
    
    # Loại bỏ các dấu gạch ngang liên tiếp
    text = re.sub(r'-+', '-', text)
    
    # Loại bỏ dấu gạch ngang ở đầu và cuối
    text = text.strip('-')
    
    return text

# --- Hàm 2: Tìm kiếm sử dụng TfidfVectorizer ---
def tim_kiem_tfidf(chuoi_can_tim, df_kmcp, cot_tim_kiem='TenKMCP', so_luong_ket_qua=3, cot_can_lay=None):
    """
    Tìm kiếm các mục trong DataFrame có độ tương đồng cao nhất với chuỗi đầu vào
    sử dụng TfidfVectorizer và cosine similarity.

    Args:
        chuoi_can_tim (str): Chuỗi văn bản cần tìm kiếm.
        df_kmcp (pandas.DataFrame): DataFrame chứa dữ liệu.
        cot_tim_kiem (str, optional): Tên cột trong df_kmcp dùng để thực hiện tìm kiếm.
                                      Mặc định là 'TenKMCP'.
        so_luong_ket_qua (int, optional): Số lượng kết quả có độ tương đồng cao nhất
                                         cần trả về. Mặc định là 3.
        cot_can_lay (list, optional): Danh sách các tên cột cần lấy trong kết quả.
                                      Nếu None, tất cả các cột sẽ được trả về.
                                      Cột 'do_tuong_dong' sẽ luôn được thêm vào.

    Returns:
        pandas.DataFrame: DataFrame chứa các hàng có độ tương đồng cao nhất,
                          hoặc DataFrame rỗng nếu không có kết quả hoặc có lỗi.
    """
    if df_kmcp is None or df_kmcp.empty:
        print("DataFrame đầu vào rỗng hoặc None.")
        return pd.DataFrame()

    if cot_tim_kiem not in df_kmcp.columns:
        print(f"DataFrame thiếu cột '{cot_tim_kiem}' để thực hiện tìm kiếm.")
        return pd.DataFrame()

    # Tạo một bản sao để tránh thay đổi DataFrame gốc khi thêm cột tạm
    df_processed = df_kmcp.copy()
    # Đảm bảo cột dùng để tìm kiếm không có giá trị NaN và là kiểu string
    df_processed[f'{cot_tim_kiem}_processed'] = df_processed[cot_tim_kiem].fillna('').astype(str)


    # Tạo một corpus từ cột được chỉ định
    corpus = df_processed[f'{cot_tim_kiem}_processed'].tolist()

    if not any(corpus): # Kiểm tra xem corpus có rỗng hoặc chỉ chứa chuỗi rỗng không
        print(f"Cột '{cot_tim_kiem}' không có dữ liệu để thực hiện TF-IDF.")
        return pd.DataFrame()

    try:
        # Khởi tạo TfidfVectorizer
        vectorizer = TfidfVectorizer()

        # Học từ vựng và tính toán TF-IDF cho corpus
        tfidf_matrix = vectorizer.fit_transform(corpus)

        # Tính toán TF-IDF cho chuỗi cần tìm
        chuoi_can_tim_tfidf = vectorizer.transform([str(chuoi_can_tim)])

        # Tính toán cosine similarity
        cosine_similarities = cosine_similarity(chuoi_can_tim_tfidf, tfidf_matrix).flatten()

        # Lấy chỉ số của các mục có độ tương đồng cao nhất
        # Đảm bảo so_luong_ket_qua không lớn hơn số lượng item có trong cosine_similarities
        actual_so_luong_ket_qua = min(so_luong_ket_qua, len(cosine_similarities))
        if actual_so_luong_ket_qua == 0:
             print("Không có dữ liệu để sắp xếp.")
             return pd.DataFrame()

        top_n_indices = cosine_similarities.argsort()[-actual_so_luong_ket_qua:][::-1]


        # Lọc ra các kết quả có độ tương đồng > 0
        relevant_indices = [idx for idx in top_n_indices if cosine_similarities[idx] > 0]

        if not relevant_indices:
            print("Không tìm thấy kết quả nào có độ tương đồng > 0.")
            return pd.DataFrame()

        # Trả về các hàng tương ứng từ DataFrame gốc (sử dụng df_kmcp để lấy cột gốc)
        ket_qua_tim_kiem = df_kmcp.iloc[relevant_indices].copy() # Tạo bản sao để thêm cột mới

        # Thêm cột điểm tương đồng
        ket_qua_tim_kiem.loc[:, 'do_tuong_dong'] = cosine_similarities[relevant_indices]

        # Lọc cột nếu cot_can_lay được chỉ định
        if cot_can_lay and isinstance(cot_can_lay, list):
            # Đảm bảo các cột yêu cầu tồn tại trong kết quả
            cot_hien_co = [col for col in cot_can_lay if col in ket_qua_tim_kiem.columns]
            # Luôn bao gồm cột 'do_tuong_dong'
            if 'do_tuong_dong' not in cot_hien_co:
                cot_hien_co.append('do_tuong_dong')
            # Loại bỏ các cột trùng lặp nếu có
            final_cols_to_select = list(dict.fromkeys(cot_hien_co))
            ket_qua_tim_kiem = ket_qua_tim_kiem[final_cols_to_select]
        else: # Nếu cot_can_lay không được cung cấp, đảm bảo 'do_tuong_dong' vẫn ở đó
            if 'do_tuong_dong' not in ket_qua_tim_kiem.columns:
                 # Điều này không nên xảy ra nếu logic ở trên đúng, nhưng để chắc chắn
                 ket_qua_tim_kiem.loc[:, 'do_tuong_dong'] = cosine_similarities[relevant_indices]


        return ket_qua_tim_kiem.drop(columns=[f'{cot_tim_kiem}_processed'], errors='ignore')


    except Exception as e:
        print(f"Lỗi trong quá trình tính toán TF-IDF hoặc cosine similarity: {e}")
        return pd.DataFrame()
    
def convert_currency_to_float(value: str) -> float:
    try:
        # Loại bỏ tất cả các ký tự không phải số và dấu chấm
        value = ''.join(c for c in value if c.isdigit() or c == '.')
        # Loại bỏ dấu chấm ngăn cách hàng nghìn
        value = value.replace('.', '')
        # Chuyển đổi thành float
        return float(value)
    except (ValueError, TypeError):
        return 0
    
def convert_currency_to_int(value: str) -> int:
    try:
        # Loại bỏ tất cả các ký tự không phải số và dấu chấm
        value = ''.join(c for c in value if c.isdigit() or c == '.')
        # Loại bỏ dấu chấm ngăn cách hàng nghìn
        value = value.replace('.', '')
        # Chuyển đổi thành float
        return int(value)
    except (ValueError, TypeError):
        return 0

def decode_jwt_token(token: str) -> dict:
    """
    Giải mã JWT token và trả về thông tin userID và donViID.
    
    Args:
        token (str): JWT token cần giải mã
        
    Returns:
        dict: Dictionary chứa userID và donViID
        
    Raises:
        Exception: Nếu token không hợp lệ hoặc không thể giải mã
    """
    try:
        # Lấy secret key từ biến môi trường
        secret_key = os.getenv("JWT_SECRET_KEY")
        if not secret_key:
            raise ValueError("Không tìm thấy JWT_SECRET_KEY trong file .env")
            
        # Giải mã token với options để bỏ qua audience validation
        decoded = jwt.decode(
            token, 
            secret_key, 
            algorithms=["HS256"],
            options={
                "verify_aud": False,  
                "verify_exp": True,   
                "verify_iat": True,   
                "verify_nbf": True    
            }
        )
        
        if "UserId" not in decoded or "DonViID" not in decoded:
            raise ValueError("Token không chứa đủ thông tin userID hoặc donViID")
            
        return {
            "userID": decoded["UserId"],
            "donViID": decoded["DonViID"]
        }
    except jwt.ExpiredSignatureError:
        raise Exception("Token đã hết hạn")
    except jwt.InvalidTokenError as e:
        raise Exception(f"Token không hợp lệ: {str(e)}")
    except Exception as e:
        raise Exception(f"Lỗi khi giải mã token: {str(e)}")
    
def encode_image_to_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def LayMaDoiTuong(don_vi_id: str, user_id: str, ten_toi_tuong: str, la_ca_nhan: str) -> str:
    """
    Lấy mã đối tượng từ CSDL hoặc tạo mới nếu chưa tồn tại
    
    Args:
        don_vi_id (str): ID đơn vị
        user_id (str): ID người dùng
        ten_toi_tuong (str): Tên đối tượng cần tìm
        la_ca_nhan (str): Có phải cá nhân hay không
        
    Returns:
        str: ID đối tượng
    """
    # Kiểm tra đối tượng đã tồn tại chưa
    query_check = f"""
    Select DoiTuongID from dbo.DoiTuong 
    where TenDoiTuong=N'{ten_toi_tuong}' and DonViID=N'{don_vi_id}'
    """
    result = lay_du_lieu_tu_sql_server(query_check)
    
    # Nếu đã tồn tại thì trả về DoiTuongID
    if not result.empty:
        return result.iloc[0]['DoiTuongID']
        
    # Nếu chưa tồn tại thì tạo mới
    doi_tuong_id = str(uuid.uuid4())
    query_insert = f"""
    Insert into dbo.DoiTuong (DoiTuongID, MaDoiTuong, TenDoiTuong, LaCaNhan, DonViID, UserID)
    Select 
        DoiTuongID=N'{doi_tuong_id}',
        MaDoiTuong=dbo.Func_GenerateMaDoiTuong(N'{don_vi_id}'),
        TenDoiTuong=N'{ten_toi_tuong}',
        LaCaNhan=N'{la_ca_nhan}',
        DonViID=N'{don_vi_id}',
        UserID=N'{user_id}'
    """
    thuc_thi_truy_van(query_insert)    
    return doi_tuong_id

# Khởi tạo mô hình (nên thực hiện một lần và truyền vào các hàm)
# Model này sẽ được truyền vào hàm tim_khoan_muc_tuong_ung
# model = SentenceTransformer('distiluse-base-multilingual-cased') # Bỏ comment và chạy nếu bạn chưa khởi tạo model ở đâu đó

import unidecode
from sentence_transformers import SentenceTransformer, util
import re # Import regex module

# Khởi tạo mô hình một lần (đảm bảo mô hình được tải)
# model_st = SentenceTransformer('distiluse-base-multilingual-cased') # Đảm bảo dòng này không bị comment nếu chưa có ở đâu khác

def lam_sach(text):
    """
    Làm sạch văn bản: chuyển về chữ thường, bỏ dấu tiếng Việt, loại bỏ ký tự đặc biệt (trừ chữ, số, khoảng trắng),
    và chuẩn hóa khoảng trắng.
    Args:
        text (str): Văn bản đầu vào.
    Returns:
        str: Văn bản đã được làm sạch.
    """
    if not isinstance(text, str):
        # Log lỗi hoặc xử lý ngoại lệ nếu cần thiết, nhưng trả về chuỗi rỗng hoặc None có thể an toàn hơn
        # tùy thuộc vào cách hàm này được sử dụng. Hiện tại giữ nguyên raise TypeError.
        raise TypeError(f"Đầu vào cho lam_sach phải là chuỗi. Nhận được: {type(text)}, Giá trị: {text}")
        
    # Chuyển về chữ thường và bỏ dấu tiếng Việt
    text = unidecode.unidecode(text.lower())
    
    # Loại bỏ các ký tự không phải chữ cái, số, hoặc khoảng trắng
    text = re.sub(r'[^a-z0-9\s]', '', text)
    
    # Chuẩn hóa khoảng trắng (thay thế nhiều khoảng trắng bằng một khoảng trắng duy nhất và loại bỏ khoảng trắng ở đầu/cuối)
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def thay_the_viet_tat(text, current_viet_tat_dict):
    """
    Thay thế các từ viết tắt trong văn bản bằng cụm từ đầy đủ.
    Sử dụng regex để thay thế các từ viết tắt đứng độc lập hoặc được phân cách bởi khoảng trắng/ký tự đặc biệt.
    Args:
        text (str): Văn bản đầu vào.
        current_viet_tat_dict (dict): Từ điển viết tắt hiện tại để sử dụng (key là viết tắt, value là cụm đầy đủ).
    Returns:
        str: Văn bản đã được thay thế từ viết tắt.
    """
    if not isinstance(text, str):
        raise TypeError(f"Đầu vào cho thay_the_viet_tat phải là chuỗi. Nhận được: {type(text)}, Giá trị: {text}")
        
    # Sắp xếp các từ viết tắt theo độ dài giảm dần để thay thế các cụm dài trước
    sorted_viet_tat = sorted(current_viet_tat_dict.items(), key=lambda item: len(item[0]), reverse=True)
    
    processed_text = text
    for viet_tat, full_term in sorted_viet_tat:
        # Tạo regex pattern để tìm từ viết tắt đứng độc lập (word boundary)
        # \b đảm bảo chỉ khớp toàn bộ từ
        pattern = r'\b' + re.escape(viet_tat) + r'\b'
        processed_text = re.sub(pattern, full_term, processed_text)
        
    return processed_text

def tien_xu_ly(text, current_viet_tat_dict):
    """
    Tiền xử lý văn bản bằng cách thay thế từ viết tắt và sau đó làm sạch.
    Thứ tự này giúp các từ viết tắt được thay thế đúng trước khi làm sạch loại bỏ ký tự đặc biệt.
    Args:
        text (str): Văn bản đầu vào.
        current_viet_tat_dict (dict): Từ điển viết tắt để sử dụng.
    Returns:
        str: Văn bản đã được tiền xử lý.
    """
    if not isinstance(text, str):
        raise TypeError(f"Đầu vào cho tien_xu_ly phải là chuỗi. Nhận được: {type(text)}, Giá trị: {text}")
        
    # Thay thế từ viết tắt trước
    text_after_viet_tat = thay_the_viet_tat(text, current_viet_tat_dict)
    
    # Sau đó làm sạch văn bản
    text_sach = lam_sach(text_after_viet_tat)
    
    return text_sach

# Khởi tạo mô hình một lần (đảm bảo dòng này tồn tại và không bị comment)
# model_st = SentenceTransformer('distiluse-base-multilingual-cased')

# def tim_tuong_dong(ten_khoan_muc_thuc_te, current_dm_chuan, current_viet_tat, danh_sach_loai_tru=None, nguong=0.65):
#     """
#     Tìm khoản mục chuẩn tương ứng với tên khoản mục thực tế, sử dụng danh mục chuẩn và từ điển viết tắt được cung cấp.
#     Áp dụng tiền xử lý (thay thế viết tắt, làm sạch) cho cả đầu vào và danh mục chuẩn.
#     Args:
#         ten_khoan_muc_thuc_te (str): Tên khoản mục chi phí thực tế.
#         current_dm_chuan (dict): Dictionary chứa 2 cột, cột 1 là ID, cột 2 là tên để tìm kiếm ({ID: Tên}).
#         current_viet_tat (dict): Từ điển viết tắt ({Viết tắt: Cụm đầy đủ}).
#         danh_sach_loai_tru (list): Danh sách các tên khoản mục chuẩn cần loại trừ khỏi kết quả tìm kiếm.
#         nguong (float): Ngưỡng điểm tương đồng (cosine similarity) để chấp nhận kết quả.
#     Returns:
#         tuple: (Dictionary chứa ID và tên của phần tử tương ứng từ current_dm_chuan, điểm tương đồng)
#         current_dm_chuan (dict): Dictionary chứa 2 cột, cột 1 là ID, cột 2 là tên để tìm kiếm.
#         current_viet_tat (dict): Từ điển viết tắt.
#         danh_sach_loai_tru (list): Danh sách các khoản mục cần loại trừ khỏi kết quả tìm kiếm.
#         nguong (float): Ngưỡng điểm tương đồng để chấp nhận kết quả.
#     Returns:
#         tuple: (Phần tử tương ứng từ current_dm_chuan, điểm tương đồng) hoặc (None, điểm tương đồng) nếu không đạt ngưỡng.
#     """
#     model = model_st
#     if not isinstance(ten_khoan_muc_thuc_te, str):
#         raise TypeError(f"Input item '{ten_khoan_muc_thuc_te}' to tim_khoan_muc_tuong_ung must be a string.")
#     if not model:
#         raise ValueError("SentenceTransformer model must be provided.")

#     # Lấy danh sách tên để tìm kiếm (cột 2)
#     ten_dm_chuan = list(current_dm_chuan.values())
#     id_dm_chuan = list(current_dm_chuan.keys())

#     # Lọc danh mục chuẩn để loại bỏ các khoản mục trong danh_sach_loai_tru
#     if danh_sach_loai_tru:
#         filtered_items = [(id, ten) for id, ten in current_dm_chuan.items() if ten not in danh_sach_loai_tru]
#         id_dm_chuan = [item[0] for item in filtered_items]
#         ten_dm_chuan = [item[1] for item in filtered_items]

#     # Tiền xử lý danh mục chuẩn với từ điển viết tắt hiện tại
#     dm_chuan_clean = [tien_xu_ly(t, current_viet_tat) for t in ten_dm_chuan]
#     if not dm_chuan_clean or all(not item for item in dm_chuan_clean):
#         return (None, 0.0)
        
#     emb_chuan = model.encode(dm_chuan_clean, convert_to_tensor=True)

#     # Tiền xử lý tên khoản mục thực tế với từ điển viết tắt hiện tại
#     ten_clean = tien_xu_ly(ten_khoan_muc_thuc_te, current_viet_tat)

#     if not ten_clean.strip():
#         return (None, 0.0)

#     emb_input = model.encode(ten_clean, convert_to_tensor=True)

#     if emb_chuan.nelement() == 0:
#         return (None, 0.0)

#     cos_sim_result = util.cos_sim(emb_input, emb_chuan)

#     if cos_sim_result is None or cos_sim_result.nelement() == 0:
#         return (None, 0.0)

#     cos_scores = cos_sim_result[0]
#     best_match_idx = int(cos_scores.argmax())
#     best_score = float(cos_scores[best_match_idx])

#     if best_score >= nguong:
#         # Trả về phần tử tương ứng từ current_dm_chuan
#         matched_item = {
#             "id": id_dm_chuan[best_match_idx],
#             "name": ten_dm_chuan[best_match_idx]
#         }
#         return (matched_item, best_score)
#     else:
#         return (None, best_score)
    

def parse_page_string(page_string):
    """
    Chuyển đổi một chuỗi số trang (ví dụ: '1,2,5-8') thành một danh sách các số nguyên.

    Args:
        page_string (str): Chuỗi chứa các số trang, có thể bao gồm số đơn lẻ,
                           hoặc dải số được phân tách bằng dấu gạch ngang.

    Returns:
        list: Một danh sách các số nguyên biểu thị các trang.
    """
    result = []
    # Loại bỏ khoảng trắng và đảm bảo chuỗi không rỗng
    page_string = page_string.replace(" ", "").strip()
    if not page_string:
        return []

    # Xử lý trường hợp chuỗi kết thúc bằng dấu phẩy
    if page_string.endswith(','):
        page_string = page_string[:-1]

    parts = page_string.split(',')
    for part in parts:
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                if start <= end:
                    result.extend(range(start, end + 1))
                else:
                    # Xử lý trường hợp dải số không hợp lệ (ví dụ: 8-5)
                    print(f"Cảnh báo: Dải số không hợp lệ '{part}' đã bị bỏ qua.")
            except ValueError:
                print(f"Cảnh báo: Định dạng dải số không đúng '{part}' đã bị bỏ qua.")
        else:
            try:
                result.append(int(part))
            except ValueError:
                print(f"Cảnh báo: Định dạng số không đúng '{part}' đã bị bỏ qua.")
    
    # Loại bỏ các số trùng lặp và sắp xếp lại
    return sorted(list(set(result)))

# Azure credentials
azure_endpoint = os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT")
azure_key = os.getenv("AZURE_FORM_RECOGNIZER_KEY")

# Initialize Azure client
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult, DocumentTable, DocumentLine, AnalyzeDocumentRequest, DocumentContentFormat
from azure.core.credentials import AzureKeyCredential

azure_client = DocumentIntelligenceClient(
    endpoint=azure_endpoint, credential=AzureKeyCredential(azure_key)
)
def extract_text_from_images_azure(image_files: List[str]) -> str:
    """
    Extract text and table data from images using Azure Form Recognizer.

    Args:
        image_files (List[str]): List of image file paths.

    Returns:
        str: Extracted content including text and tables.
    """
    print("======================extract_text_from_images_azure image_files==================")
    print(image_files)
    print("======================extract_text_from_images_azure end image_files==================")
    combiletext = ""
    for document_path in image_files:
        print(f"\n=== Processing file: {document_path} ===")
        try:
            if document_path.startswith("http://") or document_path.startswith("https://"):
                # Phân tích tài liệu từ URL
                print(f"Đang phân tích tài liệu từ URL: {document_path}...")
                poller = azure_client.begin_analyze_document(
                    "prebuilt-layout",
                    AnalyzeDocumentRequest(url_source=document_path),
                    output_content_format=DocumentContentFormat.MARKDOWN, # Yêu cầu đầu ra Markdown
                )
            else:
                # Phân tích tài liệu từ tệp cục bộ
                if not os.path.exists(document_path):
                    return f"### Lỗi: Tệp `{document_path}` không tồn tại.\n\n"
                print(f"Đang phân tích tài liệu từ tệp cục bộ: {document_path}...")
                with open(document_path, "rb") as f:
                    poller = azure_client.begin_analyze_document(
                        "prebuilt-layout", 
                        body=f.read(),
                        output_content_format=DocumentContentFormat.MARKDOWN, # Yêu cầu đầu ra Markdown
                    )
            with open(document_path, "rb") as f:
                poller = azure_client.begin_analyze_document("prebuilt-layout", body=f)
                result = poller.result()
            result: AnalyzeResult = poller.result()
            print("-------------------")
            # print(result.content)
            markdown_table = ""
            if result.tables is not None:  # Kiểm tra xem result.tables có tồn tại không
                for table in result.tables:
                    # print(table)
                    column_count = table['columnCount']
                    if column_count > 3:
                        markdown_table += f"=== START_BANG_CHI_TIET===\n"
                    else:
                        markdown_table += f"=== START_BANG_TONG_HOP===\n"
                    row_count = table['rowCount']
                    cells_data = table['cells']

                    # Tạo một cấu trúc dữ liệu để lưu trữ nội dung của các ô,
                    # ví dụ: một danh sách các danh sách (mảng 2D)
                    table_content = [['' for _ in range(column_count)] for _ in range(row_count)]

                    # Điền nội dung vào cấu trúc bảng
                    for cell in cells_data:
                        r_idx = cell['rowIndex']
                        c_idx = cell['columnIndex']
                        content = cell['content']
                        if 0 <= r_idx < row_count and 0 <= c_idx < column_count:
                            table_content[r_idx][c_idx] = content
                    # Tạo các hàng dữ liệu
                    for row in table_content:
                        markdown_table += "| " + " | ".join(row) + " |\n"
                    if column_count > 3:
                        markdown_table += f"=== END_BANG_CHI_TIET===\n"
                    else:
                        markdown_table += f"=== END_BANG_TONG_HOP===\n"
            print(markdown_table)
            # print("-------------------")
            # print(result.content)
            print("-------------------")
            # --- Trích xuất và định dạng văn bản và bảng (đã có sẵn trong result.content) ---
            #markdown_result += "### Nội dung trích xuất (định dạng Markdown):\n"
            if result.content:
                # markdown_result += result.content
                # Xóa phần table trong nội dung
                markdown_result = re.sub(r'<table>.*?</table>', '', str(result.content), flags=re.DOTALL)
                markdown_result += markdown_table
            else:
                markdown_result += "Không tìm thấy nội dung nào trong tài liệu.\n"
            combiletext += markdown_result
        except HttpResponseError as error:
            print(error)
            # Xử lý các lỗi HTTP cụ thể từ dịch vụ Azure
            #markdown_result += f"### Lỗi phản hồi HTTP khi phân tích tài liệu: {error.error.code} - {error.message}\n\n"
        except Exception as e:
            print(e)
            #combined_text += f"\n[Error processing {document_path}]: {str(e)}\n"
    # print("======================markdown_result==================")
    # print(markdown_result)
    # print("======================end markdown_result==================")
    return combiletext

def extract_text_from_images_google_cloud(image_files: List[str]) -> str:
    """
    Extract text from images using Google Cloud Vision API.
    
    Args:
        image_files (List[str]): List of paths to image files
        
    Returns:
        str: Combined text extracted from all images
    """
    combined_text = ""
    client = vision.ImageAnnotatorClient()
    
    for temp_file in image_files:
        try:
            # Read the image file
            with open(temp_file, "rb") as f:
                content = f.read()

            # Create image object
            image = vision.Image(content=content)

            # Perform text detection
            response = client.document_text_detection(image=image)
            texts = response.text_annotations

            if texts:
                # Get the full text (first annotation contains the entire text)
                text_content = texts[0].description
                combined_text += text_content + "\n"
            else:
                print("No text detected in the image")

            if response.error.message:
                print(f"Cloud Vision API error: {response.error.message}")
                raise Exception(
                    '{}\nFor more info on error messages, check: '
                    'https://cloud.google.com/apis/design/errors'.format(
                        response.error.message))

        except Exception as e:
            print(f"Error processing file {temp_file}: {str(e)}")
            print(f"Error type: {type(e)}")
            print(f"Error details: {traceback.format_exc()}")
            continue
            
    return combined_text