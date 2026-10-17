# 📋 Changelog — JKAI Zenith
All notable changes to the JKAI Zenith Cognitive Operating System are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and adheres to Semantic Versioning.

## [v28.20.0] - 2026-10-17
### Added & Hardened — Antigravity Aesthetic UI Reform & Dual-Tier Language Governance Protocol
- **Antigravity Aesthetic UI Reform (`services/mission-control/frontend/src/components/zenith/`)**:
  - **Universal Backend Log Sanitizer (`stripLogMetadata` in `LogElements.tsx`)**:
    * Recursive multi-pattern extraction and stripping of raw backend log headers: `[INFO]`, timestamps (`DD/MM/YYYY`, ISO), roles (`[RECEPTIONIST]`, `[SUMMARIZER]`, `[PLANNER]`), and `[Task: ...]`.
  - **Antigravity-Grade Reasoning Drawer (`ReasoningBlock` in `LogElements.tsx`, `LogItem.tsx`)**:
    * Automatically encapsulates all raw JSON planning dumps, critic evaluations, and intermediate thoughts into collapsible disclosures with adaptive headers (`Kế hoạch chiến lược`, `Thẩm định chất lượng`, `Đã tư duy`).
    * Structured markdown parsing of inner JSON plans into human-readable steps.
  - **Action Badge Visual Overhaul & Consecutive Dedup (`ActionBadge` in `LogElements.tsx`, `IntelligenceStream.tsx`)**:
    * Explicit categorization and chips for Web Searches (with clean query chips, e.g. `"đơn xin nghỉ phép học sinh"`), Web Reads (domain chip, e.g. `maudon.vn`), Codebase Searches, and Shell Commands.
    * Eliminated cryptic noise tokens such as `[/]`.
    * Consecutive action deduplication ensuring 1 tool invocation renders exactly 1 badge with zero stacked clones.
  - **Receptionist Identity Polish (`LogItem.tsx`)**:
    * Normalized conversational responses to the **JKAI** identity with high-tier cyan aura and brain emblem, eliminating fragmented intermediary agent banners.
- **Dual-Tier Language Governance Protocol (`.keywork.md`, `.keyword.md`, `intelligence/identity/ZENITH_SOVEREIGN_RULES.md`, `core/kernel/cognitive_loop.py`)**:
  - **Master Communication Tier (100% Vietnamese)**:
    * Enforced strict rule across all agent roles: all conversational exchanges, explanations, progress reports, and final deliverables directed to Master MUST be 100% in natural, idiomatic Vietnamese.
  - **Execution & Retrieval Tier (Adaptive Multilingual)**:
    * Granted full operational freedom for internal execution: web searches, technical documentation retrieval, error diagnosis, and tool parameter querying dynamically utilize Vietnamese, English, or any source language that maximizes data precision and information quality.

---

## [v28.19.0] - 2026-10-16
### Added & Hardened — Multi-Agent Cloud Discussion Subsystem (JKAI Discuss Protocol v1.0) & Universal Dynamic Model Resolver
- **Multi-Agent Cloud Discussion Subsystem (`core/security/trigger_parser.py`, `core/security/egress_gate.py`, `core/security/data_leak_guard.py`, `core/security/canary_guard.py`, `core/security/context_canary.py`, `core/security/egress_log.py`, `core/security/role_contract.py`, `core/security/delphi_protocol.py`, `core/security/dynamic_model_resolver.py`, `core/security/cloud_provider_client.py`, `core/os/cognition/cloud_discuss_orchestrator.py`, `core/os/orchestrator/handlers/cloud_discuss.py`)**:
  - **Deterministic Trigger Parsing & Source Isolation (`core/security/trigger_parser.py`)**:
    * Implemented Unicode NFKD diacritics stripping and normalization for Vietnamese commands ("Hãy thảo luận với group AI...", "thảo luận với Gemini và ChatGPT...").
    * Enforced strict Source Isolation accepting triggers exclusively from `master_cli`, `master_ui`, or `master_voice`, completely defusing indirect prompt injection from file or web ingestion.
    * Integrated Deterministic Negation Guard rejecting negative commands ("Đừng gọi Gemini...", "Chỉ local...").
  - **Dual-Killswitch Egress Gate & Hardened Pre-Send Scrubber (`core/security/egress_gate.py`)**:
    * Maintained `JKAI_LOCAL_ONLY=1` immutable baseline; egress requires dual authorization (`JKAI_DISCUSS_ALLOWED=1` scoped strictly within execution lifecycle via `try...finally`).
    * Pre-send scrubber sanitizes local absolute paths (`D:/Docker/JKAI`, `C:\Users`), internal IPs (`127.0.0.1`, `10.0.0.0/8`, `192.168.0.0/16`), API key patterns (`sk-`, `tvly-`, `xai-`, `AIzaSy`), and Vietnamese citizen IDs (12 digits).
  - **Data Leak Guard & Reverse Solicitation Defense (`core/security/data_leak_guard.py`)**:
    * Detects reverse prompt probes soliciting internal source code, credentials, `.env` files, or filesystem layout.
    * Hard blocks leaking outbound payloads and emits real-time `MasterSecurityAlert` with `CRITICAL` severity.
  - **Virtual Canary Guard & Active Context Mosaic Defense (`core/security/canary_guard.py`, `core/security/context_canary.py`)**:
    * In-memory virtual canary token registry mapping sensitive project files to UUIDs, blocking egress upon detection without physical git conflicts.
    * 100% rule-based Active Context Canary combining regex, architecture gazetteer, and Jaccard overlap to prevent cumulative mosaic leaks.
  - **Egress Cryptographic Hash-Chain Ledger (`core/security/egress_log.py`)**:
    * Tamper-evident ledger chaining `prev_hash -> entry_hash` persisted to `data/telemetry/egress_hash_chain.jsonl`.
  - **Neutral Technical Role Contract & Delphi Protocol Consensus Tracker (`core/security/role_contract.py`, `core/security/delphi_protocol.py`)**:
    * Zero metadata leakage: system prompts completely strip mentions of "Master", "JKAI", "internal", or org identity.
    * Enforces strict schema formatting (`FACT`, `INFERENCE`, `HYPOTHESIS`, `UNKNOWN`) and verifies role drift.
    * Claim-level consensus tracking classifying outcomes into 5 states: `VERIFIED`, `AGREED_UNVERIFIED`, `CONFLICTED`, `INSUFFICIENT_EVIDENCE`, `REJECTED`. Unverified consensus is never automatically treated as true. Includes model shuffling and 10-round circuit breaker.
  - **Universal Dynamic Model Resolver & Fallback Cascade (`core/security/dynamic_model_resolver.py`)**:
    * Future-proof model version resolution supporting aliases (`latest-flash`, `latest-mini`, `latest-reasoner`, `AUTO_LATEST`) and semantic version sorting (`3.8 > 2.5 > 1.5`).
    * Implemented provider-specific fallback cascade for Google Gemini (`gemini-3.8-flash` -> `gemini-2.5-flash` -> `gemini-1.5-flash`), OpenAI (`gpt-5-mini` -> `gpt-4o-mini`), DeepSeek, and Grok/xAI to withstand 404 deprecations and 503 high-load spikes.
  - **Receptionist Early Interception Handler (`core/os/orchestrator/handlers/cloud_discuss.py`)**:
    * Registered as Handler #3 in `core/os/orchestrator/handlers/__init__.py`, intercepting discussion queries before standard FAST/Deep pipelines and returning a structured 4-part Executive Briefing.
