from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, List, Any
import uuid
from datetime import datetime
from app.services.DungChung import convert_currency_to_int
import json

class DatabaseService:
    @staticmethod
    async def insert_van_ban(db: Session, van_ban_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Insert main document data
            insert_van_ban_query = text("""
                INSERT INTO VanBan (
                    VanBanID,
                    SoVanBan,
                    NgayKy,
                    NguoiKy,
                    ChucDanhNguoiKy,
                    CoQuanBanHanh,
                    TrichYeu,
                    LaVanBanDieuChinh,
                    LoaiVanBan
                ) VALUES (
                    :VanBanID,
                    :SoVanBan,
                    :NgayKy,
                    :NguoiKy,
                    :ChucDanhNguoiKy,
                    :CoQuanBanHanh,
                    :TrichYeu,
                    :LaVanBanDieuChinh,
                    :LoaiVanBan
                )
            """)
            
            db.execute(insert_van_ban_query, van_ban_data)
            db.commit()
            
            return {
                "success": True,
                "message": "Thêm văn bản thành công",
                "van_ban_id": van_ban_data["VanBanID"]
            }
            
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": "Lỗi khi thêm văn bản",
                "error": str(e)
            }

    @staticmethod
    async def insert_van_ban_ai(db: Session, van_ban_data: Dict[str, Any], loaiVanBan: str) -> Dict[str, Any]:
        try:
            # Xử lý chuyển đổi định dạng ngày nếu cột NgayKy tồn tại và có giá trị
            if van_ban_data.get('NgayKy'):
                try:
                    van_ban_data['NgayKy'] = datetime.strptime(van_ban_data['NgayKy'], '%d/%m/%Y').strftime('%Y-%m-%d')
                except ValueError as e:
                    # Nếu không muốn dừng thực thi ở đây, có thể ghi log và tiếp tục
                    # Hoặc đặt NgayKy thành None hoặc một giá trị mặc định khác
                    print(f"Lỗi chuyển đổi ngày tháng cho NgayKy: {van_ban_data['NgayKy']}. Lỗi: {e}")
                    van_ban_data['NgayKy'] = None # Hoặc xử lý theo cách khác
            if van_ban_data.get('NgayKyCanCu'):
                try:
                    van_ban_data['NgayKyCanCu'] = datetime.strptime(van_ban_data['NgayKyCanCu'], '%d/%m/%Y').strftime('%Y-%m-%d')
                except ValueError as e:
                    # Nếu không muốn dừng thực thi ở đây, có thể ghi log và tiếp tục
                    # Hoặc đặt NgayKy thành None hoặc một giá trị mặc định khác
                    print(f"Lỗi chuyển đổi ngày tháng cho NgayKyCanCu: {van_ban_data['NgayKyCanCu']}. Lỗi: {e}")
                    van_ban_data['NgayKyCanCu'] = None # Hoặc xử lý theo cách khác
            if van_ban_data.get('GiaTri'):
                try:
                    van_ban_data['GiaTri'] = convert_currency_to_int(van_ban_data['GiaTri'])
                except ValueError as e:
                    # Nếu không muốn dừng thực thi ở đây, có thể ghi log và tiếp tục
                    # Hoặc đặt NgayKy thành None hoặc một giá trị mặc định khác
                    print(f"Lỗi chuyển đổi số cho GiaTri: {van_ban_data['GiaTri']}. Lỗi: {e}")
                    van_ban_data['GiaTri'] = 0 # Hoặc xử lý theo cách khác
            if van_ban_data.get('NgayHieuLuc') and isinstance(van_ban_data.get('NgayHieuLuc'), str) and van_ban_data.get('NgayHieuLuc') != "":
                try:
                    van_ban_data['NgayHieuLuc'] = datetime.strptime(van_ban_data['NgayHieuLuc'], '%d/%m/%Y').strftime('%Y-%m-%d')
                except ValueError:
                    print(f"Lỗi định dạng NgayHieuLuc: {van_ban_data['NgayHieuLuc']}. Để giá trị gốc.")
                    # Giữ giá trị gốc hoặc đặt là None nếu không parse được
                    # van_ban_data['NgayHieuLuc'] = None

            if van_ban_data.get('NgayKetThuc') and isinstance(van_ban_data.get('NgayKetThuc'), str) and van_ban_data.get('NgayKetThuc') != "":
                try:
                    van_ban_data['NgayKetThuc'] = datetime.strptime(van_ban_data['NgayKetThuc'], '%d/%m/%Y').strftime('%Y-%m-%d')
                except ValueError:
                    print(f"Lỗi định dạng NgayKetThuc: {van_ban_data['NgayKetThuc']}. Để giá trị gốc.")
                    # Giữ giá trị gốc hoặc đặt là None nếu không parse được
                    # van_ban_data['NgayKetThuc'] = None


            # Đặt các giá trị mặc định hoặc tính toán cho các trường dựa trên loaiVanBan
            # Phần này giữ nguyên logic cũ của bạn để đảm bảo van_ban_data có đủ các trường cần thiết
            # trước khi xây dựng câu lệnh SQL.
            # Ví dụ:
            # van_ban_data.setdefault('NgayThaotac', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            # van_ban_data.setdefault('TenLoaiVanBan', loaiVanBan) # Giả sử loaiVanBan là tên
            # ... (các setdefault khác từ logic cũ của bạn)

            # Logic đặt giá trị mặc định dựa trên loaiVanBan (giữ nguyên từ code gốc của bạn)
            if f"[{loaiVanBan}]" == "[BCDX_CT]": # Báo cáo đề xuất chủ trương đầu tư
                van_ban_data.setdefault('LoaiVanBanID', "3d4566fb-cf78-42e0-bebb-b22018b53763")
                van_ban_data.setdefault('GiaiDoanID', "6F6BB0B9-92BF-4831-8053-6246F42929B6")
                van_ban_data.setdefault('GiaiDoan', "2")
            elif f"[{loaiVanBan}]" == "[QDPD_CT]": # Phê duyệt chủ trương đầu tư
                if van_ban_data.get("DieuChinh") == "1":
                    van_ban_data.setdefault('LoaiVanBanID', "d8821afb-76a4-4b24-9fd3-ba1aa84e156d")
                else:
                    van_ban_data.setdefault('LoaiVanBanID', "550358d9-a68a-4122-89da-6fc7cb6df0df")
                van_ban_data.setdefault('GiaiDoanID', "AD8D512D-AA6B-4243-B651-A80A1CB59FFC")
                van_ban_data.setdefault('GiaiDoan', "2")
            elif f"[{loaiVanBan}]" == "[QDPDDT_CBDT]": # Phê quyệt dự toán chuẩn bị đầu tư
                if van_ban_data.get("DieuChinh") == "1":
                    van_ban_data.setdefault('LoaiVanBanID', "8f4faa5a-9725-4f5f-bf8e-0862569936b3")
                else:
                    van_ban_data.setdefault('LoaiVanBanID', "ac6e7501-eea1-4546-9195-4e44ade01990")
                van_ban_data.setdefault('GiaiDoanID', "2BB4A12A-A588-48FC-9BE2-5B99E31F1212")
                van_ban_data.setdefault('GiaiDoan', "2")
            elif f"[{loaiVanBan}]" == "[QDPD_DT_THDT]": # Phê quyệt dự toán chuẩn bị đầu tư
                if van_ban_data.get("DieuChinh") == "1":
                    van_ban_data.setdefault('LoaiVanBanID', "b4bf9da4-bd66-47e8-97ee-b1669433f62f")
                else:
                    van_ban_data.setdefault('LoaiVanBanID', "07b523ba-7e50-405a-95d2-6591a4916289")
                van_ban_data.setdefault('GiaiDoanID', "76504374-7603-4ED7-9FD4-0991FB9E0830")
                van_ban_data.setdefault('GiaiDoan', "3")
            elif f"[{loaiVanBan}]" == "[QDPD_DA]": # Phê duyệt dự án
                if van_ban_data.get("DieuChinh") == "1":
                    van_ban_data.setdefault('LoaiVanBanID', "f20710a1-7ea6-4c4a-9dec-52bea3d37f3d")
                else:
                    van_ban_data.setdefault('LoaiVanBanID', "4e31610d-31b7-4fbb-b530-c1f97b99e362")
                van_ban_data.setdefault('GiaiDoanID', "F9C3D581-53B2-4EBE-A223-1E0B4839A45A")
                van_ban_data.setdefault('GiaiDoan', "3")
            elif f"[{loaiVanBan}]" == "[QDPD_KHLCNT_CBDT]": # Phê duyệt KHLCNT giai đoạn chuẩn bị đầu tư
                if van_ban_data.get("DieuChinh") == "1":
                    van_ban_data.setdefault('LoaiVanBanID', "f8f74942-566b-4ae9-b612-855f0fe63127")
                else:
                    van_ban_data.setdefault('LoaiVanBanID', "7017f242-e957-4e64-8048-3cff04519176")
                van_ban_data.setdefault('GiaiDoanID', "68B4F3FB-BBB1-45B3-92C1-7456E57CFB9E")
                van_ban_data.setdefault('GiaiDoan', "2")
            elif f"[{loaiVanBan}]" == "[QDPD_KHLCNT_THDT]": # Phê duyệt KHLCNT giai đoạn thực hiện dự án
                if van_ban_data.get("DieuChinh") == "1":
                    van_ban_data.setdefault('LoaiVanBanID', "93559dce-aa92-4b2c-93b5-b36f566fb1a2")
                else:
                    van_ban_data.setdefault('LoaiVanBanID', "b38eb6d6-ecb5-418d-9f2f-60469ed5fcf1")
                van_ban_data.setdefault('GiaiDoanID', "7BAE2A20-4377-4DE5-87B6-C905C955A882")
                van_ban_data.setdefault('GiaiDoan', "3")
            else: # Ngược lại
                van_ban_data.setdefault('LoaiVanBanID', "00000000-0000-0000-0000-000000000000")
                van_ban_data.setdefault('GiaiDoanID', "00000000-0000-0000-0000-000000000000")
                van_ban_data.setdefault('GiaiDoan', "")
            
            # Đảm bảo các trường cơ bản luôn có giá trị mặc định nếu chưa được cung cấp
            # (Những trường này có trong ví dụ `van_ban_data` ban đầu của bạn)
            van_ban_data.setdefault('VanBanAIID', str(uuid.uuid4())) # Đảm bảo có ID nếu chưa có
            van_ban_data.setdefault('SoVanBan', "")
            # NgayKy đã được xử lý ở trên
            # NgayHieuLuc, NgayKetThuc đã được xử lý ở trên
            van_ban_data.setdefault('NguoiKy', "")
            van_ban_data.setdefault('ChucDanhNguoiKy', "")
            van_ban_data.setdefault('TrichYeu', "")
            van_ban_data.setdefault('CoQuanBanHanh', "")
            van_ban_data.setdefault('NgayThaotac', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            van_ban_data.setdefault('TenLoaiVanBan', loaiVanBan) # Giả sử loaiVanBan là tên
            # LoaiVanBanID, GiaiDoanID, GiaiDoan đã được xử lý trong khối if/elif ở trên
            van_ban_data.setdefault('DuAnID', "00000000-0000-0000-0000-000000000000")
            van_ban_data.setdefault('DieuChinh', "0") # Giá trị mặc định từ ví dụ
            van_ban_data.setdefault('JsonAI', json.dumps({}, ensure_ascii=False)) # Mặc định JSON rỗng
            van_ban_data.setdefault('DataOCR', "")
            van_ban_data.setdefault('TenFile', "")
            # UserID và DonViID nên được truyền vào và không nên có giá trị mặc định ở đây trừ khi có yêu cầu cụ thể
            # van_ban_data.setdefault('UserID', None) 
            # van_ban_data.setdefault('DonViID', None)


            # Xây dựng câu lệnh INSERT động
            # Lấy danh sách các cột từ keys của van_ban_data sau khi đã xử lý
            # QUAN TRỌNG: Đảm bảo rằng tất cả các keys trong van_ban_data đều là tên cột hợp lệ trong bảng VanBanAI
            # Nếu không, câu lệnh SQL sẽ bị lỗi.
            # Một cách an toàn hơn là có một danh sách các cột được phép và chỉ lấy các keys có trong danh sách đó.
            # Tuy nhiên, theo yêu cầu "chạy động cột theo van_ban_data", chúng ta sẽ dùng tất cả keys.
            
            columns = []
            placeholders = []
            
            # Lọc ra các giá trị None để không đưa vào câu lệnh INSERT nếu không muốn
            # Hoặc bạn có thể để chúng được chèn dưới dạng NULL vào DB nếu cột cho phép NULL
            final_van_ban_data_for_sql = {}
            for key, value in van_ban_data.items():
                # Ở đây bạn có thể quyết định có muốn loại bỏ các trường có giá trị None hay không
                # Ví dụ: if value is not None:
                # Tuy nhiên, nếu cột trong DB cho phép NULL, việc gửi None là chấp nhận được.
                # Hiện tại, chúng ta sẽ bao gồm tất cả các key có trong van_ban_data.
                columns.append(key)
                placeholders.append(f":{key}")
                final_van_ban_data_for_sql[key] = value

            if not columns: # Nếu không có cột nào (trường hợp hiếm)
                 return {
                    "success": False,
                    "message": "Không có dữ liệu để thêm vào văn bản AI.",
                }

            insert_van_ban_ai_query_str = f"""
                INSERT INTO VanBanAI (
                    {', '.join(columns)}
                ) VALUES (
                    {', '.join(placeholders)}
                )
            """
            insert_van_ban_ai_query = text(insert_van_ban_ai_query_str)
            
            # Thực thi câu lệnh query
            try:
                db.execute(insert_van_ban_ai_query, final_van_ban_data_for_sql)
                db.commit()
            except Exception as e:
                db.rollback()
                return {
                    "success": False,
                    "message": "Lỗi khi thực hiện insert vào database VanBanAI",
                    "error": str(e),
                    "query": insert_van_ban_ai_query_str, # Thêm câu query để debug
                    "data_sent": final_van_ban_data_for_sql # Thêm data đã gửi để debug
                }
            
            return {
                "success": True,
                "message": "Thêm văn bản AI thành công",
                "van_ban_id": final_van_ban_data_for_sql.get("VanBanAIID") # Lấy ID từ dữ liệu đã được chèn
            }
            
        except Exception as e:
            # db.rollback() # Rollback ở đây có thể không cần thiết nếu đã rollback ở inner try-except
            return {
                "success": False,
                "message": "Lỗi xử lý chung khi thêm văn bản AI",
                "error": str(e)
            }

    @staticmethod
    async def insert_bang_du_lieu_chi_tiet_ai(
        db: Session, 
        chi_tiet_data: List[Dict[str, Any]],
        required_columns: List[str]
    ) -> Dict[str, Any]:
        try:
            if not chi_tiet_data:
                return {
                    "success": True,
                    "message": "Không có chi tiết để thêm"
                }

            # Build dynamic SQL query based on required columns
            columns = ["BangDuLieuChiTietAIID", "VanBanAIID"] + required_columns
            placeholders = [f":{col}" for col in columns]
            
            insert_chi_tiet_query_str = f"""
                INSERT INTO BangDuLieuChiTietAI (
                    {', '.join(columns)}
                ) VALUES (
                    {', '.join(placeholders)}
                )
            """
            insert_chi_tiet_query = text(insert_chi_tiet_query_str)

            for chi_tiet_item in chi_tiet_data: # Đổi tên biến để tránh trùng lặp
                # Generate a new UUID for each record
                current_item_data = chi_tiet_item.copy() # Làm việc trên bản sao để không thay đổi dữ liệu gốc
                current_item_data['BangDuLieuChiTietAIID'] = str(uuid.uuid4())
                
                # Convert numeric values to float
                for col in required_columns:
                    if (col.startswith('GiaTri') or col.startswith('SoTien')) and current_item_data.get(col):
                        try:
                            current_item_data[col] = convert_currency_to_int(str(current_item_data[col]))
                        except: # Bắt lỗi cụ thể hơn nếu có thể, ví dụ ValueError
                            current_item_data[col] = 0 # Hoặc None, hoặc log lỗi
                
                # Execute the query
                # print("insert_chi_tiet_query")
                # print(insert_chi_tiet_query_str)
                # print("chi_tiet_item_data")
                # print(current_item_data)
                db.execute(insert_chi_tiet_query, current_item_data)
            
            db.commit()
            
            return {
                "success": True,
                "message": "Thêm chi tiết vào BangDuLieuChiTietAI thành công"
            }
            
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": "Lỗi khi thêm chi tiết vào BangDuLieuChiTietAI",
                "error": str(e)
            }


    @staticmethod
    async def insert_bang_du_lieu_chi_tiet_ai(
        db: Session, 
        chi_tiet_data: List[Dict[str, Any]],
        required_columns: List[str]
    ) -> Dict[str, Any]:
        try:
            if not chi_tiet_data:
                return {
                    "success": True,
                    "message": "Không có chi tiết để thêm"
                }

            # Build dynamic SQL query based on required columns
            columns = ["BangDuLieuChiTietAIID", "VanBanAIID"] + required_columns
            placeholders = [f":{col}" for col in columns]
            
            insert_chi_tiet_query = text(f"""
                INSERT INTO BangDuLieuChiTietAI (
                    {', '.join(columns)}
                ) VALUES (
                    {', '.join(placeholders)}
                )
            """)

            for chi_tiet in chi_tiet_data:
                # Generate a new UUID for each record
                chi_tiet['BangDuLieuChiTietAIID'] = str(uuid.uuid4())
                
                # Convert numeric values to float
                for col in required_columns:
                    if (col.startswith('GiaTri') or col.startswith('SoTien')) and chi_tiet.get(col):
                        try:
                            chi_tiet[col] = convert_currency_to_int(str(chi_tiet[col]))
                        except:
                            chi_tiet[col] = 0
                
                # Execute the query
                print("insert_chi_tiet_query")
                print(insert_chi_tiet_query)
                print("chi_tiet")
                print(chi_tiet)
                db.execute(insert_chi_tiet_query, chi_tiet)
            
            db.commit()
            
            return {
                "success": True,
                "message": "Thêm chi tiết vào BangDuLieuChiTietAI thành công"
            }
            
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": "Lỗi khi thêm chi tiết vào BangDuLieuChiTietAI",
                "error": str(e)
            }

    @staticmethod
    async def save_document_data(
        db: Session,
        van_ban_data: Dict[str, Any],
        tong_muc_dau_tu_chi_tiet: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        try:
            # Insert main document
            van_ban_result = await DatabaseService.insert_van_ban(db, van_ban_data)
            if not van_ban_result["success"]:
                return van_ban_result

            # Insert TongMucDauTuChiTiet if exists
            if tong_muc_dau_tu_chi_tiet:
                # First insert into TongMucDauTuChiTiet
                chi_tiet_result = await DatabaseService.insert_tong_muc_dau_tu_chi_tiet(
                    db, 
                    tong_muc_dau_tu_chi_tiet
                )
                if not chi_tiet_result["success"]:
                    return chi_tiet_result

                # Then insert into BangDuLieuChiTietAI
                bang_du_lieu_result = await DatabaseService.insert_bang_du_lieu_chi_tiet_ai(
                    db,
                    tong_muc_dau_tu_chi_tiet,
                    ["CoCauVonID", "KMCPID", "TenKMCP", "GiaTriTMDTKMCP", "GiaTriTMDTKMCPTang", "GiaTriTMDTKMCPGiam"]
                )
                if not bang_du_lieu_result["success"]:
                    return bang_du_lieu_result

            return {
                "success": True,
                "message": "Lưu dữ liệu thành công",
                "van_ban_id": van_ban_data["VanBanID"]
            }

        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": "Lỗi khi lưu dữ liệu",
                "error": str(e)
            } 