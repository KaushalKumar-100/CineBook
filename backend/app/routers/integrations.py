import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import select

from app.config import get_settings
from app.dependencies import DbSession, require_roles
from app.models import Movie, User
from app.schemas import DescriptionAssistInput, MovieImportOptions

router = APIRouter(prefix="/integrations", tags=["External Data and Media"])
settings = get_settings()
BACKEND_ROOT = Path(__file__).resolve().parents[2]
POSTER_DIR = BACKEND_ROOT / "uploads" / "posters"
MAX_POSTER_BYTES = 5 * 1024 * 1024


def _tmdb_headers() -> dict[str, str]:
    if settings.tmdb_read_access_token:
        return {"Authorization": f"Bearer {settings.tmdb_read_access_token}"}
    return {}


def _tmdb_params(extra: dict | None = None) -> dict:
    params = dict(extra or {})
    if not settings.tmdb_read_access_token and settings.tmdb_api_key:
        params["api_key"] = settings.tmdb_api_key
    return params


def _poster_url(path: str | None) -> str | None:
    return f"https://image.tmdb.org/t/p/w500{path}" if path else None


async def _tmdb_get(path: str, params: dict | None = None) -> dict:
    if not (settings.tmdb_read_access_token or settings.tmdb_api_key):
        raise HTTPException(status_code=503, detail="Configure TMDB_READ_ACCESS_TOKEN or TMDB_API_KEY in backend/.env")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"https://api.themoviedb.org/3/{path.lstrip('/')}",
                headers=_tmdb_headers(),
                params=_tmdb_params(params),
            )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"TMDB returned HTTP {exc.response.status_code}")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Could not connect to TMDB")


@router.get("/tmdb/upcoming")
async def tmdb_upcoming(
    region: str = Query(default="IN", min_length=2, max_length=2),
    page: int = Query(default=1, ge=1, le=500),
):
    data = await _tmdb_get("movie/upcoming", {"region": region.upper(), "page": page, "language": "en-US"})
    return {
        "page": data.get("page", page),
        "total_pages": data.get("total_pages", 0),
        "results": [{
            **item,
            "poster_url": _poster_url(item.get("poster_path")),
            "backdrop_url": _poster_url(item.get("backdrop_path")),
            "source": "tmdb",
        } for item in data.get("results", [])],
    }


@router.get("/tmdb/search")
async def tmdb_search(
    query: str = Query(min_length=2, max_length=120),
    page: int = Query(default=1, ge=1, le=500),
):
    data = await _tmdb_get("search/movie", {"query": query, "page": page, "include_adult": "false", "language": "en-US"})
    return {
        "page": data.get("page", page),
        "total_pages": data.get("total_pages", 0),
        "results": [{
            **item,
            "poster_url": _poster_url(item.get("poster_path")),
            "backdrop_url": _poster_url(item.get("backdrop_path")),
            "source": "tmdb",
        } for item in data.get("results", [])],
    }


@router.post("/tmdb/import", status_code=status.HTTP_201_CREATED)
async def import_tmdb_movie(
    payload: MovieImportOptions,
    db: DbSession,
    _: Annotated[User, Depends(require_roles("admin"))],
):
    data = await _tmdb_get(f"movie/{payload.tmdb_id}", {"language": "en-US"})
    movie = db.scalar(select(Movie).where(Movie.tmdb_id == payload.tmdb_id))
    if movie is None:
        movie = Movie(
            title=(data.get("title") or "Untitled")[:200],
            duration_minutes=max(1, int(data.get("runtime") or 120)),
            language=payload.language,
            release_date=datetime.fromisoformat(data["release_date"]) if data.get("release_date") else None,
            synopsis=data.get("overview") or None,
            certificate=None,
            poster_url=_poster_url(data.get("poster_path")) if payload.import_poster else None,
            tmdb_id=payload.tmdb_id,
            is_active=True,
        )
        db.add(movie)
    else:
        movie.title = (data.get("title") or movie.title)[:200]
        movie.duration_minutes = max(1, int(data.get("runtime") or movie.duration_minutes))
        movie.release_date = datetime.fromisoformat(data["release_date"]) if data.get("release_date") else movie.release_date
        movie.synopsis = data.get("overview") or movie.synopsis
        if payload.import_poster:
            movie.poster_url = _poster_url(data.get("poster_path"))
        movie.language = payload.language
        movie.is_active = True
    db.commit()
    db.refresh(movie)
    return {
        "id": movie.id, "tmdb_id": movie.tmdb_id, "title": movie.title,
        "duration_minutes": movie.duration_minutes, "language": movie.language,
        "release_date": movie.release_date, "synopsis": movie.synopsis,
        "poster_url": movie.poster_url, "source": "tmdb",
    }


