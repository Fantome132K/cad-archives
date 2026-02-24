from fastapi import FastAPI, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from database import Base, engine, SessionLocal
from route import auth, upload, files
from apscheduler.schedulers.background import BackgroundScheduler
from cleanup import delete_expired_files

Base.metadata.create_all(bind=engine)

def get_db_main():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

scheduler = BackgroundScheduler()
scheduler.add_job(delete_expired_files, "interval", hours=1)
scheduler.start()

app.mount("/static", StaticFiles(directory="static"), name="static")


app.include_router(auth.router, prefix="/auth")
app.include_router(upload.router, prefix="/files")
app.include_router(files.router)

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db=Depends(get_db_main)):
    token = request.cookies.get("token")
    if not token:
        return RedirectResponse(url="/login")
    try:
        from auth import decode_token
        user_data = decode_token(token)
    except:
        return RedirectResponse(url="/login")
    
    from database import File as FileModel
    from datetime import datetime
    files = db.query(FileModel).filter(
        FileModel.uploaded_by == user_data["sub"]
    ).all()
    
    now = datetime.utcnow()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "username": user_data["sub"],
        "role": user_data["role"],
        "files": files,
        "now": now
    })


@app.get("/")
async def root():
    return {"message": "CAD Archives en ligne"}