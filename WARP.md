# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

SpotifyRandomAlbum is a Django-based application that queues random albums to your Spotify queue. It supports two modes:
- **Web mode**: A Django web interface with HTMX for dynamic interactions
- **Terminal mode**: A CLI interface for terminal-based interaction

The application can queue random albums from either your followed artists or from a specified playlist.

## Architecture

### Core Components

- **`spotify_logic/`**: Core Spotify API integration logic
  - `client.py`: Handles Spotify OAuth authentication and session management
  - `album.py`: Album discovery, querying, and queueing functionality  
  - `artist.py`: Artist-related operations for followed artists
  - `playlist.py`: Playlist-based album discovery
- **`web/`**: Django web application frontend
  - Uses `django-htmx` for dynamic album rotations without page reloads
  - `views.py` contains the main view logic with Album and Playlist classes
- **`terminal/`**: CLI interface
  - `app.py`: Interactive terminal application with action-based menu system
- **`SpotifyRandomAlbum/`**: Django project configuration

### Key Design Patterns

- **Dual Frontend Architecture**: The same core Spotify logic (`spotify_logic/`) is shared between web and terminal interfaces
- **OAuth Session Management**: Uses `DjangoSessionCacheHandler` for web sessions and standard OAuth flow for terminal
- **Weighted Album Selection**: Albums in your saved library get higher selection weight (3x) when choosing random albums
- **Error Handling**: Custom `SpotifyException` parsing via `exception_parser.py`

## Development Commands

### Environment Setup
```bash
# Copy environment template and configure Spotify API credentials
cp .env.template .env
# Edit .env with your Spotify app credentials
```

### Running the Application

**Web Mode:**
```bash
docker compose up web
```
Access at http://localhost:8000

**Terminal Mode:**
```bash
docker compose up terminal
```

### Development Workflow

**Add new Python dependencies:**
```bash
./add-dependency.sh PACKAGE_NAME [VERSION]
# Example: ./add-dependency.sh requests "~=2.28.0"
```

**Rebuild after dependency changes:**
```bash
docker compose build
docker compose down && docker compose up <mode>
```

### Django Management

**Run migrations:**
```bash
# Inside web container
python manage.py migrate
```

**Collect static files:**
```bash
# Inside web container  
python manage.py collectstatic --no-input
```

**Access Django admin:**
Navigate to http://localhost:8000/admin/ when running web mode

## Configuration

### Required Environment Variables
- `SPOTIPY_CLIENT_ID`: Spotify app client ID
- `SPOTIPY_CLIENT_SECRET`: Spotify app client secret  
- `SPOTIPY_REDIRECT_URI`: OAuth redirect URI (must match Spotify app settings)

### Optional Environment Variables
- `DJANGO_SECRET_KEY`: Django secret key (uses default if not set)
- `DJANGO_DEBUG`: Enable/disable debug mode (default: True)
- `DJANGO_ALLOWED_HOSTS`: Comma-separated allowed hosts

## Spotify API Integration

### OAuth Scopes Required
- `user-library-read`: Access saved albums
- `user-read-playback-state`: Read current playback state
- `user-modify-playback-state`: Add tracks to queue
- `user-follow-read`: Read followed artists

### Rate Limiting
- 1-second delay between track queuing to ensure correct order
- Automatic retry on device availability issues

## Container Architecture

- **Base Image**: python:3.11-slim
- **Multi-stage build**: Separate stages for dependencies and runtime
- **Non-root execution**: Runs as `appuser` for security
- **Volume mounting**: Code is mounted for development
- **Profile-based services**: Separate Docker Compose profiles for web/terminal modes

## Key Files to Understand

- `spotify_logic/client.py`: OAuth flow and token management
- `web/views.py`: Main web application logic and HTMX responses
- `terminal/app.py`: CLI interaction logic
- `compose.yml`: Docker service definitions and environment configuration
- `exception_parser.py`: Spotify API error handling