- **Verification Suite**:
  * `tests/test_cloud_discuss_protocol.py`: **21/21 passed (100%)** in 1.17s.
  * Full regression test suite (A1–A8 + Sovereign Cascade + Cloud Discuss): **74/74 passed (100%)**.

---

## [v28.18.0] - 2026-10-16
### Added & Verified — Phase A8: Live End-to-End PARTIAL Replan Drill & Sovereign Adaptation Ledger
- **Live End-to-End PARTIAL Replan Subsystem (`core/os/cognition/adaptive_controller.py`, `core/os/cognition/recovery_drill_harness.py`, `core/os/cognition/event_checkpoint.py`, `tests/test_phase_a8_live_partial_replan_drill.py`)**:
  - **Completion Gate & Checkpoint Backtracking Integration**:
    * Strictly enforced `INCOMPLETE` refusal on partial delivery (e.g. 2/5 criteria verified), eliminating fake completion risks.
    * CheckpointStore automatically captures immutable `PARTIAL` snapshot and enables Time-Travel Backtracking to preserve verified achievements.
  - **AdaptiveController TARGETED_REPAIR Branch**:
    * Extended `CognitiveStateSnapshot` with `outcome_status`, `unresolved_criteria_ids`, and `verified_criteria_ids`.
    * Implemented deterministic routing to `AdaptiveStrategy.ERROR_ADAPTIVE_RECOVERY` with `TARGETED_REPAIR` recovery branch, eliminating blind repetition.
  - **Live Recovery Drill Harness (`execute_partial_delivery_replan_drill`)**:
    * Added `FaultType.PARTIAL_DELIVERY` to operational recovery taxonomy.
    * Automated closed loop: Step 1 Partial delivery (2/5) $\rightarrow$ Checkpoint committed $\rightarrow$ Time-Travel Backtracking $\rightarrow$ AdaptiveController replan $\rightarrow$ Step 2 Targeted Repair (remaining 3/5) $\rightarrow$ Completion Gate verification (5/5) $\rightarrow$ `COMPLETE`.
    * Synchronized with `FullChainTracer` and persisted cryptographically to `data/telemetry/recovery_drill_ledger.jsonl` with pure LF line endings.
  - **Phase A8 Verification Suite**: **6/6 passed (100%)** in `tests/test_phase_a8_live_partial_replan_drill.py` (Full Phase A suite: **50/50 passed**).

---

