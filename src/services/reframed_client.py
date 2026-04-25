import re
import time
import asyncio
import logging
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import quote

import httpx

_LOGGER = logging.getLogger(__name__)

CDN_BASE = "https://imagedelivery.net/ypD62Q2Ttpsm-db9mriXAg"
R2_BASE = "https://pub-673dde4b801742e293be307ab76eb45d.r2.dev"
SITE_BASE = "https://www.reframed.gallery"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.reframed.gallery/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Nav/UI links that should not be treated as artist/artwork hrefs
_EXCLUDED_PATHS = {
    "/recent", "/collections", "/browse", "/artists", "/login",
    "/privacy", "/terms", "/about", "/contact",
}


def _thumbnail_url(image_id: str) -> str:
    return f"{CDN_BASE}/{image_id}/thumbnail"


def _preview_url(image_id: str) -> str:
    return f"{CDN_BASE}/{image_id}/preview"


def _slug_to_name(slug: str) -> str:
    return " ".join(w.capitalize() for w in slug.replace("-", " ").split())


class _ArtworkParser(HTMLParser):
    """Parse artwork cards from listing pages (collections, recent, artists)."""

    def __init__(self):
        super().__init__()
        self.artworks: list[dict] = []
        self._seen_ids: set[str] = set()
        self._current_href: Optional[str] = None

    def handle_starttag(self, tag: str, attrs: list[tuple]) -> None:
        attrs_dict = dict(attrs)

        if tag == "a":
            href = attrs_dict.get("href", "")
            parts = href.strip("/").split("/")
            if (
                len(parts) == 2
                and all(parts)
                and href not in _EXCLUDED_PATHS
                and not href.startswith("/collections/")
                and not href.startswith("/recent/")
                and not href.startswith("/artists/")
            ):
                self._current_href = href

        elif tag == "img" and self._current_href:
            src = attrs_dict.get("src", "")
            alt = attrs_dict.get("alt", "Untitled")
            if "imagedelivery.net" in src:
                # URL: https://imagedelivery.net/{account}/{image_id}/{variant}
                url_parts = src.split("/")
                if len(url_parts) >= 6:
                    image_id = url_parts[4]
                    if image_id and image_id not in self._seen_ids:
                        self._seen_ids.add(image_id)
                        href_parts = self._current_href.strip("/").split("/")
                        artist_slug = href_parts[0]
                        self.artworks.append({
                            "object_id": image_id,
                            "title": alt,
                            "artist": _slug_to_name(artist_slug),
                            "slug": self._current_href.strip("/"),
                            "thumbnail": _thumbnail_url(image_id),
                            "image_url": _preview_url(image_id),
                            "width": 0,
                            "height": 0,
                        })

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self._current_href = None


class _CollectionParser(HTMLParser):
    """Parse collection cards from /collections page."""

    def __init__(self):
        super().__init__()
        self.collections: list[dict] = []
        self._seen: set[str] = set()
        self._current_slug: Optional[str] = None
        self._current_name: Optional[str] = None

    def handle_starttag(self, tag: str, attrs: list[tuple]) -> None:
        attrs_dict = dict(attrs)

        if tag == "a":
            href = attrs_dict.get("href", "")
            if href.startswith("/collections/"):
                slug = href[len("/collections/"):]
                if slug and slug not in self._seen:
                    self._current_slug = slug

        elif tag == "img" and self._current_slug:
            alt = attrs_dict.get("alt", "")
            if alt:
                self._current_name = alt

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current_slug and self._current_name:
            self._seen.add(self._current_slug)
            self.collections.append({
                "slug": self._current_slug,
                "name": self._current_name,
            })
            self._current_slug = None
            self._current_name = None
        elif tag == "a":
            self._current_slug = None
            self._current_name = None


