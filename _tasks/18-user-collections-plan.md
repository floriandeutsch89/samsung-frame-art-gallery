# User Collections Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add user-defined collections for organizing artwork from Local and Met sources, with batch upload to TV and slideshow controls.

**Architecture:** JSON file persistence for collections (`/app/data/collections.json`), new FastAPI router for CRUD operations, Vue 3 panel as third source tab. Collections resolve items from existing Local/Met sources at read time.

**Tech Stack:** FastAPI, Python dataclasses, Vue 3 Composition API, existing ImageGrid/ActionBar components

---

## Task 1: Collections Service - Data Model

**Files:**
- Create: `src/services/collections.py`

**Step 1: Create the collections service with data model**

```python
import json
import logging
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional
from dataclasses import dataclass, asdict, field

_LOGGER = logging.getLogger(__name__)

COLLECTIONS_FILE = Path("/app/data/collections.json")


@dataclass
class CollectionItem:
    type: Literal["local", "met"]
    path: Optional[str] = None  # for local
    object_id: Optional[int] = None  # for met
    added_at: str = ""

    def __post_init__(self):
        if not self.added_at:
            self.added_at = datetime.now(timezone.utc).isoformat()


@dataclass
class Collection:
    id: str
    name: str
    created_at: str = ""
    items: list[CollectionItem] = field(default_factory=list)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


@dataclass
class CollectionsData:
    version: int = 1
    collections: list[Collection] = field(default_factory=list)


def _generate_id() -> str:
    """Generate a short random ID."""
    return secrets.token_hex(3)


def load_collections() -> CollectionsData:
    """Load collections from disk."""
    if not COLLECTIONS_FILE.exists():
        _LOGGER.info("No collections file found, using empty list")
        return CollectionsData()

    try:
        data = json.loads(COLLECTIONS_FILE.read_text())
        collections = []
        for c in data.get("collections", []):
            items = [
                CollectionItem(
                    type=item["type"],
                    path=item.get("path"),
                    object_id=item.get("object_id"),
                    added_at=item.get("added_at", "")
                )
                for item in c.get("items", [])
            ]
            collections.append(Collection(
                id=c["id"],
                name=c["name"],
                created_at=c.get("created_at", ""),
                items=items
            ))
        return CollectionsData(
            version=data.get("version", 1),
            collections=collections
        )
    except Exception as e:
        _LOGGER.error(f"Failed to load collections: {e}")
        return CollectionsData()


def save_collections(data: CollectionsData) -> None:
    """Save collections to disk atomically."""
    COLLECTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Convert to JSON-serializable dict
    output = {
        "version": data.version,
        "collections": []
    }
    for c in data.collections:
        output["collections"].append({
            "id": c.id,
            "name": c.name,
            "created_at": c.created_at,
            "items": [
                {k: v for k, v in asdict(item).items() if v is not None and v != ""}
                for item in c.items
            ]
        })

    # Atomic write: write to temp file, then rename
    temp_file = COLLECTIONS_FILE.with_suffix(".tmp")
    temp_file.write_text(json.dumps(output, indent=2))
    temp_file.replace(COLLECTIONS_FILE)
    _LOGGER.info(f"Saved {len(data.collections)} collections")


def get_collection_by_id(data: CollectionsData, collection_id: str) -> Optional[Collection]:
    """Find collection by ID."""
    for c in data.collections:
        if c.id == collection_id:
            return c
    return None


def create_collection(name: str) -> Collection:
    """Create a new collection and save."""
    data = load_collections()
    collection = Collection(id=_generate_id(), name=name.strip()[:100])
    data.collections.append(collection)
    save_collections(data)
    return collection


def delete_collection(collection_id: str) -> bool:
    """Delete a collection by ID."""
    data = load_collections()
    original_len = len(data.collections)
    data.collections = [c for c in data.collections if c.id != collection_id]
    if len(data.collections) < original_len:
        save_collections(data)
        return True
    return False


def rename_collection(collection_id: str, new_name: str) -> Optional[Collection]:
    """Rename a collection."""
    data = load_collections()
    collection = get_collection_by_id(data, collection_id)
    if collection:
        collection.name = new_name.strip()[:100]
        save_collections(data)
        return collection
    return None


def add_items_to_collection(collection_id: str, items: list[CollectionItem]) -> Optional[Collection]:
    """Add items to a collection, skipping duplicates."""
    data = load_collections()
    collection = get_collection_by_id(data, collection_id)
    if not collection:
        return None

    # Build set of existing items for dedup
    existing = set()
    for item in collection.items:
        if item.type == "local" and item.path:
            existing.add(("local", item.path))
        elif item.type == "met" and item.object_id:
            existing.add(("met", item.object_id))

    # Add new items, skipping duplicates
    added = 0
    for item in items:
        key = None
        if item.type == "local" and item.path:
            key = ("local", item.path)
        elif item.type == "met" and item.object_id:
            key = ("met", item.object_id)

        if key and key not in existing:
            existing.add(key)
            collection.items.append(item)
            added += 1

    if added > 0:
        save_collections(data)
        _LOGGER.info(f"Added {added} items to collection {collection_id}")

    return collection


def remove_items_from_collection(collection_id: str, item_keys: list[dict]) -> Optional[Collection]:
    """Remove items from collection by their identifiers."""
    data = load_collections()
    collection = get_collection_by_id(data, collection_id)
    if not collection:
        return None

    # Build removal set
    to_remove = set()
    for key in item_keys:
        if key.get("type") == "local" and key.get("path"):
            to_remove.add(("local", key["path"]))
        elif key.get("type") == "met" and key.get("object_id"):
            to_remove.add(("met", key["object_id"]))

    original_len = len(collection.items)
    collection.items = [
        item for item in collection.items
        if (item.type == "local" and ("local", item.path) not in to_remove) or
           (item.type == "met" and ("met", item.object_id) not in to_remove)
    ]

    if len(collection.items) < original_len:
        save_collections(data)

    return collection


def reorder_collection_items(collection_id: str, ordered_keys: list[dict]) -> Optional[Collection]:
    """Reorder items in collection to match the given order."""
    data = load_collections()
    collection = get_collection_by_id(data, collection_id)
    if not collection:
        return None

    # Build lookup by key
    item_lookup = {}
    for item in collection.items:
        if item.type == "local" and item.path:
            item_lookup[("local", item.path)] = item
        elif item.type == "met" and item.object_id:
            item_lookup[("met", item.object_id)] = item

    # Reorder based on provided keys
    new_items = []
    for key in ordered_keys:
        lookup_key = None
        if key.get("type") == "local" and key.get("path"):
            lookup_key = ("local", key["path"])
        elif key.get("type") == "met" and key.get("object_id"):
            lookup_key = ("met", key["object_id"])

        if lookup_key and lookup_key in item_lookup:
            new_items.append(item_lookup.pop(lookup_key))

    # Append any remaining items not in the order list
    new_items.extend(item_lookup.values())

    collection.items = new_items
    save_collections(data)
    return collection
```

