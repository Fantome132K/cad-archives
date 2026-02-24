from fastapi import FastAPI
from database import Base, engine
from route import auth, upload, files
from apscheduler.schedulers.background import BackgroundScheduler
from cleanup import delete_expired_files

Base.metadata.create_all(bind=engine)

app = FastAPI()

scheduler = BackgroundScheduler()
scheduler.add_job(delete_expired_files, "interval", hours=1)
scheduler.start()

app.include_router(auth.router, prefix="/auth")
app.include_router(upload.router, prefix="/files")
app.include_router(files.router)



@app.get("/")
async def root():
    return {"message": "CAD Archives en ligne"}