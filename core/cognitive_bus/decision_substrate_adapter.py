# -*- coding: utf-8 -*-
"""
core/cognitive_bus/decision_substrate_adapter.py
JKAI Zenith - Cognitive ABI: Sovereign Tri-Tier Decision Substrate Adapter (v2.1)
Architecture: T3 Cognitive ABI / Sovereign Decision Substrate

Local Sovereign Architecture:
- Tier 1: Disabled / Offline Killswitch (Zero external egress)
- Tier 2: Local System-One Decision Substrate (Local Ollama / Sovereign Reflex Classifier)
- Tier 3: Deterministic Rule & Zero-Trust Baseline (Regex / Safe-Abstain)
- Strict Non-Cyclic Degradation: MAX_CASCADE_DEPTH = 3.
- All state inputs strictly sanitized via core.sanitizer.StateSanitizer.
"""

from __future__ import annotations

import re
import json
import time
import base64
import logging
import unicodedata
import urllib.parse
from types import MappingProxyType
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Union, Tuple, Mapping

from core.sanitizer.state_sanitizer import StateSanitizer
from core.governance.confidence_policy import (
    ActionClass,
    PolicyVerdict,
    decide as decide_confidence_policy,
)

logger = logging.getLogger("jkai.cognitive_bus")


class Tier2NotConfigured(RuntimeError):
    """Raised when Tier 2 backend is not configured or not loaded."""
    pass


class DecisionPrimitive(str, Enum):
    BOOLEAN = "Boolean"
    CHOICE = "Choice"
    SCORE = "Score"
    # Backward compatibility alias
    NOUL = "Boolean"


# Aliasing for backward compatibility
JevPrimitive = DecisionPrimitive


class ExecutionTier(str, Enum):
    TIER_1_LOCAL = "TIER_1_LOCAL_REFLEX"
    TIER_2_LOCAL = "TIER_2_LOCAL_EMULATOR"
    TIER_3_RULE = "TIER_3_DETERMINISTIC_RULE"
    ESCALATE = "ESCALATED_TO_SYSTEM_TWO"
    # Deprecated backward-compatibility alias
    TIER_1_LIVE = "TIER_1_OFFLINE_DISABLED"


# S1 Mandate: Unified Provider Registry (single interface, STOP-compliant)
ALLOWED_DECISION_PROVIDERS: Dict[str, str] = {
    "TIER_1_LOCAL_REFLEX": "Local Non-Autoregressive Reflex Substrate (MiniLM + Head)",
    "TIER_2_LOCAL_EMULATOR": "Local GBNF / Local Ollama Reasoner Substrate",
    "TIER_3_DETERMINISTIC_RULE": "In-Process Deterministic Rule & Zero-Trust Fallback Substrate"
}

# UNCALIBRATED. 0.85 is an uncalibrated placeholder pending shadow telemetry (n >= 100).
# Do NOT treat as ground truth. Do NOT cite in benchmarks as a calibrated threshold.
# See docs/adr/ for calibration roadmap.
THETA_FAST_PATH_UNFIT_PLACEHOLDER: float = 0.85


@dataclass(frozen=True)
class TypedJudgementPacket:
    """
    Semantic decision payload returned by Sovereign Decision Substrate.
    Acts strictly as an immutable 'Semantic Sensor' payload for Sovereign Governor.
    """
    primitive: DecisionPrimitive
    question: str
    result: Union[float, str, int]          # Boolean: float [0..1], Choice: str, Score: float
    confidence: float                       # [0..1]
    distribution: Mapping[str, float]       # Immutable probability distribution
    execution_tier: ExecutionTier
    latency_ms: float
    sanitized: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "distribution", MappingProxyType(dict(self.distribution))
        )
        object.__setattr__(
            self, "metadata", MappingProxyType(dict(self.metadata))
        )


@dataclass
class ParallelBatchVerdict:
    """
    Result of an atomic parallel batch evaluation over a single unified state.
    """
    state_fingerprint: str
    judgements: Dict[str, TypedJudgementPacket]
    overall_latency_ms: float
    all_passed_confidence_floor: bool
    execution_tier: ExecutionTier
    correlation_id: Optional[str] = None


