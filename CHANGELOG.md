# 📋 Changelog — JKAI Zenith
All notable changes to the JKAI Zenith Cognitive Operating System are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and adheres to Semantic Versioning.

---

## [v28.8.0] - 2026-10-14
### Added
- **Bước 2 Lộ Trình 6 Bước: Khung Điều Phối & Huấn Luyện LoRA Thật Đầu Tiên (Slice 6.2 Real LoRA Training & Verification Harness)**:
  - **Bu-lông 1 (N-gram Overlap Guard `< 0.40`, `core/os/cognition/real_lora_trainer.py`)**: Tự động bóc tách và đối chiếu 4-gram giữa dữ liệu candidate và kho Đề thi tuần (A, B, C). Loại bỏ tự động bất kỳ mẫu nào có tỷ lệ trùng lặp $> 40\%$ (`EXAM_NGRAM_OVERLAP_EXCEEDED`), bảo đảm zero exam leakage.
  - **Bu-lông 2 (50 Mẫu Gold Cân Bằng & Hợp Đồng 8 Trường, `data/dataset/gold_lora_50_samples.jsonl`)**: Phân bổ chính xác $10$ mẫu/nhóm cho cả 5 nhóm A_MATH_FIDELITY, B_ANAPHORA_GROUNDING, C_RETRIEVAL_CITATION, D_TOOL_AND_FILEOPS, E_MASTER_COMMUNICATION ($n=50$). Toàn bộ mẫu mang hợp đồng chuẩn 8 trường theo Hiến Chương Tự Học Điều 4 (`source`, `sample_count`, `created_at`, `expires_at`, `freshness_policy`, `benchmark_id`, `compute_budget`, `approval_tier`).
  - **Bu-lông 3 (Backend CPU_PEFT Thật, Time-box 30 Phút, CPU Quota $\le 70\%$)**:
    * `verify_training_backend`: Xác thực backend thực tế `CPU_PEFT` trên `torch 2.12.0+cpu` và `peft 0.21.1` (xóa bỏ triệt để số VRAM ảo).
    * Hạn ngạch thời gian: Áp trần tối đa 30 phút (`time_budget_seconds = 1800`) và lưu Checkpoint nguyên tử mỗi 10 bước (`step_10` đến `step_50`).
    * Hạn ngạch tài nguyên: Kill-switch ngắt job ngay lập tức (`JOB_TERMINATED_RESOURCE_GUARD`) nếu CPU vượt quá $70\%$, bảo đảm không làm treo máy chủ Master.
  - **Bu-lông 4 (Instant Auto-Rollback Dưới 10ms Khi Hồi Quy An Toàn)**: Cơ chế `evaluate_and_rollback` tự động kích hoạt hoàn tác về baseline trong $0.021\text{ms} < 10\text{ms}$ khi phát hiện `safety_regression > 0`.
  - **Kiểm Thử Toàn Diện**: `tests/test_slice_6_2_real_lora_training.py` đạt **5/5 passed in 13.69s**. Toàn bộ Sprint Suite đạt **110 passed, 1 skipped in 40.21s** (0 warnings, 0 regressions). Phương trình bảo toàn tệp tin: $2368 + 216 + 0 = 2584$.

---