class _ArtistListParser(HTMLParser):
    """Parse artist cards from /artists listing pages."""

    def __init__(self):
        super().__init__()
        self.artists: list[dict] = []
        self._seen: set[str] = set()
        self._current_slug: Optional[str] = None

    def handle_starttag(self, tag: str, attrs: list[tuple]) -> None:
        attrs_dict = dict(attrs)

        if tag == "a":
            href = attrs_dict.get("href", "")
            parts = href.strip("/").split("/")
            # Single-segment slug: /paul-jenkins
            if (
                len(parts) == 1
                and parts[0]
                and href not in _EXCLUDED_PATHS
                and not href.startswith("/colors/")
                and not href.startswith("/collections/")
            ):
                self._current_slug = parts[0]

        elif tag == "img" and self._current_slug:
            alt = attrs_dict.get("alt", "")
            src = attrs_dict.get("src", "")
            if alt and "imagedelivery.net" in src and self._current_slug not in self._seen:
                self._seen.add(self._current_slug)
                self.artists.append({"slug": self._current_slug, "name": alt})

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self._current_slug = None


class _PaginationParser(HTMLParser):
    """Find max page number from pagination links."""

    def __init__(self, path_prefix: str):
        super().__init__()
        self._pattern = re.compile(rf'^{re.escape(path_prefix)}/page/(\d+)$')
        self.max_page = 1

    def handle_starttag(self, tag: str, attrs: list[tuple]) -> None:
        if tag == "a":
            href = dict(attrs).get("href", "")
            m = self._pattern.match(href)
            if m:
                self.max_page = max(self.max_page, int(m.group(1)))


def _parse_artworks(html: str) -> list[dict]:
    parser = _ArtworkParser()
    parser.feed(html)
    return parser.artworks


def _parse_collections(html: str) -> list[dict]:
    parser = _CollectionParser()
    parser.feed(html)
    return parser.collections


def _parse_max_page(html: str, path_prefix: str) -> int:
    parser = _PaginationParser(path_prefix)
    parser.feed(html)
    return parser.max_page


def _extract_r2_url(html: str) -> Optional[str]:
    """Find the public R2 full-resolution download URL embedded in an artwork page."""
    m = re.search(r'r2\.dev/(originals/[^"\\]+)', html)
    if m:
        key = m.group(1).strip()
        return f"{R2_BASE}/{quote(key, safe='/')}"
    return None


