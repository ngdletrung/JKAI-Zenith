# -*- coding: utf-8 -*-
"""
Unit test suite cho Speculative Multi-Index RAG Fusion
"""

import pytest
from core.knowledge_sources.speculative_fusion import SpeculativeFusionEngine, fusion_engine


class TestSpeculativeFusion:
    """Kiểm tra độ chính xác của BM25 Sparse Search và Reciprocal Rank Fusion."""

    def test_bm25_exact_keyword_matching(self):
        docs = [
            {"id": "doc1", "payload": {"text": "Báo cáo tài chính quý 3 năm 2026 của công ty"}},
            {"id": "doc2", "payload": {"text": "Tài liệu hướng dẫn kỹ thuật kiến trúc phần mềm"}},
            {"id": "doc3", "payload": {"text": "Lịch họp ban lãnh đạo tổng kết quý 3"}}
        ]
        results = fusion_engine.bm25_rank("báo cáo tài chính", docs, top_k=2)
        assert len(results) >= 1
        assert results[0]["id"] == "doc1"
        assert results[0]["score"] > 0

    def test_bm25_empty_query_returns_empty(self):
        docs = [{"id": "doc1", "payload": {"text": "Nội dung văn bản"}}]
        results = fusion_engine.bm25_rank("", docs)
        assert results == []

    def test_rrf_boosts_documents_found_in_both(self):
        # Doc 1 xuất hiện ở cả Dense và Sparse
        dense_results = [
            {"id": "doc1", "score": 0.85, "payload": {"text": "Doc 1"}},
            {"id": "doc2", "score": 0.80, "payload": {"text": "Doc 2"}},
        ]
        sparse_results = [
            {"id": "doc3", "score": 2.5, "payload": {"text": "Doc 3"}},
            {"id": "doc1", "score": 2.0, "payload": {"text": "Doc 1"}},
        ]
        
        fused = fusion_engine.reciprocal_rank_fusion(dense_results, sparse_results, top_k=3)
        assert len(fused) == 3
        # Doc 1 xuất hiện ở cả hai nguồn -> RRF score phải cao nhất
        assert fused[0]["payload"]["text"] == "Doc 1"
        assert fused[0]["dense_score"] > 0
        assert fused[0]["sparse_score"] > 0

    def test_rrf_preserves_single_source_documents(self):
        dense_results = [{"id": "doc_dense", "score": 0.9, "payload": {"text": "Dense Only"}}]
        sparse_results = [{"id": "doc_sparse", "score": 3.0, "payload": {"text": "Sparse Only"}}]
        
        fused = fusion_engine.reciprocal_rank_fusion(dense_results, sparse_results, top_k=2)
        texts = [f["payload"]["text"] for f in fused]
        assert "Dense Only" in texts
        assert "Sparse Only" in texts
