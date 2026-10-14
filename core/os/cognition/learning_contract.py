# -*- coding: utf-8 -*-
"""
core/os/cognition/learning_contract.py
======================================
JKAI-ZENITH — Hiến Chương Tự Học & Hợp Đồng Dữ Liệu (Slice 5.1)
Author: Antigravity (Lead Architect) & OpenCode (Senior Red Team Auditor)
Directive: Master's 14 Learning Commandments, 4 Learning Layers & Anti-Cheating Protocol.

Các quy tắc cốt lõi:
1. Điều 4: Hợp đồng đề xuất học có hạn dùng (expires_at) và freshness policy.
2. Điều 8: An toàn đa cổng (Multi-gate safety) phủ quyết hiệu năng.
3. Điều 9: Đo vòng học toàn diện, chống gaming tỷ lệ Master minutes / proposals.
4. Điều 10: Quy tắc âm 2 chu kỳ kích hoạt LEARNING_FREEZE.
5. Điều 12: Cách ly tuyệt đối kho đề/đáp án thi (RAG Isolation & Exam Blocklist).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


# ==============================================================================
# HẰNG SỐ & ĐỊNH DANH CÁCH LY THI CỬ (EXAM ISOLATION CONSTANTS)
# ==============================================================================
EXAM_ISOLATE_DIR_NAME = "sealed_C"
EXAM_SEALED_PATHS = ("sealed_c", "sealed_exam", "data/eval/sealed")

FOUR_LEARNING_LAYERS = {
    "LAYER_1_IN_SESSION": "Working Memory / Context Stack (Ephemeral, 0 drift)",
    "LAYER_2_OPERATIONAL": "Dynamic Lexicons / Router Policy (Config/Rule, Rollback < 1ms)",
    "LAYER_3_SKILL": "Skill Library (Semantic versioned, AST checked, Isolated test)",
    "LAYER_4_MODEL_ADAPTER": "LoRA Adapter (Rank <= 16, 3-fold Golden Vault, Canary, Rollback < 10ms)",
}

MANDATORY_SAFETY_SUBGATES = (
    "PRIVILEGE_GATE",
    "DATA_LEAKAGE_GATE",
    "PROMPT_INJECTION_GATE",
    "DESTRUCTIVE_ACTION_GATE",
)


# ==============================================================================
# T1: HỢP ĐỒNG ĐỀ XUẤT HỌC & KIỂM TRA HẠN DÙNG (DATA CONTRACT & TTL)
# ==============================================================================
def validate_learning_proposal(proposal: Dict[str, Any]) -> Dict[str, Any]:
    """
    Kiểm tra hợp đồng đề xuất học theo Điều 4 & 5 Hiến chương.
    Bắt buộc khai đủ: source, sample_count, benchmark_id, compute_budget, approval_tier, expires_at.
    """
    required_fields = ["source", "sample_count", "benchmark_id", "compute_budget", "approval_tier"]
    for field in required_fields:
        if field not in proposal or proposal[field] is None:
            return {
                "accepted": False,
                "reason_code": f"MISSING_{field.upper()}",
                "message": f"Proposal lacks required field '{field}'",
            }

    # Kiểm tra expires_at / data_ttl
    if "expires_at" not in proposal or proposal["expires_at"] is None:
        return {
            "accepted": False,
            "reason_code": "MISSING_EXPIRY",
            "message": "Proposal lacks required expiry timestamp (expires_at)",
        }

    expires_at_str = str(proposal["expires_at"]).strip()
    try:
        # Hỗ trợ ISO 8601 (có thể kết thúc bằng 'Z')
        iso_str = expires_at_str.replace("Z", "+00:00")
        expiry_dt = datetime.fromisoformat(iso_str)
        if expiry_dt.tzinfo is None:
            expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
        
        now_dt = datetime.now(timezone.utc)
        if expiry_dt < now_dt:
            return {
                "accepted": False,
                "reason_code": "DATA_EXPIRED",
                "message": f"Proposal training data expired at {expires_at_str} (current: {now_dt.isoformat()})",
            }
    except Exception as exc:
        return {
            "accepted": False,
            "reason_code": "INVALID_EXPIRY_FORMAT",
            "message": f"Cannot parse expires_at timestamp: {exc}",
        }

    return {
        "accepted": True,
        "reason_code": "OK",
        "message": "Learning proposal validated and accepted",
    }


# ==============================================================================
# T2: ĐÁNH GIÁ SỨC KHỎE VÒNG HỌC (CHỐNG GAMING METRIC & MASTER TIME)
# ==============================================================================
def evaluate_loop_health(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Đánh giá tiến bộ vòng học theo Điều 9 & 10.
    Chống hành vi gaming: không tính là cải thiện nếu chỉ giảm số proposal
    để làm đẹp tỷ lệ Master minutes / proposal mà không có cải thiện benchmark thực tế.
    """
    proposals = metrics.get("proposals", 0)
    promoted = metrics.get("promoted", 0)
    master_minutes = metrics.get("master_minutes", 0)
    held_out_delta = metrics.get("held_out_delta", 0.0)
    rollbacks = metrics.get("rollbacks", 0)
    freezes = metrics.get("freezes", 0)

    # Nếu có rollback hoặc freeze -> Không bao giờ tính là cải thiện
    if rollbacks > 0 or freezes > 0:
        return {
            "counts_as_improvement": False,
            "reason": "SAFETY_REGRESSION_OR_FREEZE_ACTIVE",
            "held_out_delta": held_out_delta,
        }

    # Gaming check: Quá ít proposal (<= 2) hoặc delta held-out <= 0 -> Không tính là cải thiện
    if proposals <= 2 or held_out_delta <= 0.0:
        return {
            "counts_as_improvement": False,
            "reason": "LOW_VOLUME_OR_ZERO_DELTA_GAMING",
            "held_out_delta": held_out_delta,
        }

    # Cải thiện thực tế: Có khối lượng đủ, delta held-out dương, promoted >= 1
    return {
        "counts_as_improvement": True,
        "reason": "STATISTICALLY_SIGNIFICANT_IMPROVEMENT",
        "held_out_delta": held_out_delta,
        "efficiency_ratio": (master_minutes / promoted) if promoted > 0 else 0.0,
    }


