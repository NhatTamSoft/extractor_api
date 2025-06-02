import os
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult, DocumentTable, DocumentLine, AnalyzeDocumentRequest, DocumentContentFormat
from azure.core.exceptions import HttpResponseError
import re

# Thay thế bằng Endpoint và API Key của tài nguyên Azure AI Document Intelligence của bạn
# Luôn khuyến nghị lưu trữ các thông tin này trong biến môi trường để bảo mật
# Ví dụ: endpoint = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
# Ví dụ: key = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_API_KEY")
endpoint = "https://aidocum.cognitiveservices.azure.com/"
key = "F6VC9nbyCdbmTw5v2bxLuAbTGFeoiHhQu5KoJs5AgOCzJe2hwHazJQQJ99BEACqBBLyXJ3w3AAALACOGnZLn"

# Biến toàn cục để đếm số bảng
dem = 0

def analyze_document_and_format_markdown(document_path: str, client: DocumentIntelligenceClient) -> str:
    """
    Phân tích một tài liệu và trả về kết quả dưới dạng chuỗi Markdown.
    Hỗ trợ cả đường dẫn cục bộ và URL, sử dụng đầu ra Markdown trực tiếp từ dịch vụ.
    """
    global dem
    markdown_result = ""
    #markdown_result = f"## Phân tích tài liệu: `{document_path}`\n\n"

    try:
        if document_path.startswith("http://") or document_path.startswith("https://"):
            # Phân tích tài liệu từ URL
            print(f"Đang phân tích tài liệu từ URL: {document_path}...")
            poller = client.begin_analyze_document(
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
                poller = client.begin_analyze_document(
                    "prebuilt-layout", 
                    body=f.read(),
                    output_content_format=DocumentContentFormat.MARKDOWN, # Yêu cầu đầu ra Markdown
                )

        result: AnalyzeResult = poller.result()
        print("-------------------")
        
        markdown_table = ""
        if result.tables is not None:  # Kiểm tra xem result.tables có tồn tại không
            for table in result.tables:
                # print(table)
                dem+=1
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
                # Tạo hàng tiêu đề động
                # headers = [f"Cột {i + 1}" for i in range(column_count)]
                # markdown_table += "| " + " | ".join(headers) + " |\n"

                # Tạo hàng phân cách động
                # separators = ["---" for _ in range(column_count)]
                # markdown_table += "| " + " | ".join(separators) + " |\n"

                # Tạo các hàng dữ liệu
                for row in table_content:
                    markdown_table += "| " + " | ".join(row) + " |\n"
                if column_count > 3:
                    markdown_table += f"=== END_BANG_CHI_TIET===\n"
                else:
                    markdown_table += f"=== END_BANG_TONG_HOP===\n"
        #print(markdown_table)
        print("-------------------")
        #print(result.content)
        # --- Trích xuất và định dạng văn bản và bảng (đã có sẵn trong result.content) ---
        #markdown_result += "### Nội dung trích xuất (định dạng Markdown):\n"
        if result.content:
            # markdown_result += result.content
            # Xóa phần table trong nội dung
            markdown_result = re.sub(r'<table>.*?</table>', '', str(result.content), flags=re.DOTALL)
            markdown_result += markdown_table
        else:
            markdown_result += "Không tìm thấy nội dung nào trong tài liệu.\n"

    except HttpResponseError as error:
        print(error)
        # Xử lý các lỗi HTTP cụ thể từ dịch vụ Azure
        #markdown_result += f"### Lỗi phản hồi HTTP khi phân tích tài liệu: {error.error.code} - {error.message}\n\n"
    except Exception as e:
        print(e)
        # Xử lý các lỗi chung khác
        #markdown_result += f"### Lỗi khi phân tích tài liệu: {e}\n\n"
    
    markdown_result += "\n\n" # Dấu phân cách giữa các tài liệu

    return markdown_result

def process_multiple_documents(document_paths: list[str]) -> str:
    """
    Xử lý một mảng các đường dẫn tài liệu và trả về kết quả Markdown tổng hợp.
    """
    global dem
    if not endpoint or endpoint == "YOUR_DOCUMENT_INTELLIGENCE_ENDPOINT" or not key or key == "YOUR_DOCUMENT_INTELLIGENCE_API_KEY":
        return "## Lỗi cấu hình:\nVui lòng thay thế 'YOUR_DOCUMENT_INTELLIGENCE_ENDPOINT' và 'YOUR_DOCUMENT_INTELLIGENCE_API_KEY' bằng thông tin của bạn.\n\n"

    client = DocumentIntelligenceClient(
        endpoint=endpoint, credential=AzureKeyCredential(key)
    )

    full_markdown_output = "\n\n" #"# Kết quả phân tích tài liệu từ Azure AI Document Intelligence\n\n"
    
    if not document_paths:
        full_markdown_output += "Không có đường dẫn tài liệu nào được cung cấp để phân tích.\n"
        return full_markdown_output

    for path in document_paths:
        full_markdown_output += analyze_document_and_format_markdown(path, client)
    
    return full_markdown_output

if __name__ == "__main__":
    # --- Ví dụ sử dụng ---
    # Thay thế các đường dẫn này bằng đường dẫn tệp thực tế của bạn
    # Bạn có thể sử dụng cả đường dẫn cục bộ và URL
    sample_document_paths = [
        "D:\\11.jpg",
        "D:\\12.jpg",
        "D:\\13.jpg",
        "D:\\14.jpg",
        "D:\\15.jpg"
        # Thêm các file khác vào đây
    ]

    # Để thử nghiệm với tệp cục bộ, hãy tạo một tệp PDF hoặc hình ảnh đơn giản
    # có chứa văn bản và bảng, sau đó cập nhật đường dẫn ở đây.
    # Ví dụ: Tạo một tệp "my_local_document.pdf" trong cùng thư mục với script này
    # và thêm vào danh sách:
    # sample_document_paths.append("my_local_document.pdf")

    # Kiểm tra nếu chưa có tệp cục bộ nào được thêm vào và các URL mẫu không phải là thật
    if not sample_document_paths:
        print("Vui lòng cung cấp ít nhất một đường dẫn tài liệu (cục bộ hoặc URL) để phân tích.")
    else:
        markdown_output = process_multiple_documents(sample_document_paths)
        pattern = r"===\s*END_BANG_CHI_TIET===\s*?[\s\n]+?===\s*START_BANG_CHI_TIET==="
        # Thay thế bằng chuỗi rỗng để nối các bảng lại
        chuoi_da_xu_ly = re.sub(pattern, "", markdown_output, flags=re.DOTALL)

        print(chuoi_da_xu_ly)

        # Bạn có thể lưu kết quả Markdown vào một tệp:
        # with open("analysis_results.md", "w", encoding="utf-8") as f:
        #     f.write(markdown_output)
        # print("\nKết quả đã được lưu vào tệp analysis_results.md")

