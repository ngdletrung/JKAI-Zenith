"""
🏛️ ADAPTIVE MODEL GOVERNOR (AMG) v2 — RUNTIME DISCOVERY
File: core/runtime/runtime_discovery.py

Purpose:
    Pure HTTP probe layer — discovers Ollama endpoint health, endpoint capabilities,
    and available/resident models. Has NO imports from core.governor.
    It answers WHAT is available.

Constitutional Invariants:
    1. EndpointType (GPU | CPU | UNKNOWN) comes from endpoint configuration / probe metadata,
       NEVER hardcoded inside decision logic.
    2. Separates DISCOVERED models (/api/tags) from RESIDENT models (/api/ps).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional

import requests

logger = logging.getLogger("AMG_RuntimeDiscovery")

DEFAULT_GPU_HOST = "127.0.0.1:11434"
DEFAULT_CPU_HOST = "127.0.0.1:11435"

PROBE_TIMEOUT_S  = 3.0
WARMUP_TIMEOUT_S = 90.0


class EndpointType(Enum):
    """Execution domain of an Ollama endpoint."""
    GPU     = auto()
    CPU     = auto()
    UNKNOWN = auto()


@dataclass
class EndpointInfo:
    """
    Health and capability snapshot of an Ollama endpoint.
    """
    host: str
    endpoint_type: EndpointType = EndpointType.UNKNOWN
    is_alive: bool = False
    version: str = ""
    latency_ms: float = 0.0
    error: str = ""

    # Hardware info — populated lazily by AMGBootstrap via enrich_from_hw()
    gpu_name: str = ""
    vram_total_mb: float = 0.0
    vram_free_mb: float = 0.0
    ram_total_gb: float = 0.0
    ram_free_gb: float = 0.0

    @property
    def supports_gpu(self) -> bool:
        return self.endpoint_type == EndpointType.GPU

    @property
    def backend_label(self) -> str:
        return self.endpoint_type.name


@dataclass
class AvailableModel:
    """Model available in local store (/api/tags). Discovered, NOT necessarily resident."""
    name: str
    size_gb: float = 0.0
    digest: str = ""
    modified_at: str = ""


@dataclass
class ResidentModel:
    """Model currently loaded in memory (/api/ps). Used for lifecycle decisions."""
    name: str
    host: str
    size_vram_mb: float = 0.0
    size_ram_mb: float = 0.0
    expires_at: str = ""    # ISO timestamp — raw LRU signal


@dataclass
class RuntimeSnapshot:
    """
    Complete point-in-time runtime state.
    """
    endpoints: Dict[str, EndpointInfo] = field(default_factory=dict)
    available_models: List[AvailableModel] = field(default_factory=list)
    resident_models: List[ResidentModel] = field(default_factory=list)
    snapshot_at: float = field(default_factory=time.time)

    @property
    def gpu_endpoint(self) -> Optional[EndpointInfo]:
        for ep in self.endpoints.values():
            if ep.endpoint_type == EndpointType.GPU:
                return ep
        return None

    @property
    def cpu_endpoint(self) -> Optional[EndpointInfo]:
        for ep in self.endpoints.values():
            if ep.endpoint_type == EndpointType.CPU:
                return ep
        return None

    @property
    def any_alive(self) -> bool:
        return any(e.is_alive for e in self.endpoints.values())

    @property
    def all_alive(self) -> bool:
        return all(e.is_alive for e in self.endpoints.values()) and bool(self.endpoints)

    @property
    def available_model_names(self) -> List[str]:
        return [m.name for m in self.available_models]

    @property
    def resident_model_names(self) -> List[str]:
        return [m.name for m in self.resident_models]

    def is_resident(self, name: str) -> bool:
        for rm in self.resident_models:
            if rm.name == name or rm.name.split(":")[0] == name.split(":")[0]:
                return True
        return False

    def log_summary(self) -> str:
        alive = sum(1 for e in self.endpoints.values() if e.is_alive)
        return (
            f"Endpoints: {alive}/{len(self.endpoints)} alive | "
            f"Available: {len(self.available_models)} | "
            f"Resident: {len(self.resident_models)}"
        )


class RuntimeDiscovery:
    """
    Discovers endpoint health and model availability.
    Endpoint types (GPU vs CPU) are explicitly mapped via config, not hardcoded.
    """

    def __init__(
        self,
        endpoint_mapping: Optional[Dict[str, EndpointType]] = None,
    ):
        # Default mapping if none provided
        self.endpoint_mapping = endpoint_mapping or {
            DEFAULT_GPU_HOST: EndpointType.GPU,
            DEFAULT_CPU_HOST: EndpointType.CPU,
        }

    def snapshot(self) -> RuntimeSnapshot:
        """Full runtime snapshot."""
        snap = RuntimeSnapshot()

        for host, ep_type in self.endpoint_mapping.items():
            snap.endpoints[host] = self.probe_endpoint(host, ep_type)

        seen: set = set()
        for host, info in snap.endpoints.items():
            if not info.is_alive:
                continue
            for m in self.get_available_models(host):
                if m.name not in seen:
                    snap.available_models.append(m)
                    seen.add(m.name)

        for host, info in snap.endpoints.items():
            if not info.is_alive:
                continue
            snap.resident_models.extend(self.get_resident_models(host))

        logger.info(f"[DISCOVERY] {snap.log_summary()}")
        return snap

    def probe_endpoint(self, host: str, endpoint_type: EndpointType = EndpointType.UNKNOWN) -> EndpointInfo:
        """Probe a single endpoint."""
        t0 = time.monotonic()
        try:
            resp = requests.get(f"http://{host}/api/tags", timeout=PROBE_TIMEOUT_S)
            latency_ms = (time.monotonic() - t0) * 1000
            if resp.status_code == 200:
                return EndpointInfo(
                    host=host,
                    endpoint_type=endpoint_type,
                    is_alive=True,
                    version=resp.headers.get("X-Ollama-Version", ""),
                    latency_ms=round(latency_ms, 1),
                )
            return EndpointInfo(host=host, endpoint_type=endpoint_type, error=f"HTTP {resp.status_code}")
        except requests.exceptions.ConnectionError:
            return EndpointInfo(host=host, endpoint_type=endpoint_type, error="Connection refused")
        except requests.exceptions.Timeout:
            return EndpointInfo(host=host, endpoint_type=endpoint_type, error=f"Timeout >{PROBE_TIMEOUT_S}s")
        except Exception as e:
            return EndpointInfo(host=host, endpoint_type=endpoint_type, error=str(e))

    def get_available_models(self, host: str) -> List[AvailableModel]:
        """List available models (/api/tags)."""
        try:
            resp = requests.get(f"http://{host}/api/tags", timeout=PROBE_TIMEOUT_S)
            resp.raise_for_status()
            return [
                AvailableModel(
                    name=item.get("name", ""),
                    size_gb=round(item.get("size", 0) / (1024 ** 3), 2),
                    digest=item.get("digest", ""),
                    modified_at=item.get("modified_at", ""),
                )
                for item in resp.json().get("models", [])
                if item.get("name")
            ]
        except Exception as e:
            logger.warning(f"[DISCOVERY] list_models({host}): {e}")
            return []

    def get_resident_models(self, host: str) -> List[ResidentModel]:
        """List resident models (/api/ps)."""
        try:
            resp = requests.get(f"http://{host}/api/ps", timeout=PROBE_TIMEOUT_S)
            resp.raise_for_status()
            result = []
            for item in resp.json().get("models", []):
                size_bytes = item.get("size", 0)
                vram_bytes = item.get("size_vram", 0)
                result.append(ResidentModel(
                    name=item.get("name", ""),
                    host=host,
                    size_vram_mb=round(vram_bytes / (1024 ** 2), 1),
                    size_ram_mb=round(max(0, size_bytes - vram_bytes) / (1024 ** 2), 1),
                    expires_at=item.get("expires_at", ""),
                ))
            return result
        except Exception as e:
            logger.warning(f"[DISCOVERY] get_resident({host}): {e}")
            return []

    def wait_until_ready(
        self,
        hosts: Optional[List[str]] = None,
        timeout_s: float = WARMUP_TIMEOUT_S,
        poll_interval_s: float = 3.0,
    ) -> bool:
        """Wait until all specified hosts are online."""
        target_hosts = hosts or list(self.endpoint_mapping.keys())
        deadline = time.monotonic() + timeout_s
        attempt = 0
        while time.monotonic() < deadline:
            alive = [h for h in target_hosts if self.probe_endpoint(h).is_alive]
            if len(alive) == len(target_hosts):
                logger.info(f"[DISCOVERY] All {len(target_hosts)} endpoints ready (retries={attempt})")
                return True
            time.sleep(poll_interval_s)
            attempt += 1
        logger.error(f"[DISCOVERY] Timeout after {timeout_s}s waiting for endpoints")
        return False

    def enrich_from_hw(self, endpoint: EndpointInfo, hw_state) -> EndpointInfo:
        """Enrich EndpointInfo lazily with hardware details."""
        if not hw_state:
            return endpoint
        if endpoint.supports_gpu:
            endpoint.vram_total_mb = getattr(hw_state, "vram_total_mb", 0.0)
            endpoint.vram_free_mb  = getattr(hw_state, "vram_free_mb", 0.0)
            endpoint.gpu_name      = getattr(hw_state, "gpu_name", "")
        endpoint.ram_total_gb = getattr(hw_state, "ram_total_gb", 0.0)
        endpoint.ram_free_gb  = getattr(hw_state, "ram_free_gb", 0.0)
        return endpoint
