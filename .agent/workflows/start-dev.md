---
description: Uruchomienie środowiska deweloperskiego OCR Dashboard
---

# Uruchomienie środowiska deweloperskiego

// turbo-all

1. Przejdź do katalogu projektu
```bash
cd /home/tomaasz/ocr-dashboard-v2
```

2. Aktywuj wirtualne środowisko
```bash
source venv/bin/activate
```

3. Uruchom serwer deweloperski
```bash
./scripts/start_web.sh
```

4. Otwórz dashboard w przeglądarce
```
http://localhost:9090/v2
```

## Weryfikacja

- Dashboard powinien być dostępny pod adresem http://localhost:9090/v2
- Sprawdź logi w terminalu pod kątem błędów
- Sprawdź połączenie z bazą danych PostgreSQL
