# Reguły Antigravity dla OCR Dashboard V2

## Standardy Kodowania

### Python Code Style

- **PEP 8**: Przestrzegaj standardu PEP 8
- **Type hints**: Używaj type hints dla wszystkich funkcji
- **Docstrings**: Dokumentuj funkcje i klasy używając Google style docstrings
- **Line length**: Maksymalnie 100 znaków na linię
- **Imports**: Grupuj importy (stdlib, third-party, local)

### Przykład:

```python
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from app.models.worker import Worker
from app.services.worker_service import WorkerService


async def start_workers(
    profile_name: str,
    worker_count: int = 2
) -> List[Worker]:
    """Start workers for the specified profile.
    
    Args:
        profile_name: Name of the Chrome profile
        worker_count: Number of workers to start
        
    Returns:
        List of started Worker instances
        
    Raises:
        HTTPException: If profile not found or workers fail to start
    """
    # Implementation
    pass
```

### Naming Conventions

- **Files**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions**: `snake_case()`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private methods**: `_leading_underscore()`

## Struktura Projektu

### Organizacja Kodu

```
app/
├── main.py              # FastAPI app initialization
├── config.py            # Configuration
├── routes/              # API endpoints (thin layer)
├── services/            # Business logic (thick layer)
├── models/              # Pydantic models
└── utils/               # Helper functions
```

### Zasady

1. **Routes** - tylko routing i walidacja, deleguj do services
2. **Services** - cała logika biznesowa
3. **Models** - Pydantic models dla walidacji
4. **Utils** - funkcje pomocnicze, reusable code

## API Design

### RESTful Conventions

- `GET /api/v2/resources` - Lista zasobów
- `GET /api/v2/resources/{id}` - Pojedynczy zasób
- `POST /api/v2/resources` - Tworzenie zasobu
- `PUT /api/v2/resources/{id}` - Aktualizacja zasobu (pełna)
- `PATCH /api/v2/resources/{id}` - Aktualizacja zasobu (częściowa)
- `DELETE /api/v2/resources/{id}` - Usunięcie zasobu

### Response Format

Zawsze zwracaj spójny format:

```python
# Success
{
    "success": true,
    "data": {...}
}

# Error
{
    "error": true,
    "message": "Error description",
    "code": "ERROR_CODE"
}
```

## Database

### Queries

- Używaj **async** queries z asyncpg
- Zawsze używaj **parameterized queries** (nigdy string interpolation)
- Implementuj **connection pooling**
- Dodawaj **indexes** dla często queryowanych kolumn

### Przykład:

```python
async def get_worker_by_id(worker_id: int) -> Optional[Worker]:
    """Get worker by ID using parameterized query."""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM workers WHERE id = $1",
            worker_id
        )
        return Worker(**row) if row else None
```

## Error Handling

### Zasady

1. **Catch specific exceptions** - nie używaj golego `except:`
2. **Log errors** - zawsze loguj błędy z kontekstem
3. **User-friendly messages** - zwracaj zrozumiałe komunikaty
4. **HTTP status codes** - używaj odpowiednich kodów HTTP

### Przykład:

```python
try:
    worker = await start_worker(profile_name)
except ProfileNotFoundException as e:
    logger.error(f"Profile not found: {profile_name}", exc_info=True)
    raise HTTPException(
        status_code=404,
        detail=f"Profile '{profile_name}' not found"
    )
except Exception as e:
    logger.error(f"Failed to start worker: {e}", exc_info=True)
    raise HTTPException(
        status_code=500,
        detail="Internal server error"
    )
```

## Logging

### Format

```python
import logging

logger = logging.getLogger(__name__)

# Levels
logger.debug("Debug info")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message", exc_info=True)
logger.critical("Critical error")
```

### Zasady

- **Structured logging** - dodawaj kontekst (user_id, request_id, etc.)
- **Log levels** - używaj odpowiednich poziomów
- **Sensitive data** - nigdy nie loguj haseł, tokenów, etc.

## Testing

### Struktura Testów

```
tests/
├── unit/               # Unit tests
├── integration/        # Integration tests
└── e2e/               # End-to-end tests
```

### Zasady

- **Test coverage** - minimum 80% coverage
- **Naming** - `test_function_name_scenario_expected_result()`
- **Fixtures** - używaj pytest fixtures
- **Mocking** - mockuj external dependencies

## Security

### Zasady Bezpieczeństwa

1. **Input validation** - waliduj wszystkie dane wejściowe
2. **SQL injection** - używaj parameterized queries
3. **XSS protection** - sanityzuj output
4. **CORS** - konfiguruj odpowiednio CORS
5. **Secrets** - nigdy nie commituj secrets do repo

### Environment Variables

```python
# .env (NIGDY nie commituj tego pliku!)
OCR_PG_DSN=postgresql://user:pass@localhost/db
OCR_SECRET_KEY=your-secret-key

# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ocr_pg_dsn: str
    ocr_secret_key: str
    
    class Config:
        env_file = ".env"
```

## Git Workflow

### Commit Messages

Format: `type(scope): description`

Types:
- `feat`: Nowa funkcjonalność
- `fix`: Naprawa błędu
- `docs`: Dokumentacja
- `style`: Formatowanie
- `refactor`: Refaktoryzacja
- `test`: Testy
- `chore`: Maintenance

Przykład:
```
feat(workers): add support for remote workers
fix(profiles): resolve profile lock issue
docs(api): update API reference
```

### Branches

- `main` - production-ready code
- `develop` - development branch
- `feature/feature-name` - feature branches
- `fix/bug-name` - bugfix branches

## Performance

### Optymalizacja

1. **Async/await** - używaj async dla I/O operations
2. **Connection pooling** - dla database connections
3. **Caching** - cache często używanych danych
4. **Pagination** - dla dużych list
5. **Lazy loading** - ładuj dane on-demand

## Documentation

### Dokumentuj

- **API endpoints** - OpenAPI/Swagger docs
- **Functions** - docstrings
- **Complex logic** - inline comments
- **Architecture** - high-level docs w `.context/`
- **Workflows** - w `.agent/workflows/`

## OCR-Specific Rules

### Workers Management

- **Graceful shutdown** - zawsze zamykaj workers gracefully
- **Resource cleanup** - zwalniaj zasoby (Chrome processes, etc.)
- **Heartbeat** - implementuj heartbeat mechanism
- **Error recovery** - automatyczne restartowanie failed workers

### Chrome Profiles

- **Profile locking** - sprawdzaj lock files przed użyciem profilu
- **Proxy configuration** - waliduj proxy settings
- **User agent rotation** - rotuj user agents dla różnych profili
- **Profile synchronization** - synchronizuj profile między serwerami
