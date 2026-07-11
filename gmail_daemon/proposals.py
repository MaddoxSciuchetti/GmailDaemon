from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .actions import TaskCandidate
from .classifier import EmailClassification
from .gmail import EmailMessage


PROPOSALS_FILE = Path("email_proposals.json")


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
    status: str = "proposed"
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    replacement_text: str | None = None
    sent_message_id: str | None = None
    calendar_event_id: str | None = None


class ProposalStore:
    def __init__(self, path: Path = PROPOSALS_FILE) -> None:
        self.path = path

    def list(self) -> list[EmailProposal]:
        if not self.path.exists():
            return []

        data = json.loads(self.path.read_text(encoding="utf-8"))
        return [EmailProposal(**item) for item in data.get("proposals", [])]

    def save_all(self, proposals: list[EmailProposal]) -> None:
        self.path.write_text(
            json.dumps({"proposals": [asdict(item) for item in proposals]}, indent=2),
            encoding="utf-8",
        )

    def upsert_from_email(
        self,
        message: EmailMessage,
        classification: EmailClassification,
        candidate: TaskCandidate,
    ) -> EmailProposal:
        proposals = self.list()
        existing = next((item for item in proposals if item.message_id == message.id), None)
        if existing:
            return existing

        proposal = EmailProposal(
            id=str(uuid.uuid4()),
            message_id=message.id,
            thread_id=message.thread_id,
            sender=message.sender,
            subject=message.subject,
            reason=candidate.reason,
            task_title=candidate.title,
            proposed_reply=_default_reply(candidate),
            labels=classification.labels,
        )
        proposals.append(proposal)
        self.save_all(proposals)
        return proposal

    def update(self, proposal: EmailProposal) -> None:
        proposals = self.list()
        for index, item in enumerate(proposals):
            if item.id == proposal.id:
                proposal.updated_at = _now()
                proposals[index] = proposal
                self.save_all(proposals)
                return
        raise KeyError(f"Proposal not found: {proposal.id}")

    def get(self, proposal_id: str) -> EmailProposal:
        for proposal in self.list():
            if proposal.id == proposal_id:
                return proposal
        raise KeyError(f"Proposal not found: {proposal_id}")


def _default_reply(candidate: TaskCandidate) -> str:
    if candidate.reason == "Meeting changed or cancelled":
        return "Thanks for the update. I saw the change and will adjust accordingly."

    if candidate.reason == "Payment or invoice follow-up":
        return "Thanks for sending this over. I will review the details and follow up if anything is missing."

    if candidate.reason == "Support issue needs review":
        return "Thanks for flagging this. I will take a look and get back to you."

    return "Thanks for reaching out. I will review this and follow up shortly."
