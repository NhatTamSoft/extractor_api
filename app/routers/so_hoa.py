from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends, Form, Header
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel
import os
import base64
from io import BytesIO
from PIL import Image
import json
from dotenv import load_dotenv
from app.services.prompt_service import PromptService
from fastapi.responses import JSONResponse
from openai import OpenAI
from unidecode import unidecode
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult, DocumentTable, DocumentLine, AnalyzeDocumentRequest, DocumentContentFormat
from azure.core.credentials import AzureKeyCredential
import tempfile
import fitz  # PyMuPDF for PDF processing
import traceback
from fastapi import UploadFile, File, HTTPException, Query, Depends, Form, Header
from google.cloud import vision
from google.api_core.client_options import ClientOptions
import google.generativeai as genai
import re
from pathlib import Path
from datetime import datetime

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

def load_prompt_template():
    """Load prompt template from file"""
    prompt_path = Path(__file__).parent.parent.parent / "data" / "document_extract_prompt.md"
    with open(prompt_path, "r", encoding="utf-8") as f:
        content = f.read()
        # Split content into system and user messages
        parts = content.split("# User Message")
        system_message = parts[0].replace("# System Message", "").strip()
        user_message = parts[1].strip()
        return system_message, user_message

@router.post("/document_extract_SoHoa")
async def extract_document_SoHoa(
    files: List[UploadFile] = File(...),
    file_type: str = Form(...),  # 'image' or 'pdf'
    pages: Optional[str] = Form(None),  # Comma-separated list of page numbers for PDF
    ocr_type: str = Form("azure"),  # 'azure' or 'google_cloud'
    chat_type: str = Form("gemini")  # 'gemini' or 'chatgpt'
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

    # Validate OCR type
    if ocr_type not in ['azure', 'google_cloud']:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "code": 400,
                "message": "Invalid OCR type",
                "detail": "ocr_type must be either 'azure' or 'google_cloud'"
            }
        )

    # Validate chat type
    if chat_type not in ['gemini', 'chatgpt']:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "code": 400,
                "message": "Invalid chat type",
                "detail": "chat_type must be either 'gemini' or 'chatgpt'"
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
                await process_image_file(file, require_fields, combined_data, ocr_type, chat_type)
        else:
            # Process PDF file
            await process_pdf_file(files[0], selected_pages, require_fields, combined_data, ocr_type, chat_type)

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

