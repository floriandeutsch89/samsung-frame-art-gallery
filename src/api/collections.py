from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.services.collections import (
    load_collections,
    create_collection,
    delete_collection,
    rename_collection,
    get_collection_by_id,
)

router = APIRouter()


class CreateCollectionRequest(BaseModel):
    name: str


class RenameCollectionRequest(BaseModel):
    name: str


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
