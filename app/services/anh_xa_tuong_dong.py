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
    # print(f"Sử dụng thiết bị: {device}")
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
    {
        "MaKMCP": "CP701",
        "TenKMCP": "Chi phí dự phòng cho khối lượng, công việc phát sinh"
    },
    {
        "MaKMCP": "CP58231",
        "TenKMCP": "Chi phí thẩm tra thiết kế bản vẽ thi công (BVTC) (Phát sinh)"
    },
    {
        "MaKMCP": "CP514",
        "TenKMCP": "Chi phí lập HSMT (HSYC), đánh giá HSDT (HSĐX) thi công xây dựng"
    },
    {
        "MaKMCP": "CP537",
        "TenKMCP": "Phí thẩm định kết quả lựa chọn nhà thầu tư vấn đầu tư xây dựng"
    },
    {
        "MaKMCP": "CP228",
        "TenKMCP": "Chi phí xây dựng khác"
    },
    {
        "MaKMCP": "CP535",
        "TenKMCP": "Phí thẩm định kết quả lựa chọn nhà thầu thi công xây dựng"
    },
    {
        "MaKMCP": "CP617",
        "TenKMCP": "Chi phí đo đạc địa chính"
    },
    {
        "MaKMCP": "CP508",
        "TenKMCP": "Chi phí thẩm tra báo cáo nghiên cứu khả thi"
    },
    {
        "MaKMCP": "CP557",
        "TenKMCP": "Chi phí thử tĩnh"
    },
    {
        "MaKMCP": "CP104",
        "TenKMCP": "Chi phí tổ chức bồi thường, hỗ trợ và tái định cư"
    },
    {
        "MaKMCP": "CP519",
        "TenKMCP": "Chi phí đánh giá HSDT (HSĐX) mua sắm vật tư, thiết bị"
    },
    {
        "MaKMCP": "CP106",
        "TenKMCP": "Chi phí di dời, hoàn trả cho phần hạ tầng kỹ thuật đã được đầu tư xây dựng phục vụ giải phóng mặt bằng"
    },
    {
        "MaKMCP": "CP506",
        "TenKMCP": "Chi phí lập nhiệm vụ khảo sát xây dựng"
    },
    {
        "MaKMCP": "CP532",
        "TenKMCP": "Phí thẩm định hồ sơ mời thầu (hồ sơ yêu cầu) gói thầu thi công xây dựng"
    },
    {
        "MaKMCP": "CP570",
        "TenKMCP": "Chi phí nội đồng nghệ thuật"
    },
    {
        "MaKMCP": "CP56306",
        "TenKMCP": "Chi phí khảo sát địa hình  (Bước lập thiết kế bản vẽ thi công - dự toán (BVTC-DT))"
    },
    {
        "MaKMCP": "CP504",
        "TenKMCP": "Chi phí thiết kế xây dựng"
    },
    {
        "MaKMCP": "CP566",
        "TenKMCP": "Chi phí lập báo cáo đánh giá tác động môi trường"
    },
    {
        "MaKMCP": "CP56303",
        "TenKMCP": "Chi phí khảo sát địa hình (Bước lập báo cáo nghiên cứu khả thi (NCKT))"
    },
    {
        "MaKMCP": "CP57401",
        "TenKMCP": "Chi phí thẩm tra dự toán phát sinh"
    },
    {
        "MaKMCP": "CP527",
        "TenKMCP": "Chi phí thẩm tra báo cáo nghiên cứu tiền khả thi"
    },
    {
        "MaKMCP": "CP51611",
        "TenKMCP": "Chi phí đánh giá hồ sơ dự thầu (hồ sơ đề xuất) thi công xây dựng (Phát sinh)"
    },
    {
        "MaKMCP": "CP509",
        "TenKMCP": "Chi phí thẩm tra thiết kế xây dựng"
    },
    {
        "MaKMCP": "CP52803",
        "TenKMCP": "Chi phí khảo sát (Bước lập báo cáo nghiên cứu khả thi (NCKT))"
    },
    {
        "MaKMCP": "CP511",
        "TenKMCP": "Chi phí lập hồ sơ mời thầu (hồ sơ yêu cầu), đánh giá hồ sơ dự thầu (hồ sơ đề xuât) tư vấn"
    },
    {
        "MaKMCP": "CP5",
        "TenKMCP": "Chi phí tư vấn đầu tư xây dựng"
    },
    {
        "MaKMCP": "CP609",
        "TenKMCP": "Chi phí kiểm toán độc lập"
    },
    {
        "MaKMCP": "CP50420",
        "TenKMCP": "Chi phí thiết kế kỹ thuật"
    },
    {
        "MaKMCP": "CP619",
        "TenKMCP": "Chi phí lán trại"
    },
    {
        "MaKMCP": "CP610",
        "TenKMCP": "Chi phí bảo hiểm"
    },
    {
        "MaKMCP": "CP560",
        "TenKMCP": "Chi phí kiểm định chất lượng phục vụ công tác nghiệm thu"
    },
    {
        "MaKMCP": "CP614",
        "TenKMCP": "Chi phí di dời điện"
    },
    {
        "MaKMCP": "CP512",
        "TenKMCP": "Chi phí lập hồ sơ mời thầu (hồ sơ yêu cầu) tư vấn"
    },
    {
        "MaKMCP": "CP56205",
        "TenKMCP": "Chi phí khảo sát địa chất (Bước lập thiết kế bản vẽ thi công (BVTC))"
    },
    {
        "MaKMCP": "CP52099",
        "TenKMCP": "Chi phí giám sát thi công xây dựng (Phát sinh)"
    },
    {
        "MaKMCP": "CP321",
        "TenKMCP": "Chi phí thiết bị phát sinh"
    },
    {
        "MaKMCP": "CP225",
        "TenKMCP": "Chi phí xây dựng công trình chính"
    },
    {
        "MaKMCP": "CP6",
        "TenKMCP": "Chi phí khác"
    },
    {
        "MaKMCP": "CP62101",
        "TenKMCP": "Chi phí điều tiết giao thông khác"
    },
    {
        "MaKMCP": "CP578",
        "TenKMCP": "Chi phí chuyển giao công nghệ"
    },
    {
        "MaKMCP": "CP505",
        "TenKMCP": "Chi phí thiết kế bản vẽ thi công"
    },
    {
        "MaKMCP": "CP56201",
        "TenKMCP": "Chi phí khảo sát địa chất"
    },
    {
        "MaKMCP": "CP51811",
        "TenKMCP": "Chi phí lập HSMT (HSYC) mua sắm vật tư, thiết bị (Phát sinh)"
    },
    {
        "MaKMCP": "CP605",
        "TenKMCP": "Chi phí thẩm định giá thiết bị"
    },
    {
        "MaKMCP": "CP608",
        "TenKMCP": "Chi phí kiểm tra công tác nghiệm thu"
    },
    {
        "MaKMCP": "CP103",
        "TenKMCP": "Chi phí tái định cư"
    },
    {
        "MaKMCP": "CP623",
        "TenKMCP": "Chi phí thẩm định thiết kế bản vẽ thi công, lệ phí thẩm định báo cáo kinh tế kỹ thuật (KTKT)"
    },
    {
        "MaKMCP": "CP7",
        "TenKMCP": "Chi phí dự phòng"
    },
    {
        "MaKMCP": "CP540",
        "TenKMCP": "Phí thẩm định hồ sơ mời thầu (hồ sơ yêu cầu), đánh giá kết quả lựa chọn nhà thầu (hồ sơ đề xuất) tư vấn đầu tư xây dựng"
    },
    {
        "MaKMCP": "CP199",
        "TenKMCP": "Chi phí khác có liên quan đến công tác bồi thường, hỗ trợ và tái định cư"
    },
    {
        "MaKMCP": "CP50301",
        "TenKMCP": "Chi phí lập dự án đầu tư"
    },
    {
        "MaKMCP": "CP507",
        "TenKMCP": "Chi phí thẩm tra báo cáo kinh tế - kỹ thuật"
    },
    {
        "MaKMCP": "CP223",
        "TenKMCP": "Chi phí xây dựng sau thuế"
    },
    {
        "MaKMCP": "CP533",
        "TenKMCP": "Phí thẩm định hồ sơ mời thầu (hồ sơ yêu cầu) gói thầu lắp đặt thiết bị"
    },
    {
        "MaKMCP": "CP222",
        "TenKMCP": "Chi phí xây dựng trước thuế"
    },
    {
        "MaKMCP": "CP528",
        "TenKMCP": "Chi phí khảo sát xây dựng"
    },
    {
        "MaKMCP": "CP584",
        "TenKMCP": "Chi phí đăng báo đấu thầu"
    },
    {
        "MaKMCP": "CP56301",
        "TenKMCP": "Chi phí khảo sát địa hình"
    },
    {
        "MaKMCP": "CP50431",
        "TenKMCP": "Chi phí thiết kế kỹ thuật (Phát sinh)"
    },
    {
        "MaKMCP": "CP630",
        "TenKMCP": "Lệ phí thẩm tra thiết kế"
    },
    {
        "MaKMCP": "CP50530",
        "TenKMCP": "Chi phí lập thiết kế bản vẽ thi công - dự toán"
    },
    {
        "MaKMCP": "CP51711",
        "TenKMCP": "Chi phí lập HSMT (HSYC), đánh giá HSDT (HSĐX) mua sắm vật tư, thiết bị (Phát sinh)"
    },
    {
        "MaKMCP": "CP61703",
        "TenKMCP": "Chi phí đo đạc, đền bù giải phóng mặt bằng (GPMB)"
    },
    {
        "MaKMCP": "CP620",
        "TenKMCP": "Chi phí đảm bảo giao thông"
    },
    {
        "MaKMCP": "CP622",
        "TenKMCP": "Chi phí một số công tác không xác định số lượng từ thiết kế"
    },
    {
        "MaKMCP": "CP62501",
        "TenKMCP": "Chi phí giám sát đánh giá đầu tư"
    },
    {
        "MaKMCP": "CP567",
        "TenKMCP": "Chi phí thí nghiệm đối chứng, kiểm định xây dựng, thử nghiệm khả năng chịu lực của công trình"
    },
    {
        "MaKMCP": "CP572",
        "TenKMCP": "Chi phí hoạt động của Hội đồng nghệ thuật"
    },
    {
        "MaKMCP": "CP633",
        "TenKMCP": "Chi phí thẩm định phê duyệt quyết toán"
    },
    {
        "MaKMCP": "CP3",
        "TenKMCP": "Chi phí thiết bị"
    },
    {
        "MaKMCP": "CP631",
        "TenKMCP": "Phí thẩm định lựa chọn nhà thầu"
    },
    {
        "MaKMCP": "CP539",
        "TenKMCP": "Phí thẩm định hồ sơ mời thầu (hồ sơ yêu cầu), đánh giá kết quả lựa chọn nhà thầu (hồ sơ đề xuất) lắp đặt thiết bị"
    },
    {
        "MaKMCP": "CP621",
        "TenKMCP": "Chi phí điều tiết giao thông"
    },
    {
        "MaKMCP": "CP52802",
        "TenKMCP": "Chi phí khảo sát (Bước lập báo cáo nghiên cứu tiền khả thi (NCTKT))"
    },
    {
        "MaKMCP": "CP634",
        "TenKMCP": "Chi phí thẩm định báo cáo nghiên cứu khả thi"
    },
    {
        "MaKMCP": "CP50541",
        "TenKMCP": "Chi phí lập thiết kế bản vẽ thi công - dự toán (Phát sinh)"
    },
    {
        "MaKMCP": "CP552",
        "TenKMCP": "Chi phí nhiệm vụ thử tỉnh cọc"
    },
    {
        "MaKMCP": "CP62701",
        "TenKMCP": "Chi phí khoan địa chất"
    },
    {
        "MaKMCP": "CP574",
        "TenKMCP": "Chi phí tư vấn thẩm tra dự toán"
    },
    {
        "MaKMCP": "CP61404",
        "TenKMCP": "Chi phí di dời nước"
    },
    {
        "MaKMCP": "CP632",
        "TenKMCP": "Chi phí thẩm tra quyết toán"
    },
    {
        "MaKMCP": "CP61099",
        "TenKMCP": "Chi phí bảo hiểm (Phát sinh)"
    },
    {
        "MaKMCP": "CP561",
        "TenKMCP": "Chi phí cắm mốc ranh giải phóng mặt bằng"
    },
    {
        "MaKMCP": "CP541",
        "TenKMCP": "Phí thẩm định hồ sơ mời thầu (hồ sơ yêu cầu), đánh giá kết quả lựa chọn nhà thầu (hồ sơ đề xuất)"
    },
    {
        "MaKMCP": "CP56203",
        "TenKMCP": "Chi phí khảo sát địa chất (Bước lập báo cáo nghiên cứu khả thi (NCKT))"
    },
    {
        "MaKMCP": "CP51011",
        "TenKMCP": "Chi phí thẩm tra dự toán xây dựng (Phát sinh)"
    },
    {
        "MaKMCP": "CP522",
        "TenKMCP": "Chi phí giám sát công tác khảo sát xây dựng"
    },
    {
        "MaKMCP": "CP575",
        "TenKMCP": "Chi phí thẩm định dự toán giá gói thầu"
    },
    {
        "MaKMCP": "CP56305",
        "TenKMCP": "Chi phí khảo sát địa hình  (Bước lập thiết kế bản vẽ thi công (BVTC))"
    },
    {
        "MaKMCP": "CP513",
        "TenKMCP": "Chi phí đánh giá hồ sơ dự thầu (hồ sơ đề xuất) tư vấn"
    },
    {
        "MaKMCP": "CP521",
        "TenKMCP": "Chi phí giám sát lắp đặt thiết bị"
    },
    {
        "MaKMCP": "CP56401",
        "TenKMCP": "Chi phí khảo sát địa, địa hình"
    },
    {
        "MaKMCP": "CP60999",
        "TenKMCP": "Chi phí kiểm toán độc lập (Phát sinh)"
    },
    {
        "MaKMCP": "CP536",
        "TenKMCP": "Phí thẩm định kết quả lựa chọn nhà thầu lắp đặt thiết bị"
    },
    {
        "MaKMCP": "CP615",
        "TenKMCP": "Phí thẩm tra di dời điện"
    },
    {
        "MaKMCP": "CP582",
        "TenKMCP": "Chi phí thẩm tra thiết kế bản vẽ thi công - dự toán (BVTC-DT)"
    },
    {
        "MaKMCP": "CP628",
        "TenKMCP": "Chi phí thẩm định đồ án quy hoạch"
    },
    {
        "MaKMCP": "CP503",
        "TenKMCP": "Chi phí lập báo cáo kinh tế - kỹ thuật"
    },
    {
        "MaKMCP": "CP56304",
        "TenKMCP": "Chi phí khảo sát địa hình  (Bước lập báo cáo kinh tế kỹ thuật (KTKT))"
    },
    {
        "MaKMCP": "CP56111",
        "TenKMCP": "Chi phí lập đồ án quy hoạch"
    },
    {
        "MaKMCP": "CP607",
        "TenKMCP": "Chi phí thẩm tra, phê duyệt quyết toán"
    },
    {
        "MaKMCP": "CP553",
        "TenKMCP": "Công tác điều tra, đo đạt và thu thập số liệu"
    },
    {
        "MaKMCP": "CP612",
        "TenKMCP": "Chi phí bảo hành, bảo trì"
    },
    {
        "MaKMCP": "CP61401",
        "TenKMCP": "Chi phí di dời hệ thống điện chiếu sáng"
    },
    {
        "MaKMCP": "CP580",
        "TenKMCP": "Chi phí tư vấn giám sát"
    },
    {
        "MaKMCP": "CP61820",
        "TenKMCP": "Chi phí tổ chức kiểm tra công tác nghiệm thu"
    },
    {
        "MaKMCP": "CP538",
        "TenKMCP": "Phí thẩm định hồ sơ mời thầu (hồ sơ yêu cầu), đánh giá kết quả lựa chọn nhà thầu (hồ sơ đề xuất) xây lắp"
    },
    {
        "MaKMCP": "CP102",
        "TenKMCP": "Chi phí các khoản hỗ trợ khi nhà nước thu hồi đất"
    },
    {
        "MaKMCP": "CP611",
        "TenKMCP": "Chi phí thẩm định báo cáo đánh giá tác động môi trường"
    },
    {
        "MaKMCP": "CP563",
        "TenKMCP": "Chi phí thẩm tra tính hiệu quả, tính khả thi của dự án"
    },
    {
        "MaKMCP": "CP626",
        "TenKMCP": "Chi phí thẩm định kết quả lựa chọn nhà thầu"
    },
    {
        "MaKMCP": "CP601",
        "TenKMCP": "Phí thẩm định dự án đầu tư xây dựng"
    },
    {
        "MaKMCP": "CP61704",
        "TenKMCP": "Chi phí đo đạc thu hồi đất"
    },
    {
        "MaKMCP": "CP61403",
        "TenKMCP": "Chi phí di dời nhà"
    },
    {
        "MaKMCP": "CP569",
        "TenKMCP": "Chi phí chỉ đạo thể hiện phần mỹ thuật"
    },
    {
        "MaKMCP": "CP51311",
        "TenKMCP": "Chi phí đánh giá hồ sơ dự thầu (hồ sơ đề xuất) tư vấn (Phát sinh)"
    },
    {
        "MaKMCP": "CP60902",
        "TenKMCP": "Chi phí kiểm toán công trình"
    },
    {
        "MaKMCP": "CP517",
        "TenKMCP": "Chi phí lập HSMT (HSYC), đánh giá HSDT (HSĐX) mua sắm vật tư, thiết bị"
    },
    {
        "MaKMCP": "CP101",
        "TenKMCP": "Chi phí bồi thường về đất, nhà, công trình trên đất, các tài sản gắn liền với đất, trên mặt nước và chi phí bồi thường khác"
    },
    {
        "MaKMCP": "CP604",
        "TenKMCP": "Phí thẩm định phê duyệt thiết kế về phòng cháy và chữa cháy"
    },
    {
        "MaKMCP": "CP534",
        "TenKMCP": "Phí thẩm định hồ sơ mời thầu (hồ sơ yêu cầu) gói thầu tư vấn đầu tư xây dựng"
    },
    {
        "MaKMCP": "CP703",
        "TenKMCP": "Chi phí dự phòng phát sinh khối lượng (cho yếu tố khối lượng phát sinh (KLPS))"
    },
    {
        "MaKMCP": "CP502",
        "TenKMCP": "Chi phí lập báo cáo nghiên cứu khả thi"
    },
    {
        "MaKMCP": "CP56302",
        "TenKMCP": "Chi phí khảo sát địa hình (Bước lập báo cáo nghiên cứu tiền khả thi (NCTKT))"
    },
    {
        "MaKMCP": "CP585",
        "TenKMCP": "Chi phí đo vẽ hiện trạng"
    },
    {
        "MaKMCP": "CP52806",
        "TenKMCP": "Chi phí khảo sát (Bước lập thiết kế bản vẽ thi công - dự toán (TKBVTC-DT))"
    },
    {
        "MaKMCP": "CP616",
        "TenKMCP": "Chi phí hạng mục chung"
    },
    {
        "MaKMCP": "CP558",
        "TenKMCP": "Chi phí công bố quy hoạch"
    },
    {
        "MaKMCP": "CP50603",
        "TenKMCP": "Chi phí lập nhiệm vụ khảo sát (Bước lập báo cáo nghiên cứu khả thi (NCKT))"
    },
    {
        "MaKMCP": "CP613",
        "TenKMCP": "Phí bảo vệ môi trường"
    },
    {
        "MaKMCP": "CP57301",
        "TenKMCP": "Chi phí kiểm định theo yêu cầu chủ đầu tư"
    },
    {
        "MaKMCP": "CP51411",
        "TenKMCP": "Chi phí lập HSMT (HSYC), đánh giá HSDT (HSĐX) thi công xây dựng (Phát sinh)"
    },
    {
        "MaKMCP": "CP56202",
        "TenKMCP": "Chi phí khảo sát địa chất (Bước lập báo cáo nghiên cứu tiền khả thi (NCTKT))"
    },
    {
        "MaKMCP": "CP01",
        "TenKMCP": "Chi phí bồi thường, hỗ trợ, tái định cư"
    },
    {
        "MaKMCP": "CP568",
        "TenKMCP": "Chi phí chuẩn bị đầu tư ban đầu sáng tác thi tuyển mẫu phác thảo bước 1"
    },
    {
        "MaKMCP": "CP581",
        "TenKMCP": "Chi phí báo cáo giám sát đánh giá đầu tư"
    },
    {
        "MaKMCP": "CP515",
        "TenKMCP": "Chi phí lập hồ sơ mời thầu (hồ sơ yêu cầu) thi công xây dựng"
    },
    {
        "MaKMCP": "CP52804",
        "TenKMCP": "Chi phí khảo sát (Bước lập báo cáo kinh tế kỹ thuật (KTKT))"
    },
    {
        "MaKMCP": "CP58220",
        "TenKMCP": "Chi phí thẩm tra thiết kế bản vẽ thi công (BVTC)"
    },
    {
        "MaKMCP": "CP51511",
        "TenKMCP": "Chi phí lập hồ sơ mời thầu (hồ sơ yêu cầu) thi công xây dựng (Phát sinh)"
    },
    {
        "MaKMCP": "CP606",
        "TenKMCP": "Phí thẩm định thiết kế xây dựng triển khai sau thiết kế cơ sở"
    },
    {
        "MaKMCP": "CP702",
        "TenKMCP": "Chi phí dự phòng cho yếu tố trược giá"
    },
    {
        "MaKMCP": "CP602",
        "TenKMCP": "Phí thẩm định dự toán xây dựng"
    },
    {
        "MaKMCP": "CP510",
        "TenKMCP": "Chi phí thẩm tra dự toán xây dựng"
    },
    {
        "MaKMCP": "CP56204",
        "TenKMCP": "Chi phí khảo sát địa chất (Bước lập báo cáo kinh tế kỹ thuật (KTKT))"
    },
    {
        "MaKMCP": "CP520",
        "TenKMCP": "Chi phí giám sát thi công xây dựng"
    },
    {
        "MaKMCP": "CP699",
        "TenKMCP": "Chi phí khác"
    },
    {
        "MaKMCP": "CP52805",
        "TenKMCP": "Chi phí khảo sát (Bước lập thiết kế bản vẽ thi công (TKBVTC))"
    },
    {
        "MaKMCP": "CP573",
        "TenKMCP": "Chi phí giám sát thi công xây dựng phát sinh"
    },
    {
        "MaKMCP": "CP559",
        "TenKMCP": "Chi phí thử tải cừ tràm"
    },
    {
        "MaKMCP": "CP61405",
        "TenKMCP": "Chi phí di dời trụ điện trong trường"
    },
    {
        "MaKMCP": "CP501",
        "TenKMCP": "Chi phí lập báo cáo nghiên cứu tiền khả thi"
    },
    {
        "MaKMCP": "CP551",
        "TenKMCP": "Chi phí khảo sát, thiết kế"
    },
    {
        "MaKMCP": "CP224",
        "TenKMCP": "Chi phí xây dựng công trình phụ"
    },
    {
        "MaKMCP": "CP571",
        "TenKMCP": "Chi phí sáng tác mẫu phác thảo tượng đài"
    },
    {
        "MaKMCP": "CP226",
        "TenKMCP": "Chi phí xây dựng điều chỉnh"
    },
    {
        "MaKMCP": "CP50604",
        "TenKMCP": "Chi phí lập nhiệm vụ khảo sát (Bước lập thiết kế bản vẽ thi công (TKBVTC))"
    },
    {
        "MaKMCP": "CP523",
        "TenKMCP": "Chi phí quy đổi vốn đầu tư xây dựng"
    },
    {
        "MaKMCP": "CP227",
        "TenKMCP": "Chi phí xây dựng công trình chính và phụ"
    },
    {
        "MaKMCP": "CP599",
        "TenKMCP": "Chi phí đo đạc thu hồi đất"
    },
    {
        "MaKMCP": "CP61402",
        "TenKMCP": "Chi phí di dời đường dây hạ thế"
    },
    {
        "MaKMCP": "CP50411",
        "TenKMCP": "Chi phí thiết kế xây dựng (Phát sinh)"
    },
    {
        "MaKMCP": "CP51911",
        "TenKMCP": "Chi phí đánh giá HSDT (HSĐX) mua sắm vật tư, thiết bị (Phát sinh)"
    },
    {
        "MaKMCP": "CP556",
        "TenKMCP": "Chi phí thẩm tra an toàn giao thông"
    },
    {
        "MaKMCP": "CP221",
        "TenKMCP": "Chi phí xây dựng phát sinh"
    },
    {
        "MaKMCP": "CP518",
        "TenKMCP": "Chi phí lập HSMT (HSYC) mua sắm vật tư, thiết bị"
    },
    {
        "MaKMCP": "CP526",
        "TenKMCP": "Phí thẩm định hồ sơ mời thầu (hồ sơ yêu cầu)"
    },
    {
        "MaKMCP": "CP105",
        "TenKMCP": "Chi phí sử dụng đất, thuê đất tính trong thời gian xây dựng"
    },
    {
        "MaKMCP": "CP577",
        "TenKMCP": "Chi phí lập hồ sơ điều chỉnh dự toán"
    },
    {
        "MaKMCP": "CP61701",
        "TenKMCP": "Chi phí đo đạc bản đồ địa chính"
    },
    {
        "MaKMCP": "CP56206",
        "TenKMCP": "Chi phí khảo sát địa chất (Bước lập thiết kế bản vẽ thi công - dự toán (BVTC-DT))"
    },
    {
        "MaKMCP": "CP554",
        "TenKMCP": "Chi phí kiểm tra và chứng nhận sự phù hợp về chất lượng công trình xây dựng"
    },
    {
        "MaKMCP": "CP61702",
        "TenKMCP": "Chi phí đo đạc lập bản đồ địa chính giải phóng mặt bằng (GPMB)"
    },
    {
        "MaKMCP": "CP603",
        "TenKMCP": "Chi phí rà phá bom mìn, vật nổ"
    },
    {
        "MaKMCP": "CP58211",
        "TenKMCP": "Chi phí thẩm tra thiết kế bản vẽ thi công - dự toán (BVTC-DT) (Phát sinh)"
    },
    {
        "MaKMCP": "CP50605",
        "TenKMCP": "Chi phí lập nhiệm vụ khảo sát (Bước lập thiết kế bản vẽ thi công - dự toán (TKBVTC-DT))"
    },
    {
        "MaKMCP": "CP421",
        "TenKMCP": "Chi phí quản lý dự án phát sinh"
    },
    {
        "MaKMCP": "CP107",
        "TenKMCP": "Chi phí đầu tư vào đất"
    },
    {
        "MaKMCP": "CP629",
        "TenKMCP": "Chi phí thẩm định HSMT (HSYC)"
    },
    {
        "MaKMCP": "CP50511",
        "TenKMCP": "Chi phí thiết kế bản vẽ thi công (Phát sinh)"
    },
    {
        "MaKMCP": "CP2",
        "TenKMCP": "Chi phí xây dựng"
    },
    {
        "MaKMCP": "CP579",
        "TenKMCP": "Chi phí thẩm định giá"
    },
    {
        "MaKMCP": "CP50602",
        "TenKMCP": "Chi phí lập nhiệm vụ khảo sát (Bước lập báo cáo nghiên cứu tiền khả thi (NCTKT))"
    },
    {
        "MaKMCP": "CP52111",
        "TenKMCP": "Chi phí giám sát lắp đặt thiết bị (Phát sinh)"
    },
    {
        "MaKMCP": "CP564",
        "TenKMCP": "Tư vấn lập văn kiện dự án và các báo cáo thành phần của dự án"
    },
    {
        "MaKMCP": "CP516",
        "TenKMCP": "Chi phí đánh giá hồ sơ dự thầu (hồ sơ đề xuất) thi công xây dựng"
    },
    {
        "MaKMCP": "CP4",
        "TenKMCP": "Chi phí quản lý dự án"
    },
    {
        "MaKMCP": "CP50911",
        "TenKMCP": "Chi phí thẩm tra thiết kế xây dựng (Phát sinh)"
    },
    {
        "MaKMCP": "CP565",
        "TenKMCP": "Chi phí lập kế hoạch bảo vệ môi trường"
    },
    {
        "MaKMCP": "CP583",
        "TenKMCP": "Tư vấn đầu tư xây dựng"
    },
    {
        "MaKMCP": "CP624",
        "TenKMCP": "Chi phí nhà tạm"
    }
])

    du_lieu_can_tim = pd.DataFrame([
    {
        "TenKMCP": "Bảo hiểm công trình"
    },
    {
        "TenKMCP": "Bảo hiểm công trình."
    },
    {
        "TenKMCP": "Bê tông cổ móng SX bằng máy trộn, đổ bằng thủ công, M250, đá 1x2, PCB40"
    },
    {
        "TenKMCP": "Bê tông lót móng SX bằng máy trộn, đổ bằng thủ công, M150, đá 4x6, PCB40"
    },
    {
        "TenKMCP": "Bê tông móng SX bằng máy trộn, đổ bằng thủ công, M250, đá 1x2, PCB40"
    },
    {
        "TenKMCP": "Các phòng chức năng"
    },
    {
        "TenKMCP": "Chi phí bảo hiểm"
    },
    {
        "TenKMCP": "Chi phí bảo hiểm (bao gồm VAT)"
    },
    {
        "TenKMCP": "Chi phí bồi thường, hỗ trợ, tái định cư"
    },
    {
        "TenKMCP": "Chi phí cắm cọc chỉ giới giải phóng mặt bằng"
    },
    {
        "TenKMCP": "Chi phí cảm cọc chỉ giới giải phóng mặt bằng"
    },
    {
        "TenKMCP": "Chi phí cám cọc chỉ giới GPMB"
    },
    {
        "TenKMCP": "Chi phí cắm cọc chỉ giới GPMB"
    },
    {
        "TenKMCP": "Chi phí đo vẽ hiện trạng"
    },
    {
        "TenKMCP": "Chi phí đo về hiện trạng"
    },
    {
        "TenKMCP": "Chỉ phí đo vẽ hiện trạng (làm tròn)"
    },
    {
        "TenKMCP": "Chi phí đo vẽ hiện trạng (làm tròn):"
    },
    {
        "TenKMCP": "Chi phí đo vẽ hiện trạng sau thuế"
    },
    {
        "TenKMCP": "Chi phí đo vẽ hiện trạng sau thuế (1+2)"
    },
    {
        "TenKMCP": "Chi phí đo vẽ hiện trạng trước thuế"
    },
    {
        "TenKMCP": "Chi phí dự phòng"
    },
    {
        "TenKMCP": "Chi phí giải phóng mặt bằng"
    },
    {
        "TenKMCP": "Chi phí giám sát công tác khảo sát"
    },
    {
        "TenKMCP": "Chi phí giám sát khảo sát"
    },
    {
        "TenKMCP": "Chi phí giám sát khảo sát địa hình"
    },
    {
        "TenKMCP": "Chi phí giám sát khảo sát giai đoạn lập báo cáo nghiên cứu khả thi"
    },
    {
        "TenKMCP": "Chi phí giám sát khảo sát giai đoạn thiết kế bản vẽ thi công"
    },
    {
        "TenKMCP": "Chi phí giám sát khảo sát giai đoạn thiết kế bản vẽ thì công"
    },
    {
        "TenKMCP": "Chi phí giám sát thi công xây dựng"
    },
    {
        "TenKMCP": "Chỉ phí giám sát thi công xây dựng"
    },
    {
        "TenKMCP": "Chi phí giám sát xây dựng"
    },
    {
        "TenKMCP": "Chi phí khác"
    },
    {
        "TenKMCP": "Chi phí khảo sát địa chất"
    },
    {
        "TenKMCP": "Chi phí khảo sát địa hình"
    },
    {
        "TenKMCP": "Chỉ phí khảo sát địa hình (I=74)"
    },
    {
        "TenKMCP": "Chi phí khảo sát địa hình (Làm tròn)"
    },
    {
        "TenKMCP": "Chỉ phí khảo sát địa hình (làm tròn)"
    },
    {
        "TenKMCP": "Chi phí khảo sát địa hình giai đoạn lập báo cáo nghiên cứu khả thi"
    },
    {
        "TenKMCP": "Chi phí khảo sát địa hình giai đoạn thiết kế bản vẽ thi công"
    },
    {
        "TenKMCP": "Chi phí khảo sát sau thuế (23 == Z1+Z2)"
    },
    {
        "TenKMCP": "Chi phí khảo sát sau thuế (7.4=Z2+23)"
    },
    {
        "TenKMCP": "Chỉ phí khảo sát trước thuế (Z2=Z+Z1)"
    },
    {
        "TenKMCP": "Chi phí kiểm định chất lượng phục vụ công tác nghiệm thu"
    },
    {
        "TenKMCP": "Chi phí kiểm định chất lượng phục vụ công tác nghiệm thu (20% chi phí giám sát)"
    },
    {
        "TenKMCP": "Chi phí kiểm định chất lượng phục vụ công tác nghiệm thu (20% chỉ phí giám sát)"
    },
    {
        "TenKMCP": "Chi phí kiểm toán công trình"
    },
    {
        "TenKMCP": "Chi phí kiểm tra công tác nghiệm thu công trình xây dựng"
    },
    {
        "TenKMCP": "Chỉ phí kiểm tra công tác nghiệm thu công trình xây dựng"
    },
    {
        "TenKMCP": "Chi phí lập Báo cáo kinh tế - kỹ thuật"
    },
    {
        "TenKMCP": "Chí phí lập báo cáo Kinh tế - kỹ thuật"
    },
    {
        "TenKMCP": "Chỉ phí lập báo cáo Kinh tế - kỹ thuật"
    },
    {
        "TenKMCP": "Chi phí lập Báo cáo Kinh tế - kỹ thuật (làm tròn)"
    },
    {
        "TenKMCP": "Chi phí lập Báo cáo Kinh tế - kỹ thuật sau thuế"
    },
    {
        "TenKMCP": "Chỉ phí lập Báo cáo Kinh tế - kỹ thuật trước thuế"
    },
    {
        "TenKMCP": "Chi phí lập báo cáo kinh tế - kỹ thuật."
    },
    {
        "TenKMCP": "Chi phí lập báo cáo kinh tế kỹ thuật"
    },
    {
        "TenKMCP": "Chỉ phí lập báo cáo kinh tế kỹ thuật"
    },
    {
        "TenKMCP": "Chi phí lập báo cáo kinh tế kỹ thuật (làm tròn)"
    },
    {
        "TenKMCP": "Chi phí lập Báo cáo kinh tế kỹ thuật (làm tròn):"
    },
    {
        "TenKMCP": "Chi phí lập Báo cáo kinh tế kỹ thuật sau thuế"
    },
    {
        "TenKMCP": "Chi phí lập Báo cáo kinh tế kỹ thuật sau thuế (1+2)"
    },
    {
        "TenKMCP": "Chi phí lập báo cáo kinh tế kỹ thuật sau thuế (3=1+2)"
    },
    {
        "TenKMCP": "Chi phí lập Báo cáo kinh tế kỹ thuật trước thuế"
    },
    {
        "TenKMCP": "Chỉ phí lập Báo cáo kinh tế kỹ thuật trước thuế"
    },
    {
        "TenKMCP": "Chí phí lập báo cáo KTKT"
    },
    {
        "TenKMCP": "Chi phí lập Báo cáo nghiên cứu khả thi"
    },
    {
        "TenKMCP": "Chỉ phí lập BCKTKT ( Làm tròn )"
    },
    {
        "TenKMCP": "Chi phí lập hồ sơ thiết kế và dự toán xây dựng"
    },
    {
        "TenKMCP": "Chi phí lập hồ sơ yêu cầu, đánh giá hồ sơ đề xuất"
    },
    {
        "TenKMCP": "Chi phí lập hồ sơ yêu cầu, đánh giá hồ sơ đề xuất thi công xây dựng"
    },
    {
        "TenKMCP": "Chi phí lập hồ sơ yêu cầu. đánh giá hồ sơ đề xuất thi công xây dựng"
    },
    {
        "TenKMCP": "Chỉ phí lập nhiệm vụ khảo sát xây dựng"
    },
    {
        "TenKMCP": "Chỉ phí lập nhiệm vụ khảo sát xây dựng (Z1=Z*3%)"
    },
    {
        "TenKMCP": "Chi phí lựa chọn nhà thầu thi công xây dựng"
    },
    {
        "TenKMCP": "Chi phí QLDA"
    },
    {
        "TenKMCP": "Chi phí quản lý dự án"
    },
    {
        "TenKMCP": "Chi phí thẩm định báo cáo Kinh tế - kỹ thuật"
    },
    {
        "TenKMCP": "Chi phí thẩm định báo cáo kinh tế kỹ thuật"
    },
    {
        "TenKMCP": "Chi phí thẩm định báo cáo KTKT"
    },
    {
        "TenKMCP": "Chi phí thẩm định hồ sơ mời thầu thi công xây dựng"
    },
    {
        "TenKMCP": "Chi phí thẩm định hồ sơ yêu cầu"
    },
    {
        "TenKMCP": "Chi phí thẩm định hồ sơ yêu cầu thi công xây dựng"
    },
    {
        "TenKMCP": "Chi phí thẩm định kết quả lựa chọn nhà thầu"
    },
    {
        "TenKMCP": "Chi phí thẩm định kết quả lựa chọn nhà thầu thi công xây dựng"
    },
    {
        "TenKMCP": "Chi phí thẩm định kết quả lựa chọn nhà thầu thì công xây dựng"
    },
    {
        "TenKMCP": "Chi phí thẩm tra dự toán công trình"
    },
    {
        "TenKMCP": "Chi phí thầm tra dự toán xây dựng"
    },
    {
        "TenKMCP": "Chi phí thắm tra dự toán xây dựng"
    },
    {
        "TenKMCP": "Chi phí thảm tra dự toán xây dựng"
    },
    {
        "TenKMCP": "Chi phí thẩm tra dự toán xây dựng"
    },
    {
        "TenKMCP": "Chi phí thẩm tra Dự toán xây dựng ( làm tròn )"
    },
    {
        "TenKMCP": "Chi phí thẩm tra dự toán xây dựng (làm tròn)"
    },
    {
        "TenKMCP": "Chi phí thẩm tra phê duyệt quyết toán"
    },
    {
        "TenKMCP": "Chi phí thẩm tra thiết kế bản vẽ thi công"
    },
    {
        "TenKMCP": "Chi phí thẩm tra thiết kế bản vẽ thi công + dự toán"
    },
    {
        "TenKMCP": "Chi phí thẩm tra thiết kế xây dựng"
    },
    {
        "TenKMCP": "Chỉ phí thẩm tra thiết kế xây dựng"
    },
    {
        "TenKMCP": "Chi phí thẩm tra Thiết kế xây dựng ( làm tròn )"
    },
    {
        "TenKMCP": "Chi phí thẩm tra thiết kế xây dựng (làm tròn)"
    },
    {
        "TenKMCP": "Chi phí thẩm tra thiết kế xây dựng + dự toán xây dựng"
    },
    {
        "TenKMCP": "Chi phí thẩm tra TK BVTC + DT"
    },
    {
        "TenKMCP": "Chi phí thẩm tra, phê duyệt quyết toán"
    },
    {
        "TenKMCP": "Chi phí thí nghiệm đối chứng, kiểm định xây dựng, thử nghiệm khả năng chịu lực của công trình"
    },
    {
        "TenKMCP": "Chi phí thiết bị"
    },
    {
        "TenKMCP": "CHI PHÍ TƯ VẤN"
    },
    {
        "TenKMCP": "Chi phí tư vấn đầu tư xây dựng"
    },
    {
        "TenKMCP": "Chỉ phí tư vấn đầu tư xây dựng"
    },
    {
        "TenKMCP": "Chi phí xây dựng"
    },
    {
        "TenKMCP": "CHI PHÍ XÂY DỰNG CÔNG TRÌNH"
    },
    {
        "TenKMCP": "Công tác đo khống chế cao, thủy chuẩn kỹ thuật, cấp địa hình III"
    },
    {
        "TenKMCP": "Công tác đo lưới khống chế mặt bằng, đường chuyên cấp II, máy toàn đạc điện tử"
    },
    {
        "TenKMCP": "Công tác do lưới khống chế mặt bằng, đường chuyển cấp Il, máy toàn đạc điện tử"
    },
    {
        "TenKMCP": "Công tác đo vẽ mặt cắt địa hình, đo vẽ mặt cắt dọc ở trên cạn; cấp địa hình III"
    },
    {
        "TenKMCP": "Công trình dân dụng"
    },
    {
        "TenKMCP": "Công trình hạ tầng kỹ thuật"
    },
    {
        "TenKMCP": "Đào móng bằng máy đào 0,4m3, Cấp đất 1"
    },
    {
        "TenKMCP": "Đào móng bằng máy đào 0,4m3, Cấp đất I"
    },
    {
        "TenKMCP": "Đắp cát lót đáy móng"
    },
    {
        "TenKMCP": "Đắp đất bằng đầm đất cầm tay 70kg, độ chặt Y/C K = 0,90"
    },
    {
        "TenKMCP": "Đo vẽ bản đồ trên cạn TL 1/500"
    },
    {
        "TenKMCP": "Đo vẽ chi tiết bản đồ địa hình trên cạn bằng máy toàn đạc điện tử và máy thủy bình điện tử; bản đồ tỷ lệ 1/200, đường đồng mức 1m, cấp địa hình III"
    },
    {
        "TenKMCP": "Đo vẽ chỉ tiết bản đồ địa hình trên cạn bằng máy toàn đạc điện từ và máy thủy bình điện tử; bản đồ tỷ lệ 1/200, đường đồng mức 1m, cấp địa hình III"
    },
    {
        "TenKMCP": "Đo về chỉ tiết bản đồ địa hình trên cạn bằng máy toàn đạc điện tử và máy thủy bình điện tử; bản đồ tỷ lệ 1/200, đường đồng mức 1m. cấp địa hình !!!"
    },
    {
        "TenKMCP": "Đo vẽ chi tiết bản đồ địa hình trên cạn bằng máy toàn đạc điện tử và máy thủy bình điện tử; bản đồ tỷ lệ 1/500, đường đồng mức 0,5m, cấp địa hình III"
    },
    {
        "TenKMCP": "Đo vẽ mặt cắt dọc tuyến trên cạn"
    },
    {
        "TenKMCP": "Đo vẽ mặt cắt ngang ở dưới nước; cấp địa hình I"
    },
    {
        "TenKMCP": "Đo vẽ mặt cắt ngang ở trên cạn; cấp địa hình III"
    },
    {
        "TenKMCP": "Đo vẽ mặt cắt ngang sông"
    },
    {
        "TenKMCP": "Đo vẽ mặt cắt ngang tuyến trên cạn"
    },
    {
        "TenKMCP": "Đóng cọc tràm bằng máy đào 0,5m3 - Cấp đất I"
    },
    {
        "TenKMCP": "Dự phòng cho yếu tố KLPS"
    },
    {
        "TenKMCP": "Gia công, lắp dựng, tháo dỡ ván khuôn kim loại, ván khuôn nắp đan, tấm chớp"
    },
    {
        "TenKMCP": "Giá trị khảo sát địa hình sau thuế (Z+9)"
    },
    {
        "TenKMCP": "Giá trị khảo sắt sau thuế"
    },
    {
        "TenKMCP": "Giai đoạn lập Báo cáo nghiên cứu khả thi"
    },
    {
        "TenKMCP": "Giai đoạn lập Báo cáo nghiên cứu khả thị"
    },
    {
        "TenKMCP": "Giai đoạn thiết kế bản vẽ thi công"
    },
    {
        "TenKMCP": "Giám sát thi công xây dựng"
    },
    {
        "TenKMCP": "Giám sát thi công xây dựng."
    },
    {
        "TenKMCP": "Giảm thuế 2% theo Nghị định 72/2024/NĐ-CP ngày 30/6/2024"
    },
    {
        "TenKMCP": "Gói thầu số 01 - Thi công xây lắp công trình"
    },
    {
        "TenKMCP": "Gói thầu số 01: Thi công xây lắp công trình khối phòng học hiện trạng Trường tiểu học Tài Văn (điểm Bưng Chông) thành nhà sinh hoạt cộng đồng; Sửa chữa nhà vệ sinh; Sân đường thoát nước"
    },
    {
        "TenKMCP": "Gói thầu số 01: Tư vấn khảo sát, lập hồ sơ thiết kế bản vẽ thi công và dự toán xây dựng"
    },
    {
        "TenKMCP": "Gói thầu số 02: Giám sát thi công xây dựng"
    },
    {
        "TenKMCP": "Gói thầu số 02: Giám sát thị công xây dựng"
    },
    {
        "TenKMCP": "Gói thầu số 02: Giám sát thi công xây dựng. Thực hiện công tác giám sát trong quá trình thi công"
    },
    {
        "TenKMCP": "Gói thầu số 02: Tư vấn giám sát khảo sát giai đoạn thiết kế bản vẽ thi công"
    },
    {
        "TenKMCP": "Gói thầu số 03: Tư vấn thẩm tra thiết kế bản vẽ thi công và dự toán xây dựng"
    },
    {
        "TenKMCP": "Gói thầu số 04: Thi công xây lắp công trình"
    },
    {
        "TenKMCP": "Gói thầu số 05: Bảo hiểm công trình"
    },
    {
        "TenKMCP": "Gói thầu số 06: Lập hồ sơ mời thầu, đánh giá hồ sơ dự thầu"
    },
    {
        "TenKMCP": "Gói thầu số 07: Giám sát thi công xây dựng"
    },
    {
        "TenKMCP": "Gói thầu số 08: Kiểm toán công trình"
    },
    {
        "TenKMCP": "Khảo sát bình đồ trên cạn TL 1/200"
    },
    {
        "TenKMCP": "Khối 10 phòng học"
    },
    {
        "TenKMCP": "khối phòng học hiện trạng Trường tiểu học Tài Văn (điểm Bưng Chông) thành nhà sinh hoạt cộng đồng; Sửa chữa nhà vệ sinh; Sân đường thoát nước"
    },
    {
        "TenKMCP": "Khu hiệu bộ"
    },
    {
        "TenKMCP": "Khu vệ sinh"
    },
    {
        "TenKMCP": "Kiểm toán công trình"
    },
    {
        "TenKMCP": "KS bình đồ dưới nước TL 1/200"
    },
    {
        "TenKMCP": "Lắp các loại CKBT đúc sẵn bằng thủ công, trọng lượng ≤100kg"
    },
    {
        "TenKMCP": "Lắp đặt ống nhựa PVC miệng bát, nối bằng p/p dán keo, đoạn ống dài 6m - Đường kính 250mm"
    },
    {
        "TenKMCP": "Lắp dựng cốt thép móng, ĐK 12mm"
    },
    {
        "TenKMCP": "Lắp dựng cốt thép móng, ĐK 14mm"
    },
    {
        "TenKMCP": "Lắp dựng cốt thép móng, ĐK 16mm"
    },
    {
        "TenKMCP": "Lắp dựng cốt thép móng, ĐK 6mm"
    },
    {
        "TenKMCP": "Lập hồ sơ mời thầu, đánh giá hồ sơ dự thầu thi công xây dựng"
    },
    {
        "TenKMCP": "Lập hồ sơ mời thầu, đánh giá hồ sơ dự thầu thi công xây dựng."
    },
    {
        "TenKMCP": "Lập hồ sơ yêu cầu, đánh giá hồ sơ đề xuất thi công xây dựng"
    },
    {
        "TenKMCP": "Lệ phí thẩm định báo cáo KTKT"
    },
    {
        "TenKMCP": "Mốc cao độ thi công (đường chuyền cấp"
    },
    {
        "TenKMCP": "Nhà xe"
    },
    {
        "TenKMCP": "Phá dỡ cột, trụ bê tông cốt thép bằng thủ công"
    },
    {
        "TenKMCP": "Phá dỡ tưởng xây gạch chiều đầy ≤1lem"
    },
    {
        "TenKMCP": "Phí thẩm định dự án đầu tư xây dựng công trình"
    },
    {
        "TenKMCP": "Phí thẩm định dự toán xây dựng"
    },
    {
        "TenKMCP": "Phí thẩm định thiết kế xây dựng"
    },
    {
        "TenKMCP": "Sửa chữa nhà văn hóa thành nhà sinh hoạt cộng đồng (1+ ..... 163)"
    },
    {
        "TenKMCP": "Thẩm tra thiết kế xây dựng - dự toán xây dựng công trình Đường bê tông Thanh Nhàn - Tắc Bướm (giai đoạn 02), xã Thạnh Thới An"
    },
    {
        "TenKMCP": "Tháo đỡ cửa bằng thủ công"
    },
    {
        "TenKMCP": "Thảo dỡ kết cấu gỗ bằng thủ công, chiều cao Som"
    },
    {
        "TenKMCP": "Thảo đỡ kết cấu sắt thép bằng thủ công, chiều cao ≤6m"
    },
    {
        "TenKMCP": "Tháo dỡ mái tôn bằng thủ công, chiều cao ≤6m"
    },
    {
        "TenKMCP": "Thảo dỡ trần"
    },
    {
        "TenKMCP": "Thi công xây lắp công trình"
    },
    {
        "TenKMCP": "Thực hiện công tác giám sát trong quá trình thi công"
    },
    {
        "TenKMCP": "Thủy chuẩn kỹ thuật"
    },
    {
        "TenKMCP": "Trung tâm - văn hoá hội nghị huyện"
    },
    {
        "TenKMCP": "Tư vấn đo vẽ hiện trạng, lập Báo cáo kinh tế - kỹ thuật"
    },
    {
        "TenKMCP": "Tư vấn khảo sát địa hình, đo vẽ hiện trạng và lập Báo cáo kinh tế - kỹ thuật"
    },
    {
        "TenKMCP": "Tư vấn khảo sát địa hình, lập Báo cáo kinh tế - kỹ thuật"
    },
    {
        "TenKMCP": "Tư vấn khảo sát, lập Báo cáo kinh tế - kỹ thuật"
    },
    {
        "TenKMCP": "Tư vấn lập Báo cáo nghiên cứu khả thi"
    },
    {
        "TenKMCP": "Tư vấn thẩm tra thiết kế xây dựng - dự toán xây dựng"
    },
    {
        "TenKMCP": "Ván khuôn móng cột"
    },
    {
        "TenKMCP": "Vét bùn đầu cử"
    }
])
    # Chuỗi cần tìm kiếm
    chuoi_tim = "Chi phí xây dựng"
    # chuoi_tim_2 = "Thẩm định dự án đầu tư xây dựng"
    ket_qua_tim_kiem = []
    for index, row in du_lieu_can_tim.iterrows():
        chuoi_can_tim = row['TenKMCP']
        ket_qua = tim_kiem_tuong_dong(chuoi_can_tim, du_lieu_mau_df, nguong_diem=0.5, model_name='VoVanPhuc/sup-SimCSE-VietNamese-phobert-base')
        if ket_qua['success']:
            for res in ket_qua['results']:
                ket_qua_tim_kiem.append({'TenKMCP_Cu': row['TenKMCP'], 'MaKMCP': res['MaKMCP'], 'TenKMCP': res['TenKMCP'], 'score': res['score']})
    
    print(ket_qua_tim_kiem)
    #print(f"--- Tìm kiếm cho: '{chuoi_tim}' ---")
    # Sử dụng mô hình mặc định (tiếng Anh, đa ngôn ngữ cơ bản)
    # ket_qua_default = tim_kiem_tuong_dong(chuoi_tim, du_lieu_mau_df, nguong_diem=0.5, model_name='VoVanPhuc/sup-SimCSE-VietNamese-phobert-base')
    # print("Kết quả (mô hình default 'all-MiniLM-L6-v2'):")
    # if ket_qua_default['success']:
    #     for res in ket_qua_default['results']:
    #         print(f"  {res['MaKMCP']}: {res['TenKMCP']} (Score: {res['score']})")
    # else:
    #     print(f"  {ket_qua_default['message']}")
    # print("-" * 30)
