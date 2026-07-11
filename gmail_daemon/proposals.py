from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

from .actions import TaskCandidate
from .classifier import EmailClassification
from .gmail import EmailMessage
from .response_generator import template_reply


DB_FILE = Path("gmail_daemon.db")
LEGACY_PROPOSALS_FILE = Path("email_proposals.json")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class EmailProposal:
    id: str
    message_id: str
    thread_id: str
    sender: str
    subject: str
    reason: str
    task_title: str
    proposed_reply: str
    labels: list[str]
    original_text: str = ""
    status: str = "proposed"
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    replacement_text: str | None = None
    sent_message_id: str | None = None
    calendar_event_id: str | None = None


class ProposalStore:
    def __init__(
        self,
        path: Path = DB_FILE,
        legacy_path: Path = LEGACY_PROPOSALS_FILE,
    ) -> None:
        self.path = path
        self.legacy_path = legacy_path
        self._init_db()
        self._migrate_legacy_json()

    def list(self) -> list[EmailProposal]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM proposals
                ORDER BY created_at DESC
                """
            ).fetchall()

        return [_row_to_proposal(row) for row in rows]

    def list_sent_by_thread(self, thread_id: str) -> list[EmailProposal]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM proposals
                WHERE thread_id = ? AND status = 'sent'
                ORDER BY updated_at DESC
                """,
                (thread_id,),
            ).fetchall()

        return [_row_to_proposal(row) for row in rows]

    def save_all(self, proposals: list[EmailProposal]) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM proposals")
            self._insert_many(connection, proposals)

    def upsert_from_email(
        self,
        message: EmailMessage,
        classification: EmailClassification,
        candidate: TaskCandidate,
        proposed_reply: str | None = None,
    ) -> EmailProposal:
        existing = self.get_by_message_id(message.id)
        if existing:
            if not existing.original_text:
                existing.original_text = _original_text(message)
                self.update(existing)
            return existing

        proposal = EmailProposal(
            id=str(uuid.uuid4()),
            message_id=message.id,
            thread_id=message.thread_id,
            sender=message.sender,
            subject=message.subject,
            reason=candidate.reason,
            task_title=candidate.title,
            proposed_reply=proposed_reply or template_reply(candidate),
            labels=classification.labels,
            original_text=_original_text(message),
        )

        with self._connect() as connection:
            self._insert_many(connection, [proposal])

        return proposal

    def update(self, proposal: EmailProposal) -> None:
        proposal.updated_at = _now()
        with self._connect() as connection:
            result = connection.execute(
                """
                UPDATE proposals
                SET
                    message_id = ?,
                    thread_id = ?,
                    sender = ?,
                    subject = ?,
                    reason = ?,
                    task_title = ?,
                    proposed_reply = ?,
                    labels_json = ?,
                    original_text = ?,
                    status = ?,
                    created_at = ?,
                    updated_at = ?,
                    replacement_text = ?,
                    sent_message_id = ?,
                    calendar_event_id = ?
                WHERE id = ?
                """,
                _proposal_update_values(proposal),
            )

        if result.rowcount == 0:
            raise KeyError(f"Proposal not found: {proposal.id}")

    def get(self, proposal_id: str) -> EmailProposal:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM proposals WHERE id = ?",
                (proposal_id,),
            ).fetchone()

        if row is None:
            raise KeyError(f"Proposal not found: {proposal_id}")
        return _row_to_proposal(row)

    def get_by_message_id(self, message_id: str) -> EmailProposal | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM proposals WHERE message_id = ?",
                (message_id,),
            ).fetchone()

        if row is None:
            return None
        return _row_to_proposal(row)

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS proposals (
                    id TEXT PRIMARY KEY,
                    message_id TEXT NOT NULL UNIQUE,
                    thread_id TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    task_title TEXT NOT NULL,
                    proposed_reply TEXT NOT NULL,
                    labels_json TEXT NOT NULL,
                    original_text TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    replacement_text TEXT,
                    sent_message_id TEXT,
                    calendar_event_id TEXT
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_proposals_thread_status ON proposals(thread_id, status)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_proposals_status_created ON proposals(status, created_at)"
            )
            _ensure_column(connection, "proposals", "original_text", "TEXT NOT NULL DEFAULT ''")

    def _migrate_legacy_json(self) -> None:
        if not self.legacy_path.exists():
            return

        with self._connect() as connection:
            count = connection.execute("SELECT COUNT(*) FROM proposals").fetchone()[0]
            if count:
                return

        data = json.loads(self.legacy_path.read_text(encoding="utf-8"))
        proposals = [_proposal_from_dict(item) for item in data.get("proposals", [])]
        if proposals:
            with self._connect() as connection:
                self._insert_many(connection, proposals)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA busy_timeout=5000")
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _insert_many(
        self,
        connection: sqlite3.Connection,
        proposals: Iterable[EmailProposal],
    ) -> None:
        connection.executemany(
            """
            INSERT OR IGNORE INTO proposals (
                id,
                message_id,
                thread_id,
                sender,
                subject,
                reason,
                task_title,
                proposed_reply,
                labels_json,
                original_text,
                status,
                created_at,
                updated_at,
                replacement_text,
                sent_message_id,
                calendar_event_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [_proposal_insert_values(proposal) for proposal in proposals],
        )


def _row_to_proposal(row: sqlite3.Row) -> EmailProposal:
    return EmailProposal(
        id=row["id"],
        message_id=row["message_id"],
        thread_id=row["thread_id"],
        sender=row["sender"],
        subject=row["subject"],
        reason=row["reason"],
        task_title=row["task_title"],
        proposed_reply=row["proposed_reply"],
        labels=json.loads(row["labels_json"]),
        original_text=row["original_text"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        replacement_text=row["replacement_text"],
        sent_message_id=row["sent_message_id"],
        calendar_event_id=row["calendar_event_id"],
    )


def _proposal_from_dict(data: dict) -> EmailProposal:
    return EmailProposal(
        id=data["id"],
        message_id=data["message_id"],
        thread_id=data["thread_id"],
        sender=data["sender"],
        subject=data["subject"],
        reason=data["reason"],
        task_title=data["task_title"],
        proposed_reply=data["proposed_reply"],
        labels=data["labels"],
        original_text=data.get("original_text", ""),
        status=data.get("status", "proposed"),
        created_at=data.get("created_at", _now()),
        updated_at=data.get("updated_at", _now()),
        replacement_text=data.get("replacement_text"),
        sent_message_id=data.get("sent_message_id"),
        calendar_event_id=data.get("calendar_event_id"),
    )


def _proposal_insert_values(proposal: EmailProposal) -> tuple:
    data = asdict(proposal)
    return (
        data["id"],
        data["message_id"],
        data["thread_id"],
        data["sender"],
        data["subject"],
        data["reason"],
        data["task_title"],
        data["proposed_reply"],
        json.dumps(data["labels"]),
        data["original_text"],
        data["status"],
        data["created_at"],
        data["updated_at"],
        data["replacement_text"],
        data["sent_message_id"],
        data["calendar_event_id"],
    )


def _proposal_update_values(proposal: EmailProposal) -> tuple:
    insert_values = _proposal_insert_values(proposal)
    return insert_values[1:] + (proposal.id,)


def _ensure_column(
    connection: sqlite3.Connection,
    table: str,
    column: str,
    definition: str,
) -> None:
    columns = {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _original_text(message: EmailMessage) -> str:
    text = message.body.strip() or message.snippet.strip()
    return text[:8000]

