from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends, Form, Header
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel
import os
import base64
from io import BytesIO
from PIL import Image
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv
from app.services.database_service import DatabaseService
from app.services.prompt_service import PromptService
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
import shutil
from fastapi.responses import JSONResponse
from app.services.DungChung import convert_currency_to_int, lay_du_lieu_tu_sql_server, thuc_thi_truy_van, decode_jwt_token, LayMaDoiTuong, pdf_to_images, extract_text_from_images_azure, extract_text_from_images_google_cloud
from app.services.anh_xa_tuong_dong import tim_kiem_tuong_dong
from app.core.auth import get_current_user
from app.schemas.user import User
import pandas as pd
import httpx
import re
from app.services.DungChung import encode_image_to_base64 
from openai import OpenAI
from unidecode import unidecode
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult, DocumentTable, DocumentLine, AnalyzeDocumentRequest, DocumentContentFormat
from azure.core.credentials import AzureKeyCredential
import tempfile
import fitz  # PyMuPDF for PDF processing
import traceback
import PIL
import openpyxl
from fastapi import UploadFile, File, HTTPException, Query, Depends, Form, Header
import logging
from tempfile import SpooledTemporaryFile
import requests
from google.cloud import vision
from google.api_core.client_options import ClientOptions

# Load biến môi trường từ file .env
load_dotenv()

router = APIRouter()

model_openai = os.getenv('MODEL_API_OPENAI')

# Khởi tạo PromptService
prompt_service = PromptService()

# Định nghĩa IMAGE_STORAGE_PATH
IMAGE_STORAGE_PATH = os.getenv('IMAGE_STORAGE_PATH', 'image_storage')
ALLOWED_PDF_TYPE = 'application/pdf'
os.makedirs(IMAGE_STORAGE_PATH, exist_ok=True)

# Định nghĩa các định dạng ảnh được chấp nhận
ALLOWED_IMAGE_TYPES = {
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/bmp',
    'image/webp'
}

# Azure Form Recognizer configuration
AZURE_ENDPOINT = os.getenv('AZURE_FORM_RECOGNIZER_ENDPOINT')
AZURE_KEY = os.getenv('AZURE_FORM_RECOGNIZER_KEY')

# Initialize Azure client
azure_client = DocumentIntelligenceClient(
    endpoint=AZURE_ENDPOINT, credential=AzureKeyCredential(AZURE_KEY)
)

class MultiImageExtractRequest(BaseModel):
    pages: Optional[List[int]] = None

class DocumentExtractRequest(BaseModel):
    file_type: str  # 'image' or 'pdf'
    pages: Optional[List[int]] = None  # For PDF, specify which pages to process


