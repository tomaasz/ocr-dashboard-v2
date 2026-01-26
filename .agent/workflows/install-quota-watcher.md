# Instalacja AntigravityQuotaWatcher

## Krok 1: Instalacja rozszerzenia

### Metoda 1: Przez Marketplace (Zalecana)

1. Otwórz Antigravity IDE
2. Kliknij ikonę **Extensions** (Rozszerzenia) w lewym pasku bocznym lub naciśnij `Ctrl+Shift+X`
3. Wyszukaj: **`Antigravity Quota Watcher`**
4. Kliknij **Install** (Zainstaluj)

### Metoda 2: Przez Command Palette

1. Naciśnij `Ctrl+Shift+P` (Windows/Linux) lub `Cmd+Shift+P` (Mac)
2. Wpisz: `Extensions: Install Extensions`
3. Wyszukaj: **`Antigravity Quota Watcher`**
4. Kliknij **Install**

### Metoda 3: Bezpośredni link

Otwórz w przeglądarce:
```
https://marketplace.visualstudio.com/items?itemName=wusimpl.antigravity-quota-watcher
```

## Krok 2: Konfiguracja (Już gotowa!)

Konfiguracja została już przygotowana w pliku `.vscode/settings.json`:

```json
{
  "antigravityQuotaWatcher.language": "en",
  "antigravityQuotaWatcher.enableAutoMonitor": true,
  "antigravityQuotaWatcher.pollingInterval": 60,
  "antigravityQuotaWatcher.warningThreshold": 50,
  "antigravityQuotaWatcher.criticalThreshold": 30,
  "antigravityQuotaWatcher.statusBarStyle": "percentage",
  "antigravityQuotaWatcher.apiMethod": "GOOGLE_API",
  "antigravityQuotaWatcher.showAccountLevel": true
}
```

### Ustawienia:

- **Język**: Angielski (`en`)
- **Auto-monitoring**: Włączony
- **Interwał odświeżania**: 60 sekund
- **Próg ostrzeżenia**: 50%
- **Próg krytyczny**: 30%
- **Styl wyświetlania**: Procenty
- **Metoda API**: Google API (szybsza)
- **Pokazuj poziom konta**: Tak

## Krok 3: Logowanie

Po zainstalowaniu rozszerzenia:

1. Kliknij na status rozszerzenia w dolnym pasku (status bar)
2. Zostaniesz przekierowany do przeglądarki
3. Zaloguj się swoim kontem Google
4. Autoryzuj dostęp
5. Rozszerzenie automatycznie zacznie monitorować Twoje limity

## Krok 4: Weryfikacja

Po zalogowaniu powinieneś zobaczyć w dolnym pasku statusu:
- Procent wykorzystania limitów (np. `80%`)
- Ikony statusu (🟢 OK, 🟡 Ostrzeżenie, 🔴 Krytyczny)
- Poziom konta (Free/Pro)

## Dostępne komendy

Naciśnij `Ctrl+Shift+P` i wpisz:

- `Antigravity Quota Watcher: Refresh Quota` - Odśwież limity
- `Antigravity Quota Watcher: Open Dashboard` - Otwórz dashboard
- `Antigravity Quota Watcher: Login with Google` - Zaloguj się
- `Antigravity Quota Watcher: Logout from Google` - Wyloguj się

## Troubleshooting

Jeśli rozszerzenie nie działa:

1. Sprawdź czy jesteś zalogowany (kliknij status bar)
2. Odśwież limity: `Ctrl+Shift+P` → `Refresh Quota`
3. Sprawdź logi: `Ctrl+Shift+P` → `Developer: Show Logs`
4. Zrestartuj Antigravity IDE

## Bezpieczeństwo

⚠️ **Ważne**: Rozszerzenie używa Twojego Google access token do pobierania limitów. Token jest przechowywany **tylko lokalnie** na Twoim komputerze. Projekt jest open-source i nie wysyła żadnych danych na zewnętrzne serwery.
