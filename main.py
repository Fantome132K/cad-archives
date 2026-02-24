from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from database import Base, engine
from route import auth, upload, files
from apscheduler.schedulers.background import BackgroundScheduler
from cleanup import delete_expired_files

Base.metadata.create_all(bind=engine)

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


@app.get("/")
async def root():
    return {"message": "CAD Archives en ligne"}