class ReframedClient:
    """Scraper client for reframed.gallery."""

    def __init__(self):
        self._cache: dict[str, tuple[float, any]] = {}
        self._ttl = 3600  # 1 hour

    def _get_cached(self, key: str) -> Optional[any]:
        entry = self._cache.get(key)
        if entry and entry[0] > time.time():
            return entry[1]
        return None

    def _set_cached(self, key: str, data: any) -> None:
        self._cache[key] = (time.time() + self._ttl, data)

    async def _fetch_html(self, url: str) -> str:
        _LOGGER.debug(f"Fetching: {url}")
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(url, headers=_HEADERS, timeout=15)
            resp.raise_for_status()
            return resp.text

    async def get_collections(self) -> list[dict]:
        cached = self._get_cached("collections")
        if cached is not None:
            return cached

        html = await self._fetch_html(f"{SITE_BASE}/collections")
        collections = _parse_collections(html)
        self._set_cached("collections", collections)
        return collections

    async def get_collection(self, slug: str, page: int = 1, page_size: int = 48) -> dict:
        cache_key = f"collection:{slug}"
        all_artworks = self._get_cached(cache_key)

        if all_artworks is None:
            html = await self._fetch_html(f"{SITE_BASE}/collections/{slug}")
            all_artworks = _parse_artworks(html)
            self._set_cached(cache_key, all_artworks)

        total = len(all_artworks)
        start = (page - 1) * page_size
        end = start + page_size

        return {
            "objects": all_artworks[start:end],
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": end < total,
        }

    async def get_recent(self, page: int = 1) -> dict:
        cache_key = f"recent:{page}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        url = f"{SITE_BASE}/recent" if page == 1 else f"{SITE_BASE}/recent/page/{page}"
        html = await self._fetch_html(url)
        artworks = _parse_artworks(html)
        max_page = _parse_max_page(html, "/recent")

        result = {
            "objects": artworks,
            "total": None,
            "page": page,
            "has_more": page < max_page,
        }
        self._set_cached(cache_key, result)
        return result

    async def get_color(self, color: str, page: int = 1, page_size: int = 48) -> dict:
        cache_key = f"color:{color}"
        all_artworks = self._get_cached(cache_key)

        if all_artworks is None:
            html = await self._fetch_html(f"{SITE_BASE}/colors/{color}")
            all_artworks = _parse_artworks(html)
            self._set_cached(cache_key, all_artworks)

        total = len(all_artworks)
        start = (page - 1) * page_size
        end = start + page_size

        return {
            "objects": all_artworks[start:end],
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": end < total,
        }

    async def get_artists(self) -> list[dict]:
        cached = self._get_cached("artists")
        if cached is not None:
            return cached

        async def fetch_page(page: int) -> list[dict]:
            url = f"{SITE_BASE}/artists" if page == 1 else f"{SITE_BASE}/artists/page/{page}"
            html = await self._fetch_html(url)
            parser = _ArtistListParser()
            parser.feed(html)
            return parser.artists

        pages = await asyncio.gather(*[fetch_page(p) for p in range(1, 8)])
        artists: list[dict] = []
        seen: set[str] = set()
        for page_artists in pages:
            for artist in page_artists:
                if artist["slug"] not in seen:
                    seen.add(artist["slug"])
                    artists.append(artist)

        self._set_cached("artists", artists)
        return artists

    async def get_artist(self, artist_slug: str, page: int = 1, page_size: int = 48) -> dict:
        cache_key = f"artist:{artist_slug}"
        all_artworks = self._get_cached(cache_key)

        if all_artworks is None:
            html = await self._fetch_html(f"{SITE_BASE}/{artist_slug}")
            all_artworks = _parse_artworks(html)
            self._set_cached(cache_key, all_artworks)

        total = len(all_artworks)
        start = (page - 1) * page_size
        end = start + page_size

        return {
            "objects": all_artworks[start:end],
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": end < total,
        }

    async def fetch_image(self, image_id: str, slug: str = "") -> bytes:
        """Download the full-resolution image for TV upload.

        Fetches the artwork page to extract the public R2 URL (original file).
        Falls back to CDN /public and /download variants if no R2 URL is found.
        """
        image_headers = {**_HEADERS, "Accept": "image/*"}

        if slug:
            try:
                html = await self._fetch_html(f"{SITE_BASE}/{slug}")
                r2_url = _extract_r2_url(html)
                if r2_url:
                    async with httpx.AsyncClient(follow_redirects=True) as client:
                        resp = await client.get(r2_url, headers=image_headers, timeout=60)
                        if resp.status_code == 200:
                            _LOGGER.info(f"Downloaded full-res from R2: {slug}")
                            return resp.content
                        _LOGGER.debug(f"R2 returned {resp.status_code} for {slug}")
            except Exception as e:
                _LOGGER.debug(f"R2 fetch failed for {slug}: {e}")

        last_error: Optional[Exception] = None
        async with httpx.AsyncClient(follow_redirects=True) as client:
            for variant in ("public", "download"):
                url = f"{CDN_BASE}/{image_id}/{variant}"
                try:
                    resp = await client.get(url, headers=image_headers, timeout=30)
                    if resp.status_code == 200:
                        _LOGGER.info(f"Downloaded reframed image via /{variant}: {image_id}")
                        return resp.content
                    _LOGGER.debug(f"/{variant} returned {resp.status_code} for {image_id}")
                    last_error = Exception(f"HTTP {resp.status_code} from /{variant}")
                except Exception as e:
                    _LOGGER.debug(f"/{variant} failed for {image_id}: {e}")
                    last_error = e

        raise RuntimeError(f"Could not download full-resolution image {image_id}") from last_error


_client: Optional[ReframedClient] = None


def get_reframed_client() -> ReframedClient:
    global _client
    if _client is None:
        _client = ReframedClient()
    return _client
