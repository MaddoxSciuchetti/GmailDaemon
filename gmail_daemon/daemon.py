from __future__ import annotations

import signal
import time
from datetime import datetime

from googleapiclient.discovery import build

from .auth import get_credentials
from .classifier import EmailClassification, build_classifier
from .config import load_config
from .gmail import get_message, list_message_ids
from .recommendations import recommend_next_steps
from .state import DaemonState


_running = True


def _stop(_signum: int, _frame: object) -> None:
    global _running
    _running = False


def main() -> None:
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    config = load_config()
    credentials = get_credentials(config)
    service = build("gmail", "v1", credentials=credentials)
    state = DaemonState.load(config.state_file)
    classifier = build_classifier(
        enabled=config.classifier_enabled,
        model_path=config.classifier_model_path,
        threshold=config.classifier_threshold,
    )

    print("Gmail recommendation daemon started.")
    print(f"Query: {config.gmail_query}")
    print(f"Polling every {config.poll_interval_seconds} seconds.")
    if config.classifier_enabled:
        print(f"Email classifier: {config.classifier_model_path}")
    else:
        print("Email classifier: disabled")

    while _running:
        try:
            _poll_once(service, state, config.gmail_query, classifier)
            state.save(config.state_file)
        except Exception as exc:
            print(f"[{datetime.now().isoformat(timespec='seconds')}] Poll failed: {exc}")

        if _running:
            time.sleep(config.poll_interval_seconds)

    state.save(config.state_file)
    print("Gmail recommendation daemon stopped.")


def _poll_once(service: object, state: DaemonState, query: str, classifier: object) -> None:
    message_ids = list_message_ids(service, query)
    new_ids = [message_id for message_id in reversed(message_ids) if message_id not in state.seen_message_ids]

    if not new_ids:
        print(f"[{datetime.now().isoformat(timespec='seconds')}] No new messages.")
        return

    for message_id in new_ids:
        message = get_message(service, message_id)
        state.seen_message_ids.add(message.id)
        try:
            classification = classifier.classify(message)
        except Exception as exc:
            print(f"Classification failed; using rule-based recommendations: {exc}")
            classification = EmailClassification(labels=[], scores={}, model_name="none")
        _print_recommendation(message, classification)


def _print_recommendation(message: object, classification: EmailClassification) -> None:
    print("")
    print(f"[{datetime.now().isoformat(timespec='seconds')}] New email")
    print(f"From: {message.sender}")
    print(f"Subject: {message.subject or '(no subject)'}")
    print(f"Date: {message.date}")
    if classification.labels:
        labels = ", ".join(classification.labels)
        print(f"Classification: {labels}")
    print("Recommended next steps:")
    for index, recommendation in enumerate(recommend_next_steps(message, classification), start=1):
        print(f"{index}. {recommendation}")
