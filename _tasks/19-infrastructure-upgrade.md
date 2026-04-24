# Infrastructure Upgrade - Caddy Reverse Proxy & Dependency Updates

## Summary
Updated the Samsung Frame Art Gallery project with modern infrastructure practices:
- Added Caddy reverse proxy for HTTPS with automatic self-signed certificate generation
- Updated all dependencies to latest stable versions
- Implemented environment-based configuration (.env)
- Enhanced documentation and deployment experience

## Changes Made

### 1. Dependency Updates

#### Frontend (`src/frontend/package.json`)
- **Vue:** 3.4.0 → 3.6.0+ (latest stable)
- **Vite:** 5.0.0 → 6.2.0+ (latest stable)
- **@vitejs/plugin-vue:** 5.0.0 → 6.1.0+ (latest stable)
- `@yeger/vue-masonry-wall` kept at 5.1.4 (stable)

#### Backend (`requirements.txt`)
- **FastAPI:** 0.109.0 → 0.115.0+ (latest stable)
- **uvicorn:** 0.27.0 → 0.32.0+ (latest stable)
- **Pillow:** 10.2.0 → 11.1.0+ (latest stable)
- **python-multipart:** 0.0.6 → 0.0.7+ (latest stable)
- **httpx:** Added at 0.27.0+ (explicit dependency)
- `samsung-tv-ws-api` kept at git source (no pinned version)

### 2. New Files Created

#### `.env.example`
Template for environment configuration. Includes:
- `IMAGES_DIR` - Local image collection path
- `TV_IP` - Optional pre-configured TV IP
- `DEFAULT_CROP_PERCENT` - Image crop default (0-50%)
- `DEFAULT_MATTE_PERCENT` - Matte size default (0-50%)
- `DOMAIN` - Application domain (default: artgallery.example.com)

#### `.env`
Actual environment file (not committed to git). Users copy from `.env.example` and customize with their domain.

#### `Caddyfile`
Caddy reverse proxy configuration:
- Listens on `{$DOMAIN}:443` (HTTP) and `{$DOMAIN}:80` (HTTPS)
- Auto-redirects HTTP → HTTPS
- **Automatically generates self-signed certificates** (via `tls internal`)
- Proxies all requests to FastAPI backend (app:8080)
- Uses environment variable substitution: `{$DOMAIN}` reads from `.env` (passed via docker-compose)

### 3. Modified Files

#### `docker-compose.yml`
Complete rewrite to include Caddy:
- **New `caddy` service:**
  - Image: `caddy:2-alpine` (minimal, fast)
  - Ports: 80, 443 (public-facing)
  - Volumes: Caddyfile config only (no certs volume needed)
  - Environment: Passes `DOMAIN` from `.env` to Caddy for dynamic hostname configuration
  - Named volumes for Caddy data/config persistence
  - Depends on `app` service
- **Updated `app` service:**
  - Added port mapping for debugging: `8080:8080` (in addition to expose)
  - Added to named `frame-network` bridge network
- **New networking:**
  - Created `frame-network` bridge for inter-container communication
  - Caddy → app communication via docker DNS

#### `.gitignore`
No certificate directories needed - Caddy manages everything in `caddy_config` volume

#### `README.md`
Comprehensive documentation updates:
1. **Badge updates:** Vue 3.4+ → 3.5+
2. **Features section:** Added mentions of HTTPS and Caddy
3. **Installation section:**
   - Removed manual certificate generation steps
   - Simplified to just .env configuration
   - Updated web UI access URL to custom domain (user-configurable)
   - Browser certificate warning explanation
4. **Configuration section:** Complete rewrite
   - Environment variables table with DOMAIN variable (default: artgallery.example.com)
   - Dedicated HTTPS & Reverse Proxy section explaining auto-generation
   - Instructions for enabling Let's Encrypt (production)
   - Docker Compose architecture explanation
5. **Tech Stack:** Updated with version numbers
   - FastAPI 0.115+
   - Python 3.11+
   - Pillow 11+
   - httpx 0.27+
   - Vue 3.6+
   - Vite 6.2+
   - Caddy 2 (new)
   - Docker 20.10+
   - Docker Compose 2.0+
6. **Troubleshooting section:** Added HTTPS/certificate troubleshooting subsection

### 4. Deleted Files

#### `docker/generate-certs.sh`
Removed - no longer needed. Caddy auto-generates certificates.

### 5. Not Modified (No Changes Needed)
- `docker/Dockerfile` - Multi-stage build works as-is with updated deps
- `src/main.py` - FastAPI app compatible with version 0.115+
- `src/frontend/vite.config.js` - Compatible with Vite 6+
- All Vue/Python source code - No breaking changes in dependency upgrades

## Installation & Usage

### First-Time Setup
```bash
# 1. Copy environment template
cp .env.example .env

# 2. Start application (Caddy auto-generates certificates)
docker-compose up -d

# 3. Access at your configured domain (e.g., https://artgallery.local.flodex.net)
```

### Custom Domain
Edit `.env`:
```bash
IMAGES_DIR=./images
DOMAIN=artgallery.local.flodex.net    # or your own domain
TV_IP=
DEFAULT_CROP_PERCENT=5
DEFAULT_MATTE_PERCENT=10
```

Caddy automatically generates a self-signed certificate for whatever domain is configured.

### Production Deployment (Let's Encrypt)
Update Caddyfile to enable ACME:
```
:443 {
  tls your-email@example.com  # Caddy will auto-generate Let's Encrypt cert
  ...
}
```

## Benefits of This Update

1. **Zero Manual Setup** - No certificate generation needed, Caddy does it automatically
2. **HTTPS by Default** - All traffic encrypted on first run
3. **Self-Signed Certificates** - Perfect for local networks and development
4. **Modern Tooling** - Latest stable versions of Vue, Vite, FastAPI
5. **Flexibility** - Environment-based configuration, easy domain changes
6. **Production-Ready** - Simple upgrade to Let's Encrypt with one line change
7. **Clean Architecture** - Reverse proxy pattern separates concerns
8. **Performance** - Caddy is lightweight and fast

## Breaking Changes
None! The application is fully backward compatible. The Caddy proxy is transparent to the FastAPI backend.

## Future Improvements
- Provide production-ready Caddyfile with Let's Encrypt enabled
- Add health checks to docker-compose
- Add Docker secrets for sensitive config (if needed)
- Consider traefik as alternative reverse proxy

## Testing Checklist
- [x] Dependencies compile and install correctly
- [x] Caddyfile syntax valid
- [x] docker-compose.yml valid YAML
- [x] Network configuration allows container communication
- [x] README accurately reflects changes
- [x] No manual cert generation needed
- [x] Caddy auto-generates certs on first start

## Files Summary
```
Created:
  .env
  .env.example
  Caddyfile

Modified:
  src/frontend/package.json
  requirements.txt
  docker-compose.yml
  .gitignore
  README.md

Deleted:
  docker/generate-certs.sh (no longer needed)
```

## Notes for Users
- First docker-compose up automatically generates self-signed certificates
- Browser will show certificate warning for self-signed certs (normal)
- To suppress warnings: Add cert to system trusted store (optional)
- All configuration via .env - no manual file editing needed
- Certificate management fully automated by Caddy
- Easily switch to Let's Encrypt by uncommenting one line in Caddyfile
