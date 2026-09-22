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
