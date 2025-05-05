from app.schemas.user import UserCreate, User
from app.core.auth import get_password_hash
from sqlalchemy.orm import Session
from app.models.user import User as UserModel
from app.core.database import get_db

async def get_user_by_username(username: str) -> User:
    """
    Get user by username
    """
    db = next(get_db())
    user = db.query(UserModel).filter(UserModel.username == username).first()
    return user

async def create_user(user: UserCreate) -> User:
    """
    Create new user
    """
    db = next(get_db())
    hashed_password = get_password_hash(user.password)
    db_user = UserModel(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user 