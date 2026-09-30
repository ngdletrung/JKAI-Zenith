"""
🏛️ JKAI Zenith — 7-Predicate Model Failure Evaluator
File: core/os/cognition/model_failure_predicates.py
Purpose: Chốt chặn 2 theo chỉ đạo Master & Opencode: Định nghĩa vận hành chính xác 
         và đánh giá tự động 7 điều kiện để kết luận MODEL_BEHAVIOR_FAILURE.
"""

from typing import Dict, Any, Tuple
from dataclasses import dataclass, asdict


@dataclass
class PredicateEvaluation:
    name: str
    passed: bool
    rationale: str
    owner_if_failed: str


@dataclass
class ModelFailureReport:
    is_pure_model_failure: bool
    failure_category: str
    attributed_owner: str
    predicates: Dict[str, bool]
    details: Dict[str, str]

    def to_dict(self) -> dict:
        return asdict(self)


class ModelFailureEvaluator:
    """
    Bộ đánh giá tự động 7 vị từ (7-Predicate Evaluator) trên Execution Trace:
    Đảm bảo tuyệt đối không đổ lỗi cho Model khi lỗi xuất phát từ Kernel/Controller/Tool/RAG.
    """

    @classmethod
    def evaluate(cls, trace: Dict[str, Any]) -> ModelFailureReport:
        """
        Đánh giá trace dựa trên 7 vị từ logic độc lập.
        """
        p1 = cls.p1_is_context_sufficient(trace)
        p2 = cls.p2_is_intent_accurate(trace)
        p3 = cls.p3_is_routing_correct(trace)
        p4 = cls.p4_is_authority_granted(trace)
        p5 = cls.p5_does_tool_capability_exist(trace)
        p6 = cls.p6_is_schema_delivered_intact(trace)
        p7 = cls.p7_did_model_diverge(trace)

        preds = {
            "P1_context_sufficient": p1.passed,
            "P2_intent_accurate": p2.passed,
            "P3_routing_correct": p3.passed,
            "P4_authority_granted": p4.passed,
            "P5_tool_exists": p5.passed,
            "P6_schema_intact": p6.passed,
            "P7_model_diverged": p7.passed,
        }

        details = {
            "P1": p1.rationale,
            "P2": p2.rationale,
            "P3": p3.rationale,
            "P4": p4.rationale,
            "P5": p5.rationale,
            "P6": p6.rationale,
            "P7": p7.rationale,
        }

        # Kiểm tra theo thứ tự ưu tiên gán lỗi:
        # Nếu bất kỳ điều kiện tiên quyết nào (P1 -> P6) bị thất bại, lỗi KHÔNG THUỘC VỀ MODEL!
        if not p1.passed:
            return ModelFailureReport(
                is_pure_model_failure=False,
                failure_category="RAG_RETRIEVAL_FAILURE",
                attributed_owner=p1.owner_if_failed,
                predicates=preds,
                details=details,
            )
        if not p2.passed:
            return ModelFailureReport(
                is_pure_model_failure=False,
                failure_category="INTENT_MISCLASSIFICATION",
                attributed_owner=p2.owner_if_failed,
                predicates=preds,
                details=details,
            )
        if not p3.passed:
            return ModelFailureReport(
                is_pure_model_failure=False,
                failure_category="ROUTING_MISCONFIGURATION",
                attributed_owner=p3.owner_if_failed,
                predicates=preds,
                details=details,
            )
        if not p4.passed:
            return ModelFailureReport(
                is_pure_model_failure=False,
                failure_category="AUTHORITY_POLICY_BLOCKED",
                attributed_owner=p4.owner_if_failed,
                predicates=preds,
                details=details,
            )
        if not p5.passed:
            return ModelFailureReport(
                is_pure_model_failure=False,
                failure_category="TOOL_INFRASTRUCTURE_UNAVAILABLE",
                attributed_owner=p5.owner_if_failed,
                predicates=preds,
                details=details,
            )
        if not p6.passed:
            return ModelFailureReport(
                is_pure_model_failure=False,
                failure_category="SCHEMA_CORRUPTION_OR_CUTOFF",
                attributed_owner=p6.owner_if_failed,
                predicates=preds,
                details=details,
            )

        # Cả P1 -> P6 đều hoàn hảo, nếu model trệch hướng (P7 == True):
        if p7.passed:
            return ModelFailureReport(
                is_pure_model_failure=True,
                failure_category="MODEL_BEHAVIOR_FAILURE",
                attributed_owner="MODEL",
                predicates=preds,
                details=details,
            )

        # Không có lỗi nào
        return ModelFailureReport(
            is_pure_model_failure=False,
            failure_category="NO_FAILURE_DETECTED",
            attributed_owner="NONE",
            predicates=preds,
            details=details,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 7 VỊ TỪ CỤ THỂ (OPERATIONAL DEFINITIONS)
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def p1_is_context_sufficient(trace: Dict[str, Any]) -> PredicateEvaluation:
        """P1: Ngữ cảnh từ RAG/Bộ nhớ có đầy đủ và không bị lỗi mạng/timeout không?"""
        kb_context = trace.get("context", {}).get("kb_context", "") or ""
        error_flags = ["[TIMEOUT]", "[SEARCH-ERR]", "ConnectionRefused", "Errno 111"]
        if any(err in kb_context for err in error_flags):
            return PredicateEvaluation("P1_context_sufficient", False, "Context chứa cờ lỗi hạ tầng/timeout.", "RAG")
        
        need_kb = trace.get("intent", {}).get("need_kb", False)
        if need_kb and len(kb_context.strip()) < 20:
            return PredicateEvaluation("P1_context_sufficient", False, "Yêu cầu tri thức nhưng context trả về rỗng.", "RAG")
        
        return PredicateEvaluation("P1_context_sufficient", True, "Context đầy đủ hợp lệ.", "RAG")

    @staticmethod
    def p2_is_intent_accurate(trace: Dict[str, Any]) -> PredicateEvaluation:
        """P2: Phân loại ý định từ CentralIntentRouter có chính xác không?"""
        intent = trace.get("intent", {})
        mode = intent.get("mode")
        confidence = intent.get("confidence", 1.0)
        
        if not mode or mode in ("UNKNOWN", "INVALID") or confidence < 0.50:
            return PredicateEvaluation("P2_intent_accurate", False, f"Mode không hợp lệ hoặc độ tin cậy thấp: {mode} ({confidence})", "CONTROLLER")
        
        return PredicateEvaluation("P2_intent_accurate", True, f"Intent chuẩn xác: {mode} ({confidence})", "CONTROLLER")

    @staticmethod
    def p3_is_routing_correct(trace: Dict[str, Any]) -> PredicateEvaluation:
        """P3: Định tuyến pipeline và vai trò mô hình có chính xác không?"""
        routing = trace.get("routing", {})
        pipeline = routing.get("pipeline")
        role = routing.get("role")
        model = routing.get("model")

        if not pipeline or not role or role == "UNKNOWN":
            return PredicateEvaluation("P3_routing_correct", False, "Thiếu định tuyến pipeline hoặc role hợp lệ.", "ROUTER")
        if model and "cpu" in str(routing.get("hardware", "")).lower() and routing.get("is_heavy_reasoning"):
            return PredicateEvaluation("P3_routing_correct", False, "Gán nhầm mô hình nặng lên CPU gây treo.", "ROUTER")

        return PredicateEvaluation("P3_routing_correct", True, f"Định tuyến chuẩn: {pipeline}/{role} ({model})", "ROUTER")

    @staticmethod
    def p4_is_authority_granted(trace: Dict[str, Any]) -> PredicateEvaluation:
        """P4: Thẩm quyền thực thi có được Kernel phê duyệt không?"""
        authority = trace.get("authority", {})
        is_blocked = authority.get("is_blocked", False)
        denial_reason = authority.get("denial_reason")

        if is_blocked or denial_reason:
            return PredicateEvaluation("P4_authority_granted", False, f"Bị chặn bởi Policy/Security Kernel: {denial_reason}", "POLICY_KERNEL")

        return PredicateEvaluation("P4_authority_granted", True, "Thẩm quyền đã được phê duyệt hợp lệ.", "POLICY_KERNEL")

    @staticmethod
    def p5_does_tool_capability_exist(trace: Dict[str, Any]) -> PredicateEvaluation:
        """P5: Công cụ mà nhiệm vụ yêu cầu có thực sự tồn tại trong Runtime không?"""
        requested_tool = trace.get("execution", {}).get("tool_name")
        available_tools = trace.get("execution", {}).get("available_tools", [])

        if requested_tool and requested_tool not in available_tools:
            return PredicateEvaluation("P5_tool_exists", False, f"Công cụ '{requested_tool}' không có trong Registry.", "EXECUTOR")

        return PredicateEvaluation("P5_tool_exists", True, "Công cụ yêu cầu tồn tại hợp lệ.", "EXECUTOR")

    @staticmethod
    def p6_is_schema_delivered_intact(trace: Dict[str, Any]) -> PredicateEvaluation:
        """P6: Lược đồ schema/JSON có được chuyển giao nguyên vẹn cho model không?"""
        delivered_schema = trace.get("schema_delivery", {})
        is_corrupted = delivered_schema.get("is_corrupted", False)
        is_truncated = delivered_schema.get("is_truncated", False)

        if is_corrupted or is_truncated:
            return PredicateEvaluation("P6_schema_intact", False, "Schema bị cắt cụt token hoặc lỗi JSON escaping từ middleware.", "RUNTIME")

        return PredicateEvaluation("P6_schema_intact", True, "Schema chuyển giao nguyên vẹn không suy hao.", "RUNTIME")

    @staticmethod
    def p7_did_model_diverge(trace: Dict[str, Any]) -> PredicateEvaluation:
        """P7: Model có thực sự chọn sai hành động / trệch hướng / hallucinate không?"""
        model_out = trace.get("model_output", {})
        action_valid = model_out.get("is_action_valid", True)
        is_hallucinating = model_out.get("is_hallucinating", False)
        is_premature_stop = model_out.get("is_premature_stop", False)

        if not action_valid or is_hallucinating or is_premature_stop:
            reasons = []
            if not action_valid: reasons.append("Hành động sai logic")
            if is_hallucinating: reasons.append("Bịa đặt dữ kiện")
            if is_premature_stop: reasons.append("Dừng sớm trước khi hoàn thành")
            return PredicateEvaluation("P7_model_diverged", True, f"Mô hình trệch hướng: {', '.join(reasons)}", "MODEL")

        return PredicateEvaluation("P7_model_diverged", False, "Mô hình hành động hợp lệ, không trệch hướng.", "MODEL")


# Singleton instance
model_failure_evaluator = ModelFailureEvaluator()