## [v28.17.0] - 2026-10-16
### Added & Hardened — Sovereign 4-Tier Search Cascade & Canonical Web Interfaces
- **Sovereign 4-Tier Search Cascade (`core/retrieval/rss_poller.py`, `tools/web_search.py`, `services/tools/web_search.py`, `docker-compose.yml`, `config/searxng/settings.yml`)**:
  - **Tier 1 (Direct RSS Feeds)**: Implemented in-tree `RSSFeedPoller` with RFC-822/ISO date normalization, disk-backed cache (`data/cache/rss_feed_cache.json`), freshness categorization (`fresh`, `stale:<date>`, `date_unknown`), and strict precision lexical search (50% token coverage threshold + exact phrase + recency boost) targeting high-priority macro/financial feeds (Vietstock, VnEconomy, CafeF, Kitco).
  - **Tier 2 (Self-Hosted SearXNG Metasearch)**: Added local SearXNG service to `docker-compose.yml` (port `8888:8080`, JSON format enabled, zero docker socket, no external telemetry) acting as sovereign privacy-first metasearch aggregator.
  - **Tier 3 (Hardened DuckDuckGo Direct HTML)**: Implemented `DDGBotDetectionError` awareness in `_search_duckduckgo_direct_html` to detect HTTP 403/429 and CAPTCHA/anomaly challenge signatures, preventing misinterpretation of bot-blocking as honest zero-result search outcomes.
  - **Tier 4 (External Tavily Fallback)**: Transparent fallback when self-hosted and direct channels are exhausted.
- **Canonical Sovereign Web Tooling Standards (`tools/web_search.py`, `intelligence/skills/DEVOPS/SYSTEM_CORE_EXECUTOR/logic.py`)**:
  - Standardized canonical aliases: `webfetch = fetch_url_content` (pure HTTP GET, server sanitization, SSRF guard, no JS/bot bypass) and `websearch = execute_real_web_search_sync` (structured multi-tier search).
  - Completely eradicated legacy external proxy `r.jina.ai` across the codebase in favor of sovereign native fetch pipeline.
- **Verification Suites**:
  - `tests/test_rss_poller.py` + `tests/test_ddg_bot_detection_awareness.py` + `tests/test_websearch_searxng_fallback.py` + `tests/test_sovereign_search_cascade.py`: **18/18 passed (100%)**.
  - `tests/test_slice_1_5_web_search_and_stream_ttl.py` + `tests/test_p0_security_hardening.py`: **14/14 passed (100%)**.
  - Phase A1–A7 Verification Suite: **44/44 passed (100%)**.

---

## [v28.16.0] - 2026-10-16
### Added & Security Hardened — Phase A7: Hardened Native Web Retrieval Subsystem (Tầng 2 Safe Direct Web Fetch)
- **Tầng 2 Safe Direct Web Fetch & Verbatim Retrieval Subsystem (`core/security/ssrf_resolve_pin_guard.py`, `core/security/taint_tracking_warden.py`, `core/sanitizer/deterministic_web_sanitizer.py`, `tools/web_search.py`, `tests/test_phase_a7_hardened_web_retrieval.py`)**:
  - **Unified Single Fetch Pipeline (`SSRFResolveAndPinGuard.fetch_with_revalidation`)**:
    * Enforced `follow_redirects=False` at the HTTP client level and implemented per-hop redirect revalidation, defeating redirect-based SSRF into `127.0.0.1` and AWS/GCP/Azure instance metadata (`169.254.169.254`).
    * Defeated DNS rebinding and IPv4-mapped IPv6 evasion (`::ffff:127.0.0.1`), CGNAT networks (`100.64.0.0/10`), link-local/multicast, and rejected embedded URL userinfo credentials (`user:pass@host`).
    * Unified both canonical `fetch_url_content` (with backward-compatible alias `fetch_url_clean`) and DuckDuckGo direct HTML scraping under this single validated egress pipeline.
  - **TaintTrackingWarden Information-Flow Security Enforcement (`core/security/taint_tracking_warden.py`)**:
    * Created native 3-tier provenance tracking: `TRUSTED_SYSTEM`, `TRUSTED_MASTER`, and `UNTRUSTED_EXTERNAL`.
    * Tagged retrieved web content with cryptographic envelopes `[UNTRUSTED_WEB_CONTENT]` containing canonical SHA-256 hashes.
    * Hardened Policy Gate via `enforce_tool_sink_safety`, strictly blocking any tainted data from triggering privileged actuators (`terminal_exec`, `write_file`, `delete_file`) without Master authorization.
  - **Three-Layer DeterministicWebSanitizer (`core/sanitizer/deterministic_web_sanitizer.py`)**:
    * Layer 1: Stripped CSS-hidden DOM elements (`display:none`, `visibility:hidden`, `opacity:0`, `font-size:0`, `left:-9999px`, `aria-hidden="true"`), `<script>`, `<style>`, `<noscript>`, and HTML comments.
    * Layer 2: Sanitized invisible/bidi characters while strictly preserving linguistic formatting: Zero-Width Non-Joiner (ZWNJ `\u200c`), Zero-Width Joiner (ZWJ `\u200d`), composite emoji sequences (`👨‍👩‍👧‍👦`), and Unicode NFC accented Vietnamese text.
    * Layer 3: Neutralized LLM template delimiters (`<|im_start|>`, `[INST]`, `<<SYS>>`) and safely defused Base64-encoded prompt injection payloads (`[DEFUSED_ENCODED_PAYLOAD]`).
  - **Pure-Python BM25-CP VerbatimPassageSelector**:
    * Built an in-tree Okapi BM25 ranking algorithm with contiguous bigram (`1.5x`) and trigram (`2.0x`) boost without external dependencies.
    * Emitted exact `VerbatimPassage` records with character-level `char_start`, `char_end`, and deterministic SHA-256 checksums matching the sanitized text byte-for-byte.
  - **Comprehensive Verification Suite**: **5/5 passed (100%)** in `tests/test_phase_a7_hardened_web_retrieval.py` + **19/19 passed (100%)** in regression tests (`test_p0_security_hardening.py`, `test_two_agent_protocol_v23.py`).

