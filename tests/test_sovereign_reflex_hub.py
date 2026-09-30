# -*- coding: utf-8 -*-
"""
[ZENITH FILE DIRECTIVE]
- File: tests/test_sovereign_reflex_hub.py
- Role: End-to-End Contract, Benchmark, Governance & Multi-Task Tests for SovereignReflexHub.
- Ownership: Master LeeTrung
- Status: Active | Version: SDS v28.0
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.benchmark.tier2_bench import (
    Tier2Benchmark,
    Tier3RuleBaselineBackend,
    load_cases_jsonl,
)
from core.cognitive_bus.backends import build, list_registered
from core.cognitive_bus.backends.reflex_engine_backend import (
    MAX_OPTIONS_PER_QUESTION,
    MAX_STATE_CHARS,
    PROMPT_VERSION,
    SCORER_VERSION,
    ReflexEngineBackend,
    detect_language_bcp47,
)
from core.cognitive_bus.decision_substrate_adapter import (
    DecisionPrimitive,
    ExecutionTier,
)
from core.cognitive_bus.reflex_evolution import ReflexEvolutionManager
from core.cognitive_bus.reflex_hub import SovereignReflexHub
from core.governance.confidence_policy import ActionClass

ROOT_DIR = Path(__file__).resolve().parent.parent


class TestBilingualBackendAndBenchmark:
    """Verifies Pillar 2: Bilingual ReflexEngineBackend, batching, tournament, and benchmark."""

    def test_reflex_engine_registered_and_builds(self):
        assert "reflex-engine" in list_registered()
        assert "sovereign-reflex" in list_registered()
        b = build("reflex-engine")
        b.load()
        assert b.is_loaded()
        md = b.metadata()
        assert md.name == "reflex-engine"
        assert md.version == "0.4.2"
        assert md.calibration_state == "uncalibrated"
        assert md.is_local_only is True
        assert "vi" in md.supported_languages
        assert "en" in md.supported_languages

    def test_detect_language_bcp47_bilingual(self):
        assert detect_language_bcp47("Kiểm tra lưu lượng băng thông trên router") == "vi"
        assert detect_language_bcp47("kiem tra he thong co so du lieu nguoi dung") == "vi"
        assert detect_language_bcp47("Analyze SQL query execution plan and optimize joins") == "en"
        assert detect_language_bcp47("   ") == "*"

    def test_detect_language_no_false_positive_on_short_english(self):
        """Regression test per Opencode Turn 244 probe: short English strings must not trigger 'vi'."""
        assert detect_language_bcp47("Check the firewall") == "en"
        assert detect_language_bcp47("Ban the user") == "en"
        assert detect_language_bcp47("He is admin") == "en"
        assert detect_language_bcp47("So what is the status") == "en"
        assert detect_language_bcp47("kiem tra tuong lua") == "vi"

    def test_detect_language_ops_battery_abstains_honestly(self):
        """Root-fix gate: full ops battery (accented/unaccented/EN/neutral) must pass 100%.

        Neutral '*' is the honest answer for signal-less text; forcing 'en'/'vi'
        on guesses caused the Turn 244 misrouting incident.
        """
        bench_path = Path(__file__).resolve().parent.parent / "benchmarks" / "tier2" / "lang_detect_ops_vi_en.jsonl"
        assert bench_path.exists(), f"Missing language battery: {bench_path}"
        failures = []
        total = 0
        with open(bench_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                case = json.loads(line)
                total += 1
                got = detect_language_bcp47(case["text"])
                if got != case["expected"]:
                    failures.append(f"{case['case_id']}: {case['text']!r} -> {got!r}, expected {case['expected']!r}")
        assert total >= 20, f"Battery too small to gate markers: n={total}"
        assert not failures, "Language battery failures:\n" + "\n".join(failures)

    def test_predict_batch_preserves_order_with_length_sorting(self):
        b = ReflexEngineBackend()
        b.load()
        q = "Yêu cầu này nên đi theo luồng xử lý nào?"
        opts = ["fast_path", "deep_path"]
        items = [
            ({"body": "Thiết kế sơ đồ cơ sở dữ liệu phân tán chịu tải 100,000 rps và phân tích race condition"}, [(DecisionPrimitive.CHOICE, q, opts)]),
            ({"body": "Xin chào bạn!"}, [(DecisionPrimitive.CHOICE, q, opts)]),
            ({"body": "Phân tích giải thuật tối ưu hóa kế hoạch thực thi EXPLAIN của MariaDB"}, [(DecisionPrimitive.CHOICE, q, opts)]),
        ]
        results = b.predict_batch(items, sort_by_length=True)
        assert len(results) == 3
        assert results[0][q].result == "deep_path"
        assert results[1][q].result == "fast_path"
        assert results[2][q].result == "deep_path"

    def test_predict_tournament_handles_large_candidate_pool(self):
        b = ReflexEngineBackend()
        b.load()
        candidates = [f"dummy_skill_{i}" for i in range(24)] + ["mikrotik_router", "mariadb"]
        ranked, final_pkt = b.predict_tournament(
            state={"body": "Thêm rule chặn IP lạ vào firewall filter của routerboard Mikrotik"},
            question="Năng lực nào phù hợp nhất?",
            candidates=candidates,
            group_size=12,
            top_k=5,
        )
        assert len(ranked) == 5
        assert final_pkt.result == "mikrotik_router"
        assert ranked[0][0] == "mikrotik_router"
        assert sum(final_pkt.distribution.values()) == pytest.approx(1.0, abs=1e-6)

    def test_choice_over_cap_auto_routes_tournament(self):
        """Oversized CHOICE sets must never enter a single pass (transferred discipline)."""
        b = ReflexEngineBackend()
        b.load()
        opts = [f"skill_{i:02d}" for i in range(15)] + ["mikrotik_router"]
        assert len(opts) > MAX_OPTIONS_PER_QUESTION
        pkt = b.predict(
            state={"body": "Thêm rule chặn IP lạ vào firewall filter của routerboard Mikrotik"},
            questions=[(DecisionPrimitive.CHOICE, "pick one", opts)],
        )["pick one"]
        assert pkt.result in opts
        assert sum(pkt.distribution.values()) == pytest.approx(1.0, abs=1e-6)
        assert pkt.metadata["tournament"] is True
        assert pkt.metadata["shortlisted_from"] == len(opts)

    def test_long_state_truncation_flagged_never_silent(self):
        """Long states truncate to budget with an explicit flag; short states untouched."""
        b = ReflexEngineBackend()
        b.load()
        long_state = {"body": "x" * (MAX_STATE_CHARS + 5000)}
        pkt_long = b.predict(
            state=long_state,
            questions=[(DecisionPrimitive.BOOLEAN, "qq_long", None)],
        )["qq_long"]
        assert pkt_long.metadata["truncated"] is True
        pkt_short = b.predict(
            state={"body": "Xin chào"},
            questions=[(DecisionPrimitive.BOOLEAN, "qq_short", None)],
        )["qq_short"]
        assert pkt_short.metadata["truncated"] is False

    def test_manifest_scorer_trio_matches_code(self):
        """Manifest scorer_contract must equal backend constants (single truth)."""
        manifest = json.loads(
            (ROOT_DIR / "models" / "reflex_checkpoint_manifest.json").read_text(encoding="utf-8"))
        trio = manifest["scorer_contract"]
        assert trio["scorer_version"] == SCORER_VERSION
        assert trio["prompt_version"] == PROMPT_VERSION
        assert trio["max_options_per_question"] == MAX_OPTIONS_PER_QUESTION
        assert trio["max_state_chars"] == MAX_STATE_CHARS

    def test_reflex_engine_beats_tier3_rules_on_vi_master_40(self):
        cases_path = ROOT_DIR / "benchmarks" / "tier2" / "cases_vi_master_40.jsonl"
        cases = load_cases_jsonl(cases_path)
        assert len(cases) == 40

        reflex_res = Tier2Benchmark(ReflexEngineBackend(), warmup_runs=1, timeout_ms=450).run(cases)
        rule_res = Tier2Benchmark(Tier3RuleBaselineBackend(), warmup_runs=1, timeout_ms=450).run(cases)

        assert reflex_res.n_errors == 0
        assert reflex_res.calibration_state == "uncalibrated"
        assert reflex_res.latency.p95_ms < 450.0
        assert reflex_res.accuracy is not None and rule_res.accuracy is not None
        assert reflex_res.accuracy > rule_res.accuracy
        assert reflex_res.accuracy >= 0.95


class TestSovereignReflexHubSixTasks:
    """Verifies Pillar 3: Central Multi-Task Hub & Permanent 2-NEVER Invariant."""

    def test_task1_classify_intent_and_route_bilingual_and_fail_closed_mutate(self):
        hub = SovereignReflexHub(record_shadow=False)

        r_fast = hub.classify_intent_and_route("Xin chào buổi sáng, hôm nay thế nào?")
        assert r_fast["route"] == "fast_path"
        assert r_fast["language"] == "vi"
        assert r_fast["calibration_state"] == "uncalibrated"

        r_deep = hub.classify_intent_and_route("Phân tích memory leak trong driver C++ khi kết nối RouterOS API")
        assert r_deep["route"] == "deep_path"

        # Fail-closed invariant (ADR-0003): MUTATE_REVERSIBLE on uncalibrated backend MUST escalate to Tier 3
        r_mut = hub.classify_intent_and_route(
            "Phân tích giải thuật tối ưu hóa SQL",
            action_class=ActionClass.MUTATE_REVERSIBLE,
        )
        assert r_mut["execution_tier"] != ExecutionTier.TIER_2_LOCAL.value

    def test_task2_audit_plan_safety_permanently_locked_advisory_only(self):
        hub = SovereignReflexHub(record_shadow=False)

        # Calling with advisory_only=False MUST raise PermissionError (2-NEVER lock)
        with pytest.raises(PermissionError, match="2-NEVER Invariant Violation"):
            hub.audit_plan_safety("rm -rf /var/log", advisory_only=False)

        danger_vi = hub.audit_plan_safety("Xóa sạch thư mục /var/log bằng rm -rf")
        assert danger_vi["advisory_only"] is True
        assert danger_vi["can_authorize_execution"] is False
        assert danger_vi["risk_detected"] is True

        safe_vi = hub.audit_plan_safety("Đọc file README.md để xem hướng dẫn cài đặt")
        assert safe_vi["advisory_only"] is True
        assert safe_vi["risk_detected"] is False

    def test_task3_verify_cache_and_rerank_blocks_antonyms(self):
        hub = SovereignReflexHub(record_shadow=False)

        # Opposite meaning (bật vs tắt) must be rejected even if high vector similarity score
        res_antonym = hub.verify_cache_and_rerank(
            query="Hãy tắt tường lửa trên cổng ether1 của router",
            candidates=[
                {
                    "original_query": "Hãy bật tường lửa trên cổng ether1 của router",
                    "answer": "Đã bật tường lửa trên cổng ether1.",
                    "score": 0.96,
                }
            ],
        )
        assert res_antonym["cache_safe"] is False
        assert res_antonym["best_candidate"] is None
        assert res_antonym["rejected_antonym_count"] == 1

        # Same meaning must pass
        res_same = hub.verify_cache_and_rerank(
            query="Kiểm tra lưu lượng băng thông cổng ether1 router Mikrotik",
            candidates=[
                {
                    "original_query": "Kiểm tra băng thông cổng ether1 trên router Mikrotik",
                    "answer": "Lưu lượng hiện tại là 45 Mbps.",
                    "score": 0.94,
                }
            ],
        )
        assert res_same["cache_safe"] is True
        assert res_same["best_candidate"] is not None

    def test_verify_cache_and_rerank_accepts_string_candidates(self):
        """Regression test per Opencode Turn 244 probe: string candidates must be coerced cleanly."""
        hub = SovereignReflexHub(record_shadow=False)
        res = hub.verify_cache_and_rerank(
            query="Enable firewall on router ether1",
            candidates=[
                "Disable firewall on router ether1",
                "Enable firewall on router interface ether1",
            ],
        )
        assert res["rejected_antonym_count"] == 1
        assert res["cache_safe"] is True
        assert res["best_candidate"]["text"] == "Enable firewall on router interface ether1"

    def test_task4_audit_answer_quality(self):
        hub = SovereignReflexHub(record_shadow=False)

        good = hub.audit_answer_quality(
            query="Kiểm tra trạng thái dịch vụ",
            answer="Đã kiểm tra hoàn tất: toàn bộ dịch vụ hoạt động chính xác và ổn định.",
        )
        assert good["advisory_only"] is True
        assert good["is_grounded"] is True
        assert good["quality_score"] >= 2.5

        bad = hub.audit_answer_quality(
            query="Kiểm tra trạng thái dịch vụ",
            answer="Error: timed out. Không thể kết nối tới cơ sở dữ liệu.",
        )
        assert bad["quality_score"] < good["quality_score"]

    def test_task5_shortlist_capabilities(self):
        hub = SovereignReflexHub(record_shadow=False)
        pool = [f"tool_extra_{i}" for i in range(18)] + ["google_drive", "smtp_mail", "web_recon"]
        res = hub.shortlist_capabilities(
            query="Gửi email thông báo sự cố máy chủ đến ban quản trị",
            candidates=pool,
            group_size=10,
            top_k=4,
        )
        assert res["winner"] == "smtp_mail"
        assert "smtp_mail" in res["shortlist"]
        assert len(res["shortlist"]) == 4

    def test_task6_batch_triage_experiences(self):
        hub = SovereignReflexHub(record_shadow=False)
        logs = [
            {"body": "ConnectionResetError: [WinError 10054] An existing connection was forcibly closed"},
            {"body": "AssertionError: State conflict: order status is marked COMPLETED but payment is marked UNPAID"},
        ]
        triaged = hub.batch_triage_experiences(logs)
        assert len(triaged) == 2
        assert triaged[0]["category"] == "network_transient"
        assert triaged[0]["worth_distilling"] is False
        assert triaged[1]["category"] == "contradictory_facts"
        assert triaged[1]["worth_distilling"] is True


class TestDualCalibrationGateAndInstantFeedback:
    """Verifies Pillar 4: Dual 100/200 Gold Label Gate & <50ms Instant Feedback."""

    def test_dual_100_200_gold_label_gate(self, tmp_path: Path):
        gold_file = tmp_path / "master_gold_dataset.jsonl"
        fb_file = tmp_path / "feedback.jsonl"
        mgr = ReflexEvolutionManager(gold_dataset_path=gold_file, feedback_path=fb_file)

        # 1. 0 records -> blocked
        res0 = mgr.fit_temperature_from_gold_dataset()
        assert res0["status"] == "BLOCKED_BY_100_GOLD_LABEL_GATE"
        assert res0["calibrated"] is False
        assert mgr.get_calibration_state("vi") == "uncalibrated"

        # 2. 120 records (100 <= n < 200) -> internal fit allowed, but promotion remains BLOCKED ("uncalibrated")
        with open(gold_file, "w", encoding="utf-8") as f:
            for i in range(120):
                f.write(
                    json.dumps(
                        {
                            "sample_id": f"s_{i}",
                            "language": "vi",
                            "raw_confidence": 0.92,
                            "is_correct": True,
                            "reviewed_by_master": True,
                        }
                    )
                    + "\n"
                )
        res120 = mgr.fit_temperature_from_gold_dataset()
        assert res120["status"] == "FITTED_INTERNAL_ONLY"
        assert res120["calibrated"] is False
        assert mgr.get_calibration_state("vi") == "uncalibrated"

        # 3. 210 records (n >= 200) + low ECE -> machine call stops at READY_FOR_MASTER_APPROVAL
        with open(gold_file, "a", encoding="utf-8") as f:
            for i in range(120, 210):
                f.write(
                    json.dumps(
                        {
                            "sample_id": f"s_{i}",
                            "language": "vi",
                            "raw_confidence": 0.92,
                            "is_correct": True,
                            "reviewed_by_master": True,
                        }
                    )
                    + "\n"
                )
        res210_machine = mgr.fit_temperature_from_gold_dataset()
        assert res210_machine["status"] == "READY_FOR_MASTER_APPROVAL"
        assert res210_machine["calibrated"] is False
        assert res210_machine["ready_for_master_approval"] is True
        assert mgr.get_calibration_state("vi") == "uncalibrated"

        # Machine attempting to promote without Master key MUST raise PermissionError
        with pytest.raises(PermissionError, match="Master Governance Lock Violation"):
            mgr.promote_calibration("vi", master_approved=False)

        # Master key approval promotes "vi" to "calibrated", while "en" stays "uncalibrated"
        promo = mgr.promote_calibration(
            "vi",
            master_approved=True,
            master_signature="Master-LeeTrung-SignOff-2026",
        )
        assert promo["status"] == "PROMOTED_BY_MASTER"
        assert mgr.get_calibration_state("vi") == "calibrated"
        assert mgr.get_calibration_state("en") == "uncalibrated"

    def test_instant_feedback_under_50ms(self, tmp_path: Path):
        fb_file = tmp_path / "feedback.jsonl"
        mgr = ReflexEvolutionManager(
            gold_dataset_path=tmp_path / "gold.jsonl",
            feedback_path=fb_file,
        )
        hub = SovereignReflexHub(evolution_manager=mgr, record_shadow=False)

        fb_res = hub.learn_from_feedback(
            state={"body": "Tác vụ đặc biệt nội bộ của Master"},
            question="Năng lực nào phù hợp nhất để thực thi yêu cầu này?",
            target_value="custom_sovereign_skill",
            feedback_type="POSITIVE_EXEMPLAR",
            primitive="Choice",
            language="vi",
        )
        assert fb_res["latency_ms"] < 50.0

        shortlist_res = hub.shortlist_capabilities(
            query="Tác vụ đặc biệt nội bộ của Master",
            candidates=["mikrotik_router", "custom_sovereign_skill", "mariadb"],
            top_k=2,
        )
        assert shortlist_res["winner"] == "custom_sovereign_skill"

    def test_consumer1_soak_telemetry_counts_antonym_blocks(self, tmp_path: Path):
        soak_file = tmp_path / "reflex_cache_soak_telemetry.jsonl"
        hub = SovereignReflexHub(record_shadow=False, soak_telemetry_path=soak_file)

        hub.verify_cache_and_rerank(
            query="Hãy tắt dịch vụ cảnh báo trên server",
            candidates=[
                {
                    "original_query": "Hãy bật dịch vụ cảnh báo trên server",
                    "answer": "Đã bật dịch vụ cảnh báo.",
                    "score": 0.95,
                }
            ],
        )
        hub.verify_cache_and_rerank(
            query="Kiểm tra băng thông cổng ether1",
            candidates=[
                {
                    "original_query": "Kiểm tra lưu lượng băng thông cổng ether1",
                    "answer": "Băng thông ổn định.",
                    "score": 0.96,
                }
            ],
        )

        stats = hub.get_soak_telemetry()
        assert stats["total_cache_checks"] == 2
        assert stats["antonym_blocks"] == 1
        assert stats["cache_safe_passes"] == 1
        assert soak_file.exists()
        lines = [json.loads(line) for line in soak_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(lines) == 2
        assert lines[0]["rejected_antonym_count"] == 1
        assert lines[1]["cache_safe"] is True


class TestSixStepGovernanceAndFiveLayerLanguagePipeline:
    """Verifies the 6 OpenCode governance hardening steps, 5-layer VI/EN pipeline, and transferred decision techniques."""

    def test_step1_canonical_vocab_reuse_without_duplicate_enum(self):
        from core.cognitive_bus.reflex_hub import ACTION_VOCAB, DECISION_VOCAB

        assert len(DECISION_VOCAB) == 8
        assert len(ACTION_VOCAB) == 21
        assert "CLARIFY" in DECISION_VOCAB
        assert "DENY" in DECISION_VOCAB

        hub = SovereignReflexHub(record_shadow=False)
        res = hub.route_with_canonical_vocab("Xóa toàn bộ thư mục ~/.ssh bằng lệnh rm -rf")
        assert res["canonical_decision"] == "DENY"
        assert res["canonical_action"] in ACTION_VOCAB
        assert len(res["action_shortlist"]) == 3
        assert res["score_threshold_used"] == 0.92  # Wider abstention band for uncalibrated SCORE

    def test_step2_verify_and_close_fence_blocks_complete_candidate(self):
        hub = SovereignReflexHub(record_shadow=False)

        # Valid VERIFY_AND_CLOSE proposal never grants completion directly
        prop = hub.propose_completion_verification(
            state={"artifact": "output.json", "sha256": "abc123", "verify_file": "passed"},
            query="Đã tạo artifact và kiểm chứng hoàn tất sha256",
        )
        assert prop["proposal"] == "VERIFY_AND_CLOSE"
        assert prop["completion_granted"] is False
        assert prop["authority"] == "Runtime.CompletionAuthority"

        # Passing COMPLETE_CANDIDATE or COMPLETE as an option MUST raise PermissionError
        for bad_label in ("COMPLETE_CANDIDATE", "COMPLETE", "COMPLETED", "TASK_COMPLETE"):
            with pytest.raises(PermissionError, match="NO_EVIDENCE_NO_COMPLETION"):
                hub.propose_completion_verification(
                    state={"status": "done"},
                    custom_options=[bad_label, "CONTINUE_EXECUTION"],
                )

    def test_step3_wide_temperature_fit_and_order_invariance(self, tmp_path: Path):
        gold_file = tmp_path / "extreme_t_gold.jsonl"
        mgr = ReflexEvolutionManager(gold_dataset_path=gold_file)

        # Simulate an extreme overconfident bucket (raw_confidence=0.9999, target_prob=0.71)
        # where raw temperature T > 9.0 (beyond upstream's [0.5, 5.0] clamp).
        with open(gold_file, "w", encoding="utf-8") as f:
            for i in range(110):
                f.write(
                    json.dumps(
                        {
                            "sample_id": f"ext_{i}",
                            "language": "vi",
                            "raw_confidence": 0.9999,
                            "target_prob": 0.71,
                            "calibration_bucket": "boolean:2",
                            "reviewed_by_master": True,
                        }
                    )
                    + "\n"
                )
        fit_res = mgr.fit_temperature_from_gold_dataset()
        assert fit_res["status"] == "FITTED_INTERNAL_ONLY"
        fitted_t = mgr.get_temperature("vi", "Boolean", bucket="boolean:2")
        assert fitted_t > 8.0, f"Expected unclamped temperature > 8.0, got {fitted_t}"

        # Verify 100% option order permutation invariance
        b = ReflexEngineBackend(evolution_manager=mgr)
        b.load()
        inv = mgr.evaluate_order_invariance(
            backend=b,
            state={"body": "Thêm rule chặn IP lạ vào firewall filter của routerboard Mikrotik"},
            question="Năng lực nào phù hợp nhất?",
            options=["mariadb", "google_drive", "mikrotik_router", "smtp_mail", "web_recon"],
        )
        assert inv["passed"] is True
        assert inv["consistency_rate"] == 1.0
        assert inv["max_prob_drift"] == 0.0
        assert inv["canonical_winner"] == "mikrotik_router"

    def test_step4_real_failure_gold_harvester_and_sealed_test_independence(self, tmp_path: Path):
        gold_file = tmp_path / "real_failures_gold.jsonl"
        mgr = ReflexEvolutionManager(gold_dataset_path=gold_file)

        rec = mgr.record_real_failure_gold_candidate(
            state={"query": "Hãy tắt tường lửa cổng ether1", "cached": "Hãy bật tường lửa cổng ether1"},
            correct_choice="DENY",
            rationale="Semantic cache antonym inversion between bật and tắt",
            execution_evidence={"cache_similarity": 0.96, "antonym_pair": ["bật", "tắt"]},
            acceptance_criteria="verify_cache_and_rerank must return cache_safe=False",
            failure_archetype="SEMANTIC_CACHE_ANTONYM_CONFUSION",
            reviewed_by_master=False,
        )
        assert rec["reviewed_by_master"] is False
        # Unreviewed candidate does NOT count toward the 100-label gate
        assert mgr.count_verified_gold_labels()[0] == 0

        # Reject COMPLETE_CANDIDATE in gold harvester
        with pytest.raises(PermissionError, match="NO_EVIDENCE_NO_COMPLETION"):
            mgr.record_real_failure_gold_candidate(
                state={"query": "test"},
                correct_choice="COMPLETE_CANDIDATE",
                rationale="bad label",
                execution_evidence={"log": "1"},
                acceptance_criteria="must fail",
                failure_archetype="PREMATURE_COMPLETION_CLAIM",
            )

        # Sealed test independence: same author for test and scorer MUST raise PermissionError
        with pytest.raises(PermissionError, match="Zero Self-Grading Violation"):
            mgr.verify_sealed_test_independence("antigravity", "Antigravity")

        indep = mgr.verify_sealed_test_independence("master_leetrung", "opencode_auditor")
        assert indep["independent"] is True

    def test_step5_and_step6_ab_kill_switch_and_master_backend_flip_lock(self, tmp_path: Path):
        from core.cognitive_bus.backends import set_active_backend

        mgr = ReflexEvolutionManager(gold_dataset_path=tmp_path / "gold.jsonl")

        # All 3 improve -> KEEP_CANDIDATE
        keep = mgr.evaluate_ab_kill_switch(
            baseline_metrics={
                "true_completion_rate": 0.72,
                "premature_completion_rate": 0.14,
                "large_model_call_rate": 0.65,
            },
            candidate_metrics={
                "true_completion_rate": 0.84,
                "premature_completion_rate": 0.04,
                "large_model_call_rate": 0.42,
            },
        )
        assert keep["verdict"] == "KEEP_CANDIDATE"
        assert keep["all_three_passed"] is True

        # Missing even 1 of the 3 criteria -> KILL_AND_ROLLBACK
        kill = mgr.evaluate_ab_kill_switch(
            baseline_metrics={
                "true_completion_rate": 0.72,
                "premature_completion_rate": 0.14,
                "large_model_call_rate": 0.65,
            },
            candidate_metrics={
                "true_completion_rate": 0.85,
                "premature_completion_rate": 0.15,  # Worsened!
                "large_model_call_rate": 0.40,
            },
        )
        assert kill["verdict"] == "KILL_AND_ROLLBACK"
        assert kill["all_three_passed"] is False

        # Step 6: Machine cannot auto-flip ACTIVE_BACKEND
        with pytest.raises(PermissionError, match="Master Governance Lock Violation"):
            set_active_backend("reflex-engine", master_approved=False)

        assert set_active_backend(
            "reflex-engine",
            master_approved=True,
            master_signature="Master-LeeTrung-SignOff",
        ) == "reflex-engine"
        # Restore default "fake" with Master signature for test isolation
        set_active_backend("fake", master_approved=True, master_signature="Master-LeeTrung-Restore")

    def test_five_layer_language_pipeline_and_smart_state_truncation(self):
        from core.cognitive_bus.backends.reflex_engine_backend import (
             MAX_STATE_CHARS,
            _normalize_text,
            _truncate_state_with_flag,
            detect_language_with_trace,
        )

        # Layer 1: Diacritic shortcut
        t1 = detect_language_with_trace("Kiểm tra tường lửa trên cổng ether1")
        assert t1["language"] == "vi"
        assert t1["layer"] == "L1_DIACRITIC_SHORTCUT"
        assert t1["domain_prior"]["polysemy_resolved"] == "network_firewall"

        # Layer 2: Unaccented Vietnamese markers
        t2 = detect_language_with_trace("kiem tra tuong lua")
        assert t2["language"] == "vi"
        assert t2["layer"] == "L2_UNACCENTED_VI_MARKER"

        # Layer 3: Symmetric English function words
        t3 = detect_language_with_trace("Please check the firewall status")
        assert t3["language"] == "en"
        assert t3["layer"] == "L3_SYMMETRIC_EN_FUNCTION"

        # Layer 4: Honest abstention when evidence is missing
        t4 = detect_language_with_trace("xu ly cham", enable_upstream_accent_restore=False)
        assert t4["language"] == "*"
        assert t4["layer"] == "L4_HONEST_ABSTAIN_NEUTRAL"

        # Layer 5: Upstream phrase accent restoration + Downstream construction vs network prior
        t5 = detect_language_with_trace("xu ly cham", enable_upstream_accent_restore=True)
        assert t5["language"] == "vi"
        assert t5["layer"] == "L5_UPSTREAM_ACCENT_RESTORE_AND_DOMAIN_PRIOR"
        assert t5["accent_restored"] is True

        t_const = detect_language_with_trace("Xây dựng tường lửa bằng bê tông và cửa chống cháy ở tầng hầm")
        assert t_const["domain_prior"]["domain"] == "civil_construction"
        assert t_const["domain_prior"]["polysemy_resolved"] == "structural_fire_barrier"

        # Unaccented construction vs unaccented network disambiguation (Turn 248 Item 4)
        t_const_unacc = detect_language_with_trace("xay dung tuong lua bang be tong va cua chong chay o nha kho tang ham")
        assert t_const_unacc["domain_prior"]["domain"] == "civil_construction"
        assert t_const_unacc["domain_prior"]["polysemy_resolved"] == "structural_fire_barrier"

        t_net_unacc = detect_language_with_trace("kiem tra tuong lua tren router ether1 bang thong goi tin")
        assert t_net_unacc["domain_prior"]["domain"] == "network_security"
        assert t_net_unacc["domain_prior"]["polysemy_resolved"] == "network_firewall"

        # Coverage evaluator for upstream accent restore map (Turn 248 Item 5)
        from core.cognitive_bus.backends.reflex_engine_backend import evaluate_accent_restore_coverage
        cov = evaluate_accent_restore_coverage(["kiem tra tuong lua", "xu ly cham", "check server log"])
        assert cov["total"] == 3
        assert cov["restored_count"] == 2
        assert cov["default_enabled_in_predict"] is False

        # Step 1 ValueError on non-canonical decision label (Turn 248 Item 2)
        from core.cognitive_bus.reflex_hub import SovereignReflexHub
        hub = SovereignReflexHub()
        with pytest.raises(ValueError, match="Step 1 Governance Violation"):
            hub.route_with_canonical_vocab("Kiểm tra hệ thống", decision_options=["ALLOW", "PARALLEL_CUSTOM_ENUM"])

        # Smart State-Only Truncation: conversation lists keep tail (most recent turns), dicts keep head
        long_conv = [{"turn": i, "msg": "x" * 500} for i in range(100)]
        conv_str = _normalize_text(long_conv)
        trunc_conv, flag_conv = _truncate_state_with_flag(conv_str, long_conv)
        assert flag_conv is True
        assert len(trunc_conv) == MAX_STATE_CHARS
        assert '"turn":99' in trunc_conv  # Tail preserved for conversation list!

        long_doc = {"a_header": "START_MARKER_HEAD", "z_body": "y" * (MAX_STATE_CHARS + 2000)}
        doc_str = _normalize_text(long_doc)
        trunc_doc, flag_doc = _truncate_state_with_flag(doc_str, long_doc)
        assert flag_doc is True
        assert "start_marker_head" in trunc_doc  # Head preserved for non-conversation state!

    def test_num_predict_ssot_2048_and_length_truncation_and_version_pin(self):
        from core.governor.model_capabilities import ROLE_REQUIREMENTS, RoleRequirement
        from core.utils.engine import (
            LENGTH_CONTINUATION_NOTICE,
            append_length_continuation_notice,
            get_jkai_system_version,
            is_length_truncated,
        )
        from core.utils.model_router import ModelRouter

        # 1. Layer 1: RoleRequirement default & rule_hardware.md NUM_PREDICT column == 2048 for chat/analysis
        assert RoleRequirement("CUSTOM").max_output_tokens == 2048
        for role_name in ("RECEPTIONIST", "CHAT", "CRITIC", "PLANNER", "SUMMARIZER", "EXECUTOR"):
            assert ROLE_REQUIREMENTS[role_name].max_output_tokens == 2048

        from core.governor.execution_policy import ExecutionPolicy
        router = ModelRouter(str(ROOT_DIR / "intelligence" / "rule_hardware.md"))
        policy = ExecutionPolicy()
        for role_name in ("RECEPTIONIST", "CHAT", "CRITIC", "PLANNER", "SUMMARIZER", "EXECUTOR"):
            rc = router.get_role_config(role_name)
            assert rc["options"].get("num_predict") == 2048, f"{role_name} num_predict should be 2048"
            exec_prof = policy.derive_profile(rc)
            assert exec_prof.num_predict == 2048
            assert exec_prof.to_ollama_options()["num_predict"] == 2048

        assert router.get_role_config("DEEP_REASONER")["options"].get("num_predict") == 4096

        # 2. Layer 2: Ollama done_reason=="length" / eval_count>=num_predict detection & non-silent continuation notice
        assert is_length_truncated("length", eval_count=512, num_predict=2048) is True
        assert is_length_truncated("stop", eval_count=2048, num_predict=2048) is True
        assert is_length_truncated("stop", eval_count=410, num_predict=2048) is False

        cut_table = "| Cột 1 | Cột 2 |\n| :--- | :--- |\n| Dòng đang viết dở"
        marked = append_length_continuation_notice(cut_table)
        assert LENGTH_CONTINUATION_NOTICE.strip() in marked

        unclosed_code = "```python\ndef foo():\n    return 1"
        marked_code = append_length_continuation_notice(unclosed_code)
        assert marked_code.count("```") == 2
        assert LENGTH_CONTINUATION_NOTICE.strip() in marked_code

        # 3. Version pinning from CHANGELOG.md (v28.x, never hallucinated v47.0)
        ver = get_jkai_system_version()
        assert ver.startswith("v28.")
        assert ver != "v47.0"

        import sys
        brain_dir = str(ROOT_DIR / "services" / "ai-brain")
        if brain_dir not in sys.path:
            sys.path.insert(0, brain_dir)
        from prompt_engine.cognitive_context_compiler import CognitiveContextCompiler
        from prompt_engine.master_prompt_architect import master_prompt_architect

        compiled_ctx = CognitiveContextCompiler("test_ver").compile(role="RECEPTIONIST")
        assert f"JKAI Zenith OS {ver}" in compiled_ctx
        assert "v47.0" not in compiled_ctx

        mid_prompt = master_prompt_architect.build_master_system_prompt(role="RECEPTIONIST", prompt_variant="MID")
        assert ver in mid_prompt
        assert "v47.0" not in mid_prompt
