import os
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal, File as FileModel
from auth import decode_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter()
security = HTTPBearer()

UPLOAD_DIR = "/app/uploads"
ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif", "video/mp4", "video/webm"]
EXPIRATION_OPTIONS = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "permanent": None
}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        return decode_token(credentials.credentials)
    except:
        raise HTTPException(status_code=401, detail="Token invalide")

@router.post("/upload")
def upload_file(
    folder: str,
    expiration: str = "7d",
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Type de fichier non autorisé")

    if expiration not in EXPIRATION_OPTIONS:
        raise HTTPException(status_code=400, detail="Expiration invalide")

    if expiration == "permanent" and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Seul un admin peut uploader en permanent")

    extension = file.filename.split(".")[-1]
    unique_name = f"{uuid.uuid4().hex}.{extension}"
    folder_path = os.path.join(UPLOAD_DIR, folder)
    os.makedirs(folder_path, exist_ok=True)

    with open(os.path.join(folder_path, unique_name), "wb") as f:
        f.write(file.file.read())

    expires_at = datetime.utcnow() + EXPIRATION_OPTIONS[expiration] if EXPIRATION_OPTIONS[expiration] else None

    db_file = FileModel(
        filename=unique_name,
        original_name=file.filename,
        folder=folder,
        filetype="video" if file.content_type.startswith("video") else "image",
        uploaded_by=user["sub"],
        expires_at=expires_at
    )
    db.add(db_file)
    db.commit()

    return {"url": f"/files/{folder}/{unique_name}"}