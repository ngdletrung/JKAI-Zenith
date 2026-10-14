# -*- coding: utf-8 -*-
"""
Behavioral Red-to-Green TDD Suite for Slice 3.3 (Giai đoạn 3 Backlog Master — Khép Vòng Tự Học):
- Item 7: Reflect job nền (gom cụm trajectory -> observations trích dẫn nguyên văn + proof count, refine không ghi đè -> qua CompletionAuthority mới vào episodic; 10 cụm mẫu sinh observations đúng format, 0 ghi thẳng thiếu chữ ký).
- Item 8: Chunk-sửa-thành-nhãn (Master sửa chunk/kết quả sai -> tự sinh mẫu nhãn nhóm A-E vào dataset_manager qua cổng weak-supervision; 20 lần sửa mẫu sinh 20 nhãn đúng nhóm >= 90%).
- Item 9: Memory Defense đường retain (quét >= 45 mẫu secret/PII trước mọi ghi episodic/Qdrant, tái dùng pattern sanitizer; 30/30 mẫu độc bị chặn/redact, văn bản thường false-positive <= 5%).
- Item 10: Giữ nguyên ngữ gốc (Fact tiếng Việt giữ nguyên văn khi retain, cấm dịch ngầm; 20/20 fact VI mẫu round-trip giữ nguyên 100% dấu).
- Plus Turn 284 OpenCode improvement #1: Lock tokenizer_version and seed in evaluate_fixed_rag_harness().
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


def test_stage3_7_reflect_job_10_clusters_and_completion_authority_gate():
    """
    Item 7:
    - 10 trajectory clusters produce 10 valid observations with verbatim quotes and proof_count >= 2.
    - Refining an existing cluster increments revision and proof_count without overwriting prior quotes.
    - Direct episodic write without valid CompletionAuthority signature is 100% blocked (0 unsigned writes).
    """
    from core.os.cognition.completion_authority import CompletionAuthority
    from core.memory.episodic_brain import (
        BackgroundReflectJob,
        EpisodicBrain,
        SAMPLE_10_TRAJECTORY_CLUSTERS,
    )

    assert len(SAMPLE_10_TRAJECTORY_CLUSTERS) == 10
    brain = EpisodicBrain()
    brain.clear_local_observation_store()
    authority = CompletionAuthority()
    reflect_job = BackgroundReflectJob(authority=authority, episodic_brain=brain)

    report = reflect_job.run_batch(SAMPLE_10_TRAJECTORY_CLUSTERS)
    assert report["clusters_processed"] == 10
    assert report["observations_committed"] == 10
    assert report["unsigned_writes_committed"] == 0

    stored = brain.list_retained_observations()
    assert len(stored) == 10
    for obs in stored:
        assert obs["proof_count"] >= 2
        assert len(obs["verbatim_quotes"]) >= 2
        assert obs["revision"] == 1
        assert authority.verify_observation_signature(obs, obs["authority_signature"]) is True

    # Test refine without overwrite on cluster 0
    first_cluster_id = SAMPLE_10_TRAJECTORY_CLUSTERS[0]["cluster_id"]
    prev_obs = brain.get_retained_observation(first_cluster_id)
    prev_quotes = list(prev_obs["verbatim_quotes"])
    prev_proof_count = prev_obs["proof_count"]

    refine_res = reflect_job.refine_cluster(
        cluster_id=first_cluster_id,
        new_trajectories=[
            {
                "step_id": "step_refine_99",
                "verbatim_quote": "Bổ sung kiểm tra port 11435 trước khi chạy worker_fast.",
                "outcome_verified": True,
            }
        ],
    )
    assert refine_res["refined"] is True
    updated_obs = brain.get_retained_observation(first_cluster_id)
    assert updated_obs["revision"] == 2
    assert updated_obs["proof_count"] == prev_proof_count + 1
    for q in prev_quotes:
        assert q in updated_obs["verbatim_quotes"]
    assert "Bổ sung kiểm tra port 11435 trước khi chạy worker_fast." in updated_obs["verbatim_quotes"]
    assert len(updated_obs["revision_history"]) == 1

    # Test direct unsigned / forged write attempt -> MUST be blocked (0 unsigned writes)
    forged_obs = dict(updated_obs)
    forged_obs["cluster_id"] = "forged_cluster_unsigned"
    forged_obs["authority_signature"] = ""
    res_unsigned = brain.retain_observation(forged_obs)
    assert res_unsigned["retained"] is False
    assert res_unsigned["reason"] == "MISSING_OR_INVALID_COMPLETION_AUTHORITY_SIGNATURE"
    assert brain.get_retained_observation("forged_cluster_unsigned") is None
    assert brain.get_unauthorized_write_blocks() >= 1


def test_stage3_8_chunk_edit_to_label_weak_supervision_20_samples():
    """
    Item 8:
    - Every time Master edits a wrong chunk/response, DatasetManager.ingest_chunk_revision_as_label()
      generates a LabeledRecord in categories A..E via the weak-supervision gate.
    - Across 20 sample Master edits, classification accuracy into groups A-E is >= 90%.
    """
    from core.dataset.dataset_manager import (
        DatasetManager,
        SAMPLE_20_MASTER_CHUNK_REVISIONS,
        evaluate_chunk_revision_labeling_benchmark,
    )

    assert len(SAMPLE_20_MASTER_CHUNK_REVISIONS) == 20
    with tempfile.TemporaryDirectory() as tmpdir:
        seed_path = str(Path(tmpdir) / "seed.jsonl")
        gold_path = str(Path(tmpdir) / "gold.jsonl")
        dm = DatasetManager(seed_file=seed_path, gold_file=gold_path)

        bench = evaluate_chunk_revision_labeling_benchmark(dataset_manager_instance=dm)
        assert bench["total_revisions"] == 20
        assert bench["accuracy"] >= 0.90
        assert bench["correct_predictions"] >= 18

        stored_gold = dm.load_gold_dataset()
        assert len(stored_gold) == 20
        assert all(r.reviewed_by_master is True for r in stored_gold)


def test_stage3_9_memory_defense_retain_45_patterns_30_toxic_and_fp_rate():
    """
    Item 9:
    - StateSanitizer exposes >= 45 secret/PII/poisoning patterns in MEMORY_DEFENSE_PATTERNS.
    - 30 toxic/secret/PII samples are 30/30 caught (redacted or blocked) on the retain path.
    - Normal technical & Vietnamese prose samples have false-positive rate <= 5%.
    """
    from core.sanitizer.state_sanitizer import (
        StateSanitizer,
        SAMPLE_30_TOXIC_RETAIN_PAYLOADS,
        SAMPLE_25_BENIGN_RETAIN_PAYLOADS,
        evaluate_memory_defense_retain_benchmark,
    )

    assert len(StateSanitizer.MEMORY_DEFENSE_PATTERNS) >= 45
    assert len(SAMPLE_30_TOXIC_RETAIN_PAYLOADS) == 30
    assert len(SAMPLE_25_BENIGN_RETAIN_PAYLOADS) >= 20

    report = evaluate_memory_defense_retain_benchmark()
    assert report["pattern_count"] >= 45
    assert report["toxic_total"] == 30
    assert report["toxic_caught"] == 30
    assert report["toxic_catch_rate"] == 1.0
    assert report["benign_false_positive_rate"] <= 0.05


def test_stage3_10_vietnamese_native_fact_retention_20_roundtrip_100pct_diacritics():
    """
    Item 10:
    - 20 Vietnamese facts retained into EpisodicBrain round-trip with 100% diacritic preservation
      and zero silent translation.
    - Silently ASCII-stripped or English-translated mutations are rejected by the native-language guard.
    """
    from core.memory.episodic_brain import (
        EpisodicBrain,
        SAMPLE_20_VIETNAMESE_FACTS,
        evaluate_vietnamese_fact_roundtrip_benchmark,
        verify_vietnamese_diacritic_fidelity,
    )
    from core.utils.rag_eval_harness import evaluate_fixed_rag_harness

    assert len(SAMPLE_20_VIETNAMESE_FACTS) == 20
    brain = EpisodicBrain()
    report = evaluate_vietnamese_fact_roundtrip_benchmark(episodic_brain=brain)
    assert report["total_facts"] == 20
    assert report["exact_roundtrip_count"] == 20
    assert report["diacritic_retention_rate"] == 1.0

    # Verify silent translation / ASCII stripping is caught and rejected
    orig_vi = "Hệ thống khóa cứng cổng 11435 cho luồng phản xạ nhanh và cấm dịch ngầm tiếng Việt."
    stripped_ascii = "He thong khoa cung cong 11435 cho luong phan xa nhanh va cam dich ngam tieng Viet."
    check = verify_vietnamese_diacritic_fidelity(orig_vi, stripped_ascii)
    assert check["passed"] is False
    assert check["reason"] == "VIETNAMESE_DIACRITIC_LOSS_OR_SILENT_TRANSLATION"

    # Also verify Turn 284 OpenCode improvement #1: tokenizer_version and seed locked in RAG harness
    rag_report = evaluate_fixed_rag_harness()
    assert rag_report["tokenizer_version"] == "jkai-regex-ws-v1"
    assert rag_report["deterministic_seed"] == 42
