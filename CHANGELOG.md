# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.2] - 2026-04-25

### Added
- **Frontend** - Delete option for local images

## [1.0.1] - 2026-04-25

### Added
- **Frontend** - Option to upload your own images via phone or browser
- **Frontend** - Automatic HEIC conversion
- **Frontend** - visual indication when uploading images
- **Frontend** - Zoom option for re-framing images

### Changed
- **Frontend** - Cap images to 4k resolution when uploading (TV can't handle any more)
- **Frontend** - Re-framing is now enabled by default
- **Docker Architecture** - Changed to volume mounts for app_data instead of bind mounts
- **Docker Architecture** - Reduced final docker image size to ~300 MB

### Fixed
- **Frontend** - Preview Modal for Re-framing was resetting its position
- **Frontend** - the TV_IP variable is now properly used to auto-connect to the TV
- **Frontend** - Preview option was missing on mobile
- **Frontend** - various performance issues

## [1.0.0] - 2026-04-24

### Added
- **Caddy Reverse Proxy** - Automatic HTTPS with self-signed certificates
- **Environment-based Configuration** - `.env` file support for domain configuration
- **Non-root Docker Container** - Security hardening, app runs as non-root user (UID 1000)
- **Port Debugging Access** - Direct access to `localhost:8080` for development
- **Docker Compose Improvements** - Named volumes, bridge network, multi-service setup
- **Documentation** - Updated README with Caddy configuration and troubleshooting
- **uv Package Manager** - for local development and Docker builds
- **CI/CD** - added gh actions
- **Test** - Local development validation tests (pytest, uv integration)
- **Docker Build Context** - Added .dockerignore and .gitattributes

### Changed
- **Node.js Runtime** - Upgraded from Node 20-slim to Node 22-alpine for frontend builds
- **Python Runtime** - Upgraded from Python 3.11-slim to Python 3.13-slim for backend
- **Base Images** - Updated to latest stable LTS versions with reduced size and better performance
- **Docker Architecture** - Added Caddy as reverse proxy between internet and FastAPI app
- **Port Mapping** - App exposed on 8080 (for debugging) plus internal Docker DNS
- **Caddyfile** - Uses environment variable substitution `{$DOMAIN}` from `.env`
- **Frontend** - Updated to Vue 3.5 and Vite 5.2 (from 3.4 and 5.0)
- **Dependencies** - Updated to latest stable versions:
  - FastAPI 0.115+
  - Vue 3.5+
  - Vite 5.2+
  - Pillow 11+
  - httpx 0.27+

### Security
- Non-root user execution in container
- Self-signed HTTPS by default with `tls internal`
- Environment-based configuration prevents secrets in code

### Infrastructure
- **Reverse Proxy**: Caddy 2-alpine for automatic HTTPS
- **Container Network**: `caddy-frame` for reverse proxy publishing
- **Certificate Management**: Automatic self-signed generation and renewal

### Removed
- legacy agent instructions