import os
import asyncio
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.services.collections import (
    load_collections,
    create_collection,
    delete_collection,
    rename_collection,
    get_collection_by_id,
    add_items_to_collection,
    remove_items_from_collection,
    reorder_collection_items,
    CollectionItem,
)
from src.services.met_client import get_met_client
from src.services.thumbnails import get_image_dimensions

IMAGES_DIR = Path(os.environ.get("IMAGES_DIR", "/images"))

router = APIRouter()


class CreateCollectionRequest(BaseModel):
    name: str


class RenameCollectionRequest(BaseModel):
    name: str


class AddItemsRequest(BaseModel):
    items: list[dict]  # [{"type": "local", "path": "..."} or {"type": "met", "object_id": 123}]


class RemoveItemsRequest(BaseModel):
    items: list[dict]  # Same format as AddItemsRequest


class ReorderItemsRequest(BaseModel):
    order: list[dict]  # Items in desired order


@router.get("")
async def list_collections():
    """List all collections with item counts."""
    data = load_collections()
    return {
        "collections": [
            {
                "id": c.id,
                "name": c.name,
                "item_count": len(c.items),
                "created_at": c.created_at
            }
            for c in data.collections
        ]
    }


@router.post("")
async def create_new_collection(request: CreateCollectionRequest):
    """Create a new collection."""
    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Collection name cannot be empty")

    collection = create_collection(name)
    return {
        "id": collection.id,
        "name": collection.name,
        "item_count": 0,
        "created_at": collection.created_at
    }


@router.get("/{collection_id}")
async def get_collection(collection_id: str):
    """Get collection details (without resolved items - see /items endpoint)."""
    data = load_collections()
    collection = get_collection_by_id(data, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    return {
        "id": collection.id,
        "name": collection.name,
        "item_count": len(collection.items),
        "created_at": collection.created_at
    }


@router.patch("/{collection_id}")
async def update_collection(collection_id: str, request: RenameCollectionRequest):
    """Rename a collection."""
    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Collection name cannot be empty")

    collection = rename_collection(collection_id, name)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    return {
        "id": collection.id,
        "name": collection.name,
        "item_count": len(collection.items),
        "created_at": collection.created_at
    }


@router.delete("/{collection_id}")
async def delete_existing_collection(collection_id: str):
    """Delete a collection."""
    if delete_collection(collection_id):
        return {"success": True, "deleted": collection_id}
    raise HTTPException(status_code=404, detail="Collection not found")


@router.get("/{collection_id}/items")
async def get_collection_items(collection_id: str):
    """Get collection with resolved item details."""
    data = load_collections()
    collection = get_collection_by_id(data, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    resolved_items = []
    unavailable_count = 0
    met_client = get_met_client()

    for item in collection.items:
        if item.type == "local" and item.path:
            # Resolve local image
            full_path = IMAGES_DIR / item.path
            if full_path.exists() and full_path.is_file():
                width, height = get_image_dimensions(full_path)
                resolved_items.append({
                    "type": "local",
                    "path": item.path,
                    "name": full_path.name,
                    "width": width,
                    "height": height,
                    "added_at": item.added_at
                })
            else:
                unavailable_count += 1

        elif item.type == "met" and item.object_id:
            # Resolve Met object
            obj = await asyncio.to_thread(met_client.get_object, item.object_id)
            if obj and (obj.get("primaryImage") or obj.get("primaryImageSmall")):
                primary = obj.get("primaryImage") or obj.get("primaryImageSmall")
                resolved_items.append({
                    "type": "met",
                    "object_id": item.object_id,
                    "title": obj.get("title", "Untitled"),
                    "artist": obj.get("artistDisplayName", "Unknown"),
                    "date": obj.get("objectDate", ""),
                    "image_url": primary,
                    "image_url_small": obj.get("primaryImageSmall", primary),
                    "width": obj.get("primaryImageWidth") or 0,
                    "height": obj.get("primaryImageHeight") or 0,
                    "added_at": item.added_at
                })
            else:
                unavailable_count += 1

    return {
        "id": collection.id,
        "name": collection.name,
        "items": resolved_items,
        "item_count": len(resolved_items),
        "unavailable_count": unavailable_count
    }


@router.post("/{collection_id}/items")
async def add_items(collection_id: str, request: AddItemsRequest):
    """Add items to a collection."""
    items = []
    for item_data in request.items:
        item_type = item_data.get("type")
        if item_type == "local" and item_data.get("path"):
            items.append(CollectionItem(type="local", path=item_data["path"]))
        elif item_type == "met" and item_data.get("object_id"):
            items.append(CollectionItem(type="met", object_id=item_data["object_id"]))

    if not items:
        raise HTTPException(status_code=400, detail="No valid items provided")

    collection = add_items_to_collection(collection_id, items)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    return {
        "id": collection.id,
        "name": collection.name,
        "item_count": len(collection.items)
    }


@router.delete("/{collection_id}/items")
async def remove_items(collection_id: str, request: RemoveItemsRequest):
    """Remove items from a collection."""
    collection = remove_items_from_collection(collection_id, request.items)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    return {
        "id": collection.id,
        "name": collection.name,
        "item_count": len(collection.items)
    }


@router.put("/{collection_id}/items/order")
async def reorder_items(collection_id: str, request: ReorderItemsRequest):
    """Reorder items in a collection."""
    collection = reorder_collection_items(collection_id, request.order)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    return {
        "id": collection.id,
        "name": collection.name,
        "item_count": len(collection.items)
    }
