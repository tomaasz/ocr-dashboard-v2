# Configuration

## Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `OCR_PG_DSN` | ✅ | PostgreSQL connection string | — |
| `OCR_DASHBOARD_PORT` | | Dashboard server port | `9090` |
| `OCR_DEFAULT_WORKERS` | | Workers per profile | `2` |
| `OCR_DEFAULT_SCANS_PER_WORKER` | | Scans per worker | `2` |
| `OCR_AUTO_LOGIN` | | Enable automatic login when sessions expire | `true` |

### Remote Worker (SSH)

| Variable | Description |
|----------|-------------|
| `OCR_REMOTE_HOST` | Remote worker hostname |
| `OCR_REMOTE_USER` | SSH username |
| `OCR_REMOTE_REPO_DIR` | Remote repo path |
| `OCR_REMOTE_SSH_OPTS` | SSH options |

### Remote Desktop (WSL)

| Variable | Description |
|----------|-------------|
| `OCR_REMOTE_DESKTOP_HOST` | Desktop host |
| `OCR_REMOTE_DESKTOP_USER` | SSH username |
| `OCR_REMOTE_DESKTOP_WSL_DISTRO` | WSL distro name |

## Auto-Login Configuration

Auto-login allows profiles to automatically re-authenticate when Google sessions expire (typically after a few seconds/minutes).

### Setup

1. **Create credentials file**:
   ```bash
   cp config/credentials.json.example config/credentials.json
   ```

2. **Add your credentials** for each profile:
   ```json
   {
     "profiles": {
       "default": {
         "email": "your-email@gmail.com",
         "password": "your-password",
         "totp_secret": "YOUR_2FA_SECRET_KEY"
       }
     }
   }
   ```

3. **Get TOTP secret**:
   - Go to Google Account → Security → 2-Step Verification
   - Click "Authenticator app" → "Set up authenticator"
   - Click "Can't scan it?" to reveal the secret key
   - Copy this secret as your `totp_secret`

### Disabling Auto-Login

To disable auto-login (requires manual login via headed mode):

```bash
export OCR_AUTO_LOGIN=0
```

Or add to `.env`:
```bash
OCR_AUTO_LOGIN=0
```

**⚠️ Security Note**: Never commit `config/credentials.json` to version control!

See [config/README.md](../config/README.md) for more details.

## Example `.env`

```bash
OCR_PG_DSN=postgresql://user:pass@localhost:5432/ocr_db
OCR_DASHBOARD_PORT=9090
OCR_DEFAULT_WORKERS=2
OCR_AUTO_LOGIN=1
```
