import os
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import SessionLocal, File as FileModel
from auth import decode_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter()
security = HTTPBearer(auto_error=False)
limiter = Limiter(key_func=get_remote_address)

UPLOAD_DIR_CLASSIFIED = "/app/uploads/classified"
UPLOAD_DIR_QUICKDROP = "/app/uploads/quickdrop"

MAX_SIZE_IMAGE = 50 * 1024 * 1024   # 50Mo
MAX_SIZE_VIDEO = 500 * 1024 * 1024  # 500Mo

ALLOWED_TYPES = {
    "image/jpeg": "image",
    "image/png": "image",
    "image/webp": "image",
    "image/gif": "image",
    "video/mp4": "video",
    "video/webm": "video"
}

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
    if not credentials:
        return None
    try:
        return decode_token(credentials.credentials)
    except:
        return None

@router.post("/upload")
@limiter.limit("10/hour")
def upload_file(
    request: Request,
    folder: str = None,
    expiration: str = "7d",
    nsfw: bool = False,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    # Validation type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Type de fichier non autorisé")

    # Lecture et validation taille
    content = file.file.read()
    filetype = ALLOWED_TYPES[file.content_type]
    max_size = MAX_SIZE_VIDEO if filetype == "video" else MAX_SIZE_IMAGE

    if len(content) > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"Fichier trop volumineux — Max {'500Mo' if filetype == 'video' else '50Mo'}"
        )

    # Validation expiration
    if expiration not in EXPIRATION_OPTIONS:
        raise HTTPException(status_code=400, detail="Expiration invalide")

    # Permanent réservé aux admins
    if expiration == "permanent" and (not user or user.get("role") != "admin"):
        raise HTTPException(status_code=403, detail="Stockage permanent réservé aux admins")

    # Génération nom unique
    extension = file.filename.split(".")[-1].lower()
    unique_name = f"{uuid.uuid4().hex}.{extension}"

    # Détermine si c'est un quick drop ou classified
    is_quick_drop = user is None
    session_id = request.cookies.get("cad_session") if is_quick_drop else None

    if is_quick_drop:
        # Quick drop — expiration max 7 jours
        if expiration not in ["24h", "7d"]:
            expiration = "7d"
        save_dir = UPLOAD_DIR_QUICKDROP
        uploaded_by = session_id or "anonymous"
    else:
        # Classified — dossier obligatoire
        if not folder:
            raise HTTPException(status_code=400, detail="Dossier requis pour un upload classifié")
        save_dir = os.path.join(UPLOAD_DIR_CLASSIFIED, folder)
        uploaded_by = user["sub"]

    os.makedirs(save_dir, exist_ok=True)

    with open(os.path.join(save_dir, unique_name), "wb") as f:
        f.write(content)

    expires_at = datetime.utcnow() + EXPIRATION_OPTIONS[expiration] if EXPIRATION_OPTIONS[expiration] else None

    db_file = FileModel(
        filename=unique_name,
        original_name=file.filename,
        folder=folder,
        filetype=filetype,
        uploaded_by=uploaded_by,
        is_quick_drop=is_quick_drop,
        session_id=session_id,
        expires_at=expires_at,
        nsfw=nsfw
    )
    db.add(db_file)
    db.commit()

    base_url = "/images/quickdrop" if is_quick_drop else f"/images/classified/{folder}"
    return {"url": f"{base_url}/{unique_name}"}