@router.post("/document_extract_SoHoa")
async def extract_document_SoHoa(
    files: List[UploadFile] = File(...),
    file_type: str = Form(...),  # 'image' or 'pdf'
    pages: Optional[str] = Form(None)  # Comma-separated list of page numbers for PDF
):
    # Load require_fields from Markdown file
    try:
        with open('data/require_fields.md', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Parse markdown content to extract field information
        require_fields = []
        current_field = None
        in_mapping_table = False
        
        for line in content.split('\n'):
            line = line.strip()
            if not line:  # Skip empty lines
                continue
                
            # Check for field headers (## number. fieldName)
            if line.startswith('## '):
                if current_field:
                    require_fields.append(current_field)
                parts = line.split('. ', 1)  # Split only on first occurrence
                if len(parts) == 2:
                    field_name = parts[1].strip()
                    current_field = {
                        "tenTruong": field_name,
                        "moTa": "",
                        "extractionRules": {}
                    }
                    in_mapping_table = False
                continue

            # Check for description
            if line.startswith('**Mô tả:**'):
                if current_field:
                    current_field["moTa"] = line.replace('**Mô tả:**', '').strip()
                continue

            # Check for extraction rules section
            if line.startswith('**Quy tắc trích xuất:**'):
                continue

            # Check for rule items
            if line.startswith('- **'):
                if current_field:
                    parts = line.split(':**', 1)  # Split only on first occurrence
                    if len(parts) == 2:
                        key = parts[0].replace('- **', '').strip()
                        value = parts[1].strip()
                        current_field["extractionRules"][key] = value
                continue

            # Check for mapping table header
            if '| Mã | Giá trị |' in line:
                if current_field and 'mapping' not in current_field["extractionRules"]:
                    current_field["extractionRules"]["mapping"] = {}
                in_mapping_table = True
                continue

            # Check for mapping table rows
            if in_mapping_table and line.startswith('|'):
                if current_field:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 3:  # Ensure we have enough parts
                        code = parts[1].strip()
                        value = parts[2].strip()
                        if code and value:  # Only add if both code and value exist
                            current_field["extractionRules"]["mapping"][code] = value
                continue

            # Reset mapping table flag if we encounter a non-table line
            if in_mapping_table and not line.startswith('|'):
                in_mapping_table = False

        # Add the last field if exists
        if current_field:
            require_fields.append(current_field)

        if not require_fields:
            raise ValueError("No fields were parsed from require_fields.md")
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "code": 500,
                "message": "Lỗi đọc file require_fields.md",
                "detail": f"Error parsing file: {str(e)}"
            }
        )

    # Validate file type
    if file_type not in ['image', 'pdf']:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "code": 400,
                "message": "Invalid file type",
                "detail": "file_type must be either 'image' or 'pdf'"
            }
        )

    # Validate files based on type
    if file_type == 'image':
        for file in files:
            if file.content_type not in ALLOWED_IMAGE_TYPES:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "code": 400,
                        "message": f"Invalid file type for {file.filename}",
                        "detail": f"Expected image file, got {file.content_type}"
                    }
                )
    else:  # PDF
        if len(files) > 1:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "code": 400,
                    "message": "Only one PDF file can be uploaded at a time",
                    "detail": "Multiple files are only allowed for images"
                }
            )
        if files[0].content_type != ALLOWED_PDF_TYPE:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "code": 400,
                    "message": "Invalid file type",
                    "detail": "Expected PDF file"
                }
            )

    # Parse pages parameter for PDF
    selected_pages = None
    if file_type == 'pdf' and pages:
        try:
            selected_pages = [int(p.strip()) for p in pages.split(',')]
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "code": 400,
                    "message": "Invalid pages parameter",
                    "detail": "Pages must be comma-separated numbers"
                }
            )

    # Initialize combined data
    combined_data = {}

    try:
        if file_type == 'image':
            # Process each image file
            for file in files:
                await process_image_file(file, require_fields, combined_data)
        else:
            # Process PDF file
            await process_pdf_file(files[0], selected_pages, require_fields, combined_data)

        return {
            "status": "success",
            "data": combined_data
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "code": 500,
                "message": "Error processing document",
                "detail": str(e)
            }
        )
    
def get_code_from_mapping(value: str, mapping_table: Dict[str, str]) -> str:
    """Convert a value to its corresponding ID from a mapping table"""
    # Normalize the input value
    value = value.strip().lower()
    
    # Try direct mapping
    for code, mapped_value in mapping_table.items():
        if mapped_value.lower() == value:
            # Return the ID instead of the code
            return code
            
    # If no direct match, return the original value
    return value

async def process_image_file(file: UploadFile, require_fields: List[Dict], combined_data: Dict):
    """Process a single image file"""
    try:
        # Read file content
        content = await file.read()
        
        # Convert image to base64
        image_base64 = base64.b64encode(content).decode('utf-8')
        
        # Process with OpenAI
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI assistant that extracts information from documents according to the provided field definitions and rules. For fields with mapping tables, you MUST return the ID (not the code or value). You MUST return a valid JSON object."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Extract information from the following image according to these field definitions and rules:\n{json.dumps(require_fields, ensure_ascii=False, indent=2)}"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=4000,
            temperature=0,
            response_format={"type": "json_object"}
        )

        # Parse response
        response_text = response.choices[0].message.content
        
        # Clean up response text
        if response_text.strip().startswith("```json"):
            response_text = response_text.strip()[7:-3].strip()
        elif response_text.strip().startswith("```"):
            response_text = response_text.strip()[3:-3].strip()

        # Parse JSON response
        data = json.loads(response_text)
        
        # Post-process fields with mapping tables
        for field in require_fields:
            field_name = field["tenTruong"]
            if "extractionRules" in field and "mapping" in field["extractionRules"]:
                if field_name in data and data[field_name]:
                    data[field_name] = get_code_from_mapping(
                        data[field_name], 
                        field["extractionRules"]["mapping"]
                    )
        
        # Update combined data
        for key, value in data.items():
            if key not in combined_data or not combined_data[key]:
                combined_data[key] = value

    except Exception as e:
        raise Exception(f"Error processing image file {file.filename}: {str(e)}")

