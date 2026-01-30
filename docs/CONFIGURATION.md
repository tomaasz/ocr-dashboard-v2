# Configuration

## Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `OCR_PG_DSN` | ✅ | PostgreSQL connection string | — |
| `OCR_DASHBOARD_PORT` | | Dashboard server port | `9090` |
| `OCR_DEFAULT_WORKERS` | | Workers per profile | `2` |
| `OCR_DEFAULT_SCANS_PER_WORKER` | | Scans per worker | `2` |

## Remote Hosts (UI-backed)

Remote hosts are configured from the UI (`/#settings`) and saved to:

```
~/.cache/ocr-dashboard-v2/remote_hosts.json
```

Environment variables still work and are used as fallback defaults.

### Remote Worker (SSH / WSL / Ubuntu)

| Variable | Description |
|----------|-------------|
| `OCR_REMOTE_RUN_ENABLED` | Enable remote worker execution |
| `OCR_REMOTE_HOST` | Remote worker hostname |
| `OCR_REMOTE_USER` | SSH username (set explicitly; avoid relying on `$USER`) |
| `OCR_REMOTE_REPO_DIR` | Remote repo path |
| `OCR_REMOTE_SOURCE_DIR` | Remote source folder (documents) |
| `OCR_REMOTE_SSH_OPTS` | SSH options |

### Remote Browser (Chrome)

| Variable | Description |
|----------|-------------|
| `OCR_REMOTE_BROWSER_ENABLED` | Enable remote browser |
| `OCR_REMOTE_BROWSER_HOST` | Remote browser host |
| `OCR_REMOTE_BROWSER_USER` | SSH username (set explicitly; avoid relying on `$USER`) |
| `OCR_REMOTE_BROWSER_PROFILE_ROOT` | Chrome profiles root (set explicitly) |
| `OCR_REMOTE_BROWSER_PYTHON` | Python path on remote |
| `OCR_REMOTE_BROWSER_CHROME_BIN` | Chrome/Chromium binary path |
| `OCR_REMOTE_BROWSER_RUNNER` | Runner command (e.g. `wsl`/`wsl.exe`) |
| `OCR_REMOTE_BROWSER_WSL_DISTRO` | WSL distro name |
| `OCR_REMOTE_BROWSER_SSH_OPTS` | SSH options |
| `OCR_REMOTE_BROWSER_PORT_BASE` | Base port for remote browser |
| `OCR_REMOTE_BROWSER_PORT_SPAN` | Port span for multiple browsers |
| `OCR_REMOTE_BROWSER_LOCAL_PORT_BASE` | Local port base for tunnels |
| `OCR_REMOTE_BROWSER_TUNNEL` | Enable SSH tunnel |

### Remote Desktop (Windows / WSL)

| Variable | Description |
|----------|-------------|
| `OCR_REMOTE_DESKTOP_HOST` | Desktop host |
| `OCR_REMOTE_DESKTOP_USER` | SSH username |
| `OCR_REMOTE_DESKTOP_REPO_DIR` | Desktop repo path |
| `OCR_REMOTE_DESKTOP_SOURCE_DIR` | Desktop source folder |
| `OCR_REMOTE_DESKTOP_SSH_OPTS` | SSH options |
| `OCR_REMOTE_DESKTOP_WSL_DISTRO` | WSL distro name |
| `OCR_WSL_SHARE_PROFILE` | Share Chrome profile between WSL/Desktop |

### Presets (Optional)

| Variable | Description |
|----------|-------------|
| `OCR_REMOTE_HOSTS_LIST` | JSON list of preset entries for UI |

## Notes and Recommendations

- `OCR_DASHBOARD_PORT` defaults to `9090`. The `scripts/start_web.sh` wrapper uses
  the same default, so the UI and reverse proxy should point to 9090.
- `OCR_REMOTE_BROWSER_TUNNEL` defaults to `0` (disabled). Enable only if you need
  SSH tunneling for remote Chrome.
- Always set explicit SSH usernames (do not rely on `$USER`), especially when
  running under systemd.

## Example Remote Browser (Windows host)

```bash
OCR_REMOTE_BROWSER_ENABLED=1
OCR_REMOTE_BROWSER_HOST=1dtw2.tail7319.ts.net
OCR_REMOTE_BROWSER_USER=tomaa
OCR_REMOTE_BROWSER_PROFILE_ROOT='C:\\Users\\tomaa\\AppData\\Local\\Google\\Chrome\\User Data'
OCR_REMOTE_BROWSER_PYTHON='C:\\Python311\\python.exe'
OCR_REMOTE_BROWSER_CHROME_BIN='C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
OCR_REMOTE_BROWSER_RUNNER='wsl.exe'
OCR_REMOTE_BROWSER_WSL_DISTRO='Ubuntu-24.04'
OCR_REMOTE_BROWSER_TUNNEL=0
```

## Example `.env`

```bash
OCR_PG_DSN=postgresql://user:pass@localhost:5432/ocr_db
OCR_DASHBOARD_PORT=9090
OCR_DEFAULT_WORKERS=2
```