# ==============================================================================
# T4: CÁCH LY KHO ĐỀ & ĐÁP ÁN THI KHỎI RETRIEVAL / RAG (RAG ISOLATION)
# ==============================================================================
def is_exam_isolated_path(path: str) -> bool:
    """Xác định đường dẫn có thuộc vùng niêm phong đề thi độc lập hay không."""
    if not path:
        return False
    norm_p = path.replace("\\", "/").lower()
    return any(marker in norm_p for marker in EXAM_SEALED_PATHS)


def validate_rag_ingest_path(path: str) -> bool:
    """
    [Tier 2 Ingest Gate]: Chặn đứng nỗ lực nạp tài liệu từ vùng niêm phong đề thi vào RAG/vector store.
    """
    if is_exam_isolated_path(path):
        raise PermissionError(
            f"SEALED_EXAM_INGEST_FORBIDDEN: Attempted to ingest sealed exam file into RAG pipeline ('{path}')."
        )
    return True


def query_exam_answer_via_retrieval(query_id: str) -> Any:
    """
    Cửa ngõ truy vấn RAG/Retrieval.
    Bảo đảm tuyệt đối: Mọi truy vấn hướng đến kho đề thi kín bị chặn đứng (PermissionError).
    """
    query_l = str(query_id).lower()
    if any(marker in query_l for marker in ("sealed", "exam", "answer_key")):
        raise PermissionError(
            f"RAG_ISOLATION_VIOLATION: Exam sealed questions and answer keys cannot be retrieved "
            f"via standard RAG/retrieval pipeline (query: '{query_id}')."
        )
    return []


# ==============================================================================
# T5: KIỂM ĐỊNH ĐỘ KHÓ XOAY ĐỀ 20% (EXAM ROTATION DIFFICULTY CALIBRATION)
# ==============================================================================
def calibrate_exam_rotation_difficulty(rotation_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Kiểm định độ khó câu hỏi xoay đề tuần theo Điều 7 & 12.
    Nếu câu hỏi mới chưa được kiểm định độ khó (difficulty_report is None),
    cấm so sánh trực tiếp điểm số giữa các tuần.
    """
    diff_report = rotation_data.get("difficulty_report")
    if diff_report is None:
        return {
            "comparable": False,
            "reason": "UNTESTED_DIFFICULTY_DISTRIBUTION",
            "message": "New rotated questions lack empirical difficulty calibration; scores cannot be directly compared.",
        }

    mean_delta = abs(diff_report.get("mean_delta_vs_old", 1.0))
    n_trials = diff_report.get("n_trials", 0)

    # Điều kiện để đề mới được so sánh: độ lệch độ khó <= 15% và số lần chạy thử >= 3
    if mean_delta <= 0.15 and n_trials >= 3:
        return {
            "comparable": True,
            "reason": "DIFFICULTY_CALIBRATED_WITHIN_BOUNDS",
            "mean_delta_vs_old": mean_delta,
            "n_trials": n_trials,
        }

    return {
        "comparable": False,
        "reason": "EXCESSIVE_DIFFICULTY_VARIANCE",
        "mean_delta_vs_old": mean_delta,
        "n_trials": n_trials,
    }
