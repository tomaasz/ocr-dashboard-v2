# Configuration Directory

## Auto-Login Credentials

To enable automatic login when Google sessions expire, create `credentials.json`:

```bash
cp credentials.json.example credentials.json
```

Then edit `credentials.json` with your actual credentials:

```json
{
  "profiles": {
    "default": {
      "email": "your-email@gmail.com",
      "password": "your-password",
      "totp_secret": "YOUR_2FA_SECRET_KEY"
    },
    "profile-name": {
      "email": "profile-email@gmail.com",
      "password": "profile-password",
      "totp_secret": "PROFILE_2FA_SECRET"
    }
  }
}
```

### Required Fields

- **email**: Google account email
- **password**: Account password
- **totp_secret**: 2FA secret key (from Google Authenticator setup)

### Getting TOTP Secret

1. Go to Google Account → Security → 2-Step Verification
2. Click on "Authenticator app" → "Set up authenticator"
3. Instead of scanning QR code, click "Can't scan it?"
4. Copy the secret key shown (this is your `totp_secret`)

### Disabling Auto-Login

To disable auto-login entirely (requires manual login via headed mode):

```bash
export OCR_AUTO_LOGIN=0
```

Or add to `.env`:
```
OCR_AUTO_LOGIN=0
```

## Security

**IMPORTANT**: Never commit `credentials.json` to version control!

The file is already in `.gitignore` for your protection.
