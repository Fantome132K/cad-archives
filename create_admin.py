from database import SessionLocal, Base, engine, User
from auth import hash_password

Base.metadata.create_all(bind=engine)

db = SessionLocal()

admin = User(
    username="admin",
    password_hash=hash_password("angellust"),
    role="admin"
)

db.add(admin)
db.commit()
db.close()

print("Admin créé avec succès")