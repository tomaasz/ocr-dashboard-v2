# GitHub MCP - Przewodnik użycia

## ✅ GitHub MCP jest już zainstalowany!

GitHub MCP jest dostępny w Antigravity IDE i gotowy do użycia.

## 🔑 Wymagania

### 1. Autoryzacja GitHub

GitHub MCP wymaga tokena GitHub do działania. Sprawdź czy masz skonfigurowany token:

```bash
# Sprawdź czy token jest ustawiony
echo $GITHUB_TOKEN
```

Jeśli nie masz tokena, utwórz go:

1. Przejdź do: https://github.com/settings/tokens
2. Kliknij **Generate new token** → **Classic**
3. Nadaj nazwę: `Antigravity MCP`
4. Wybierz uprawnienia:
   - ✅ `repo` (pełny dostęp do repozytoriów)
   - ✅ `workflow` (dostęp do GitHub Actions)
   - ✅ `read:org` (odczyt organizacji)
5. Kliknij **Generate token**
6. Skopiuj token (tylko raz będzie widoczny!)

### 2. Konfiguracja tokena

Dodaj token do środowiska:

```bash
# Dodaj do ~/.bashrc lub ~/.zshrc
export GITHUB_TOKEN="ghp_twoj_token_tutaj"

# Przeładuj konfigurację
source ~/.bashrc
```

## 🚀 Dostępne funkcje GitHub MCP

### 1. **Zarządzanie Pull Requests**

#### Tworzenie PR

```
"Stwórz pull request z moimi zmianami"
"Utwórz PR z branch feature/ruff-config do main"
```

#### Aktualizacja PR

```
"Zaktualizuj PR #123 - zmień tytuł na 'Add Ruff linter'"
"Dodaj reviewera do PR #123"
```

#### Mergowanie PR

```
"Zmerguj PR #123"
"Merge pull request #123 używając squash"
```

#### Czytanie PR

```
"Pokaż szczegóły PR #123"
"Jakie pliki zostały zmienione w PR #123?"
"Pokaż komentarze w PR #123"
```

### 2. **Zarządzanie Issues**

#### Tworzenie Issue

```
"Stwórz issue: Dodać testy dla OCR workers"
"Utwórz bug report: Dashboard nie ładuje się na Chrome"
```

#### Aktualizacja Issue

```
"Zaktualizuj issue #45 - dodaj label 'bug'"
"Zamknij issue #45"
```

#### Czytanie Issues

```
"Pokaż otwarte issues"
"Jakie issues są przypisane do mnie?"
"Pokaż issue #45"
```

### 3. **Komentarze**

#### Dodawanie komentarzy do PR

```
"Dodaj komentarz do PR #123: LGTM, świetna robota!"
"Skomentuj w PR #123 na linii 45 w pliku app/main.py"
```

#### Dodawanie komentarzy do Issues

```
"Dodaj komentarz do issue #45: Pracuję nad tym"
```

### 4. **Code Review**

#### Tworzenie review

```
"Rozpocznij review PR #123"
"Zatwierdź PR #123"
"Poproś o zmiany w PR #123"
```

#### Dodawanie komentarzy review

```
"Dodaj komentarz review do PR #123 w pliku app/main.py linia 45"
```

### 5. **Branches**

#### Tworzenie branch

```
"Stwórz branch feature/github-mcp"
"Utwórz branch fix/security-issues z main"
```

#### Listowanie branches

```
"Pokaż wszystkie branches"
"Jakie branches są w repo?"
```

### 6. **Pliki i Commits**

#### Tworzenie/Aktualizacja plików

```
"Stwórz plik README.md w repo"
"Zaktualizuj plik .gitignore"
```

#### Usuwanie plików

```
"Usuń plik old-config.json"
```

#### Commits

```
"Pokaż ostatnie commity"
"Pokaż commit abc123"
```

### 7. **Repository**

#### Informacje o repo

```
"Pokaż informacje o repo ocr-dashboard-v2"
"Jakie są statystyki repo?"
```

#### Fork

```
"Zforkuj repo user/project"
```

## 🎯 Przykładowe workflow dla OCR Dashboard

### Workflow 1: Nowa funkcja

```
1. "Stwórz branch feature/add-monitoring"
2. [Wprowadź zmiany w kodzie]
3. "Stwórz PR z branch feature/add-monitoring do main"
4. "Dodaj reviewera @username do ostatniego PR"
5. [Po review]
6. "Zmerguj ostatni PR używając squash"
```

