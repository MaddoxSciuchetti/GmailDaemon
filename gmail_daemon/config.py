from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    client_id: str
    client_secret: str
    project_id: str | None
    auth_uri: str
    token_uri: str
    poll_interval_seconds: int
    gmail_query: str
    state_file: Path
    token_file: Path


def _uri(value: str, default_scheme: str = "https://") -> str:
    value = value.strip()
    if value.startswith(("http://", "https://")):
        return value
    return f"{default_scheme}{value}"


def load_config() -> Config:
    load_dotenv()

    client_id = os.getenv("CLIENT_ID", "").strip()
    client_secret = os.getenv("CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise RuntimeError("CLIENT_ID and CLIENT_SECRET must be set in .env")

    interval_raw = os.getenv("POLL_INTERVAL_SECONDS", "60").strip()
    try:
        poll_interval_seconds = int(interval_raw)
    except ValueError as exc:
        raise RuntimeError("POLL_INTERVAL_SECONDS must be an integer") from exc

    if poll_interval_seconds < 10:
        raise RuntimeError("POLL_INTERVAL_SECONDS must be at least 10 seconds")

    return Config(
        client_id=client_id,
        client_secret=client_secret,
        project_id=os.getenv("PROJECT_ID"),
        auth_uri=_uri(os.getenv("AUTH_URI", "https://accounts.google.com/o/oauth2/auth")),
        token_uri=_uri(os.getenv("TOKEN_URI", "https://oauth2.googleapis.com/token")),
        poll_interval_seconds=poll_interval_seconds,
        gmail_query=os.getenv("GMAIL_QUERY", "in:inbox newer_than:7d").strip(),
        state_file=Path(os.getenv("STATE_FILE", ".gmail_daemon_state.json")),
        token_file=Path(os.getenv("TOKEN_FILE", "token.json")),
    )