## [v28.7.0] - 2026-10-14
### Added
- **Pha 6: Bộ Đề Thi Vận Hành Hàng Tuần & Sổ Cái Điểm Năng Lực (Slice 6.1 Weekly Sovereign Exam Runner & Live Baseline)**:
  - **Cách Ly 3 Tầng Vật Lý (`core/utils/project_workspace.py`, `learning_contract.py`)**: Cách ly kho đề thi niêm phong `sealed_C` qua 3 tầng (Filesystem pruning, RAG ingest gate, và Retrieval guard) để triệt tiêu mọi khả năng rò rỉ đề thi vào ngữ cảnh mô hình.
  - **Kho Đề Thi Chuẩn Hóa (`data/eval/`)**: Xây dựng 60 nhiệm vụ phân bố chuẩn trên 5 nhóm cốt lõi (A: Math Fidelity, B: Anaphora Grounding, C: Retrieval Citation, D: Tool & FileOps, E: Master Communication). Gồm Đề A (tuần lẻ), Đề B (đột biến tuần chẵn), và Đề C (niêm phong quý).
  - **Runner Đa Chế Độ & Bộ Chấm Độc Lập (`core/os/cognition/weekly_exam_runner.py`)**:
    * Chế độ `dry_run=True`: Hoàn thành trong 0.005s (< 1.0s), phục vụ CI/CD, đóng dấu cứng `capability_status: "PLUMBING_ONLY"`.
    * Chế độ `dry_run=False`: Kết nối trực tiếp Ollama live engine (`qwen2.5-coder:3b`), timeout cứng 3.0s/nhiệm vụ. Tuyệt đối **KHÔNG echo expected answer**, ghi nhận lỗi thực tế và đóng dấu `capability_status: "LIVE_EVALUATED"`.
    * `DeterministicRubricScorer`: Chấm nhóm E bằng 4 tiêu chí quy tắc cứng (độ dài, câu hỏi làm rõ, từ chối an toàn, số liệu thực tế), triệt tiêu 100% LLM tự chấm.
    * Thống kê khoảng tin cậy Wilson 95% và quy tắc đánh giá xu hướng 4–6 tuần ($n \ge 80$).
  - **Sổ Cái Chained Ledger Bất Biến (`data/telemetry/weekly_exam_ledger.jsonl`)**: Liên kết các báo cáo thi qua chuỗi băm SHA-256 (`prev_sha256 -> curr_sha256`), bảo vệ tính toàn vẹn lịch sử.
  - **Kỳ Thi Live Đầu Tiên & Điểm Baseline 0.45**: OpenCode trực tiếp thẩm định và chạy kỳ thi live trên model thật `qwen2.5-coder:3b`, xác lập **Baseline 9/20 (45%)** trung thực đầu tiên làm mốc số 0 cho mọi chu trình tự học sau này.
  - **Kiểm Thử Toàn Diện**: `tests/test_slice_6_1_weekly_exam_suite.py` đạt **5/5 passed in 1.11s**. Toàn bộ Sprint Suite đạt **105 passed, 1 skipped in 39.09s** (0 warnings, 0 regressions). Phương trình bảo toàn tệp tin: $2366 + 216 + 0 = 2582$.

---

## [v28.6.0] - 2026-10-14
### Added
- **Pha 5: Hiến Chương Tự Học & Khung Đo Lường Vận Hành (Slice 5.1 Learning Constitution & Anti-Cheating Harness)**:
  - **4 Tầng Học & Cấm lạm dụng Gradient (`core/os/cognition/learning_contract.py`)**: Phân biệt rạch ròi 4 tầng (1: Phiên / Working Memory $\to$ 2: Vận hành / Config & Router Policy $\to$ 3: Kỹ năng / Skill Library $\to$ 4: Model / LoRA Adapter). Nghiêm cấm dùng gradient nếu bài toán giải quyết được bằng cấu hình hoặc quy tắc mã nguồn.
  - **Hiến Chương Tự Học 14 Điều & Hợp Đồng Dữ Liệu (`validate_learning_proposal`)**: Thực thi kiểm tra bắt buộc 6 dòng (provenance, sample_count, benchmark_id, compute_budget, approval_tier, expires_at/freshness_policy). Cổng từ chối tự động `MISSING_EXPIRY` và `DATA_EXPIRED`.
  - **Chống Gaming Metric & Thời gian Master (`evaluate_loop_health`)**: Đo đa chiều (tỷ lệ proposal đạt cổng, cải thiện held-out delta thực chất $\Delta > 0$, phút can thiệp Master, chi phí compute). Từ chối hành vi giảm proposal để làm đẹp tỷ lệ.
  - **Exam Trace Blocklist 2 Cửa (`core/dataset/dataset_manager.py`)**: Bịt kín lỗ rò rỉ đề thi tại cả 2 cửa: `ingest_chunk_revision_as_label` (chuyển Master revision thành nhãn) và `harvest_trace_as_lora_sample` (thu hoạch trace cho huấn luyện LoRA). Mọi trace chứa exam markers đều bị chặn đứng với `ValueError('EXAM_TRACE_BLOCKLISTED')`.
  - **Niêm Phong & Cách Ly Đề Thi (`is_exam_isolated_path`, `query_exam_answer_via_retrieval`)**: Kho đề thi `sealed_C` được niêm phong cho đánh giá cuối quý; cấm RAG nhặt trộm câu hỏi/đáp án thi (`PermissionError`).
  - **Kiểm Định Độ Khó Xoay Đề 20% (`calibrate_exam_rotation_difficulty`)**: Yêu cầu kiểm định độ khó phân bố trước khi cho phép so sánh điểm chuỗi thời gian giữa các tuần ($\Delta \le 15\%$, $n \ge 3$).
  - **Bộ 7 Bài Test Thất Bại Trước (Fail-First Tests)**: `tests/test_slice_5_1_learning_constitution_failfirst.py` đạt **7/7 passed in 0.90s**. Toàn bộ Sprint Suite đạt **100 passed, 1 skipped in 50.93s** (0 warnings, 0 regressions). Phương trình bảo toàn tệp tin: $2364 + 216 + 0 = 2580$.

