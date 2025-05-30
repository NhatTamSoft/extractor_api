from sentence_transformers import SentenceTransformer, util
import pandas as pd
import torch

def tim_kiem_tuong_dong(chuoi_can_tim, danh_sach_du_lieu, nguong_diem=0.7, model_name='all-MiniLM-L6-v2'):
    """
    Tìm kiếm các mục trong DataFrame có độ tương đồng văn bản
    lớn hơn hoặc bằng một ngưỡng cho trước so với chuỗi tìm kiếm, sử dụng SentenceTransformer.

    Args:
        chuoi_can_tim (str): Chuỗi văn bản cần tìm kiếm.
        danh_sach_du_lieu (DataFrame): DataFrame chứa dữ liệu mẫu với các cột như MaKMCP, TenKMCP.
                                       Cột chứa văn bản để so sánh được giả định là cột thứ hai (index 1).
        model_name (str, optional): Tên của mô hình SentenceTransformer_new_code_start_1716956761171_end_1716956761171.
                                    Mặc định là 'all-MiniLM-L6-v2'.
                                    Một số mô hình tiếng Việt tốt có thể là 'VoVanPhuc/sup-SimCSE-VietNamese-phobert-base'
                                    hoặc 'bkai-foundation-models/vietnamese-bi-encoder'.
        nguong_diem (float, optional): Ngưỡng điểm tương đồng (từ 0 đến 1).
                                     Mặc định là 0.7.

    Returns:
        dict: Dictionary chứa kết quả tìm kiếm và trạng thái thành công.
              Ví dụ: {'success': 1, 'results': [{'MaKMCP': ..., 'TenKMCP': ..., 'score': ...}]}
    """
    # Bước 1: Khởi tạo mô hình SentenceTransformer
    # Kiểm tra xem GPU có sẵn không và sử dụng nếu có
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Sử dụng thiết bị: {device}")
    model = SentenceTransformer(model_name, device=device)

    # Bước 2: Trích xuất các chuỗi văn bản từ DataFrame
    # Giả định cột thứ hai (index 1) trong DataFrame chứa văn bản cần so sánh (ví dụ: 'TenKMCP')
    if danh_sach_du_lieu.empty or len(danh_sach_du_lieu.columns) < 2:
        print("DataFrame dữ liệu mẫu trống hoặc không có đủ cột.")
        return {
            'success': 0,
            'results': [],
            'message': 'DataFrame dữ liệu mẫu trống hoặc không có đủ cột.'
        }

    # Lấy tên cột thứ hai để sử dụng nhất quán
    cot_van_ban = danh_sach_du_lieu.columns[1]
    cac_chuoi_mau = danh_sach_du_lieu[cot_van_ban].tolist()

    if not cac_chuoi_mau:
        print("Không có chuỗi mẫu nào trong DataFrame.")
        return {
            'success': 0,
            'results': [],
            'message': 'Không có chuỗi mẫu nào trong DataFrame.'
        }

    # Bước 3: Tạo embeddings cho chuỗi cần tìm và các chuỗi mẫu
    # Sử dụng batch_size lớn hơn để tăng tốc độ nếu có nhiều chuỗi mẫu
    embedding_chuoi_can_tim = model.encode(chuoi_can_tim, convert_to_tensor=True)
    embeddings_cac_chuoi_mau = model.encode(cac_chuoi_mau, convert_to_tensor=True, batch_size=64, show_progress_bar=True)

    # Bước 4: Tính toán độ tương đồng cosine
    # util.pytorch_cos_sim hoặc util.cos_sim đều có thể sử dụng
    diem_tuong_dong = util.pytorch_cos_sim(embedding_chuoi_can_tim, embeddings_cac_chuoi_mau)

    # Bước 5: Lọc kết quả dựa trên ngưỡng điểm
    ket_qua_phu_hop = []
    # Lặp qua các điểm số tương đồng đã tính được
    # diem_tuong_dong là một tensor 2D (1xN), nên ta lấy hàng đầu tiên diem_tuong_dong[0]
    for i, diem in enumerate(diem_tuong_dong[0]):
        diem_float = diem.item() # Chuyển tensor scalar sang float
        if diem_float >= nguong_diem:
            # Lấy dòng tương ứng từ DataFrame và chuyển thành dictionary
            ket_qua_item = danh_sach_du_lieu.iloc[i].to_dict()
            ket_qua_item['score'] = round(diem_float, 4) # Thêm điểm số vào kết quả
            ket_qua_phu_hop.append(ket_qua_item)
            # Nếu chỉ muốn lấy kết quả đầu tiên phù hợp, bỏ comment dòng dưới
            # break

    # Sắp xếp kết quả theo điểm số giảm dần (tùy chọn)
    ket_qua_phu_hop = sorted(ket_qua_phu_hop, key=lambda x: x['score'], reverse=True)

    # Trả về kết quả
    if ket_qua_phu_hop:
        
        return {
            'success': 1,
            'results': [ket_qua_phu_hop[0]] if ket_qua_phu_hop else []
        }
    else:
        # Tìm điểm cao nhất nếu không có kết quả nào vượt ngưỡng
        highest_score = 0.0
        if diem_tuong_dong.numel() > 0 : # Kiểm tra xem tensor có phần tử nào không
             highest_score = round(torch.max(diem_tuong_dong[0]).item(), 4) if diem_tuong_dong[0].numel() > 0 else 0.0

        return {
            'success': 0,
            'results': [],
            'message': f'Không tìm thấy kết quả phù hợp với ngưỡng {nguong_diem}. Điểm cao nhất là {highest_score}.',
            'highest_score': highest_score
        }

# --- Ví dụ sử dụng ---
if __name__ == "__main__":
    # Dữ liệu mẫu (định dạng DataFrame)
    du_lieu_mau_df = pd.DataFrame([
        {'MaKMCP': 'CP2', 'TenKMCP': 'Chi phí xây dựng'}
    ])

    # Chuỗi cần tìm kiếm
    chuoi_tim = "Chi phí xây dựng"
    # chuoi_tim_2 = "Thẩm định dự án đầu tư xây dựng"

    print(f"--- Tìm kiếm cho: '{chuoi_tim}' ---")
    # Sử dụng mô hình mặc định (tiếng Anh, đa ngôn ngữ cơ bản)
    ket_qua_default = tim_kiem_tuong_dong(chuoi_tim, du_lieu_mau_df, nguong_diem=0.5, model_name='VoVanPhuc/sup-SimCSE-VietNamese-phobert-base')
    print("Kết quả (mô hình default 'all-MiniLM-L6-v2'):")
    if ket_qua_default['success']:
        for res in ket_qua_default['results']:
            print(f"  {res['MaKMCP']}: {res['TenKMCP']} (Score: {res['score']})")
    else:
        print(f"  {ket_qua_default['message']}")
    print("-" * 30)
