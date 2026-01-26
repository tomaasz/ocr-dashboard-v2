# OCR Dashboard V2

Samodzielny dashboard do zarządzania OCR Farm.

## Quick Start

```bash
# Setup
cd /home/tomaasz/ocr-dashboard-v2
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run
./scripts/start_web.sh
```

Open: http://localhost:9090/v2

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `OCR_PG_DSN` | PostgreSQL connection string | - |
| `OCR_REMOTE_HOST` | Remote worker host | - |
| `OCR_DEFAULT_WORKERS` | Default workers per profile | 2 |

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for full list.

## Project Structure

app/
├── main.py          # FastAPI entry point
├── config.py        # Configuration
├── routes/          # API endpoints
├── services/        # Business logic
├── models/          # Pydantic models
└── utils/           # Helpers
```

## Antigravity Workspace

Ten projekt wykorzystuje strukturę workspace zgodną z [antigravity-workspace-template](https://github.com/study8677/antigravity-workspace-template).

### Struktura Workspace

```
.agent/
├── workflows/       # Zdefiniowane workflow dla typowych zadań
│   ├── start-dev.md
│   ├── deploy.md
│   └── test.md
└── skills/          # Modułowe możliwości agenta
    └── ocr-management/

.context/            # Baza wiedzy auto-wstrzykiwana do agenta
├── project-overview.md
├── architecture.md
└── api-reference.md

.antigravity/        # Reguły dla Antigravity IDE
└── rules.md

artifacts/           # Wyjścia i dowody pracy agenta
```

### Workflows

Użyj workflows dla typowych zadań:

- `/start-dev` - Uruchomienie środowiska deweloperskiego
- `/deploy` - Wdrożenie aplikacji
- `/test` - Uruchomienie testów

### Skills

- **OCR Management** - Zarządzanie OCR workers i profilami Chrome

Więcej informacji w [.agent/skills/ocr-management/SKILL.md](.agent/skills/ocr-management/SKILL.md)
