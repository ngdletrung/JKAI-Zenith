# -*- coding: utf-8 -*-
"""
tests/test_slice_3_2_stage2_retrieval_and_rag_harness.py
========================================================
Slice 3.2 (Giai đoạn 2 Backlog Master — Nền Retrieval):
1. Recall 4 chiến lược (học Hindsight): Vector + BM25 + Temporal Filter/Boost + Anchor/Entity kết hợp qua Reciprocal Rank Fusion (RRF) vượt trội có ý nghĩa so với Vector-only.
2. Harness đo RAG cố định (học WeKnora): Ingest tập tài liệu đóng băng -> bộ câu hỏi cố định -> đo recall@k, MRR, citation_accuracy, BLEU-1, ROUGE-L F1; tích hợp trực tiếp vào rag/app.py.
3. Parent-child chunking: Chunk con để recall chính xác, trả chunk cha để đủ ngữ cảnh trích dẫn; citation_accuracy tăng rõ rệt và token/window không tăng quá 30%.
4. Đóng nợ chính thức Lượt 282 của OpenCode: Tách test live 70s (nạp 3 model gồm 30B) sang opt-in env `JKAI_RUN_LIVE_MODEL_PROBE=1` để suite mặc định chạy nhanh + hermetic, bổ sung test toán học `eval_count / eval_duration` tức thì.
"""

from __future__ import annotations


def test_stage2_1_four_strategy_rrf_recall_beats_vector_only():
    """
    Mục 1 (Giai đoạn 2): Recall 4 chiến lược (Vector + BM25 + Temporal + Structural Anchor + RRF).
    Xong khi: harness recall trên tập cố định tăng có ý nghĩa so với chỉ dùng vector.
    """
    from core.utils.rag_eval_harness import (
        FROZEN_RAG_CORPUS,
        FROZEN_RAG_QA_BENCHMARK,
        QuadStrategyRetriever,
    )

    assert len(FROZEN_RAG_CORPUS) >= 8
    assert len(FROZEN_RAG_QA_BENCHMARK) >= 10

    retriever = QuadStrategyRetriever.from_documents(
        FROZEN_RAG_CORPUS,
        use_parent_child=True,
    )

    vec_hits = 0
    rrf_hits = 0
    for item in FROZEN_RAG_QA_BENCHMARK:
        vec_res = retriever.retrieve(
            query=item["query"],
            top_k=2,
            strategy_mode="vector_only",
            temporal_after=item.get("temporal_after"),
        )
        rrf_res = retriever.retrieve(
            query=item["query"],
            top_k=2,
            strategy_mode="quad_rrf",
            temporal_after=item.get("temporal_after"),
        )
        vec_doc_ids = {r["doc_id"] for r in vec_res}
        rrf_doc_ids = {r["doc_id"] for r in rrf_res}
        if item["expected_doc_id"] in vec_doc_ids:
            vec_hits += 1
        if item["expected_doc_id"] in rrf_doc_ids:
            rrf_hits += 1

    vec_recall = vec_hits / len(FROZEN_RAG_QA_BENCHMARK)
    rrf_recall = rrf_hits / len(FROZEN_RAG_QA_BENCHMARK)

    # 4-strategy RRF phải vượt trội rõ rệt (>= +25% tuyệt đối) so với chỉ dùng dense/char-vector
    assert rrf_recall >= 0.90, f"Expected RRF recall >= 0.90, got {rrf_recall:.2f}"
    assert rrf_recall - vec_recall >= 0.25, (
        f"Expected significant recall gain over vector_only: rrf={rrf_recall:.2f} vs vec={vec_recall:.2f}"
    )


