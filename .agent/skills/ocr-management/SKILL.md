---
name: OCR Management
description: Zarządzanie OCR workers i profilami Chrome
---

# OCR Management Skill

Ten skill umożliwia efektywne zarządzanie systemem OCR Dashboard V2.

## Możliwości

### 1. Zarządzanie Workers

- **Sprawdzanie statusu workers**: Wyświetlanie aktywnych i nieaktywnych workers
- **Uruchamianie workers**: Start workers dla wybranych profili
- **Zatrzymywanie workers**: Stop workers z graceful shutdown
- **Monitorowanie wydajności**: Śledzenie statystyk przetwarzania

### 2. Zarządzanie Profilami Chrome

- **Lista profili**: Wyświetlanie dostępnych profili Chrome
- **Konfiguracja profili**: Ustawianie proxy, user-agent, itp.
- **Synchronizacja profili**: Kopiowanie profili między serwerami
- **Weryfikacja profili**: Sprawdzanie poprawności konfiguracji

### 3. Monitorowanie Systemu

- **Dashboard metrics**: Wyświetlanie kluczowych metryk
- **Logi systemowe**: Dostęp do logów aplikacji i workers
- **Alerty**: Powiadomienia o problemach

## Kluczowe Pliki

- `app/routes/workers.py` - API endpoints dla workers
- `app/services/worker_service.py` - Logika biznesowa workers
- `app/services/profile_service.py` - Zarządzanie profilami
- `app/models/worker.py` - Modele danych workers

## Typowe Zadania

### Uruchomienie workers dla profilu

```python
# Endpoint: POST /api/v2/workers/start
{
  "profile_name": "MarinaMargarita699",
  "worker_count": 2
}
```

### Sprawdzenie statusu wszystkich workers

```python
# Endpoint: GET /api/v2/workers/status
```

### Zatrzymanie workers

```python
# Endpoint: POST /api/v2/workers/stop
{
  "profile_name": "MarinaMargarita699"
}
```

## Debugowanie

### Typowe problemy

1. **Profile lock issues**: Worker nie może uruchomić się z powodu zablokowanego profilu
   - Rozwiązanie: Sprawdź czy inny proces nie używa profilu, usuń lock file

2. **Proxy authentication errors**: Błędy uwierzytelniania proxy
   - Rozwiązanie: Sprawdź konfigurację proxy w profilu, zweryfikuj credentials

3. **Model switching issues**: Problemy z przełączaniem modeli OCR
   - Rozwiązanie: Sprawdź dostępność modeli, zweryfikuj konfigurację

## Przydatne Komendy

```bash
# Sprawdź logi workers
tail -f logs/workers.log

# Sprawdź status aplikacji
systemctl status ocr-dashboard

# Restart aplikacji
sudo systemctl restart ocr-dashboard
```