### Workflow 2: Bug fix

```
1. "Stwórz issue: Dashboard crashes on profile deletion"
2. "Stwórz branch fix/profile-deletion z issue #123"
3. [Napraw bug]
4. "Stwórz PR z opisem 'Fixes #123'"
5. "Zmerguj PR po zatwierdzeniu"
```

### Workflow 3: Code Review

```
1. "Pokaż otwarte PR"
2. "Pokaż szczegóły PR #123"
3. "Pokaż diff PR #123"
4. "Dodaj komentarz review: 'Świetna implementacja!'"
5. "Zatwierdź PR #123"
```

## 🔧 Integracja z Antigravity

### Automatyczne akcje

GitHub MCP może automatycznie:

- ✅ Tworzyć PR po zakończeniu pracy
- ✅ Dodawać komentarze z wynikami testów
- ✅ Aktualizować issues po zmianach
- ✅ Mergować PR po zatwierdzeniu

### Przykład: Auto-PR po zakończeniu zadania

```
"Zakończyłem implementację Ruff lintera.
Stwórz PR z opisem zmian i dodaj label 'enhancement'"
```

GitHub MCP:

1. Stworzy PR z Twoich zmian
2. Wygeneruje opis na podstawie commitów
3. Doda odpowiednie labele
4. Przypisze reviewerów (jeśli skonfigurowani)

## 📊 Najlepsze praktyki

### 1. **Opisowe PR**

```
"Stwórz PR z tytułem 'Add Ruff linter configuration'
i opisem:
- Dodano Ruff do extensions.json
- Skonfigurowano auto-formatting
- Dodano pyproject.toml z regułami"
```

### 2. **Używaj konwencji commitów**

```
"Stwórz PR z conventional commits"
```

### 3. **Linkuj issues**

```
"Stwórz PR który zamyka issue #123"
```

### 4. **Review przed merge**

```
"Poproś o review przed zmergowaniem PR #123"
```

## 🐛 Troubleshooting

### GitHub MCP nie działa?

1. **Sprawdź token**:

```bash
echo $GITHUB_TOKEN
```

2. **Sprawdź uprawnienia tokena**:
   - Przejdź do https://github.com/settings/tokens
   - Sprawdź czy token ma uprawnienia `repo`

3. **Sprawdź czy jesteś w repo**:

```bash
git remote -v
```

4. **Zrestartuj Antigravity IDE**

### Błąd "Not authenticated"

Ustaw token:

```bash
export GITHUB_TOKEN="ghp_twoj_token"
```

### Błąd "Repository not found"

Sprawdź czy masz dostęp do repo:

```bash
gh repo view owner/repo
```

## 📚 Więcej informacji

- [GitHub MCP Documentation](https://github.com/modelcontextprotocol/servers/tree/main/src/github)
- [GitHub API](https://docs.github.com/en/rest)
- [GitHub CLI](https://cli.github.com/)

## 🎓 Przykłady dla OCR Dashboard

### Przykład 1: Dodanie nowej funkcji

```
User: "Dodałem monitoring dla OCR workers. Stwórz PR."

Antigravity + GitHub MCP:
1. Analizuje zmiany w git
2. Tworzy PR z opisem
3. Dodaje label "enhancement"
4. Przypisuje do milestone "v2.1"
```

### Przykład 2: Fix security issue

```
User: "Naprawiłem Path Traversal w profiles.py.
Stwórz PR który zamyka issue #57 i #76"

Antigravity + GitHub MCP:
1. Tworzy PR z tytułem "Fix: Path Traversal in profiles.py"
2. Dodaje "Fixes #57, Fixes #76" w opisie
3. Dodaje label "security"
4. Prosi o review od security team
```

### Przykład 3: Code review

```
User: "Zrób review PR #123"

Antigravity + GitHub MCP:
1. Pobiera kod z PR
2. Analizuje zmiany
3. Sprawdza testy
4. Dodaje komentarze inline
5. Zatwierdza lub prosi o zmiany
```

## ✅ Podsumowanie

GitHub MCP jest **już zainstalowany i gotowy do użycia**!

Wystarczy:

1. ✅ Skonfigurować GITHUB_TOKEN
2. ✅ Używać naturalnego języka do zarządzania GitHub
3. ✅ Automatyzować workflow

**Przykład użycia**:

```
"Stwórz PR z moimi zmianami dotyczącymi Ruff lintera"
```

I GitHub MCP zrobi resztę! 🚀
