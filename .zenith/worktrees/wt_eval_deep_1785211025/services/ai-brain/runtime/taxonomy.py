from dataclasses import dataclass

@dataclass(frozen=True)
class Failure:
    """
    🚨 Khái Niệm Lỗi Chuẩn Mực (Advanced Failure Taxonomy)
    Không dùng Enum. Failure phải mang ngữ cảnh để Runtime biết cách phục hồi.
    """
    code: str
    category: str
    severity: str          # LOW, HIGH, CRITICAL
    recoverability: str    # FULL, PARTIAL, NONE
    retryable: bool
    trust_impact: float    # 0.0 -> 1.0 (Giảm điểm tin cậy của Agent/Tool)
    quarantine_scope: str  # planner, memory, tool, all

class FailureTaxonomy:
    # Các lỗi liên quan đến Planner (LLM)
    SEMANTIC_DRIFT = Failure("SEMANTIC_DRIFT", "PLANNER", "HIGH", "PARTIAL", False, 0.35, "planner")
    PLANNER_HALLUCINATION = Failure("PLANNER_HALLUCINATION", "PLANNER", "CRITICAL", "NONE", False, 0.8, "planner")
    
    # Các lỗi liên quan đến Policy / Security
    POLICY_DENIAL = Failure("POLICY_DENIAL", "SECURITY", "HIGH", "NONE", False, 0.5, "all")
    CAPABILITY_VIOLATION = Failure("CAPABILITY_VIOLATION", "SECURITY", "CRITICAL", "NONE", False, 0.9, "all")
    
    # Các lỗi liên quan đến Thực thi (Sandbox)
    RUNTIME_TIMEOUT = Failure("RUNTIME_TIMEOUT", "EXECUTION", "LOW", "FULL", True, 0.1, "tool")
    SANDBOX_KILL = Failure("SANDBOX_KILL", "EXECUTION", "HIGH", "NONE", False, 0.2, "tool")
    
    # Các lỗi liên quan đến Memory
    MEMORY_CONFLICT = Failure("MEMORY_CONFLICT", "MEMORY", "HIGH", "PARTIAL", True, 0.0, "memory")
