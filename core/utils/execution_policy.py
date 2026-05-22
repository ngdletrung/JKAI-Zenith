"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  JKAI ZENITH — EXECUTION POLICY ENGINE v1.0                                ║
║  "Thông minh không nằm ở plan. Nó nằm ở việc chọn chiến lược              ║
║   thực thi đúng theo tình huống." — JKAI Doctrine                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

Nhiệm vụ:
  - Planner chỉ tạo INTENT (ví dụ: "research_market_price").
  - ExecutionPolicyEngine quyết định: tool nào, model nào, retry strategy nào,
    timeout, parallel/sequential, cache/realtime, confidence threshold.

Tích hợp:
  policy = policy_engine.resolve(step, context, world_state)
  executor.run_step(step, policy)
"""

import time
import logging
import asyncio
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("JKAI.PolicyEngine")


# ─────────────────────────────────────────────────────────────────────────────
#  ENUMS & MODELS
# ─────────────────────────────────────────────────────────────────────────────

class ReasoningDepth(str, Enum):
    SHALLOW  = "shallow"   # FAQ, lookup, simple format
    MEDIUM   = "medium"    # Coding debug, data transform
    DEEP     = "deep"      # Architecture, complex analysis
    CRITICAL = "critical"  # Repeated failure, high uncertainty, destructive ops


class RetryStrategy(str, Enum):
    NONE          = "none"
    LINEAR        = "linear"        # Retry ngay lập tức
    EXPONENTIAL   = "exponential"   # Backoff 2^n seconds
    FALLBACK_ONLY = "fallback_only" # Không retry, dùng fallback_tool ngay


class VerificationLevel(str, Enum):
    SKIP   = "skip"    # Không verify (FAQ, nội bộ)
    SAMPLE = "sample"  # Spot-check 1 kết quả
    FULL   = "full"    # Verify toàn bộ output


@dataclass
class ExecutionPolicy:
    """
    Chiến lược thực thi đầy đủ cho 1 step.
    Executor đọc policy này thay vì hardcode logic.
    """
    # Model routing
    preferred_model:     str             = "fast"       # "fast" | "deep" | "balanced"
    hardware_override:   Optional[str]   = None         # Override ALPHA/BETA nếu cần

    # Retry
    max_retry:           int             = 2
    retry_strategy:      RetryStrategy   = RetryStrategy.EXPONENTIAL
    retry_delay_base:    float           = 1.5          # seconds

    # Reasoning
    reasoning_depth:     ReasoningDepth  = ReasoningDepth.MEDIUM
    use_critic:          bool            = False
    use_verifier:        bool            = False

    # Performance
    timeout:             float           = 30.0         # seconds
    use_cache:           bool            = True
    prefer_parallel:     bool            = False

    # Quality gates
    confidence_threshold: float          = 0.6          # Min confidence để accept output
    verification_level:  VerificationLevel = VerificationLevel.SKIP

    # Budget
    max_token_budget:    int             = 1500
    cost_sensitive:      bool            = False

    # Metadata
    risk_level:          str             = "low"        # "low" | "medium" | "high"
    doctrine_id:         Optional[str]   = None         # "SAFE_FILE_MOD" | "RAPID_RESEARCH" | ...
    rationale:           str             = ""


@dataclass
class WorldState:
    """Snapshot trạng thái hệ thống lúc resolve policy."""
    cpu_percent:    float = 0.0
    ram_percent:    float = 0.0
    active_tasks:   int   = 0
    tool_failures:  int   = 0    # Số lần tool fail trong session hiện tại
    total_tokens_used: int = 0   # Token đã dùng trong task
    elapsed_seconds: float = 0.0


# ─────────────────────────────────────────────────────────────────────────────
#  INTENT TAXONOMY
# ─────────────────────────────────────────────────────────────────────────────

# Map từ intent (goal keyword pattern) sang policy template
_INTENT_POLICIES: Dict[str, Dict[str, Any]] = {
    # Lookup / Factual
    "lookup":          {"depth": ReasoningDepth.SHALLOW,  "verify": VerificationLevel.SKIP,   "cache": True,  "timeout": 15.0, "model": "fast"},
    "faq":             {"depth": ReasoningDepth.SHALLOW,  "verify": VerificationLevel.SKIP,   "cache": True,  "timeout": 10.0, "model": "fast"},

    # Research
    "research":        {"depth": ReasoningDepth.MEDIUM,   "verify": VerificationLevel.SAMPLE, "cache": False, "timeout": 45.0, "model": "balanced", "use_verifier": True},
    "market_price":    {"depth": ReasoningDepth.SHALLOW,  "verify": VerificationLevel.FULL,   "cache": False, "timeout": 20.0, "model": "fast", "use_verifier": True},
    "competitive":     {"depth": ReasoningDepth.DEEP,     "verify": VerificationLevel.SAMPLE, "cache": False, "timeout": 60.0, "model": "deep"},

    # Coding
    "coding":          {"depth": ReasoningDepth.MEDIUM,   "verify": VerificationLevel.SAMPLE, "cache": False, "timeout": 60.0, "model": "balanced"},
    "debug":           {"depth": ReasoningDepth.DEEP,     "verify": VerificationLevel.FULL,   "cache": False, "timeout": 90.0, "model": "deep",     "use_critic": True},
    "architecture":    {"depth": ReasoningDepth.DEEP,     "verify": VerificationLevel.FULL,   "cache": False, "timeout": 120.0,"model": "deep",     "use_critic": True},
    "refactor":        {"depth": ReasoningDepth.MEDIUM,   "verify": VerificationLevel.FULL,   "cache": False, "timeout": 60.0, "model": "balanced", "use_critic": True},

    # Writing / Content
    "writing":         {"depth": ReasoningDepth.MEDIUM,   "verify": VerificationLevel.SKIP,   "cache": False, "timeout": 45.0, "model": "balanced"},
    "translation":     {"depth": ReasoningDepth.SHALLOW,  "verify": VerificationLevel.SKIP,   "cache": True,  "timeout": 20.0, "model": "fast"},
    "summarize":       {"depth": ReasoningDepth.SHALLOW,  "verify": VerificationLevel.SKIP,   "cache": True,  "timeout": 15.0, "model": "fast"},

    # Data / Analysis
    "analysis":        {"depth": ReasoningDepth.DEEP,     "verify": VerificationLevel.FULL,   "cache": False, "timeout": 90.0, "model": "deep",     "use_critic": True},
    "convert":         {"depth": ReasoningDepth.SHALLOW,  "verify": VerificationLevel.SAMPLE, "cache": True,  "timeout": 20.0, "model": "fast"},

    # Default
    "general":         {"depth": ReasoningDepth.MEDIUM,   "verify": VerificationLevel.SKIP,   "cache": True,  "timeout": 30.0, "model": "balanced"},
}

# Keywords để detect intent từ description/tool name
_INTENT_KEYWORDS: List[Tuple[str, List[str]]] = [
    ("debug",       ["debug", "fix", "error", "loi", "sua", "trace"]),
    ("architecture",["architect", "design", "kien_truc", "scaffold", "structure"]),
    ("refactor",    ["refactor", "cai_tien", "optimize", "clean"]),
    ("coding",      ["code", "viet_code", "implement", "function", "class", "api"]),
    ("market_price",["gia", "price", "market", "thi_truong", "cost", "fee"]),
    ("research",    ["research", "tim_hieu", "search", "find", "analyze", "phan_tich"]),
    ("competitive", ["compare", "so_sanh", "competitor", "benchmark"]),
    ("analysis",    ["analy", "phan_tich", "insight", "data", "report", "bao_cao"]),
    ("writing",     ["write", "viet", "draft", "content", "article", "bai"]),
    ("translation", ["translate", "dich", "convert_lang"]),
    ("summarize",   ["summar", "tom_tat", "brief", "overview"]),
    ("lookup",      ["lookup", "tra_cuu", "what_is", "define", "explain"]),
]


# ─────────────────────────────────────────────────────────────────────────────
#  POLICY ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class ExecutionPolicyEngine:
    """
    Não của việc thực thi.

    Nhận vào: step + context + world_state
    Trả ra:   ExecutionPolicy tối ưu cho tình huống đó

    KHÔNG cần LLM — rule-based + heuristics = nhanh, ổn định, predictable.
    """

    def __init__(self, tool_reliability_getter=None) -> None:
        """
        tool_reliability_getter: callable(tool_id) -> float (0=reliable, 1=unreliable)
        Thường lấy từ failure_memory.get_tool_failure_rate(tool_id)
        """
        self._get_reliability = tool_reliability_getter or (lambda t: 0.0)

    async def resolve(
        self,
        step:        Dict[str, Any],
        context:     Dict[str, Any],
        world_state: Optional[WorldState] = None,
    ) -> ExecutionPolicy:
        """
        Tổng hợp policy từ:
          1. Intent detection (task type)
          2. World state (hệ thống đang bận?)
          3. Risk assessment (tool unreliable? high failure count?)
          4. Budget constraints (token, time)

        Thứ tự ưu tiên: Safety > Budget > Quality > Speed
        """
        ws        = world_state or WorldState()
        tool_id   = step.get("tool", "")
        desc      = step.get("description", "")
        step_id   = step.get("id", "")

        # 1. Base policy từ intent
        intent   = self._detect_intent(tool_id, desc)
        template = _INTENT_POLICIES.get(intent, _INTENT_POLICIES["general"])
        policy   = self._build_from_template(template)
        policy.rationale = f"intent={intent}"

        # 2. Điều chỉnh theo world state
        policy   = self._apply_world_state_adjustments(policy, ws)

        # 3. Điều chỉnh theo tool reliability
        reliability_val = self._get_reliability(tool_id)
        if asyncio.iscoroutine(reliability_val):
            tool_fail_rate = await reliability_val
        else:
            tool_fail_rate = reliability_val
            
        policy = self._apply_tool_reliability(policy, tool_id, tool_fail_rate)

        # 4. Điều chỉnh theo context signals
        policy = self._apply_context_signals(policy, context, step)

        # 5. Cognitive guardrail cuối cùng (không bao giờ bỏ qua)
        policy = self._apply_guardrails(policy, ws, context)

        logger.debug(
            f"[POLICY-ENGINE]: {step_id} | intent={intent} | "
            f"depth={policy.reasoning_depth} | model={policy.preferred_model} | "
            f"timeout={policy.timeout}s | risk={policy.risk_level}"
        )
        return policy

    async def resolve_batch(
        self,
        steps:       List[Dict[str, Any]],
        context:     Dict[str, Any],
        world_state: Optional[WorldState] = None,
    ) -> Dict[str, ExecutionPolicy]:
        """Resolve policy cho toàn bộ plan một lần."""
        ws = world_state or WorldState()
        return {step.get("id", f"s{i}"): await self.resolve(step, context, ws)
                for i, step in enumerate(steps)}

    # ── DETECTION ────────────────────────────────────────────────────────────

    def _detect_intent(self, tool_id: str, description: str) -> str:
        """Detect intent từ tool_id và description (không gọi LLM)."""
        text = f"{tool_id} {description}".lower().replace("-", "_")
        for intent, keywords in _INTENT_KEYWORDS:
            if any(kw in text for kw in keywords):
                return intent
        return "general"

    # ── ADJUSTMENTS ──────────────────────────────────────────────────────────

    def _apply_world_state_adjustments(
        self, policy: ExecutionPolicy, ws: WorldState
    ) -> ExecutionPolicy:
        """Nếu hệ thống overloaded, chuyển sang chế độ tiết kiệm."""
        overloaded = ws.cpu_percent > 85 or ws.ram_percent > 90

        # [NEURAL-GUARD]: Đảm bảo total_tokens_used không phải là coroutine
        tokens_used = ws.total_tokens_used
        if asyncio.iscoroutine(tokens_used):
            tokens_used = 0 # Fallback an toàn nếu bị rò rỉ coroutine
            
        if overloaded:
            # Giảm tải: nhanh hơn, ít token hơn, không verify
            policy.preferred_model    = "fast"
            policy.timeout            = min(policy.timeout, 20.0)
            policy.max_token_budget   = min(policy.max_token_budget, 800)
            policy.use_verifier       = False
            policy.reasoning_depth    = ReasoningDepth.SHALLOW
            policy.rationale         += " | OVERLOAD_MODE"
            logger.warning("[POLICY-ENGINE]: System overloaded — switching to FAST mode")

        elif tokens_used > 15000:
            # Token budget gần cạn
            policy.preferred_model  = "fast"
            policy.max_token_budget = min(policy.max_token_budget, 600)
            policy.use_critic       = False
            policy.rationale       += " | TOKEN_BUDGET_LIMIT"

        return policy

    def _apply_tool_reliability(
        self, policy: ExecutionPolicy, tool_id: str, fail_rate: float
    ) -> ExecutionPolicy:
        """Tool hay fail → tăng retry, bật verifier, giảm timeout."""
        if fail_rate > 0.6:
            # Tool rất unreliable
            policy.retry_strategy = RetryStrategy.FALLBACK_ONLY
            policy.use_verifier   = True
            policy.risk_level     = "high"
            policy.rationale     += f" | TOOL_UNRELIABLE({tool_id}:{fail_rate:.0%})"
        elif fail_rate > 0.3:
            # Tool không ổn định
            policy.max_retry      = max(policy.max_retry, 3)
            policy.retry_strategy = RetryStrategy.EXPONENTIAL
            policy.risk_level     = "medium"
            policy.rationale     += f" | TOOL_UNSTABLE({tool_id}:{fail_rate:.0%})"

        return policy

    def _apply_context_signals(
        self,
        policy:  ExecutionPolicy,
        context: Dict[str, Any],
        step:    Dict[str, Any],
    ) -> ExecutionPolicy:
        """
        Đọc signals từ context để tinh chỉnh policy.
        Context keys quan trọng: pre_flight_warnings, pre_flight_risk,
                                  task_type, confidence_score.
        """
        # Pre-flight risk từ FailureMemory
        risk = context.get("pre_flight_risk", "low")
        if risk == "high":
            policy.reasoning_depth = ReasoningDepth.CRITICAL
            policy.use_critic      = True
            policy.use_verifier    = True
            policy.max_retry       = max(policy.max_retry, 3)
            policy.risk_level      = "high"
            policy.rationale      += " | PREFLIGHT_HIGH_RISK"

        # Destructive operation → cần verify
        desc_lower = step.get("description", "").lower()
        destructive_signals = ["delete", "drop", "remove", "truncate", "overwrite", "xoa", "reset"]
        if any(s in desc_lower for s in destructive_signals):
            policy.verification_level = VerificationLevel.FULL
            policy.use_critic         = True
            policy.risk_level         = "high"
            policy.rationale         += " | DESTRUCTIVE_OP"

        # External API → không cache, verify
        if step.get("hardware_target") == "BETA" and "api" in desc_lower:
            policy.use_cache      = False
            policy.use_verifier   = True
            policy.rationale     += " | EXTERNAL_API"

        return policy

    def _apply_guardrails(
        self,
        policy:  ExecutionPolicy,
        ws:      WorldState,
        context: Dict[str, Any],
    ) -> ExecutionPolicy:
        """
        Hard limits — không bao giờ vượt qua.
        Đây là Cognitive Guardrails tầng Policy.
        """
        # [NEURAL-GUARD]: Đảm bảo các thông số không bị nhiễm coroutine
        if asyncio.iscoroutine(policy.timeout):
            policy.timeout = 30.0 # Default an toàn
        if asyncio.iscoroutine(policy.max_token_budget):
            policy.max_token_budget = 1000

        # Không bao giờ timeout dưới 5s
        policy.timeout = max(5.0, policy.timeout)

        # Không bao giờ token budget dưới 200
        policy.max_token_budget = max(200, policy.max_token_budget)

        # Nếu tool_failures nhiều trong session → bắt buộc dùng fallback
        if ws.tool_failures >= 3:
            policy.retry_strategy = RetryStrategy.FALLBACK_ONLY
            policy.rationale     += " | FORCE_FALLBACK(session failures)"

        return policy

    # ── BUILDER ──────────────────────────────────────────────────────────────

    def _build_from_template(self, template: Dict[str, Any]) -> ExecutionPolicy:
        return ExecutionPolicy(
            reasoning_depth    = template.get("depth", ReasoningDepth.MEDIUM),
            verification_level = template.get("verify", VerificationLevel.SKIP),
            use_cache          = template.get("cache", True),
            timeout            = template.get("timeout", 30.0),
            preferred_model    = template.get("model", "balanced"),
            use_critic         = template.get("use_critic", False),
            use_verifier       = template.get("use_verifier", False),
            max_token_budget   = 1500 if template.get("model") == "deep" else 1000,
        )

    def summarize_for_log(self, policies: Dict[str, ExecutionPolicy]) -> str:
        """Format policy summary để log / publish lên monitor."""
        lines = ["[EXECUTION POLICIES]"]
        for sid, p in policies.items():
            lines.append(
                f"  {sid}: model={p.preferred_model} depth={p.reasoning_depth.value} "
                f"retry={p.max_retry} risk={p.risk_level} timeout={p.timeout:.0f}s"
            )
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
#  SINGLETON
# ─────────────────────────────────────────────────────────────────────────────

_engine_instance: Optional[ExecutionPolicyEngine] = None


def get_policy_engine(tool_reliability_getter=None) -> ExecutionPolicyEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = ExecutionPolicyEngine(tool_reliability_getter)
    return _engine_instance


# ─────────────────────────────────────────────────────────────────────────────
#  HƯỚNG DẪN TÍCH HỢP VÀO EXECUTOR
# ─────────────────────────────────────────────────────────────────────────────
"""
1. Import:
    from execution_policy import get_policy_engine, WorldState

2. Trong Executor.__init__():
    from failure_memory import failure_memory
    self._policy_engine = get_policy_engine(
        tool_reliability_getter=failure_memory.get_tool_failure_rate
    )

3. Trước khi chạy mỗi step:
    import psutil
    ws = WorldState(
        cpu_percent       = psutil.cpu_percent(),
        ram_percent       = psutil.virtual_memory().percent,
        tool_failures     = self._session_failures,
        total_tokens_used = engine.get_total_tokens(),
    )
    policy = self._policy_engine.resolve(step.dict(), context, ws)

4. Dùng policy trong execution:
    timeout     = policy.timeout
    max_retry   = policy.max_retry
    use_critic  = policy.use_critic
    model_mode  = policy.preferred_model
    ...

5. Log toàn bộ policies sau khi resolve batch:
    all_policies = self._policy_engine.resolve_batch(steps, context, ws)
    engine.publish_mission_log("POLICY", self._policy_engine.summarize_for_log(all_policies), task_id)
"""