---

## [v28.15.0] - 2026-10-16
### Added — Small-Model-Centric 5-Pillar Cognitive Architecture & Continuous Verified Learning Loop (Phases A0–A6)
- **Phase A6: Paraphrase & Bilingual Semantic Generalization + 6-Gate Weekly Autonomous Audit Runner (`core/os/cognition/weekly_autonomous_audit.py`, `data/eval/paraphrased_generalization_challenge.jsonl`, `tests/test_phase_a6_paraphrase_and_weekly_audit.py`)**:
  - Upgraded `DeterministicMathTool` (`core/os/cognition/verified_learning_loop.py`) with bilingual & paraphrase-resilient intent cues (`PCT_INTENT_CUES`, `THROUGHPUT_INTENT_CUES`, `MULTIPLICATION_INTENT_CUES`), directional operand ordering (`"từ X lên Y"` / `"from X to Y"` vs `"Y so với X"` / `"Y compared to X"`), and `.` / `,` thousand-separator normalization.
  - Upgraded `VerifiedMemoryStore.retrieve_for_task` (`core/os/cognition/verified_memory_store.py`) with `CONCEPT_SYNONYM_GROUPS` and `_extract_semantic_concepts(text)` so English and paraphrased Vietnamese queries retrieve the exact `top_k=1` verified memory entry without relying on surface word overlap.
  - Created `data/eval/paraphrased_generalization_challenge.jsonl` (`2,375 bytes`, pure LF, SHA-256: `8b89e49300f27ddc1e46547ae06384fc0bd701073f6a82bdb80d26a1c7b53829`) and added it to `EXAM_SUITES` in `VerifiedMemoryStore` (`0` 4-gram leak violations across all 4 exam suites).
  - Executed live GPU inference on **AMD Radeon RX 6600** (`qwen2.5-coder:3b`) across the 10-task Paraphrase & Bilingual Generalization suite: **9/10 passed (`Live TCR = 0.90`)**, combined across all 30 live tasks (`weekly_exam_B` 20 + `paraphrased_challenge` 10): **29/30 (`Combined TCR = 0.9667`)** (`data/telemetry/phase_a6_paraphrase_generalization_traces.jsonl`, `17,397 bytes`, pure LF, SHA-256: `c3a9ae5270c58de60e842dbb4786687c400646791869dc128468c9e7ae38f44f`).
  - Built `WeeklyAutonomousAuditRunner` evaluating 6 mandatory gates via `MissionCompletionGate`: **6/6 gates `COMPLETE`** (`data/telemetry/phase_a6_weekly_autonomous_audit_report.json`, `2,297 bytes`, SHA-256: `274ac56b3d44d76d026a07c9053d747fabe41a1df5e303f916de0fc95b2b20ba`).
- **Phase A5: Continuous Verified Learning Loop & Deterministic Math Tool Offloading (`core/os/cognition/verified_learning_loop.py`, `tests/test_phase_a5_verified_learning_loop.py`)**:
  - Implemented the 6-stage `VerifiedLearningLoop`: `observe_and_diagnose` → `synthesize_and_ingest_verified_lessons` (verified via `MissionCompletionGate.evaluate`) → `DeterministicMathTool` execution offloading → `verify_or_rollback_update` (enforcing zero regression on previously passed tasks).
  - Evolved `data/knowledge/verified_experience_store.jsonl` to **9 active records** (`10,860 bytes`, pure LF, SHA-256: `5790b62c33bd5f8bad6d504c03b18b8ed95543c298ba1fd4f803524f99c2645f`), adding `MEM_MATH_003` (percentage change rule).
  - Achieved **20/20 passed (`Live TCR = 1.00`, `+10%` over A4 `0.90`, `+55%` over A0 `0.45`, `0` regressions)** on live AMD Radeon RX 6600 (`qwen2.5-coder:3b`), avg latency `2.6534s`, active VRAM `4,939 MB <= 7,680 MB` (`data/telemetry/phase_a5_raw_inference_traces.jsonl`, `31,634 bytes`, pure LF, SHA-256: `0f494cf2691c8191472d498b42c14c052999ba1a62f0ea957b0b64587ce91133`).
- **Phase A4: Verified Memory Store & Domain-Specific Reasoning Guardrails (`core/os/cognition/verified_memory_store.py`, `tests/test_phase_a4_verified_memory_scaffolding.py`)**:
  - Built `VerifiedMemoryStore` enforcing 4-tier provenance (`RAW`, `HYPOTHESIS`, `VERIFIED`, `DEPRECATED`), 2-Door Anti-Leak Guard (`4-gram overlap < 0.40` against `weekly_exam_A`, `weekly_exam_B`, `sealed_C/sovereign_exam_tasks.json`), and selective `top_k=1` domain-scoped context injection (`<= 120 tokens`).
  - Improved live `qwen2.5-coder:3b` OOD Task Completion Rate from **11/20 (`0.55`) in Phase A3 to 18/20 (`0.90`) in Phase A4** (`+35%` net gain, `0` regressions) (`data/telemetry/phase_a4_raw_inference_traces.jsonl`, `30,089 bytes`, pure LF, SHA-256: `e3f14a0c32c86a59e064ca8fd979bb7488d8cc692978d4a0267806944bf0e9a5`).
