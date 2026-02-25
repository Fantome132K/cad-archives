import uuid
from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from fastapi import Depends
from database import SessionLocal, Session as SessionModel, File as FileModel
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_or_create_session(request: Request, response: Response, db: Session = Depends(get_db)):
    session_id = request.cookies.get("cad_session")
    
    if not session_id:
        session_id = uuid.uuid4().hex
        response.set_cookie(
            key="cad_session",
            value=session_id,
            max_age=60 * 60 * 24 * 30,  # 30 jours
            httponly=True
        )
        db_session = SessionModel(session_id=session_id)
        db.add(db_session)
        db.commit()
    else:
        db_session = db.query(SessionModel).filter(
            SessionModel.session_id == session_id
        ).first()
        if db_session:
            db_session.last_seen = datetime.utcnow()
            db.commit()

    return session_id

@router.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    session_id = get_or_create_session(request, response, db)
    
    token = request.cookies.get("token")
    user = None
    if token:
        try:
            from auth import decode_token
            user = decode_token(token)
        except:
            pass

    files = db.query(FileModel).filter(
        FileModel.session_id == session_id,
        FileModel.is_quick_drop == True
    ).all()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "session_id": session_id,
        "user": user,
        "files": files
    })

@router.get("/session/{session_id}", response_class=HTMLResponse)
def session_page(
    request: Request,
    session_id: str,
    db: Session = Depends(get_db)
):
    files = db.query(FileModel).filter(
        FileModel.session_id == session_id,
        FileModel.is_quick_drop == True
    ).all()

    return templates.TemplateResponse("session.html", {
        "request": request,
        "session_id": session_id,
        "files": files
    })