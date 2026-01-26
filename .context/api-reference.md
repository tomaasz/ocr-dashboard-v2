# API Reference - OCR Dashboard V2

## Base URL

```
http://localhost:9090/v2
```

## Authentication

Obecnie brak autentykacji. Planowane w przyszłych wersjach.

## Endpoints

### Workers Management

#### GET /api/v2/workers/status

Pobiera status wszystkich workers.

**Response**:
```json
{
  "workers": [
    {
      "id": 1,
      "profile_name": "MarinaMargarita699",
      "status": "running",
      "started_at": "2026-01-26T10:00:00Z",
      "last_heartbeat": "2026-01-26T10:05:00Z"
    }
  ],
  "total": 1,
  "active": 1
}
```

#### POST /api/v2/workers/start

Uruchamia workers dla profilu.

**Request**:
```json
{
  "profile_name": "MarinaMargarita699",
  "worker_count": 2
}
```

**Response**:
```json
{
  "success": true,
  "workers_started": 2,
  "profile": "MarinaMargarita699"
}
```

#### POST /api/v2/workers/stop

Zatrzymuje workers dla profilu.

**Request**:
```json
{
  "profile_name": "MarinaMargarita699"
}
```

**Response**:
```json
{
  "success": true,
  "workers_stopped": 2,
  "profile": "MarinaMargarita699"
}
```

---

### Profiles Management

#### GET /api/v2/profiles

Pobiera listę dostępnych profili Chrome.

**Query Parameters**:
- `type` (optional): `local` | `remote` | `all` (default: `all`)

**Response**:
```json
{
  "profiles": [
    {
      "name": "MarinaMargarita699",
      "type": "remote",
      "proxy": "proxy.example.com:8080",
      "user_agent": "Mozilla/5.0...",
      "is_active": true
    }
  ],
  "total": 1
}
```

#### GET /api/v2/profiles/{profile_name}

Pobiera szczegóły profilu.

**Response**:
```json
{
  "name": "MarinaMargarita699",
  "type": "remote",
  "proxy": "proxy.example.com:8080",
  "user_agent": "Mozilla/5.0...",
  "config": {
    "max_workers": 2,
    "timeout": 30
  }
}
```

#### POST /api/v2/profiles

Tworzy nowy profil.

**Request**:
```json
{
  "name": "NewProfile",
  "type": "local",
  "proxy": "proxy.example.com:8080",
  "user_agent": "Mozilla/5.0...",
  "config": {}
}
```

**Response**:
```json
{
  "success": true,
  "profile": "NewProfile"
}
```

---

### Tasks Management

#### GET /api/v2/tasks

Pobiera listę zadań OCR.

**Query Parameters**:
- `status` (optional): `pending` | `processing` | `completed` | `failed`
- `limit` (optional): liczba wyników (default: 50)
- `offset` (optional): offset dla paginacji (default: 0)

**Response**:
```json
{
  "tasks": [
    {
      "id": 1,
      "worker_id": 1,
      "status": "completed",
      "created_at": "2026-01-26T10:00:00Z",
      "completed_at": "2026-01-26T10:01:00Z",
      "result": {
        "text": "Extracted text...",
        "confidence": 0.95
      }
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

#### POST /api/v2/tasks

Tworzy nowe zadanie OCR.

**Request**:
```json
{
  "image_url": "https://example.com/image.jpg",
  "priority": "normal",
  "options": {
    "language": "eng",
    "model": "default"
  }
}
```

**Response**:
```json
{
  "success": true,
  "task_id": 123,
  "status": "pending"
}
```

#### GET /api/v2/tasks/{task_id}

Pobiera szczegóły zadania.

**Response**:
```json
{
  "id": 123,
  "worker_id": 1,
  "status": "processing",
  "created_at": "2026-01-26T10:00:00Z",
  "image_url": "https://example.com/image.jpg",
  "progress": 50
}
```

#### POST /api/v2/tasks/{task_id}/complete

Oznacza zadanie jako ukończone (używane przez workers).

**Request**:
```json
{
  "result": {
    "text": "Extracted text...",
    "confidence": 0.95
  }
}
```

**Response**:
```json
{
  "success": true,
  "task_id": 123
}
```

---

### Statistics

#### GET /api/v2/stats

Pobiera statystyki systemu.

**Response**:
```json
{
  "workers": {
    "total": 10,
    "active": 8,
    "idle": 2
  },
  "tasks": {
    "total": 1000,
    "pending": 50,
    "processing": 10,
    "completed": 930,
    "failed": 10
  },
  "performance": {
    "avg_processing_time": 1.5,
    "tasks_per_hour": 600
  }
}
```

## Error Responses

Wszystkie błędy zwracają standardowy format:

```json
{
  "error": true,
  "message": "Error description",
  "code": "ERROR_CODE"
}
```

### HTTP Status Codes

- `200 OK` - Sukces
- `201 Created` - Zasób utworzony
- `400 Bad Request` - Błędne dane wejściowe
- `404 Not Found` - Zasób nie znaleziony
- `500 Internal Server Error` - Błąd serwera

## Rate Limiting

Obecnie brak rate limiting. Planowane w przyszłych wersjach.

## Webhooks

Planowane w przyszłych wersjach dla powiadomień o ukończonych zadaniach.