- **Phase A1–A3: Full-Chain 5-Stage Telemetry, Adaptive Controller & 3-State Completion Authority (`core/os/cognition/full_chain_telemetry.py`, `core/os/cognition/adaptive_controller.py`, `tests/test_phase_a1_completion_and_telemetry.py`, `tests/test_phase_a2_adaptive_controller.py`, `tests/test_phase_a3_decision_lora_and_benchmark.py`)**:
  - Established end-to-end 5-stage telemetry (`Proposal → Controller → Execution → Verification → Outcome`) with deterministic failure attribution (`MODEL_REASONING_ERROR`, `CONTROLLER_STRATEGY_ERROR`, `EXECUTION_TOOL_ERROR`, `VERIFICATION_GATE_REJECTION`).
  - Built `AdaptiveController` (4 strategies: `DIRECT_REASONING`, `RETRIEVAL_FIRST`, `STEPWISE_VERIFIED`, `CLARIFY_OR_REFUSE_FIRST`) and `MissionCompletionGate` (`COMPLETE`, `INCOMPLETE`, `BLOCKED`), decoupling tool execution success from task completion and lifting OOD TCR from `0.45` (A0) to `0.55` (A3).
- **Full Regression Verification**: **219 passed, 1 skipped** across the entire Zenith Sprint & Hardening test suite (`72.21s`).

---

## [v28.14.0] - 2026-10-15
### Added & Security Hardened — SOTA 1–4 Architectural Upgrades & P0 Debt Closure
- **P0 Security Debt Closure (`DEBT-P0-01` & `DEBT-P0-02`)**:
  - Closed `DEBT-P0-01` (`core/security/mission_control_auth.py`): Enforced fail-closed token verification (`Bearer`, `X-Session-Token`, `Cookie`) and 100% recursive credential masking on `/api/connections`.
  - Closed `DEBT-P0-02` (`docker-compose.yml`): Eliminated full root `.:/workspace` bind-mounts across all 5 application services (`ai-control-plane`, `ai-brain`, `ai-worker`, `ai-executor`, `mission-control`), replacing them with least-privilege scoped subpath mounts (`:ro` code directories, `:rw` data/logs/telemetry, and tmpfs masks isolating `data/eval/sealed_C`).
- **SOTA 1–4 Sovereign Architecture Upgrades**:
  - **SOTA 1 (`core/governance/ab_shadow_harness.py`)**: Live GPU A/B Shadow Harness on AMD Radeon RX 6600 (`qwen2.5-coder:3b`) with hardware-enforced VRAM ceiling (`<= 7,680 MB`) and chained SHA-256 ledger (`data/telemetry/ab_shadow_ledger.jsonl`).
  - **SOTA 2 (`core/security/taint_tracking_warden.py`)**: Information-Flow Taint Tracking Engine (`TRUSTED_SYSTEM`, `TRUSTED_MASTER`, `UNTRUSTED_EXTERNAL`) blocking indirect prompt injection from external web/RAG payloads before reaching high-impact actuators.
  - **SOTA 3 (`core/os/sandbox/transactional_worktree.py`)**: Transactional Git Worktree Sandbox (`begin -> apply -> test -> commit | rollback`) guaranteeing zero dirty files in the main repository on test failure.
  - **SOTA 4 (`core/os/memory/bi_temporal_graph.py`)**: Bi-Temporal Knowledge Graph tracking transaction time (`t_created`, `t_expired`) and valid time (`t_valid_from`, `t_valid_to`) for deterministic point-in-time fact queries (`as_of`).

---

