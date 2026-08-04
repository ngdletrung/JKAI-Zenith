"""
JKAI ZENITH — EVENT BUS
File: core/events/bus.py

Async Pub/Sub EventBus allowing decoupled observation feedback loop
from Execution/Runtime back to Cognitive Kernel without circular imports.
"""

import asyncio
import logging
from typing import Dict, List, Callable, Any, Awaitable
from core.contracts.events import DomainEvent

logger = logging.getLogger("EventBus")

HandlerFunc = Callable[[DomainEvent], Awaitable[None]]


class EventBus:
    """Async Pub/Sub EventBus."""

    def __init__(self):
        self._subscribers: Dict[str, List[HandlerFunc]] = {}
        self._lock = asyncio.Lock()

    def subscribe(self, event_type: str, handler: HandlerFunc):
        """Register an async handler for a given event_type or '*' for all."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug(f"[EVENT-BUS]: Handler subscribed to {event_type!r}")

    async def publish(self, event: DomainEvent):
        """Publish a DomainEvent to all matching subscribers asynchronously."""
        handlers = list(self._subscribers.get(event.event_type, []))
        handlers.extend(self._subscribers.get("*", []))

        if not handlers:
            return

        tasks = []
        for h in handlers:
            try:
                tasks.append(asyncio.create_task(h(event)))
            except Exception as e:
                logger.error("[EVENT-BUS-ERR]: Handler dispatch error: %s", e)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


_global_event_bus: EventBus = None


def get_event_bus() -> EventBus:
    """Get singleton EventBus instance."""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus
