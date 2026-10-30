from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect

from app import models  # noqa: F401
from app.config import get_settings
from app.database import Base, engine, test_connection
from app.routers import auth, bookings, catalog, manage

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Convenience table creation is restricted to explicit local demo mode.
    if settings.app_env.lower() == "development" and settings.demo_mode:
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    description="Movie, major-event and local-event discovery and ticket-booking API.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["System"])
def home():
    return {"message": "Welcome to CineBook API", "status": "running", "docs": "/docs"}


@app.get("/health/db", tags=["System"])
def database_health():
    return {"status": "connected", "database": test_connection()}


@app.get("/health/schema", tags=["System"])
def schema_health():
    return {"tables": sorted(inspect(engine).get_table_names())}


app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(catalog.router, prefix=settings.api_prefix)
app.include_router(manage.router, prefix=settings.api_prefix)
app.include_router(bookings.router, prefix=settings.api_prefix)
