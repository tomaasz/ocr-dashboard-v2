# Configuration

## Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `OCR_PG_DSN` | ✅ | PostgreSQL connection string | — |
| `OCR_DASHBOARD_PORT` | | Dashboard server port | `9090` |
| `OCR_DEFAULT_WORKERS` | | Workers per profile | `2` |
| `OCR_DEFAULT_SCANS_PER_WORKER` | | Scans per worker | `2` |

### Remote Worker (SSH)

| Variable | Description |
|----------|-------------|
| `OCR_REMOTE_HOST` | Remote worker hostname |
| `OCR_REMOTE_USER` | SSH username |
| `OCR_REMOTE_REPO_DIR` | Remote repo path |
| `OCR_REMOTE_SSH_OPTS` | SSH options |

### Remote Desktop (WSL)

| Variable | Description |
|----------|-------------|
| `OCR_REMOTE_DESKTOP_HOST` | Desktop host |
| `OCR_REMOTE_DESKTOP_USER` | SSH username |
| `OCR_REMOTE_DESKTOP_WSL_DISTRO` | WSL distro name |

## Example `.env`

```bash
OCR_PG_DSN=postgresql://user:pass@localhost:5432/ocr_db
OCR_DASHBOARD_PORT=9090
OCR_DEFAULT_WORKERS=2
```
