from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, List, Any
import uuid
from datetime import datetime
from app.services.DungChung import convert_currency_to_float

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
    async def insert_van_ban_ai(db: Session, van_ban_data: Dict[str, Any], loaiVanBan) -> Dict[str, Any]:
        try:
            # Insert main document data
            insert_van_ban_query = text("""
                INSERT INTO VanBanAI (
                    VanBanAIID,
                    SoVanBan,
                    NgayKy,
                    TrichYeu,
                    ChucDanhNguoiKy, 
                    CoQuanBanHanh,
                    NguoiKy,
                    NgayThaotac,
                    TenLoaiVanBan,
                    LoaiVanBanID,
                    GiaiDoanID,
                    GiaiDoan,
                    DieuChinh,
                    DuAnID,
                    JsonAI,
                    DataOCR,
                    TenFile
                ) VALUES (
                    :VanBanAIID,
                    :SoVanBan,
                    :NgayKy,
                    :TrichYeu,
                    :ChucDanhNguoiKy, 
                    :CoQuanBanHanh,
                    :NguoiKy,
                    :NgayThaotac,
                    :TenLoaiVanBan,
                    :LoaiVanBanID,
                    :GiaiDoanID,
                    :GiaiDoan,
                    :DieuChinh,
                    :DuAnID,
                    :JsonAI,
                    :DataOCR,
                    :TenFile
                )
            """)
            
            # Convert date format if NgayKy exists and is not empty
            if van_ban_data.get('NgayKy'):
                try:
                    van_ban_data['NgayKy'] = datetime.strptime(van_ban_data['NgayKy'], '%d/%m/%Y').strftime('%Y-%m-%d')
                except ValueError as e:
                    return {
                        "success": False,
                        "message": "Lỗi khi chuyển đổi định dạng ngày tháng",
                        "error": str(e)
                    }
            
            # Set default values for new fields if not provided
            if loaiVanBan == "BCDX_CT": # Báo cáo đề xuất chủ trương đầu tư
                van_ban_data.setdefault('LoaiVanBanID', "3d4566fb-cf78-42e0-bebb-b22018b53763")
                van_ban_data.setdefault('GiaiDoanID', "6F6BB0B9-92BF-4831-8053-6246F42929B6")
                van_ban_data.setdefault('GiaiDoan', "2")
            elif loaiVanBan == "QDPD_CT": # Phê duyệt chủ trương đầu tư
                if van_ban_data.get("DieuChinh") == "1":
                    van_ban_data.setdefault('LoaiVanBanID', "d8821afb-76a4-4b24-9fd3-ba1aa84e156d")
                else:
                    van_ban_data.setdefault('LoaiVanBanID', "550358d9-a68a-4122-89da-6fc7cb6df0df")
                van_ban_data.setdefault('GiaiDoanID', "AD8D512D-AA6B-4243-B651-A80A1CB59FFC")
                van_ban_data.setdefault('GiaiDoan', "2")
            elif loaiVanBan == "QDPDDT_CBDT": # Phê quyệt dự toán chuẩn bị đầu tư
                if van_ban_data.get("DieuChinh") == "1":
                    van_ban_data.setdefault('LoaiVanBanID', "8f4faa5a-9725-4f5f-bf8e-0862569936b3")
                else:
                    van_ban_data.setdefault('LoaiVanBanID', "ac6e7501-eea1-4546-9195-4e44ade01990")
                van_ban_data.setdefault('GiaiDoanID', "2BB4A12A-A588-48FC-9BE2-5B99E31F1212")
                van_ban_data.setdefault('GiaiDoan', "2")
            elif loaiVanBan == "QDPD_DA": # Phê duyệt dự án
                if van_ban_data.get("DieuChinh") == "1":
                    van_ban_data.setdefault('LoaiVanBanID', "f20710a1-7ea6-4c4a-9dec-52bea3d37f3d")
                else:
                    van_ban_data.setdefault('LoaiVanBanID', "4e31610d-31b7-4fbb-b530-c1f97b99e362")
                van_ban_data.setdefault('GiaiDoanID', "F9C3D581-53B2-4EBE-A223-1E0B4839A45A")
                van_ban_data.setdefault('GiaiDoan', "3")
            elif loaiVanBan == "QDPD_KHLCNT_CBDT": # Phê duyệt KHLCNT giai đoạn chuẩn bị đầu tư
                if van_ban_data.get("DieuChinh") == "1":
                    van_ban_data.setdefault('LoaiVanBanID', "f8f74942-566b-4ae9-b612-855f0fe63127")
                else:
                    van_ban_data.setdefault('LoaiVanBanID', "7017f242-e957-4e64-8048-3cff04519176")
                van_ban_data.setdefault('GiaiDoanID', "68B4F3FB-BBB1-45B3-92C1-7456E57CFB9E")
                van_ban_data.setdefault('GiaiDoan', "2")
            elif loaiVanBan == "QDPD_KHLCNT_THDT": # Phê duyệt KHLCNT giai đoạn thực hiện dự án
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
            van_ban_data.setdefault('DuAnID', "00000000-0000-0000-0000-000000000000")
            van_ban_data.setdefault('JsonAI', "")
            van_ban_data.setdefault('DataOCR', "")
            van_ban_data.setdefault('TenFile', "")
            van_ban_data.setdefault('CoQuanBanHanh', "")
            
            # Execute query
            try:
                db.execute(insert_van_ban_query, van_ban_data)
                db.commit()

            except Exception as e:
                db.rollback()
                return {
                    "success": False,
                    "message": "Lỗi khi thực hiện insert vào database",
                    "error": str(e)
                }
            
            return {
                "success": True,
                "message": "Thêm văn bản thành công",
                "van_ban_id": van_ban_data["VanBanAIID"]
            }
            
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": "Lỗi khi thêm văn bản",
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
                    if col.startswith('GiaTri') and chi_tiet.get(col):
                        try:
                            chi_tiet[col] = convert_currency_to_float(str(chi_tiet[col]))
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