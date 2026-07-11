from __future__ import annotations

import argparse
import json

from googleapiclient.discovery import build

from .auth import get_credentials
from .config import load_config
from .email_sender import send_reply
from .gmail import get_message
from .proposals import ProposalStore


def main() -> None:
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("list")

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
