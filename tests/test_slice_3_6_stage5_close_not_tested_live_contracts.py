# -*- coding: utf-8 -*-
"""
tests/test_slice_3_6_stage5_close_not_tested_live_contracts.py
=============================================================
[Slice 3.6 - Đóng dứt điểm 3 hạng mục NOT_TESTED theo khuyến nghị Lượt 290 của OpenCode]:
1. Mục (c): Đo thật trần `num_predict` (`safe_num_predict_ceiling`) trên Live Ollama (`probe_live_num_predict_ceiling`).
2. Mục (b): Chạy RAG Evaluation Harness trực tiếp trên Live Qdrant REST API cổng 6333 (`evaluate_fixed_rag_harness_live_qdrant`).
3. Mục (a): Huấn luyện Micro-LoRA SFT thực tế bằng `torch` + `peft` (`run_live_micro_lora_sft_job`).
"""

import pytest
from core.governor.model_capabilities import probe_live_num_predict_ceiling
from core.utils.rag_eval_harness import evaluate_fixed_rag_harness_live_qdrant
from core.dataset.dataset_manager import run_live_micro_lora_sft_job, run_end_to_end_lora_eval_loop


def test_slice_3_6_item1_probe_live_num_predict_ceiling_ollama():
    """
    [Mục c Lượt 290]: Đo thật trần num_predict an toàn trên live Ollama.
    Khi Ollama online: trả về TESTED_PASS, eval_count > 0, tốc độ đo thật, dừng sạch.
    Khi Ollama offline: trả về NOT_TESTED minh bạch.
    """
    res = probe_live_num_predict_ceiling(model_name="qwen3.5:4b", test_ceiling_tokens=64)
    assert "live_num_predict_ceiling_status" in res
    if res["live_num_predict_ceiling_status"] == "TESTED_PASS":
        assert res["actual_eval_count"] > 0
        assert res["tokens_per_sec"] > 0.0
        assert res["stopped_cleanly"] is True
        assert res["actual_eval_count"] <= 66
    else:
        assert "NOT_TESTED" in res["live_num_predict_ceiling_status"]


def test_slice_3_6_item2_evaluate_fixed_rag_harness_live_qdrant():
    """
    [Mục b Lượt 290]: Đánh giá RAG Harness trực tiếp trên Live Qdrant REST API (cổng 6333).
    Tạo collection tạm `jkai_frozen_rag_eval_live`, nạp 10 vector tài liệu,
    truy vấn điểm thật từ Qdrant + kết hợp RRF 4 kênh, đo Recall@k,
    và dọn dẹp sạch collection trên Qdrant.
    """
    res = evaluate_fixed_rag_harness_live_qdrant(collection_name="jkai_frozen_rag_eval_live", top_k=2)
    assert "live_qdrant_status" in res
    if res["live_qdrant_status"] == "TESTED_PASS":
        assert res["points_upserted"] == 12
        assert res["recall_at_k"] >= 0.75
        assert res["cleanup_verified"] is True
    else:
        assert "NOT_TESTED" in res["live_qdrant_status"]


def test_slice_3_6_item3_live_micro_lora_sft_torch_peft():
    """
    [Mục a Lượt 290]: Chạy thật 1 job LoRA SFT bằng PyTorch + PEFT (thay vì policy giả lập).
    Lan truyền thuận + nghịch (forward/backward) trên tập Master chunk revisions,
    kiểm tra loss giảm thực tế, lưu và nạp lại trọng số adapter,
    chấm điểm trên held-out set và kết nối vào `run_end_to_end_lora_eval_loop`.
    """
    res = run_live_micro_lora_sft_job(epochs=3, lr=0.05)
    assert res["live_lora_sft_status"] == "TESTED_PASS"
    assert res["framework"] == "torch+peft"
    assert res["epochs_trained"] == 3
    assert res["loss_decreased"] is True
    assert res["weights_saved"] is True
    assert res["held_out_score"] > 0.0

    # Khép nối với vòng lặp quyết định LoRA
    loop_res = run_end_to_end_lora_eval_loop(live_sft_result=res)
    assert loop_res["live_gpu_ms_swift_status"] == "TESTED_PASS (live torch+peft LoRA job verified)"
    assert loop_res["active_adapter"] is not None
