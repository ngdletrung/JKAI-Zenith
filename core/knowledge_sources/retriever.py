import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional

COLLECTION_KNOWLEDGE = "jkai_knowledge"
COLLECTION_MEMORY = "jkai_memory"
COLLECTION_REASONING = "jkai_reasoning_bank"
COLLECTION_EXTERNAL = "jkai_external"


@dataclass
class RetrievalResult:
    results: List[Dict]
    sources: List[str]
    elapsed: float


class UnifiedRetriever:
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

    async def search(
        self,
        query: str,
        top_k: int = 5,
        sources: List[str] = None,
        include_external: bool = False,
        filter_dict: dict = None,
    ) -> RetrievalResult:
        from core.qdrant_client import qdrant_client
        from core.utils.embed import embed
        from core.utils.engine import engine
        import hashlib
        import json

        start = time.time()

        # ── 1. KIỂM TRA CACHE RETRIEVAL (REDIS) ──────────────────────────
        r = engine._get_redis()
        cache_key = None
        if r:
            try:
                # Tạo hash key dựa trên các tham số truy vấn
                params_str = f"{query}:{top_k}:{sources}:{include_external}:{filter_dict}"
                h = hashlib.md5(params_str.encode()).hexdigest()
                cache_key = f"brain_cache:retrieval:unified:{h}"
                cached = r.get(cache_key)
                if cached:
                    data = json.loads(cached)
                    engine.publish_mission_log("BRAIN", f"[CACHE-HIT]: Trả về kết quả tìm kiếm đã cache thưa Master: '{query[:30]}...'", stealth=True)
                    return RetrievalResult(
                        results=data.get("results", []),
                        sources=data.get("sources", []),
                        elapsed=data.get("elapsed", 0.0)
                    )
            except Exception:
                pass

        # ── 2. TÍNH EMBEDDING VECTOR ─────────────────────────────────────
        query_vector = await embed.get_embedding_async(query[:1000])
        if not query_vector:
            return RetrievalResult(results=[], sources=[], elapsed=time.time() - start)

        # ── 3. LỰA CHỌN CÁC COLLECTIONS ĐỂ TRUY VẤN SONG SONG ───────────────
        target_collections = sources or [
            COLLECTION_KNOWLEDGE,
            COLLECTION_MEMORY,
            COLLECTION_REASONING,
        ]
        if include_external:
            target_collections.append(COLLECTION_EXTERNAL)

        # 🚀 [PARALLEL-RETRIEVAL]: Truy vấn song song tất cả các collections bằng asyncio.gather
        async def _search_coll(coll: str) -> List[Dict]:
            try:
                # Quét rộng gấp đôi giới hạn (top_k * 2) để chuẩn bị cho bước Dedup & MMR
                results = await qdrant_client.search_similar(
                    query_vector, limit=top_k * 2, collection=coll, filter_dict=filter_dict
                )
                for res in results:
                    res["_collection"] = coll
                return results
            except Exception:
                return []

        tasks = [_search_coll(c) for c in target_collections]
        import asyncio as _asyncio
        results_lists = await _asyncio.gather(*tasks)

        all_results = []
        for r_list in results_lists:
            all_results.extend(r_list)

        # ── 4. KHỬ TRÙNG LẶP NỘI DUNG (DEDUP) ────────────────────────────
        deduplicated = []
        seen_texts = set()
        for res in sorted(all_results, key=lambda x: x.get("score", 0), reverse=True):
            p = res.get("payload", {})
            text = (p.get("text") or p.get("content") or "").strip()
            if not text:
                continue
            # Chuẩn hóa khoảng trắng để so sánh chính xác
            norm_text = " ".join(text.split())
            if norm_text not in seen_texts:
                seen_texts.add(norm_text)
                deduplicated.append(res)

        # ── 5. ĐA DẠNG HÓA NGUỒN TÀI LIỆU (MMR-LITE HEURISTIC) ─────────────
        # Phạt các đoạn text tiếp theo đến từ cùng một file nguồn
        selected_results = []
        remaining_results = deduplicated
        
        while len(selected_results) < top_k and remaining_results:
            best_score = -1e9
            best_idx = -1
            
            for idx, cand in enumerate(remaining_results):
                cand_score = cand.get("score", 0.0)
                
                # Check trùng file nguồn
                cand_p = cand.get("payload", {})
                cand_source = cand_p.get("rel_path") or cand_p.get("filename") or cand_p.get("path")
                
                penalty = 0.0
                if cand_source:
                    for sel in selected_results:
                        sel_p = sel.get("payload", {})
                        sel_source = sel_p.get("rel_path") or sel_p.get("filename") or sel_p.get("path")
                        if sel_source == cand_source:
                            penalty += 0.15  # Áp hình phạt 0.15 cho mỗi file nguồn trùng nhau
                
                final_score = cand_score - penalty
                if final_score > best_score:
                    best_score = final_score
                    best_idx = idx
            
            if best_idx != -1:
                selected_results.append(remaining_results.pop(best_idx))
            else:
                break

        # ── 6. THIẾT LẬP KẾT QUẢ ĐẦU RA ──────────────────────────────────
        import os as _os
        seen_sources = set()
        for res in selected_results:
            p = res.get("payload", {})
            s = p.get("rel_path") or p.get("filename") or p.get("source") or p.get("_collection", "unknown")
            seen_sources.add(_os.path.basename(str(s)))

        elapsed_time = time.time() - start
        ret_val = RetrievalResult(
            results=selected_results,
            sources=list(seen_sources),
            elapsed=elapsed_time,
        )

        # ── 7. LƯU KẾT QUẢ VÀO REDIS CACHE (TTL 600 GIÂY) ───────────────────
        if r and cache_key:
            try:
                r.setex(
                    cache_key,
                    600,  # Cache TTL 10 phút để tránh trả về dữ liệu quá cũ
                    json.dumps({
                        "results": selected_results,
                        "sources": list(seen_sources),
                        "elapsed": elapsed_time
                    })
                )
            except Exception:
                pass

        return ret_val


retriever = UnifiedRetriever()
