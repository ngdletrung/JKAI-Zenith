"""
JKAI ZENITH — CONTRACT KERNEL: OBSERVATION
File: core/contracts/observation.py

Contracts for Observation and Telemetry feedback from Execution to Cognitive Kernel.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import time


@dataclass
class Telemetry:
    """Execution telemetry data."""
    latency_ms: float = 0.0
    vram_used_mb: float = 0.0
    ram_used_mb: float = 0.0
    tokens_per_second: float = 0.0
    error_count: int = 0


@dataclass
class Observation:
    """
    Execution/Runtime -> Cognitive Kernel feedback contract.
    Delivered via EventBus to update MissionState without direct imports.
    """
    task_id: str
    status_code: int
    content: str
    telemetry: Telemetry = field(default_factory=Telemetry)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
