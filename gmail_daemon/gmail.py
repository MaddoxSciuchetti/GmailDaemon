from __future__ import annotations

import base64
from dataclasses import dataclass
from email.header import decode_header, make_header
from typing import Any


@dataclass(frozen=True)
class EmailMessage:
    id: str
    thread_id: str
    sender: str
    subject: str
    date: str
    snippet: str
    body: str


def list_message_ids(service: Any, query: str, max_results: int = 20) -> list[str]:
    response = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )
    return [message["id"] for message in response.get("messages", [])]


def get_message(service: Any, message_id: str) -> EmailMessage:
    payload = (
        service.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )

    headers = _headers(payload.get("payload", {}).get("headers", []))
    return EmailMessage(
        id=payload["id"],
        thread_id=payload.get("threadId", ""),
        sender=headers.get("from", ""),
        subject=_decode_mime_header(headers.get("subject", "")),
        date=headers.get("date", ""),
        snippet=payload.get("snippet", ""),
        body=_extract_text(payload.get("payload", {})),
    )


def _headers(raw_headers: list[dict[str, str]]) -> dict[str, str]:
    return {header["name"].lower(): header.get("value", "") for header in raw_headers}


def _decode_mime_header(value: str) -> str:
    if not value:
        return ""
    return str(make_header(decode_header(value)))


def _extract_text(payload: dict[str, Any]) -> str:
    mime_type = payload.get("mimeType", "")
    body = payload.get("body", {})
    data = body.get("data")

    if mime_type == "text/plain" and data:
        return _decode_body(data)

    parts = payload.get("parts", [])
    plain_parts = [_extract_text(part) for part in parts if part.get("mimeType") == "text/plain"]
    text = "\n".join(part for part in plain_parts if part)
    if text:
        return text

    nested_parts = [_extract_text(part) for part in parts]
    return "\n".join(part for part in nested_parts if part)


def _decode_body(data: str) -> str:
    raw = base64.urlsafe_b64decode(data.encode("utf-8"))
    return raw.decode("utf-8", errors="replace")
