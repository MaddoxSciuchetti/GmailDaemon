from __future__ import annotations

import argparse
import json

from googleapiclient.discovery import build

from .auth import get_credentials
from .config import load_config
from .email_sender import send_reply
from .actions import build_task_candidate
from .classifier import build_classifier
from .gmail import get_message, list_message_ids
from .proposals import ProposalStore
from .response_generator import ResponseGenerator


def main() -> None:
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("list")

    backfill = subcommands.add_parser("backfill")
    backfill.add_argument("--limit", type=int, default=20)

    accept = subcommands.add_parser("accept")
    accept.add_argument("proposal_id")

    decline = subcommands.add_parser("decline")
    decline.add_argument("proposal_id")
    decline.add_argument("--text", required=True)

    args = parser.parse_args()
    store = ProposalStore()

    if args.command == "list":
        print(json.dumps([item.__dict__ for item in store.list()]))
        return

    config = load_config()
    credentials = get_credentials(config)
    gmail_service = build("gmail", "v1", credentials=credentials)

    if args.command == "backfill":
        classifier = build_classifier(
            enabled=config.classifier_enabled,
            model_path=config.classifier_model_path,
            threshold=config.classifier_threshold,
        )
        response_generator = ResponseGenerator(
            enabled=config.response_generator_enabled,
            model=config.response_generator_model,
            base_url=config.response_generator_base_url,
        )
        created = []
        for message_id in list_message_ids(gmail_service, config.gmail_query, args.limit):
            message = get_message(gmail_service, message_id)
            classification = classifier.classify(message)
            candidate = build_task_candidate(message, classification)
            if candidate is None:
                continue
            proposed_reply = response_generator.generate(message, classification, candidate)
            proposal = store.upsert_from_email(message, classification, candidate, proposed_reply)
            created.append(proposal.__dict__)

        print(json.dumps(created))
        return

    if args.command == "accept":
        proposal = store.get(args.proposal_id)
        original = get_message(gmail_service, proposal.message_id)
        proposal.sent_message_id = send_reply(gmail_service, original, proposal.proposed_reply)
        proposal.status = "sent"
        store.update(proposal)
        print(json.dumps(proposal.__dict__))
        return

    if args.command == "decline":
        proposal = store.get(args.proposal_id)
        proposal.replacement_text = args.text
        proposal.status = "declined"
        store.update(proposal)
        print(json.dumps(proposal.__dict__))


if __name__ == "__main__":
    main()
