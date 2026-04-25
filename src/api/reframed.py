import asyncio
import base64

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.services.reframed_client import get_reframed_client
from src.services.tv_client import get_tv_client, TVClient
from src.services.image_processor import generate_preview, process_for_tv
from src.services.preview_cache import get_preview_cache

router = APIRouter()


def require_tv_client() -> TVClient:
    client = get_tv_client()
    if client is None:
        raise HTTPException(status_code=503, detail="No TV configured")
    return client


@router.get("/collections")
async def get_collections():
    client = get_reframed_client()
    collections = await client.get_collections()
    return {"collections": collections}


@router.get("/collection/{slug}")
async def get_collection(slug: str, page: int = 1, page_size: int = 48):
    client = get_reframed_client()
    return await client.get_collection(slug, page, page_size)


@router.get("/recent")
async def get_recent(page: int = 1):
    client = get_reframed_client()
    return await client.get_recent(page)


@router.get("/colors")
async def get_colors():
    colors = [
        {"slug": "red", "name": "Red"},
        {"slug": "orange", "name": "Orange"},
        {"slug": "gold", "name": "Gold"},
        {"slug": "yellow", "name": "Yellow"},
        {"slug": "green", "name": "Green"},
        {"slug": "teal", "name": "Teal"},
        {"slug": "blue", "name": "Blue"},
        {"slug": "navy", "name": "Navy"},
        {"slug": "purple", "name": "Purple"},
        {"slug": "pink", "name": "Pink"},
        {"slug": "earth", "name": "Earth"},
        {"slug": "black", "name": "Black"},
        {"slug": "white", "name": "White"},
        {"slug": "neutral", "name": "Neutral"},
    ]
    return {"colors": colors}


@router.get("/color/{color}")
async def get_by_color(color: str, page: int = 1, page_size: int = 48):
    client = get_reframed_client()
    return await client.get_color(color, page, page_size)


@router.get("/artists")
async def get_artists():
    client = get_reframed_client()
    artists = await client.get_artists()
    return {"artists": artists}


@router.get("/artist/{slug}")
async def get_artist(slug: str, page: int = 1, page_size: int = 48):
    client = get_reframed_client()
    return await client.get_artist(slug, page, page_size)


class ReframedItem(BaseModel):
    image_id: str
    title: str = "Untitled"
    slug: str = ""


class ReframedPreviewRequest(BaseModel):
    items: list[ReframedItem]
    crop_percent: int = 0
    matte_percent: int = 0
    reframe_enabled: bool = True


class ReframedUploadRequest(BaseModel):
    items: list[ReframedItem]
    crop_percent: int = 0
    matte_percent: int = 0
    reframe_enabled: bool = True
    display: bool = False


@router.post("/preview")
async def preview_reframed_artwork(request: ReframedPreviewRequest):
    client = get_reframed_client()
    cache = get_preview_cache()

    async def process_single(item: ReframedItem):
        try:
            cache_key = f"reframed:{item.image_id}"
            cached = cache.get(cache_key, request.crop_percent, request.matte_percent)
            if cached:
                original, processed = cached
            else:
                image_data = await client.fetch_preview_image(item.image_id)
                original, processed = await asyncio.to_thread(
                    generate_preview, image_data, request.crop_percent, request.matte_percent,
                    request.reframe_enabled,
                )
                cache.set(cache_key, request.crop_percent, request.matte_percent, original, processed)

            return {
                "id": item.image_id,
                "name": item.title,
                "original_url": f"data:image/jpeg;base64,{base64.b64encode(original).decode()}",
                "processed_url": f"data:image/jpeg;base64,{base64.b64encode(processed).decode()}",
            }
        except Exception:
            return None

    results = await asyncio.gather(*[process_single(item) for item in request.items])
    previews = [p for p in results if p is not None]
    return {"previews": previews}


@router.post("/upload")
async def upload_reframed_artwork(request: ReframedUploadRequest):
    client = get_reframed_client()
    tv_client = require_tv_client()

    async def fetch_and_process(item: ReframedItem):
        try:
            image_data = await client.fetch_image(item.image_id, item.slug)
            processed_data = await asyncio.to_thread(
                process_for_tv, image_data, request.crop_percent, request.matte_percent,
                request.reframe_enabled,
            )
            return {"item": item, "processed_data": processed_data}
        except Exception as e:
            return {"item": item, "success": False, "error": str(e)}

    processed_items = await asyncio.gather(*[fetch_and_process(item) for item in request.items])

    results = []
    for i, result in enumerate(processed_items):
        if "success" in result and not result["success"]:
            results.append({"image_id": result["item"].image_id, "success": False, "error": result["error"]})
            continue

        item = result["item"]
        try:
            display_this = request.display and i == len(processed_items) - 1
            upload_result = await asyncio.to_thread(
                tv_client.upload_artwork,
                result["processed_data"],
                display_this,
            )
            results.append({
                "image_id": item.image_id,
                "success": True,
                "content_id": upload_result.get("content_id"),
                "title": item.title,
            })
        except Exception as e:
            results.append({"image_id": item.image_id, "success": False, "error": str(e)})

    return {"results": results}