## [v28.13.0] - 2026-10-14
### Security & Architecture Hardening Campaign
- **Khép Lại Chiến Dịch Hardening P0, P1, P2 — Nghiệm Thu Xanh Toàn Diện Độc Lập Từ OpenCode (Lượt 342)**:
  - **P0 Bảo Mật Thực Chiến (6/6 Passed in 3.37s)**:
    * `P0.1`: Loại bỏ 100% hardcoded secrets (`AKAI_PRIME_SUPER_SECRET_999` gỡ hoàn toàn; static HMAC tokens trong `policy_snapshot.py`, `routing_manifest.py`, `rsil_orchestrator.py` chuyển thành dynamic entropy qua `secrets.token_bytes(32)`).
    * `P0.2`: Bịt kín `/execute` tại `services/ai-executor/main.py` và `services/ai_executor_service.py` với `verify_execution_grant()`. Mọi request thiếu grant hoặc giả mạo grant lập tức bị fail-closed (`denied=True`).
    * `P0.3`: Phủ toàn diện `validate_egress_url_ssrf_safe()` trên toàn bộ 3 endpoints của `ai-browser` (`/browse`, `/screenshot`, `/crawl`). Chặn đứng loopback, private IP, AWS/GCP metadata, Docker internal networks.
    * `P0.4`: Bắt buộc đồng bộ `should_allow_ingest_file()` trong `rag/ingest/ingest.py`, ngăn chặn RAG nuốt nhầm `sealed_C`, `.env`, `*.pem`, `credentials/`.
    * `P0.5`: Cưỡng chế `is_safe_contained_path()` tại `scripts/host_bridge.py`, ngăn chặn triệt để path traversal ra ngoài workspace.
    * `P0.6`: Triệt để gỡ bỏ toàn bộ 3 vị trí mount `/var/run/docker.sock` trong `docker-compose.yml` (`ai-control-plane`, `ai-worker`, `mission-control`). Kiểm thử tự động `test_condition_6_no_docker_socket_mounted_in_production_compose` ghim chặt trạng thái không chứa docker.sock.
  - **P1 Đấu Nối Kệ Chết (Wire-or-Delete) (5/5 Passed in 11.85s)**:
    * Đấu `Tier2ReflexGate` & Safety Veto vào hot-path `services/ai-brain/dispatcher.py`.
    * Đấu `SkillSunsetEngine` vào hot-path `services/ai-brain/dispatcher.py` (chặn gọi kỹ năng hết hạn).
    * Hiện thực hóa thẩm định chứng cứ thực tế tại `/review_execution` và `/distill_judicial` (`services/ai-brain/main.py`).
    * Khắc phục `route_to_judicial_review` trong `services/ai-control-plane/router.py` (fail-closed khi có lỗi, loại bỏ hoàn toàn PASS giả).
    * Đấu nối `episodic_brain.ingest_exemplar()` vào `_record_civilization_wisdom()` trong `task_manager.py`.
  - **P2 Real Mission Đo Lường Thực Tế (1/1 Passed in 58.89s)**:
    * Thực thi mission hoàn chỉnh từ PolicySnapshot $\to$ ExecutionGrant $\to$ ghi đĩa vật lý băm SHA-256 $\to$ EvidenceExecutionTrace (EET) E3 $\to$ CompletionAuthority $\to$ Judicial Review $\to$ CivilizationLedger & EpisodicBrain.
    * Wall-clock vật lý: 57,859ms. Tuyệt đối không mock echo.
  - **Sổ Nợ Tồn Kỹ Thuật Máy Đọc Được (`data/telemetry/debt_ledger.jsonl`)**:
    * Mở sổ theo dõi `DEBT-P0-01` (Auth & token masking trên mission-control endpoints) và `DEBT-P0-02` (Thay thế mount root `.:/workspace` bằng scoped subpath mounts). Hạn chót: Sprint tới.
  - **Khóa Mẫu Số Phương Trình Bảo Toàn Tệp**:
    * Duy trì duy nhất một mẫu số: $\text{INDEXED } (2597) + \text{EXCLUDED } (1546) + \text{SYNTAX ERRORS } (0) = \text{TOTAL } (4143)$.

---

## [v28.12.0] - 2026-10-14
### Added
- **Bước 6 Lộ Trình 6 Bước: Xóa Dứt Điểm 3 Hạng Mục NOT_TESTED Còn Lại — Đóng Sổ Minh Bạch & Hoàn Tất Trọn Vẹn Lộ Trình 1 Quý (Slice 6.6 Sovereign Closure of Lingering NOT_TESTED Contracts)**:
  - **Động Cơ Đóng Sổ Minh Bạch (`core/os/cognition/not_tested_closure_engine.py`)**:
    * **Mục 1 (Đo thật trần `num_predict` đủ dài $\ge 128$ tokens)**:
      - Kiểm chứng trực tiếp trên Live Ollama cổng 11434 (`qwen2.5-coder:3b` / `qwen3.5:4b`) với `test_ceiling_tokens = 128`.
      - Kết quả đo thật: `actual_eval_count = 128`, tốc độ $67.92\text{ tokens/s}$, dừng sạch sẽ `done = True`, `done_reason = "length"`.
      - Đóng dấu: **`TESTED_PASS`** (xóa bỏ giả định trần ngắn 64 tokens).
    * **Mục 2 (Kiểm định Production RAG trên các Collection thực tế của Qdrant)**:
      - Kết nối trực tiếp vào Live Qdrant cổng 6333, thẩm tra 3 collection production sống: `jkai_knowledge` ($11,611$ điểm), `jkai_skills` ($276$ điểm), `jkai_episodic_memory` ($100$ điểm).
      - Xác nhận $100\%$ collections đạt trạng thái `green`, thực thi truy vấn scroll/vector thực tế với độ trễ siêu tốc $5.36\text{ms} < 150\text{ms}$.
      - Đóng dấu: **`TESTED_PASS`** (xóa bỏ tình trạng chỉ đo trên collection tạm thời).
    * **Mục 3 (Thẩm định Vật lý Compute & Huấn Luyện LoRA Thật Minh Bạch)**:
      - Thẩm định phần cứng vật lý qua `torch.cuda.is_available() == False` và `hardware_pulse.json`.
      - Công bố trung thực môi trường máy chủ là `REAL_HOST_CPU` (Dual Intel Xeon E5-2699 v4 + 128GB RAM). Tuyệt đối KHÔNG bịa đặt hay làm giả số liệu GPU.
      - Chạy job PyTorch + PEFT LoRA SFT thật trên tập 50 Gold samples: loss giảm thực tế $1.6437 \to 1.6208$, lưu trọng số adapter, held-out score $0.2667$.
      - Đóng dấu: **`TESTED_PASS (Host CPU-only verified: torch.cuda.is_available()=False, live PyTorch+PEFT SFT completed, ZERO fake GPU claimed)`**.
  - **Sổ Cái Đóng Sổ Chủ Quyền Băm Chuỗi (`data/telemetry/sovereign_closure_ledger.jsonl`)**:
    * Xác nhận $3/3$ mục `TESTED_PASS`, $0$ mục `NOT_TESTED` còn sót lại, phán quyết: **`ALL_3_NOT_TESTED_SEALED`**.
    * Nối chuỗi mã băm SHA-256 bất biến khóa sổ toàn bộ chu trình 6 bước.
  - **Kiểm Thử Toàn Diện**: `tests/test_slice_6_6_close_lingering_not_tested.py` đạt **5/5 passed in 17.76s**. Toàn bộ Sprint Suite đạt **132 passed, 1 skipped in 48.42s** (0 warnings, 0 regressions). Phương trình bảo toàn tệp tin: $2381 + 216 + 0 = 2597$.
  - **Cột Mốc Lịch Sử**: Hoàn tất $6/6$ bước trong Lộ trình 1 Quý tập trung đo lường và học hỏi do Master phê duyệt!

