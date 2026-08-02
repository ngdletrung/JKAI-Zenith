# Improvement actions từ Critic
IMPROVEMENT_CONTINUE = "continue"
IMPROVEMENT_RETRY = "retry"
IMPROVEMENT_REPLAN = "replan"
IMPROVEMENT_ESCALATE = "escalate"

# Task Status
STATUS_PENDING = "pending"
STATUS_PLANNING = "planning"
STATUS_EXECUTING = "executing"
STATUS_CRITICIZING = "criticizing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_NEEDS_REPLAN = "needs_replan"

# Valid improvement actions
VALID_IMPROVEMENTS = [
    IMPROVEMENT_CONTINUE,
    IMPROVEMENT_RETRY,
    IMPROVEMENT_REPLAN,
    IMPROVEMENT_ESCALATE
]