**Step 2: Verify file was created**

Run: `python -c "from src.services.collections import load_collections; print(load_collections())"`
Expected: `CollectionsData(version=1, collections=[])`

**Step 3: Commit**

```bash
git add src/services/collections.py
git commit -m "feat: add collections service with data model and persistence"
```

---

## Task 2: Collections API - Basic CRUD

**Files:**
- Create: `src/api/collections.py`
- Modify: `src/main.py:10-11,43-45`

**Step 1: Create the collections API router**

```python
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
```

**Step 2: Mount the router in main.py**

Edit `src/main.py` - add import and mount:

After line 10 (`from src.api import images, tv, met`), change to:
```python
from src.api import images, tv, met, collections
```

After line 45 (`app.include_router(met.router, prefix="/api/met", tags=["met"])`), add:
```python
app.include_router(collections.router, prefix="/api/collections", tags=["collections"])
```

**Step 3: Test the API**

Run: `curl -X POST http://localhost:8080/api/collections -H "Content-Type: application/json" -d '{"name": "Test"}'`
Expected: `{"id":"...","name":"Test","item_count":0,"created_at":"..."}`

Run: `curl http://localhost:8080/api/collections`
Expected: `{"collections":[{"id":"...","name":"Test",...}]}`

**Step 4: Commit**

```bash
git add src/api/collections.py src/main.py
git commit -m "feat: add collections API with basic CRUD endpoints"
```

---

## Task 3: Collections API - Item Management

**Files:**
- Modify: `src/api/collections.py`

**Step 1: Add item management endpoints**

Add these imports at the top of `src/api/collections.py`:

```python
import os
import asyncio
from pathlib import Path

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
```

Add these request models after the existing ones:

```python
class AddItemsRequest(BaseModel):
    items: list[dict]  # [{"type": "local", "path": "..."} or {"type": "met", "object_id": 123}]


class RemoveItemsRequest(BaseModel):
    items: list[dict]  # Same format as AddItemsRequest


class ReorderItemsRequest(BaseModel):
    order: list[dict]  # Items in desired order
```

Add these endpoints at the end of the file:

```python
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
```

**Step 2: Test item management**

Run: `curl -X POST http://localhost:8080/api/collections/{id}/items -H "Content-Type: application/json" -d '{"items": [{"type": "local", "path": "test.jpg"}]}'`
Expected: `{"id":"...","name":"...","item_count":1}`

**Step 3: Commit**

```bash
git add src/api/collections.py
git commit -m "feat: add collection item management endpoints"
```

---

## Task 4: TV Slideshow API

**Files:**
- Modify: `src/api/tv.py`
- Modify: `src/services/tv_client.py`

**Step 1: Add slideshow methods to tv_client.py**

Add these methods to the `TVClient` class in `src/services/tv_client.py` (before the final `get_tv_client` function):

