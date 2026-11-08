"""Lightweight pub-sub event bus for decoupled gameplay notifications."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable


EventHandler = Callable[[dict[str, Any]], None]


class EventManager:
    """Dispatches named gameplay events between decoupled systems."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Register a callback function for a specific event_type."""
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)

    def emit(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        """Invoke all subscribers registered for event_type."""
        data = payload or {}
        for handler in list(self._subscribers.get(event_type, [])):
            handler(data)
