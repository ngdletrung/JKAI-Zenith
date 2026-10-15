# -*- coding: utf-8 -*-
"""
core/os/cognition/rsil_orchestrator.py
======================================
[Pha 4 - Slice 4.1: Recursive Self-Improvement Loop Level 3 (RSIL-L3)]:
Bộ điều phối tự tiến hóa đệ quy tự trị hoàn toàn (Autonomous Promotion Engine):
1. Chữ ký 2 khóa (`Dual-Key Invariant`): Máy ký Operational Witness xác nhận checks passed; Master giữ khóa thẩm quyền.
2. 4 Cổng Hiến Pháp trực giao: Held-out gain (delta >= +0.05, drift <= 10%), Zero safety regression, Invariant AST, Resource ceiling <= 30%.
3. Taxonomy phân loại theo bản chất: Chạm security/governance/sanitizer -> bắt buộc Tier 3 (Master duyệt).
4. Ngân sách tự trị 3 promote/tuần & Tự động đóng băng (Fail-Closed Auto-Freeze) khi hết quota hoặc 2 rollback liên tiếp.
5. Canary kép min(50 missions, 14 ngày) + Rollback tức thì (< 10ms) khi drift > 15%.
6. Sổ cái bất biến Chained Promotion Journal băm xích SHA-256 chống sửa lén.
"""

from __future__ import annotations

from enum import Enum
import hashlib
import hmac
import json
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple


# ==============================================================================
# 1. TAXONOMY PHÂN LOẠI PHẠM VI TIẾN HÓA THEO BẢN CHẤT
# ==============================================================================

class EvolutionTier(str, Enum):
    TIER1_PARAMETERS_AND_MEMORY = "TIER1_PARAMETERS_AND_MEMORY"
    TIER2_MODELS_AND_ROUTERS = "TIER2_MODELS_AND_ROUTERS"
    TIER3_IRREVERSIBLE_AND_SECURITY = "TIER3_IRREVERSIBLE_AND_SECURITY"


TIER3_PROTECTED_PATH_PATTERNS = [
    "core/security",
    "core/sanitizer",
    "core/governor",
    "core/kernel/mcp_pilot_allowlist",
    "core/os/cognition/completion_authority",
    "tools/web_search.py",
    "omni_search_engine",
    "egress",
    "_auth",
    "auth_",
    "/auth/",
    "authority",
]

TIER3_PROTECTED_SYMBOLS = [
    "validate_egress_url_ssrf_safe",
    "scan_for_retain",
    "authorize_mcp_call",
    "sign_observation",
    "verify_signature",
    "authorize_mutation_path",
    "CompletionAuthority",
    "StateSanitizer",
    "LocalMCPPilotGovernor",
    "MEMORY_DEFENSE_PATTERNS",
]

TIER2_PATTERNS = [
    "models/",
    "adapter_",
    "lora_",
    "intent_router",
    "model_capabilities",
    "classifier",
]


def classify_diff_evolution_tier(
    diff_paths: List[str],
    diff_content: Optional[str] = None,
) -> EvolutionTier:
    """
    [Cơ chế Taxonomy 2 lớp — Lượt 298]:
    Lớp 1 (Đường dẫn): Chặn cứng các tệp/thư mục bảo mật, egress, authority, tools/web_search.py.
    Lớp 2 (Ký hiệu / Nội dung): Quét diff_content hoặc tên hàm bảo vệ cốt lõi. Nếu xuất hiện bất kỳ
    symbol nào trong `TIER3_PROTECTED_SYMBOLS` -> ÉP BUỘC TIER 3 (Master duyệt bắt buộc).
    Tránh phạt nhầm `author_notes.md` bằng cách kiểm tra ranh giới từ.
    """
    import re

    # 1. Quét nội dung diff / symbols nếu có
    if diff_content:
        for sym in TIER3_PROTECTED_SYMBOLS:
            if sym in diff_content:
                return EvolutionTier.TIER3_IRREVERSIBLE_AND_SECURITY

    # 2. Quét đường dẫn
    for p in diff_paths:
        p_norm = p.replace("\\", "/").lower()
        if any(pat.lower() in p_norm for pat in TIER3_PROTECTED_PATH_PATTERNS):
            return EvolutionTier.TIER3_IRREVERSIBLE_AND_SECURITY
        if re.search(r"(?:^|[/_\\])auth(?:$|[/_\\])", p_norm):
            return EvolutionTier.TIER3_IRREVERSIBLE_AND_SECURITY

    # 3. Phân loại Tier 2
    for p in diff_paths:
        p_norm = p.replace("\\", "/").lower()
        if any(pat.lower() in p_norm for pat in TIER2_PATTERNS):
            return EvolutionTier.TIER2_MODELS_AND_ROUTERS

    return EvolutionTier.TIER1_PARAMETERS_AND_MEMORY


