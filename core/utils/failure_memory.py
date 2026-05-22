"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  JKAI ZENITH — FAILURE INTELLIGENCE v1.0                                   ║
║  "Hệ thống thông minh không phải vì nó không sai,                          ║
║   mà vì nó học được từ mỗi lần sai." — JKAI Doctrine                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

Nhiệm vụ:
  1. Ghi nhận failure patterns từ mỗi lần task thất bại (không chỉ lưu "timeout").
  2. Truy xuất patterns tương tự trước khi Planner tạo plan mới.
  3. Inject cảnh báo vào context để Planner tự thêm bước phòng ngừa.

Tích hợp vào planner.py:
  failure_ctx = await failure_memory.pre_flight_check(goal, task_type)
  if failure_ctx:
      context["past_failures"] = failure_ctx
"""

import json
import time
import hashlib
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger("JKAI.FailureMemory")


# ─────────────────────────────────────────────────────────────────────────────
#  DATA MODELS
# ─────────────────────────────────────────────────────────────────────────────

class FailureStage(str, Enum):
    PLANNING        = "planning"
    TOOL_EXECUTION  = "tool_execution"
    DEPENDENCY      = "dependency"
    VALIDATION      = "validation"
    NETWORK         = "network"
    SCHEMA          = "schema"
    TIMEOUT         = "timeout"
    UNKNOWN         = "unknown"


@dataclass
class FailurePattern:
    """
    Không lưu lỗi — lưu pattern.
    Sự khác biệt: "timeout" là lỗi. "Docker tasks fail ở dependency stage
    khi thiếu venv" là pattern có thể học được.
    """
    pattern_id:      str
    task_type:       str                       # "coding", "research", "writing"...
    goal_keywords:   List[str]                 # Top-5 keywords từ goal
    failure_stage:   FailureStage
    root_cause:      str                       # Nguyên nhân gốc, do LLM phân tích
    successful_fix:  Optional[str]             # Giải pháp đã giải quyết được
    failed_tools:    List[str]                 # Tools đã fail trong task này
    prevention_step: Optional[str]             # Bước phòng ngừa khuyến nghị
    confidence:      float = 0.5              # 0.0 - 1.0
    occurrence:      int   = 1               # Số lần pattern này lặp lại
    last_seen:       float = field(default_factory=time.time)
    task_id:         str   = ""

    def similarity_key(self) -> str:
        """Hash để detect patterns tương tự."""
        key = f"{self.task_type}:{self.failure_stage}:{':'.join(sorted(self.goal_keywords[:3]))}"
        return hashlib.md5(key.encode()).hexdigest()[:12]


@dataclass
class PreFlightWarning:
    """Kết quả trả về cho Planner trước khi tạo plan."""
    has_warnings:   bool
    warnings:       List[str]
    suggested_steps: List[Dict[str, str]]   # Các bước phòng ngừa gợi ý
    risk_level:     str                     # "low" | "medium" | "high"
    patterns_found: int


# ─────────────────────────────────────────────────────────────────────────────
#  FAILURE MEMORY ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class FailureMemory:
    """
    Bộ nhớ thất bại của JKAI Zenith.

    Không phải chat history. Không phải log.
    Là "procedural intelligence" — biết CÁCH thực thi tốt hơn theo thời gian.
    """
    _SIMILARITY_THRESHOLD = 0.55
    _MAX_PATTERNS         = 500
    _HIGH_RISK_THRESHOLD  = 3    # Pattern lặp >= 3 lần → risk cao
    _DECAY_DAYS           = 30   # Pattern cũ hơn 30 ngày giảm confidence

    def __init__(self, redis_client=None, qdrant_client=None) -> None:
        self._redis   = redis_client
        self._qdrant  = qdrant_client
        self._local:  Dict[str, FailurePattern] = {}  # In-memory fallback
        self._REDIS_KEY = "jkai:failure_patterns"

    # ── PUBLIC API ────────────────────────────────────────────────────────────

    async def record_failure(
        self,
        task_id:      str,
        goal:         str,
        task_type:    str,
        failure_stage: FailureStage,
        error_detail: str,
        failed_tools: List[str],
        attempted_fix: Optional[str] = None,
        fix_worked:    bool = False,
    ) -> FailurePattern:
        """
        Ghi nhận một failure pattern mới hoặc tăng occurrence nếu đã tồn tại.

        Gọi từ Executor sau khi task fail hoặc từ HINDSIGHT module.
        """
        keywords = self._extract_keywords(goal)
        root_cause = await self._analyze_root_cause(error_detail, failure_stage, task_type)
        prevention = self._derive_prevention(failure_stage, root_cause, failed_tools)

        pattern = FailurePattern(
            pattern_id     = f"fp_{task_id}_{int(time.time())}",
            task_type      = task_type,
            goal_keywords  = keywords,
            failure_stage  = failure_stage,
            root_cause     = root_cause,
            successful_fix = attempted_fix if fix_worked else None,
            failed_tools   = failed_tools,
            prevention_step= prevention,
            confidence     = 0.7 if fix_worked else 0.5,
            task_id        = task_id,
        )

        # Tìm pattern tương tự để merge thay vì tạo trùng
        existing = self._find_similar(pattern)
        if existing:
            existing.occurrence += 1
            existing.confidence  = min(0.95, existing.confidence + 0.05)
            existing.last_seen   = time.time()
            if fix_worked and not existing.successful_fix:
                existing.successful_fix = attempted_fix
                existing.prevention_step = prevention
            await self._persist(existing)
            logger.info(f"[FAILURE-MEMORY]: Pattern merged. occurrence={existing.occurrence} | {existing.root_cause[:60]}")
            return existing

        await self._persist(pattern)
        logger.info(f"[FAILURE-MEMORY]: New pattern recorded: {pattern.pattern_id} | stage={failure_stage} | {root_cause[:60]}")
        return pattern

    async def pre_flight_check(
        self,
        goal:      str,
        task_type: str,
    ) -> PreFlightWarning:
        """
        ⚡ Gọi trước khi Planner tạo plan.

        Trả về warnings và suggested_steps để Planner inject vào plan.
        Ví dụ: nếu 3 lần trước Docker task fail ở dependency stage,
               Planner sẽ tự thêm step "validate_environment" vào đầu plan.
        """
        all_patterns = await self._load_all()
        keywords     = self._extract_keywords(goal)
        matches      = self._match_patterns(all_patterns, task_type, keywords)

        if not matches:
            return PreFlightWarning(False, [], [], "low", 0)

        warnings:        List[str]           = []
        suggested_steps: List[Dict[str, str]] = []
        max_occurrence   = max(p.occurrence for p in matches)

        for p in matches:
            age_factor   = self._age_decay(p.last_seen)
            eff_conf     = p.confidence * age_factor

            if eff_conf < 0.3:
                continue

            warn_msg = (
                f"⚠️ Pattern (x{p.occurrence}): {p.root_cause} "
                f"[stage: {p.failure_stage}, confidence: {eff_conf:.0%}]"
            )
            warnings.append(warn_msg)

            if p.prevention_step:
                suggested_steps.append({
                    "id":          f"pre_prevent_{p.failure_stage}",
                    "description": p.prevention_step,
                    "reason":      f"Phòng ngừa failure đã xảy ra {p.occurrence} lần",
                    "stage":       p.failure_stage,
                })

        risk = "low"
        if max_occurrence >= self._HIGH_RISK_THRESHOLD:
            risk = "high"
        elif max_occurrence >= 2:
            risk = "medium"

        return PreFlightWarning(
            has_warnings    = bool(warnings),
            warnings        = warnings,
            suggested_steps = suggested_steps,
            risk_level      = risk,
            patterns_found  = len(matches),
        )

    async def get_tool_failure_rate(self, tool_id: str) -> float:
        """Tỷ lệ failure của một tool cụ thể. 0.0 = hoàn hảo, 1.0 = luôn fail."""
        all_patterns = await self._load_all()
        total = sum(1 for p in all_patterns if tool_id in p.failed_tools)
        if not all_patterns:
            return 0.0
        return min(1.0, total / max(1, len(all_patterns)) * 3)  # Amplify signal

    # ── PRIVATE HELPERS ───────────────────────────────────────────────────────

    def _extract_keywords(self, text: str) -> List[str]:
        """Top 5 meaningful keywords (stopword removal đơn giản)."""
        STOPWORDS = {
            "và", "hoặc", "với", "cho", "của", "một", "các", "là", "có",
            "the", "a", "an", "with", "for", "and", "or", "in", "to",
            "using", "based", "build", "create", "make", "generate",
        }
        words = text.lower().split()
        keywords = [w.strip(".,!?;:\"'") for w in words if len(w) > 3 and w not in STOPWORDS]
        # Deduplicate, preserve order
        seen = set()
        unique = []
        for w in keywords:
            if w not in seen:
                seen.add(w)
                unique.append(w)
        return unique[:5]

    def _find_similar(self, pattern: FailurePattern) -> Optional[FailurePattern]:
        """Tìm pattern đã lưu có similarity_key giống."""
        target_key = pattern.similarity_key()
        for p in self._local.values():
            if p.similarity_key() == target_key:
                return p
        return None

    def _match_patterns(
        self,
        patterns:  List[FailurePattern],
        task_type: str,
        keywords:  List[str],
    ) -> List[FailurePattern]:
        """Tìm các patterns liên quan đến task hiện tại."""
        results = []
        kw_set  = set(keywords)
        for p in patterns:
            if p.task_type != task_type and task_type != "general":
                continue
            overlap = len(kw_set & set(p.goal_keywords))
            if overlap >= 1 or p.task_type == task_type:
                results.append(p)
        return sorted(results, key=lambda x: x.occurrence, reverse=True)[:5]

    def _age_decay(self, last_seen: float) -> float:
        """Patterns cũ hơn 30 ngày giảm confidence."""
        days_old = (time.time() - last_seen) / 86400
        if days_old > self._DECAY_DAYS:
            return max(0.1, 1.0 - (days_old - self._DECAY_DAYS) / 30)
        return 1.0

    def _derive_prevention(
        self,
        stage:       FailureStage,
        root_cause:  str,
        failed_tools: List[str],
    ) -> Optional[str]:
        """Rule-based prevention suggestion (không gọi LLM để tiết kiệm token)."""
        prevention_map = {
            FailureStage.DEPENDENCY:   "Validate environment và dependencies trước khi execution",
            FailureStage.NETWORK:      "Kiểm tra connectivity và retry policy trước khi gọi external API",
            FailureStage.SCHEMA:       "Validate schema và data types trước khi processing",
            FailureStage.TIMEOUT:      "Tăng timeout hoặc chia nhỏ task thành sub-tasks",
            FailureStage.VALIDATION:   "Thêm bước pre-validation với sample data trước full execution",
            FailureStage.TOOL_EXECUTION: f"Kiểm tra fallback cho: {', '.join(failed_tools[:2])}",
        }
        return prevention_map.get(stage)

    async def _analyze_root_cause(
        self,
        error_detail:  str,
        stage:         FailureStage,
        task_type:     str,
    ) -> str:
        """
        Phân tích root cause.
        Dùng pattern matching trước (nhanh, free), LLM chỉ khi cần thiết.
        """
        error_lower = error_detail.lower()

        # Fast pattern matching (không tốn token)
        PATTERNS = [
            (["modulenotfounderror", "importerror", "no module"],     "Missing Python dependency"),
            (["connection refused", "connection timeout", "econnreset"], "Network connectivity failure"),
            (["timeout", "timed out", "deadline exceeded"],           "Execution timeout"),
            (["permission denied", "access denied", "forbidden"],     "Permission/auth failure"),
            (["json decode", "jsondecodeerror", "invalid json"],      "Invalid JSON schema"),
            (["keyerror", "attributeerror", "typeerror"],              "Data structure mismatch"),
            (["out of memory", "oom", "memory error"],                "Memory exhaustion"),
            (["rate limit", "429", "quota exceeded"],                 "API rate limit exceeded"),
            (["docker", "container", "image not found"],              "Docker/container failure"),
            (["venv", "virtualenv", "pip install"],                   "Python environment issue"),
        ]

        for keywords, cause in PATTERNS:
            if any(k in error_lower for k in keywords):
                return cause

        # Fallback: mô tả ngắn gọn từ error detail
        return f"{stage.value} failure: {error_detail[:80]}..."

    async def _persist(self, pattern: FailurePattern) -> None:
        """Lưu pattern vào Redis (primary) và local dict (fallback)."""
        self._local[pattern.pattern_id] = pattern
        if self._redis:
            try:
                payload = json.dumps(asdict(pattern), ensure_ascii=False)
                self._redis.hset(self._REDIS_KEY, pattern.pattern_id, payload)
            except Exception as e:
                logger.warning(f"[FAILURE-MEMORY]: Redis persist failed: {e}")

    async def _load_all(self) -> List[FailurePattern]:
        """Load tất cả patterns từ Redis hoặc local dict."""
        if self._redis:
            try:
                raw = self._redis.hgetall(self._REDIS_KEY)
                patterns = []
                for v in raw.values():
                    data = json.loads(v)
                    data["failure_stage"] = FailureStage(data["failure_stage"])
                    patterns.append(FailurePattern(**data))
                return patterns
            except Exception as e:
                logger.warning(f"[FAILURE-MEMORY]: Redis load failed, using local: {e}")
        return list(self._local.values())

    def format_for_planner(self, warning: PreFlightWarning) -> str:
        """Format warning để inject vào system prompt của Planner."""
        if not warning.has_warnings:
            return ""

        lines = [f"[PRE-FLIGHT WARNING — Risk: {warning.risk_level.upper()}]"]
        lines.extend(warning.warnings)
        if warning.suggested_steps:
            lines.append("\n[SUGGESTED PREVENTION STEPS]:")
            for s in warning.suggested_steps:
                lines.append(f"  - {s['description']} (reason: {s['reason']})")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
#  SINGLETON
# ─────────────────────────────────────────────────────────────────────────────

# 🚀 [AUTO-INIT]: Khởi tạo nơ-ron ngay khi nạp
failure_memory = FailureMemory()


def init_failure_memory(redis_client=None, qdrant_client=None) -> FailureMemory:
    global failure_memory
    # Nếu đã có data local, giữ lại
    if failure_memory:
        failure_memory._redis = redis_client
        failure_memory._qdrant = qdrant_client
    else:
        failure_memory = FailureMemory(redis_client=redis_client, qdrant_client=qdrant_client)
    return failure_memory


# ─────────────────────────────────────────────────────────────────────────────
#  PATCH CHO planner.py — Thêm vào generate_plan() sau khi lấy complexity
# ─────────────────────────────────────────────────────────────────────────────
"""
HƯỚNG DẪN TÍCH HỢP VÀO planner.py:

Bước 1 — Import:
    from failure_memory import failure_memory, FailureStage

Bước 2 — Trong generate_plan(), sau dòng `complexity = self._estimate_complexity(goal)`:

    # 🛡️ [PRE-FLIGHT]: Kiểm tra failure patterns trước khi lập kế hoạch
    task_type = context.get("task_type", "general")
    pre_flight = await failure_memory.pre_flight_check(goal, task_type)
    if pre_flight.has_warnings:
        context["pre_flight_warnings"] = failure_memory.format_for_planner(pre_flight)
        context["suggested_prevention"] = pre_flight.suggested_steps
        engine.publish_mission_log(
            "PLANNER",
            f"[PRE-FLIGHT]: {pre_flight.patterns_found} patterns nguy hiểm, risk={pre_flight.risk_level}",
            task_id
        )

Bước 3 — Trong Executor, sau khi task fail, gọi:

    await failure_memory.record_failure(
        task_id       = task_id,
        goal          = goal,
        task_type     = task_type,
        failure_stage = FailureStage.TOOL_EXECUTION,
        error_detail  = str(error),
        failed_tools  = [step.tool],
    )
"""
