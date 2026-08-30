# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — UNIFIED RETRIEVER v2.0 (L1/L2 HYBRID FUSION)     ║
║   Động Cơ Truy Xuất Tri Thức Đa Tầng, Lọc Ngưỡng & Nén Facts    ║
╚══════════════════════════════════════════════════════════════════╝
*Kiến Trúc Sư Trưởng Chủ Động Tối Ưu Hóa Tốc Độ & Trí Thông Minh RAG. ⚡🧠📚*
"""

import os
import time
import json
import hashlib
import asyncio
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

logger = logging.getLogger("JKAI.UnifiedRetriever")

COLLECTION_KNOWLEDGE = "jkai_knowledge"
COLLECTION_MEMORY = "jkai_memory"
COLLECTION_REASONING = "jkai_reasoning_bank"
COLLECTION_EXTERNAL = "jkai_external"


@dataclass
class RetrievalResult:
    results: List[Dict]
    sources: List[str]
    elapsed: float
    distilled_summary: Optional[str] = None


class UnifiedRetriever:
    """
    📚 [UNIFIED-RETRIEVER v2.0]: Truy Xuất Tri Thức Siêu Tốc & Lọc Ngưỡng Thông Minh
    Đặc tính nâng cấp:
      1. L1 In-Memory Fast Cache: Phục hồi kết quả trong <0.1ms.
      2. Relevance Score Gating: Lọc bỏ tài liệu điểm thấp (<0.35) chống loãng context.
      3. Integrated Fact Distillation: Tự động cô đọng qua FactDistiller v2.0.
      4. MMR-Lite Diversity: Triệt tiêu thiên vị file nguồn trùng lặp.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        # L1 In-Memory Cache: Dict dạng {cache_key: (timestamp, data)}
        self._l1_cache: Dict[str, tuple[float, Dict[str, Any]]] = {}
        self._l1_ttl = 300.0  # 5 phút trong RAM
        self._min_relevance_score = 0.35

    def _get_l1_cache(self, key: str) -> Optional[Dict[str, Any]]:
        if key in self._l1_cache:
            ts, data = self._l1_cache[key]
            if time.time() - ts <= self._l1_ttl:
                return data
            else:
                del self._l1_cache[key]
        return None

    def _set_l1_cache(self, key: str, data: Dict[str, Any]):
        # Giới hạn kích thước cache 500 phần tử
        if len(self._l1_cache) > 500:
            oldest_key = min(self._l1_cache.keys(), key=lambda k: self._l1_cache[k][0])
            del self._l1_cache[oldest_key]
        self._l1_cache[key] = (time.time(), data)

    async def search(
        self,
        query: str,
        top_k: int = 5,
        sources: List[str] = None,
        include_external: bool = False,
        filter_dict: dict = None,
        auto_distill: bool = True,
    ) -> RetrievalResult:
        from core.qdrant_client import qdrant_client
        from core.utils.embed import embed
        from core.utils.engine import engine

        start = time.time()
        params_str = f"{query}:{top_k}:{sources}:{include_external}:{filter_dict}"
        cache_hash = hashlib.md5(params_str.encode()).hexdigest()
        cache_key = f"brain_cache:retrieval:unified:{cache_hash}"

        # ── 1. L1 IN-MEMORY CACHE (<0.1ms) ──────────────────────────────
        l1_hit = self._get_l1_cache(cache_hash)
        if l1_hit:
            return RetrievalResult(
                results=l1_hit.get("results", []),
                sources=l1_hit.get("sources", []),
                elapsed=time.time() - start,
                distilled_summary=l1_hit.get("distilled_summary")
            )

        # ── 2. L2 REDIS CACHE (<3ms) ────────────────────────────────────
        r = engine._get_redis()
        if r:
            try:
                cached = r.get(cache_key)
                if cached:
                    data = json.loads(cached)
                    self._set_l1_cache(cache_hash, data)
                    return RetrievalResult(
                        results=data.get("results", []),
                        sources=data.get("sources", []),
                        elapsed=time.time() - start,
                        distilled_summary=data.get("distilled_summary")
                    )
            except Exception:
                pass

        # ── 3. TÍNH EMBEDDING VECTOR ─────────────────────────────────────
        query_vector = await embed.get_embedding_async(query[:1000])
        if not query_vector:
            return RetrievalResult(results=[], sources=[], elapsed=time.time() - start)

        # ── 4. TRUY VẤN SONG SONG TẤT CẢ COLLECTIONS ──────────────────────
        target_collections = sources or [
            COLLECTION_KNOWLEDGE,
            COLLECTION_MEMORY,
            COLLECTION_REASONING,
        ]
        if include_external:
            target_collections.append(COLLECTION_EXTERNAL)

        async def _search_coll(coll: str) -> List[Dict]:
            try:
                results = await qdrant_client.search_similar(
                    query_vector, limit=top_k * 2, collection=coll, filter_dict=filter_dict
                )
                for res in results:
                    res["_collection"] = coll
                return results
            except Exception:
                return []

        tasks = [_search_coll(c) for c in target_collections]
        results_lists = await asyncio.gather(*tasks)

        all_results = []
        for r_list in results_lists:
            all_results.extend(r_list)

        # ── 5. SPECULATIVE MULTI-INDEX FUSION (DENSE + BM25 QUA RRF) ───────
        try:
            from core.knowledge_sources.speculative_fusion import fusion_engine
            bm25_results = fusion_engine.bm25_rank(query, all_results, top_k=top_k * 2)
            fused_candidates = fusion_engine.reciprocal_rank_fusion(
                dense_results=all_results,
                sparse_results=bm25_results,
                top_k=top_k * 2
            )
        except Exception:
            fused_candidates = all_results

        # ── 6. KHỬ TRÙNG LẶP & LỌC NGƯỠNG ĐIỂM LIÊN QUAN (RELEVANCE GATING) ───
        deduplicated = []
        seen_texts = set()
        for res in sorted(fused_candidates, key=lambda x: x.get("score", 0), reverse=True):
            score = res.get("score", 0.0)
            # Lọc bỏ tài liệu rác có độ tương đồng quá thấp
            if score < self._min_relevance_score and len(deduplicated) >= 2:
                continue

            p = res.get("payload", {})
            text = (p.get("text") or p.get("content") or "").strip()
            if not text:
                continue
            norm_text = " ".join(text.split())
            if norm_text not in seen_texts:
                seen_texts.add(norm_text)
                deduplicated.append(res)

        # ── 7. TEMPORAL DECAY SCORING ──────────────────────────────────────
        try:
            from core.kernel.temporal_ranker import apply_temporal_decay
            deduplicated = apply_temporal_decay(deduplicated)
            deduplicated.sort(key=lambda x: x.get("score", 0), reverse=True)
        except Exception:
            pass

        # ── 8. MMR-LITE DIVERSITY HEURISTIC ───────────────────────────────
        selected_results = []
        remaining_results = deduplicated
        
        while len(selected_results) < top_k and remaining_results:
            best_score = -1e9
            best_idx = -1
            
            for idx, cand in enumerate(remaining_results):
                cand_score = cand.get("score", 0.0)
                cand_p = cand.get("payload", {})
                cand_source = cand_p.get("rel_path") or cand_p.get("filename") or cand_p.get("path")
                
                penalty = 0.0
                if cand_source:
                    for sel in selected_results:
                        sel_p = sel.get("payload", {})
                        sel_source = sel_p.get("rel_path") or sel_p.get("filename") or sel_p.get("path")
                        if sel_source == cand_source:
                            penalty += 0.15
                
                final_score = cand_score - penalty
                if final_score > best_score:
                    best_score = final_score
                    best_idx = idx
            
            if best_idx != -1:
                selected_results.append(remaining_results.pop(best_idx))
            else:
                break

        # ── 9. FACT DISTILLATION CHO CONTEXT (TỰ ĐỘNG CHẮT LỌC SỐ LIỆU) ────
        distilled_summary = None
        if auto_distill and selected_results:
            try:
                from core.knowledge_sources.fact_distiller import fact_distiller
                raw_texts = []
                for item in selected_results:
                    pl = item.get("payload", {})
                    t = pl.get("text") or pl.get("content") or ""
                    if t:
                        raw_texts.append(t)
                combined_raw = "\n".join(raw_texts)
                distilled_summary = fact_distiller.distill_facts(combined_raw, query=query, max_facts=5)
            except Exception:
                pass

        # ── 10. ĐÓNG GÓI KẾT QUẢ & LƯU L1 / L2 CACHE ────────────────────────
        seen_sources = set()
        for res in selected_results:
            p = res.get("payload", {})
            s = p.get("rel_path") or p.get("filename") or p.get("source") or p.get("_collection", "unknown")
            seen_sources.add(os.path.basename(str(s)))

        elapsed_time = time.time() - start
        cache_data = {
            "results": selected_results,
            "sources": list(seen_sources),
            "elapsed": elapsed_time,
            "distilled_summary": distilled_summary
        }

        # Lưu L1 Cache (RAM)
        self._set_l1_cache(cache_hash, cache_data)

        # Lưu L2 Cache (Redis TTL 600s)
        if r:
            try:
                r.setex(cache_key, 600, json.dumps(cache_data))
            except Exception:
                pass

        return RetrievalResult(
            results=selected_results,
            sources=list(seen_sources),
            elapsed=elapsed_time,
            distilled_summary=distilled_summary
        )


retriever = UnifiedRetriever()
