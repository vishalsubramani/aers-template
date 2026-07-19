"""A deliberately small todo core used by the AERS tutorial."""
from __future__ import annotations

import itertools


class TodoList:
    def __init__(self) -> None:
        self._items: dict[int, dict] = {}
        self._ids = itertools.count(1)

    def add(self, title: str) -> int:
        if not title or not title.strip():
            raise ValueError("title must be a non-empty string")
        item_id = next(self._ids)
        self._items[item_id] = {"id": item_id, "title": title.strip(), "done": False}
        return item_id

    def complete(self, item_id: int) -> None:
        if item_id not in self._items:
            raise KeyError(f"no such todo: {item_id}")
        self._items[item_id]["done"] = True

    def items(self) -> list[dict]:
        return [dict(item) for item in self._items.values()]
