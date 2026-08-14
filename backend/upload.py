from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from auth import get_current_user
from config import supabase
import uuid
import os

router = APIRouter(prefix="/api/upload", tags=["Upload"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".tiff", ".mp3", ".mp4", ".wav", ".pdf", ".doc", ".docx"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    # Check file extension
    _, ext = os.path.splitext(file.filename or "")
    ext = ext.lower()
    
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Read file content
    content = await file.read()
    
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds 50MB limit")
    
    # Generate unique filename
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = f"uploads/{current_user['sub']}/{unique_name}"
    
    if supabase:
        try:
            result = supabase.storage.from_("archives").upload(
                file_path,
                content,
                file_options={"content-type": file.content_type or "application/octet-stream"}
            )
            public_url = supabase.storage.from_("archives").get_public_url(file_path)
            return {
                "message": "File uploaded successfully",
                "url": public_url,
                "path": file_path,
                "filename": file.filename,
                "size": len(content),
            }
        except Exception as e:
            print(f"WARNING: Supabase storage upload failed ({e}). Saving to local uploads folder.")

    # Local fallback storage
    local_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "uploads")
    os.makedirs(local_dir, exist_ok=True)
    local_file_path = os.path.join(local_dir, unique_name)
    with open(local_file_path, "wb") as f:
        f.write(content)
        
    local_url = f"http://localhost:3000/uploads/{unique_name}"
    return {
        "message": "File uploaded successfully (Local storage)",
        "url": local_url,
        "path": local_file_path,
        "filename": file.filename,
        "size": len(content),
    }