---

## [v28.11.0] - 2026-10-14
### Added
- **Bước 5 Lộ Trình 6 Bước: Diễn Tập Phục Hồi Vận Hành & Khung Đo Lường Chỉ Số Thích Ứng (Slice 6.5 Operational Recovery Drills & Sovereign Adaptation Harness)**:
  - **Khung Diễn Tập Chọc Lỗi Thực Chiến (`core/os/cognition/recovery_drill_harness.py`)**:
    * 3 nhóm sự cố cố tình chọc lỗi:
      1. `TOOL_CRASH`: Tiến trình chết đột ngột (BrokenPipeError / ProcessLookupError) $\to$ Phục hồi tức thì qua Circuit Breaker Fallback Tool.
      2. `NETWORK_DROP`: Mạng rớt / timeout socket / từ chối kết nối $\to$ Tự động Backoff Retry và chuyển đổi mượt mà sang Offline Local Cache.
      3. `MALFORMED_FORMAT`: Upstream trả về JSON dị dạng, markdown fence, stream truncated $\to$ Tự phục hồi cấu trúc dữ liệu qua Self-Healing FastToolParser.
  - **Lấp Đầy Chỉ Số Thích Ứng (Adaptation Metric)**:
    * Chạy toàn bộ 15 kịch bản diễn tập thực chiến (5 kịch bản/kiểu sự cố).
    * Kết quả thực nghiệm vật lý: Tỷ lệ phục hồi $\text{Recovery Rate} = \mathbf{100.0\%} \ge \mathbf{90\%}$, độ trễ trung bình $\mathbf{0.16\text{ms}}$, chính thức đóng dấu `CRITERION_FULFILLED`.
    * Lấp đầy trọn vẹn ô trống duy nhất trong 10 Tiêu Chí Vận Hành Sovereign JKAI.
  - **Sổ Cái Băm Chuỗi SHA-256 (`data/telemetry/recovery_drill_ledger.jsonl`)**: Ghi nhận toàn bộ 15 ca diễn tập và 1 bản tổng kết thích ứng với liên kết chuỗi băm bất biến.
  - **Kiểm Thử Toàn Diện**: `tests/test_slice_6_5_recovery_drills_and_adaptation.py` đạt **5/5 passed in 1.30s**. Toàn bộ Sprint Suite đạt **127 passed, 1 skipped in 45.64s** (0 warnings, 0 regressions). Phương trình bảo toàn tệp tin: $2379 + 216 + 0 = 2595$.

---

