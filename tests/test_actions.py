import unittest

from gmail_daemon.actions import build_task_candidate
from gmail_daemon.classifier import EmailClassification
from gmail_daemon.gmail import EmailMessage


class ActionTests(unittest.TestCase):
    def message(
        self,
        subject: str,
        body: str,
        sender: str = "sender@example.com",
    ) -> EmailMessage:
        return EmailMessage(
            id="msg-1",
            thread_id="thread-1",
            sender=sender,
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

    def test_skips_generic_marketing_cta(self) -> None:
        candidate = build_task_candidate(
            self.message(
                "Last chance to improve your workflow",
                "Hi there, please register now for our webinar. Learn more and unsubscribe here.",
                sender="marketing@saas-company.example",
            ),
            self.classification(["needs reply", "sales"]),
        )

        self.assertIsNone(candidate)

    def test_skips_newsletter_with_question_style_subject(self) -> None:
        candidate = build_task_candidate(
            self.message(
                "Ready to grow faster?",
                "Book a demo today and see how our platform can help. Unsubscribe anytime.",
                sender="updates@hubspot.example",
            ),
            self.classification(["needs reply", "newsletter"]),
        )

        self.assertIsNone(candidate)

    def test_allows_luma_cancellation_action(self) -> None:
        candidate = build_task_candidate(
            self.message(
                "Event cancelled: Founder Dinner",
                "The host cancelled this Luma event. Your RSVP is no longer active.",
                sender="notifications@lu.ma",
            ),
            self.classification(["meeting", "newsletter"]),
        )

        self.assertIsNotNone(candidate)
        self.assertEqual("Meeting changed or cancelled", candidate.reason)


if __name__ == "__main__":
    unittest.main()
