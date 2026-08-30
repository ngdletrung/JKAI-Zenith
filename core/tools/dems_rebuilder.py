# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — DEMS v1.0: DERIVED INDEX REBUILDER CLI           ║
│   Khôi Phục 100% Derived Indexes từ SQLite Raw Trace Store      │
╚══════════════════════════════════════════════════════════════════╝
Tuân thủ 7 Bất biến DEMS:
  I-DEMS-07: Derived Views Are Rebuildable (Graph, BM25, Qdrant tự sinh từ SQLite)
"""

from __future__ import annotations
import sys
import time
import logging
from typing import Dict, Any, List, Optional

from core.storage.raw_trace_store import RawTraceStore, raw_trace_store
from core.kernel.world_model import TypedWorldGraph, NodeType, create_default_world_graph
from core.governor.claim_ledger import ClaimLedger, claim_ledger, ClaimScope

logger = logging.getLogger("JKAI.DEMS.Rebuilder")


class DemsIndexRebuilder:
    """
    🛠️ Bộ Tái Tạo Chỉ Mục Phụ (Derived Index Rebuilder)
    Đọc toàn bộ lịch sử thô bất biến từ SQLite `raw_traces` và tự động:
      1. Tái thiết lập TypedWorldGraph (Entity-Context Graph).
      2. Tái lập ClaimLedger từ các observational events.
    """
    def __init__(
        self,
        trace_store: RawTraceStore = raw_trace_store,
        claim_led: Optional[ClaimLedger] = None,
        world_graph: Optional[TypedWorldGraph] = None
    ):
        self.trace_store = trace_store
        self.claim_ledger = claim_led or claim_ledger
        self.world_graph = world_graph or create_default_world_graph()

    def rebuild_all(self) -> Dict[str, Any]:
        start = time.time()
        count = self.trace_store.count_traces()
        logger.info(f"🚀 [DEMS-REBUILD]: Bắt đầu quét {count} raw traces từ SQLite...")

        rebuilt_nodes = 0
        rebuilt_claims = 0

        for trace in self.trace_store.iterate_all_traces(batch_size=100):
            payload = trace.payload or {}

            # 1. Rebuild TypedWorldGraph từ các service / container events
            if trace.event_type in ("service_init", "container_start"):
                srv = payload.get("service") or payload.get("name")
                if srv:
                    self.world_graph.add_node(
                        node_id=str(srv),
                        node_type=NodeType.CONTAINER,
                        properties={"source": "dems_rebuild", "trace_id": trace.trace_id}
                    )
                    rebuilt_nodes += 1

            # 2. Rebuild ClaimLedger từ observation & config traces
            if trace.event_type in ("command_exec", "file_mutation", "observation"):
                subj = payload.get("subject") or payload.get("service")
                pred = payload.get("predicate") or payload.get("key")
                obj = payload.get("object") or payload.get("value") or payload.get("stdout")
                if subj and pred and obj:
                    self.claim_ledger.register_claim(
                        subject=str(subj),
                        predicate=str(pred),
                        object_val=str(obj)[:100],
                        scope=ClaimScope.RUNTIME if trace.event_type == "command_exec" else ClaimScope.STATIC_CONFIG,
                        evidence_id=f"ev_{trace.trace_id}",
                        authority_level=trace.authority_level
                    )
                    rebuilt_claims += 1

        elapsed = time.time() - start
        logger.info(f"✨ [DEMS-REBUILD-COMPLETE]: Hoàn tất trong {elapsed:.2f}s! Rebuilt {rebuilt_nodes} graph nodes, {rebuilt_claims} claims.")
        return {
            "status": "SUCCESS",
            "total_traces_scanned": count,
            "rebuilt_graph_nodes": rebuilt_nodes,
            "rebuilt_claims": rebuilt_claims,
            "elapsed_seconds": round(elapsed, 2)
        }


rebuilder = DemsIndexRebuilder()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = rebuilder.rebuild_all()
    print(res)