---

## [v28.5.0] - 2026-10-14
### Added
- **Pha 4: Recursive Self-Improvement Level 3 (RSIL-L3) & Autonomous Promotion (`core/os/cognition/rsil_orchestrator.py`, `rsil_tier1_loop.py`, `rsil_tier2_lora_loop.py`, `rsil_tier3_cross_stage_engine.py`)**:
  - **Slice 4.1 (RSIL-L3 Core Orchestrator & 2-Layer Taxonomy)**: Implemented `RSILOrchestrator` with 4 orthogonal constitutional gates (Gain, Safety, AST Invariant, Resource Ceiling $\le 30\%$). 2-Layer Taxonomy enforces Tier 3 on any diff touching protected security paths (`security/`, `auth/`, `sanitizer/`, `egress/`) or symbols (`validate_egress_url_ssrf_safe`, `CompletionAuthority`...). Chained SHA-256 Promotion Journal ensures cryptographic traceability.
  - **Slice 4.2 (Tier 1 Autonomous Tuning Loop)**: Implemented `AutonomousRAGOptimizer` for automatic RRF $k=60$ parameter optimization ($\Delta \ge +0.05$), `AutonomousDatasetIngestionLoop` for 100% accurate weak-supervision labeling, and `AutonomousPrefixOptimizer` for volatile header relocation to maximize KV-cache reuse.
  - **Slice 4.3 (Tier 2 LoRA Evolution Loop & Instant Rollback)**: Implemented `AutonomousLoRAEvolutionLoop` evaluated on 3-fold held-out Golden Vault ($H_1, H_2, H_3$) under CPU load $\le 70\%$ and quota limit (max 3/week). Implemented `CanaryDriftMonitor` with 10-mission sliding window, **Instant Auto-Rollback in $< 10\text{ms}$** ($0.018\text{ms}$), and **Fail-Closed Auto-Freeze** after 2 consecutive rollbacks.
  - **Slice 4.4 (Cross-Stage Proposal Engine & Master Handshake Gate)**: Implemented `CrossStageProposalEngine` mapping StageAttribution 6-stage telemetry to remediation proposals. Implemented `MasterAuthorityHandshakeGate` with out-of-band HMAC-SHA256 Master Key challenge-response, 0 secrets in core source code, and fail-closed rejection of autonomous self-signing. Complete recursive self-improvement cycle orchestrated via `run_rsil_l3_full_cycle`.
- **Pha 3: Backlog Master 5-Stage Closure & Live Services Hardening (`core/utils/`, `core/cognitive_bus/`, `tests/`)**:
  - Closed 15 backlog items: StageAttribution 6 khâu (2.1% overhead), CacheAligner (20/20), Capability Registry live, Quad RRF (1.0), Parent-Child (1.0), Reflect Job HMAC (10/10), Chunk-to-label (100%), Memory Defense (45 samples, 0% FP), LongMemEval-VI (0% drift), Boot Page (152 tok, 81%-94% savings), Fork/Rewind, and Chunk Versioning.
  - Verified live service contracts on Ollama (num_predict ceiling at 19.37 tok/s), Qdrant REST port 6333, and live PyTorch 2.12 + PEFT 0.21 LoRA fine-tuning.
