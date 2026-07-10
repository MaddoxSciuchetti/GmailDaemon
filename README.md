# Gmail Recommendation Daemon

Small read-only daemon that watches a Gmail inbox and prints recommended next steps for newly observed emails.

## What it does

- Uses `CLIENT_ID` and `CLIENT_SECRET` from `.env`.
- Requests only Gmail read-only access.
- Stores the local OAuth token in `token.json`.
- Tracks processed Gmail message IDs in `.gmail_daemon_state.json`.
- Polls Gmail on an interval and prints simple next-step recommendations.
- Does not request or use any send-email permission.

## Setup

1. Install dependencies:

   ```bash
   python3 -m venv .venv
   . .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Make sure your Google Cloud OAuth client is configured as a Desktop app, or has `http://localhost:8080/` added as an authorized redirect URI.

3. Run the daemon:

   ```bash
   python -m gmail_daemon
   ```

The first run opens a Google OAuth flow in your browser. After approval, future runs use `token.json`.

## Configuration

Optional `.env` values:

```env
POLL_INTERVAL_SECONDS=60
GMAIL_QUERY=in:inbox newer_than:7d
STATE_FILE=.gmail_daemon_state.json
TOKEN_FILE=token.json
```

## Notes

`CLIENT_ID` and `CLIENT_SECRET` are not enough by themselves to read email. Gmail requires the account owner to complete OAuth once, which creates the local `token.json` file.
