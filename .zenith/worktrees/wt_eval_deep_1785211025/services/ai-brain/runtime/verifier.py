from dataclasses import dataclass
from typing import List

@dataclass(frozen=True)
class VerifierResult:
    valid: bool
    confidence: float
    violations: List[str]

class VerifierLayer:
    """
    👁️ Thần Nhãn - Verifier Layer (Chống Hallucination & Prompt Injection)
    Mọi Output từ Tool/Planner đều phải qua đây rà soát trước khi Commit.
    """
    def __init__(self):
        pass

    def verify_tool_output(self, tool_name: str, output: str) -> VerifierResult:
        violations = []
        
        # 1. Entropy / Anomaly Detection
        if len(output) > 10000:
            violations.append("Output entropy too high (payload explosion risk)")
            
        # 2. Jailbreak Check (đơn giản)
        suspicious = ["ignore all previous", "system prompt", "bypass"]
        if any(s in output.lower() for s in suspicious):
            violations.append("Suspected prompt injection payload in tool output")
            
        # 3. Semantic / Schema Match (Sẽ ráp Pydantic vào đây sau)
        
        is_valid = len(violations) == 0
        return VerifierResult(
            valid=is_valid,
            confidence=1.0 if is_valid else 0.0,
            violations=violations
        )