- **Pha 1 & 2: Dual-Pillar Infrastructure (`core/kernel/`, `core/utils/repo_map.py`, `core/os/cognition/worktree_sandbox.py`)**:
  - Implemented 2-Tier AST RepoMap (< 3.3ms warm cache), ACI Guarded Code Surgery (< 2.1% error, 0 token waste), StreamBufferStore with TTL, MCP Allowlist, SSRF Guard (6/6 vectors blocked), and Git Worktree Sandbox lifecycle.

---

## [v28.4.1] - 2026-10-11
### Fixed
- **Eliminated 512-Token Output Truncation & Hallucinated Version (`intelligence/rule_hardware.md`, `core/governor/model_capabilities.py`, `core/governor/execution_policy.py`, `core/utils/engine.py`, `services/ai-brain/prompt_engine/cognitive_context_compiler.py`, `master_prompt_architect.py`)**:
  - **Layer 1 (`NUM_PREDICT` SSoT Column & 2048 Budget)**: Added explicit `num_predict` column and `CHAT` role to Section 3 (`Active Role Mapping`) of `intelligence/rule_hardware.md`, and raised `RoleRequirement.max_output_tokens` for `RECEPTIONIST`, `CHAT`, `CRITIC`, `PLANNER`, `SUMMARIZER`, and `EXECUTOR*` to `2048` (`DEEP_REASONER` at `4096`).
  - **Layer 2 (Ollama `done_reason="length"` Guard & 1-Hop Auto-Continuation)**: Added `is_length_truncated()` and `append_length_continuation_notice()` in `core/utils/engine.py`. When Ollama stops due to `done_reason == "length"` (or `eval_count >= num_predict`), `call_chat` automatically triggers a 1-hop continuation pass or appends an explicit continuation notice (closing any unclosed code fence), strictly forbidding silent mid-table truncation.
  - **Canonical Repo Version Pinning (`get_jkai_system_version`)**: Replaced hardcoded `v47.0` in `cognitive_context_compiler.py` with dynamic version lookup from `CHANGELOG.md` (`v28.4.1`) and pinned `[RUNTIME VERSION]` in `MasterPromptArchitect` across `FULL`, `MID`, and `LEAN` variants.

---

## [v28.4.0] - 2026-10-11
### Added
- **6-Step Governance Hardening & Master Key Lock (`core/cognitive_bus/reflex_hub.py`, `reflex_evolution.py`, `backends/__init__.py`, `confidence_policy.py`)**:
  - **Step 1 (Zero New Duplicate Enums)**: Locked canonical 8-label `DECISION_VOCAB` and 21-label `ACTION_VOCAB` (`route_with_canonical_vocab`).
  - **Step 2 (`VERIFY_AND_CLOSE` Fence)**: Blocked model completion claims (`FORBIDDEN_COMPLETION_LABELS`); only `VERIFY_AND_CLOSE` proposals (`propose_completion_verification`) are permitted for Runtime `CompletionAuthority`.
  - **Step 3 (Calibration & Order-Invariance)**: Wider `SCORE` abstention (`0.92` uncalibrated / `0.80` calibrated), wide `[0.2, 15.0]` bucketed temperature fitting (`choice:2`, `choice:3-5`, `choice:6-10`, `boolean:2`, `score:3-5`), compact JSON state serialization (`separators=(",", ":")`), smart conversation-tail vs document-head truncation, and 100% option-order invariance (`evaluate_order_invariance`).
  - **Step 4 (Real Failure Harvester & Sealed Test Independence)**: 5-archetype gold harvester (`record_real_failure_gold_candidate`) and author/scorer independence gate (`verify_sealed_test_independence`).
  - **Step 5 & 6 (3-Metric A/B Kill-Switch & Master Key Lock)**: `evaluate_ab_kill_switch` (`true_completion_rate` up, `premature_completion_rate` down, `large_model_call_rate` down) and `PermissionError` lock on `set_active_backend` and `promote_calibration` without `master_approved=True` and `master_signature`.