```python
    def get_slideshow_status(self) -> dict:
        """Get current slideshow status."""
        try:
            tv = self._get_tv()
            return tv.art().get_slideshow_status()
        except Exception as e:
            _LOGGER.warning(f"Failed to get slideshow status: {e}")
            return {"error": str(e)}

    def set_slideshow_status(self, enabled: bool, duration: int = 15, shuffle: bool = True) -> dict:
        """Set slideshow status.

        Args:
            enabled: Whether slideshow is enabled
            duration: Minutes between image changes (0 to disable)
            shuffle: Random order (True) or sequential (False)
        """
        try:
            tv = self._get_tv()
            if not enabled:
                return tv.art().set_slideshow_status(duration=0)
            else:
                # type=True means shuffle/random, type=False means sequential
                return tv.art().set_slideshow_status(
                    duration=duration,
                    type=shuffle,
                    category=2  # MY-C0002 = My Collection
                )
        except Exception as e:
            _LOGGER.error(f"Failed to set slideshow status: {e}")
            return {"error": str(e)}
```

**Step 2: Add slideshow endpoints to tv.py**

Add this request model after the existing ones in `src/api/tv.py`:

```python
class SlideshowRequest(BaseModel):
    enabled: bool
    duration: int = 15  # minutes
    shuffle: bool = True
```

Add these endpoints at the end of `src/api/tv.py`:

```python
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
```

**Step 3: Test slideshow endpoints**

Run: `curl http://localhost:8080/api/tv/slideshow`
Expected: `{"value": "off", ...}` or similar status

**Step 4: Commit**

```bash
git add src/api/tv.py src/services/tv_client.py
git commit -m "feat: add TV slideshow control endpoints"
```

---

## Task 5: Frontend - CollectionPicker Component

**Files:**
- Create: `src/frontend/src/components/CollectionPicker.vue`

**Step 1: Create the CollectionPicker component**

```vue
<template>
  <div class="collection-picker-overlay" @click.self="$emit('close')">
    <div class="collection-picker">
      <div class="picker-header">
        <h3>Add to Collection</h3>
        <button class="close-btn" @click="$emit('close')">&times;</button>
      </div>

      <div class="picker-content">
        <div class="new-collection">
          <input
            v-model="newName"
            type="text"
            placeholder="Create new collection..."
            @keyup.enter="createAndAdd"
          />
          <button
            :disabled="!newName.trim() || creating"
            @click="createAndAdd"
          >
            Create
          </button>
        </div>

        <div v-if="loading" class="loading">Loading collections...</div>

        <div v-else-if="collections.length === 0" class="empty">
          No collections yet. Create one above.
        </div>

        <div v-else class="collections-list">
          <button
            v-for="collection in collections"
            :key="collection.id"
            class="collection-item"
            :disabled="adding"
            @click="addToCollection(collection.id)"
          >
            <span class="collection-name">{{ collection.name }}</span>
            <span class="collection-count">{{ collection.item_count }} items</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps({
  items: {
    type: Array,
    required: true
    // Array of {type: 'local', path: '...'} or {type: 'met', object_id: 123}
  }
})

const emit = defineEmits(['close', 'added'])

const collections = ref([])
const loading = ref(true)
const newName = ref('')
const creating = ref(false)
const adding = ref(false)

const loadCollections = async () => {
  loading.value = true
  try {
    const res = await fetch('/api/collections')
    const data = await res.json()
    collections.value = data.collections || []
  } catch (e) {
    console.error('Failed to load collections:', e)
  } finally {
    loading.value = false
  }
}

const createAndAdd = async () => {
  const name = newName.value.trim()
  if (!name) return

  creating.value = true
  try {
    // Create collection
    const createRes = await fetch('/api/collections', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    })
    const collection = await createRes.json()

    // Add items to it
    await fetch(`/api/collections/${collection.id}/items`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: props.items })
    })

    emit('added', collection)
    emit('close')
  } catch (e) {
    console.error('Failed to create collection:', e)
  } finally {
    creating.value = false
  }
}

const addToCollection = async (collectionId) => {
  adding.value = true
  try {
    await fetch(`/api/collections/${collectionId}/items`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: props.items })
    })

    const collection = collections.value.find(c => c.id === collectionId)
    emit('added', collection)
    emit('close')
  } catch (e) {
    console.error('Failed to add to collection:', e)
  } finally {
    adding.value = false
  }
}

onMounted(loadCollections)
</script>

<style scoped>
.collection-picker-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.collection-picker {
  background: #1a1a2e;
  border-radius: 8px;
  width: 90%;
  max-width: 400px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.picker-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #2a2a4e;
}

.picker-header h3 {
  margin: 0;
  font-size: 1.1rem;
}

.close-btn {
  background: transparent;
  border: none;
  color: #888;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.close-btn:hover {
  color: white;
}

.picker-content {
  padding: 1rem;
  overflow-y: auto;
}

.new-collection {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.new-collection input {
  flex: 1;
  padding: 0.5rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: #2a2a4e;
  color: white;
}

.new-collection input:focus {
  outline: none;
  border-color: #4a90d9;
}

.new-collection button {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  border: none;
  background: #4a90d9;
  color: white;
  cursor: pointer;
}

.new-collection button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading, .empty {
  text-align: center;
  color: #888;
  padding: 2rem;
}

.collections-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.collection-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: #2a2a4e;
  border: 1px solid #3a3a5e;
  border-radius: 4px;
  cursor: pointer;
  color: white;
  text-align: left;
}

.collection-item:hover:not(:disabled) {
  background: #3a3a5e;
  border-color: #4a90d9;
}

.collection-item:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.collection-name {
  font-weight: 500;
}

.collection-count {
  color: #888;
  font-size: 0.85rem;
}
</style>
```