async def process_pdf_file(file: UploadFile, selected_pages: Optional[List[int]], require_fields: List[Dict], combined_data: Dict):
    """Process a PDF file"""
    temp_file_path = None
    doc = None
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()
            temp_file_path = temp_file.name

        # Read PDF pages
        doc = fitz.open(temp_file_path)
        total_pages = len(doc)

        if selected_pages is None:
            selected_pages = list(range(1, total_pages + 1))

        # Process each selected page
        for page_num in selected_pages:
            if 1 <= page_num <= total_pages:
                page = doc.load_page(page_num - 1)
                
                # Convert page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72), alpha=False)
                img = Image.frombuffer("RGB", [pix.width, pix.height], pix.samples, "raw", "RGB", 0, 1)
                
                # Convert image to base64
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                image_base64 = base64.b64encode(buffered.getvalue()).decode()

                # Process with OpenAI
                client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": """You are an AI assistant that extracts information from documents. 
                            For fields with mapping tables, you MUST return the ID (not the code or value).
                            For example, if the language is 'Tiếng Việt', return '92CD991B-B7DB-4AA6-B217-F345954B91C6' instead of '01'.
                            You MUST return a valid JSON object containing the mapped fields. 
                            Do not include any other text or explanation in your response."""
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"""
                                    Extract and map information from the following PDF page to the specified fields.
                                    Return ONLY a JSON object with the following structure:
                                    {{
                                        "docId": "string or null",
                                        "arcDocCode": "string or null",
                                        "maintenance": "string or null",
                                        "typeName": "string or null",
                                        "codeNumber": "string or null",
                                        "codeNotation": "string or null",
                                        "issuedDate": "string or null",
                                        "organName": "string or null",
                                        "subject": "string or null",
                                        "language": "string or null",
                                        "numberOfPage": "string or null",
                                        "inforSign": "string or null",
                                        "keyword": "string or null",
                                        "mode": "string or null",
                                        "confidenceLevel": "string or null",
                                        "autograph": "string or null",
                                        "format": "string or null",
                                        "process": "string or null",
                                        "riskRecovery": "string or null",
                                        "riskRecoveryStatus": "string or null",
                                        "description": "string or null",
                                        "SignerTitle": "string or null",
                                        "SignerName": "string or null"
                                    }}

                                    Field definitions and extraction rules:
                                    {json.dumps(require_fields, ensure_ascii=False, indent=2)}

                                    IMPORTANT: For fields with mapping tables, return the ID (not the code or value).
                                    For example:
                                    - For language: return '92CD991B-B7DB-4AA6-B217-F345954B91C6' for 'Tiếng Việt', '02' for 'Tiếng Anh'
                                    - For maintenance: return '01' for 'Vĩnh viễn', '02' for '70 năm'
                                    - For typeName: return '01' for 'Nghị quyết', '02' for 'Quyết định'
                                    - For mode: return '01' for 'Công khai', '02' for 'Sử dụng có điều kiện'
                                    - For confidenceLevel: return '01' for 'Gốc điện tử', '02' for 'Số hóa'
                                    - For format: return '01' for 'Tốt', '02' for 'Bình thường'
                                    - For process: return '0' for 'Không có quy trình xử lý đi kèm', '1' for 'Có quy trình xử lý đi kèm'
                                    - For riskRecovery: return '0' for 'Không', '1' for 'Có'
                                    - For riskRecoveryStatus: return '01' for 'Đã dự phòng', '02' for 'Chưa dự phòng'
                                    """
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{image_base64}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=4000,
                    temperature=0,
                    response_format={"type": "json_object"}
                )

                # Parse response
                response_text = response.choices[0].message.content
                
                # Clean up response text
                if response_text.strip().startswith("```json"):
                    response_text = response_text.strip()[7:-3].strip()
                elif response_text.strip().startswith("```"):
                    response_text = response_text.strip()[3:-3].strip()

                # Parse JSON response
                data = json.loads(response_text)
                
                # Post-process fields with mapping tables
                for field in require_fields:
                    field_name = field["tenTruong"]
                    if "extractionRules" in field and "mapping" in field["extractionRules"]:
                        if field_name in data and data[field_name]:
                            data[field_name] = get_code_from_mapping(
                                data[field_name], 
                                field["extractionRules"]["mapping"]
                            )
                
                # Update combined data
                for key, value in data.items():
                    if key not in combined_data or not combined_data[key]:
                        combined_data[key] = value

    except Exception as e:
        raise Exception(f"Error processing PDF file {file.filename}: {str(e)}")
    finally:
        # Close the PDF document if it's open
        if doc:
            doc.close()
        
        # Delete the temporary file if it exists
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                print(f"Warning: Could not delete temporary file {temp_file_path}: {str(e)}")
