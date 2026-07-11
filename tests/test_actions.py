import unittest

from gmail_daemon.actions import build_task_candidate
from gmail_daemon.classifier import EmailClassification
from gmail_daemon.gmail import EmailMessage


class ActionTests(unittest.TestCase):
    def message(self, subject: str, body: str) -> EmailMessage:
        return EmailMessage(
            id="msg-1",
            thread_id="thread-1",
            sender="sender@example.com",
            subject=subject,
            date="Fri, 10 Jul 2026 12:00:00 -0700",
            snippet=body[:80],
            body=body,
        )

    def classification(self, labels: list[str]) -> EmailClassification:
        return EmailClassification(
            labels=labels,
            scores={label: 0.95 for label in labels},
            model_name="test-model",
        )

    def test_creates_task_for_cancelled_meeting(self) -> None:
        candidate = build_task_candidate(
            self.message("Tomorrow's meeting", "I need to cancel our meeting tomorrow."),
            self.classification(["meeting"]),
        )

        self.assertIsNotNone(candidate)
        self.assertEqual("Meeting changed or cancelled", candidate.reason)

    def test_creates_task_for_direct_request(self) -> None:
        candidate = build_task_candidate(
            self.message("Contract", "Can you review this today?"),
            self.classification(["needs reply"]),
        )

        self.assertIsNotNone(candidate)
        self.assertEqual("Reply or action requested", candidate.reason)

    def test_skips_newsletter(self) -> None:
        candidate = build_task_candidate(
            self.message("Weekly update", "Here are this week's product updates."),
            self.classification(["newsletter"]),
        )

        self.assertIsNone(candidate)

    def test_skips_informational_email(self) -> None:
        candidate = build_task_candidate(
            self.message("FYI", "The office will be closed Monday."),
            self.classification([]),
        )

        self.assertIsNone(candidate)


if __name__ == "__main__":
    unittest.main()