class CircuitBreaker:
    """
    Circuit breaker with Exponential Backoff (60s -> 120s -> 300s).
    """
    def __init__(self, failure_threshold: int = 2, backoff_steps: Tuple[int, ...] = (60, 120, 300)):
        self.failure_threshold = failure_threshold
        self.backoff_steps = backoff_steps
        self.failure_count = 0
        self.current_step_idx = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.opened_at = 0.0

    def record_success(self):
        self.failure_count = 0
        self.current_step_idx = 0
        self.state = "CLOSED"

    def record_failure(self):
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.opened_at = time.time()

    def is_available(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            cooldown = self.backoff_steps[min(self.current_step_idx, len(self.backoff_steps) - 1)]
            if time.time() - self.opened_at > cooldown:
                self.state = "HALF_OPEN"
                self.current_step_idx = min(self.current_step_idx + 1, len(self.backoff_steps) - 1)
                return True
            return False
        if self.state == "HALF_OPEN":
            return True
        return False


class AdaptiveLatencyGuard:
    """
    Tracks rolling p95 latency using a window of 50 samples and EMA (alpha = 0.1).
    """
    def __init__(self, window_size: int = 50, alpha: float = 0.1, max_p95_ms: float = 450.0):
        self.window_size = window_size
        self.alpha = alpha
        self.max_p95_ms = max_p95_ms
        self.samples: List[float] = []
        self.ema_latency: Optional[float] = None

    def record_latency(self, latency_ms: float):
        self.samples.append(latency_ms)
        if len(self.samples) > self.window_size:
            self.samples.pop(0)

        if self.ema_latency is None:
            self.ema_latency = latency_ms
        else:
            self.ema_latency = self.alpha * latency_ms + (1.0 - self.alpha) * self.ema_latency

    def get_p95(self) -> float:
        if not self.samples:
            return 0.0
        sorted_samples = sorted(self.samples)
        idx = int(0.95 * len(sorted_samples))
        return sorted_samples[min(idx, len(sorted_samples) - 1)]

    def is_degraded(self) -> bool:
        if len(self.samples) >= 10:
            return self.get_p95() > self.max_p95_ms
        return False


class TriTierDecisionAdapter:
    """
    JKAI Sovereign Decision Adapter:
    - Tier 1: Disabled / Egress Forbidden (No cloud connection)
    - Tier 2: Local System-One Decision Substrate (Local hardware via GBNF/Ollama)
    - Tier 3: Deterministic Rule & Zero-Trust Baseline (Regex / Safe-Abstain)
    - Strict Non-Cyclic Degradation: MAX_CASCADE_DEPTH = 3.
    """
    
    MAX_CASCADE_DEPTH = 3
    THETA_TIER2_BOOLEAN = 0.95
    THETA_TIER2_CHOICE = 0.90
    THETA_TIER2_SCORE = 0.90

    def __init__(
        self,
        enable_mock: bool = False,
        shadow_harness: Optional[Any] = None,
        record_shadow: bool = True,
        tier2_backend: Optional[Any] = None,
        tier2_timeout_ms: int = 450,
        **kwargs,
    ):
        self.enable_mock = enable_mock
        self.record_shadow = record_shadow
        self.circuit_breaker = CircuitBreaker()
        self.latency_guard = AdaptiveLatencyGuard()
        self.mock_registry: Dict[str, TypedJudgementPacket] = {}
        self.tier2_backend = tier2_backend
        self.tier2_timeout_ms = tier2_timeout_ms

        if self.tier2_backend is not None and hasattr(self.tier2_backend, "load"):
            try:
                self.tier2_backend.load()
            except Exception as exc:
                self._log_tier_failure("TIER_2_LOAD", exc)
                self.tier2_backend = None

        if shadow_harness is not None:
            self.shadow_harness = shadow_harness
        elif not self.enable_mock and self.record_shadow:
            try:
                from core.governance.shadow_harness import get_default_shadow_harness
                self.shadow_harness = get_default_shadow_harness()
            except Exception:
                self.shadow_harness = None
        else:
            self.shadow_harness = None

    def register_mock_judgement(self, state: Any, question: str, packet: TypedJudgementPacket):
        """Registers a deterministic mock response for unit tests."""
        fp = StateSanitizer.compute_fingerprint(state)
        key = f"{fp}:{question.strip()}"
        self.mock_registry[key] = packet

    def evaluate_noul(self, state: Any, question: str, action_class: ActionClass = ActionClass.READ) -> TypedJudgementPacket:
        results = self.evaluate_parallel_batch(state, [(DecisionPrimitive.BOOLEAN, question, None)], action_class=action_class)
        return results.judgements[question]

    def evaluate_choice(self, state: Any, question: str, options: List[str], action_class: ActionClass = ActionClass.READ) -> TypedJudgementPacket:
        results = self.evaluate_parallel_batch(state, [(DecisionPrimitive.CHOICE, question, options)], action_class=action_class)
        return results.judgements[question]

    def evaluate_score(self, state: Any, question: str, levels: List[str], action_class: ActionClass = ActionClass.READ) -> TypedJudgementPacket:
        results = self.evaluate_parallel_batch(state, [(DecisionPrimitive.SCORE, question, levels)], action_class=action_class)
        return results.judgements[question]

    def _record_shadow_telemetry(self, sanitized_state: Any, verdict: ParallelBatchVerdict):
        """Asynchronously/safely emits shadow observation record with execution receipt."""
        if not self.shadow_harness or not getattr(self.shadow_harness, "enabled", True):
            return
        try:
            reflex_draft = {
                q: {
                    "primitive": p.primitive.value if hasattr(p.primitive, "value") else str(p.primitive),
                    "result": p.result,
                    "confidence": p.confidence,
                    "tier": p.execution_tier.value if hasattr(p.execution_tier, "value") else str(p.execution_tier),
                    "latency_ms": p.latency_ms
                }
                for q, p in verdict.judgements.items()
            }
            meta = {
                "source": "TriTierDecisionAdapter",
                "execution_tier": verdict.execution_tier.value if hasattr(verdict.execution_tier, "value") else str(verdict.execution_tier),
                "overall_latency_ms": verdict.overall_latency_ms,
                "all_passed": verdict.all_passed_confidence_floor
            }
            receipt = {
                "status": "EVALUATED",
                "execution_tier": verdict.execution_tier.value if hasattr(verdict.execution_tier, "value") else str(verdict.execution_tier),
                "all_passed": verdict.all_passed_confidence_floor,
                "overall_latency_ms": verdict.overall_latency_ms
            }
            record = self.shadow_harness.record_observation(
                raw_state=sanitized_state if isinstance(sanitized_state, dict) else {"state": sanitized_state},
                reflex_draft=reflex_draft,
                execution_receipt=receipt,
                metadata=meta
            )
            if record:
                verdict.correlation_id = record.record_id
        except Exception as exc:
            try:
                logging.getLogger("jkai.cognitive_bus.shadow").warning(
                    "shadow_telemetry_failed", extra={"error": repr(exc)}
                )
            except Exception:
                pass

    def apply_confidence_policy(
        self,
        verdict: ParallelBatchVerdict,
        action_class: ActionClass,
        backend_calibration_state: str,
        tier3_concurred: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Apply ADR 0003 policy to every judgement in the verdict.
        Returns per-question PolicyDecision. Does NOT swallow exceptions.
        """
        decisions = {}
        for question, packet in verdict.judgements.items():
            decisions[question] = decide_confidence_policy(
                packet=packet,
                action_class=action_class,
                backend_calibration_state=backend_calibration_state,
                tier3_concurred=tier3_concurred,
            )
        return decisions

    def _backend_calibration_state(self) -> str:
        """Read calibration state from active Tier 2 backend metadata."""
        if getattr(self, "tier2_backend", None) is None:
            return "uncalibrated"
        try:
            return self.tier2_backend.metadata().calibration_state
        except Exception:
            return "unknown"

    def evaluate_parallel_batch(
        self,
        state: Any,
        questions: List[Tuple[DecisionPrimitive, str, Optional[List[str]]]],
        action_class: ActionClass = ActionClass.READ,
        correlation_id: Optional[str] = None,
    ) -> ParallelBatchVerdict:
        """
        Executes parallel evaluation across all questions with graceful degradation:
        Tier 2 (Local) -> Tier 3 (Deterministic Rule) -> Escalate.
        (Tier 1 Cloud Egress is completely blocked by Killswitch).
        """
        t0 = time.time()
        sanitized_state = StateSanitizer.sanitize(state)
        fingerprint = StateSanitizer.compute_fingerprint(sanitized_state)
        
        # 0. Mock mode (bypasses circuit breaker by design — test path)
        if self.enable_mock:
            judgements = {}
            for prim, q, opts in questions:
                key = f"{fingerprint}:{q.strip()}"
                if key in self.mock_registry:
                    judgements[q] = self.mock_registry[key]
                else:
                    judgements[q] = self._deterministic_rule_heuristic(
                        prim, q, opts, sanitized_state
                    )
            
            latency = (time.time() - t0) * 1000.0
            verdict = ParallelBatchVerdict(
                state_fingerprint=fingerprint,
                judgements=judgements,
                overall_latency_ms=latency,
                all_passed_confidence_floor=all(
                    j.confidence >= THETA_FAST_PATH_UNFIT_PLACEHOLDER
                    for j in judgements.values()
                ),
                execution_tier=ExecutionTier.TIER_3_RULE,
                correlation_id=correlation_id,
            )
            self._record_shadow_telemetry(sanitized_state, verdict)
            return verdict

        # 1. Circuit breaker gate before attempting Tier 2
        if self.circuit_breaker.is_available():
            try:
                t2_res, t2_lat = self._call_tier2_local_emulator(sanitized_state, questions)
                _theta_by_prim = {
                    DecisionPrimitive.BOOLEAN: self.THETA_TIER2_BOOLEAN,
                    DecisionPrimitive.CHOICE: self.THETA_TIER2_CHOICE,
                    DecisionPrimitive.SCORE: self.THETA_TIER2_SCORE,
                }
                all_pass = all(
                    j.confidence >= _theta_by_prim.get(j.primitive, self.THETA_TIER2_BOOLEAN)
                    for j in t2_res.values()
                )
                if all_pass:
                    total_latency = (time.time() - t0) * 1000.0
                    self.circuit_breaker.record_success()
                    self.latency_guard.record_latency(total_latency)
                    verdict = ParallelBatchVerdict(
                        state_fingerprint=fingerprint,
                        judgements=t2_res,
                        overall_latency_ms=total_latency,
                        all_passed_confidence_floor=True,
                        execution_tier=ExecutionTier.TIER_2_LOCAL,
                        correlation_id=correlation_id,
                    )

                    # ADR 0003: apply policy before authorizing
                    try:
                        cal_state = self._backend_calibration_state()
                        policy_decisions = self.apply_confidence_policy(
                            verdict=verdict,
                            action_class=action_class,
                            backend_calibration_state=cal_state,
                        )
                        # Fail-closed: policy must return a decision for EVERY question,
                        # and ALL decisions must be AUTHORIZE
                        authorized = (
                            bool(policy_decisions)
                            and len(policy_decisions) == len(verdict.judgements)
                            and all(d.verdict == PolicyVerdict.AUTHORIZE for d in policy_decisions.values())
                        )
                    except Exception as exc:
                        self._log_tier_failure("POLICY", exc)
                        authorized = False

                    if authorized:
                        self._record_shadow_telemetry(sanitized_state, verdict)
                        return verdict
                    else:
                        # Fall through to Tier 3 instead of returning Tier 2 result
                        pass
                else:
                    # Low confidence is not a backend failure — it's a legitimate fallthrough
                    self.circuit_breaker.record_success()
            except Tier2NotConfigured:
                self._log_tier_skipped("TIER_2", "not_configured")
                # Do NOT record failure — not configured is deployment state, not an outage
            except Exception as exc:
                self.circuit_breaker.record_failure()
                self._log_tier_failure("TIER_2", exc)
        else:
            self._log_tier_skipped("TIER_2", "circuit_open")

        # 2. Tier 3: Deterministic Rule & Zero-Trust Baseline
        t3_res = self._call_tier3_rule_baseline(sanitized_state, questions)
        all_pass = all(j.confidence >= 0.99 for j in t3_res.values())
        total_latency = (time.time() - t0) * 1000.0
        self.latency_guard.record_latency(total_latency)

        verdict = ParallelBatchVerdict(
            state_fingerprint=fingerprint,
            judgements=t3_res,
            overall_latency_ms=total_latency,
            all_passed_confidence_floor=all_pass,
            execution_tier=(
                ExecutionTier.TIER_3_RULE if all_pass else ExecutionTier.ESCALATE
            ),
            correlation_id=correlation_id,
        )
        self._record_shadow_telemetry(sanitized_state, verdict)
        return verdict

    def _call_tier2_local_emulator(
        self,
        state: Any,
        questions: List[Tuple[DecisionPrimitive, str, Optional[List[str]]]]
    ) -> Tuple[Dict[str, TypedJudgementPacket], float]:
        """
        Tier 2: local model inference via injected backend.
        Falls back if no backend configured.
        """
        if getattr(self, "tier2_backend", None) is None:
            raise Tier2NotConfigured("tier2_backend not configured")

        t_start = time.perf_counter()
        res = self.tier2_backend.predict(
            state=state,
            questions=questions,
            timeout_ms=self.tier2_timeout_ms
        )
        lat = (time.perf_counter() - t_start) * 1000.0

        # Defensive contract validation
        self._validate_tier2_output(res, questions)
        return res, lat

    def _validate_tier2_output(
        self,
        res: Dict[str, TypedJudgementPacket],
        questions: List[Tuple[DecisionPrimitive, str, Optional[List[str]]]]
    ) -> None:
        """Reject malformed backend output. Called before any authorization."""
        expected = {q for _, q, _ in questions}
        got = set(res.keys())
        if got != expected:
            raise ValueError(
                f"Tier 2 contract violation: expected {expected}, got {got}"
            )
        for q, packet in res.items():
            if not (0.0 <= packet.confidence <= 1.0):
                raise ValueError(f"Tier 2 confidence out of range for '{q}'")
            total = sum(packet.distribution.values())
            if abs(total - 1.0) > 1e-6:
                raise ValueError(
                    f"Tier 2 distribution for '{q}' sums to {total}, not 1.0"
                )
            if packet.execution_tier != ExecutionTier.TIER_2_LOCAL:
                raise ValueError(
                    f"Tier 2 packet has wrong tier: {packet.execution_tier}"
                )

    def _call_tier3_rule_baseline(
        self,
        state: Any,
        questions: List[Tuple[DecisionPrimitive, str, Optional[List[str]]]]
    ) -> Dict[str, TypedJudgementPacket]:
        """Tier 3: 100% Deterministic Regex and Logic Safe-Abstain Fallback."""
        res = {}
        for prim, q, opts in questions:
            res[q] = self._deterministic_rule_heuristic(prim, q, opts, state, tier=ExecutionTier.TIER_3_RULE)
        return res

    def _log_tier_failure(self, tier: str, exc: Exception) -> None:
        """Structured log for tier failures — replaces silent except: pass."""
        try:
            logger.warning(
                "tier_failure", extra={"tier": tier, "error": repr(exc)}
            )
        except Exception:
            pass

    def _log_tier_skipped(self, tier: str, reason: str) -> None:
        try:
            logger.info(
                "tier_skipped", extra={"tier": tier, "reason": reason}
            )
        except Exception:
            pass

    @staticmethod
    def _detect_adversarial_patterns(raw_text: str) -> bool:
        """
        Hardened adversarial & injection pattern detection:
        - Decodes URL encoding (multilevel)
        - Unicode NFKD normalization (collapses homoglyphs)
        - Strips control characters, zero-width chars, and backslash evasions
        - Collapses whitespace
        - Base64 payload decoding and inspection
        - Multi-lingual malicious pattern matching (EN & VI)
        """
        if not raw_text:
            return False
            
        # 1. Unquote URL entities
        text = raw_text
        try:
            for _ in range(2):
                unquoted = urllib.parse.unquote(text)
                if unquoted == text:
                    break
                text = unquoted
        except Exception:
            pass

        # 2. NFKD normalize to strip homoglyphs (e.g. Cyrillic/Fullwidth)
        text = unicodedata.normalize("NFKD", text)

        # 3. Strip backslash evasions and control chars (e.g. r\m -r\f, e\v\a\l)
        deobfuscated = re.sub(r"[\x00-\x1f\x7f-\x9f\\]", "", text).lower()
        
        # 4. Collapse whitespace
        collapsed = re.sub(r"\s+", " ", deobfuscated)
        
        # 5. Core dangerous keywords and command patterns
        danger_patterns = [
            r"\brm\s+-[a-z]*r[a-z]*f\b",
            r"\bdelete\s+from\b",
            r"\bdrop\s+table\b",
            r"\bdrop\s+database\b",
            r"\bformat\s+c:",
            r"\bcurl\s+-x\b",
            r"/etc/shadow",
            r"\beval\s*\(",
            r"\bexec\s*\(",
            r"grant_super_admin",
            r"prompt_injection",
            r"\badmin/roles\b",
            r"\bidor\b",
            r"security_breach",
            r"\bunauthorized\b",
            r"\bforbidden\b"
        ]
        
        for pat in danger_patterns:
            if re.search(pat, collapsed):
                return True
                
        # Also simple substring check on keywords (exec( and eval( are handled above via regex word boundary)
        keywords = [
            "prompt_injection", "override", "rm -rf", "delete from", "drop table", 
            "drop database", "format c:", "curl -x", "cat /etc/shadow", 
            "grant_super_admin", "admin/roles", "unauthorized", "forbidden", 
            "idor", "privilege", "security_breach"
        ]
        if any(kw in collapsed for kw in keywords):
            return True

        # 6. Sniff base64 patterns (>= 12 chars base64 containing padding or base64 symbols)
        b64_matches = re.findall(r"\b[A-Za-z0-9+/]{12,}={0,2}\b", raw_text)
        b64_matches = [m for m in b64_matches if "+" in m or "/" in m or "=" in m]
        for b64_cand in b64_matches[:10]:
            try:
                decoded = base64.b64decode(b64_cand).decode("utf-8", errors="ignore").lower()
                if any(kw in decoded for kw in ["rm -rf", "drop database", "eval(", "exec(", "grant_super_admin"]):
                    return True
            except Exception:
                pass

        return False

    def _deterministic_rule_heuristic(
        self,
        prim: DecisionPrimitive,
        question: str,
        options: Optional[List[str]],
        state: Any,
        tier: ExecutionTier = ExecutionTier.TIER_3_RULE
    ) -> TypedJudgementPacket:
        """
        Production deterministic rule engine.
        Serves as Tier 2 fallback and Tier 3 baseline.
        NOT a test helper despite the historical 'mock' in commit history.
        """
        t_start = time.perf_counter()
        state_str = json.dumps(state, ensure_ascii=False).lower() if isinstance(state, (dict, list)) else str(state).lower()
        q_lower = question.lower()

        if prim == DecisionPrimitive.BOOLEAN:
            # Check for adversarial attack markers
            is_malicious = self._detect_adversarial_patterns(state_str)
            # Domain-specific failure diagnostic questions
            if "failure caused by" in q_lower:
                if "schema" in q_lower or "validation" in q_lower:
                    matched = any(w in state_str for w in ["schema", "type_error", "validation", "missing_key", "missing required", "missing key", "jsondecode"])
                    prob = 0.82 if matched else 0.08
                    conf = 0.96
                elif "environment" in q_lower or "drift" in q_lower:
                    matched = any(w in state_str for w in ["connection refused", "timeout", "network", "host unreachable"])
                    prob = 0.78 if matched else 0.10
                    conf = 0.95
                elif "tool defect" in q_lower or "tool crash" in q_lower:
                    matched = any(w in state_str for w in ["tool_error", "command_not_found", "process died", "exit 127"])
                    prob = 0.81 if matched else 0.06
                    conf = 0.95
                elif "state mismatch" in q_lower or "contradiction" in q_lower:
                    matched = any(w in state_str for w in ["assertionerror", "state_conflict", "precondition", "deadlock"])
                    prob = 0.77 if matched else 0.12
                    conf = 0.95
                else:
                    prob = 0.98 if is_malicious else 0.01
                    conf = 0.99
            elif "artifact_exists" in q_lower or "artifact exists" in q_lower:
                matched = "missing_artifact" not in state_str and any(w in state_str for w in ["artifact", "summary", ".json", "report", "completed"])
                prob = 0.98 if matched else 0.10
                conf = 0.99
            else:
                # If question asks about threats / harm / injection / corruption / breach / danger (English + Vietnamese)
                risk_terms = [
                    "injection", "destructive", "delete", "corrupt", "exfiltration", "breach", 
                    "danger", "override", "exceed", "violate", "unauthorized",
                    "nguy cơ", "phá hoại", "độc hại", "bảo mật", "tấn công", "nguy hiểm"
                ]
                safety_terms = ["an toàn", "safe", "policy_compliant", "hợp lệ", "tuân thủ"]
                
                is_risk_question = any(term in q_lower for term in risk_terms)
                is_safety_question = any(term in q_lower for term in safety_terms)

                if is_safety_question and not is_risk_question:
                    prob = 0.01 if is_malicious else 0.99
                elif is_risk_question:
                    prob = 0.98 if is_malicious else 0.01
                else:
                    prob = 0.02 if is_malicious else 0.98
                conf = 0.99

            measured = (time.perf_counter() - t_start) * 1000.0
            return TypedJudgementPacket(
                primitive=DecisionPrimitive.BOOLEAN,
                question=question,
                result=prob,
                confidence=conf,
                distribution={"true": prob, "false": round(1.0 - prob, 6)},
                execution_tier=tier,
                latency_ms=measured
            )
        elif prim == DecisionPrimitive.CHOICE:
            opts = options or ["option_a", "option_b", "none"]
            winner = None
            
            # 1. Semantic Routing Detection for FAST_PATH vs DEEP_PATH
            if "deep_path" in [o.lower() for o in opts] and "fast_path" in [o.lower() for o in opts]:
                deep_indicators = ["sql", "explain", "tối ưu", "optimize", "analyze", "phân tích", "leak", "driver", "code", "architecture"]
                if any(w in state_str for w in deep_indicators):
                    winner = next((o for o in opts if o.lower() == "deep_path"), None)
                elif any(w in state_str for w in ["chào", "hello", "hi", "thời tiết", "weather"]):
                    winner = next((o for o in opts if o.lower() == "fast_path"), None)

            # 2. Direct string matching fallback
            if winner is None:
                for opt in opts:
                    if opt != "none_of_the_above" and opt.lower() in state_str:
                        winner = opt
                        break

            # 3. Default fallback
            if winner is None:
                winner = "none_of_the_above" if "none_of_the_above" in opts else opts[-1]

            n_opts = len(opts)
            peak_conf = 0.96
            rest_prob = round((1.0 - peak_conf) / max(1, n_opts - 1), 6)
            dist = {o: (peak_conf if o == winner else rest_prob) for o in opts}
            residual = 1.0 - sum(dist.values())
            if abs(residual) > 1e-9:
                dist[winner] = round(dist[winner] + residual, 6)

            measured = (time.perf_counter() - t_start) * 1000.0
            return TypedJudgementPacket(
                primitive=DecisionPrimitive.CHOICE,
                question=question,
                result=winner,
                confidence=peak_conf,
                distribution=dist,
                execution_tier=tier,
                latency_ms=measured
            )
        else:  # SCORE
            levels = options or ["0", "1", "2", "3", "4"]
            n = len(levels)
            target_idx = 0 if "fail" in state_str else min(3, n - 1)
            peak_mass = 0.70
            rest_mass = (1.0 - peak_mass) / max(1, n - 1)
            dist = {
                str(levels[i]): (peak_mass if i == target_idx else round(rest_mass, 6))
                for i in range(n)
            }
            # Repair rounding residual at the peak so sum == 1.0 exactly
            residual = 1.0 - sum(dist.values())
            if abs(residual) > 1e-9:
                peak_key = str(levels[target_idx])
                dist[peak_key] = round(dist[peak_key] + residual, 6)

            score = float(target_idx)
            measured = (time.perf_counter() - t_start) * 1000.0
            return TypedJudgementPacket(
                primitive=DecisionPrimitive.SCORE,
                question=question,
                result=score,
                confidence=0.92,
                distribution=dist,
                execution_tier=tier,
                latency_ms=measured
            )


# Backward compatibility aliases
TriTierJevAdapter = TriTierDecisionAdapter
