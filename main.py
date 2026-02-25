from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from database import Base, engine, SessionLocal
from routes import auth, upload, files, public
from apscheduler.schedulers.background import BackgroundScheduler
from cleanup import delete_expired_files
from auth import decode_token

Base.metadata.create_all(bind=engine)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

scheduler = BackgroundScheduler()
scheduler.add_job(delete_expired_files, "interval", hours=1)
scheduler.start()

app.include_router(auth.router, prefix="/auth")
app.include_router(upload.router, prefix="/files")
app.include_router(files.router)
app.include_router(public.router)

def get_db_main():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db=Depends(get_db_main)):
    token = request.cookies.get("token")
    if not token:
        return RedirectResponse(url="/login")
    try:
        user_data = decode_token(token)
    except:
        return RedirectResponse(url="/login")

    from database import File as FileModel
    from datetime import datetime
    files_list = db.query(FileModel).filter(
        FileModel.uploaded_by == user_data["sub"],
        FileModel.is_quick_drop == False
    ).all()

    now = datetime.utcnow()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "username": user_data["sub"],
        "role": user_data["role"],
        "files": files_list,
        "now": now
    })
