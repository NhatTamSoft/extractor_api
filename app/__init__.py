from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Image Extraction API")

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Import and include routers
from app.routers import image_router, auth_router, health_router, extract_router

app.include_router(auth_router.router, prefix="/auth", tags=["Authentication"])
app.include_router(image_router.router, prefix="/images", tags=["Images"])
app.include_router(health_router.router, tags=["Health Check"])
app.include_router(extract_router.router, prefix="/extract", tags=["PDF Extraction"]) 