**Step 2: Verify component syntax**

Run: `cd src/frontend && npm run build`
Expected: Build succeeds without errors

**Step 3: Commit**

```bash
git add src/frontend/src/components/CollectionPicker.vue
git commit -m "feat: add CollectionPicker component for adding images to collections"
```

---

## Task 6: Frontend - Add to Collection in LocalPanel

**Files:**
- Modify: `src/frontend/src/views/LocalPanel.vue`

**Step 1: Import CollectionPicker and add state**

Add import after line 70 (`import PreviewModal from '../components/PreviewModal.vue'`):

```javascript
import CollectionPicker from '../components/CollectionPicker.vue'
```

Add state after line 86 (`const reframeOffsets = ref({})`):

```javascript
const showCollectionPicker = ref(false)
```

**Step 2: Add computed property for collection items**

Add after the state declarations (around line 88):

```javascript
import { ref, watch, onMounted, computed } from 'vue'
```

(Update the existing import on line 66)

Add computed property:

```javascript
const selectedItemsForCollection = computed(() => {
  return Array.from(selectedIds.value).map(path => ({
    type: 'local',
    path
  }))
})
```

**Step 3: Add handler function**

Add after the `upload` function (around line 238):

```javascript
const onAddedToCollection = (collection) => {
  console.log(`Added ${selectedIds.value.size} items to collection: ${collection.name}`)
  // Optionally clear selection after adding
  // selectedIds.value = new Set()
}
```

**Step 4: Add "Add to Collection" button in template**

In the template, find the ActionBar section (around line 26-48). Add a new button after CropSettings and before the Upload buttons:

```vue
    <ActionBar>
      <template #left>
        <CropSettings
          :has-selection="selectedIds.size > 0"
          @change="setSettings"
          @preview="loadPreviews"
        />
      </template>
      <button
        class="secondary"
        :disabled="selectedIds.size === 0"
        @click="showCollectionPicker = true"
      >
        + Collection
      </button>
      <button
        class="secondary"
        :disabled="selectedIds.size === 0 || uploading"
        @click="upload(false)"
      >
        Upload ({{ selectedIds.size }})
      </button>
      <button
        class="primary"
        :disabled="selectedIds.size === 0 || uploading"
        @click="upload(true)"
      >
        Upload & Display
      </button>
    </ActionBar>
```

**Step 5: Add CollectionPicker to template**

Add after PreviewModal (around line 62):

```vue
    <CollectionPicker
      v-if="showCollectionPicker"
      :items="selectedItemsForCollection"
      @close="showCollectionPicker = false"
      @added="onAddedToCollection"
    />
```

**Step 6: Verify build**

Run: `cd src/frontend && npm run build`
Expected: Build succeeds

**Step 7: Commit**

```bash
git add src/frontend/src/views/LocalPanel.vue
git commit -m "feat: add 'Add to Collection' button to LocalPanel"
```

---

## Task 7: Frontend - Add to Collection in MetPanel

**Files:**
- Modify: `src/frontend/src/views/MetPanel.vue`

**Step 1: Import CollectionPicker and add state**

Add import after line 116 (`import ResolutionWarning from '../components/ResolutionWarning.vue'`):

```javascript
import CollectionPicker from '../components/CollectionPicker.vue'
```

Update the import on line 111 to include `computed`:

```javascript
import { ref, onMounted, computed } from 'vue'
```

Add state after line 153 (`const activeSearch = ref(initialParams.q)`):

```javascript
const showCollectionPicker = ref(false)
```

**Step 2: Add computed property for collection items**

Add after the state declarations:

```javascript
const selectedItemsForCollection = computed(() => {
  return Array.from(selectedIds.value).map(object_id => ({
    type: 'met',
    object_id
  }))
})
```

**Step 3: Add handler function**

Add after the `doUpload` function (around line 467):

```javascript
const onAddedToCollection = (collection) => {
  console.log(`Added ${selectedIds.value.size} items to collection: ${collection.name}`)
}
```

**Step 4: Add "Add to Collection" button in template**

Find the ActionBar section (around line 66-89). Add a new button:

