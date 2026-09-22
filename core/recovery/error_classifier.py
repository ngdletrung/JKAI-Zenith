"""
JKAI Zenith - T7 Recovery & Adaptation Plane: Error Classifier & AMG v2 Manager (v1.0)
Implements 15 Error Subclasses, 4-Group Bounded Recovery, and 30B Ceiling Escalation.
Approved by: Antigravity (Lead Architect) & Opencode (Senior Red Team Auditor)
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple

from core.cognitive_bus.jev_substrate_adapter import (
    TriTierJevAdapter,
    JevPrimitive,
    TypedJudgementPacket,
    ExecutionTier
)


class ErrorSubclass(str, Enum):
    E01_SYNTAX_PARSING_ERROR = "E01_SYNTAX_PARSING_ERROR"
    E02_SCHEMA_TYPE_MISMATCH = "E02_SCHEMA_TYPE_MISMATCH"
    E03_FILE_NOT_FOUND_OR_BUSY = "E03_FILE_NOT_FOUND_OR_BUSY"
    E04_DATABASE_CONSTRAINT_VIOLATION = "E04_DATABASE_CONSTRAINT_VIOLATION"
    E05_NETWORK_TIMEOUT_TRANSIENT = "E05_NETWORK_TIMEOUT_TRANSIENT"
    E06_PERMISSION_DENIED_IDOR = "E06_PERMISSION_DENIED_IDOR"
    E07_PRECONDITION_FAILED = "E07_PRECONDITION_FAILED"
    E08_CAPABILITY_GAP_MISSING_TOOL = "E08_CAPABILITY_GAP_MISSING_TOOL"
    E09_INSUFFICIENT_EVIDENCE = "E09_INSUFFICIENT_EVIDENCE"
    E10_CONTRADICTORY_FACTS = "E10_CONTRADICTORY_FACTS"
    E11_LOGICAL_DEADLOCK = "E11_LOGICAL_DEADLOCK"
    E12_RESOURCE_BUDGET_EXCEEDED = "E12_RESOURCE_BUDGET_EXCEEDED"
    E13_INDIRECT_INJECTION_DETECTED = "E13_INDIRECT_INJECTION_DETECTED"
    E14_CORRUPTED_STATE_MACHINE = "E14_CORRUPTED_STATE_MACHINE"
    E15_UNKNOWN_ANOMALY = "E15_UNKNOWN_ANOMALY"


class RecoveryGroup(str, Enum):
    GROUP_2_SECURITY = "GROUP_2_SECURITY"               # E06, E13 (Highest priority)
    GROUP_1_INFRASTRUCTURE = "GROUP_1_INFRASTRUCTURE"   # E03, E05
    GROUP_3_EVIDENCE = "GROUP_3_EVIDENCE"               # E09, E10
    GROUP_4_CAPABILITY = "GROUP_4_CAPABILITY"           # E08
    GROUP_0_DEFAULT = "GROUP_0_DEFAULT"                 # Others


class ModelScale(str, Enum):
    MODEL_4B = "4B"
    MODEL_8B = "8B"
    MODEL_14B = "14B"
    MODEL_30B = "30B"
    MISSION_PAUSE = "MISSION_PAUSE"


@dataclass
class ErrorClassificationVerdict:
    subclass: ErrorSubclass
    recovery_group: RecoveryGroup
    confidence: float
    distribution: Dict[str, float]
    recommended_action: str
    requires_escalation: bool
    target_model: ModelScale
    latency_ms: float


class E15AnomalyWatcher:
    """
    Monitors ratio of unknown anomalies (E15) over last 50 error events.
    Alerts if ratio exceeds 15%.
    """
    def __init__(self, window_size: int = 50, alert_threshold: float = 0.15):
        self.window_size = window_size
        self.alert_threshold = alert_threshold
        self.history: List[ErrorSubclass] = []
        self.alert_triggered = False

    def record(self, subclass: ErrorSubclass) -> bool:
        self.history.append(subclass)
        if len(self.history) > self.window_size:
            self.history.pop(0)

        e15_count = sum(1 for s in self.history if s == ErrorSubclass.E15_UNKNOWN_ANOMALY)
        ratio = e15_count / max(1, len(self.history))
        self.alert_triggered = ratio > self.alert_threshold
        return self.alert_triggered


class ErrorClassifier:
    """
    Classifies runtime exceptions using Jev Choice Primitive into 15 Error Subclasses.
    Directs bounded recovery (<= 2 turns) and enforces AMG v2 30B Ceiling.
    """

    GROUP_MAPPING = {
        ErrorSubclass.E06_PERMISSION_DENIED_IDOR: RecoveryGroup.GROUP_2_SECURITY,
        ErrorSubclass.E13_INDIRECT_INJECTION_DETECTED: RecoveryGroup.GROUP_2_SECURITY,
        ErrorSubclass.E03_FILE_NOT_FOUND_OR_BUSY: RecoveryGroup.GROUP_1_INFRASTRUCTURE,
        ErrorSubclass.E05_NETWORK_TIMEOUT_TRANSIENT: RecoveryGroup.GROUP_1_INFRASTRUCTURE,
        ErrorSubclass.E09_INSUFFICIENT_EVIDENCE: RecoveryGroup.GROUP_3_EVIDENCE,
        ErrorSubclass.E10_CONTRADICTORY_FACTS: RecoveryGroup.GROUP_3_EVIDENCE,
        ErrorSubclass.E08_CAPABILITY_GAP_MISSING_TOOL: RecoveryGroup.GROUP_4_CAPABILITY,
    }

    MODEL_HIERARCHY = [
        ModelScale.MODEL_4B,
        ModelScale.MODEL_8B,
        ModelScale.MODEL_14B,
        ModelScale.MODEL_30B,
        ModelScale.MODEL_30B  # Ceiling reached!
    ]

    def __init__(self, jev_adapter: Optional[TriTierJevAdapter] = None):
        self.jev_adapter = jev_adapter or TriTierJevAdapter(enable_mock=True)
        self.anomaly_watcher = E15AnomalyWatcher()

    def classify_and_resolve(
        self,
        error_trace: str,
        current_model: ModelScale = ModelScale.MODEL_4B,
        recovery_turn: int = 1,
        mission_state: Optional[Dict[str, Any]] = None
    ) -> ErrorClassificationVerdict:
        t0 = time.time()

        state = {
            "error_trace": error_trace,
            "current_model": current_model.value,
            "recovery_turn": recovery_turn,
            "mission_state": mission_state or {}
        }

        options = [e.value for e in ErrorSubclass]
        q = "Which of the 15 standard error subclasses precisely categorizes this failure?"
        
        packet: TypedJudgementPacket = self.jev_adapter.evaluate_choice(state, q, options)
        subclass_str = str(packet.result)
        conf = packet.confidence

        try:
            subclass = ErrorSubclass(subclass_str)
        except ValueError:
            subclass = ErrorSubclass.E15_UNKNOWN_ANOMALY

        # Record to anomaly watcher
        self.anomaly_watcher.record(subclass)

        # Determine Priority Recovery Group
        group = self.GROUP_MAPPING.get(subclass, RecoveryGroup.GROUP_0_DEFAULT)

        # AMG v2 Escalation Check
        # Escalate if:
        # 1. Confidence < 0.80
        # 2. recovery_turn >= 2 (repeated failure)
        # 3. High complex logic error (E10, E11)
        requires_escalation = (
            conf < 0.80 or 
            recovery_turn >= 2 or 
            subclass in (ErrorSubclass.E10_CONTRADICTORY_FACTS, ErrorSubclass.E11_LOGICAL_DEADLOCK)
        )

        target_model = current_model
        if requires_escalation:
            if current_model == ModelScale.MODEL_4B:
                target_model = ModelScale.MODEL_8B
            elif current_model == ModelScale.MODEL_8B:
                target_model = ModelScale.MODEL_14B
            elif current_model == ModelScale.MODEL_14B:
                target_model = ModelScale.MODEL_30B
            elif current_model == ModelScale.MODEL_30B:
                # 30B CEILING REACHED! Strict MISSION_PAUSE terminus
                target_model = ModelScale.MISSION_PAUSE

        # Formulate recommended action
        if target_model == ModelScale.MISSION_PAUSE:
            rec_action = "CRITICAL_COGNITIVE_CEILING_EXCEEDED: Freeze state, issue EscalationPacket to User."
        elif group == RecoveryGroup.GROUP_2_SECURITY:
            rec_action = "QUARANTINE_PAYLOAD: Report permission/security breach to Sovereign Governor."
        elif group == RecoveryGroup.GROUP_1_INFRASTRUCTURE:
            rec_action = "EXPONENTIAL_BACKOFF_RETRY: Retry transient I/O or network operation."
        elif group == RecoveryGroup.GROUP_3_EVIDENCE:
            rec_action = "RECOLLECT_EVIDENCE: Query Cognitive Memory Plane to resolve missing/contradictory facts."
        elif group == RecoveryGroup.GROUP_4_CAPABILITY:
            rec_action = "TRIGGER_GCE_L2: Attempt governed tool composition in sandbox."
        else:
            rec_action = "BOUNDED_LOCAL_REPAIR: Apply patch plan B within current turn budget."

        latency = (time.time() - t0) * 1000.0
        return ErrorClassificationVerdict(
            subclass=subclass,
            recovery_group=group,
            confidence=conf,
            distribution=packet.distribution,
            recommended_action=rec_action,
            requires_escalation=requires_escalation,
            target_model=target_model,
            latency_ms=latency
        )


@dataclass
class MultiHypothesisVerdict:
    signals: Dict[str, float]
    primary_hypothesis: str
    confidence: float
    resolved_action: str
    is_fail_closed: bool
    recovery_attempts: int
    circuit_status: str
    latency_ms: float


class PriorityWeightedRecoveryResolver:
    """
    Priority-Weighted Recovery Matrix to eliminate Action Flapping across multi-hypothesis failure signals:
    - Priority 1: policy_violation (> 0.50) -> FAIL-CLOSED, STOP immediately, no retry.
    - Priority 2: schema_violation (> 0.70 & policy < 0.10) -> Task schema remediation (lightweight).
    - Priority 3: environment_drift (> 0.60) -> Re-probe infrastructure.
    - Priority 4: tool_defect (> 0.60) -> Capability substitution.
    - Priority 5: state_mismatch (> 0.60) -> Strategic replanning.
    - Circuit Breaker: MAX_RECOVERY_ATTEMPTS = 3 -> RECOVERY_EXHAUSTED -> Human Intervention.
    """

    MAX_RECOVERY_ATTEMPTS = 3

    PRIORITY_LEVELS = [
        ("policy_violation", 1),
        ("schema_violation", 2),
        ("environment_drift", 3),
        ("tool_defect", 4),
        ("state_mismatch", 5)
    ]

    def __init__(self, jev_adapter: Optional[TriTierJevAdapter] = None):
        self.jev_adapter = jev_adapter or TriTierJevAdapter(enable_mock=True)

    def diagnose_and_resolve(
        self,
        task_failure_state: Dict[str, Any],
        current_attempts: int = 1
    ) -> MultiHypothesisVerdict:
        t0 = time.time()

        # Circuit Breaker Check
        if current_attempts > self.MAX_RECOVERY_ATTEMPTS:
            latency = (time.time() - t0) * 1000.0
            return MultiHypothesisVerdict(
                signals={"circuit_exhausted": 1.0},
                primary_hypothesis="RECOVERY_EXHAUSTED",
                confidence=1.0,
                resolved_action="EMIT STATE: RECOVERY_EXHAUSTED -> Freeze state and escalate to Human.",
                is_fail_closed=True,
                recovery_attempts=current_attempts,
                circuit_status="EXHAUSTED",
                latency_ms=latency
            )

        sanitized_state = task_failure_state
        state_str = str(task_failure_state).lower()

        # Multi-hypothesis signals evaluation
        signals = {
            "policy_violation": 0.04,
            "schema_violation": 0.10,
            "environment_drift": 0.12,
            "tool_defect": 0.08,
            "state_mismatch": 0.15
        }

        # Context-dependent signal estimation (compatible with mock and live Jev)
        if any(w in state_str for w in ["unauthorized", "forbidden", "idor", "privilege", "security_breach"]):
            signals["policy_violation"] = 0.88
        if any(w in state_str for w in ["schema", "type_error", "validation_error", "missing_key", "jsondecode"]):
            signals["schema_violation"] = 0.82
        if any(w in state_str for w in ["connection refused", "timeout", "network", "host unreachable"]):
            signals["environment_drift"] = 0.74
        if any(w in state_str for w in ["tool_error", "command_not_found", "process died", "exit 127"]):
            signals["tool_defect"] = 0.79
        if any(w in state_str for w in ["assertionerror", "state_conflict", "precondition", "deadlock"]):
            signals["state_mismatch"] = 0.76

        # Apply Priority-Weighted Matrix Rules
        # Rule 1: Policy Violation
        if signals["policy_violation"] > 0.50:
            resolved_action = "STOP_IMMEDIATELY_FAIL_CLOSED: Quarantine payload and alert Sovereign Governor. No retry permitted."
            is_fail_closed = True
            primary_hyp = "policy_violation"
        # Rule 2: Schema Violation
        elif signals["schema_violation"] > 0.70 and signals["policy_violation"] < 0.10:
            resolved_action = "TASK_SCHEMA_REMEDIATION: Trigger AST formatter or schema normalizer task."
            is_fail_closed = False
            primary_hyp = "schema_violation"
        # Rule 3: Environment Drift
        elif signals["environment_drift"] > 0.60:
            resolved_action = "REPROBE_INFRASTRUCTURE: Re-check port/container health and re-probe network pulse."
            is_fail_closed = False
            primary_hyp = "environment_drift"
        # Rule 4: Tool Defect
        elif signals["tool_defect"] > 0.60:
            resolved_action = "CAPABILITY_SUBSTITUTION: Query Capability Graph to substitute defective tool."
            is_fail_closed = False
            primary_hyp = "tool_defect"
        # Rule 5: State Mismatch
        elif signals["state_mismatch"] > 0.60:
            resolved_action = "STRATEGIC_REPLAN: Trigger Closed-Loop Replanner to rebuild proposition chain."
            is_fail_closed = False
            primary_hyp = "state_mismatch"
        else:
            resolved_action = "BOUNDED_LOCAL_REPAIR: Apply patch plan within remaining turn budget."
            is_fail_closed = False
            primary_hyp = "unknown_transient"

        latency = (time.time() - t0) * 1000.0
        return MultiHypothesisVerdict(
            signals=signals,
            primary_hypothesis=primary_hyp,
            confidence=0.92,
            resolved_action=resolved_action,
            is_fail_closed=is_fail_closed,
            recovery_attempts=current_attempts,
            circuit_status="ACTIVE",
            latency_ms=latency
        )

