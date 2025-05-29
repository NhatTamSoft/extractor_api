from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def tim_kiem_tuong_dong(chuoi_can_tim, danh_sach_du_lieu, nguong_diem=0.7):
    """
    Tìm kiếm các mục trong danh sách dữ liệu có độ tương đồng văn bản 
    lớn hơn hoặc bằng một ngưỡng cho trước so với chuỗi tìm kiếm.

    Args:
        chuoi_can_tim (str): Chuỗi văn bản cần tìm kiếm.
        danh_sach_du_lieu (list): Danh sách các dictionary, mỗi dictionary 
                                chứa dữ liệu mẫu (ví dụ: {'MaKMCP': ..., 'TenKMCP': ...}).
        nguong_diem (float, optional): Ngưỡng điểm tương đồng (từ 0 đến 1). 
                                     Mặc định là 0.7.

    Returns:
        list: Danh sách các dictionary chứa mục phù hợp và điểm số tương đồng.
              Ví dụ: [{'ket_qua': {'MaKMCP': ..., 'TenKMCP': ...}, 'diem_so': ...}]
    """
    # Bước 1: Trích xuất các chuỗi văn bản từ danh sách dữ liệu mẫu
    # và tạo một kho văn bản (corpus) để tính toán
    cac_chuoi_mau = [list(muc.values())[1] for muc in danh_sach_du_lieu]
    print("danh_sach_du_lieu")
    print(danh_sach_du_lieu)
    # Thêm chuỗi cần tìm vào đầu danh sách để vector hóa cùng lúc
    kho_van_ban = [chuoi_can_tim] + cac_chuoi_mau

    # Bước 2: Khởi tạo và sử dụng TfidfVectorizer
    # TfidfVectorizer sẽ chuyển đổi kho văn bản thành một ma trận các vector TF-IDF.
    # TF-IDF đánh giá tầm quan trọng của một từ trong một văn bản so với toàn bộ kho văn bản.
    vectorizer = TfidfVectorizer()
    ma_tran_tfidf = vectorizer.fit_transform(kho_van_ban)

    # Bước 3: Tính toán độ tương đồng cosine
    # Chúng ta sẽ tính độ tương đồng giữa vector của chuỗi cần tìm (vector đầu tiên)
    # và tất cả các vector của dữ liệu mẫu (các vector còn lại).
    # cosine_similarity trả về một ma trận, ta lấy hàng đầu tiên.
    diem_tuong_dong = cosine_similarity(ma_tran_tfidf[0:1], ma_tran_tfidf[1:])
    
    # Bước 4: Lọc kết quả dựa trên ngưỡng điểm
    ket_qua_phu_hop = []
    # Lặp qua các điểm số tương đồng đã tính được
    for i, diem in enumerate(diem_tuong_dong[0]):
        if diem >= nguong_diem:
            ket_qua_phu_hop.append(danh_sach_du_lieu[i])
            break # chỉ lấy 1 kết quả duy nhất
            
    # Sắp xếp kết quả theo điểm số giảm dần để mục tương đồng nhất lên đầu
    if ket_qua_phu_hop:
        return {
            'success': 1,
            'results': ket_qua_phu_hop
        }
        #{'success': 1, 'results': [{'MaKMCP': 'CP2', 'TenKMCP': 'Chi phí xây dựng'}]}
    else:
        return { 
            'success': 0,
            'results': { }, 
            'score': 0
        }

# --- Ví dụ sử dụng ---
if __name__ == "__main__":
    # Dữ liệu mẫu (định dạng list của các dict)
    du_lieu_mau = [
        {'MaKMCP': 'CP1', 'TenKMCP': 'Chi phí bồi thường, hỗ trợ, tái định cư'},
        {'MaKMCP': 'CP101', 'TenKMCP': 'Chi phí bồi thường về đất, nhà, công trình trên đất, các tài sản gắn liền với đất, trên mặt nước và chi phí bồi thường khác'},
        {'MaKMCP': 'CP102', 'TenKMCP': 'Chi phí các khoản hỗ trợ khi nhà nước thu hồi đất'},
        {'MaKMCP': 'CP103', 'TenKMCP': 'Chi phí tái định cư'},
        {'MaKMCP': 'CP104', 'TenKMCP': 'Chi phí tổ chức bồi thường, hỗ trợ và tái định cư'},
        {'MaKMCP': 'CP105', 'TenKMCP': 'Chi phí sử dụng đất, thuê đất tính trong thời gian xây dựng'},
        {'MaKMCP': 'CP106', 'TenKMCP': 'Chi phí di dời, hoàn trả cho phần hạ tầng kỹ thuật đã được đầu tư xây dựng phục vụ giải phóng mặt bằng'},
        {'MaKMCP': 'CP107', 'TenKMCP': 'Chi phí đầu tư vào đất'},
        {'MaKMCP': 'CP199', 'TenKMCP': 'Chi phí khác có liên quan đến công tác bồi thường, hỗ trợ và tái định cư'},
        {'MaKMCP': 'CP2', 'TenKMCP': 'Chi phí xây dựng'},
        {'MaKMCP': 'CP202', 'TenKMCP': 'Chi phí xây dựng công trình chính'},
        {'MaKMCP': 'CP203', 'TenKMCP': 'Chi phí xây dựng công trình chính và phụ'},
    ]

    # Chuỗi cần tìm kiếm
    chuoi_tim = "Chi phí xây dựng"

    # Gọi hàm tìm kiếm
    ket_qua = tim_kiem_tuong_dong(chuoi_tim, du_lieu_mau, nguong_diem=0.5) # Dùng ngưỡng thấp hơn để thấy nhiều kết quả hơn

    # In kết quả
    print(ket_qua)