```vue
    <ActionBar>
      <template #left>
        <CropSettings
          :has-selection="selectedIds.size > 0"
          :allow-reframe="false"
          @change="setSettings"
          @preview="loadPreviews"
        />
      </template>
      <button
        class="secondary"
        :disabled="selectedIds.size === 0"
        @click="showCollectionPicker = true"
      >
        + Collection
      </button>
      <button
        class="secondary"
        :disabled="selectedIds.size === 0 || uploading"
        @click="upload(false)"
      >
        Upload ({{ selectedIds.size }})
      </button>
      <button
        class="primary"
        :disabled="selectedIds.size === 0 || uploading"
        @click="upload(true)"
      >
        Upload & Display
      </button>
    </ActionBar>
```

**Step 5: Add CollectionPicker to template**

Add after ResolutionWarning (around line 107):

```vue
    <CollectionPicker
      v-if="showCollectionPicker"
      :items="selectedItemsForCollection"
      @close="showCollectionPicker = false"
      @added="onAddedToCollection"
    />
```

**Step 6: Verify build**

Run: `cd src/frontend && npm run build`
Expected: Build succeeds

**Step 7: Commit**

```bash
git add src/frontend/src/views/MetPanel.vue
git commit -m "feat: add 'Add to Collection' button to MetPanel"
```

---

## Task 8: Frontend - CollectionsPanel View

**Files:**
- Create: `src/frontend/src/views/CollectionsPanel.vue`

**Step 1: Create the CollectionsPanel component**

```vue
<template>
  <div class="collections-panel">
    <div class="panel-header">
      <div class="collection-select">
        <select v-model="selectedCollectionId" @change="loadCollectionItems">
          <option :value="null" disabled>Select a collection...</option>
          <option
            v-for="c in collections"
            :key="c.id"
            :value="c.id"
          >
            {{ c.name }} ({{ c.item_count }})
          </option>
        </select>
        <button class="new-btn" @click="showNewModal = true" title="New collection">+</button>
      </div>

      <div v-if="selectedCollection" class="collection-actions">
        <button class="icon-btn" @click="showRenameModal = true" title="Rename">
          <span>Rename</span>
        </button>
        <button class="icon-btn danger" @click="confirmDelete" title="Delete">
          <span>Delete</span>
        </button>
      </div>
    </div>

    <div v-if="!selectedCollectionId" class="empty-state">
      <p>Select a collection to view its contents</p>
      <button @click="showNewModal = true">Create New Collection</button>
    </div>

    <template v-else>
      <div v-if="unavailableCount > 0" class="unavailable-notice">
        {{ unavailableCount }} image(s) unavailable
      </div>

      <ImageGrid
        :images="items"
        :selected-ids="selectedIds"
        :loading="loading"
        :is-local="false"
        @toggle="toggleSelection"
        @select-all="selectAll"
        @preview="(img) => $emit('preview', img, img.type === 'local')"
      />

      <ActionBar>
        <template #left>
          <CropSettings
            :has-selection="selectedIds.size > 0"
            :allow-reframe="false"
            @change="setSettings"
          />
        </template>
        <button
          class="secondary danger"
          :disabled="selectedIds.size === 0"
          @click="removeSelected"
        >
          Remove ({{ selectedIds.size }})
        </button>
        <button
          class="secondary"
          :disabled="selectedIds.size === 0 || uploading"
          @click="upload(false)"
        >
          Upload ({{ selectedIds.size }})
        </button>
        <button
          class="primary"
          :disabled="selectedIds.size === 0 || uploading"
          @click="upload(true)"
        >
          Upload & Display
        </button>
      </ActionBar>
    </template>

    <!-- New Collection Modal -->
    <div v-if="showNewModal" class="modal-overlay" @click.self="showNewModal = false">
      <div class="modal">
        <h3>New Collection</h3>
        <input
          v-model="newCollectionName"
          type="text"
          placeholder="Collection name"
          @keyup.enter="createCollection"
        />
        <div class="modal-actions">
          <button class="secondary" @click="showNewModal = false">Cancel</button>
          <button class="primary" :disabled="!newCollectionName.trim()" @click="createCollection">Create</button>
        </div>
      </div>
    </div>

    <!-- Rename Modal -->
    <div v-if="showRenameModal" class="modal-overlay" @click.self="showRenameModal = false">
      <div class="modal">
        <h3>Rename Collection</h3>
        <input
          v-model="renameValue"
          type="text"
          placeholder="New name"
          @keyup.enter="renameCollection"
        />
        <div class="modal-actions">
          <button class="secondary" @click="showRenameModal = false">Cancel</button>
          <button class="primary" :disabled="!renameValue.trim()" @click="renameCollection">Rename</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import ImageGrid from '../components/ImageGrid.vue'
import ActionBar from '../components/ActionBar.vue'
import CropSettings from '../components/CropSettings.vue'

const emit = defineEmits(['uploaded', 'preview'])

const collections = ref([])
const selectedCollectionId = ref(null)
const selectedCollection = computed(() =>
  collections.value.find(c => c.id === selectedCollectionId.value)
)

const items = ref([])
const selectedIds = ref(new Set())
const loading = ref(false)
const uploading = ref(false)
const unavailableCount = ref(0)

const cropPercent = ref(0)
const mattePercent = ref(10)

const showNewModal = ref(false)
const newCollectionName = ref('')
const showRenameModal = ref(false)
const renameValue = ref('')

const loadCollections = async () => {
  try {
    const res = await fetch('/api/collections')
    const data = await res.json()
    collections.value = data.collections || []
  } catch (e) {
    console.error('Failed to load collections:', e)
  }
}

const loadCollectionItems = async () => {
  if (!selectedCollectionId.value) {
    items.value = []
    return
  }

  loading.value = true
  selectedIds.value = new Set()

  try {
    const res = await fetch(`/api/collections/${selectedCollectionId.value}/items`)
    const data = await res.json()

    // Transform items for ImageGrid compatibility
    items.value = (data.items || []).map(item => {
      if (item.type === 'local') {
        return {
          ...item,
          // Use path as unique ID for local items
          _id: `local:${item.path}`,
          thumbnail: `/api/images/${encodeURIComponent(item.path)}/thumbnail`
        }
      } else {
        return {
          ...item,
          _id: `met:${item.object_id}`,
          content_id: `met_${item.object_id}`,
          thumbnail: item.image_url_small || item.image_url
        }
      }
    })

    unavailableCount.value = data.unavailable_count || 0
  } catch (e) {
    console.error('Failed to load collection items:', e)
  } finally {
    loading.value = false
  }
}

const toggleSelection = (item) => {
  const id = item._id
  const newSet = new Set(selectedIds.value)
  if (newSet.has(id)) {
    newSet.delete(id)
  } else {
    newSet.add(id)
  }
  selectedIds.value = newSet
}

const selectAll = (checked) => {
  if (checked) {
    selectedIds.value = new Set(items.value.map(i => i._id))
  } else {
    selectedIds.value = new Set()
  }
}

const setSettings = (settings) => {
  cropPercent.value = settings.crop
  mattePercent.value = settings.matte
}

const createCollection = async () => {
  const name = newCollectionName.value.trim()
  if (!name) return

  try {
    const res = await fetch('/api/collections', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    })
    const collection = await res.json()
    await loadCollections()
    selectedCollectionId.value = collection.id
    showNewModal.value = false
    newCollectionName.value = ''
  } catch (e) {
    console.error('Failed to create collection:', e)
  }
}

const renameCollection = async () => {
  const name = renameValue.value.trim()
  if (!name || !selectedCollectionId.value) return

  try {
    await fetch(`/api/collections/${selectedCollectionId.value}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    })
    await loadCollections()
    showRenameModal.value = false
  } catch (e) {
    console.error('Failed to rename collection:', e)
  }
}

