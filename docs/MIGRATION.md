# Migration Notes

## What Was Migrated

| Component | Source | Target |
|-----------|--------|--------|
| Static files | `web_interface/static/` | `static/` |
| Templates | `web_interface/templates/` | `templates/` |
| Config extraction | `app.py` env vars | `app/config.py` |
| Security utils | `app.py` validators | `app/utils/security.py` |
| Profile service | `app.py` profile funcs | `app/services/profiles.py` |
| Process service | `app.py` process funcs | `app/services/process.py` |
| Pydantic models | `app.py` models | `app/models/requests.py` |

## What Was NOT Migrated

| Component | Reason |
|-----------|--------|
| `farm_status.py` | Stats service — add later if needed |
| Job control endpoints | Require `run.py` worker |
| Limit check endpoints | Require limit worker |
| Post-process endpoints | Optional, legacy |

## Breaking Changes

1. **No stats API** — `/api/stats` and `/api/v2/stats` not available until `farm_status.py` is ported
2. **No job control** — Cannot start/stop OCR workers from dashboard
3. **Standalone** — Dashboard runs independently, does not control OCR engine
