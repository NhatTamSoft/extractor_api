from sqlalchemy import Boolean, Column, Integer, String
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, index=True)        # ✅ fix
    email = Column(String(255), unique=True, index=True, nullable=True)  # ✅ fix
    full_name = Column(String(255), nullable=True)                # ✅ fix
    hashed_password = Column(String(255))                         # ✅ fix
    is_active = Column(Boolean, default=True)

    def verify_password(self, password: str) -> bool:
        from app.core.auth import verify_password
        return verify_password(password, self.hashed_password)
