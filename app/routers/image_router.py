from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from typing import List
import os
from app.services.image_service import process_image
from app.core.config import settings

router = APIRouter()

@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    """
    Upload an image file and process it
    """
    try:
        # Save the uploaded file
        file_location = f"static/uploads/{file.filename}"
        os.makedirs("static/uploads", exist_ok=True)
        
        with open(file_location, "wb+") as file_object:
            file_object.write(await file.read())
        
        # Process the image
        result = await process_image(file_location)
        
        return {
            "message": "File uploaded successfully",
            "filename": file.filename,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{filename}")
async def get_image(filename: str):
    """
    Get an uploaded image by filename
    """
    file_path = f"static/uploads/{filename}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(file_path) 