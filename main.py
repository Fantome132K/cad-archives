from fastapi import FastAPI
from database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(auth.router, prefix="/auth")


@app.get("/")
async def root():
    return {"message": "CAD Archives en ligne"}