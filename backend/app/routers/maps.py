import httpx
from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings

router = APIRouter(prefix="/maps", tags=["Google Maps"])
settings = get_settings()
GOOGLE_PLACES_URL = "https://places.googleapis.com/v1"


def _require_key() -> str:
    if not settings.google_maps_api_key:
        raise HTTPException(status_code=503, detail="Google Maps is not configured. Set GOOGLE_MAPS_API_KEY.")
    return settings.google_maps_api_key


@router.get("/places")
async def autocomplete_places(
    input: str = Query(min_length=2, max_length=200),
    city: str | None = Query(default=None, max_length=100),
):
    """Return venue/place autocomplete suggestions without exposing the server API key."""
    key = _require_key()
    body = {"input": input}
    if city:
        body["input"] = f"{input}, {city}"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": "suggestions.placePrediction.placeId,suggestions.placePrediction.text.text,suggestions.placePrediction.structuredFormat.mainText.text,suggestions.placePrediction.structuredFormat.secondaryText.text",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(f"{GOOGLE_PLACES_URL}/places:autocomplete", json=body, headers=headers)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Google Places returned HTTP {exc.response.status_code}")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Could not connect to Google Places")
    results = []
    for item in data.get("suggestions", []):
        prediction = item.get("placePrediction") or {}
        structured = prediction.get("structuredFormat") or {}
        results.append({
            "place_id": prediction.get("placeId"),
            "text": (prediction.get("text") or {}).get("text"),
            "main_text": (structured.get("mainText") or {}).get("text"),
            "secondary_text": (structured.get("secondaryText") or {}).get("text"),
        })
    return {"results": results}


@router.get("/places/{place_id}")
async def place_details(place_id: str):
    """Fetch a selected place's address and coordinates."""
    key = _require_key()
    headers = {
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": "id,displayName,formattedAddress,location,googleMapsUri",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{GOOGLE_PLACES_URL}/{place_id}", headers=headers)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Google Places returned HTTP {exc.response.status_code}")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Could not connect to Google Places")
    location = data.get("location") or {}
    return {
        "place_id": data.get("id"),
        "name": (data.get("displayName") or {}).get("text"),
        "address": data.get("formattedAddress"),
        "latitude": location.get("latitude"),
        "longitude": location.get("longitude"),
        "maps_url": data.get("googleMapsUri"),
    }


@router.get("/geocode")
async def geocode_address(address: str = Query(min_length=4, max_length=500)):
    """Convert an address into coordinates for venue records."""
    key = _require_key()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={"address": address, "key": key},
            )
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Google Geocoding returned HTTP {exc.response.status_code}")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Could not connect to Google Geocoding")
    if data.get("status") != "OK" or not data.get("results"):
        raise HTTPException(status_code=404, detail="No coordinates found for this address")
    result = data["results"][0]
    point = result.get("geometry", {}).get("location", {})
    return {"formatted_address": result.get("formatted_address"), "latitude": point.get("lat"), "longitude": point.get("lng")}
