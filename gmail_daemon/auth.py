from __future__ import annotations

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from .config import Config


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


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


def get_credentials(config: Config) -> Credentials:
    credentials = None

    if config.token_file.exists():
        credentials = Credentials.from_authorized_user_file(str(config.token_file), SCOPES)

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    if not credentials or not credentials.valid:
        flow = InstalledAppFlow.from_client_config(_client_config(config), SCOPES)
        credentials = flow.run_local_server(port=8080, prompt="consent")

    config.token_file.write_text(credentials.to_json(), encoding="utf-8")
    return credentials
