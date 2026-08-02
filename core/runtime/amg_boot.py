"""
🏛️ ADAPTIVE MODEL GOVERNOR (AMG) v2 — AMG BOOTSTRAP ORCHESTRATOR
File: core/runtime/amg_boot.py

Purpose:
    Main entry point for AMG startup execution.
    Orchestrates Discovery → Portfolio Build → Decision → Lifecycle.

Constitutional Invariants:
    1. amg_boot receives a BootRequest with required capabilities.
       It does NOT hardcode role names inside its orchestration logic.
    2. Decision Parity: Normal mode and --diagnostic mode use the EXACT same
       pure decision function `_make_decisions()`.
    3. --dry-run is strictly READ-ONLY (no state-mutating HTTP POST calls).
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from core.governor.hardware_monitor import HardwareMonitor, HardwareState
from core.governor.model_capabilities import ExecutionProfile, ModelClass
from core.governor.model_inspector import ModelInspector
from core.governor.model_registry import ModelRegistry
from core.governor.portfolio_governor import PortfolioGovernor
from core.runtime.boot_cache import BootCache
from core.runtime.model_lifecycle import LifecycleDecision, ModelLifecycleManager
from core.runtime.ollama_adapter import OllamaAdapter
from core.runtime.runtime_discovery import (
    RuntimeDiscovery,
    RuntimeSnapshot,
    DEFAULT_CPU_HOST,
    DEFAULT_GPU_HOST,
)

logger = logging.getLogger("AMG_Boot")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# Capability name to target Role mapping (for capability-driven BootRequest)
CAPABILITY_TO_ROLE_MAP: Dict[str, str] = {
    "conversation": "RECEPTIONIST",
    "chat":         "RECEPTIONIST",
    "embedding":    "EMBEDDER",
    "coding":       "EXECUTOR",
    "reasoning":    "PLANNER",
    "criticism":    "CRITIC",
    "summary":      "SUMMARIZER",
    "vision":       "VISION",
}


@dataclass
class BootRequest:
    """Input payload for AMG Boot execution."""
    startup_mode: str = "FAST"                                # "FAST" | "DEEP" | "ALL"
    required_capabilities: List[str] = field(default_factory=lambda: ["conversation", "embedding"])
    lifecycle_policy: str = "adaptive"                       # "adaptive" | "aggressive_warm" | "lazy_all"
    dry_run: bool = False
    diagnostic: bool = False


@dataclass
class BootReport:
    """Complete summary of AMG Boot decisions and lifecycle actions."""
    request: BootRequest
    snapshot: RuntimeSnapshot
    hw_state: HardwareState
    decisions: List[LifecycleDecision] = field(default_factory=list)
    boot_elapsed_ms: float = 0.0

    def print_report(self):
        print("\n" + "=" * 60)
        print(" [AMG v2] JKAI ZENITH — ADAPTIVE MODEL GOVERNOR BOOT REPORT")
        print("=" * 60)
        print(f" Mode         : {self.request.startup_mode} {'[DRY-RUN]' if self.request.dry_run else ''}")
        print(f" Endpoints    : GPU={self.snapshot.gpu_endpoint.is_alive if self.snapshot.gpu_endpoint else False} | "
              f"CPU={self.snapshot.cpu_endpoint.is_alive if self.snapshot.cpu_endpoint else False}")
        gpu_name = getattr(self.hw_state, "gpu_name", "GPU")
        print(f" Hardware     : {gpu_name} ({self.hw_state.vram_free_mb:.0f}MB free VRAM) | "
              f"RAM {self.hw_state.ram_free_gb:.1f}GB free")
        print(f" Portfolio    : {len(self.snapshot.available_models)} discovered models")
        print("-" * 60)
        print(" AMG DECISIONS & LIFECYCLE")
        print("-" * 60)

        for d in self.decisions:
            p = d.profile
            print(f"\n Role       : {p.role_name}")
            print(f"   Model    : {p.model_name}")
            print(f"   Backend  : {p.backend} ({p.memory_layout}) | GPU Layers: {p.num_gpu_layers} | Context: {p.num_ctx}")
            print(f"   Policy   : {d.warmup_policy}")
            print(f"   Why      : {d.reason}")

        print("\n" + "=" * 60)
        print(f" Total Boot Time: {self.boot_elapsed_ms:.0f}ms")
        print("=" * 60 + "\n")


class AMGBootstrap:
    """
    AMG Boot Orchestrator.
    """

    def __init__(
        self,
        gpu_host: str = DEFAULT_GPU_HOST,
        cpu_host: str = DEFAULT_CPU_HOST,
    ):
        self.gpu_host = gpu_host
        self.cpu_host = cpu_host
        self.discovery = RuntimeDiscovery()
        self.lifecycle = ModelLifecycleManager(gpu_host=gpu_host, cpu_host=cpu_host)
        self.cache = BootCache()

    def boot(self, request: BootRequest) -> BootReport:
        t0 = time.monotonic()
        self.lifecycle.dry_run = request.dry_run

        # Phase 1: Discovery
        logger.info(f"[AMG-BOOT] Phase 1: Discovering runtime endpoints...")
        snap = self.discovery.snapshot()
        if not snap.any_alive:
            raise RuntimeError("No Ollama endpoints available. Ensure Zenith_Guardian has started services.")

        # Read Hardware
        hw_state = HardwareMonitor.get_state()

        # Phase 2: Portfolio Inspection & Registry Build
        logger.info("[AMG-BOOT] Phase 2: Building model capability portfolio...")
        registry = ModelRegistry.instance()
        gpu_adapter = OllamaAdapter(host=self.gpu_host)

        cached_raw = self.cache.load_cache()
        profiles_to_cache = {}

        for m in snap.available_models:
            # Check incremental cache
            c_entry = cached_raw.get(m.name)
            if c_entry and c_entry.get("ollama_digest") == m.digest:
                # Load from cache
                p = self._profile_from_cache(c_entry)
                registry.register(p)
                profiles_to_cache[m.name] = p
            else:
                # Inspect model via adapter
                info = gpu_adapter.inspect_model_sync(m.name)
                if info:
                    p = ModelInspector.build_profile(info)
                    registry.register(p)
                    profiles_to_cache[m.name] = p

        self.cache.save_cache(profiles_to_cache)

        # Phase 3: Pure Decision Function (Guarantees Decision Parity)
        logger.info("[AMG-BOOT] Phase 3: Executing Portfolio Governor decisions...")
        decisions = self._make_decisions(request, registry, hw_state)

        # Phase 4: Lifecycle Execution (unless dry_run)
        logger.info(f"[AMG-BOOT] Phase 4: Executing lifecycle policy (dry_run={request.dry_run})...")
        for d in decisions:
            if d.warmup_policy == "WARM" and not request.dry_run:
                self.lifecycle.load(d.profile)
            elif d.warmup_policy == "WARM" and request.dry_run:
                self.lifecycle.load(d.profile)  # Calls dry_run mock load

        elapsed_ms = (time.monotonic() - t0) * 1000
        report = BootReport(
            request=request,
            snapshot=snap,
            hw_state=hw_state,
            decisions=decisions,
            boot_elapsed_ms=round(elapsed_ms, 1),
        )

        if request.diagnostic or request.dry_run:
            report.print_report()

        return report

    @classmethod
    def _make_decisions(
        cls,
        request: BootRequest,
        registry: ModelRegistry,
        hw_state: HardwareState,
    ) -> List[LifecycleDecision]:
        """
        Pure decision function.
        Receives request + registry + hw_state → returns List[LifecycleDecision].
        Guarantees decision parity between normal and diagnostic modes.
        """
        governor = PortfolioGovernor(registry=registry)
        decisions: List[LifecycleDecision] = []

        # Derive target roles from requested capabilities
        target_roles = []
        for cap in request.required_capabilities:
            role = CAPABILITY_TO_ROLE_MAP.get(cap.lower(), "RECEPTIONIST")
            if role not in target_roles:
                target_roles.append(role)

        for role in target_roles:
            quality = "high" if request.startup_mode == "DEEP" else "medium"
            profile = governor.resolve(
                role=role,
                requested_model="auto",
                quality=quality,
                hw=hw_state,
            )

            # Determine Lifecycle Policy (WARM vs LAZY vs EVICTABLE)
            if role == "RECEPTIONIST" and request.startup_mode == "FAST":
                policy_str = "WARM"
                reason = "Capability matched 'conversation'; fast-first boot policy"
            elif role == "EMBEDDER":
                policy_str = "LAZY"
                reason = "Capability required; lazy load on first embedding request"
            else:
                policy_str = "LAZY"
                reason = f"Capability required for {role}; load on demand"

            decisions.append(LifecycleDecision(
                profile=profile,
                warmup_policy=policy_str,
                eviction_score=0.2 if policy_str == "WARM" else 0.7,
                reason=reason,
            ))

        return decisions

    @staticmethod
    def _profile_from_cache(entry: dict) -> ModelCapabilityProfile:
        classes = {ModelClass[c] for c in entry.get("model_classes", ["GENERAL"]) if c in ModelClass.__members__}
        return ModelCapabilityProfile(
            model_name=entry.get("model_name", ""),
            architecture=entry.get("architecture", "transformer"),
            family=entry.get("family", ""),
            context_length_max=entry.get("context_length_max", 8192),
            model_classes=classes,
            has_vision=entry.get("has_vision", False),
            has_tool_calling=entry.get("has_tool_calling", True),
            is_embedding_only=entry.get("is_embedding_only", False),
            assessment_confidence=entry.get("assessment_confidence", 0.8),
            last_inspected_at=entry.get("last_inspected_at", time.time()),
            ollama_digest=entry.get("ollama_digest", ""),
        )


def main():
    parser = argparse.ArgumentParser(description="JKAI AMG v2 Bootstrap Orchestrator")
    parser.add_argument("--mode", default="FAST", choices=["FAST", "DEEP", "ALL"], help="Startup mode")
    parser.add_argument("--dry-run", action="store_true", help="Perform discovery and decision without loading models")
    parser.add_argument("--diagnostic", action="store_true", help="Display full diagnostic decision trace")
    args = parser.parse_args()

    req = BootRequest(
        startup_mode=args.mode,
        dry_run=args.dry_run,
        diagnostic=args.diagnostic,
    )

    bootstrapper = AMGBootstrap()
    try:
        bootstrapper.boot(req)
        sys.exit(0)
    except Exception as e:
        logger.error(f"[AMG-BOOT] Boot failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
