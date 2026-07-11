import unittest
from unittest.mock import Mock, patch

from gmail_daemon.actions import TaskCandidate
from gmail_daemon.classifier import EmailClassification
from gmail_daemon.gmail import EmailMessage
from gmail_daemon.response_generator import ResponseGenerator


class ResponseGeneratorTests(unittest.TestCase):
    def test_disabled_generator_uses_template(self) -> None:
        generator = ResponseGenerator(enabled=False, model="unused", base_url="http://127.0.0.1:11434")
        candidate = TaskCandidate(
            title="Reschedule required: test",
            notes="notes",
            reason="Reschedule required",
        )

        response = generator.generate(self.message(), self.classification(), candidate)

        self.assertIn("send over a few times", response)

    def test_enabled_generator_uses_model_response(self) -> None:
        generator = ResponseGenerator(enabled=True, model="local-model", base_url="http://127.0.0.1:11434")
        response = Mock()
        response.read.return_value = b'{"response": "Reply: I can do Tuesday afternoon. Does that work?"}'
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)

        with patch("urllib.request.urlopen", return_value=response):
            generated = generator.generate(self.message(), self.classification(), self.candidate())

        self.assertEqual("I can do Tuesday afternoon. Does that work?", generated)

    def test_enabled_generator_falls_back_when_model_fails(self) -> None:
        generator = ResponseGenerator(enabled=True, model="local-model", base_url="http://127.0.0.1:11434")

        with patch("urllib.request.urlopen", side_effect=OSError("offline")):
            generated = generator.generate(self.message(), self.classification(), self.candidate())

        self.assertIn("send over a few times", generated)

    def test_enabled_generator_tries_multiple_models(self) -> None:
        generator = ResponseGenerator(enabled=True, model="broken-model, working-model", base_url="http://127.0.0.1:11434")
        broken_response = Mock()
        broken_response.read.return_value = b'{"error": "model failed"}'
        broken_response.__enter__ = Mock(return_value=broken_response)
        broken_response.__exit__ = Mock(return_value=False)
        working_response = Mock()
        working_response.read.return_value = b'{"response": "Thanks, please send a few times that work for you."}'
        working_response.__enter__ = Mock(return_value=working_response)
        working_response.__exit__ = Mock(return_value=False)

        with patch("urllib.request.urlopen", side_effect=[broken_response, working_response]):
            generated = generator.generate(self.message(), self.classification(), self.candidate())

        self.assertEqual("Thanks, please send a few times that work for you.", generated)

    def message(self) -> EmailMessage:
        return EmailMessage(
            id="message-1",
            thread_id="thread-1",
            sender="person@example.com",
            subject="test",
            date="",
            snippet="I have to cancel. Can you send me dates?",
            body="I have to cancel. Can you send me dates?",
        )

    def classification(self) -> EmailClassification:
        return EmailClassification(
            labels=["needs reply"],
            scores={"needs reply": 0.95},
            model_name="test-model",
        )

    def candidate(self) -> TaskCandidate:
        return TaskCandidate(
            title="Reschedule required: test",
            notes="notes",
            reason="Reschedule required",
        )


if __name__ == "__main__":
    unittest.main()
