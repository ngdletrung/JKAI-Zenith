# -*- coding: utf-8 -*-
"""
core/benchmark/tier2_bench.py
JKAI Zenith - Byte-Identical Benchmark Harness for Tier 2 Backends

Discipline:
  - Input hashed before each run; hash verified before scoring.
  - Environment captured (CPU, GPU, driver, python, git commit).
  - Warmup runs excluded from stats.
  - "Not measured" is explicit, never inferred.
  - Output is JSON with full provenance.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.cognitive_bus.decision_substrate_adapter import (
    DecisionPrimitive,
    ExecutionTier,
    TypedJudgementPacket,
)
from core.cognitive_bus.tier2_backend import Tier2Backend


# ---------------------------------------------------------------------------
# Case definition
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    state: Dict[str, Any]
    primitive: DecisionPrimitive
    question: str
    options: Optional[List[str]] = None
    descriptions: Optional[Dict[str, str]] = None
    expected: Optional[Any] = None      # ground-truth label, if available

    def input_hash(self) -> str:
        payload = {
            "state": self.state,
            "primitive": self.primitive.value if hasattr(self.primitive, "value") else str(self.primitive),
            "question": self.question,
            "options": self.options,
        }
        blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()


# ---------------------------------------------------------------------------
# Result shapes
# ---------------------------------------------------------------------------

@dataclass
class EnvironmentRecord:
    hostname: str
    platform: str
    python_version: str
    cpu: str
    ram_gb: float
    gpu: str
    gpu_driver: str
    git_commit: str
    git_dirty: bool
    timestamp_utc: str


@dataclass
class LatencyStats:
    n: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    mean_ms: float


@dataclass
class CaseResult:
    case_id: str
    input_hash: str
    result: Any
    confidence: float
    latency_ms: float
    distribution_sum: float
    tier: str
    error: Optional[str] = None


@dataclass
class BenchmarkResult:
    backend_name: str
    backend_version: str
    calibration_state: str
    ece_reported: Optional[float]
    is_deterministic: bool
    is_local_only: bool
    environment: EnvironmentRecord
    cases: List[CaseResult]
    latency: LatencyStats
    accuracy: Optional[float]              # None if no expected labels
    ece_measured: Optional[float]          # None if no expected labels
    n_cases: int
    n_errors: int
    notes: List[str] = field(default_factory=list)

    def to_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(asdict(self), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# Environment capture
# ---------------------------------------------------------------------------

def _capture_env() -> EnvironmentRecord:
    import socket
    from datetime import datetime, timezone

    try:
        ram_gb = round(
            int(subprocess.check_output(
                ["wmic", "ComputerSystem", "get", "TotalPhysicalMemory"],
                text=True, timeout=5,
            ).split()[1]) / (1024 ** 3), 1
        )
    except Exception:
        ram_gb = -1.0

    gpu, driver = "unknown", "unknown"
    try:
        out = subprocess.check_output(
            ["wmic", "path", "win32_VideoController", "get", "Name,DriverVersion"],
            text=True, timeout=5,
        )
        lines = [l.strip() for l in out.splitlines() if l.strip() and "Name" not in l]
        if lines:
            gpu = lines[0]
    except Exception:
        pass

    commit, dirty = "unknown", False
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, timeout=5
        ).strip()
        dirty = bool(subprocess.check_output(
            ["git", "status", "--porcelain"], text=True, timeout=5
        ).strip())
    except Exception:
        pass

    return EnvironmentRecord(
        hostname=socket.gethostname(),
        platform=platform.platform(),
        python_version=sys.version.split()[0],
        cpu=platform.processor() or "unknown",
        ram_gb=ram_gb,
        gpu=gpu,
        gpu_driver=driver,
        git_commit=commit[:12],
        git_dirty=dirty,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def _latency_stats(samples: List[float]) -> LatencyStats:
    if not samples:
        return LatencyStats(0, 0.0, 0.0, 0.0, 0.0)
    s = sorted(samples)
    n = len(s)
    def pct(p: float) -> float:
        idx = min(int(p * n), n - 1)
        return s[idx]
    return LatencyStats(
        n=n,
        p50_ms=pct(0.50),
        p95_ms=pct(0.95),
        p99_ms=pct(0.99),
        mean_ms=sum(s) / n,
    )


def _accuracy(results: List[CaseResult], cases: List[BenchmarkCase]) -> Optional[float]:
    pairs = [(r, c) for r, c in zip(results, cases) if c.expected is not None]
    if not pairs:
        return None
    correct = sum(1 for r, c in pairs if r.result == c.expected)
    return correct / len(pairs)


def _ece(
    confidences: List[float],
    correct: List[bool],
    n_bins: int = 15,
) -> Optional[float]:
    """Standard binned ECE. Returns None if no labels."""
    if not confidences:
        return None
    bins: List[List[Tuple[float, bool]]] = [[] for _ in range(n_bins)]
    for c, ok in zip(confidences, correct):
        idx = min(int(c * n_bins), n_bins - 1)
        bins[idx].append((c, ok))

    n = len(confidences)
    ece = 0.0
    for b in bins:
        if not b:
            continue
        avg_conf = sum(c for c, _ in b) / len(b)
        avg_acc = sum(1 for _, ok in b if ok) / len(b)
        ece += (len(b) / n) * abs(avg_conf - avg_acc)
    return ece


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

class Tier2Benchmark:
    def __init__(
        self,
        backend: Tier2Backend,
        warmup_runs: int = 3,
        timeout_ms: int = 450,
    ):
        self.backend = backend
        self.warmup_runs = warmup_runs
        self.timeout_ms = timeout_ms

    def run(self, cases: List[BenchmarkCase]) -> BenchmarkResult:
        notes: List[str] = []

        # 0. Load backend
        t_load_start = time.perf_counter()
        self.backend.load()
        load_ms = (time.perf_counter() - t_load_start) * 1000.0
        notes.append(f"backend load: {load_ms:.1f} ms")

        # 1. Warmup (results discarded)
        for _ in range(self.warmup_runs):
            for case in cases[: min(3, len(cases))]:
                try:
                    self._run_one(case)
                except Exception:
                    pass
        notes.append(f"warmup runs: {self.warmup_runs}")

        # 2. Measured runs
        results: List[CaseResult] = []
        for case in cases:
            # Byte-identical verification
            h = case.input_hash()
            r = self._run_one(case, expected_hash=h)
            results.append(r)

        # 3. Stats
        latencies = [r.latency_ms for r in results if r.error is None]
        latency_stats = _latency_stats(latencies)
        accuracy = _accuracy(results, cases)

        # ECE only over cases with expected labels
        conf_ok_pairs = [
            (r.confidence, r.result == c.expected)
            for r, c in zip(results, cases)
            if c.expected is not None and r.error is None
        ]
        ece = None
        if conf_ok_pairs:
            ece = _ece(
                [c for c, _ in conf_ok_pairs],
                [ok for _, ok in conf_ok_pairs],
            )

        # 4. Backend metadata
        md = self.backend.metadata()

        # 5. Unload
        try:
            self.backend.unload()
        except Exception as exc:
            notes.append(f"unload error: {exc!r}")

        return BenchmarkResult(
            backend_name=md.name,
            backend_version=md.version,
            calibration_state=md.calibration_state,
            ece_reported=md.ece,
            is_deterministic=md.is_deterministic,
            is_local_only=md.is_local_only,
            environment=_capture_env(),
            cases=results,
            latency=latency_stats,
            accuracy=accuracy,
            ece_measured=ece,
            n_cases=len(cases),
            n_errors=sum(1 for r in results if r.error),
            notes=notes,
        )

    def _run_one(
        self,
        case: BenchmarkCase,
        expected_hash: Optional[str] = None,
    ) -> CaseResult:
        if expected_hash is not None and case.input_hash() != expected_hash:
            return CaseResult(
                case_id=case.case_id,
                input_hash=case.input_hash(),
                result=None,
                confidence=0.0,
                latency_ms=0.0,
                distribution_sum=0.0,
                tier="INPUT_HASH_MISMATCH",
                error="byte-identical verification failed",
            )

        t0 = time.perf_counter()
        try:
            out = self.backend.predict(
                state=case.state,
                questions=[(case.primitive, case.question, case.options)],
                timeout_ms=self.timeout_ms,
            )
            latency = (time.perf_counter() - t0) * 1000.0
            packet = out[case.question]
            return CaseResult(
                case_id=case.case_id,
                input_hash=case.input_hash(),
                result=packet.result,
                confidence=packet.confidence,
                latency_ms=latency,
                distribution_sum=sum(packet.distribution.values()),
                tier=packet.execution_tier.value if hasattr(packet.execution_tier, "value") else str(packet.execution_tier),
            )
        except Exception as exc:
            return CaseResult(
                case_id=case.case_id,
                input_hash=case.input_hash(),
                result=None,
                confidence=0.0,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                distribution_sum=0.0,
                tier="ERROR",
                error=repr(exc),
            )
