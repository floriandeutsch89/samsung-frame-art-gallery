# Samsung Frame Art Gallery — Claude Context

## What this project is

A self-hosted web app for managing artwork on Samsung Frame TVs. FastAPI backend + Vue 3 SPA, deployed via Docker Compose with Caddy as HTTPS reverse proxy.

## Stack

- **Backend:** Python 3.13, FastAPI, Pillow, pillow-heif, samsungtvws
- **Frontend:** Vue 3 (Composition API, `<script setup>`), Vite, no UI framework
- **Proxy:** Caddy 2 (terminates TLS, proxies HTTP to app:8080)
- **Package manager:** `uv` (backend), `npm` (frontend)
- **Docker:** multi-stage build — Node build stage → Python deps stage → slim runtime

## Key architecture decisions

### TV upload is strictly sequential
The Samsung WebSocket art API (`samsungtvws`) cannot upload in parallel — it is a request-response protocol over a single connection. `upload_artwork_batch()` in `tv_client.py` reuses one WebSocket session across all images to avoid repeated handshakes. Do not attempt parallelism here.

### Upload progress uses SSE
`POST /api/tv/upload/stream` returns `text/event-stream`. The async generator uses `asyncio.Queue` + `loop.call_soon_threadsafe()` to bridge events from the blocking upload thread back to the async SSE generator. The frontend composable `useUploadStream.js` reads this stream.

### Image processing pipeline
All images sent to the TV are JPEG regardless of source format (3-5× smaller than PNG, visually identical on the TV). `process_for_tv()` in `image_processor.py` is the single entry point — handles crop, matte, and reframe modes. HEIC/HEIF support requires `pillow_heif.register_heif_opener()` which is called at module level in both `images.py` and `thumbnails.py`.

### Reframe zoom quality
When zoom > 1.0, `_reframe_image` returns the crop at its **native resolution** (no upscaling). The TV resolution cap (`TV_MAX_WIDTH = 3840`, `TV_MAX_HEIGHT = 2160`) is applied afterwards in `process_for_tv`. Do not add upscaling back — it degrades quality by interpolating then downscaling again.

### Auth middleware
`APP_PASSWORD` env var enables optional password auth. Middleware in `main.py` checks for an HMAC-signed cookie before every request. The login page is a self-contained HTML page served by FastAPI (not Vue) so it gates the entire app including static assets. Changing `APP_PASSWORD` automatically invalidates all existing cookies.

### reframe_offsets dict shape
The `reframe_offsets` field in `PreviewRequest` and `UploadRequest` maps path → `{"x": float, "y": float, "zoom": float}`. Zoom defaults to 1.0 if absent. This keeps the API shape stable — no separate zoom field at the top level.

### Reframed Gallery integration
`reframed_client.py` scrapes reframed.gallery using stdlib `html.parser` — no BeautifulSoup. Key details:

- **Full-res download:** Each artwork page embeds a public Cloudflare R2 URL (`pub-673dde4b801742e293be307ab76eb45d.r2.dev/originals/{Artist} - {Title} - reframed.jpg`). `fetch_image(image_id, slug)` fetches the artwork page, extracts this URL via regex, and downloads from R2. Falls back to CDN `/public` and `/download` variants; **no `/preview` fallback** — the user requires original quality. For the **preview modal only**, `fetch_preview_image(image_id)` downloads the lightweight CDN `/preview` variant instead — sufficient for on-screen comparison, avoids fetching MB-sized originals.
- **Artist pages are at `/{slug}`**, not `/artists/{slug}`. Fetching `/artists/{slug}` returns 404.
- **Reframe mode is the default** for Reframed Gallery uploads (`reframe_enabled=True` in `ReframedUploadRequest`). This center-crops to fill 16:9 with no white borders. matte_percent defaults to 0.
- **Two-layer caching:** Backend in-memory dict (TTL 3600s), frontend module-level Map (TTL 3600ms, survives tab switches).
- **Artists list:** Fetches all 7 pages in parallel via `asyncio.gather`. The CDN variants available on this account are `blur`, `thumbnail`, and `preview` — `public` and `download` are not configured.
- The `slug` field on `ReframedItem` must be passed from the frontend so the backend can look up the R2 URL. It is the `artist-slug/artwork-slug` path extracted during scraping.
- Preview cache entries are purged at startup for files older than 30 days (`get_preview_cache().purge_older_than(30)` in `main.py` lifespan).

## File layout

