from fastapi import FastAPI
from database import Base, engine
from route import auth, upload

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(auth.router, prefix="/auth")
app.include_router(upload.router, prefix="/files")


@app.get("/")
async def root():
    return {"message": "CAD Archives en ligne"}