from __future__ import annotations

import re
from dataclasses import dataclass

from .classifier import EmailClassification
from .gmail import EmailMessage


_QUESTION_RE = re.compile(r"\?")
_REQUEST_RE = re.compile(
    r"\b("
    r"can you|could you|would you|please|need you to|i need|"
    r"action required|follow up|reply|respond|review|confirm"
    r")\b",
    re.IGNORECASE,
)
_MEETING_CHANGE_RE = re.compile(
    r"\b("
    r"cancelled|canceled|cancel|reschedule|rescheduled|postpone|postponed|"
    r"can't make|cannot make|won't make|move our meeting"
    r")\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TaskCandidate:
    title: str
    notes: str
    reason: str


def build_task_candidate(
    message: EmailMessage,
    classification: EmailClassification,
) -> TaskCandidate | None:
    text = _message_text(message)
    labels = set(classification.labels)

    if "spam" in labels or "newsletter" in labels:
        return None

    reason = _action_reason(text, labels)
    if reason is None:
        return None

    return TaskCandidate(
        title=_task_title(message, reason),
        notes=_task_notes(message, classification, reason),
        reason=reason,
    )


def _message_text(message: EmailMessage) -> str:
    return "\n".join((message.subject, message.snippet, message.body)).strip()


def _action_reason(text: str, labels: set[str]) -> str | None:
    lowered = text.lower()

    if "meeting" in labels and _MEETING_CHANGE_RE.search(lowered):
        return "Meeting changed or cancelled"

    if "payment" in labels:
        return "Payment or invoice follow-up"

    if "support" in labels:
        return "Support issue needs review"

    if "needs reply" in labels and (_QUESTION_RE.search(text) or _REQUEST_RE.search(text)):
        return "Reply or action requested"

    if _MEETING_CHANGE_RE.search(lowered):
        return "Meeting changed or cancelled"

    if _QUESTION_RE.search(text) or _REQUEST_RE.search(text):
        return "Reply or action requested"

    return None


def _task_title(message: EmailMessage, reason: str) -> str:
    subject = message.subject.strip() or "Email needs attention"
    return f"{reason}: {subject}"[:1024]


def _task_notes(
    message: EmailMessage,
    classification: EmailClassification,
    reason: str,
) -> str:
    labels = ", ".join(classification.labels) if classification.labels else "none"
    gmail_link = f"https://mail.google.com/mail/u/0/#inbox/{message.thread_id}"
    notes = "\n".join(
        (
            f"Reason: {reason}",
            f"From: {message.sender}",
            f"Date: {message.date}",
            f"Classification: {labels}",
            f"Gmail thread: {gmail_link}",
            "",
            "Snippet:",
            message.snippet,
        )
    )
    return notes[:8192]
