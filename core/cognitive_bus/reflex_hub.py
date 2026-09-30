# -*- coding: utf-8 -*-
"""
[ZENITH FILE DIRECTIVE]
- File: core/cognitive_bus/reflex_hub.py
- Role: Central Multi-Task Sovereign Reflex Hub (Bilingual EN/VI System-1 Substrate).
- Ownership: Master LeeTrung
- Status: Active | Version: SDS v28.0

Invariants:
  1. Single Central Hub (.keywork.md Part IX.3): Consolidates all 6 System-1 non-autoregressive
     decision tasks into one reusable bilingual (EN/VI) hub backed by ReflexEngineBackend.
  2. Permanent 2-NEVER Lock (.keywork.md Part VII): System-1 reflex NEVER controls FSM state
     transitions and NEVER overrides Policy Gate. Specifically, `audit_plan_safety` is
     permanently locked to `advisory_only=True` in code and raises PermissionError if any
     caller attempts to use it as an enforcement gate (`advisory_only=False`).
  3. Fail-Closed Governance (ADR-0003 & ADR-0005): Exposes honest per-language calibration
     state ("uncalibrated" until Master Gold Dataset reaches n >= 200 and ECE <= 0.15).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.cognitive_bus.backends.reflex_engine_backend import (
    FORBIDDEN_COMPLETION_LABELS,
    ReflexEngineBackend,
    detect_language_bcp47,
    detect_language_with_trace,
    validate_no_model_completion_label,
)
from core.cognitive_bus.decision_substrate_adapter import (
    DecisionPrimitive,
    TriTierDecisionAdapter,
)
from core.cognitive_bus.reflex_evolution import (
    ROOT_DIR,
    ReflexEvolutionManager,
    get_reflex_evolution_manager,
)
from core.governance.confidence_policy import (
    ActionClass,
    PolicyVerdict,
    decide as decide_confidence_policy,
)

DEFAULT_SOAK_TELEMETRY_PATH = ROOT_DIR / "data" / "telemetry" / "reflex_cache_soak_telemetry.jsonl"

# Step 1 Hard Lock: Reuse canonical 8-label DECISION_VOCAB and 21-label ACTION_VOCAB.
# Creating any parallel 5-label routing enum is strictly forbidden.
DECISION_VOCAB: Tuple[str, ...] = (
    "ALLOW",
    "CLARIFY",
    "DENY",
    "ESCALATE",
    "HANDLE_FAULT",
    "MODIFY",
    "RECOVER",
    "REJECT_INVALID_REASONING",
)

ACTION_VOCAB: Tuple[str, ...] = (
    "ANSWER",
    "ENABLE_COMPATIBILITY_ADAPTER",
    "ENGAGE_LOAD_SHEDDING",
    "ESCALATE_TO_MASTER",
    "EXECUTE",
    "EXPLAIN_FALLACY",
    "PURGE_INODES_AND_ROTATE",
    "REDUCE_DNS_TTL_BEFORE_MIGRATION",
    "REFUSE_WITH_POLICY_RULE",
    "REJECT_IDEMPOTENCY_MISMATCH",
    "REQUEST_CONSISTENCY_LEVEL",
    "REQUEST_LEGAL_PRECEDENCE",
    "REQUEST_METRIC_OBJECTIVE",
    "REQUEST_TRANSACTION_PATTERN",
    "REQUIRE_FENCING_TOKEN",
    "RESTART_WORKER_DRAIN",
    "SEPARATE_TASK_THREAD_POOLS",
    "SYNC_NTP_CLOCK",
    "TRIGGER_KEY_REVOCATION_CEREMONY",
    "USE_ATOMIC_FILE_CREATION",
    "USE_CONSTANT_TIME_COMPARE",
)

# Step 2 Hard Fence: Model can NEVER emit COMPLETE / COMPLETE_CANDIDATE.
# It may only propose VERIFY_AND_CLOSE; Runtime CompletionAuthority alone grants completion.
COMPLETION_PROPOSAL_VOCAB: Tuple[str, ...] = (
    "VERIFY_AND_CLOSE",
    "CONTINUE_EXECUTION",
    "CLARIFY",
)

DECISION_CRITERIA_DESCRIPTIONS: Dict[str, str] = {
    "ALLOW": "Safe, valid, read-only or policy-compliant request ready to answer or execute",
    "CLARIFY": "Ambiguous request, conflicting constraints, or missing required parameter",
    "DENY": "Violates security policy, negative list, destructive rm -rf, SSRF, or credential exposure",
    "ESCALATE": "Requires Master authority, key revocation ceremony, or critical incident escalation",
    "HANDLE_FAULT": "System fault such as NTP clock skew, worker drain, or hardware/process hang",
    "MODIFY": "Proposal requires safety modification (atomic file write, constant-time compare, fencing token)",
    "RECOVER": "Resource exhaustion or compatibility failure requiring inode purge, load shedding, or adapter",
    "REJECT_INVALID_REASONING": "Logical fallacy, affirming the consequent, pigeonhole violation, or spurious correlation",
}


class SovereignReflexHub:
    """
    Central Multi-Task Bilingual (EN/VI) Decision Hub for JKAI-Zenith.

    Provides 6 standardized System-1 capabilities:
      1. classify_intent_and_route    (Fast-Path vs Deep-Path & canonical DECISION_VOCAB/ACTION_VOCAB routing)
      2. audit_plan_safety            (Critic pre-screen — PERMANENTLY advisory_only=True)
      3. verify_cache_and_rerank      (Semantic cache antonym/negation guard & RAG rerank)
      4. audit_answer_quality         (Post-generation grounding & rubric quality score)
      5. shortlist_capabilities       (Tournament bracket shortlisting for N > 12 skills/tools)
      6. batch_triage_experiences     (Length-sorted batch triage for Experience Distiller)
    """

    def __init__(
        self,
        backend: Optional[ReflexEngineBackend] = None,
        evolution_manager: Optional[ReflexEvolutionManager] = None,
        record_shadow: bool = False,
        soak_telemetry_path: Optional[Path] = None,
    ):
        self.evolution = evolution_manager or get_reflex_evolution_manager()
        self.backend = backend or ReflexEngineBackend(evolution_manager=self.evolution)
        if not self.backend.is_loaded():
            self.backend.load()
        self.adapter = TriTierDecisionAdapter(
            enable_mock=False,
            record_shadow=record_shadow,
            tier2_backend=self.backend,
        )
        self.soak_telemetry_path = Path(soak_telemetry_path or DEFAULT_SOAK_TELEMETRY_PATH)
        self._soak_stats: Dict[str, int] = {
            "total_cache_checks": 0,
            "antonym_blocks": 0,
            "cache_safe_passes": 0,
        }

    # ------------------------------------------------------------------
    # Task 1: Intent, Complexity & Canonical Vocab Routing (EN / VI)
    # ------------------------------------------------------------------

    def classify_intent_and_route(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        action_class: ActionClass = ActionClass.READ,
    ) -> Dict[str, Any]:
        """
        Single-pass bilingual evaluation of request routing path ("fast_path" vs "deep_path").
        Respects ADR-0003 confidence policy via TriTierDecisionAdapter.
        """
        state = {"body": query, "context": context or {}}
        lang_trace = detect_language_with_trace(query)
        lang = str(lang_trace["language"])
        q_route = (
            "Yêu cầu này nên đi theo luồng xử lý nào?"
            if lang == "vi"
            else "Which execution path should handle this request?"
        )
        verdict = self.adapter.evaluate_parallel_batch(
            state=state,
            questions=[(DecisionPrimitive.CHOICE, q_route, ["fast_path", "deep_path"])],
            action_class=action_class,
        )
        pkt = verdict.judgements[q_route]
        return {
            "route": str(pkt.result),
            "confidence": pkt.confidence,
            "distribution": dict(pkt.distribution),
            "language": lang,
            "lang_detect_layer": lang_trace["layer"],
            "domain_prior": lang_trace["domain_prior"]["domain"],
            "execution_tier": verdict.execution_tier.value,
            "calibration_state": self.evolution.get_calibration_state(lang),
            "latency_ms": verdict.overall_latency_ms,
        }

    def route_with_canonical_vocab(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        action_class: ActionClass = ActionClass.READ,
        decision_options: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Step 1 Canonical Router: Expresses all routing, decision, action, and urgency/risk
        needs strictly as CHOICE and SCORE questions over existing DECISION_VOCAB (8)
        and ACTION_VOCAB (21, via tournament group_size=12), without any duplicate enum.
        Enforces the wider SCORE abstention band (THETA_SCORE_UNCAL_FIT_PLACEHOLDER = 0.92).
        """
        dec_opts = list(decision_options) if decision_options is not None else list(DECISION_VOCAB)
        invalid_dec = [opt for opt in dec_opts if str(opt).strip().upper() not in DECISION_VOCAB]
        if invalid_dec:
            raise ValueError(
                f"Step 1 Governance Violation: Non-canonical decision labels {invalid_dec!r} are forbidden. "
                f"Must use canonical DECISION_VOCAB: {DECISION_VOCAB!r}"
            )

        state = {"body": query, "context": context or {}}
        lang_trace = detect_language_with_trace(query)
        lang = str(lang_trace["language"])
        cal_state = self.evolution.get_calibration_state(lang)

        q_route = "Yêu cầu này nên đi theo luồng xử lý nào?" if lang == "vi" else "Which execution path should handle this request?"
        q_dec = "Quyết định chuẩn nào trong DECISION_VOCAB phù hợp nhất?" if lang == "vi" else "Which canonical decision in DECISION_VOCAB applies?"
        q_urg = "Mức độ khẩn cấp và rủi ro từ 0 đến 4?" if lang == "vi" else "What is the urgency and risk level from 0 to 4?"

        out = self.backend.predict(
            state=state,
            questions=[
                (DecisionPrimitive.CHOICE, q_route, ["fast_path", "deep_path"]),
                (DecisionPrimitive.CHOICE, q_dec, dec_opts),
                (DecisionPrimitive.SCORE, q_urg, ["0", "1", "2", "3", "4"]),
            ],
            descriptions=DECISION_CRITERIA_DESCRIPTIONS,
        )
        route_pkt = out[q_route]
        dec_pkt = out[q_dec]
        urg_pkt = out[q_urg]

        # Tournament over the 21 canonical actions (group_size=12 respects the 20-option ceiling)
        action_shortlist = self.shortlist_capabilities(
            query=query,
            candidates=list(ACTION_VOCAB),
            group_size=12,
            top_k=3,
        )

        # Apply ADR-0003 confidence policy (including wider 0.92 abstention band for uncalibrated SCORE)
        choice_policy = decide_confidence_policy(dec_pkt, action_class, cal_state)
        score_policy = decide_confidence_policy(urg_pkt, action_class, cal_state)

        return {
            "route": str(route_pkt.result),
            "canonical_decision": str(dec_pkt.result),
            "canonical_action": str(action_shortlist["winner"]),
            "action_shortlist": list(action_shortlist["shortlist"]),
            "urgency_score": float(urg_pkt.result),
            "score_abstained": (score_policy.verdict != PolicyVerdict.AUTHORIZE),
            "score_threshold_used": score_policy.threshold_used,
            "choice_policy_verdict": choice_policy.verdict.value,
            "score_policy_verdict": score_policy.verdict.value,
            "language": lang,
            "lang_detect_layer": lang_trace["layer"],
            "calibration_state": cal_state,
        }

    def propose_completion_verification(
        self,
        state: Dict[str, Any],
        query: str = "",
        custom_options: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Step 2 Completion Fence: Models NEVER emit COMPLETE or COMPLETE_CANDIDATE.
        Emits a 'VERIFY_AND_CLOSE' (or 'CONTINUE_EXECUTION' / 'CLARIFY') proposal
        for Runtime CompletionAuthority to verify physical artifacts, schema, and state transition.
        """
        opts = list(custom_options) if custom_options is not None else list(COMPLETION_PROPOSAL_VOCAB)
        validate_no_model_completion_label(opts)

        q_comp = "Trạng thái hiện tại đã đủ bằng chứng để đề xuất VERIFY_AND_CLOSE chưa?"
        pkt = self.backend.predict(
            state={"state": state, "query": query},
            questions=[(DecisionPrimitive.CHOICE, q_comp, opts)],
        )[q_comp]

        return {
            "proposal": str(pkt.result),
            "completion_granted": False,
            "authority": "Runtime.CompletionAuthority",
            "requires_artifact_and_state_transition": True,
            "confidence": pkt.confidence,
            "distribution": dict(pkt.distribution),
        }

    # ------------------------------------------------------------------
    # Task 2: Critic Plan Safety Pre-Screen (PERMANENTLY ADVISORY ONLY)
    # ------------------------------------------------------------------

    def audit_plan_safety(
        self,
        plan: Any,
        query: str = "",
        *,
        advisory_only: bool = True,
    ) -> Dict[str, Any]:
        """
        Pre-screens an execution plan or command for destructive/injection risks.
        PERMANENT 2-NEVER INVARIANT: This method is permanently locked to
        `advisory_only=True` and CANNOT be used as an authorization or blocking gate.
        """
        if advisory_only is not True:
            raise PermissionError(
                "2-NEVER Invariant Violation: audit_plan_safety is permanently locked to "
                "advisory_only=True. System-1 reflex must NEVER act as a hard execution gate."
            )

        state = {"body": plan, "query": query}
        lang = detect_language_bcp47(f"{query} {plan}")
        q_risk = (
            "Hành động này có nguy hiểm không?"
            if lang == "vi"
            else "Is this action dangerous or destructive?"
        )
        out = self.backend.predict(
            state=state,
            questions=[(DecisionPrimitive.BOOLEAN, q_risk, None)],
        )
        pkt = out[q_risk]
        risk_prob = float(pkt.distribution.get("true", pkt.result))
        return {
            "advisory_only": True,
            "can_authorize_execution": False,
            "risk_detected": risk_prob >= 0.5,
            "risk_probability": round(risk_prob, 6),
            "confidence": pkt.confidence,
            "language": lang,
            "calibration_state": self.evolution.get_calibration_state(lang),
            "latency_ms": pkt.latency_ms,
        }

    # ------------------------------------------------------------------
    # Task 3: Cognitive Memory Cache Verification & RAG Reranking
    # ------------------------------------------------------------------

    def verify_cache_and_rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 3,
    ) -> Dict[str, Any]:
        """
        Pure-advisory semantic guard for CognitiveMemory (`check_reflex`) and RAG.
        1. Detects antonym / negation inversions between `query` and `cached_query`
           (e.g. 'bật tường lửa' vs 'tắt tường lửa', 'enable' vs 'disable', 'xóa' vs 'sao lưu')
           to prevent semantic cache poisoning when cosine similarity is high.
        2. Reranks valid candidates by semantic relevance.
        """
        if not candidates:
            return {
                "cache_safe": False,
                "best_candidate": None,
                "accepted_candidates": [],
                "rejected_antonym_count": 0,
            }

        accepted: List[Dict[str, Any]] = []
        rejected_antonyms = 0
        q_equiv = "Hai yêu cầu này có cùng ý định ngữ nghĩa và không đối lập nhau không?"

        for raw_cand in candidates:
            cand = (
                {"text": raw_cand, "original_query": raw_cand, "score": 0.90}
                if isinstance(raw_cand, str)
                else dict(raw_cand)
            )
            cached_q = str(cand.get("original_query") or cand.get("query") or cand.get("text") or "")
            if cached_q and self.backend._has_antonym_conflict(query, cached_q):
                rejected_antonyms += 1
                continue

            state = {"query": query, "cached_query": cached_q or str(cand.get("answer", ""))}
            pkt = self.backend.predict(
                state=state,
                questions=[(DecisionPrimitive.BOOLEAN, q_equiv, None)],
            )[q_equiv]
            equiv_prob = float(pkt.distribution.get("true", pkt.result))
            base_score = float(cand.get("score", 0.90))
            combined_score = round(0.65 * base_score + 0.35 * equiv_prob, 6)

            enriched = dict(cand)
            enriched["reflex_equiv_prob"] = round(equiv_prob, 6)
            enriched["reflex_combined_score"] = combined_score
            accepted.append(enriched)

        accepted.sort(key=lambda item: item.get("reflex_combined_score", 0.0), reverse=True)
        shortlist = accepted[: max(1, int(top_k))]
        best = shortlist[0] if shortlist else None
        cache_safe = bool(best is not None and best.get("reflex_equiv_prob", 0.0) >= 0.5)

        self._soak_stats["total_cache_checks"] += 1
        if rejected_antonyms > 0:
            self._soak_stats["antonym_blocks"] += rejected_antonyms
        if cache_safe:
            self._soak_stats["cache_safe_passes"] += 1

        try:
            self.soak_telemetry_path.parent.mkdir(parents=True, exist_ok=True)
            soak_record = {
                "timestamp": time.time(),
                "consumer": "CognitiveMemory.check_reflex",
                "query": query,
                "cache_safe": cache_safe,
                "rejected_antonym_count": rejected_antonyms,
                "cumulative_stats": dict(self._soak_stats),
            }
            with open(self.soak_telemetry_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(soak_record, ensure_ascii=False) + "\n")
        except Exception:
            pass

        return {
            "cache_safe": cache_safe,
            "best_candidate": best if cache_safe else None,
            "accepted_candidates": shortlist,
            "rejected_antonym_count": rejected_antonyms,
            "soak_stats": dict(self._soak_stats),
        }

    def get_soak_telemetry(self) -> Dict[str, Any]:
        """Returns cumulative soak telemetry counters for Consumer 1 (verify_cache_and_rerank)."""
        return {
            "consumer": "CognitiveMemory.check_reflex",
            "telemetry_path": str(self.soak_telemetry_path),
            **self._soak_stats,
        }

    # ------------------------------------------------------------------
    # Task 4: Post-Generation Answer Quality & Grounding Gate (Advisory)
    # ------------------------------------------------------------------

    def audit_answer_quality(
        self,
        query: str,
        answer: str,
        evidence: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates post-generation response quality on a 5-level rubric ["0","1","2","3","4"]
        and checks whether the response is grounded without error/refusal artifacts.
        """
        state = {"query": query, "body": answer, "evidence": evidence or ""}
        lang = detect_language_bcp47(f"{query} {answer}")
        q_score = "Đánh giá chất lượng câu trả lời từ 0 đến 4"
        q_ground = "Câu trả lời này có hợp lệ và an toàn để lưu trữ không?"

        out = self.backend.predict(
            state=state,
            questions=[
                (DecisionPrimitive.SCORE, q_score, ["0", "1", "2", "3", "4"]),
                (DecisionPrimitive.BOOLEAN, q_ground, None),
            ],
        )
        score_pkt = out[q_score]
        ground_pkt = out[q_ground]
        ground_prob = float(ground_pkt.distribution.get("true", ground_pkt.result))

        return {
            "advisory_only": True,
            "quality_score": float(score_pkt.result),
            "quality_distribution": dict(score_pkt.distribution),
            "is_grounded": ground_prob >= 0.5 and float(score_pkt.result) >= 2.0,
            "grounding_probability": round(ground_prob, 6),
            "confidence": round(min(score_pkt.confidence, ground_pkt.confidence), 6),
            "language": lang,
        }

    # ------------------------------------------------------------------
    # Task 5: Skill / Tool Tournament Shortlisting (N > 12 -> Top-K)
    # ------------------------------------------------------------------

    def shortlist_capabilities(
        self,
        query: str,
        candidates: List[str],
        descriptions: Optional[Dict[str, str]] = None,
        group_size: int = 12,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        Uses tournament bracket scoring (`predict_tournament`) to shortlist large
        skill/tool pools (e.g. 20-50 tools) down to top_k candidates in a few milliseconds.
        """
        lang = detect_language_bcp47(query)
        q_cap = (
            "Năng lực nào phù hợp nhất để thực thi yêu cầu này?"
            if lang == "vi"
            else "Which capability is best suited to execute this request?"
        )
        ranked, final_pkt = self.backend.predict_tournament(
            state={"body": query},
            question=q_cap,
            candidates=candidates,
            descriptions=descriptions,
            group_size=group_size,
            top_k=top_k,
        )
        return {
            "winner": final_pkt.result,
            "shortlist": [cand for cand, _ in ranked],
            "ranked_scores": [{"candidate": cand, "probability": prob} for cand, prob in ranked],
            "confidence": final_pkt.confidence,
            "language": lang,
            "latency_ms": final_pkt.latency_ms,
        }

    # ------------------------------------------------------------------
    # Task 6: Experience Distiller Batch Log Triage
    # ------------------------------------------------------------------

    def batch_triage_experiences(
        self,
        logs: List[Dict[str, Any]],
        sort_by_length: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Evaluates a batch of experience logs using length-sorted batching (`predict_batch`)
        to classify each log into actionable distillation categories.
        """
        if not logs:
            return []

        q_triage = "Nhóm lỗi nào phân loại chính xác sự cố này?"
        categories = [
            "network_transient",
            "permission_denied",
            "file_not_found",
            "contradictory_facts",
            "unknown_anomaly",
        ]
        batch_items = [
            (log_entry, [(DecisionPrimitive.CHOICE, q_triage, categories)])
            for log_entry in logs
        ]
        batch_outputs = self.backend.predict_batch(batch_items, sort_by_length=sort_by_length)

        triaged: List[Dict[str, Any]] = []
        for log_entry, pkt_map in zip(logs, batch_outputs):
            pkt = pkt_map[q_triage]
            triaged.append(
                {
                    "category": str(pkt.result),
                    "confidence": pkt.confidence,
                    "worth_distilling": str(pkt.result) in ("contradictory_facts", "permission_denied"),
                    "latency_ms": pkt.latency_ms,
                    "original": log_entry,
                }
            )
        return triaged

    # ------------------------------------------------------------------
    # Evolution & Instant Feedback Delegation
    # ------------------------------------------------------------------

    def learn_from_feedback(
        self,
        state: Any,
        question: str,
        target_value: Any,
        feedback_type: str = "POSITIVE_EXEMPLAR",
        primitive: str = "Choice",
        language: str = "*",
        reason: str = "",
    ) -> Dict[str, Any]:
        return self.evolution.learn_from_feedback(
            state=state,
            question=question,
            target_value=target_value,
            feedback_type=feedback_type,
            primitive=primitive,
            language=language,
            reason=reason,
        )


_DEFAULT_HUB: Optional[SovereignReflexHub] = None


def get_sovereign_reflex_hub() -> SovereignReflexHub:
    global _DEFAULT_HUB
    if _DEFAULT_HUB is None:
        _DEFAULT_HUB = SovereignReflexHub()
    return _DEFAULT_HUB
