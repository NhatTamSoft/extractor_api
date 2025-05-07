import urllib
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Gán thông tin kết nối trực tiếp
DB_SERVER = "127.0.0.1,1433"  # Hoặc IP+cổng SQL Server
DB_NAME = "ProOnline_soctrang2016"
DB_USER = "sa"
DB_PASSWORD = "123456"

# Chuỗi kết nối
connection_string = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={DB_SERVER};"
    f"DATABASE={DB_NAME};"
    f"UID={DB_USER};"
    f"PWD={DB_PASSWORD};"
    f"TrustServerCertificate=yes;"
    f"MultipleActiveResultSets=true;"
)

# Mã hóa chuỗi kết nối
params = urllib.parse.quote_plus(connection_string)
SQLALCHEMY_DATABASE_URL = f"mssql+pyodbc:///?odbc_connect={params}"

# Tạo engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
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