```
src/
  main.py                  # FastAPI app, auth middleware, router registration
  api/
    auth.py                # Login page, cookie auth, APP_PASSWORD logic
    images.py              # Local image browse/upload/delete endpoints
    tv.py                  # TV control, upload (batch + SSE stream), preview, slideshow
    met.py                 # Met Museum API proxy
    reframed.py            # Reframed Gallery proxy + upload endpoints
    collections.py         # Collections management
  services/
    tv_client.py           # TVClient singleton, WebSocket wrapper, thumbnail cache
    tv_settings.py         # Persistent TV IP/name settings (JSON file in /app/data)
    tv_thumbnail_cache.py  # Disk cache for TV artwork thumbnails (/app/data/thumbnails/tv)
    tv_discovery.py        # SSDP network scan
    image_processor.py     # process_for_tv(), generate_preview(), _reframe_image()
    thumbnails.py          # Local image thumbnail generation + dimension cache
    preview_cache.py       # Disk cache for preview images (keyed by path+params+zoom)
    reframed_client.py     # HTML scraper for reframed.gallery; R2 full-res download
src/frontend/src/
  views/
    LocalPanel.vue         # Local image browser, upload, bulk delete, reframe state
    MetPanel.vue           # Met Museum browser
    ReframedPanel.vue      # Reframed Gallery browser (recent/colors/collections/artists)
    CollectionsPanel.vue   # Collections
    TVPanel.vue            # TV artwork management
  components/
    ImageCard.vue          # Single image card (checkbox, lazy load) — no per-card delete
    ImageGrid.vue          # Masonry grid with infinite scroll
    CropSettings.vue       # Crop/matte/reframe controls (no Preview button — it's in ActionBar)
    PreviewModal.vue       # Before/after preview + reframe drag canvas + zoom slider
    TvConnectionModal.vue  # TV discovery + manual IP entry (pre-fills from env_ip)
    ActionBar.vue          # Bottom bar with left slot (settings/progress) + button slot
  composables/
    useUploadStream.js     # SSE upload state (uploading, phase, current, total, name, pct)
docker/
  Dockerfile               # 3-stage: node:22-alpine → python:3.13-slim deps → runtime
  entrypoint.sh
  Caddyfile
```

## Environment variables

| Var | Default | Notes |
|-----|---------|-------|
| `APP_PASSWORD` | - | Leave empty = no auth |
| `IMAGES_DIR` | `/images` | Bind-mount path inside container |
| `TV_IP` | - | Bootstrap auto-connect; saved settings take precedence |
| `DEFAULT_CROP_PERCENT` | `0` | Sent to frontend via `/api/tv/config` |
| `DEFAULT_MATTE_PERCENT` | `10` | Sent to frontend via `/api/tv/config` |
| `THUMBNAILS_DIR` | `/app/data/thumbnails` | Auto-detected in Docker |
| `DISABLE_MET_GALLERY` | `1` | Set to `1` to hide the Metropolitan Museum of Art tab (default hidden) |

## Gotchas

- `/images` volume must be **read-write** (not `:ro`) — the upload endpoint writes to `/images/uploads/`
- `CACHE_DIR.mkdir(parents=True, exist_ok=True)` — always use `parents=True`; the parent directories may not exist yet
- The `json` module must be imported in `tv.py` — the SSE endpoint uses `json.dumps()` inside an async generator where missing imports fail silently (stream closes, frontend sees nothing)
- Per-card delete was removed from `ImageCard.vue` — local images are deleted via the bulk "Delete (N)" button in ActionBar only. `ImageCard` no longer emits `delete` and `ImageGrid` no longer proxies it.
- `ImageCard` has a hover preview: after 250ms, a 360px overlay is teleported to `<body>` showing the image at full card width. Uses `image.image_url` (Reframed `/preview`, Met primary) when available, falls back to thumbnail. The scoped `img` rule uses class `.card-img` — **do not revert to a bare `img` selector** or it bleeds `opacity: 0` into the teleported overlay via Vue's scoped data attribute.
- `Array.from(selectedIds)` inline in a Vue template creates a new array reference on every render and triggers watches. Use a `computed()` instead
- Touch `touchmove` listeners need `{ passive: false }` to allow `e.preventDefault()` in the drag handler
- The SPA catch-all route `/{full_path:path}` in `main.py` must be registered **after** all other routes including `/login`

## Supported local image formats

Browse + thumbnail: `.jpg`, `.jpeg`, `.png`, `.webp`, `.tiff`, `.tif`, `.heic`, `.heif`
Upload from browser: same, plus auto-conversion to JPEG on ingest
TV upload: always JPEG (converted by `process_for_tv`)

## Docker / deployment notes

- Caddy terminates TLS; backend only speaks plain HTTP on port 8080
- `appuser` UID 1000 owns `/app`, `/app/data`, `/images`, `/thumbnails` — pre-created in Dockerfile
- Git is only in the `python-deps` build stage (needed for `samsungtvws` install); not in the runtime image
- Both `docker-compose.yml` and `docker-compose.ghcr.yml` must stay in sync on env vars

## Release process

1. Bump `VERSION` file
2. Update `CHANGELOG.md`
3. Commit + push → GitHub Actions builds and pushes to GHCR automatically
