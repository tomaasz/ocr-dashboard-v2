---
description: Uruchomienie testów aplikacji OCR Dashboard
---

# Testowanie aplikacji

// turbo-all

1. Aktywuj wirtualne środowisko
```bash
cd /home/tomaasz/ocr-dashboard-v2
source venv/bin/activate
```

2. Uruchom testy jednostkowe (jeśli istnieją)
```bash
pytest tests/ -v
```

3. Sprawdź pokrycie kodu testami
```bash
pytest tests/ --cov=app --cov-report=html
```

4. Uruchom linter
```bash
flake8 app/
```

5. Sprawdź formatowanie kodu
```bash
black --check app/
```

## Testy manualne

1. Uruchom aplikację lokalnie
2. Przetestuj główne funkcjonalności:
   - Logowanie do dashboardu
   - Zarządzanie workers
   - Wyświetlanie statystyk
   - Zarządzanie profilami Chrome

## Weryfikacja

- Wszystkie testy powinny przejść pomyślnie
- Brak błędów lintera
- Kod zgodny z formatowaniem Black
