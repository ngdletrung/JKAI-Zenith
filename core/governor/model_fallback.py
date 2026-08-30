# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — ADAPTIVE MODEL GOVERNOR: MODEL FALLBACK v2.0    ║
║   Định Tuyến Thay Thế Theo Năng Lực Tác Vụ, Health Check & Cache ║
╚══════════════════════════════════════════════════════════════════╝
*Kiến Trúc Sư Trưởng Chủ Động Tối Ưu Hóa Bộ Điều Phối Mô Hình Thông Minh. 🏛️⚡🧠*
"""

import time
import logging
from typing import Set, Optional, List, Dict, Tuple, Any
from core.governor.model_capabilities import ModelCapabilityProfile

logger = logging.getLogger("AMG_ModelFallback")


class ModelFallback:
    """
    🏗️ Capability-Driven Autonomous Model Fallback v2.0
    Lựa chọn mô hình thay thế tối ưu dựa trên:
      1. Yêu cầu năng lực cụ thể của tác vụ (required_capabilities).
      2. Bộ đệm quyết định LRU Cache 60s.
      3. Health check trạng thái tải thực tế.
      4. Báo cáo đo lường Telemetry vào Observability Engine.
    """
    MIN_RELIABILITY: float = 0.50
    MIN_ACTIVE_PARAMS_B: float = 0.5
    
    # In-memory Decision Cache: key -> (fallback_model, timestamp)
    _decision_cache: Dict[Tuple, Tuple[str, float]] = {}
    _CACHE_TTL_SEC: float = 60.0

    @classmethod
    def resolve_fallback(
        cls,
        requested_model: str,
        loaded_models: Set[str],
        preferred_backend: str = "GPU",
        registered_profiles: Optional[List[ModelCapabilityProfile]] = None,
        required_capabilities: Optional[Dict[str, float]] = None,
        unhealthy_models: Optional[Set[str]] = None,
    ) -> str:
        """
        Tìm kiếm mô hình thay thế phù hợp nhất theo năng lực tác vụ.
        """
        chain = cls.resolve_fallback_chain(
            requested_model=requested_model,
            loaded_models=loaded_models,
            preferred_backend=preferred_backend,
            registered_profiles=registered_profiles,
            required_capabilities=required_capabilities,
            unhealthy_models=unhealthy_models,
        )
        return chain[0] if chain else ""

    @classmethod
    def resolve_fallback_chain(
        cls,
        requested_model: str,
        loaded_models: Set[str],
        preferred_backend: str = "GPU",
        registered_profiles: Optional[List[ModelCapabilityProfile]] = None,
        required_capabilities: Optional[Dict[str, float]] = None,
        unhealthy_models: Optional[Set[str]] = None,
    ) -> List[str]:
        """
        Trả về danh sách các mô hình thay thế theo thứ tự ưu tiên giảm dần.
        """
        if not loaded_models:
            logger.error("[AMG-FALLBACK]: No models loaded at all. Cannot resolve fallback.")
            return []

        unhealthy = unhealthy_models or set()
        healthy_loaded = {m for m in loaded_models if m not in unhealthy}
        if not healthy_loaded:
            logger.warning("[AMG-FALLBACK]: All resident models marked unhealthy. Fallback to raw loaded models.")
            healthy_loaded = loaded_models

        # 1. Kiểm tra cache
        cache_key = (
            requested_model,
            tuple(sorted(healthy_loaded)),
            preferred_backend,
            tuple(sorted(required_capabilities.items())) if required_capabilities else None
        )
        now = time.time()
        if cache_key in cls._decision_cache:
            cached_chain, ts = cls._decision_cache[cache_key]
            if now - ts < cls._CACHE_TTL_SEC and any(m in healthy_loaded for m in cached_chain):
                return [m for m in cached_chain if m in healthy_loaded]

        t0 = time.perf_counter()

        # 2. Direct Match (nếu model yêu cầu còn khỏe và đang nạp)
        clean_req = requested_model.strip().lower() if requested_model else ""
        if clean_req and (clean_req in healthy_loaded or clean_req.split(":")[0] in healthy_loaded):
            cls._record_metric(requested_model, requested_model, "direct_match", (time.perf_counter() - t0) * 1000)
            return [requested_model]

        # 3. Capability-Driven Selection từ registered profiles
        candidate_chain = []
        if registered_profiles:
            valid_profiles = [
                p for p in registered_profiles
                if p.model_name in healthy_loaded
                and not p.is_embedding_only
                and p.parameters_active_b >= cls.MIN_ACTIVE_PARAMS_B
            ]

            if valid_profiles:
                if required_capabilities:
                    # Chấm điểm theo độ khớp năng lực
                    def _score_profile(p: ModelCapabilityProfile) -> float:
                        total_score = 0.0
                        for cap_name, weight in required_capabilities.items():
                            # Lấy điểm từ quant_vector hoặc quant_profile
                            score_obj = None
                            if hasattr(p, "quant_profile") and hasattr(p.quant_profile, cap_name):
                                score_obj = getattr(p.quant_profile, cap_name)
                            elif hasattr(p, "quant_vector") and hasattr(p.quant_vector, cap_name):
                                score_obj = getattr(p.quant_vector, cap_name)
                            
                            val = score_obj.effective_value if hasattr(score_obj, "effective_value") else (score_obj if isinstance(score_obj, (int, float)) else 0.5)
                            total_score += val * weight
                        return total_score

                    ranked = sorted(valid_profiles, key=_score_profile, reverse=True)
                    candidate_chain = [p.model_name for p in ranked]
                else:
                    # Ưu tiên model nhỏ nhất đạt độ tin cậy tối thiểu
                    reliable_cands = [p for p in valid_profiles if getattr(p.quant_vector, "reliability", 1.0) >= cls.MIN_RELIABILITY]
                    ranked = sorted(reliable_cands or valid_profiles, key=lambda p: p.parameters_active_b)
                    candidate_chain = [p.model_name for p in ranked]

        # 4. Best effort fallback nếu không có profile
        if not candidate_chain:
            candidate_chain = sorted(healthy_loaded)

        selected = candidate_chain[0] if candidate_chain else next(iter(loaded_models))
        
        # Cập nhật cache toàn bộ chain
        cls._decision_cache[cache_key] = (candidate_chain, now)

        # Ghi log và metric
        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.warning(
            f"[AMG-FALLBACK]: '{requested_model}' not available → Resolved to '{selected}' "
            f"(Candidates: {len(candidate_chain)}, Took: {elapsed_ms:.2f}ms)"
        )
        cls._record_metric(requested_model, selected, "capability_resolved", elapsed_ms)

        return candidate_chain

    @classmethod
    def _record_metric(cls, from_model: str, to_model: str, reason: str, duration_ms: float) -> None:
        """Ghi nhận telemetry metric vào Observability Engine."""
        try:
            from core.telemetry.observability_engine import observability_engine
            observability_engine.record_span(
                name="amg_model_fallback",
                category="AMG",
                duration_ms=duration_ms,
                metadata={"from_model": from_model, "to_model": to_model, "reason": reason}
            )
        except Exception:
            pass


model_fallback = ModelFallback()