## [v28.10.0] - 2026-10-14
### Added
- **Bước 4 Lộ Trình 6 Bước: Quản Lý Phiên Bản Kỹ Năng, Khung Kiểm Thử Hồi Quy & Động Cơ Sunset Hoàng Hôn (Slice 6.4 Skill Versioning, Regression Test Harness & Sunset Lifecycle Engine)**:
  - **Hợp Đồng Phiên Bản Kỹ Năng Chuẩn Hóa (`core/kernel/skill_lifecycle_engine.py`)**:
    * 4 trạng thái vòng đời nghiêm ngặt: `ACTIVE` $\to$ `DEPRECATED` $\to$ `SUNSET` $\to$ `ARCHIVED`.
    * Định dạng phiên bản ngữ nghĩa SemVer (`major.minor.patch`), thời hạn hỗ trợ `max_supported_days` (mặc định 90 ngày) và con trỏ kế nhiệm `superseded_by`.
    * `is_expired`: Tự động phát hiện kỹ năng quá hạn theo thời gian sống hoặc mốc `sunset_at`.
  - **Khung Kiểm Thử Hồi Quy Kỹ Năng Bắt Buộc (`SkillRegressionHarness`)**:
    * Khóa chặn mọi nâng cấp khi chưa có bài thi hồi quy (`ZERO_REGRESSION_TESTS_REGISTERED`).
    * Thực thi tập bài thi hồi quy đã đăng ký với các predicate nghiệm thu độc lập.
    * Nguyên tắc Hiến pháp: Tỷ lệ đạt phải là $100\%$ (`pass_rate == 1.0`). Bất kỳ test nào rớt lập tức kích hoạt phủ quyết nâng cấp (`REGRESSION_DETECTED`), bảo toàn phiên bản cũ an toàn.
  - **Động Cơ Sunset & Chống "Sự Thật Cũ" (`SkillSunsetEngine`)**:
    * `scan_and_sunset_expired_skills`: Tự động quét và hạ sát các kỹ năng quá hạn hoặc bị thay thế quá 30 ngày sang trạng thái `SUNSET`.
    * `can_invoke_skill`: Chặn đứng mọi hành vi gọi kỹ năng `SUNSET` (`SKILL_SUNSET_ERROR`), buộc chuyển đổi sang kỹ năng kế nhiệm, triệt tiêu nguy cơ "kỹ năng cũ thành sự thật cũ". Hỗ trợ cờ `allow_sunset=True` duy nhất cho kiểm toán lịch sử.
  - **Sổ Cái Băm Chuỗi SHA-256 (`data/telemetry/skill_lifecycle_ledger.jsonl`)**: Ghi nhận toàn bộ sự kiện đăng ký, nâng cấp, từ chối và sunset với liên kết chuỗi băm bất biến.
  - **Kiểm Thử Toàn Diện**: `tests/test_slice_6_4_skill_versioning_and_sunset.py` đạt **5/5 passed in 0.49s**. Toàn bộ Sprint Suite đạt **120 passed, 1 skipped in 39.98s** (0 warnings, 0 regressions). Phương trình bảo toàn tệp tin: $2376 + 216 + 0 = 2592$.

---

## [v28.9.0] - 2026-10-14
### Added
- **Bước 3 Lộ Trình 6 Bước: Hiệu Chuẩn Tầng 2 & Mở Khóa Cổng Phản Xạ Nhanh Có Kiểm Soát (Slice 6.3 Tier 2 Calibration Engine & Controlled Reflex Gate)**:
  - **Tập 200 Mẫu Gold Cân Bằng (`data/dataset/tier2_calibration_gold_200.jsonl`)**:
    * 5 nhóm tác vụ chuyên sâu (40 mẫu/nhóm): `FAST_TOOL_ROUTING`, `CODE_REASONING`, `BILINGUAL_EN_VI`, `SAFETY_REFUSAL`, `CONTEXT_ROUTING` ($n=200$).
    * 100% mẫu tuân thủ hợp đồng học tập 8 trường (`source`, `sample_count`, `created_at`, `expires_at`, `freshness_policy`, `benchmark_id`, `compute_budget`, `approval_tier`).
    * 0/200 mẫu rò rỉ N-gram thi (overlap $< 0.40$ so với kho Đề thi tuần A, B, C).
  - **Bộ Đo ECE Phân Vùng & Hiệu Chuẩn Nhiệt Độ (`core/os/cognition/tier2_calibration_gate.py`)**:
    * `compute_ece`: Thuật toán binned ECE ($M=10$ bins) đo lường chính xác khoảng cách giữa độ tin cậy mô hình và độ chính xác thực nghiệm.
    * `TemperatureCalibrator`: Tối ưu hóa nhiệt độ $T$ trên tập Calib (160 mẫu), kiểm định độc lập trên tập Held-out (40 mẫu, 8 mẫu/nhóm).
    * Kết quả thực nghiệm: $\text{ECE}_{\text{held\_out}} = 0.1083 \le 0.15$, độ chính xác $\text{Accuracy}_{\text{held\_out}} = 92.5\% \ge 80\%$, $T = 0.6$.
  - **Cổng Phản Xạ Nhanh Có Kiểm Soát (`Tier2ReflexGate`)**:
    * Fast-Path Reflex Routing: Mở khóa phản xạ siêu tốc ($< 50\text{ms}$) cho các truy vấn an toàn có độ tin cậy hiệu chuẩn $p_{\text{cal}} \ge 0.85$.
    * Safety Veto: Phủ quyết $100\%$ các chỉ dẫn độc hại/tiêm nhiễm/phá hoại, khóa cứng phản xạ và chuyển hướng sang bộ xử lý từ chối an toàn.
    * Fail-closed: Tự động khóa phản xạ về Deliberative Tier 3 khi mô hình chưa được hiệu chuẩn hoặc độ tin cậy thấp.
  - **Sổ Cái Băm Chuỗi SHA-256 (`data/telemetry/tier2_calibration_ledger.jsonl`)**: Ghi nhận toàn bộ sự kiện hiệu chuẩn và mở khóa reflex với liên kết chuỗi băm bất biến.
  - **Kiểm Thử Toàn Diện**: `tests/test_slice_6_3_tier2_calibration.py` đạt **5/5 passed in 1.22s**. Toàn bộ Sprint Suite đạt **115 passed, 1 skipped in 39.75s** (0 warnings, 0 regressions). Phương trình bảo toàn tệp tin: $2371 + 216 + 0 = 2587$.

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
