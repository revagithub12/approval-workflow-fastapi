import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import select

from .database import Base, SessionLocal, engine
from .models import Role, User
from .routers import auth, requests
from .security import hash_password


def seed_admin() -> None:
    """Create the first admin from environment variables if it does not exist."""
    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")
    if not email or not password:
        return
    with SessionLocal() as db:
        if not db.scalar(select(User).where(User.email == email)):
            db.add(User(email=email, hashed_password=hash_password(password), role=Role.ADMIN))
            db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_admin()
    yield


app = FastAPI(
    title="Approval Workflow API",
    description="Multi-stage approval workflow with JWT auth and role-based access control.",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(auth.router)
app.include_router(requests.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
