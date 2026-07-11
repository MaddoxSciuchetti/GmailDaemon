import json
import tempfile
import unittest
from pathlib import Path

from gmail_daemon.actions import TaskCandidate
from gmail_daemon.classifier import EmailClassification
from gmail_daemon.gmail import EmailMessage
from gmail_daemon.proposals import EmailProposal, ProposalStore


class ProposalStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.db_path = root / "test.db"
        self.legacy_path = root / "email_proposals.json"
        self.store = ProposalStore(path=self.db_path, legacy_path=self.legacy_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def message(self, message_id: str = "message-1", thread_id: str = "thread-1") -> EmailMessage:
        return EmailMessage(
            id=message_id,
            thread_id=thread_id,
            sender="sender@example.com",
            subject="Can you review this?",
            date="Fri, 10 Jul 2026 12:00:00 -0700",
            snippet="Can you review this today?",
            body="Can you review this today?",
        )

    def classification(self) -> EmailClassification:
        return EmailClassification(
            labels=["needs reply"],
            scores={"needs reply": 0.95},
            model_name="test-model",
        )

    def candidate(self) -> TaskCandidate:
        return TaskCandidate(
            title="Reply or action requested: Can you review this?",
            notes="notes",
            reason="Reply or action requested",
        )

    def test_upsert_is_idempotent_by_message_id(self) -> None:
        first = self.store.upsert_from_email(self.message(), self.classification(), self.candidate())
        second = self.store.upsert_from_email(self.message(), self.classification(), self.candidate())

        self.assertEqual(first.id, second.id)
        self.assertEqual(1, len(self.store.list()))

    def test_update_persists_status(self) -> None:
        proposal = self.store.upsert_from_email(self.message(), self.classification(), self.candidate())
        proposal.status = "sent"
        proposal.sent_message_id = "sent-1"

        self.store.update(proposal)

        stored = self.store.get(proposal.id)
        self.assertEqual("sent", stored.status)
        self.assertEqual("sent-1", stored.sent_message_id)

    def test_lists_sent_proposals_by_thread(self) -> None:
        sent = self.store.upsert_from_email(self.message(), self.classification(), self.candidate())
        sent.status = "sent"
        self.store.update(sent)
        self.store.upsert_from_email(
            self.message(message_id="message-2", thread_id="other-thread"),
            self.classification(),
            self.candidate(),
        )

        proposals = self.store.list_sent_by_thread("thread-1")

        self.assertEqual([sent.id], [proposal.id for proposal in proposals])

    def test_migrates_legacy_json_when_database_is_empty(self) -> None:
        legacy = EmailProposal(
            id="legacy-1",
            message_id="legacy-message",
            thread_id="legacy-thread",
            sender="sender@example.com",
            subject="Legacy",
            reason="Reply or action requested",
            task_title="Reply",
            proposed_reply="Thanks.",
            labels=["needs reply"],
        )
        self.legacy_path.write_text(json.dumps({"proposals": [legacy.__dict__]}), encoding="utf-8")

        migrated = ProposalStore(path=self.db_path, legacy_path=self.legacy_path)

        self.assertEqual("legacy-1", migrated.get("legacy-1").id)


if __name__ == "__main__":
    unittest.main()