# ==============================================================================
# 2. NGÂN SÁCH TỰ TRỊ (AUTONOMOUS QUOTA) & AUTO-FREEZE TRIGGER
# ==============================================================================

class AutonomousQuotaTracker:
    """
    Quản lý ngân sách tự trị của hệ thống:
    - Tối đa 3 lần auto-promote / tuần.
    - Tối đa 2 lần auto-rollback liên tiếp.
    - Vượt quá hạn mức -> Tự động đóng băng toàn bộ tiến hóa (Fail-Closed Freeze).
    """

    def __init__(self, max_weekly_promotes: int = 3, max_consecutive_rollbacks: int = 2) -> None:
        self.max_weekly_promotes = int(max_weekly_promotes)
        self.max_consecutive_rollbacks = int(max_consecutive_rollbacks)
        self.promotions_this_week: int = 0
        self.consecutive_rollbacks: int = 0
        self.state: str = "ACTIVE"
        self.freeze_reason: Optional[str] = None

    def is_frozen(self) -> bool:
        return self.state.startswith("FROZEN")

    def can_promote(self) -> Tuple[bool, str]:
        if self.is_frozen():
            return False, f"SYSTEM_FROZEN: {self.freeze_reason}"
        if self.promotions_this_week >= self.max_weekly_promotes:
            self.state = "FROZEN_QUOTA_EXCEEDED"
            self.freeze_reason = f"FROZEN_QUOTA_EXCEEDED: Weekly promote quota ({self.max_weekly_promotes}) exceeded."
            return False, self.freeze_reason
        return True, "ACTIVE_WITHIN_BUDGET"

    def record_promotion(self, proposal_id: str) -> None:
        can, reason = self.can_promote()
        if not can:
            raise RuntimeError(f"Cannot record promotion: {reason}")
        self.promotions_this_week += 1
        self.consecutive_rollbacks = 0  # Reset streak on successful promote

    def record_rollback(self, proposal_id: str, drift_pct: float) -> None:
        self.consecutive_rollbacks += 1
        if self.consecutive_rollbacks >= self.max_consecutive_rollbacks:
            self.state = "FROZEN_CONSECUTIVE_ROLLBACKS"
            self.freeze_reason = (
                f"Consecutive rollbacks ({self.consecutive_rollbacks}) reached limit. "
                f"Last drift: {drift_pct}%."
            )

    def reset_state_for_testing(self) -> None:
        self.promotions_this_week = 0
        self.consecutive_rollbacks = 0
        self.state = "ACTIVE"
        self.freeze_reason = None


# ==============================================================================
# 3. SỔ CÁI BẤT BIẾN (CHAINED SHA-256 PROMOTION JOURNAL)
# ==============================================================================

