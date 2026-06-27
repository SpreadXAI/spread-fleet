from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, engine, ensure_schema
from app.routers import admin as admin_router
from app.routers import app as app_router
from app.routers import auth as auth_router
from app.routers import workspaces as workspaces_router

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_schema()
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router, prefix=settings.api_prefix)
app.include_router(workspaces_router.router, prefix=settings.api_prefix)
app.include_router(app_router.router, prefix=settings.api_prefix)
app.include_router(admin_router.router, prefix=settings.api_prefix)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}
