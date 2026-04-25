from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import os
import asyncio
import json
import time
import base64

from src.services.tv_client import get_tv_client, TVClient
from src.services.tv_settings import load_settings, save_settings, TVSettings
from src.services.tv_discovery import discover_tvs
from src.services.image_processor import process_for_tv, generate_preview
from src.services.preview_cache import get_preview_cache

router = APIRouter()


def require_tv_client() -> TVClient:
    """Get TV client or raise 503 if not configured."""
    client = get_tv_client()
    if client is None:
        raise HTTPException(status_code=503, detail="No TV configured")
    return client

IMAGES_DIR = Path(os.environ.get("IMAGES_DIR", "/images"))
DEFAULT_CROP_PERCENT = int(os.environ.get("DEFAULT_CROP_PERCENT", "0"))


def get_safe_path(relative_path: str) -> Path:
    full_path = (IMAGES_DIR / relative_path).resolve()
    if not str(full_path).startswith(str(IMAGES_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")
    return full_path


class SetCurrentRequest(BaseModel):
    content_id: str


class PreviewRequest(BaseModel):
    paths: list[str]
    crop_percent: int = 0
    matte_percent: int = 10
    reframe_enabled: bool = False
    reframe_offsets: dict[str, dict] = {}  # path -> {"x": 0.5, "y": 0.5}


class UploadRequest(BaseModel):
    paths: list[str]
    crop_percent: int = 0
    matte_percent: int = 10
    display: bool = False
    reframe_enabled: bool = False
    reframe_offsets: dict[str, dict] = {}  # path -> {"x": 0.5, "y": 0.5}


class TVSettingsRequest(BaseModel):
    ip: str
    name: str = "Samsung TV"
    manual_entry: bool = False


class SlideshowRequest(BaseModel):
    enabled: bool
    duration: int = 15  # minutes
    shuffle: bool = True


DEFAULT_MATTE_PERCENT = int(os.environ.get("DEFAULT_MATTE_PERCENT", "10"))


@router.get("/config")
async def get_config():
    """Get app configuration including defaults."""
    return {
        "default_crop_percent": DEFAULT_CROP_PERCENT,
        "default_matte_percent": DEFAULT_MATTE_PERCENT
    }


@router.get("/settings")
async def get_tv_settings():
    """Get current TV settings."""
    settings = load_settings()
    env_ip = os.environ.get("TV_IP", "").strip() or None
    return {
        "selected_tv_ip": settings.selected_tv_ip,
        "selected_tv_name": settings.selected_tv_name,
        "manual_entry": settings.manual_entry,
        "configured": settings.configured,
        "env_ip": env_ip,
    }


@router.post("/settings")
async def set_tv_settings(request: TVSettingsRequest):
    """Save TV settings and reconfigure client."""
    # Try to connect to verify TV is reachable
    try:
        client = TVClient.configure(request.ip)
        status = await asyncio.to_thread(client.get_status)
        if not status.get("connected"):
            raise HTTPException(
                status_code=400,
                detail=f"Could not connect to TV at {request.ip}: {status.get('error', 'Unknown error')}"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not connect to TV: {e}")

    # Save settings
    settings = TVSettings(
        selected_tv_ip=request.ip,
        selected_tv_name=request.name,
        manual_entry=request.manual_entry
    )
    save_settings(settings)

    return {
        "success": True,
        "selected_tv_ip": settings.selected_tv_ip,
        "selected_tv_name": settings.selected_tv_name
    }


@router.get("/discover")
async def discover_samsung_tvs():
    """Discover Samsung TVs on the network."""
    start = time.time()

    tvs = await asyncio.to_thread(discover_tvs)

    return {
        "tvs": [{"ip": tv.ip, "name": tv.name, "model": tv.model} for tv in tvs],
        "scan_duration_ms": int((time.time() - start) * 1000)
    }


@router.get("/status")
async def get_status():
    client = get_tv_client()
    if client is None:
        return {"connected": False, "configured": False, "error": "No TV configured"}
    status = await asyncio.to_thread(client.get_status)
    status["configured"] = True
    return status


@router.get("/artwork")
async def list_artwork():
    client = require_tv_client()
    try:
        artwork = await asyncio.to_thread(client.get_artwork_list)
        # Add default dimensions (TV API doesn't provide them)
        # Using 16:9 as default since TV displays in that ratio
        for item in artwork:
            if "width" not in item:
                item["width"] = 1920
            if "height" not in item:
                item["height"] = 1080
        return {"artwork": artwork, "count": len(artwork)}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/artwork/current")
async def get_current_artwork():
    client = require_tv_client()
    try:
        return await asyncio.to_thread(client.get_current_artwork)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/artwork/current")
async def set_current_artwork(request: SetCurrentRequest):
    client = require_tv_client()
    try:
        await asyncio.to_thread(client.set_current_artwork, request.content_id)
        return {"success": True, "content_id": request.content_id}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.delete("/artwork/{content_id}")
async def delete_artwork(content_id: str):
    client = require_tv_client()
    try:
        await asyncio.to_thread(client.delete_artwork, content_id)
        return {"success": True, "deleted": content_id}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/artwork/{content_id}/thumbnail")
async def get_artwork_thumbnail(content_id: str):
    """Get thumbnail for TV artwork. May timeout for built-in Samsung content."""
    client = require_tv_client()
    try:
        # Run blocking TV call in thread pool to not block event loop
        thumbnail_data = await asyncio.to_thread(client.get_thumbnail, content_id)
        if not thumbnail_data:
            raise HTTPException(status_code=404, detail="Thumbnail not found")
        return Response(content=thumbnail_data, media_type="image/jpeg")
    except Exception as e:
        # Thumbnail retrieval often times out for built-in Samsung content
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/preview")
async def preview_processed(request: PreviewRequest):
    """Generate preview of processed images (cropped + matted)."""
    cache = get_preview_cache()

    async def process_single_preview(path: str):
        try:
            image_path = get_safe_path(path)
            if not image_path.exists():
                return None

            # Get reframe offset for this path (default center)
            offset = request.reframe_offsets.get(path, {"x": 0.5, "y": 0.5})
            offset_x = offset.get("x", 0.5)
            offset_y = offset.get("y", 0.5)
            offset_zoom = float(offset.get("zoom", 1.0))

            # Check cache first
            cached = cache.get(
                path, request.crop_percent, request.matte_percent,
                request.reframe_enabled, offset_x, offset_y, offset_zoom,
            )
            if cached:
                original, processed = cached
                return {
                    "id": path,
                    "name": image_path.name,
                    "original_url": f"data:image/jpeg;base64,{base64.b64encode(original).decode('utf-8')}",
                    "processed_url": f"data:image/jpeg;base64,{base64.b64encode(processed).decode('utf-8')}"
                }

            image_data = image_path.read_bytes()
            original, processed = await asyncio.to_thread(
                generate_preview,
                image_data,
                request.crop_percent,
                request.matte_percent,
                request.reframe_enabled,
                offset_x,
                offset_y,
                offset_zoom,
            )

            # Store in cache
            cache.set(
                path, request.crop_percent, request.matte_percent,
                original, processed,
                request.reframe_enabled, offset_x, offset_y, offset_zoom,
            )

            return {
                "id": path,
                "name": image_path.name,
                "original_url": f"data:image/jpeg;base64,{base64.b64encode(original).decode('utf-8')}",
                "processed_url": f"data:image/jpeg;base64,{base64.b64encode(processed).decode('utf-8')}"
            }
        except Exception:
            return None  # Skip failed previews silently

    # Process all previews in parallel
    results = await asyncio.gather(*[process_single_preview(p) for p in request.paths])
    previews = [p for p in results if p is not None]

    return {"previews": previews}


async def _process_image(path: str, request: UploadRequest) -> dict:
    """Read and process one image for TV upload."""
    try:
        image_path = get_safe_path(path)
        if not image_path.exists():
            return {"path": path, "success": False, "error": "File not found"}
        offset = request.reframe_offsets.get(path, {"x": 0.5, "y": 0.5})
        image_data = image_path.read_bytes()
        processed_data = await asyncio.to_thread(
            process_for_tv,
            image_data,
            request.crop_percent,
            request.matte_percent,
            request.reframe_enabled,
            float(offset.get("x", 0.5)),
            float(offset.get("y", 0.5)),
            float(offset.get("zoom", 1.0)),
        )
        return {"path": path, "processed_data": processed_data}
    except Exception as e:
        return {"path": path, "success": False, "error": str(e)}


@router.post("/upload")
async def upload_artwork(request: UploadRequest):
    client = require_tv_client()

    processed_items = await asyncio.gather(*[_process_image(p, request) for p in request.paths])

    failed = [item for item in processed_items if "success" in item and not item["success"]]
    to_upload = [item for item in processed_items if "processed_data" in item]

    upload_results = []
    if to_upload:
        last_idx = len(to_upload) - 1
        batch = [
            (item["processed_data"], request.display and i == last_idx)
            for i, item in enumerate(to_upload)
        ]
        batch_results = await asyncio.to_thread(client.upload_artwork_batch, batch)
        for item, result in zip(to_upload, batch_results):
            upload_results.append({"path": item["path"], **result})

    return {"results": failed + upload_results}


@router.post("/upload/stream")
async def upload_artwork_stream(request: UploadRequest):
    """Upload artwork with SSE progress events."""
    from fastapi.responses import StreamingResponse as SR
    client = require_tv_client()

    async def generate():
        def sse(data: dict) -> str:
            return f"data: {json.dumps(data)}\n\n"

        yield sse({"type": "processing", "total": len(request.paths)})

        processed_items = await asyncio.gather(*[_process_image(p, request) for p in request.paths])
        failed = [i for i in processed_items if "success" in i and not i["success"]]
        to_upload = [i for i in processed_items if "processed_data" in i]

        if not to_upload:
            yield sse({"type": "done", "results": failed})
            return

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def run_uploads():
            results = list(failed)
            last_idx = len(to_upload) - 1
            try:
                tv = client._get_tv()
                with tv.art() as art:
                    for idx, item in enumerate(to_upload):
                        loop.call_soon_threadsafe(queue.put_nowait, {
                            "type": "uploading",
                            "current": idx + 1,
                            "total": len(to_upload),
                            "name": Path(item["path"]).name,
                        })
                        try:
                            content_id = art.upload(
                                item["processed_data"],
                                file_type="jpg", matte="none", portrait_matte="none",
                            )
                            if request.display and idx == last_idx and content_id:
                                art.select_image(content_id)
                            results.append({"path": item["path"], "success": True, "content_id": content_id})
                        except Exception as e:
                            results.append({"path": item["path"], "success": False, "error": str(e)})
            except Exception as e:
                results.append({"path": "batch", "success": False, "error": str(e)})
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "done", "results": results})

        upload_future = loop.run_in_executor(None, run_uploads)

        while True:
            event = await queue.get()
            yield sse(event)
            if event["type"] == "done":
                break

        await upload_future

    return SR(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/slideshow")
async def get_slideshow_status():
    """Get current slideshow status."""
    client = require_tv_client()
    try:
        status = await asyncio.to_thread(client.get_slideshow_status)
        return status
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/slideshow")
async def set_slideshow_status(request: SlideshowRequest):
    """Set slideshow status."""
    client = require_tv_client()
    try:
        result = await asyncio.to_thread(
            client.set_slideshow_status,
            request.enabled,
            request.duration,
            request.shuffle
        )
        if "error" in result:
            raise HTTPException(status_code=503, detail=result["error"])
        return {"success": True, **result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
