from __future__ import annotations

import re

from .classifier import EmailClassification
from .gmail import EmailMessage


_URGENT_WORDS = ("urgent", "asap", "immediately", "today", "deadline", "overdue")
_MEETING_WORDS = ("meeting", "calendar", "schedule", "call", "zoom", "meet")
_PAYMENT_WORDS = ("invoice", "payment", "receipt", "bank", "wire", "billing")
_ACTION_WORDS = ("please", "can you", "could you", "would you", "need", "action required")
_QUESTION_RE = re.compile(r"\?")


def recommend_next_steps(
    message: EmailMessage,
    classification: EmailClassification | None = None,
) -> list[str]:
    text = f"{message.subject}\n{message.snippet}\n{message.body}".lower()
    recommendations: list[str] = []
    labels = set(classification.labels if classification else [])

    if "urgent" in labels or any(word in text for word in _URGENT_WORDS):
        recommendations.append("Review this first; it appears time-sensitive.")

    if "meeting" in labels or any(word in text for word in _MEETING_WORDS):
        recommendations.append("Check your calendar availability and prepare a scheduling reply.")

    if "payment" in labels or any(word in text for word in _PAYMENT_WORDS):
        recommendations.append("Verify the sender and payment details before taking financial action.")

    if "needs reply" in labels or _QUESTION_RE.search(text) or any(phrase in text for phrase in _ACTION_WORDS):
        recommendations.append("Draft a response or convert the requested action into a task.")

    if "newsletter" in labels:
        recommendations.append("Label this as a newsletter and read it later if it is not urgent.")

    if "sales" in labels:
        recommendations.append("Decide whether this is a real opportunity before spending time on it.")

    if "support" in labels:
        recommendations.append("Open or update a support task with the relevant context.")

    if "spam" in labels:
        recommendations.append("Mark as spam or block the sender if this is unsolicited.")

    if not recommendations:
        recommendations.append("Skim and archive or label if no response is needed.")

    return recommendations
