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
                    NgayThaotac,
                    TenLoaiVanBan,
                    DuAnID
                ) VALUES (
                    :VanBanAIID,
                    :SoVanBan,
                    :NgayKy,
                    :TrichYeu,
                    :ChucDanhNguoiKy,
                    :TenNguoiKy,
                    :NgayThaotac,
                    :TenLoaiVanBan,
                    :DuAnID
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
            van_ban_data.setdefault('TenLoaiVanBan', None)
            van_ban_data.setdefault('DuAnID', None)
            
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
        chi_tiet_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        try:
            if not chi_tiet_data:
                return {
                    "success": True,
                    "message": "Không có chi tiết để thêm"
                }

            # Insert BangDuLieuChiTietAI data
            insert_chi_tiet_query = text("""
                INSERT INTO BangDuLieuChiTietAI (
                    BangDuLieuChiTietAIID,
                    CoCauVonID,
                    KMCPID,
                    VanBanAIID,
                    TenKMCP,
                    GiaTriTMDTKMCP,
                    GiaTriTMDTKMCP_DC,
                    GiaTriTMDTKMCPTang,
                    GiaTriTMDTKMCPGiam
                ) VALUES (
                    :BangDuLieuChiTietAIID,
                    :CoCauVonID,
                    :KMCPID,
                    :VanBanAIID,
                    :TenKMCP,
                    :GiaTriTMDTKMCP,
                    :GiaTriTMDTKMCP_DC,
                    :GiaTriTMDTKMCPTang,
                    :GiaTriTMDTKMCPGiam
                )
            """)

            for chi_tiet in chi_tiet_data:
                # Generate a new UUID for each record
                chi_tiet['BangDuLieuChiTietAIID'] = str(uuid.uuid4())
                
                # Set default values for optional fields
                chi_tiet.setdefault('CoCauVonID', None)
                chi_tiet.setdefault('KMCPID', None)
                
                # Execute the query
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
                    tong_muc_dau_tu_chi_tiet
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