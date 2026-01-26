# OCR Dashboard V2 - Przegląd Projektu

## Cel Projektu

OCR Dashboard V2 to samodzielny dashboard do zarządzania OCR Farm - systemem przetwarzania obrazów za pomocą OCR (Optical Character Recognition) z wykorzystaniem zdalnych workers opartych na profilach Chrome.

## Główne Funkcjonalności

### 1. Zarządzanie Workers

- Uruchamianie i zatrzymywanie workers dla różnych profili Chrome
- Monitorowanie statusu workers w czasie rzeczywistym
- Konfiguracja liczby workers per profil
- Graceful shutdown workers

### 2. Zarządzanie Profilami Chrome

- Lista dostępnych profili Chrome (lokalne i zdalne)
- Konfiguracja profili (proxy, user-agent, etc.)
- Synchronizacja profili między serwerami
- Weryfikacja poprawności konfiguracji profili

### 3. Dashboard i Monitoring

- Wyświetlanie statystyk przetwarzania OCR
- Metryki wydajności workers
- Historia zadań OCR
- Alerty i powiadomienia

### 4. Zarządzanie Zadaniami OCR

- Kolejkowanie zadań OCR
- Przypisywanie zadań do workers
- Śledzenie postępu przetwarzania
- Zarządzanie priorytetami zadań

## Architektura

### Backend

- **Framework**: FastAPI (Python)
- **Baza danych**: PostgreSQL
- **ORM**: SQLAlchemy / asyncpg
- **API**: RESTful API z dokumentacją OpenAPI

### Frontend

- **Framework**: HTML/CSS/JavaScript (vanilla)
- **UI Components**: Custom components
- **Routing**: Client-side routing
- **State Management**: Local state

### Workers

- **Środowisko**: Chrome profiles z Selenium/Playwright
- **Deployment**: Lokalne i zdalne serwery
- **Komunikacja**: REST API + WebSockets (opcjonalnie)

## Struktura Projektu

```
ocr-dashboard-v2/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Konfiguracja aplikacji
│   ├── routes/              # API endpoints
│   │   ├── workers.py       # Workers management
│   │   ├── profiles.py      # Profiles management
│   │   └── tasks.py         # OCR tasks
│   ├── services/            # Business logic
│   │   ├── worker_service.py
│   │   ├── profile_service.py
│   │   └── task_service.py
│   ├── models/              # Pydantic models
│   └── utils/               # Helpers
├── static/                  # Frontend assets
├── templates/               # HTML templates
├── scripts/                 # Utility scripts
└── tests/                   # Tests
```

## Technologie

- **Python 3.10+**
- **FastAPI** - Web framework
- **PostgreSQL** - Baza danych
- **asyncpg** - Async PostgreSQL driver
- **Pydantic** - Data validation
- **Uvicorn** - ASGI server

## Konfiguracja

Główne zmienne środowiskowe:

- `OCR_PG_DSN` - PostgreSQL connection string
- `OCR_REMOTE_HOST` - Remote worker host
- `OCR_DEFAULT_WORKERS` - Default workers per profile

## Deployment

### Development

```bash
cd /home/tomaasz/ocr-dashboard-v2
source venv/bin/activate
./scripts/start_web.sh
```

Dashboard dostępny pod: http://localhost:9090/v2

### Production

Aplikacja deployowana jako systemd service na serwerze Ubuntu.

## Integracje

- **Remote Workers**: SSH connection do zdalnych serwerów z workers
- **Chrome Profiles**: Zarządzanie profilami Chrome na lokalnym i zdalnych serwerach
- **PostgreSQL**: Baza danych dla zadań, statystyk i konfiguracji

## Roadmap

- [ ] WebSocket support dla real-time updates
- [ ] Advanced analytics i reporting
- [ ] Multi-tenant support
- [ ] API authentication i authorization
- [ ] Automated testing suite
