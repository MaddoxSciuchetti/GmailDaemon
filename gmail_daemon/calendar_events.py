from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from .gmail import EmailMessage
from .proposals import EmailProposal


_AGREEMENT_RE = re.compile(
    r"\b("
    r"yes|sounds good|works for me|that works|confirmed|agreed|"
    r"see you then|perfect|let's do it|lets do it"
    r")\b",
    re.IGNORECASE,
)
_ISOISH_RE = re.compile(
    r"\b(?P<date>\d{4}-\d{2}-\d{2})[ T](?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\b"
)
_TOMORROW_RE = re.compile(r"\btomorrow\s+(?:at\s+)?(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<ampm>am|pm)?\b", re.IGNORECASE)


@dataclass(frozen=True)
class CalendarCandidate:
    summary: str
    start: datetime
    end: datetime
    description: str


def build_calendar_candidate(
    proposal: EmailProposal,
    message: EmailMessage,
    timezone_name: str = "America/Los_Angeles",
) -> CalendarCandidate | None:
    text = "\n".join((message.subject, message.snippet, message.body))
    if not _AGREEMENT_RE.search(text):
        return None

    start = _extract_start(text, timezone_name)
    if start is None:
        return None

    return CalendarCandidate(
        summary=f"Appointment: {proposal.subject or proposal.reason}",
        start=start,
        end=start + timedelta(hours=1),
        description=f"Created from Gmail thread {proposal.thread_id}\nFrom: {message.sender}",
    )


def create_calendar_event(service: Any, candidate: CalendarCandidate, calendar_id: str = "primary") -> str:
    response = (
        service.events()
        .insert(
            calendarId=calendar_id,
            body={
                "summary": candidate.summary,
                "description": candidate.description,
                "start": {
                    "dateTime": candidate.start.isoformat(),
                    "timeZone": str(candidate.start.tzinfo),
                },
                "end": {
                    "dateTime": candidate.end.isoformat(),
                    "timeZone": str(candidate.end.tzinfo),
                },
            },
        )
        .execute()
    )
    return response["id"]


def _extract_start(text: str, timezone_name: str) -> datetime | None:
    timezone = ZoneInfo(timezone_name)
    iso_match = _ISOISH_RE.search(text)
    if iso_match:
        minute = int(iso_match.group("minute") or "0")
        return datetime.fromisoformat(
            f"{iso_match.group('date')}T{int(iso_match.group('hour')):02d}:{minute:02d}:00"
        ).replace(tzinfo=timezone)

    tomorrow_match = _TOMORROW_RE.search(text)
    if tomorrow_match:
        hour = int(tomorrow_match.group("hour"))
        minute = int(tomorrow_match.group("minute") or "0")
        ampm = (tomorrow_match.group("ampm") or "").lower()
        if ampm == "pm" and hour < 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0
        tomorrow = datetime.now(timezone).date() + timedelta(days=1)
        return datetime(tomorrow.year, tomorrow.month, tomorrow.day, hour, minute, tzinfo=timezone)

    return None
