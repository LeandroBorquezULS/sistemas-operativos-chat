from __future__ import annotations

import json
from pathlib import Path

from shared.protocol import HISTORY_LIMIT


class HistoryStore:
    def __init__(self, path: str | Path, limit: int = HISTORY_LIMIT) -> None:
        self.path = Path(path)
        self.limit = limit

    def load(self) -> list[dict]:
        if not self.path.exists():
            return []
        items: list[dict] = []
        with self.path.open("r", encoding="utf-8") as fh:
            for raw_line in fh:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    items.append(json.loads(raw_line))
                except json.JSONDecodeError:
                    continue
        return items[-self.limit :]

    def append(self, event: dict) -> list[dict]:
        history = self.load()
        history.append(event)
        history = history[-self.limit :]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as fh:
            for item in history:
                fh.write(json.dumps(item, ensure_ascii=False) + "\n")
        return history