@router.get("/ticketmaster/events")
async def ticketmaster_events(
    city: str = Query(min_length=2, max_length=100),
    page: int = Query(default=0, ge=0, le=100),
):
    if not settings.ticketmaster_api_key:
        raise HTTPException(status_code=503, detail="Configure TICKETMASTER_API_KEY in backend/.env")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                "https://app.ticketmaster.com/discovery/v2/events.json",
                params={"apikey": settings.ticketmaster_api_key, "city": city, "countryCode": "IN", "page": page, "size": 20},
            )
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Ticketmaster returned HTTP {exc.response.status_code}")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Could not connect to Ticketmaster")
    embedded = data.get("_embedded") or {}
    return {
        "page": data.get("page", {}),
        "events": [{
            "id": item.get("id"),
            "name": item.get("name"),
            "url": item.get("url"),
            "description": item.get("info") or item.get("pleaseNote"),
            "start": (item.get("dates") or {}).get("start", {}),
            "venue": ((item.get("_embedded") or {}).get("venues") or [{}])[0],
            "images": item.get("images") or [],
            "source": "ticketmaster",
            "import_requires_admin_review": True,
        } for item in embedded.get("events", [])],
    }


@router.post("/posters", status_code=status.HTTP_201_CREATED)
async def upload_poster(
    request: Request,
    file: UploadFile = File(...),
    _: User = Depends(require_roles("admin", "organizer")),
):
    content = await file.read(MAX_POSTER_BYTES + 1)
    if not content or len(content) > MAX_POSTER_BYTES:
        raise HTTPException(status_code=413, detail="Poster must be a non-empty image no larger than 5 MB")
    mime = file.content_type or ""
    signatures = {
        "image/png": (b"\x89PNG\r\n\x1a\n", ".png"),
        "image/jpeg": (b"\xff\xd8\xff", ".jpg"),
        "image/webp": (b"RIFF", ".webp"),
    }
    if mime not in signatures:
        raise HTTPException(status_code=415, detail="Only PNG, JPEG and WebP posters are supported")
    signature, extension = signatures[mime]
    if not content.startswith(signature) or (mime == "image/webp" and content[8:12] != b"WEBP"):
        raise HTTPException(status_code=415, detail="Image content does not match the declared file type")
    POSTER_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{extension}"
    (POSTER_DIR / filename).write_bytes(content)
    url = f"{settings.public_api_url.rstrip('/')}/uploads/posters/{filename}"
    return {"filename": filename, "poster_url": url, "size_bytes": len(content), "content_type": mime}


@router.post("/ai/event-description")
async def suggest_event_description(
    payload: DescriptionAssistInput,
    _: Annotated[User, Depends(require_roles("organizer", "admin"))],
):
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="Configure OPENAI_API_KEY in backend/.env to enable AI description suggestions")
    highlights = "\\n".join(f"- {item}" for item in payload.highlights)
    prompt = (
        f"Create a concise, accurate event listing for the event below. Do not invent dates, "
        f"performers, venue facts, awards, ticket availability or claims not supplied. "
        f"Use a {payload.tone.replace('_', ' ')} tone. Return one short paragraph and three bullet highlights.\\n\\n"
        f"Title: {payload.title}\\nCategory: {payload.category}\\nCity: {payload.city}\\n"
        f"Venue: {payload.venue or 'Not provided'}\\nSupplied highlights:\\n{highlights or '- Not provided'}"
    )
    try:
        async with httpx.AsyncClient(timeout=35) as client:
            response = await client.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"},
                json={"model": settings.openai_model, "input": prompt, "store": False},
            )
        response.raise_for_status()
        data = response.json()
        chunks = []
        for output in data.get("output", []):
            if output.get("type") == "message":
                for item in output.get("content", []):
                    if item.get("type") == "output_text" and item.get("text"):
                        chunks.append(item["text"])
        text = "\\n".join(chunks).strip()
        if not text:
            raise HTTPException(status_code=502, detail="AI provider returned no description text")
        return {"description": text, "provider": "openai", "model": settings.openai_model, "requires_organizer_review": True}
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"AI provider returned HTTP {exc.response.status_code}")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Could not connect to the AI description provider")