const confirmDelete = async () => {
  if (!selectedCollection.value) return
  if (!confirm(`Delete "${selectedCollection.value.name}"? This cannot be undone.`)) return

  try {
    await fetch(`/api/collections/${selectedCollectionId.value}`, {
      method: 'DELETE'
    })
    selectedCollectionId.value = null
    items.value = []
    await loadCollections()
  } catch (e) {
    console.error('Failed to delete collection:', e)
  }
}

const removeSelected = async () => {
  if (selectedIds.value.size === 0 || !selectedCollectionId.value) return

  const itemsToRemove = items.value
    .filter(i => selectedIds.value.has(i._id))
    .map(i => i.type === 'local'
      ? { type: 'local', path: i.path }
      : { type: 'met', object_id: i.object_id }
    )

  try {
    await fetch(`/api/collections/${selectedCollectionId.value}/items`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: itemsToRemove })
    })
    await loadCollectionItems()
    await loadCollections() // Update item counts
  } catch (e) {
    console.error('Failed to remove items:', e)
  }
}

const upload = async (display) => {
  if (selectedIds.value.size === 0) return

  uploading.value = true

  // Separate local and met items
  const selected = items.value.filter(i => selectedIds.value.has(i._id))
  const localPaths = selected.filter(i => i.type === 'local').map(i => i.path)
  const metIds = selected.filter(i => i.type === 'met').map(i => i.object_id)

  try {
    // Upload local images
    if (localPaths.length > 0) {
      await fetch('/api/tv/upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          paths: localPaths,
          crop_percent: cropPercent.value,
          matte_percent: mattePercent.value,
          display: display && metIds.length === 0
        })
      })
    }

    // Upload Met images
    if (metIds.length > 0) {
      await fetch('/api/met/upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          object_ids: metIds,
          crop_percent: cropPercent.value,
          matte_percent: mattePercent.value,
          display
        })
      })
    }

    selectedIds.value = new Set()
    emit('uploaded')
  } catch (e) {
    console.error('Upload failed:', e)
  } finally {
    uploading.value = false
  }
}

// Open rename modal with current name
watch(showRenameModal, (show) => {
  if (show && selectedCollection.value) {
    renameValue.value = selectedCollection.value.name
  }
})

onMounted(loadCollections)
</script>

