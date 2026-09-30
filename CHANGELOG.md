# 📋 Changelog — JKAI Zenith
All notable changes to the JKAI Zenith Cognitive Operating System are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and adheres to Semantic Versioning.

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
