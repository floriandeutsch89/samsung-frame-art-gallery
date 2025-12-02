# User Collections - Design Document

## Overview

User-defined collections for organizing artwork from Local and Met sources, batch uploading to TV, plus TV slideshow controls.

## Features

1. **Collections as a source** - Third tab alongside Local/Met
2. **Mixed sources** - Collections contain both local images and Met artwork
3. **Workflow** - Select images in Local/Met → "Add to Collection" → pick/create collection
4. **Full management** - Browse, upload, remove, reorder, rename, delete
5. **Creation** - On-demand when adding, or explicit in Collections tab
6. **TV slideshow controls** - Enable/disable, duration, shuffle

---

## Data Model

**File:** `/app/data/collections.json`

```json
{
  "version": 1,
  "collections": [
    {
      "id": "c1a2b3",
      "name": "Living Room Art",
      "created_at": "2024-01-15T10:30:00Z",
      "items": [
        {
          "type": "local",
          "path": "/images/landscapes/sunset.jpg",
          "added_at": "2024-01-15T10:30:00Z"
        },
        {
          "type": "met",
          "object_id": 436535,
          "added_at": "2024-01-15T10:32:00Z"
        }
      ]
    }
  ]
}
```

**Backend dataclasses** (`src/services/collections.py`):

```python
@dataclass
class CollectionItem:
    type: Literal["local", "met"]
    path: str | None = None       # for local
    object_id: int | None = None  # for met
    added_at: str

@dataclass
class Collection:
    id: str
    name: str
    created_at: str
    items: list[CollectionItem]
```

**Key decisions:**
- `version` field for future schema migrations
- Short IDs (6-char hex) - human-readable, collision-unlikely
- `type` discriminator determines how to resolve item
- `added_at` timestamps for ordering
- No cached metadata - fetch fresh from source

---

## Backend API

**New file:** `src/api/collections.py`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/collections` | List all collections (id, name, item count) |
| `POST` | `/api/collections` | Create new collection |
| `GET` | `/api/collections/{id}` | Get collection with resolved items |
| `PATCH` | `/api/collections/{id}` | Rename collection |
| `DELETE` | `/api/collections/{id}` | Delete collection |
| `POST` | `/api/collections/{id}/items` | Add items to collection |
| `DELETE` | `/api/collections/{id}/items` | Remove items from collection |
| `PUT` | `/api/collections/{id}/items/order` | Reorder items |

**New service:** `src/services/collections.py`
- Singleton pattern (matches `tv_settings.py`)
- `load_collections()`, `save_collections()`
- In-memory cache, writes to disk on changes

**Item resolution on GET:**
- Local: read file info, skip missing files
- Met: fetch from MetClient cache or API
- Return `unavailable_count` for missing items

**TV slideshow endpoints** (add to `src/api/tv.py`):

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/tv/slideshow` | Get current slideshow status |
| `POST` | `/api/tv/slideshow` | Set slideshow settings |

Request body:
```json
{
  "enabled": true,
  "duration": 15,
  "shuffle": true
}
```

---

## Frontend Components

### New Components

**`src/frontend/src/views/CollectionsPanel.vue`**

```
┌─────────────────────────────────────────────┐
│ [Dropdown: Select Collection ▼] [+ New]     │
├─────────────────────────────────────────────┤
│                                             │
│   (reuses ImageGrid + ImageCard)            │
│   Cards show source badge                   │
│                                             │
├─────────────────────────────────────────────┤
│ ActionBar:                                  │
│ [Upload to TV] [Remove from Collection]     │
│ [Rename] [Delete Collection]                │
└─────────────────────────────────────────────┘
```

**`src/frontend/src/components/CollectionPicker.vue`**
- Dropdown list of existing collections
- Text input to create new collection inline
- Used by LocalPanel and MetPanel when adding

### Modifications to Existing Components

**SourcePanel.vue:**
- Add Collections as third tab alongside Local/Met

**LocalPanel.vue & MetPanel.vue:**
- Add "Add to Collection" button in ActionBar (visible when images selected)
- Opens CollectionPicker modal/dropdown

**TVPanel.vue:**
- Add slideshow settings section:

```
┌─────────────────────────────────────────────┐
│ Slideshow Settings                          │
│ ┌─────────────────────────────────────────┐ │
│ │ [Toggle: Off / On]                      │ │
│ │ Duration: [Dropdown: 5 min ▼]           │ │
│ │ [Checkbox] Shuffle order                │ │
│ └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

Controls visible only when TV connected.

---

## Error Handling

**Missing local images:**
- Skip silently when resolving collection items
- Return `unavailable_count` in API response
- Frontend shows subtle notice: "X images unavailable"

**Missing Met artwork:**
- Skip item if Met API returns 404
- Include in `unavailable_count`

**Empty collections:**
- Allowed - show empty state with prompt to add images

**Duplicate prevention:**
- Check if item already in collection before adding
- Skip duplicates silently

**Collection name validation:**
- Trim whitespace, reject empty names
- Allow duplicate names
- Max length: 100 characters

**Concurrent access:**
- Write atomically (temp file + rename)

**TV slideshow:**
- Show error toast if TV disconnected
- Hide controls if TV doesn't support slideshow

---

## File Changes Summary

### New Files
- `src/api/collections.py` - Collections API routes
- `src/services/collections.py` - Collections service (singleton)
- `src/frontend/src/views/CollectionsPanel.vue` - Collections panel
- `src/frontend/src/components/CollectionPicker.vue` - Collection picker modal

### Modified Files
- `src/main.py` - Mount collections router
- `src/api/tv.py` - Add slideshow endpoints
- `src/services/tv_client.py` - Add slideshow methods (if not already exposed)
- `src/frontend/src/components/SourcePanel.vue` - Add Collections tab
- `src/frontend/src/views/LocalPanel.vue` - Add "Add to Collection" button
- `src/frontend/src/views/MetPanel.vue` - Add "Add to Collection" button
- `src/frontend/src/views/TVPanel.vue` - Add slideshow controls