def test_stage2_2_fixed_rag_evaluation_harness_and_rag_app_integration():
    """
    Mục 2 (Giai đoạn 2): Harness đo RAG cố định (học WeKnora) tích hợp vào rag/app.py.
    Xong khi: chạy baseline xanh, đo đầy đủ recall_at_k, citation_accuracy, bleu1, rouge_l_f1.
    """
    from core.utils.rag_eval_harness import evaluate_fixed_rag_harness
    import rag.app as rag_app

    report = evaluate_fixed_rag_harness(top_k=2)

    assert report["corpus_doc_count"] >= 8
    assert report["question_count"] >= 10
    assert "vector_only" in report["modes"]
    assert "quad_rrf_flat" in report["modes"]
    assert "quad_rrf_parent_child" in report["modes"]

    pc_metrics = report["modes"]["quad_rrf_parent_child"]
    assert pc_metrics["recall_at_k"] >= 0.90
    assert pc_metrics["citation_accuracy"] >= 0.85
    assert pc_metrics["bleu1"] >= 0.50
    assert pc_metrics["rouge_l_f1"] >= 0.50

    # Kiểm tra rag/app.py có gắn hàm/endpoint chạy bộ đo RAG cố định
    assert hasattr(rag_app, "run_rag_fixed_harness"), "rag/app.py must expose run_rag_fixed_harness"
    app_report = rag_app.run_rag_fixed_harness(top_k=2)
    assert app_report["modes"]["quad_rrf_parent_child"]["recall_at_k"] == pc_metrics["recall_at_k"]


def test_stage2_3_parent_child_chunking_citation_gain_and_token_budget():
    """
    Mục 3 (Giai đoạn 2): Parent-child chunking.
    Xong khi: citation_accuracy trên harness tăng rõ rệt so với flat child,
    và token/window không tăng quá 30% so với chuẩn chunk đơn (baseline 180 tokens/window).
    """
    from core.utils.rag_eval_harness import evaluate_fixed_rag_harness

    report = evaluate_fixed_rag_harness(top_k=2)
    flat_mode = report["modes"]["quad_rrf_flat"]
    pc_mode = report["modes"]["quad_rrf_parent_child"]

    # Chunk con chỉ giữ câu khớp hẹp nên thiếu dòng tiêu đề/metadata/điều khoản bao quanh -> citation_accuracy thấp hơn
    assert pc_mode["citation_accuracy"] > flat_mode["citation_accuracy"], (
        f"Parent-child citation_accuracy ({pc_mode['citation_accuracy']}) must beat flat ({flat_mode['citation_accuracy']})"
    )
    # Token/window của parent chunk có trần kiểm soát chặt, không tăng quá 30% so với baseline_window_tokens
    assert pc_mode["token_window_overhead_pct"] <= 30.0, (
        f"Parent-child token overhead {pc_mode['token_window_overhead_pct']}% exceeded 30% ceiling!"
    )


def test_turn282_debt_closure_hermetic_speed_math_and_opt_in_live_gate():
    """
    Đóng nợ chính thức Lượt 282 của OpenCode:
    - Tách test live 70s sang opt-in `JKAI_RUN_LIVE_MODEL_PROBE=1` để bộ test mặc định chạy nhanh.
    - Kiểm chứng toán học `_measure_live_tps` (`eval_count / (eval_duration / 1e9)`) bằng fake fetcher tức thì.
    """
    from core.governor.model_capabilities import probe_ollama_model_card

    calls = []

    def _fake_show(host: str, model: str):
        return {
            "capabilities": ["completion", "tools"],
            "details": {
                "format": "gguf",
                "family": "qwen35",
                "parameter_size": "4.7B",
                "quantization_level": "Q4_K_M",
            },
            "model_info": {"qwen35.context_length": 262144},
        }

    def _fake_generate(host: str, model: str, num_predict: int):
        calls.append(num_predict)
        # 48 tokens in 2.4 seconds -> exactly 20.00 tok/s
        return {
            "eval_count": num_predict,
            "eval_duration": int(num_predict / 20.0 * 1_000_000_000),
        }

    card = probe_ollama_model_card(
        "qwen3.5:4b",
        ollama_host="http://127.0.0.1:11434",
        repeat_runs=2,
        show_fetcher=_fake_show,
        generate_fetcher=_fake_generate,
        measure_speed=True,
        speed_num_predict=48,
    )

    assert calls == [8, 48, 48]  # 1 warm-up (8 tokens) + 2 measured runs (48 tokens)
    assert card["card_status"] == "LIVE"
    assert card["speed_source"] == "live_api_generate"
    assert card["tokens_per_sec"] == 20.0
    assert card["repeat_speed_drift_pct"] == 0.0
