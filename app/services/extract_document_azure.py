import os
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult, DocumentTable, DocumentLine, AnalyzeDocumentRequest, DocumentContentFormat
from azure.core.exceptions import HttpResponseError

# Thay thế bằng Endpoint và API Key của tài nguyên Azure AI Document Intelligence của bạn
# Luôn khuyến nghị lưu trữ các thông tin này trong biến môi trường để bảo mật
# Ví dụ: endpoint = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
# Ví dụ: key = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_API_KEY")
endpoint = "https://aidocum.cognitiveservices.azure.com/"
key = "F6VC9nbyCdbmTw5v2bxLuAbTGFeoiHhQu5KoJs5AgOCzJe2hwHazJQQJ99BEACqBBLyXJ3w3AAALACOGnZLn"

# Hàm format_table_to_markdown không còn cần thiết vì chúng ta sẽ yêu cầu đầu ra Markdown trực tiếp từ dịch vụ.
# def format_table_to_markdown(table: DocumentTable) -> str:
#     """
#     Định dạng một đối tượng DocumentTable thành chuỗi Markdown.
#     """
#     markdown_output = ""
    
#     # Tạo một mảng 2D để lưu trữ nội dung ô, giúp dễ dàng định dạng bảng
#     # Khởi tạo với chuỗi rỗng
#     table_data = [["" for _ in range(table.column_count)] for _ in range(table.row_count)]

#     # Điền nội dung ô vào mảng 2D
#     for cell in table.cells:
#         if 0 <= cell.row_index < table.row_count and 0 <= cell.column_index < table.column_count:
#             table_data[cell.row_index][cell.column_index] = cell.content or "" # Đảm bảo không phải None

#     # Xác định độ rộng tối đa cho mỗi cột để căn chỉnh
#     column_widths = [0] * table.column_count
#     for r_idx in range(table.row_count):
#         for c_idx in range(table.column_count):
#             column_widths[c_idx] = max(column_widths[c_idx], len(table_data[r_idx][c_idx]))

#     # In hàng tiêu đề (giả định hàng đầu tiên là tiêu đề)
#     # Nếu bảng có ít nhất một hàng
#     if table.row_count > 0:
#         header_row_content = table_data[0]
#         header_row_markdown = "| " + " | ".join([cell.ljust(column_widths[i]) for i, cell in enumerate(header_row_content)]) + " |"
#         markdown_output += header_row_markdown + "\n"

#         # In hàng phân cách
#         separator_row_markdown = "| " + " | ".join(["-" * column_widths[i] for i in range(table.column_count)]) + " |"
#         markdown_output += separator_row_markdown + "\n"

#         # In các hàng dữ liệu (bắt đầu từ hàng thứ hai)
#         for r_idx in range(1, table.row_count):
#             data_row_content = table_data[r_idx]
#             data_row_markdown = "| " + " | ".join([cell.ljust(column_widths[i]) for i, cell in enumerate(data_row_content)]) + " |"
#             markdown_output += data_row_markdown + "\n"

#     return markdown_output

def analyze_document_and_format_markdown(document_path: str, client: DocumentIntelligenceClient) -> str:
    """
    Phân tích một tài liệu và trả về kết quả dưới dạng chuỗi Markdown.
    Hỗ trợ cả đường dẫn cục bộ và URL, sử dụng đầu ra Markdown trực tiếp từ dịch vụ.
    """
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
        print(result)
        print("-------------------")
        # --- Trích xuất và định dạng văn bản và bảng (đã có sẵn trong result.content) ---
        #markdown_result += "### Nội dung trích xuất (định dạng Markdown):\n"
        if result.content:
            markdown_result += result.content
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
        "D:\\5.jpg",
        "D:\\6.jpg",
        "D:\\7.jpg",
        "D:\\8.jpg",
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
        print(markdown_output)

        # Bạn có thể lưu kết quả Markdown vào một tệp:
        # with open("analysis_results.md", "w", encoding="utf-8") as f:
        #     f.write(markdown_output)
        # print("\nKết quả đã được lưu vào tệp analysis_results.md")
