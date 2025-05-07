from sqlalchemy import text
from app.core.database import get_db
import logging
from datetime import datetime

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseService:
    @staticmethod
    async def insert_ho_so_luu_tru(mapped_data: dict):
        db = None
        try:
            db = next(get_db())
            
            # Loại bỏ cột IDENTITY khỏi dữ liệu insert
            insert_data = {k: v for k, v in mapped_data.items() if k != 'sttHoSoLuuTruCTpr'}
            
            # Chuyển đổi kiểu dữ liệu
            processed_data = {}
            for key, value in insert_data.items():
                if key in ['sttHoSoLuuTrupr_sd', 'sttDuAnpr_sd', 'sttPhongLuuTrupr_sd', 'maDonVipr_sd', 'nguoiThaoTac']:
                    # Chuyển đổi sang decimal
                    try:
                        processed_data[key] = float(value) if value and str(value).strip() else None
                    except:
                        processed_data[key] = None
                elif key in ['soLuongTrang', 'soTTVBTrongHS', 'toSo']:
                    # Chuyển đổi sang int
                    try:
                        processed_data[key] = int(value) if value and str(value).strip() else None
                    except:
                        processed_data[key] = None
                elif key in ['ngayKy', 'ngayThaoTac']:
                    # Chuyển đổi sang datetime
                    try:
                        if value and str(value).strip():
                            processed_data[key] = datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
                        else:
                            processed_data[key] = None
                    except:
                        processed_data[key] = None
                else:
                    # Các trường khác giữ nguyên
                    processed_data[key] = value if value else None
            
            # Log dữ liệu trước khi insert
            logger.info(f"Preparing to insert data with keys: {list(processed_data.keys())}")
            
            # Chỉ lấy các trường có trong processed_data
            columns = ', '.join(processed_data.keys())
            values = ', '.join([f':{key}' for key in processed_data.keys()])
            
            query = f"""
            INSERT INTO [dbo].[tblHoSoLuuTruCT] 
            ({columns})
            VALUES 
            ({values})
            """
            
            # Log câu query
            logger.info(f"Generated SQL query: {query}")
            logger.info(f"Data to insert: {processed_data}")
            
            # Thực hiện insert
            result = db.execute(text(query), processed_data)
            db.commit()
            
            logger.info("Data inserted successfully")
            
            return {
                "success": True,
                "message": "Thêm dữ liệu thành công!",
                "inserted_id": result.lastrowid
            }
            
        except Exception as e:
            if db:
                db.rollback()
            
            # Log chi tiết lỗi
            logger.error(f"Error inserting data: {str(e)}")
            logger.error(f"Data that caused error: {mapped_data}")
            
            return {
                "success": False,
                "message": "Lỗi khi thêm dữ liệu!",
                "error": str(e),
                "error_details": {
                    "data_keys": list(mapped_data.keys()) if mapped_data else None,
                    "error_type": type(e).__name__
                }
            }
        finally:
            if db:
                db.close() 