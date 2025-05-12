import urllib
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Gán thông tin kết nối trực tiếp
DB_SERVER = "103.162.21.146,1435"  # Thay đổi dấu : thành dấu ,
DB_NAME = "QLDA_AI"
DB_USER = "phonglt"
DB_PASSWORD = "@PhongLT2020!"

# Chuỗi kết nối
connection_string = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={DB_SERVER};"
    f"DATABASE={DB_NAME};"
    f"UID={DB_USER};"
    f"PWD={DB_PASSWORD};"
    f"TrustServerCertificate=yes;"
    f"MultipleActiveResultSets=true;"
    f"Connection Timeout=30;"  # Thêm timeout
)

# Mã hóa chuỗi kết nối
params = urllib.parse.quote_plus(connection_string)
SQLALCHEMY_DATABASE_URL = f"mssql+pyodbc:///?odbc_connect={params}"

# Tạo engine với các tùy chọn bổ sung
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_timeout=30,  # Thêm pool timeout
    pool_size=5,      # Giới hạn số lượng kết nối
    max_overflow=10   # Số lượng kết nối tối đa có thể tạo thêm
)

# Session và Base
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Hàm get_db để dùng trong FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
