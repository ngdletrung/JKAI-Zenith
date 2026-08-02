"""
🏛️ ADAPTIVE MODEL GOVERNOR (AMG) v2 — MODEL LIFECYCLE MANAGER
File: core/runtime/model_lifecycle.py

Purpose:
    Executes model residency operations (load, unload, evict) based on
    ExecutionProfile or ResidentModel.

Constitutional Invariants:
    1. ModelLifecycleManager NEVER selects which model to use.
    2. Interface is Profile-Centric / Resident-Centric:
       unload(profile) or unload(resident), NEVER raw model_name string.
    3. EvictionScore components are normalized to [0.0, 1.0].
    4. dry_run mode performs NO state-mutating HTTP POST requests.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from core.governor.model_capabilities import ExecutionProfile

from core.runtime.runtime_discovery import (
    RuntimeDiscovery,
    ResidentModel,
    EndpointType,
    DEFAULT_GPU_HOST,
    DEFAULT_CPU_HOST,
)

logger = logging.getLogger("AMG_ModelLifecycle")

LOAD_TIMEOUT_S   = 120.0
UNLOAD_TIMEOUT_S = 15.0
EVICT_TIMEOUT_S  = 10.0


@dataclass
class LifecycleResult:
    """Result of a lifecycle operation."""
    model_name: str
    operation: str          # "load" | "unload" | "evict"
    success: bool
    host: str
    elapsed_ms: float = 0.0
    vram_used_mb: float = 0.0
    ram_used_mb: float = 0.0
    dry_run: bool = False
    error: str = ""

    def log_summary(self) -> str:
        dry_tag = " [DRY-RUN]" if self.dry_run else ""
        status = "OK" if self.success else f"FAIL({self.error})"
        return (
            f"[LIFECYCLE{dry_tag}] {self.operation.upper()} {self.model_name!r} "
            f"@ {self.host} → {status} ({self.elapsed_ms:.0f}ms)"
        )


@dataclass
class LifecycleDecision:
    """Decision produced by Lifecycle Policy for a candidate ExecutionProfile."""
    profile: "ExecutionProfile"
    warmup_policy: str           # "WARM" | "LAZY" | "EVICTABLE"
    eviction_score: float = 0.0  # 0.0 = protect, 1.0 = evict first
    reason: str = ""


class EvictionScorer:
    """
    Computes normalized EvictionScore in range [0.0, 1.0].

    Components:
        1. age_norm: time since last use (longer = higher evict score)
        2. size_norm: VRAM footprint (larger = higher evict score to free space)
        3. reload_ease_norm: smaller/faster file size (easier to reload = higher evict score)
        4. low_priority_norm: role priority (lower priority role = higher evict score)

    Formula:
        score = 0.35 * age_norm + 0.30 * size_norm + 0.20 * reload_ease_norm + 0.15 * low_priority_norm
    """

    @classmethod
    def compute(
        cls,
        resident: ResidentModel,
        all_residents: List[ResidentModel],
        protected_names: List[str],
    ) -> float:
        if resident.name in protected_names or any(resident.name.startswith(p) for p in protected_names):
            return 0.0  # Protect entirely

        # 1. Age normalization: compute real time elapsed or time until expiration
        age_norm = 0.5  # default neutral
        if resident.expires_at:
            try:
                from datetime import datetime, timezone
                # Parse ISO 8601 string e.g. "2026-08-02T18:30:00.000Z"
                exp_clean = resident.expires_at.rstrip("Z").split(".")[0]
                exp_dt = datetime.fromisoformat(exp_clean).replace(tzinfo=timezone.utc)
                now_dt = datetime.now(timezone.utc)
                # Ollama sets keep_alive expiration in future. Sooner expiration = less recently used / closer to expire
                time_remaining_sec = max(0.0, (exp_dt - now_dt).total_seconds())
                # Less time remaining -> higher eviction score (norm [0.0, 1.0])
                age_norm = max(0.0, 1.0 - min(1.0, time_remaining_sec / 600.0))
            except Exception:
                age_norm = 0.7

        # 2. Size normalization
        max_vram = max((r.size_vram_mb for r in all_residents), default=1.0)
        size_norm = min(1.0, resident.size_vram_mb / max(max_vram, 1.0))

        # 3. Reload ease normalization (smaller footprint = easier to reload)
        total_mb = resident.size_vram_mb + resident.size_ram_mb
        reload_ease_norm = max(0.0, 1.0 - min(1.0, total_mb / 20000.0))

        # 4. Low priority norm (default baseline)
        low_priority_norm = 0.5

        score = (
            0.35 * age_norm +
            0.30 * size_norm +
            0.20 * reload_ease_norm +
            0.15 * low_priority_norm
        )
        return round(min(1.0, max(0.0, score)), 3)


class ModelLifecycleManager:
    """
    Manages model residency via profile-centric APIs.
    Supports dry_run mode for safe testing and inspection.
    """

    def __init__(
        self,
        gpu_host: str = DEFAULT_GPU_HOST,
        cpu_host: str = DEFAULT_CPU_HOST,
        dry_run: bool = False,
        discovery: Optional[RuntimeDiscovery] = None,
    ):
        self.gpu_host = gpu_host
        self.cpu_host = cpu_host
        self.dry_run = dry_run
        self._discovery = discovery or RuntimeDiscovery()

        # Track call counts for dry-run verification tests
        self.load_calls: int = 0
        self.unload_calls: int = 0
        self.evict_calls: int = 0

    def load(self, profile: "ExecutionProfile") -> LifecycleResult:
        """
        Load/warm a model according to ExecutionProfile.
        """
        self.load_calls += 1
        model_name = profile.model_name
        host = self._select_host(profile)
        is_embed = getattr(profile, "is_embedding_only", False)

        if self.dry_run:
            logger.info(f"[LIFECYCLE-DRYRUN] Would load {model_name!r} on {host}")
            return LifecycleResult(
                model_name=model_name,
                operation="load",
                success=True,
                host=host,
                elapsed_ms=1.0,
                dry_run=True,
            )

        api_path = "embeddings" if is_embed else "generate"
        url = f"http://{host}/api/{api_path}"
        options = self._profile_to_options(profile)

        body = {
            "model": model_name,
            "keep_alive": profile.keep_alive,
            "options": options,
            "prompt": "warmup" if is_embed else ".",
        }

        t0 = time.monotonic()
        try:
            resp = requests.post(url, json=body, timeout=LOAD_TIMEOUT_S)
            elapsed_ms = (time.monotonic() - t0) * 1000
            if resp.status_code == 200:
                vram_mb, ram_mb = self._read_model_memory(model_name, host)
                res = LifecycleResult(
                    model_name=model_name, operation="load", success=True,
                    host=host, elapsed_ms=round(elapsed_ms, 0),
                    vram_used_mb=vram_mb, ram_used_mb=ram_mb,
                )
                logger.info(res.log_summary())
                return res
            return LifecycleResult(
                model_name=model_name, operation="load", success=False,
                host=host, elapsed_ms=round(elapsed_ms, 0), error=f"HTTP {resp.status_code}",
            )
        except Exception as e:
            elapsed_ms = (time.monotonic() - t0) * 1000
            return LifecycleResult(
                model_name=model_name, operation="load", success=False,
                host=host, elapsed_ms=round(elapsed_ms, 0), error=str(e),
            )

    def unload(
        self,
        target: Union["ExecutionProfile", ResidentModel],
        host: Optional[str] = None,
    ) -> LifecycleResult:
        """
        Unload a model using ExecutionProfile or ResidentModel.
        NEVER accepts raw string model names.
        """
        self.unload_calls += 1

        if hasattr(target, "model_name"):
            model_name = target.model_name
            target_host = host or self._select_host(target)
        elif hasattr(target, "name"):
            model_name = target.name
            target_host = host or getattr(target, "host", self.gpu_host)
        else:
            raise TypeError("unload target must be ExecutionProfile or ResidentModel")

        if self.dry_run:
            logger.info(f"[LIFECYCLE-DRYRUN] Would unload {model_name!r} from {target_host}")
            return LifecycleResult(
                model_name=model_name, operation="unload", success=True,
                host=target_host, elapsed_ms=1.0, dry_run=True,
            )

        t0 = time.monotonic()
        try:
            body = {"model": model_name, "keep_alive": 0, "prompt": ""}
            resp = requests.post(f"http://{target_host}/api/generate", json=body, timeout=UNLOAD_TIMEOUT_S)
            elapsed_ms = (time.monotonic() - t0) * 1000
            if resp.status_code == 200:
                return LifecycleResult(
                    model_name=model_name, operation="unload", success=True,
                    host=target_host, elapsed_ms=round(elapsed_ms, 0),
                )
            return LifecycleResult(
                model_name=model_name, operation="unload", success=False,
                host=target_host, elapsed_ms=round(elapsed_ms, 0), error=f"HTTP {resp.status_code}",
            )
        except Exception as e:
            elapsed_ms = (time.monotonic() - t0) * 1000
            return LifecycleResult(
                model_name=model_name, operation="unload", success=False,
                host=target_host, elapsed_ms=round(elapsed_ms, 0), error=str(e),
            )

    def evict_for_pressure(
        self,
        required_vram_mb: float,
        host: str,
        protect_profiles: Optional[List["ExecutionProfile"]] = None,
    ) -> List[LifecycleResult]:
        """
        Evict models based on normalized EvictionScore.
        """
        self.evict_calls += 1
        protect_names = [p.model_name for p in (protect_profiles or [])]
        residents = self._discovery.get_resident_models(host)

        # Compute normalized EvictionScore for each resident model
        scored = []
        for r in residents:
            score = EvictionScorer.compute(r, residents, protect_names)
            scored.append((score, r))

        # Higher score = evict first
        scored.sort(key=lambda x: x[0], reverse=True)

        results: List[LifecycleResult] = []
        freed_mb = 0.0

        for score, r in scored:
            if score <= 0.0:
                continue  # Protected
            if freed_mb >= required_vram_mb:
                break
            res = self.unload(r, host=host)
            results.append(res)
            if res.success:
                freed_mb += r.size_vram_mb

        return results

    def _select_host(self, profile: "ExecutionProfile") -> str:
        backend = str(getattr(profile, "backend", "CPU")).upper()
        if backend in ("GPU", "HYBRID"):
            return self.gpu_host
        return self.cpu_host

    @staticmethod
    def _profile_to_options(profile: "ExecutionProfile") -> dict:
        opts: dict = {}
        if getattr(profile, "num_gpu_layers", None) is not None:
            opts["num_gpu"] = int(profile.num_gpu_layers)
        if getattr(profile, "num_ctx", None):
            opts["num_ctx"] = int(profile.num_ctx)
        if getattr(profile, "num_thread", None):
            opts["num_thread"] = int(profile.num_thread)
        if getattr(profile, "temperature", None) is not None:
            opts["temperature"] = float(profile.temperature)
        raw = getattr(profile, "raw_options", {})
        if raw:
            opts.update(raw)
        return opts

    def _read_model_memory(self, model_name: str, host: str) -> tuple[float, float]:
        for rm in self._discovery.get_resident_models(host):
            if rm.name == model_name or rm.name.split(":")[0] == model_name.split(":")[0]:
                return rm.size_vram_mb, rm.size_ram_mb
        return 0.0, 0.0
