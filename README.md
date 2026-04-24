# Samsung Frame Art Gallery

A self-hosted web application for managing artwork on Samsung Frame TVs. Browse your local image collection or discover public domain masterpieces from the Metropolitan Museum of Art, then upload them to your TV with customizable framing options.

> **Note:** This is a fork of [samsung-frame-art-gallery](https://github.com/mcsdodo/samsung-frame-art-gallery) with a custom infrastructure stack including Caddy reverse proxy, automated GHCR releases, and enhanced security features.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.13+-blue.svg)
![Node](https://img.shields.io/badge/node-22+-green.svg)
![Vue](https://img.shields.io/badge/vue-3.5+-green.svg)

## Features

### Image Sources
- **Local Images** - Browse your personal image collection with folder navigation and smart thumbnails
- **Met Museum Collection** - Discover and upload public domain artwork from The Metropolitan Museum of Art's open collection (400,000+ works)

### TV Integration
- **Auto TV Discovery** - Automatically finds Samsung Frame TVs on your network via SSDP
- **Batch Upload** - Upload multiple images to your TV at once
- **Art Management** - View, display, and delete artwork on your TV
- **Live Preview** - See exactly how your images will look before uploading

### Image Processing
- **Smart Cropping** - Remove unwanted edges from images (0-50%)
- **Auto Matte** - Automatically add museum-style matting to fit the 16:9 frame
- **Re-framing Mode** - Fill the entire frame with adjustable positioning for single images

### User Experience
- **Responsive Design** - Split-panel desktop layout, tabbed mobile interface
- **Infinite Scroll** - Seamless browsing through large collections
- **Masonry Layout** - Beautiful variable-height image grid
- **Docker-Ready** - One-command deployment with automatic HTTPS via Caddy
- **Secure HTTPS** - Built-in reverse proxy with self-signed certificate support

## Screenshots

### Local Images with Masonry Layout
Browse your image collection with a beautiful masonry grid and TV artwork panel.

![Local Images](screenshots/01-local-images.png)

### Met Museum Collection Search
Search and browse public domain artwork from The Metropolitan Museum of Art.

![Met Museum Search](screenshots/02-met-museum.png)

### Preview with Crop & Matte
See how your images will look with cropping and automatic matting before upload.

![Preview Modal](screenshots/03-preview-modal.png)

### Re-framing Mode
Fill the entire frame with draggable positioning for single images.

![Re-framing Preview](screenshots/04-reframe-preview.png)

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Samsung Frame TV (or any Samsung TV with Art Mode) on the same network
- A folder of images (optional - you can also use the Met Museum collection)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/samsung-frame-art-gallery.git
   cd samsung-frame-art-gallery
   ```

2. **Configure your setup**

   Copy `.env.example` to `.env` and customize as needed:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` to set your domain and paths:
   ```env
   IMAGES_DIR=./images
   DOMAIN=artgallery.example.com         # Update to your domain
   TV_IP=                                # Optional: pre-configured TV IP
   ```

3. **Start the application**
   ```bash
   docker-compose up -d
   ```

4. **Open the web UI**

   Navigate to `https://artgallery.example.com` (or your configured domain)

   **Note:** You'll see a browser warning about the self-signed certificate. This is expected for self-hosted local network applications. Click "Advanced" and accept the certificate to proceed.

5. **Connect to your TV**

   Click the TV status indicator in the header to discover and select your Samsung TV.

### Using Pre-built Images from GHCR

Instead of building the image locally, you can use pre-built images from GitHub Container Registry:

1. **Use the GHCR-based compose file**
   ```bash
   cp .env.example .env
   docker-compose -f docker-compose.ghcr.yml up -d
   ```

2. **Update the image reference** in `docker-compose.ghcr.yml`
   - Replace `YOUR_USERNAME` with the actual GitHub username
   - Example: `ghcr.io/yourusername/samsung-frame-art-gallery:latest`

3. **Authenticate with GHCR** (if image is private)
   ```bash
   docker login ghcr.io -u yourusername -p YOUR_GITHUB_TOKEN
   ```

**Available image tags:**
- `latest` - Most recent stable release
- `1.0.0`, `1.1.0`, etc. - Specific version tags (semantic versioning)

**Benefits:**
- No local build required - faster deployment
- Consistent images across environments
- Automatic updates via GitHub Actions on releases

## Versioning & Releases

This project uses **Semantic Versioning** and maintains a [CHANGELOG.md](CHANGELOG.md) documenting all changes.

### Release Process

1. Update `VERSION` file with new version number (e.g., `1.1.0`)
2. Add changes to `CHANGELOG.md` under the version header
3. Commit and push to main/master
4. GitHub Actions automatically:
   - Creates a GitHub Release with changelog content
   - Builds and pushes Docker image to GHCR
   - Tags image with version number and `latest`

### GitHub Container Registry

Images are automatically published to:
```
ghcr.io/YOUR_USERNAME/samsung-frame-art-gallery:VERSION
ghcr.io/YOUR_USERNAME/samsung-frame-art-gallery:latest
```

Build status and image metadata are visible on the [Packages](../../packages) page.

## Configuration

### Environment Variables

Create a `.env` file (see `.env.example`) to configure the application:

| Variable | Default | Description |
|----------|---------|-------------|
| `IMAGES_DIR` | `./images` | Path to your local image collection |
| `TV_IP` | - | Pre-configure TV IP (skips auto-discovery) |
| `DEFAULT_CROP_PERCENT` | `5` | Default edge crop percentage (0-50) |
| `DEFAULT_MATTE_PERCENT` | `10` | Default matte size percentage (0-50) |
| `DOMAIN` | `artgallery.example.com` | Domain for HTTPS reverse proxy |

### HTTPS & Reverse Proxy

The application uses **Caddy** as a reverse proxy to automatically provide HTTPS with self-signed certificates. This setup:

- Listens on ports 80 (HTTP) and 443 (HTTPS)
- Automatically redirects HTTP → HTTPS
- Automatically generates and manages self-signed certificates
- Reads the domain from the `DOMAIN` environment variable (set in `.env`)
- Proxies all requests to the FastAPI backend

**Certificate Generation:**

Caddy automatically generates self-signed certificates on first start. No manual setup required. The certificates are stored in the `caddy_config` Docker volume and persist across restarts.

The domain is configured via the `DOMAIN` environment variable in `.env`, which is passed to Caddy at startup.

For **production use with Let's Encrypt**, update the Caddyfile:
```
{$DOMAIN}:443 {
  tls your-email@example.com  # Enable ACME (Let's Encrypt)
  reverse_proxy app:8080
}
```

### Docker Compose Services

```yaml
services:
  caddy:
    image: caddy:2-alpine
    # Reverse proxy with automatic self-signed HTTPS
    # Reads DOMAIN from .env for hostname configuration
    # Ports: 80 (HTTP → HTTPS redirect), 443 (HTTPS)
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data              # Certificate storage
      - caddy_config:/config          # Configuration persistence
    environment:
      - DOMAIN=${DOMAIN:-artgallery.example.com}

  app:
    build: ./docker/Dockerfile
    ports:
      - "8080:8080"  # Direct access for debugging
    volumes:
      - ./images:/images:ro
      - ./data/thumbnails:/thumbnails
      - ./data:/app/data
```

## Usage

### Local Images Tab

1. Browse your image collection using folder navigation
2. Select one or more images by clicking on them
3. Adjust crop and matte percentages, or enable "Re-framing" mode
4. Click "Preview" to see how images will look on the TV
5. Click "Upload" or "Upload & Display"

### Met Museum Tab

1. Browse highlighted works or filter by medium (Paintings, Drawings, etc.)
2. Use search to find specific artworks
3. Select works and preview/upload just like local images
4. All Met Museum images are public domain - free to use

### TV Panel

1. View all artwork currently stored on your TV
2. Click any artwork to display it
3. Delete artwork you no longer want

## Development

### Local Setup

**Backend (with uv):**
```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies and create virtual environment
uv sync

# Activate virtual environment
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Run with hot reload
uvicorn src.main:app --reload --host 0.0.0.0 --port 8080
```

**Frontend:**
```bash
cd src/frontend
npm install
npm run dev
```

### Project Structure

```
samsung-frame-art-gallery/
├── src/
│   ├── main.py                 # FastAPI application entry point
│   ├── api/
│   │   ├── images.py           # Local image endpoints
│   │   ├── tv.py               # TV control & upload endpoints
│   │   └── met.py              # Met Museum API endpoints
│   ├── services/
│   │   ├── tv_client.py        # Samsung TV WebSocket client
│   │   ├── tv_discovery.py     # SSDP-based TV discovery
│   │   ├── tv_settings.py      # Persistent TV selection
│   │   ├── met_client.py       # Met Museum API client
│   │   ├── image_processor.py  # Crop, matte, reframe processing
│   │   ├── thumbnails.py       # Local image thumbnails
│   │   └── preview_cache.py    # Preview generation cache
│   └── frontend/               # Vue 3 + Vite SPA
│       ├── src/
│       │   ├── views/
│       │   │   ├── LocalPanel.vue
│       │   │   ├── MetPanel.vue
│       │   │   └── TVPanel.vue
│       │   └── components/
│       └── package.json
├── docker/
│   ├── Dockerfile              # Multi-stage build
│   └── Caddyfile               # Caddy reverse proxy config
├── .github/workflows/
│   ├── build.yml               # Build and push Docker image
│   └── release.yml             # Create GitHub Release
├── docker-compose.yml
├── docker-compose.ghcr.yml
├── pyproject.toml              # Python project configuration (uv)
├── requirements.txt            # Legacy pip requirements
└── Caddyfile                   # Caddy configuration
│   │   └── preview_cache.py    # Preview generation cache
│   └── frontend/               # Vue 3 + Vite SPA
│       ├── src/
│       │   ├── views/
│       │   │   ├── LocalPanel.vue
│       │   │   ├── MetPanel.vue
│       │   │   └── TVPanel.vue
│       │   └── components/
│       └── package.json
├── docker/
│   └── Dockerfile              # Multi-stage build
├── docker-compose.yml
└── requirements.txt
```

### Tech Stack

- **Backend:** FastAPI 0.115+, Python 3.13-slim, Pillow 11+, httpx 0.27+
- **Frontend:** Vue 3.5+, Vite 5.2+, Node 22-alpine (build)
- **Reverse Proxy:** Caddy 2-alpine (HTTPS, self-signed certificates)
- **TV Communication:** [samsung-tv-ws-api](https://github.com/NickWaterton/samsung-tv-ws-api)
- **External APIs:** [Met Museum Collection API](https://metmuseum.github.io/)
- **Infrastructure:** Docker 20.10+, Docker Compose 2.0+
- **CI/CD:** GitHub Actions (automatic builds to GHCR on version changes)

## Deployment

### Local Build & Run
```bash
docker-compose up -d --build
```
Builds image locally and starts services.

### From GHCR (Pre-built)
```bash
docker-compose -f docker-compose.ghcr.yml up -d
```
Uses pre-built image from GitHub Container Registry - faster startup, no build required.

## API Reference

### Local Images

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/images` | List images (optional `?folder=` filter) |
| GET | `/api/images/folders` | List available folders |
| GET | `/api/images/{path}/thumbnail` | Get image thumbnail |
| GET | `/api/images/{path}/full` | Get full image |

### Met Museum

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/met/departments` | List museum departments |
| GET | `/api/met/highlights` | Get highlighted artworks |
| GET | `/api/met/medium/{medium}` | Get artworks by medium |
| GET | `/api/met/search?q=` | Search artworks |
| GET | `/api/met/object/{id}` | Get artwork details |
| POST | `/api/met/preview` | Generate processed preview |
| POST | `/api/met/upload` | Upload artwork to TV |

### TV Control

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tv/discover` | Scan for Samsung TVs |
| GET | `/api/tv/status` | Get TV connection status |
| GET | `/api/tv/settings` | Get saved TV selection |
| POST | `/api/tv/settings` | Save TV selection |
| GET | `/api/tv/artwork` | List artwork on TV |
| GET | `/api/tv/artwork/current` | Get currently displayed artwork |
| POST | `/api/tv/artwork/current` | Display specific artwork |
| DELETE | `/api/tv/artwork/{id}` | Delete artwork from TV |
| POST | `/api/tv/preview` | Generate upload preview |
| POST | `/api/tv/upload` | Upload local images to TV |

## TV Compatibility

Tested with Samsung Frame TVs. Should work with any Samsung TV that supports Art Mode via WebSocket API.

**Supported TV API versions:**
- v3.x (older Frame models)
- v4.x+ (newer models with SSL)

## Troubleshooting

**Caddy/domain issues:** Verify `.env` has `DOMAIN=artgallery.example.com`. Restart: `docker-compose down && docker-compose up -d`

**Linux permissions:**
If images or thumbnails won't load, or you see errors like `[Errno 13] Permission denied: '/thumbnails/tv'`, your bind-mounted directories may be owned by root or another user.

To fix this, ensure the container's appuser (UID 1000) owns the relevant folders:

```bash
sudo chown -R 1000:1000 ./images ./data
```

This is required on Linux when using bind mounts, since Docker creates new host folders as root by default. (You may need to run this after first starting the container.)

**HTTPS certificate warning:** Expected with self-signed certificates. Click "Advanced" → "Proceed" and browser will remember.

**TV not discovered:** Ensure TV is on same network and powered on (not deep standby).

**Upload fails:** Verify TV is in Art Mode and image is JPEG/PNG format.

**Thumbnails missing:** Allow time for first-run processing; check read permissions on images directory.

## License

MIT License - see [LICENSE](LICENSE) file for details.
