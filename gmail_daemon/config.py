from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


_LOCAL_MNLI_MODEL = Path(
    "/Users/maddoxsciuchetti/.cache/huggingface/hub/"
    "models--FacebookAI--roberta-large-mnli/snapshots/"
    "2a8f12d27941090092df78e4ba6f0928eb5eac98"
)


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
    classifier_enabled: bool
    classifier_model_path: str
    classifier_threshold: float
    google_tasks_enabled: bool
    google_tasks_list_id: str


def _uri(value: str, default_scheme: str = "https://") -> str:
    value = value.strip()
    if value.startswith(("http://", "https://")):
        return value
    return f"{default_scheme}{value}"


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _default_classifier_model_path() -> str:
    if _LOCAL_MNLI_MODEL.exists():
        return str(_LOCAL_MNLI_MODEL)
    return "FacebookAI/roberta-large-mnli"


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

    threshold_raw = os.getenv("EMAIL_CLASSIFIER_THRESHOLD", "0.90").strip()
    try:
        classifier_threshold = float(threshold_raw)
    except ValueError as exc:
        raise RuntimeError("EMAIL_CLASSIFIER_THRESHOLD must be a number") from exc

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
        classifier_enabled=_bool_env("EMAIL_CLASSIFIER_ENABLED", True),
        classifier_model_path=os.getenv(
            "EMAIL_CLASSIFIER_MODEL_PATH",
            _default_classifier_model_path(),
        ).strip(),
        classifier_threshold=classifier_threshold,
        google_tasks_enabled=_bool_env("GOOGLE_TASKS_ENABLED", True),
        google_tasks_list_id=os.getenv("GOOGLE_TASKS_LIST_ID", "@default").strip(),
    )
