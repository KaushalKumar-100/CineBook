from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
import threading
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect

from app import models  # noqa: F401
from app.config import get_settings
from app.database import Base, engine, test_connection
from app.routers import auth, bookings, catalog, integrations, manage, portal

settings = get_settings()
UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class ApiRateLimitMiddleware:
    """Small per-process guard for local/single-instance deployments.

    Use a shared Redis-backed limiter at the edge when running multiple workers
    or replicas; this in-memory bucket is intentionally not advertised as
    distributed protection.
    """
    def __init__(self, app, normal_limit: int = 120):
        self.app = app
        self.normal_limit = normal_limit
        self.window_seconds = 60
        self.requests = defaultdict(deque)
        self.lock = threading.Lock()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request = Request(scope, receive=receive)
        path = request.url.path
        if request.method == "OPTIONS":
            await self.app(scope, receive, send)
            return

        sensitive_groups = (
            ("/auth/login", 15),
            ("/auth/register", 10),
            ("/auth/password-reset", 5),
            ("/bookings", self.normal_limit),
            ("/tickets/check-in", self.normal_limit),
            ("/integrations/posters", 20),
            ("/integrations/ai", 20),
        )
        group = next(((prefix, limit) for prefix, limit in sensitive_groups if path.startswith(f"{settings.api_prefix}{prefix}")), None)
        if group:
            address = request.client.host if request.client else "unknown"
            key = f"{address}:{group[0]}"
            now = time.monotonic()
            with self.lock:
                bucket = self.requests[key]
                while bucket and now - bucket[0] >= self.window_seconds:
                    bucket.popleft()
                if len(bucket) >= group[1]:
                    response = JSONResponse(
                        {"detail": "Too many requests. Please wait and try again."},
                        status_code=429,
                        headers={"Retry-After": "60"},
                    )
                    await response(scope, receive, send)
                    return
                bucket.append(now)
        await self.app(scope, receive, send)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.app_env == "development" and settings.demo_mode:
        Base.metadata.create_all(bind=engine)
    yield


is_production = settings.app_env.lower() in {"production", "prod"}
configured_origins = [
    origin.strip()
    for origin in settings.cors_allowed_origins.split(",")
    if origin.strip()
]
app = FastAPI(
    title=settings.app_name,
    description="Movie, major-event and local-event discovery, organizer management and ticket booking API.",
    version="1.1.0",
    lifespan=lifespan,
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
    openapi_url=None if is_production else "/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
app.add_middleware(ApiRateLimitMiddleware, normal_limit=settings.rate_limit_per_minute)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR), check_dir=False), name="uploads")


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
app.include_router(portal.router, prefix=settings.api_prefix)
app.include_router(integrations.router, prefix=settings.api_prefix)
