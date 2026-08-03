"""
JKAI ZENITH — INFRASTRUCTURE PLANE (PLANE 5b)
Directory: core/infrastructure/

Responsibility:
    Hardware resource enforcement (HardwareScheduler), Redis connection pooling,
    PostgreSQL persistence, and OpenTelemetry tracing.

Constitutional Invariant:
    Infrastructure components execute raw resource acquisitions (ResourceRequest)
    and I/O operations without any model-name or business logic awareness.
"""

from core.utils.hardware_scheduler import HardwareScheduler, hardware_scheduler
from core.utils.redis_client import get_redis, redis_safe
from core.utils.models import ResourceRequest, BackendType

__all__ = [
    "HardwareScheduler",
    "hardware_scheduler",
    "get_redis",
    "redis_safe",
    "ResourceRequest",
    "BackendType",
]
