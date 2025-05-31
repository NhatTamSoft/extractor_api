import json
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import os

# Azure credentials
endpoint = "https://aidocum.cognitiveservices.azure.com/"
azure_key = "F6VC9nbyCdbmTw5v2bxLuAbTGFeoiHhQu5KoJs5AgOCzJe2hwHazJQQJ99BEACqBBLyXJ3w3AAALACOGnZLn"

# Initialize Azure client
azure_client = DocumentAnalysisClient(endpoint, AzureKeyCredential(azure_key))

def read_text_from_images_azure(image_files):
    """
    Xử lý danh sách các file hình ảnh, trích xuất văn bản và bảng.
    Bảng sẽ được định dạng theo cú pháp Markdown.

    Args:
        image_files: Danh sách đường dẫn đến các file hình ảnh.

    Returns:
        Một chuỗi chứa văn bản đã trích xuất và các bảng đã được định dạng Markdown.
    """
    duLieuText = ""  # Chuỗi để lưu trữ kết quả đầu ra
    for file_index, file_name in enumerate(image_files):
        #duLieuText += f"\n--- Đang xử lý file {file_index + 1}: {os.path.basename(file_name)} ---\n"
        if not os.path.exists(file_name):
            duLieuText += f"LỖI: File không tồn tại: {file_name}\n"
            continue
            
        # Trích xuất dữ liệu với Azure Form Recognizer
        result_dict = {"text": [], "tables": []}
        try:
            with open(file_name, "rb") as f:
                # Sử dụng model "prebuilt-layout" để trích xuất văn bản, bảng, và cấu trúc
                poller = azure_client.begin_analyze_document("prebuilt-layout", document=f)
                result = poller.result()

            # Thu thập văn bản từ các trang
            for page in result.pages:
                for line in page.lines:
                    result_dict["text"].append(line.content)

            # Thu thập và xử lý bảng
            for table_idx, table in enumerate(result.tables):
                table_data = {
                    "row_count": table.row_count,
                    "column_count": table.column_count,
                    "rows": []
                }
                
                # Sắp xếp các ô theo thứ tự hàng và cột để đảm bảo đúng cấu trúc
                # Điều này quan trọng vì API có thể trả về các ô không theo thứ tự trực quan
                cells = sorted(table.cells, key=lambda cell: (cell.row_index, cell.column_index))
                
                current_row_index = -1
                row_cells_list_for_table = [] 
                current_row_cells = [] 

                for cell_obj in cells:
                    # Nếu ô này bắt đầu một hàng mới
                    if cell_obj.row_index > current_row_index:
                        if current_row_cells: 
                            # Đảm bảo hàng có đủ số cột, đệm bằng chuỗi rỗng nếu cần
                            while len(current_row_cells) < table.column_count:
                                 current_row_cells.append("")
                            row_cells_list_for_table.append(current_row_cells)
                        
                        current_row_cells = [] # Bắt đầu một danh sách mới cho hàng mới
                        current_row_index = cell_obj.row_index
                        
                        # Đệm bằng chuỗi rỗng cho bất kỳ cột nào bị bỏ qua ở đầu hàng mới
                        for _ in range(cell_obj.column_index):
                            current_row_cells.append("")
                    
                    # Đệm bằng chuỗi rỗng cho bất kỳ cột nào bị bỏ qua ở giữa hàng
                    while len(current_row_cells) < cell_obj.column_index:
                        current_row_cells.append("")
                    
                    current_row_cells.append(cell_obj.content if cell_obj.content else "")

                # Thêm hàng cuối cùng đã xử lý
                if current_row_cells:
                    # Đảm bảo hàng cuối cùng cũng có số cột chính xác
                    while len(current_row_cells) < table.column_count: 
                        current_row_cells.append("")
                    row_cells_list_for_table.append(current_row_cells)
                
                table_data["rows"] = row_cells_list_for_table
                result_dict["tables"].append(table_data)

        except Exception as e:
            duLieuText += f"LỖI khi xử lý file {file_name}: {str(e)}\n"
            continue

        # Xác định file dựa trên bảng hay văn bản
        is_table_file = len(result_dict["tables"]) > 0
        
        # Hiển thị và lưu kết quả dựa trên loại nội dung
        if is_table_file:
            #duLieuText += f"\n**Các bảng đã trích xuất từ {os.path.basename(file_name)}:**\n"
            for i, table_content in enumerate(result_dict["tables"], 1):
                duLieuText += f"\n### Bảng:\n"
                rows = table_content["rows"]
                if not rows:
                    duLieuText += "Bảng này không có dữ liệu.\n"
                    continue
                # Lấy hàng đầu tiên làm tiêu đề
                header = rows[0]
                # Thay thế ký tự "|" trong nội dung ô để không làm hỏng cú pháp Markdown
                duLieuText += "| " + " | ".join(str(cell).replace("|", "\\|") for cell in header) + " |\n"
                
                # Tạo dòng phân cách cho Markdown
                duLieuText += "| " + " | ".join(["---"] * len(header)) + " |\n"
                
                # Thêm các hàng dữ liệu còn lại
                for row in rows[1:]:
                    processed_row = [str(cell).replace("|", "\\|") for cell in row]
                    duLieuText += "| " + " | ".join(processed_row) + " |\n"
        
        # Nếu có văn bản ngoài bảng, hoặc không có bảng nào
        else:
            #duLieuText += f"\n**Văn bản đã trích xuất từ {os.path.basename(file_name)}:**\n"
            duLieuText += "\n".join(result_dict["text"]) + "\n"

    return duLieuText

# Ví dụ sử dụng:
if __name__ == "__main__":
    # Danh sách các file hình ảnh cần xử lý
    image_files = [
        "D:/ProjectGoc/GitLab/FAST_API_QLDA_fn/image_storage/1-2025-05-26 8.36.53 AM.jpg",
        "D:/ProjectGoc/GitLab/FAST_API_QLDA_fn/image_storage/2-2025-05-26 8.36.44 AM.jpg",
        "D:/ProjectGoc/GitLab/FAST_API_QLDA_fn/image_storage/3-2025-05-26 8.36.49 AM.jpg",
        "D:/ProjectGoc/GitLab/FAST_API_QLDA_fn/image_storage/4-2025-05-26 8.36.38 AM.jpg",
        # Thêm các file khác vào đây
    ]
    print(read_text_from_images(image_files))