- **5-Layer VI/EN Language Pipeline & Zero External URLs in Manifests (`reflex_engine_backend.py`, `models/reflex_checkpoint_manifest.json`, `models/reflex_engine/0.4.2/manifest.json`)**:
  - Implemented `detect_language_with_trace` across 5 layers (`L1_DIACRITIC_SHORTCUT`, `L2_UNACCENTED_VI_MARKER`, `L3_SYMMETRIC_EN_FUNCTION`, `L4_HONEST_ABSTAIN_NEUTRAL`, `L5_UPSTREAM_ACCENT_RESTORE_AND_DOMAIN_PRIOR` distinguishing network firewall vs civil construction fire barrier).
  - Purged all external URLs from manifests (`"external_urls_allowed": false`) and locked with `71/71` passing tests across all 4 suites.

---

## [v28.3.1] - 2026-10-11
### Added
- **Transferred decision-model discipline, batch 1 (`core/cognitive_bus/backends/reflex_engine_backend.py`, manifests, tests)**:
  - CHOICE questions above 10 options auto-route to tournament brackets inside `predict()` (winner share as temperature-scaled confidence, `tournament` + `shortlisted_from` flags in packet metadata).
  - State truncation budget (32000 chars) with explicit `truncated` flag on every packet, never silent.
  - Scorer/prompt/temperature version trio (`bilingual_semantic_matrix_v2` / `1`) locked in both manifests and asserted equal to code constants by test.
  - Tests: 3 new regression tests, suites at 103 passing.

---

## [v28.3.0] - 2026-10-11
### Changed
- **Local-first processing caps (`core/governance/token_budget_guard.py`, `intelligence/rule_hardware.md`)**:
  - Token quota 50K/mission no longer hard-aborts: 80%/100%/200% thresholds emit telemetry only. Legacy hard abort preserved behind opt-in `abort_on_exceed=True`.
  - New processing cap `max_invocations` (default 500): exceeding aborts + trips replan breaker (infinite-loop / Self-DoS protection). Data in store is uncapped; per-call processing is capped per model.
  - New `2.6 Per-Model Processing Envelope` table in `rule_hardware.md` documenting native vs operational ctx per model (GPU VRAM-fit values kept at soak-proven levels).
  - Tests: `tests/test_token_budget_guard.py` 7/7 passing under the new spec.

---

## [v28.2.1] - 2026-10-11
### Fixed
- **Root language-routing fix (`detect_language_bcp47` in `core/cognitive_bus/backends/reflex_engine_backend.py`)**:
  - Undiacritic text with insufficient signal now abstains to neutral `"*"` instead of guessing `"en"`, eliminating forced misrouting of short Vietnamese ops commands (`mo file bao cao`, `xem log server`) and bare noun phrases (`Check firewall gap`).
  - Added 9 collision-audited ops markers (`mo`, `tat`, `xem`, `ghi`, `doi`, `danh`, `sach`, `tinh`, `lenh`) plus an English function-word set that excludes Vietnamese lookalikes (`an`, `in`, `do`, `to`, `can`, `no`, `a`).
  - Locked by ops battery `benchmarks/tier2/lang_detect_ops_vi_en.jsonl` (30 cases: accented/unaccented/EN/neutral) with 100% gate in `tests/test_sovereign_reflex_hub.py` (`62/62` tests passing). Turn-245 regressions (`Check the firewall`, `Ban the user`, `He is admin`) stay green.

---

## [v28.2.0] - 2026-10-11
### Added
- **Sovereign Bilingual (EN/VI) Reflex Decision Backend (`core/cognitive_bus/backends/reflex_engine_backend.py`, `local_reflex_backend.py`)**:
  - Clean-room single-pass decision backend (`ReflexEngineBackend`, registered as `"reflex-engine"` and `"sovereign-reflex"`) supporting Vietnamese and English (`detect_language_bcp47`), symmetric binary cross-check for `Boolean`, expected-value rubric scoring for `Score`, length-sorted batch evaluation (`predict_batch`), and tournament bracket shortlisting (`predict_tournament`, `group_size=12`).
  - Benchmarks on `benchmarks/tier2/cases_vi_master_40.jsonl`: `100%` accuracy (`40/40`, `P95 = 0.315ms < 450ms`) vs `40%` (`16/40`) on Tier 3 deterministic rules.
