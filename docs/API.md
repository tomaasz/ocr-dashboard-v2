# API Reference

## Dashboard Views

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main dashboard (V2) |
| `/dashboard2` | GET | Dashboard 2 view |
| `/v2` | GET | Dashboard V2 view |

## Profiles API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/profiles` | GET | List all profiles |
| `/api/profiles/active-dir?profile=X` | GET | Get active Chrome profile dir |
| `/api/profiles/create?name=X` | POST | Create new profile |
| `/api/profiles/{name}` | DELETE | Delete profile |
| `/api/profiles/{name}/reset` | POST | Clear profile cache |

## Settings API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/favorites` | GET | Get favorite directories |
| `/api/favorites` | POST | Save favorites |
| `/api/browse?path=/` | GET | Browse filesystem |
| `/api/auto-restart` | GET/POST | Auto-restart setting |
| `/api/x11-display` | GET/POST | X11 display setting |
| `/api/default-source-path` | GET | Default source path |

## Health

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check with uptime |
