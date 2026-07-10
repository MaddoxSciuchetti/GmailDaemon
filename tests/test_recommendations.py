import unittest

from gmail_daemon.gmail import EmailMessage
from gmail_daemon.recommendations import recommend_next_steps


class RecommendationTests(unittest.TestCase):
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

    def test_flags_urgent_action(self) -> None:
        recommendations = recommend_next_steps(
            self.message("Urgent deadline", "Can you please handle this today?")
        )

        self.assertIn("Review this first; it appears time-sensitive.", recommendations)
        self.assertIn("Draft a response or convert the requested action into a task.", recommendations)

    def test_flags_payment_caution(self) -> None:
        recommendations = recommend_next_steps(
            self.message("Invoice", "Please wire payment to the account below.")
        )

        self.assertIn(
            "Verify the sender and payment details before taking financial action.",
            recommendations,
        )

    def test_default_recommendation(self) -> None:
        recommendations = recommend_next_steps(self.message("FYI", "Monthly newsletter"))

        self.assertEqual(["Skim and archive or label if no response is needed."], recommendations)


if __name__ == "__main__":
    unittest.main()
