import os
from datetime import datetime
from database import SessionLocal, File as FileModel

UPLOAD_DIR = "/app/uploads"

def delete_expired_files():
    db = SessionLocal()
    try:
        expired = db.query(FileModel).filter(
            FileModel.expires_at != None,
            FileModel.expires_at < datetime.utcnow()
        ).all()

        for file in expired:
            path = os.path.join(UPLOAD_DIR, file.folder, file.filename)
            if os.path.exists(path):
                os.remove(path)
            db.delete(file)

        db.commit()
        print(f"Nettoyage : {len(expired)} fichier(s) supprimé(s)")
    finally:
        db.close()