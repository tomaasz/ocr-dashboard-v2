# Ruff Linter - Instalacja i Użycie

## ✅ Konfiguracja już gotowa!

Ruff został skonfigurowany dla projektu OCR Dashboard V2.

## 📦 Instalacja rozszerzenia

1. Otwórz Extensions (`Ctrl+Shift+X`)
2. Wyszukaj: **`Ruff`**
3. Zainstaluj rozszerzenie **`charliermarsh.ruff`**

## ⚙️ Konfiguracja

### `.vscode/settings.json`

```json
{
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": "explicit",
      "source.organizeImports": "explicit"
    },
    "editor.defaultFormatter": "charliermarsh.ruff"
  },
  "ruff.enable": true,
  "ruff.format.args": ["--line-length=100"],
  "ruff.organizeImports": true,
  "ruff.fixAll": true
}
```

**Co to robi**:

- ✅ Auto-formatowanie przy zapisie
- ✅ Automatyczne naprawianie błędów
- ✅ Organizowanie importów
- ✅ Linia max 100 znaków

### `pyproject.toml`

Pełna konfiguracja Ruff dla FastAPI:

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # pyflakes
    "I",      # isort
    "N",      # pep8-naming
    "UP",     # pyupgrade
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "PT",     # flake8-pytest-style
    "SIM",    # flake8-simplify
    "ARG",    # flake8-unused-arguments
    "PL",     # pylint
    "RUF",    # ruff-specific rules
]

ignore = [
    "E501",    # line too long (handled by formatter)
    "B008",    # FastAPI Depends
    "PLR0913", # too many arguments
]
```

## 🚀 Użycie

### Automatyczne

Po zainstalowaniu rozszerzenia, Ruff będzie:

- ✅ Sprawdzać kod w czasie rzeczywistym
- ✅ Pokazywać błędy inline (dzięki Error Lens)
- ✅ Formatować kod przy zapisie (`Ctrl+S`)
- ✅ Organizować importy automatycznie

### Manualne

**Formatowanie pliku**:

```
Ctrl+Shift+P → Format Document
```

**Naprawianie błędów**:

```
Ctrl+Shift+P → Ruff: Fix all auto-fixable problems
```

**Organizowanie importów**:

```
Ctrl+Shift+P → Organize Imports
```

## 📊 Co Ruff sprawdza?

### 1. **Code Quality**

- Nieużywane zmienne i importy
- Zbyt skomplikowane funkcje
- Code smells

### 2. **Style (PEP 8)**

- Naming conventions
- Indentation
- Line length
- Whitespace

### 3. **Bugs**

- Potencjalne błędy
- Type errors
- Logic errors

### 4. **Best Practices**

- FastAPI patterns
- Async/await usage
- Exception handling

## 🔧 Komendy CLI

Możesz też używać Ruff z linii komend:

```bash
# Sprawdź kod
ruff check .

# Napraw automatycznie
ruff check --fix .

# Formatuj kod
ruff format .

# Sprawdź konkretny plik
ruff check app/main.py
```

## 📈 Statystyki

Ruff jest **10-100x szybszy** niż:

- Flake8
- Pylint
- Black + isort + pyupgrade

## 🎯 Dla projektu OCR Dashboard

Ruff został skonfigurowany specjalnie dla:

- ✅ FastAPI (ignore B008 dla Depends)
- ✅ Async/await patterns
- ✅ Pytest
- ✅ Type hints
- ✅ 100 znaków na linię

## 🐛 Troubleshooting

### Ruff nie działa?

1. Sprawdź czy rozszerzenie jest zainstalowane
2. Zrestartuj Antigravity IDE
3. Sprawdź Output → Ruff

### Zbyt wiele błędów?

Możesz dostosować reguły w `pyproject.toml`:

```toml
[tool.ruff.lint]
ignore = [
    "E501",    # line too long
    # Dodaj inne reguły do ignorowania
]
```

## 📚 Więcej informacji

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Ruff Rules](https://docs.astral.sh/ruff/rules/)
- [VS Code Extension](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff)
