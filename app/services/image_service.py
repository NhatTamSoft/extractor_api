from PIL import Image
import os
from app.core.config import settings

async def process_image(image_path: str) -> dict:
    """
    Process the uploaded image and return relevant information
    """
    try:
        with Image.open(image_path) as img:
            # Get basic image information
            image_info = {
                "format": img.format,
                "mode": img.mode,
                "size": img.size,
                "width": img.width,
                "height": img.height,
            }
            
            # Add any additional processing here
            # For example: OCR, object detection, etc.
            
            return image_info
    except Exception as e:
        raise Exception(f"Error processing image: {str(e)}")

def allowed_file(filename: str) -> bool:
    """
    Check if the file extension is allowed
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in settings.ALLOWED_EXTENSIONS 