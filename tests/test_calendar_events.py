import unittest

from gmail_daemon.calendar_events import build_calendar_candidate
from gmail_daemon.gmail import EmailMessage
from gmail_daemon.proposals import EmailProposal


class CalendarEventTests(unittest.TestCase):
    def proposal(self) -> EmailProposal:
        return EmailProposal(
            id="proposal-1",
            message_id="message-1",
            thread_id="thread-1",
            sender="person@example.com",
            subject="Coffee",
            reason="Reply or action requested",
            task_title="Reply",
            proposed_reply="Sounds good.",
            labels=["needs reply"],
            status="sent",
        )

    def message(self, body: str) -> EmailMessage:
        return EmailMessage(
            id="message-2",
            thread_id="thread-1",
            sender="person@example.com",
            subject="Re: Coffee",
            date="",
            snippet=body,
            body=body,
        )

    def test_builds_event_for_agreement_with_iso_time(self) -> None:
        candidate = build_calendar_candidate(
            self.proposal(),
            self.message("Yes, sounds good. Let's meet 2026-07-12 15:00."),
        )

        self.assertIsNotNone(candidate)
        self.assertEqual(15, candidate.start.hour)

    def test_skips_agreement_without_time(self) -> None:
        candidate = build_calendar_candidate(
            self.proposal(),
            self.message("Yes, sounds good."),
        )

        self.assertIsNone(candidate)


if __name__ == "__main__":
    unittest.main()