async def process_image_file(file: UploadFile, require_fields: List[Dict], combined_data: Dict, ocr_type: str, chat_type: str):
    """Process a single image file"""
    try:
        # Read file content
        content = await file.read()
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # Extract text using selected OCR type
            if ocr_type == 'azure':
                extracted_text = extract_text_from_images_azure([temp_file_path])
            else:  # google_cloud
                extracted_text = extract_text_from_images_google_cloud([temp_file_path])

            # Convert image to base64 for chat model
            image_base64 = base64.b64encode(content).decode('utf-8')

            # Load prompt template
            system_message, user_message = load_prompt_template()
            
            # Format user message with OCR text
            formatted_user_message = f"""
            {user_message}
            ===BẮT ĐẦU_VĂN_BẢN_OCR===
            {extracted_text}
            ===KẾT_THÚC_VĂN_BẢN_OCR===
            """

            # Process with selected chat model
            if chat_type == 'gemini':
                client = genai.GenerativeModel('gemini-2.0-flash')
                response = client.generate_content([
                    {
                        "parts": [
                            {
                                "text": formatted_user_message
                            },
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": image_base64
                                }
                            }
                        ]
                    }
                ])
                response_text = response.text
            else:  # chatgpt
                client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": system_message
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": formatted_user_message
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
                response_text = response.choices[0].message.content

            # Clean up response text
            if response_text.strip().startswith("```json"):
                response_text = response_text.strip()[7:-3].strip()
            elif response_text.strip().startswith("```"):
                response_text = response_text.strip()[3:-3].strip()

            # Parse JSON response
            try:
                # Nếu có ```json ``` bao ngoài
                match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                if not match:
                    # Nếu chỉ có ``` bao ngoài
                    match = re.search(r'```\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                if not match:
                    # Nếu không có markdown block, cố parse toàn bộ
                    match = re.search(r'(\{.*\})', response_text, re.DOTALL)

                if match:
                    clean_json = match.group(1)
                    data = json.loads(clean_json)
                else:
                    raise ValueError("Không tìm thấy JSON hợp lệ trong phản hồi AI")
            except json.JSONDecodeError as e:
                raise ValueError(f"Lỗi parse JSON từ AI: {str(e)}")
            
            # Update combined data
            for key, value in data.items():
                if key not in combined_data or not combined_data[key]:
                    combined_data[key] = value

        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception as e:
                    print(f"Warning: Could not delete temporary file {temp_file_path}: {str(e)}")

    except Exception as e:
        raise Exception(f"Error processing image file {file.filename}: {str(e)}")

async def process_pdf_file(file: UploadFile, selected_pages: Optional[List[int]], require_fields: List[Dict], combined_data: Dict, ocr_type: str, chat_type: str):
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
                
                # Save page image to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_img_file:
                    img.save(temp_img_file.name, format="PNG")
                    temp_img_path = temp_img_file.name

                try:
                    # Extract text using selected OCR type
                    if ocr_type == 'azure':
                        extracted_text = extract_text_from_images_azure([temp_img_path])
                    else:  # google_cloud
                        extracted_text = extract_text_from_images_google_cloud([temp_img_path])

                    # Convert image to base64
                    buffered = BytesIO()
                    img.save(buffered, format="PNG")
                    image_base64 = base64.b64encode(buffered.getvalue()).decode()

                    # Load prompt template
                    system_message, user_message = load_prompt_template()
                    
                    # Format user message with actual data
                    formatted_user_message = user_message.format(
                        extracted_text=extracted_text,
                        require_fields=json.dumps(require_fields, ensure_ascii=False, indent=2)
                    )

                    # Process with selected chat model
                    if chat_type == 'gemini':
                        client = genai.GenerativeModel('gemini-2.0-flash')
                        response = client.generate_content([
                            {
                                "parts": [
                                    {
                                        "text": formatted_user_message
                                    },
                                    {
                                        "inline_data": {
                                            "mime_type": "image/png",
                                            "data": image_base64
                                        }
                                    }
                                ]
                            }
                        ])
                        response_text = response.text
                    else:  # chatgpt
                        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                        response = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[
                                {
                                    "role": "system",
                                    "content": system_message
                                },
                                {
                                    "role": "user",
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": formatted_user_message
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
                        response_text = response.choices[0].message.content

                    # Clean up response text
                    if response_text.strip().startswith("```json"):
                        response_text = response_text.strip()[7:-3].strip()
                    elif response_text.strip().startswith("```"):
                        response_text = response_text.strip()[3:-3].strip()

                    # Parse JSON response
                    data = json.loads(response_text)
                    
                    # Update combined data
                    for key, value in data.items():
                        if key not in combined_data or not combined_data[key]:
                            combined_data[key] = value

                finally:
                    # Clean up temporary image file
                    if os.path.exists(temp_img_path):
                        try:
                            os.remove(temp_img_path)
                        except Exception as e:
                            print(f"Warning: Could not delete temporary file {temp_img_path}: {str(e)}")

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

def extract_text_from_images_azure(image_files: List[str]) -> str:
    """
    Extract text and table data from images using Azure Form Recognizer.

    Args:
        image_files (List[str]): List of image file paths.

    Returns:
        str: Extracted content including text and tables.
    """
    combined_text = ""

    for file_path in image_files:
        print(f"\n=== Processing file: {file_path} ===")
        try:
            with open(file_path, "rb") as f:
                poller = azure_client.begin_analyze_document("prebuilt-layout", document=f)
                result = poller.result()

            # Text extraction
            text_lines = []
            for page in result.pages:
                for line in page.lines:
                    text_lines.append(line.content)
            if text_lines:
                combined_text += f"\n--- Text from {file_path} ---\n"
                combined_text += "\n".join(text_lines) + "\n"
            else:
                combined_text += f"\n--- No text found in {file_path} ---\n"

            # Table extraction
            if result.tables:
                combined_text += f"\n--- Tables from {file_path} ---\n"
                for i, table in enumerate(result.tables, 1):
                    combined_text += f"\nTable {i} (Rows: {table.row_count}, Columns: {table.column_count}):\n"
                    for row_index in range(table.row_count):
                        row = [cell.content or "" for cell in table.cells if cell.row_index == row_index]
                        combined_text += " | ".join(row) + "\n"
            else:
                combined_text += f"\n--- No tables found in {file_path} ---\n"

        except Exception as e:
            combined_text += f"\n[Error processing {file_path}]: {str(e)}\n"

    return combined_text

def extract_text_from_images_google_cloud(image_files: List[str]) -> str:
    """
    Extract text from images using Google Cloud Vision API.
    
    Args:
        image_files (List[str]): List of paths to image files
        0
    Returns:\
        str: Combined text extracted from all images
    """
    combined_text = ""
    client = vision.ImageAnnotatorClient()
    
    for temp_file in image_files:
        try:
            # Read the image file
            with open(temp_file, "rb") as f:
                content = f.read()

            # Create image object
            image = vision.Image(content=content)

            # Perform text detection
            response = client.document_text_detection(image=image)
            texts = response.text_annotations

            if texts:
                # Get the full text (first annotation contains the entire text)
                text_content = texts[0].description
                combined_text += text_content + "\n"
            else:
                print("No text detected in the image")

            if response.error.message:
                print(f"Cloud Vision API error: {response.error.message}")
                raise Exception(
                    '{}\nFor more info on error messages, check: '
                    'https://cloud.google.com/apis/design/errors'.format(
                        response.error.message))

        except Exception as e:
            print(f"Error processing file {temp_file}: {str(e)}")
            print(f"Error type: {type(e)}")
            print(f"Error details: {traceback.format_exc()}")
            continue
            
    return combined_text
