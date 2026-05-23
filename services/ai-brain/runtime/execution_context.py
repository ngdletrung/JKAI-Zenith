from dataclasses import dataclass
from typing import Tuple

class MemoryZone:
    WORKING = "WORKING"
    EPISODIC = "EPISODIC"
    LONG_TERM = "LONG_TERM"
    SECURITY = "SECURITY"
    SYSTEM = "SYSTEM"

@dataclass(frozen=True)
class MemoryCapability:
    read_zones: Tuple[str, ...]
    write_zones: Tuple[str, ...]

@dataclass(frozen=True)
class ExecutionProposal:
    """
    📝 Bản Đề Xuất (Tước quyền của LLM)
    LLM chỉ được quyền nộp bản này, Runtime mới là kẻ duyệt lệnh.
    """
    trace_id: str
    proposed_steps: Tuple[dict, ...] # DAG ý định
    reasoning: str
    estimated_risk: str
