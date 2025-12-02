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
