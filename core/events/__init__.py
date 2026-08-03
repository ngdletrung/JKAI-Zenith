"""
JKAI ZENITH — EVENT BUS SUBPACKAGE
Package: core/events/

Decoupled Pub/Sub EventBus for feedback loop communication between domains.
"""

from core.events.bus import EventBus, get_event_bus

__all__ = ["EventBus", "get_event_bus"]