<style scoped>
.collections-panel {
  display: contents;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #2a2a4e;
  background: #12121f;
  gap: 1rem;
  flex-wrap: wrap;
}

.collection-select {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.collection-select select {
  padding: 0.4rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: #2a2a4e;
  color: white;
  min-width: 200px;
}

.new-btn {
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: #4a90d9;
  color: white;
  cursor: pointer;
  font-size: 1rem;
  font-weight: bold;
}

.collection-actions {
  display: flex;
  gap: 0.5rem;
}

.icon-btn {
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: #2a2a4e;
  color: #ccc;
  cursor: pointer;
  font-size: 0.85rem;
}

.icon-btn:hover {
  background: #3a3a5e;
}

.icon-btn.danger {
  color: #ff6b6b;
}

.icon-btn.danger:hover {
  background: #4a2a2e;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  color: #888;
  gap: 1rem;
}

.empty-state button {
  padding: 0.75rem 1.5rem;
  border-radius: 4px;
  border: none;
  background: #4a90d9;
  color: white;
  cursor: pointer;
}

.unavailable-notice {
  padding: 0.5rem 1rem;
  background: #3a2a2e;
  color: #ff9999;
  font-size: 0.85rem;
  text-align: center;
}

/* Modal styles */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: #1a1a2e;
  border-radius: 8px;
  padding: 1.5rem;
  width: 90%;
  max-width: 400px;
}

.modal h3 {
  margin: 0 0 1rem 0;
}

.modal input {
  width: 100%;
  padding: 0.75rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: #2a2a4e;
  color: white;
  margin-bottom: 1rem;
  box-sizing: border-box;
}

.modal input:focus {
  outline: none;
  border-color: #4a90d9;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.modal-actions button {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  border: none;
  cursor: pointer;
}

.modal-actions button.primary {
  background: #4a90d9;
  color: white;
}

.modal-actions button.secondary {
  background: #3a3a5e;
  color: white;
}

.modal-actions button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
```

**Step 2: Verify build**

Run: `cd src/frontend && npm run build`
Expected: Build succeeds

**Step 3: Commit**

```bash
git add src/frontend/src/views/CollectionsPanel.vue
git commit -m "feat: add CollectionsPanel view for browsing and managing collections"
```

---

## Task 9: Frontend - Add Collections Tab to SourcePanel

**Files:**
- Modify: `src/frontend/src/components/SourcePanel.vue`

**Step 1: Import CollectionsPanel**

Add import after line 31 (`import MetPanel from '../views/MetPanel.vue'`):

```javascript
import CollectionsPanel from '../views/CollectionsPanel.vue'
```

**Step 2: Add Collections to tabs array**

Update the tabs array (line 35-38) to:

```javascript
const tabs = [
  { id: 'local', label: 'Local' },
  { id: 'met', label: 'Met Museum' },
  { id: 'collections', label: 'Collections' }
]
```

**Step 3: Add CollectionsPanel to template**

After the MetPanel component (around line 24), add:

```vue
    <CollectionsPanel
      v-show="activeTab === 'collections'"
      @uploaded="$emit('uploaded')"
      @preview="(img, isLocal) => $emit('preview', img, isLocal)"
    />
```

**Step 4: Verify build**

Run: `cd src/frontend && npm run build`
Expected: Build succeeds

**Step 5: Commit**

```bash
git add src/frontend/src/components/SourcePanel.vue
git commit -m "feat: add Collections tab to SourcePanel"
```

---

## Task 10: Frontend - TV Slideshow Controls

**Files:**
- Modify: `src/frontend/src/views/TVPanel.vue`

**Step 1: Read TVPanel.vue to understand current structure**

First, read the file to see current implementation.

**Step 2: Add slideshow state and functions**

Add state variables after the existing ones:

```javascript
const slideshowEnabled = ref(false)
const slideshowDuration = ref(15)
const slideshowShuffle = ref(true)
const slideshowLoading = ref(false)
```

Add functions to load and save slideshow settings:

```javascript
const loadSlideshowStatus = async () => {
  try {
    const res = await fetch('/api/tv/slideshow')
    const data = await res.json()
    if (!data.error) {
      // Parse the response - format varies by TV
      slideshowEnabled.value = data.value !== 'off' && data.value !== '0'
      if (data.duration) {
        slideshowDuration.value = parseInt(data.duration) || 15
      }
      if (data.type !== undefined) {
        slideshowShuffle.value = data.type === true || data.type === 'shuffle'
      }
    }
  } catch (e) {
    console.error('Failed to load slideshow status:', e)
  }
}

