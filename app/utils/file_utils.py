import os
from typing import Optional
from fastapi import UploadFile, HTTPException
import shutil
from ..core.config import settings

async def save_upload_file(upload_file: UploadFile, destination: str) -> str:
    """Save uploaded file to destination"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        # Save file
        with open(destination, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
        
        return destination
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")

def validate_file_size(file: UploadFile) -> bool:
    """Validate file size"""
    if file.size and file.size > settings.max_file_size:
        return False
    return True

def validate_file_type(file: UploadFile, allowed_types: list) -> bool:
    """Validate file type"""
    if file.content_type not in allowed_types:
        return False
    return True

def get_file_extension(filename: str) -> str:
    """Get file extension"""
    return os.path.splitext(filename)[1].lower()

def generate_unique_filename(original_filename: str) -> str:
    """Generate unique filename"""
    import uuid
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    extension = get_file_extension(original_filename)
    
    return f"{timestamp}_{unique_id}{extension}"