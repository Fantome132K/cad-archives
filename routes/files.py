import os
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from database import SessionLocal, File as FileModel

router = APIRouter()

UPLOAD_DIR_CLASSIFIED = "/app/uploads/classified"
UPLOAD_DIR_QUICKDROP = "/app/uploads/quickdrop"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/images/quickdrop/{filename}")
def serve_quickdrop(filename: str, db: Session = Depends(get_db)):
    file = db.query(FileModel).filter(
        FileModel.filename == filename,
        FileModel.is_quick_drop == True
    ).first()

    if not file:
        raise HTTPException(status_code=404, detail="Fichier introuvable")

    if file.expires_at and file.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Ce fichier a expiré")

    path = os.path.join(UPLOAD_DIR_QUICKDROP, filename)
    return FileResponse(path)

@router.get("/images/classified/{folder}/{filename}")
def serve_classified(folder: str, filename: str, db: Session = Depends(get_db)):
    file = db.query(FileModel).filter(
        FileModel.folder == folder,
        FileModel.filename == filename
    ).first()

    if not file:
        raise HTTPException(status_code=404, detail="Fichier introuvable")

    if file.expires_at and file.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Ce fichier a expiré")

    path = os.path.join(UPLOAD_DIR_CLASSIFIED, folder, filename)
    return FileResponse(path)

@router.get("/dossiers/{folder}")
def serve_folder(folder: str, db: Session = Depends(get_db)):
    files = db.query(FileModel).filter(
        FileModel.folder == folder,
        FileModel.is_quick_drop == False
    ).all()

    files = [f for f in files if not f.expires_at or f.expires_at > datetime.utcnow()]

    if not files:
        raise HTTPException(status_code=404, detail="Dossier introuvable ou vide")

    return {
        "folder": folder,
        "files": [
            {
                "filename": f.filename,
                "original_name": f.original_name,
                "filetype": f.filetype,
                "url": f"/images/classified/{folder}/{f.filename}",
                "expires_at": f.expires_at
            }
            for f in files
        ]
    }