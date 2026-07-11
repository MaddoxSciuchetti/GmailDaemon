from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .actions import TaskCandidate


@dataclass(frozen=True)
class CreatedTask:
    id: str
    title: str
    web_view_link: str | None


def resolve_tasklist_id(service: Any, configured_tasklist_id: str) -> str:
    if configured_tasklist_id != "@default":
        return configured_tasklist_id

    response = service.tasklists().list(maxResults=1).execute()
    tasklists = response.get("items", [])
    if tasklists:
        return tasklists[0]["id"]

    created = service.tasklists().insert(body={"title": "Gmail Daemon"}).execute()
    return created["id"]


def create_task(service: Any, tasklist_id: str, candidate: TaskCandidate) -> CreatedTask:
    response = (
        service.tasks()
        .insert(
            tasklist=tasklist_id,
            body={
                "title": candidate.title,
                "notes": candidate.notes,
            },
        )
        .execute()
    )
    return CreatedTask(
        id=response["id"],
        title=response.get("title", candidate.title),
        web_view_link=response.get("webViewLink"),
    )
