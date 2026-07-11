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
_RESCHEDULE_REQUEST_RE = re.compile(
    r"\b("
    r"send me (some )?dates|send (over )?(some )?dates|"
    r"what (time|date) works|where it would work best|"
    r"availability|available times|new time|another time"
    r")\b",
    re.IGNORECASE,
)
_MARKETING_CTA_RE = re.compile(
    r"\b("
    r"book a demo|schedule a demo|join us|register now|sign up|"
    r"learn more|read more|get started|start your free trial|"
    r"download (the )?(guide|whitepaper|ebook)|limited time|"
    r"don't miss|exclusive offer|save [0-9]+%|unsubscribe|"
    r"view (this )?email in (your )?browser"
    r")\b",
    re.IGNORECASE,
)
_MARKETING_SENDER_RE = re.compile(
    r"\b("
    r"marketing|newsletter|noreply|no-reply|updates|campaign|"
    r"mailchimp|hubspot|sendgrid|klaviyo|constantcontact"
    r")\b",
    re.IGNORECASE,
)
_GENERIC_GREETING_RE = re.compile(r"\b(hi there|hello there|dear customer|dear friend)\b", re.IGNORECASE)
_OPERATIONAL_PLATFORM_RE = re.compile(
    r"\b("
    r"luma|lu\.ma|calendly|google calendar|eventbrite|zoom|meetup"
    r")\b",
    re.IGNORECASE,
)
_OPERATIONAL_EVENT_RE = re.compile(
    r"\b("
    r"rsvp|event|ticket|reservation|booking|meeting|webinar|"
    r"cancelled|canceled|rescheduled|updated|venue|host"
    r")\b",
    re.IGNORECASE,
)
_NON_ACTION_EVENT_RE = re.compile(
    r"\b("
    r"is starting|starting in|starting tomorrow|thanks for joining|"
    r"how did you like|view event|my ticket|featured event|"
    r"new message in|pending approval|host needs to approve"
    r")\b",
    re.IGNORECASE,
)
_ACCOUNT_MARKETING_RE = re.compile(
    r"\b("
    r"rabatte|discounts|deal|deals|offer|offers|free week|trial spots|"
    r"konto l[aä]uft bald ab"
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
    operational_platform_action = _is_operational_platform_action(message, text)

    if "spam" in labels:
        return None

    if _is_non_action_platform_update(message, text):
        return None

    if _ACCOUNT_MARKETING_RE.search(text):
        return None

    if ("newsletter" in labels or "sales" in labels) and not operational_platform_action:
        return None

    if _is_marketing_noise(message, text, labels) and not operational_platform_action:
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


def _is_operational_platform_action(message: EmailMessage, text: str) -> bool:
    platform_context = f"{message.sender}\n{text}"
    return bool(_OPERATIONAL_PLATFORM_RE.search(platform_context) and _OPERATIONAL_EVENT_RE.search(text))


def _is_non_action_platform_update(message: EmailMessage, text: str) -> bool:
    platform_context = f"{message.sender}\n{text}"
    if not _OPERATIONAL_PLATFORM_RE.search(platform_context):
        return False
    if _MEETING_CHANGE_RE.search(text.lower()) or _RESCHEDULE_REQUEST_RE.search(text.lower()):
        return False
    return bool(_NON_ACTION_EVENT_RE.search(text))


def _is_marketing_noise(message: EmailMessage, text: str, labels: set[str]) -> bool:
    sender = message.sender.lower()
    lowered = text.lower()
    score = 0

    if "sales" in labels or "newsletter" in labels:
        score += 2

    if _MARKETING_CTA_RE.search(lowered):
        score += 2

    if _MARKETING_SENDER_RE.search(sender):
        score += 1

    if _GENERIC_GREETING_RE.search(lowered):
        score += 1

    if "unsubscribe" in lowered:
        score += 2

    return score >= 2


def _action_reason(text: str, labels: set[str]) -> str | None:
    lowered = text.lower()

    if _MEETING_CHANGE_RE.search(lowered) and _RESCHEDULE_REQUEST_RE.search(lowered):
        return "Reschedule required"

    if "meeting" in labels and _MEETING_CHANGE_RE.search(lowered):
        return "Meeting changed or cancelled"

    if "payment" in labels:
        return "Payment or invoice follow-up"

    if "support" in labels:
        return "Support issue needs review"

    if _MEETING_CHANGE_RE.search(lowered):
        return "Meeting changed or cancelled"

    if "needs reply" in labels and (_QUESTION_RE.search(text) or _REQUEST_RE.search(text)):
        return "Reply or action requested"

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