const updateSlideshow = async () => {
  slideshowLoading.value = true
  try {
    await fetch('/api/tv/slideshow', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        enabled: slideshowEnabled.value,
        duration: slideshowDuration.value,
        shuffle: slideshowShuffle.value
      })
    })
  } catch (e) {
    console.error('Failed to update slideshow:', e)
  } finally {
    slideshowLoading.value = false
  }
}
```

Call `loadSlideshowStatus()` in the onMounted or when TV connects.

**Step 3: Add slideshow UI to template**

Add a slideshow settings section in the template (location depends on current TVPanel structure - typically in the header area):

```vue
<div v-if="connected" class="slideshow-settings">
  <h4>Slideshow</h4>
  <div class="slideshow-controls">
    <label class="toggle-label">
      <input
        type="checkbox"
        v-model="slideshowEnabled"
        @change="updateSlideshow"
        :disabled="slideshowLoading"
      />
      <span>Enable slideshow</span>
    </label>

    <div v-if="slideshowEnabled" class="slideshow-options">
      <label>
        <span>Change every:</span>
        <select v-model="slideshowDuration" @change="updateSlideshow" :disabled="slideshowLoading">
          <option :value="5">5 minutes</option>
          <option :value="10">10 minutes</option>
          <option :value="15">15 minutes</option>
          <option :value="30">30 minutes</option>
          <option :value="60">1 hour</option>
        </select>
      </label>

      <label class="toggle-label">
        <input
          type="checkbox"
          v-model="slideshowShuffle"
          @change="updateSlideshow"
          :disabled="slideshowLoading"
        />
        <span>Shuffle order</span>
      </label>
    </div>
  </div>
</div>
```

**Step 4: Add slideshow styles**

```css
.slideshow-settings {
  padding: 1rem;
  background: #12121f;
  border-bottom: 1px solid #2a2a4e;
}

.slideshow-settings h4 {
  margin: 0 0 0.75rem 0;
  font-size: 0.9rem;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.slideshow-controls {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.slideshow-options {
  display: flex;
  gap: 1.5rem;
  flex-wrap: wrap;
  padding-left: 1.5rem;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.toggle-label input {
  width: 18px;
  height: 18px;
}

.slideshow-options label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.slideshow-options select {
  padding: 0.3rem 0.5rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: #2a2a4e;
  color: white;
}
```

**Step 5: Verify build**

Run: `cd src/frontend && npm run build`
Expected: Build succeeds

**Step 6: Commit**

```bash
git add src/frontend/src/views/TVPanel.vue
git commit -m "feat: add slideshow controls to TVPanel"
```

---

## Task 11: Fix ImageGrid for Collection Items

**Files:**
- Modify: `src/frontend/src/components/ImageGrid.vue`

**Step 1: Understand the issue**

ImageGrid currently uses different ID fields for different sources:
- Local: `image.path`
- Met: `image.object_id`
- TV: `image.content_id`

Collection items need to use `item._id` which we set during transformation.

**Step 2: Update ImageGrid to handle collection items**

The ImageGrid component needs to detect collection items (which have `_id` field) and use that for selection.

Look for where the component extracts the ID from items and add handling for `_id`:

```javascript
const getItemId = (item) => {
  // Collection items have explicit _id
  if (item._id) return item._id
  // Local images use path
  if (item.path) return item.path
  // Met images use object_id
  if (item.object_id) return item.object_id
  // TV images use content_id
  if (item.content_id) return item.content_id
  return null
}
```

Use this function wherever the component checks selection state or emits toggle events.

**Step 3: Verify build and test**

Run: `cd src/frontend && npm run build`
Expected: Build succeeds

**Step 4: Commit**

```bash
git add src/frontend/src/components/ImageGrid.vue
git commit -m "fix: handle collection items with _id in ImageGrid"
```

---

## Task 12: End-to-End Testing

**Files:** None (manual testing)

**Step 1: Start the application**

Run: `docker-compose up --build`

**Step 2: Test collection CRUD**

1. Navigate to Collections tab
2. Create a new collection
3. Verify it appears in the dropdown
4. Rename it
5. Delete it

**Step 3: Test adding items to collection**

1. Go to Local tab, select some images
2. Click "+ Collection"
3. Create new collection or add to existing
4. Go to Collections tab, verify items appear

**Step 4: Test Met items in collection**

1. Go to Met tab, select some artwork
2. Add to collection
3. Verify items appear in collection with proper thumbnails

**Step 5: Test upload from collection**

1. In Collections tab, select items
2. Click "Upload & Display"
3. Verify images upload to TV

**Step 6: Test slideshow controls**

1. Go to TV tab (ensure TV is connected)
2. Enable slideshow
3. Change duration
4. Toggle shuffle
5. Verify settings persist

**Step 7: Commit any fixes**

If any issues found, fix and commit incrementally.

---

## Summary

This plan implements:

1. **Backend** (Tasks 1-4):
   - Collections service with JSON persistence
   - Full CRUD API for collections
   - Item management endpoints
   - TV slideshow control endpoints

2. **Frontend** (Tasks 5-11):
   - CollectionPicker modal component
   - "Add to Collection" in Local and Met panels
   - CollectionsPanel view with full management
   - Collections tab in SourcePanel
   - TV slideshow controls in TVPanel
   - ImageGrid updates for collection items

3. **Testing** (Task 12):
   - End-to-end verification of all features
