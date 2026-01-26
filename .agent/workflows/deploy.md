---
description: Wdrożenie aplikacji OCR Dashboard na serwer produkcyjny
---

# Wdrożenie aplikacji

1. Sprawdź status aplikacji
```bash
systemctl status ocr-dashboard
```

2. Zatrzymaj aplikację (jeśli działa)
```bash
sudo systemctl stop ocr-dashboard
```

3. Zaktualizuj kod z repozytorium
```bash
cd /home/tomaasz/ocr-dashboard-v2
git pull origin main
```

4. Zaktualizuj zależności
```bash
source venv/bin/activate
pip install -r requirements.txt
```

5. Uruchom aplikację
```bash
sudo systemctl start ocr-dashboard
```

6. Sprawdź status
```bash
sudo systemctl status ocr-dashboard
```

7. Sprawdź logi
```bash
sudo journalctl -u ocr-dashboard -f
```

## Weryfikacja

- Aplikacja powinna być dostępna pod skonfigurowanym adresem
- Sprawdź logi pod kątem błędów
- Przetestuj kluczowe funkcjonalności dashboardu
