from __future__ import annotations

import signal
import threading
from datetime import datetime

from googleapiclient.discovery import build

from .auth import get_credentials
from .actions import build_task_candidate
from .calendar_events import build_calendar_candidate, create_calendar_event
from .classifier import EmailClassification, build_classifier
from .config import load_config
from .gmail import get_message, list_message_ids
from .proposals import ProposalStore
from .recommendations import recommend_next_steps
from .state import DaemonState
from .tasks import create_task, resolve_tasklist_id


_stop_event = threading.Event()


def _stop(_signum: int, _frame: object) -> None:
    print("\nStopping Gmail recommendation daemon...")
    _stop_event.set()


def main() -> None:
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    config = load_config()
    credentials = get_credentials(config)
    gmail_service = build("gmail", "v1", credentials=credentials)
    tasks_service = build("tasks", "v1", credentials=credentials) if config.google_tasks_enabled else None
    calendar_service = build("calendar", "v3", credentials=credentials)
    tasklist_id = resolve_tasklist_id(tasks_service, config.google_tasks_list_id) if tasks_service else ""
    state = DaemonState.load(config.state_file)
    proposal_store = ProposalStore()
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
    if config.google_tasks_enabled:
        print(f"Google Tasks: enabled ({tasklist_id})")
    else:
        print("Google Tasks: disabled")

    while not _stop_event.is_set():
        try:
            _poll_once(
                gmail_service,
                tasks_service,
                state,
                config.gmail_query,
                classifier,
                config.google_tasks_enabled,
                tasklist_id,
                proposal_store,
                calendar_service,
            )
            state.save(config.state_file)
        except Exception as exc:
            print(f"[{datetime.now().isoformat(timespec='seconds')}] Poll failed: {exc}")

        _stop_event.wait(config.poll_interval_seconds)

    state.save(config.state_file)
    print("Gmail recommendation daemon stopped.")


def _poll_once(
    gmail_service: object,
    tasks_service: object | None,
    state: DaemonState,
    query: str,
    classifier: object,
    tasks_enabled: bool,
    tasklist_id: str,
    proposal_store: ProposalStore,
    calendar_service: object,
) -> None:
    message_ids = list_message_ids(gmail_service, query)
    new_ids = [message_id for message_id in reversed(message_ids) if message_id not in state.seen_message_ids]

    if not new_ids:
        print(f"[{datetime.now().isoformat(timespec='seconds')}] No new messages.")
        return

    for message_id in new_ids:
        message = get_message(gmail_service, message_id)
        state.seen_message_ids.add(message.id)
        try:
            classification = classifier.classify(message)
        except Exception as exc:
            print(f"Classification failed; using rule-based recommendations: {exc}")
            classification = EmailClassification(labels=[], scores={}, model_name="none")
        _maybe_create_calendar_event(calendar_service, state, proposal_store, message)
        _maybe_create_task(
            tasks_service,
            state,
            tasklist_id,
            message,
            classification,
            tasks_enabled,
            proposal_store,
        )
        _print_recommendation(message, classification)


def _maybe_create_task(
    tasks_service: object | None,
    state: DaemonState,
    tasklist_id: str,
    message: object,
    classification: EmailClassification,
    tasks_enabled: bool,
    proposal_store: ProposalStore,
) -> None:
    if not tasks_enabled or tasks_service is None or message.id in state.created_task_message_ids:
        return

    candidate = build_task_candidate(message, classification)
    if candidate is None:
        return

    proposal = proposal_store.upsert_from_email(message, classification, candidate)
    print(f"Created email proposal: {proposal.task_title}")

    try:
        task = create_task(tasks_service, tasklist_id, candidate)
    except Exception as exc:
        print(f"Google Task creation failed: {exc}")
        return

    state.created_task_message_ids.add(message.id)
    print(f"Created Google Task: {task.title}")
    if task.web_view_link:
        print(f"Task link: {task.web_view_link}")


def _maybe_create_calendar_event(
    calendar_service: object,
    state: DaemonState,
    proposal_store: ProposalStore,
    message: object,
) -> None:
    if message.thread_id in state.created_calendar_thread_ids:
        return

    sent_proposals = [
        proposal
        for proposal in proposal_store.list()
        if proposal.thread_id == message.thread_id and proposal.status == "sent"
    ]
    if not sent_proposals:
        return

    candidate = build_calendar_candidate(sent_proposals[0], message)
    if candidate is None:
        return

    try:
        event_id = create_calendar_event(calendar_service, candidate)
    except Exception as exc:
        print(f"Calendar event creation failed: {exc}")
        return

    sent_proposals[0].calendar_event_id = event_id
    proposal_store.update(sent_proposals[0])
    state.created_calendar_thread_ids.add(message.thread_id)
    print(f"Created calendar event: {candidate.summary}")


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