- **Central Multi-Task Sovereign Reflex Hub (`core/cognitive_bus/reflex_hub.py`)**:
  - Unified 6-task System-1 hub (`classify_intent_and_route`, `audit_plan_safety` with permanent `advisory_only=True` lock in code, `verify_cache_and_rerank` with soak telemetry counters, `audit_answer_quality`, `shortlist_capabilities`, and `batch_triage_experiences`).
  - Wired Consumer 1 (`verify_cache_and_rerank`) into `core/utils/cognitive_memory.py` (`check_reflex`) to block antonym/negation semantic cache hits.
- **Dual 100/200 Gold Label Calibration Gate & Instant Feedback (`core/cognitive_bus/reflex_evolution.py`)**:
  - Enforces `n < 100` (`BLOCKED_BY_100_GOLD_LABEL_GATE`), `100 <= n < 200` (`FITTED_INTERNAL_ONLY`, remaining `"uncalibrated"`), and `n >= 200` with `ECE <= 0.15` (`CALIBRATED`), plus `<50ms` RAM-first `learn_from_feedback` and contrastive trajectory harvesting.
- **IP & Brand Honesty Guardrail & Dual Manifest (`tests/test_ip_brand_guardrail.py`, `models/reflex_checkpoint_manifest.json`, `models/reflex_engine/0.4.2/manifest.json`, `requirements-reflex.txt`)**:
  - Word-boundary AST identifier scanner, Apache-2.0 attribution compliance, and 2-way synchronized checkpoint manifests (`61/61` tests passing).

---

## [v28.1.0] - 2026-10-11
### Fixed
- **Stream Loop Indentation & Premature Thought Flush (`core/utils/engine.py`)**:
  - Dedented final non-delta stream flush and `[THINKING EXTRACTION]` outside `async for line in _iter_stream_lines():` so Redis pub/sub is flushed once upon stream completion instead of on every token, and prevented `full_content` from being prematurely overwritten by partial `thinking_content` on the first reasoning token.
- **GPU VRAM Lock Leak on CPU-Bound Roles (`core/utils/engine.py`)**:
  - Scoped `lock:gpu_vram` acquisition strictly to GPU executions (`use_gpu_lock = bool(is_gpu and not is_cloud)`) and paired release with `gpu_lock_acquired`, eliminating the 30-second Redis lock leak previously caused by CPU roles (`EMBEDDER`, `VISION` on Port 11435).
- **SSoT Hardware Temperature & AMG v2 Profile Enforcement (`core/utils/engine.py`)**:
  - Merged `exec_profile.to_ollama_options()` with `rule_hardware.md` SSoT options, sanitized metadata keys from `safe_options`, and prevented hardcoded role temperatures (`0.7`) from overriding SSoT values in `intelligence/rule_hardware.md`.
- **StatePipeline Cognitive Override `TypeError` (`services/ai-brain/state_pipeline.py`)**:
  - Safely handled both `dict` and `str` returns from `engine.call_chat(..., json_mode=True)` before inspecting `res_data.get("override")`.
- **Single-Pass Coreference & Intent Routing (`services/ai-brain/receptionist/receptionist_core.py`, `services/ai-brain/fast_pipeline.py`)**:
  - Forwarded `jkai_route_decision` and `jkai_coref_resolved` from the AI OS Ingress Orchestrator into `FastPipeline.execute` to eliminate redundant coreference resolution and double intent routing.

---