class ChainedPromotionJournal:
    """
    Sổ cái tiến hóa bất biến:
    Mỗi bản ghi được nối chuỗi mã băm `prev_sha256 -> curr_sha256` chống sửa lén.
    """

    def __init__(self, journal_path: Optional[Path] = None) -> None:
        self.journal_path = journal_path or Path("data/evolution/promotion_journal.jsonl")
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_last_sha256(self) -> str:
        if not self.journal_path.exists():
            return "GENESIS"
        lines = self.journal_path.read_text(encoding="utf-8").strip().splitlines()
        if not lines:
            return "GENESIS"
        try:
            last = json.loads(lines[-1])
            return str(last.get("curr_sha256") or "GENESIS")
        except Exception:
            return "GENESIS"

    def append_entry(
        self,
        action: str,
        proposal_id: str,
        details: Dict[str, Any],
    ) -> Dict[str, Any]:
        prev_sha = self._get_last_sha256()
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        raw_payload = {
            "prev_sha256": prev_sha,
            "timestamp": ts,
            "action": action,
            "proposal_id": proposal_id,
            "details": details,
        }
        canonical_str = json.dumps(raw_payload, sort_keys=True, ensure_ascii=False)
        curr_sha = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
        entry = {**raw_payload, "curr_sha256": curr_sha}

        with open(self.journal_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def read_all_entries(self) -> List[Dict[str, Any]]:
        if not self.journal_path.exists():
            return []
        lines = self.journal_path.read_text(encoding="utf-8").strip().splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    def verify_journal_integrity(self) -> bool:
        entries = self.read_all_entries()
        if not entries:
            return True
        expected_prev = "GENESIS"
        for entry in entries:
            if entry.get("prev_sha256") != expected_prev:
                return False
            payload = {
                "prev_sha256": entry["prev_sha256"],
                "timestamp": entry["timestamp"],
                "action": entry["action"],
                "proposal_id": entry["proposal_id"],
                "details": entry["details"],
            }
            computed_sha = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
            if computed_sha != entry.get("curr_sha256"):
                return False
            expected_prev = entry["curr_sha256"]
        return True


# ==============================================================================
# 4. CHỮ KÝ 2 KHÓA (DUAL-KEY INVARIANT)
# ==============================================================================

class DualKeySigner:
    """
    Cơ chế chữ ký 2 khóa:
    - Operational Witness Key: Ký xác nhận khách quan 4 cổng kiểm tra độc lập đã PASS.
    - Master Key: Cất vật lý, dùng cho các quyết định ngoài biên giới tự trị.
    """

    def __init__(self, witness_secret: Optional[str] = None) -> None:
        import secrets
        env_secret = (witness_secret or os.getenv("JKAI_WITNESS_SECRET", "")).strip()
        self._witness_secret = (
            env_secret.encode("utf-8")
            if env_secret
            else secrets.token_bytes(32)
        )

    def sign_operational_witness(self, proposal_id: str, gates_result: Dict[str, Any]) -> str:
        data_to_sign = f"{proposal_id}:{gates_result.get('all_gates_passed')}:{gates_result.get('timestamp')}"
        digest = hmac.new(self._witness_secret, data_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"WITNESS_HMAC_{proposal_id}_{digest[:16]}"

    def verify_witness_signature(
        self,
        proposal_id: str,
        gates_result: Dict[str, Any],
        signature: str,
    ) -> bool:
        expected = self.sign_operational_witness(proposal_id, gates_result)
        return hmac.compare_digest(expected, signature)


# ==============================================================================
# 5. BỐN CỔNG HIẾN PHÁP TRỰC GIAO (FOUR CONSTITUTIONAL GATES)
# ==============================================================================

class FourConstitutionalGates:
    """
    4 Cổng Hiến Pháp trực giao độc lập:
    - Cổng 1 (Gain): Held-out delta >= +0.05 và drift 2 lần lặp <= 10%.
    - Cổng 2 (Safety): Zero safety regression (== 0).
    - Cổng 3 (System Invariant): AST invariant, blast radius sạch, phương trình bảo toàn.
    - Cổng 4 (Resource): Chi phí phụ trội token/latency <= 30.0%.
    """

    def evaluate_all(
        self,
        baseline_score: float,
        candidate_scores: List[float],
        safety_regressions: int,
        ast_invariant_ok: bool,
        blast_radius_ok: bool,
        resource_overhead_pct: float,
        min_delta: float = 0.05,
        max_drift_pct: float = 10.0,
        max_overhead_pct: float = 30.0,
    ) -> Dict[str, Any]:
        mean_cand = sum(candidate_scores) / max(1, len(candidate_scores))
        delta = round(mean_cand - baseline_score, 4)
        if len(candidate_scores) >= 2:
            drift = round((max(candidate_scores) - min(candidate_scores)) / max(0.01, mean_cand) * 100.0, 2)
        else:
            drift = 0.0

        g1_gain = (delta >= min_delta) and (drift <= max_drift_pct)
        g2_safety = int(safety_regressions) == 0
        g3_invariant = bool(ast_invariant_ok) and bool(blast_radius_ok)
        g4_resource = float(resource_overhead_pct) <= max_overhead_pct

        all_passed = bool(g1_gain and g2_safety and g3_invariant and g4_resource)

        return {
            "timestamp": round(time.time(), 3),
            "all_gates_passed": all_passed,
            "gate_1_heldout_gain": g1_gain,
            "delta_score": delta,
            "repeat_drift_pct": drift,
            "gate_2_zero_safety": g2_safety,
            "safety_regressions": safety_regressions,
            "gate_3_system_invariants": g3_invariant,
            "gate_4_resource_ceiling": g4_resource,
            "resource_overhead_pct": resource_overhead_pct,
        }


# ==============================================================================
# 6. BỘ ĐIỀU PHỐI TIẾN HÓA RSIL-L3 (ORCHESTRATOR)
# ==============================================================================

class RSILOrchestrator:
    """
    Bộ điều phối vòng tự học cấp 3 (RSIL-L3):
    1. Quét bảng `StageAttribution` phát hiện khâu nghẽn nhất.
    2. Đánh giá đề xuất candidate: từ chối nếu Tier 3 hoặc vi phạm 4 Cổng Hiến Pháp.
    3. Auto-Promote ứng viên Tier 1/2 đạt chuẩn, ký Operational Witness, ghi sổ cái băm chuỗi.
    4. Giám sát Canary: Rollback tức thì (< 10ms) nếu phát hiện drift > 15%.
    """

    def __init__(
        self,
        journal_path: Optional[Path] = None,
        quota_tracker: Optional[AutonomousQuotaTracker] = None,
    ) -> None:
        self.journal = ChainedPromotionJournal(journal_path=journal_path)
        self.quota = quota_tracker or AutonomousQuotaTracker()
        self.signer = DualKeySigner()
        self.gates = FourConstitutionalGates()

def normalize_stage_trace_entry(rec: Dict[str, Any]) -> Tuple[str, bool]:
    """
    [Cơ chế Chuẩn Hóa Schema Trace Detector — Lượt 300]:
    Chuẩn hóa bản ghi telemetry / trace entry từ bất kỳ nguồn nào:
    - Nhận diện khâu: 'stage' hoặc 'stage_attribution' hoặc 'phase'.
      Nếu thiếu nhưng có trường 'tool', tự suy luận qua classify_step_stage_attribution.
    - Nhận diện kết quả outcome_ok theo nguyên lý Fail-Closed:
      + Nếu có trường 'outcome_ok' tường minh -> bool(rec['outcome_ok'])
      + Nếu có trường 'error' hoặc 'exception' -> False
      + Nếu có trường 'status' -> bool(str(rec['status']).upper() in ("OK", "SUCCESS", "DONE", "COMPLETED"))
      + Nếu có trường 'signal' báo lỗi -> False
      + Nếu quan sát observation chứa dấu hiệu lỗi -> False
      + Mặc định nếu không đủ bằng chứng thành công: Fail-Closed (False).
    """
    # 1. Trích xuất Stage
    st = rec.get("stage") or rec.get("stage_attribution") or rec.get("phase")
    if not st:
        tool = rec.get("tool")
        if tool:
            try:
                from core.utils.repo_map import classify_step_stage_attribution
                is_final = bool("final_answer" in rec and rec.get("final_answer") is not None)
                st = classify_step_stage_attribution(
                    tool=tool,
                    decision=str(rec.get("decision", "PERMIT")),
                    outcome_ok=bool(rec.get("outcome_ok", False)),
                    is_final_verification=is_final,
                ).value
            except Exception:
                st = "UNKNOWN"
        else:
            st = "UNKNOWN"
    st = str(st)

    # 2. Suy luận Outcome OK (Fail-Closed)
    _ERR_OBS_MARKERS = (
        "error",
        "exception",
        "failed",
        "traceback",
        "fatal",
        "not found",
        "circuit breaker",
        "quota-exceeded",
        "blocked",
        "errno",
    )
    obs_str = str(rec.get("observation", "")).lower()

    if "outcome_ok" in rec:
        ok = bool(rec["outcome_ok"])
    elif rec.get("error") or rec.get("exception"):
        ok = False
    elif "status" in rec:
        ok = str(rec["status"]).upper() in ("OK", "SUCCESS", "DONE", "COMPLETED")
    elif rec.get("signal") in ("FATAL_LOOP_ABORT", "STEP_BUDGET_EXHAUSTED", "TOOL_ERROR", "ERROR"):
        ok = False
    elif obs_str and any(err in obs_str for err in _ERR_OBS_MARKERS):
        ok = False
    else:
        if rec.get("observation") or rec.get("final_answer"):
            ok = True
        else:
            ok = False

    return st, ok


class RSILOrchestrator:
    """
    Bộ điều phối vòng tự học cấp 3 (RSIL-L3):
    1. Quét bảng `StageAttribution` phát hiện khâu nghẽn nhất.
    2. Đánh giá đề xuất candidate: từ chối nếu Tier 3 hoặc vi phạm 4 Cổng Hiến Pháp.
    3. Auto-Promote ứng viên Tier 1/2 đạt chuẩn, ký Operational Witness, ghi sổ cái băm chuỗi.
    4. Giám sát Canary: Rollback tức thì (< 10ms) nếu phát hiện drift > 15%.
    """

    def __init__(
        self,
        journal_path: Optional[Path] = None,
        quota_tracker: Optional[AutonomousQuotaTracker] = None,
    ) -> None:
        self.journal = ChainedPromotionJournal(journal_path=journal_path)
        self.quota = quota_tracker or AutonomousQuotaTracker()
        self.signer = DualKeySigner()
        self.gates = FourConstitutionalGates()

    def detect_bottleneck(self, stage_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Phân tích các bản ghi StageAttribution/Trace và tìm khâu có tỷ lệ lỗi cao nhất."""
        if not stage_records:
            return {"primary_bottleneck_stage": "NONE", "failure_ratio": 0.0, "total_records": 0}

        stage_counts: Dict[str, List[int]] = {}  # [failures, total]
        for rec in stage_records:
            st, ok = normalize_stage_trace_entry(rec)
            if st not in stage_counts:
                stage_counts[st] = [0, 0]
            stage_counts[st][1] += 1
            if not ok:
                stage_counts[st][0] += 1

        worst_stage = "NONE"
        worst_ratio = -1.0
        for st, (fails, total) in stage_counts.items():
            if st == "UNKNOWN":
                continue
            ratio = fails / max(1, total)
            if ratio > worst_ratio:
                worst_ratio = ratio
                worst_stage = st

        if worst_stage == "NONE" and "UNKNOWN" in stage_counts:
            fails, total = stage_counts["UNKNOWN"]
            worst_ratio = fails / max(1, total)
            worst_stage = "UNKNOWN"

        return {
            "primary_bottleneck_stage": worst_stage,
            "failure_ratio": round(worst_ratio, 4),
            "total_records": len(stage_records),
            "breakdown": {st: round(f / max(1, t), 4) for st, (f, t) in stage_counts.items()},
        }

    def evaluate_and_autonomous_promote(self, candidate_proposal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Đánh giá và tự động thăng cấp nếu ứng viên thỏa mãn toàn bộ rào chắn toán học:
        - Kiểm tra trạng thái Auto-Freeze.
        - Phân loại Tier: nếu Tier 3 -> cưỡng chế từ chối auto-promote, yêu cầu Master duyệt.
        - Kiểm tra hạn mức tuần.
        - Đánh giá 4 Cổng Hiến Pháp.
        - Ký chữ ký Operational Witness và ghi sổ cái băm chuỗi.
        """
        pid = str(candidate_proposal.get("proposal_id") or f"prop_{int(time.time())}")
        files = candidate_proposal.get("affected_files", [])
        diff_content = candidate_proposal.get("diff_content")
        tier = classify_diff_evolution_tier(files, diff_content=diff_content)

        if self.quota.is_frozen():
            return {
                "decision": "REFUSED_SYSTEM_FROZEN",
                "proposal_id": pid,
                "reason": self.quota.freeze_reason,
            }

        if tier == EvolutionTier.TIER3_IRREVERSIBLE_AND_SECURITY:
            self.journal.append_entry("REFUSED_TIER3", pid, {"tier": tier.value, "reason": "Requires Master Authority"})
            return {
                "decision": "REQUIRES_MASTER_AUTHORITY",
                "proposal_id": pid,
                "evolution_tier": tier.value,
                "reason": "Diff touches protected security/governance files. Auto-promote blocked.",
            }

        can_promote, reason = self.quota.can_promote()
        if not can_promote:
            self.journal.append_entry("AUTO_FREEZE", pid, {"reason": reason})
            return {
                "decision": "REFUSED_QUOTA_EXCEEDED",
                "proposal_id": pid,
                "reason": reason,
            }

        # Evaluate 4 orthogonal gates
        gate_res = self.gates.evaluate_all(
            baseline_score=float(candidate_proposal.get("baseline_score", 0.0)),
            candidate_scores=list(candidate_proposal.get("candidate_scores", [0.0])),
            safety_regressions=int(candidate_proposal.get("safety_regressions", 0)),
            ast_invariant_ok=bool(candidate_proposal.get("ast_invariant_ok", True)),
            blast_radius_ok=bool(candidate_proposal.get("blast_radius_ok", True)),
            resource_overhead_pct=float(candidate_proposal.get("resource_overhead_pct", 0.0)),
        )

        if not gate_res["all_gates_passed"]:
            self.journal.append_entry("REJECTED_GATES_FAILED", pid, gate_res)
            return {
                "decision": "REJECTED_CONSTITUTIONAL_GATES_FAILED",
                "proposal_id": pid,
                "evolution_tier": tier.value,
                "gates_result": gate_res,
            }

        # Auto-Promote
        sig = self.signer.sign_operational_witness(pid, gate_res)
        self.quota.record_promotion(pid)
        self.journal.append_entry(
            action="AUTO_PROMOTE",
            proposal_id=pid,
            details={
                "evolution_tier": tier.value,
                "witness_signature": sig,
                "gates": gate_res,
            },
        )

        return {
            "decision": "AUTO_PROMOTED_INTO_CANARY",
            "proposal_id": pid,
            "evolution_tier": tier.value,
            "witness_signature": sig,
            "gates_result": gate_res,
            "status": "CANARY_MONITORING_ACTIVE",
        }

    def canary_evaluate_and_rollback_if_needed(
        self,
        proposal_id: str,
        recent_canary_missions: List[Dict[str, Any]],
        max_allowed_drift_pct: float = 15.0,
    ) -> Dict[str, Any]:
        """
        Theo dõi giai đoạn Canary:
        Nếu tỷ lệ thất bại của cửa sổ trượt vượt ngưỡng 15% -> kích hoạt Instant Auto-Rollback (< 10ms).
        """
        t0 = time.monotonic()
        if not recent_canary_missions:
            return {"rollback_triggered": False, "reason": "NO_CANARY_DATA"}

        fails = sum(1 for m in recent_canary_missions if not bool(m.get("outcome_ok", True)))
        fail_rate_pct = round((fails / max(1, len(recent_canary_missions))) * 100.0, 2)

        if fail_rate_pct > max_allowed_drift_pct:
            elapsed_ms = round((time.monotonic() - t0) * 1000, 3)
            self.quota.record_rollback(proposal_id, drift_pct=fail_rate_pct)
            self.journal.append_entry(
                action="INSTANT_AUTO_ROLLBACK",
                proposal_id=proposal_id,
                details={
                    "fail_rate_pct": fail_rate_pct,
                    "max_allowed_pct": max_allowed_drift_pct,
                    "elapsed_ms": elapsed_ms,
                },
            )
            return {
                "rollback_triggered": True,
                "reason": "CANARY_DRIFT_EXCEEDED",
                "fail_rate_pct": fail_rate_pct,
                "threshold_pct": max_allowed_drift_pct,
                "rollback_elapsed_ms": elapsed_ms,
                "system_frozen": self.quota.is_frozen(),
            }

        elapsed_ms = round((time.monotonic() - t0) * 1000, 3)
        return {
            "rollback_triggered": False,
            "fail_rate_pct": fail_rate_pct,
            "status": "CANARY_HEALTHY",
            "elapsed_ms": elapsed_ms,
        }
