from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, List, Any
import uuid
from datetime import datetime

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
    async def insert_van_ban_ai(db: Session, van_ban_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Insert main document data
            insert_van_ban_query = text("""
                INSERT INTO VanBanAI (
                    VanBanAIID,
                    SoVanBan,
                    NgayKy,
                    TrichYeu,
                    ChucDanhNguoiKy,
                    TenNguoiKy,
                    NgayThaotac
                ) VALUES (
                    :VanBanAIID,
                    :SoVanBan,
                    :NgayKy,
                    :TrichYeu,
                    :ChucDanhNguoiKy,
                    :TenNguoiKy,
                    :NgayThaotac
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
    async def insert_tong_muc_dau_tu_chi_tiet(
        db: Session, 
        tong_muc_dau_tu_chi_tiet: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        try:
            if not tong_muc_dau_tu_chi_tiet:
                return {
                    "success": True,
                    "message": "Không có chi tiết tổng mức đầu tư để thêm"
                }

            # Insert TongMucDauTuChiTiet data
            insert_chi_tiet_query = text("""
                INSERT INTO TongMucDauTuChiTiet (
                    VanBanID,
                    TenKMCP,
                    GiaTri,
                    GiaTriDieuChinh
                ) VALUES (
                    :VanBanID,
                    :TenKMCP,
                    :GiaTri,
                    :GiaTriDieuChinh
                )
            """)
            
            for chi_tiet in tong_muc_dau_tu_chi_tiet:
                db.execute(insert_chi_tiet_query, chi_tiet)
            
            db.commit()
            
            return {
                "success": True,
                "message": "Thêm chi tiết tổng mức đầu tư thành công"
            }
            
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": "Lỗi khi thêm chi tiết tổng mức đầu tư",
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
                chi_tiet_result = await DatabaseService.insert_tong_muc_dau_tu_chi_tiet(
                    db, 
                    tong_muc_dau_tu_chi_tiet
                )
                if not chi_tiet_result["success"]:
                    return chi_tiet_result

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