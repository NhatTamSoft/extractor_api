from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Endpoint để kiểm tra xem API có hoạt động hay không
    """
    return {
        "status": "healthy",
        "message": "API is running normally"
    } 