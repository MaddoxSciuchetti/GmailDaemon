from __future__ import annotations

import base64
from email.message import EmailMessage as MimeEmailMessage
from typing import Any

from .gmail import EmailMessage


def send_reply(service: Any, original: EmailMessage, body: str) -> str:
    message = MimeEmailMessage()
    message["To"] = original.sender
    message["Subject"] = _reply_subject(original.subject)
    message.set_content(body)

    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    response = (
        service.users()
        .messages()
        .send(
            userId="me",
            body={
                "raw": encoded,
                "threadId": original.thread_id,
            },
        )
        .execute()
    )
    return response["id"]


def _reply_subject(subject: str) -> str:
    subject = subject.strip() or "(no subject)"
    if subject.lower().startswith("re:"):
        return subject
    return f"Re: {subject}"
