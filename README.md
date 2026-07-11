# Gmail Recommendation Daemon

Small read-only daemon that watches a Gmail inbox and prints recommended next steps for newly observed emails.

## What it does

- Uses `CLIENT_ID` and `CLIENT_SECRET` from `.env`.
- Requests only Gmail read-only access.
- Stores the local OAuth token in `token.json`.
- Tracks processed Gmail message IDs in `.gmail_daemon_state.json`.
- Polls Gmail on an interval and prints simple next-step recommendations.
- Classifies emails locally with an open-source Hugging Face model when configured.
- Creates Google Tasks for emails that clearly require action.
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
EMAIL_CLASSIFIER_ENABLED=true
EMAIL_CLASSIFIER_MODEL_PATH=/Users/maddoxsciuchetti/.cache/huggingface/hub/models--FacebookAI--roberta-large-mnli/snapshots/2a8f12d27941090092df78e4ba6f0928eb5eac98
EMAIL_CLASSIFIER_THRESHOLD=0.90
GOOGLE_TASKS_ENABLED=true
GOOGLE_TASKS_LIST_ID=@default
```

## Notes

`CLIENT_ID` and `CLIENT_SECRET` are not enough by themselves to read email. Gmail requires the account owner to complete OAuth once, which creates the local `token.json` file.

The default classifier uses a locally cached Hugging Face zero-shot model. On this machine, a usable cache was found at:

```text
/Users/maddoxsciuchetti/.cache/huggingface/hub/models--FacebookAI--roberta-large-mnli/snapshots/2a8f12d27941090092df78e4ba6f0928eb5eac98
```

The daemon sets `local_files_only=True`, so email text is not sent to Hugging Face. If the model or ML dependencies are unavailable, the daemon falls back to the rule-based recommendations.

## Re-run Google OAuth

Creating Google Tasks, sending accepted replies, and creating Calendar events require additional OAuth scopes. After enabling the Google Tasks and Google Calendar APIs, run:

```bash
python -m gmail_daemon.reauth
```

This refreshes `token.json` with:

```text
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/gmail.send
https://www.googleapis.com/auth/tasks
https://www.googleapis.com/auth/calendar.events
```

## Review UI

The daemon writes actionable email proposals to `email_proposals.json`. Start the local review UI with:

```bash
cd web
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

Accepting a proposal sends the proposed reply through Gmail. Declining a proposal stores your replacement text without sending it.

If a later message in the same Gmail thread clearly agrees with your sent proposal and includes a parseable time such as `2026-07-12 15:00` or `tomorrow at 3pm`, the daemon creates a Google Calendar event. If no clear time is present, it does not create a calendar event.