## [v28.0.0] - 2026-09-30
### Added
- **Embodied OS Agent Actuators (M0–M2)**:
  - `M0`: Atomic file writing with `.tmp.<pid>.<time_ns>`, automatic `.bak` backups, SHA-256 verification, and 3-tier resilient file surgery (Exact $\to$ CRLF/LF normalization $\to$ Indentation-stripped fuzzy match).
  - `M1`: Command execution sandbox with 4-tier policy gate (`READ_ONLY`, `MUTATION_LOCAL`, `DANGEROUS_SYSTEM`, `AMBIGUOUS_HIGH_IMPACT`), subprocess tree termination, and 16KB output truncation.
  - `M2`: Containerized browser interaction service (`services/ai-browser` on port 8003) with CloakBrowser Stealth Engine v2.0, Crawl4AI, and Playwright Chromium.
- **SSoT AI Agent Working Principles (`.keyword.md`)**:
  - Restored and consolidated comprehensive working principles for AI coding agents across 11 structured sections.
  - Incorporated Boot-on-Start protocol, Root Philosophy (Anti-Patching, Anti-Redundancy), 4-Step Self-Audit Protocol, 6 Red Lines, and Evidence Execution Contract.
- **International Architecture Documentation**:
  - Added `docs/architecture/SYSTEM_ARCHITECTURE.md` (IEEE/ISO 42010 Architecture Description).
  - Added `docs/architecture/HARDWARE_AFFINITY.md` (NCNN-inspired NUMA & INT8 KV Cache specs).

### Changed
- Standardized Windows path normalization (`os.path.normpath`) in `_guard_path` to resolve drive letter conflicts (`D:/Docker/JKAI`).
- Enforced strict separation between AI Agent Working Principles (`.keyword.md`) and JKAI System Architecture documentation (`docs/architecture/`).

### Removed
- Permanently purged obsolete LoRA fine-tuning scripts and temporary distillation scratch files per Master directive.

---

## [v27.0.0] - 2026-08-02
### Added
- **Adaptive Model Governor (AMG v2)**:
  - Model-blind bootstrap architecture in `core/governor/` and `core/runtime/`.
  - Dynamic hardware inspection, VRAM budgeting, and automatic `ExecutionProfile` generation.
  - Separation of Infrastructure Plane (`Start_JKAI_Zenith.bat`) from Decision Plane (`amg_boot.py`).

---

## [v26.2.0] - 2026-08-02
### Added
- **Execution Integrity Layer & Security Boundary**:
  - 3-state authorization: `ALLOW`, `DENY`, `REQUIRE_APPROVAL` (Fail-Closed).
  - Permanent Execution Security Matrix covering 10 adversarial vectors (Replay attacks, Action mutation, ID spoofing, Subprocess bypassing).
  - Architect's Rule #1 (Rule of Merger): Every side-effect must have an authorized execution path.
- **3-Layer Separation Architecture**:
  - Formal registration of Cognitive Layer, Authority Layer, and Execution Layer.
  - Cognitive Scaling Hypothesis formalized.

---

## [v25.0.0] - 2026-08-02
### Added
- **Universal Cognitive World State (UCWS)** & **Cognitive Continuity Engine (CCE)**:
  - 7-dimensional cognitive state reducer: $W(N+1) = \text{Reduce}(W(N), \text{Event})$.
  - Causal execution tracing and state snapshotting.

---

## [v24.0.0] - 2026-08-02
### Added
- **Active Core Memory & Human Approval Gate**:
  - Dynamic prompt injection for active memory blocks.
  - Interrupt-driven Human-in-the-Loop gate for high-risk system mutations.
  - W3C OTLP `traceparent` distributed telemetry across microservices.

---

## [v19.1.0] - 2026-05-24
### Added
- **Event-Sourced Mission Runtime & DAG Scheduler**:
  - Append-only JSONL Event Store with O(1) snapshot state recovery.
  - Asynchronous DAG execution waves with token-pruned context policies.
  - Critic validation nodes with closed-loop self-correction.
- **NCNN-Inspired Hardware Affinity**:
  - NUMA node pinning (`CPU_OLLAMA_NUMA=1`) for dual Xeon Broadwell-EP sockets.
  - INT8 KV Cache quantization (`OLLAMA_KV_CACHE_TYPE=q8_0`).
  - Zero-copy memory-mapped file backing (MMAP) for CPU model layers.

---
*For internal cognitive memory logs, see `intelligence/identity/GLOBAL_SYSTEM_CONTEXT.md`.*
