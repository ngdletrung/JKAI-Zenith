# -*- coding: utf-8 -*-
"""
[TEMPORAL DECAY RANKER]
File: core/kernel/temporal_ranker.py

Cơ chế phân rã điểm theo thời gian (Temporal Decay Scoring) cho RAG Vector Retrieval.

Vấn đề:
  - Qdrant không phân biệt dữ liệu mới vs cũ — chỉ dùng cosine similarity.
  - Dữ liệu tuần trước (similarity 0.92) rank cao hơn dữ liệu mới (similarity 0.88).
  - Gây "ô nhiễm context" — model nhỏ bị nhiễm thông tin cũ, trả lời sai.

Giải pháp:
  - Công thức phân rã: adjusted_score = vector_score × decay_factor
  - decay_factor = exp(-λ × age_hours)
  - λ = 0.01 (bán rã ~70 giờ = 3 ngày) — cân bằng giữa freshness và stability

Bảng tham chiếu λ=0.01:
  age_hours=0   → decay=1.00 (điểm gốc)
  age_hours=24  → decay=0.787 (1 ngày: giảm ~21%)
  age_hours=72  → decay=0.487 (3 ngày: giảm ~51%)
  age_hours=168 → decay=0.187 (7 ngày: giảm ~81%)
  age_hours=720 → decay=0.001 (30 ngày: gần như bị loại)

Cấu hình:
  Đặt biến môi trường RAG_DECAY_LAMBDA để điều chỉnh (mặc định 0.01).
"""

import math
import os
import time
import logging
from typing import List, Dict, Optional

logger = logging.getLogger("JKAI.TemporalRanker")

# Hệ số phân rã mặc định — điều chỉnh qua env var nếu cần
_DECAY_LAMBDA = float(os.environ.get("RAG_DECAY_LAMBDA", "0.01"))

# Các field chứa timestamp trong Qdrant payload (thử theo thứ tự ưu tiên)
_TIMESTAMP_FIELDS = ("indexed_at", "created_at", "timestamp", "updated_at", "ts")

# Điểm tối thiểu sau khi áp decay (tránh loại hoàn toàn dữ liệu rất cũ nhưng rất relevant)
_MIN_DECAY_FACTOR = 0.05


def _extract_timestamp(payload: Dict) -> Optional[float]:
    """Trích xuất timestamp từ payload Qdrant (Unix epoch float)."""
    for field in _TIMESTAMP_FIELDS:
        val = payload.get(field)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
    return None


def apply_temporal_decay(
    results: List[Dict],
    decay_lambda: Optional[float] = None,
    current_time: Optional[float] = None,
    mode: str = "default",
    min_decay: float = _MIN_DECAY_FACTOR,
) -> List[Dict]:
    """
    Áp dụng phân rã điểm số theo thời gian cho danh sách kết quả retrieval.

    decay_lambda: Nếu None, tự động chọn dựa trên mode:
      - mode='realtime' / 'news': λ = 0.05 (phân rã nhanh theo giờ)
      - mode='knowledge' / 'default': λ = 0.005 (giữ tri thức bền vững)
    """
    if not results:
        return results

    if decay_lambda is None:
        if mode in ("realtime", "news", "fast"):
            decay_lambda = 0.05
        elif mode in ("knowledge", "doc", "code"):
            decay_lambda = 0.005
        else:
            decay_lambda = _DECAY_LAMBDA

    now = current_time if current_time is not None else time.time()
    adjusted = []

    for res in results:
        score = res.get("score", 0.0)
        payload = res.get("payload", {})

        ts = _extract_timestamp(payload)
        if ts is not None:
            age_seconds = max(0.0, now - ts)
            age_hours = age_seconds / 3600.0
            decay_factor = max(min_decay, math.exp(-decay_lambda * age_hours))
            original_score = score
            score = score * decay_factor

            if decay_factor < 0.5:
                logger.debug(
                    "[TEMPORAL-DECAY] payload_ts=%s age_hours=%.1f decay=%.3f "
                    "score: %.4f → %.4f",
                    ts, age_hours, decay_factor, original_score, score
                )

        adjusted.append({**res, "score": score, "_temporal_decay_applied": ts is not None})

    return adjusted


def session_boost(
    results: List[Dict],
    task_id: Optional[str] = None,
    boost_factor: float = 2.0,
) -> List[Dict]:
    """
    Tăng điểm cho kết quả thuộc session nhiệm vụ hiện tại.

    Dữ liệu trong session hiện tại luôn được ưu tiên tuyệt đối
    so với tri thức long-term từ các session khác.

    Args:
        results: Danh sách result từ RAG.
        task_id: ID nhiệm vụ hiện tại.
        boost_factor: Hệ số tăng điểm (mặc định 2.0 = gấp đôi).

    Returns:
        Danh sách result đã điều chỉnh điểm session.
    """
    if not task_id:
        return results

    boosted = []
    for res in results:
        payload = res.get("payload", {})
        score = res.get("score", 0.0)

        # Kiểm tra nếu kết quả thuộc session hiện tại
        res_task_id = payload.get("task_id") or payload.get("session_id") or payload.get("mission_id")
        if res_task_id and res_task_id == task_id:
            score = score * boost_factor
            logger.debug("[SESSION-BOOST] task_id=%s score boosted %.4f → %.4f", task_id, score / boost_factor, score)

        boosted.append({**res, "score": score})

    return boosted
