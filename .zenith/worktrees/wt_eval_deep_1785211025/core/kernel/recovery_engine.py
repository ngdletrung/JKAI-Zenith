from enum import Enum
from typing import Dict, Any, List

class FailureType(str, Enum):
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    SCHEMA_VIOLATION = "SCHEMA_VIOLATION"
    SECURITY_VIOLATION = "SECURITY_VIOLATION"
    HALLUCINATION = "HALLUCINATION"
    CRITICAL_EXCEPTION = "CRITICAL_EXCEPTION"
    POLICY_FAILURE = "POLICY_FAILURE"
    NEURAL_LOOP = "NEURAL_LOOP"
    UNKNOWN = "UNKNOWN"

class RecoveryAction(str, Enum):
    RETRY_SAME = "RETRY_SAME"
    RETRY_INCREASE_TIMEOUT = "RETRY_INCREASE_TIMEOUT"
    TRIGGER_SURGERY = "TRIGGER_SURGERY"
    REPLAN = "REPLAN"
    QUARANTINE = "QUARANTINE"
    ABORT_AND_ROLLBACK = "ABORT_AND_ROLLBACK"

class RecoveryPolicyEngine:
    """
    🧠 Recovery Policy Engine (Self-Healing Router)
    Applies deterministic rules to classify failures and select the best recovery action.
    """
    
    @staticmethod
    def classify_failure(error_msg: str) -> FailureType:
        """🔍 Phân loại lỗi dựa trên nội dung thông báo lỗi."""
        if not error_msg:
            return FailureType.UNKNOWN
            
        err = error_msg.lower()
        if any(x in err for x in ["timeout", "deadline", "timed out", "timedout"]):
            return FailureType.TOOL_TIMEOUT
        if any(x in err for x in ["auth", "permission", "denied", "401", "403", "violation", "missing capability"]):
            return FailureType.SECURITY_VIOLATION
        if any(x in err for x in ["schema", "validation", "format", "missing", "invalid json", "parse"]):
            return FailureType.SCHEMA_VIOLATION
        if any(x in err for x in ["hallucinated", "not found", "no such tool", "not registered"]):
            return FailureType.HALLUCINATION
        if any(x in err for x in ["loop detected", "neural loop", "infinite recursion"]):
            return FailureType.NEURAL_LOOP
        if any(x in err for x in ["policy", "forbidden", "blacklist"]):
            return FailureType.POLICY_FAILURE
            
        return FailureType.CRITICAL_EXCEPTION

    @classmethod
    def determine_strategy(cls, failure_type: FailureType, attempt_count: int) -> RecoveryAction:
        """🎯 Áp dụng chính sách để lựa chọn chiến lược khôi phục."""
        # 1. Loop detected or Security violation -> Quarantine immediately! No retries.
        if failure_type in [FailureType.SECURITY_VIOLATION, FailureType.NEURAL_LOOP, FailureType.POLICY_FAILURE]:
            return RecoveryAction.QUARANTINE
            
        # 2. Too many retries -> Quarantine or Abort
        if attempt_count >= 3:
            if failure_type in [FailureType.TOOL_TIMEOUT, FailureType.CRITICAL_EXCEPTION]:
                return RecoveryAction.ABORT_AND_ROLLBACK
            return RecoveryAction.QUARANTINE
            
        # 3. Timeouts -> Retry with increased timeouts
        if failure_type == FailureType.TOOL_TIMEOUT:
            return RecoveryAction.RETRY_INCREASE_TIMEOUT
            
        # 4. Schema issues -> Trigger self-healing surgery (fix arguments)
        if failure_type == FailureType.SCHEMA_VIOLATION:
            return RecoveryAction.TRIGGER_SURGERY
            
        # 5. Hallucinated tools -> Replan
        if failure_type == FailureType.HALLUCINATION:
            return RecoveryAction.REPLAN
            
        # 6. Basic exceptions -> Just retry
        return RecoveryAction.RETRY_SAME
