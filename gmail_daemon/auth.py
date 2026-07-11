from __future__ import annotations

import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from .config import Config


SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/calendar.events",
]


def _client_config(config: Config) -> dict:
    return {
        "installed": {
            "client_id": config.client_id,
            "project_id": config.project_id,
            "auth_uri": config.auth_uri,
            "token_uri": config.token_uri,
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": config.client_secret,
            "redirect_uris": ["http://localhost"],
        }
    }


def _token_has_required_scopes(config: Config) -> bool:
    if not config.token_file.exists():
        return False

    data = json.loads(config.token_file.read_text(encoding="utf-8"))
    raw_scopes = data.get("scopes") or data.get("scope") or []
    if isinstance(raw_scopes, str):
        granted_scopes = set(raw_scopes.split())
    else:
        granted_scopes = set(raw_scopes)

    return set(SCOPES).issubset(granted_scopes)


def _run_oauth_flow(config: Config) -> Credentials:
    flow = InstalledAppFlow.from_client_config(_client_config(config), SCOPES)
    return flow.run_local_server(port=8080, prompt="consent")


def get_credentials(config: Config, force_reauth: bool = False) -> Credentials:
    credentials = None

    if config.token_file.exists() and not force_reauth and _token_has_required_scopes(config):
        credentials = Credentials.from_authorized_user_file(str(config.token_file), SCOPES)

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    if not credentials or not credentials.valid:
        credentials = _run_oauth_flow(config)

    config.token_file.write_text(credentials.to_json(), encoding="utf-8")
    return credentials
