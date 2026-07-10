from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DaemonState:
    seen_message_ids: set[str] = field(default_factory=set)

    @classmethod
    def load(cls, path: Path) -> "DaemonState":
        if not path.exists():
            return cls()

        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(seen_message_ids=set(data.get("seen_message_ids", [])))

    def save(self, path: Path) -> None:
        path.write_text(
            json.dumps({"seen_message_ids": sorted(self.seen_message_ids)}, indent=2),
            encoding="utf-8",
        )
