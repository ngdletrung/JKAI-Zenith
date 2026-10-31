# 🏛️ JKAI Zenith: Microkernel-Inspired Decision-Native Sovereign AI OS

[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen?style=for-the-badge&logo=github)](https://github.com/ngdletrung/JKAI-Zenith.git)
[![Version](https://img.shields.io/badge/Version-v28.19.0-blue?style=for-the-badge)](https://github.com/ngdletrung/JKAI-Zenith.git)
[![Architecture](https://img.shields.io/badge/Architecture-5--Pillar_Small--Model_Centric-indigo?style=for-the-badge)](https://github.com/ngdletrung/JKAI-Zenith.git)
[![Security](https://img.shields.io/badge/Security-Zero--Egress_Sovereign-red?style=for-the-badge)](https://github.com/ngdletrung/JKAI-Zenith.git)
[![Hardware](https://img.shields.io/badge/Hardware-RX6600_8GB_%2B_Xeon_128GB-purple?style=for-the-badge)](https://github.com/ngdletrung/JKAI-Zenith.git)
[![Test Suite](https://img.shields.io/badge/Tests-245_Passing-success?style=for-the-badge)](https://github.com/ngdletrung/JKAI-Zenith.git)
[![Live OOD TCR](https://img.shields.io/badge/Live_OOD_TCR-29%2F30_(96.7%25)-success?style=for-the-badge)](https://github.com/ngdletrung/JKAI-Zenith.git)

> **JKAI Zenith** is an enterprise-grade, microkernel-inspired **Decision-Native Sovereign AI Operating System**.  
> Designed for long-horizon mission autonomy, mathematical determinism, and zero-trust reliability under constrained local hardware, using a **Small Language Model (`qwen2.5-coder:3b`) as the central reasoning core** reinforced by an adaptive cognitive scaffolding and a continuous verified learning loop.

---

## 🧭 Executive Summary & Core Architectural Paradigm

JKAI Zenith represents a fundamental architectural evolution: transitioning from an *"AI OS with external governance"* to a **"Decision-Native Sovereign AI OS"**. 

Unlike conventional agentic frameworks that delegate entire execution chains to stochastic large language models (LLMs), JKAI Zenith enforces a strict, mathematically verifiable **Separation of Powers**:

```text
                                  JKAI ZENITH ARCHITECTURE
                                  
  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │                                    OPERATOR / MISSION                                  │
  └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                              │ Mission Intent (Natural Language / Telegram)
                                              ▼
  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │                            DETERMINISTIC KERNEL SPACE (Ring 0)                         │
  │  • Zero-Trust Gate 0 Invariants             • Pure Finite State Machine (FSM)          │
  │  • 8-Link Identity Traceability Chain       • Closed-Loop Physical Verifier (L1-L4)    │
  │  • Dual-Stage Action Firewall (Gate 1 & 2)  • Token Budget Guard & Instant-Fail Guard  │
  │  • State Sanitizer 2.3a (64KB Cap & SHA256) • Action Circuit Breaker & Safety Killswitch│
  │  • Shadow Harness 2-Phase Telemetry Recorder (100% Paired State-Draft-Receipt Triples) │
  └───────────────────────────────┬───────────────────────────────▲────────────────────────┘
                                  │ Propose Action / Verify       │ Authorize & Enforce
                                  ▼                               │
  ┌───────────────────────────────────────────────────────────────┴────────────────────────┐
  │                   COGNITIVE BUS & REFLEX DECISION SUBSTRATE (System 1)                 │
  │  • Tri-Tier Decision Adapter:                                                          │
  │     - Tier 1: Local Reflex Substrate (Non-Autoregressive Classifier, In Calibration)   │
  │     - Tier 2: Pluggable Local Reasoner (`Tier2Backend`: Local Ollama / Sovereign Reflex)│
  │     - Tier 3: Deterministic Rule Baseline (100% In-Process Regex & Logic Safe-Abstain) │
  │  • Decision Primitives: BOOLEAN, CHOICE, SCORE (Normalized Probability Dist $\sum=1.0$)│
  │  • Calibrated Confidence Scoring & Fast-Path Verification Routing                      │
  │  • Invariant: "Decision ≠ Authority" (Advisory Only, Zero Authority over Kernel)      │
  └───────────────────────────────┬────────────────────────────────────────────────────────┘
                                  │ Capability Invocation
                                  ▼
  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │                          CAPABILITY BROKER & USER SPACE (Ring 3)                       │
  │  • Google Drive & Office Suite   • MikroTik Router & Firewall  • MariaDB & PostgreSQL  │
  │  • Web Recon & Threat Intel      • SMTP Executive Mail Alert   • Telegram Bot Service  │
  └───────────────────────────────┬────────────────────────────────────────────────────────┘
                                  │ Hardware Execution
                                  ▼
  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │                         SOVEREIGN HARDWARE AFFINITY RUNTIME                            │
  │  • AMD Radeon RX 6600 (8GB VRAM ROCm / Vulkan) • Dual Intel Xeon E5-2699 v4 (128GB RAM)│
  │  • Default-Deny Egress with Scoped Audit (JKAI_LOCAL_ONLY=1 Killswitch)             │
  └────────────────────────────────────────────────────────────────────────────────────────┘
```

### The Five Pillars of Small-Model-Centric Intelligence (Năm Trụ Cột Năng Lực)

JKAI Zenith empowers a small local model (`qwen2.5-coder:3b`) to solve complex, novel, multi-step tasks without inflating model weights, governed by **Five Core Capability Pillars** ([`docs/JKAI_ZENITH_OBJECTIVES_AND_DIRECTION.md`](file:///d:/Docker/JKAI/docs/JKAI_ZENITH_OBJECTIVES_AND_DIRECTION.md)):

```text
                       JKAI-ZENITH SMALL-MODEL-CENTRIC ARCHITECTURE
                                             │
     ┌───────────────────┬───────────────────┼───────────────────┬───────────────────┐
     ▼                   ▼                   ▼                   ▼                   ▼
1. SMALL MODEL     2. VERIFIED MEMORY   3. ADAPTIVE CTRL   4. VERIFICATION &   5. VERIFIED
REASONING CORE      & EXTERNAL KNOWL.    & OS RUNTIME       COMPLETION GATE    LEARNING LOOP
     │                   │                   │                   │                   │
qwen2.5-coder:3b    4-Tier Provenance   4 Dynamic Strat.   3-State Authority   6-Stage Closed Loop
Proposal & Plan     Bilingual Concept   Deterministic      COMPLETE /          Observe -> Diagnose
Boundary Aware      2-Door Anti-Leak    Math Offloading    INCOMPLETE /        -> Verify -> Gate
                    (<0.40 4-gram)      (Exact Arithmetic) BLOCKED             6-Gate Weekly Audit
```

1. **Pillar 1 — Small Model Reasoning Core**: Local `qwen2.5-coder:3b` serves as the central language understanding, hypothesis generation, and planning engine. It recognizes its own epistemic boundaries and requests clarification or tool offloading rather than hallucinating.
2. **Pillar 2 — External Knowledge & Verified Memory Store (`core/os/cognition/verified_memory_store.py`)**: Selective, deduplicated memory governed by 4-tier provenance (`RAW`, `HYPOTHESIS`, `VERIFIED`, `DEPRECATED`), Bilingual Concept Synonym Normalization (`CONCEPT_SYNONYM_GROUPS`), and a strict 2-Door Anti-Leak Guard (`4-gram overlap < 0.40` across all 4 exam suites). Only `VERIFIED` entries (`top_k=1`, `<= 120 tokens`) are injected into model context.
3. **Pillar 3 — Adaptive Controller & Runtime (`core/os/cognition/adaptive_controller.py`)**: Dynamically routes tasks across 4 context-aware strategies (`DIRECT_REASONING`, `RETRIEVAL_FIRST`, `STEPWISE_VERIFIED`, `CLARIFY_OR_REFUSE_FIRST`) and offloads exact multi-digit arithmetic, percentage changes, and throughput ratios to `DeterministicMathTool`.
4. **Pillar 4 — Verification & 3-State Completion Authority (`MissionCompletionGate`)**: Strictly decouples tool execution success from task completion. Every task is evaluated against physical evidence into one of 3 states: `COMPLETE`, `INCOMPLETE`, or `BLOCKED`, traced end-to-end across 5 stages (`Proposal → Controller → Execution → Verification → Outcome`).
5. **Pillar 5 — Continuous Verified Learning Loop (`core/os/cognition/verified_learning_loop.py` & `weekly_autonomous_audit.py`)**: Closed-loop empirical improvement (`Observe → Diagnose → Verify Lesson → Select Improvement → Independent Eval → Promote or Rollback`) audited by the **6-Gate Weekly Autonomous Audit Runner**.

---

## 🏛️ Constitutional Invariants & Core Laws

JKAI Zenith is anchored upon non-negotiable operational laws enforced at compile-time and runtime:

### 1. The JKAI Mission Law
> **"MISSION IS INVARIANT. ONLY STRATEGY ADAPTS."**  
> Under environmental uncertainty or tool failure, strategies adapt dynamically (Plan A $\rightarrow$ Plan B), while mission objectives, security boundaries, and success invariants remain 100% immutable (Goal Conservation Rate = 100%).

### 2. Decision ≠ Authority Principle
> **"Reflex Engines Propose. The Deterministic Kernel Commands."**  
> Fast-path System 1 reflex engines produce decision primitives (`BOOLEAN`, `CHOICE`, `SCORE`) with calibrated confidence. However, they hold **zero operational authority**. Every proposed decision must be cryptographically traced, sanitized, and authorized by the Deterministic Kernel before execution.

### 3. The Two Absolute Invariants (2 NEVER)
1. **NEVER System 1 in FSM**: Finite State Machine state transitions are strictly deterministic. No probabilistic model can trigger, alter, or synthesize state transitions.
2. **NEVER System 1 in Policy Gate**: Access control, security boundaries, and action authorization through the Dual-Stage Action Firewall are 100% deterministic and zero-trust.

### 4. Default-Deny Egress with Scoped Audit & Sovereign External Actuation Gate
- Hardened by the `SOVEREIGN-NO-CLOUD-KILLSWITCH` (`JKAI_LOCAL_ONLY=1`) as an immutable baseline (Default-Deny).
- Completely rejects unsolicited external commercial cloud APIs, preventing proprietary telemetry leakage, vendor lock-in, and unpredictable latency.
- Full cognitive stack operates strictly on local hardware (Dual Xeon E5-2699 v4 + AMD RX 6600).
- **Scoped External Actuation & Sovereign Consultation Boundary**: External network actuation (e.g., visual web browsing, search engines, or multi-agent consultation) is exclusively activated upon explicit, intentional Master command (`master_cli`, `master_ui`, `master_voice`). It operates under dual-killswitch control (`JKAI_DISCUSS_ALLOWED=1` scoped to execution lifecycle), pre-send sanitization (scrubbing internal paths, IPs, and keys), zero organizational metadata exposure, reverse solicitation defense, active context mosaic defense, and chained cryptographic egress logging.

---

## 🛡️ Key Architectural Subsystems

### A. Small-Model Cognitive Scaffolding & Verified Learning (`core/os/cognition/`)
- **Full-Chain 5-Stage Telemetry** ([`full_chain_telemetry.py`](file:///d:/Docker/JKAI/core/os/cognition/full_chain_telemetry.py)): Tracks every task across `Proposal → Controller → Execution → Verification → Outcome` with deterministic root-cause classification (`MODEL_REASONING_ERROR`, `CONTROLLER_STRATEGY_ERROR`, `EXECUTION_TOOL_ERROR`, `VERIFICATION_GATE_REJECTION`).
- **Adaptive Controller & 3-State Completion Gate** ([`adaptive_controller.py`](file:///d:/Docker/JKAI/core/os/cognition/adaptive_controller.py)): Selects optimal execution strategy and enforces `MissionCompletionGate` (`COMPLETE`, `INCOMPLETE`, `BLOCKED`).
- **Verified Memory Store** ([`verified_memory_store.py`](file:///d:/Docker/JKAI/core/os/cognition/verified_memory_store.py)): Manages `data/knowledge/verified_experience_store.jsonl` with bilingual concept normalization and 2-door exam anti-leak verification.
- **Continuous Verified Learning Loop & Deterministic Math Tool** ([`verified_learning_loop.py`](file:///d:/Docker/JKAI/core/os/cognition/verified_learning_loop.py)): Synthesizes verified failure lessons, offloads exact arithmetic (`PERCENTAGE_CHANGE`, `TOKEN_THROUGHPUT`, `UNIT_MULTIPLICATION`), and enforces zero-regression rollback.
- **6-Gate Weekly Autonomous Audit Runner** ([`weekly_autonomous_audit.py`](file:///d:/Docker/JKAI/core/os/cognition/weekly_autonomous_audit.py)): Evaluates all 6 constitutional gates (OOD TCR $\ge 0.95$, Paraphrase Generalization TCR $\ge 0.85$, Zero Anti-Leak, Hardware VRAM $\le 7,680\text{ MB}$ & Latency $\le 15\text{s}$, Zero Regression, and Pure LF + SHA-256 Parity).

### B. SOTA 1–4 Sovereign Governance, Security & Memory (`core/governance/`, `core/security/`, `core/os/`)
- **SOTA 1 — Live GPU A/B Shadow Harness** ([`ab_shadow_harness.py`](file:///d:/Docker/JKAI/core/governance/ab_shadow_harness.py)): Runs paired baseline vs. candidate inference on AMD Radeon RX 6600 within the $7,680\text{ MB}$ VRAM ceiling.
- **SOTA 2 — Information-Flow Taint Tracking Warden** ([`taint_tracking_warden.py`](file:///d:/Docker/JKAI/core/security/taint_tracking_warden.py)): Tags data provenance (`TRUSTED_SYSTEM`, `TRUSTED_MASTER`, `UNTRUSTED_EXTERNAL`) and blocks indirect prompt injection from triggering privileged tools.
- **SOTA 3 — Transactional Git Worktree Sandbox** ([`transactional_worktree.py`](file:///d:/Docker/JKAI/core/os/sandbox/transactional_worktree.py)): Isolates autonomous code mutations in ephemeral worktrees with automatic rollback on test failure.
- **SOTA 4 — Bi-Temporal Knowledge Graph** ([`bi_temporal_graph.py`](file:///d:/Docker/JKAI/core/os/memory/bi_temporal_graph.py)): Tracks transaction time (`t_created`, `t_expired`) and valid time (`t_valid_from`, `t_valid_to`) for deterministic point-in-time queries.

### C. Tri-Tier Decision Adapter (`core/cognitive_bus/`)
Provides resilient, tiered intelligence for routing, fast-path verification, and risk assessment:
- **Tier 1 (Local Reflex Substrate)**: Non-autoregressive neural classification ($< 5\text{ms}$ target).
- **Tier 2 (Pluggable Local Reasoner & Calibrated Reflex Gate)**: Standardized `Tier2Backend` protocol ([ADR 0001](file:///d:/Docker/JKAI/docs/adr/0001-tier2-backend-interface.md)) paired with `Tier2ReflexGate` ([`tier2_calibration_gate.py`](file:///d:/Docker/JKAI/core/os/cognition/tier2_calibration_gate.py), held-out $\text{ECE} = 0.1083 \le 0.15$, 100% Safety Veto).
- **Tier 3 (Deterministic Rule Fallback)**: In-process deterministic regex & keyword fail-safe ($0.13\text{ms}$ P95 latency).

### D. State Sanitizer 2.3a (`core/sanitizer/`), Token Budget Guard (`core/guard/`) & Verification Graph (`core/verification/`)
- **State Sanitizer 2.3a**: Strict $64\text{KB}$ upper bound, canonical JSON SHA-256 fingerprinting, and automated secret redaction (`core/security/mission_control_auth.py`).
- **TokenBudgetGuard & H-Triad (H1/H2/H3)**: Hard token ceiling, fast-path read-only bypass, authentic model provenance, and instant-fail exclusion.
- **Layered Verification Graph (L1–L4)**: Structural (Pydantic v2), Environmental (locks/resources), Semantic (goal alignment), and Physical (exit codes, AST syntax, SHA-256 checksums).

### E. Embodied Physical Runtime Subsystems (M0–M2) (`intelligence/skills/DEVOPS/` & `services/ai-browser/`)
- **M0 File Actuators & Code Sensors** ([`logic.py`](file:///d:/Docker/JKAI/intelligence/skills/DEVOPS/SYSTEM_CORE_EXECUTOR/logic.py)): Atomic write via temporary file commit, automatic `.bak.<timestamp>` generation, physical SHA-256 integrity verification, and AST syntax pre-validation (**8/8 unit tests pass**).
- **M1 Command Execution Sandbox** ([`logic.py`](file:///d:/Docker/JKAI/intelligence/skills/DEVOPS/SYSTEM_CORE_EXECUTOR/logic.py)): Isolated OS process execution with 4-tier Policy Gate, ExecutionGrant cryptographic verification (`core/kernel/policy_snapshot.py`), CWD jailing, and 16KB output cap (**9/9 unit tests pass**).
- **M2 Browser Sensor & Actuator** ([`services/ai-browser/`](file:///d:/Docker/JKAI/services/ai-browser/)): Autonomous visual microservice on port `8003:8000` protected by `SSRFGuard` (`validate_egress_url_ssrf_safe`), powered by CloakBrowser Stealth Engine v2.0 and Crawl4AI (**4/4 unit tests pass**).

### F. Hardened Native Web Retrieval Subsystem (Phase A7) (`core/security/`, `core/sanitizer/`, `tools/web_search.py`)
- **Single Egress Pipeline & SSRF Revalidation** ([`ssrf_resolve_pin_guard.py`](file:///d:/Docker/JKAI/core/security/ssrf_resolve_pin_guard.py)): Enforces `follow_redirects=False` at the transport layer, re-resolves and validates DNS at every redirect hop, blocks loopback/metadata/CGNAT/IPv4-mapped IPv6, and unifies `fetch_url_content` and DuckDuckGo HTML queries.
- **TaintTrackingWarden Information-Flow Gate** ([`taint_tracking_warden.py`](file:///d:/Docker/JKAI/core/security/taint_tracking_warden.py)): Enforces 3-tier provenance (`TRUSTED_SYSTEM`, `TRUSTED_MASTER`, `UNTRUSTED_EXTERNAL`), wrapping external web payloads in `[UNTRUSTED_WEB_CONTENT]` envelopes and failing closed on privileged tool sink access (`terminal_exec`, `write_file`).
- **Three-Layer DeterministicWebSanitizer** ([`deterministic_web_sanitizer.py`](file:///d:/Docker/JKAI/core/sanitizer/deterministic_web_sanitizer.py)): Strips CSS-hidden elements (`display:none`, `visibility:hidden`, `opacity:0`, `font-size:0`, offscreen coordinates), neutralizes LLM delimiters and defuses base64 prompt injection attacks while strictly preserving ZWNJ (`\u200c`), ZWJ (`\u200d`), composite emoji sequences, and Unicode NFC Vietnamese diacritics.
- **Pure-Python BM25-CP VerbatimPassageSelector**: In-tree Okapi BM25 ranking with phrase boosts (1.5x bigram, 2.0x trigram) that extracts exact verbatim text slices with character bounds (`char_start`, `char_end`) and SHA-256 hashes (**5/5 unit tests pass**).

### G. Multi-Agent Cloud Discussion Subsystem & Dynamic Model Resolver (v28.19.0) (`core/security/`, `core/os/cognition/`, `core/os/orchestrator/handlers/`)
- **Deterministic Trigger Parsing & Source Isolation** ([`trigger_parser.py`](file:///d:/Docker/JKAI/core/security/trigger_parser.py)): Strips Vietnamese diacritics via Unicode NFKD, rejects negation commands, and enforces strict source isolation from `master_cli`, `master_ui`, or `master_voice` (blocking indirect injection from files/web).
- **Dual-Killswitch Egress Gate & Hardened Scrubber** ([`egress_gate.py`](file:///d:/Docker/JKAI/core/security/egress_gate.py)): Enforces `JKAI_LOCAL_ONLY=1` baseline, requiring scoped `JKAI_DISCUSS_ALLOWED=1` and sanitizing local paths (`D:/Docker/JKAI`), internal IPs, API keys, and citizen IDs before egress.
- **Data Leak Guard & Virtual Canary Token** ([`data_leak_guard.py`](file:///d:/Docker/JKAI/core/security/data_leak_guard.py), [`canary_guard.py`](file:///d:/Docker/JKAI/core/security/canary_guard.py), [`context_canary.py`](file:///d:/Docker/JKAI/core/security/context_canary.py)): Hard blocks reverse solicitation probes for source code/keys with CRITICAL `MasterSecurityAlert`, deploys in-memory virtual canaries without git conflicts, and deploys 100% rule-based Active Context Canary preventing cumulative mosaic leaks.
- **Neutral Technical Role Contract & Delphi Protocol** ([`role_contract.py`](file:///d:/Docker/JKAI/core/security/role_contract.py), [`delphi_protocol.py`](file:///d:/Docker/JKAI/core/security/delphi_protocol.py)): Eliminates organization/Master identity metadata, enforces structured schemas (`FACT`, `INFERENCE`, `HYPOTHESIS`, `UNKNOWN`), and tracks claim-level consensus with 5 states (`VERIFIED`, `AGREED_UNVERIFIED`, `CONFLICTED`, `INSUFFICIENT_EVIDENCE`, `REJECTED`) where unverified agreement is never auto-verified.
- **Universal Dynamic Model Resolver & Fallback Cascade** ([`dynamic_model_resolver.py`](file:///d:/Docker/JKAI/core/security/dynamic_model_resolver.py)): Resolves model aliases (`latest-flash`, `latest-mini`, `latest-reasoner`, `AUTO_LATEST`) with semantic version sorting (`3.8 > 2.5 > 1.5`) across Gemini, OpenAI, DeepSeek, and Grok, handling 404 deprecations and 503 high-load spikes gracefully (**21/21 unit tests pass**).

---

## 📊 Empirical Benchmarks & Production Validation

JKAI Zenith has been empirically benchmarked and audited on live local hardware (**AMD Radeon RX 6600 8GB VRAM + Dual Intel Xeon E5-2699 v4 128GB ECC RAM**):

### 1. Small-Model Cognitive Progression on Live AMD Radeon RX 6600 (`qwen2.5-coder:3b`)

| Evolutionary Phase | Architectural Capability Added | Benchmark Suite | Live TCR | Avg Latency | Active VRAM | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Phase A0 (Baseline)** | Raw `qwen2.5-coder:3b` without cognitive scaffolding | `weekly_exam_A` (20 tasks) | **9/20 (45.0%)** | `3.48s` | `4,939 MB` | 🟢 **SEALED** |
| **Phase A1–A3** | 5-Stage Telemetry + `AdaptiveController` + `MissionCompletionGate` | `weekly_exam_B` (20 OOD tasks) | **11/20 (55.0%)** | `1.39s` | `4,939 MB` | 🟢 **SEALED** |
| **Phase A4** | `VerifiedMemoryStore` (`top_k=1` Verified Rules, 2-Door Anti-Leak) | `weekly_exam_B` (20 OOD tasks) | **18/20 (90.0%)** | `2.65s` | `4,939 MB` | 🟢 **SEALED** |
| **Phase A5** | `VerifiedLearningLoop` + `DeterministicMathTool` Offloading | `weekly_exam_B` (20 OOD tasks) | **20/20 (100.0%)** | `2.65s` | `4,939 MB` | 🟢 **SEALED** |
| **Phase A6 (Bilingual OOD)** | Paraphrase & Bilingual Generalization + 6-Gate Weekly Audit | `paraphrased_challenge` (10 tasks) | **9/10 (90.0%)** | `2.83s` | `4,939 MB` | 🟢 **SEALED** |
| **Combined A5 + A6** | Full 5-Pillar Small-Model-Centric Architecture | **30 Held-Out Live Tasks** | **29/30 (96.67%)** | `2.71s` | `4,939 MB` | 🟢 **SEALED** |

### 2. Core OS, Security & Subsystem Audit Matrix

| Benchmark / Audit Suite | Target Capability | Metric / Objective | Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **6-Gate Weekly Autonomous Audit** | OOD TCR, Paraphrase TCR, Anti-Leak, Hardware, Zero-Reg, SHA-256 | 6 Mandatory Constitutional Gates | **6/6 Gates COMPLETE** | 🟢 **SEALED** |
| **P0/P1/P2 Security & Wire-Up** | Zero Hardcoded Secrets, ExecutionGrant, SSRF, Scoped Mounts | Full Exploit & Regression Suite | **100.0% Pass (0 Debt)** | 🟢 **SEALED** |
| **SOTA 1–4 Architecture Suite** | GPU A/B Harness, Taint Tracking, Git Worktree, Bi-Temporal Graph | 20 Dedicated SOTA Verification Tests | **20/20 Passing (100%)** | 🟢 **SEALED** |
| **Tier 2 Calibration & Reflex Gate** | 200 Gold Samples, Temperature Scaling ($T=0.6$), Safety Veto | Held-out $\text{ECE} \le 0.15$, Acc $\ge 80\%$ | **ECE 0.1083 / Acc 92.5%** | 🟢 **SEALED** |
| **Operational Recovery Drills** | Tool Crash, Network Drop, Malformed JSON Self-Healing | 15 Adversarial Recovery Drills | **15/15 (100%) in 0.16ms** | 🟢 **SEALED** |
| **Embodied Runtime (M0+M1+M2)** | File Primitives, Command Sandbox, Browser Actuator | 21 Real Unit & Integration Tests | **21/21 Passing (100%)** | 🟢 **SEALED** |
| **Complete System Sprint Suite** | Total Architectural, Cognitive, Security & Embodied Tests | Full Repository Pytest Verification | **219 Passed, 1 Skipped** | 🟢 **SEALED** |

### Validated Physical Envelope (Master Host)
- **Host Hardware**: Dual Intel Xeon E5-2699 v4 (44 threads), 128GB ECC RAM.
- **Accelerator**: AMD Radeon RX 6600 (8GB GDDR6 VRAM; active inference allocation `4,939 MB <= 7,680 MB` hard ceiling).
- **Latency Profile**: Tier 3 Deterministic Rule P95 = **0.13 ms**; Recovery Drill Mean = **0.16 ms**; Qdrant Production Vector Scroll = **5.36 ms**; Live `qwen2.5-coder:3b` Mission Latency Mean = **2.65 s**.

---

## 📁 Repository Directory Structure

```text
JKAI-Zenith/
├── core/                         # Ring 0: Deterministic Microkernel & Cognitive Scaffolding
│   ├── contracts/                # Identity Chain (8-Link) & Cognitive Contracts
│   ├── governance/               # Zero-Trust Gate 0, Shadow Harness & Live GPU A/B Harness (SOTA 1)
│   ├── cognitive/                # World Model & Reconstructive State Store
│   ├── cognitive_bus/            # Tri-Tier Decision Adapter & Reflex Substrate
│   ├── kernel/                   # PolicySnapshot, ExecutionGrant & Skill Lifecycle / Sunset Engine
│   ├── os/                       # Sovereign OS Subsystems:
│   │   ├── cognition/            # 5-Pillar Core: FullChainTracer, AdaptiveController, VerifiedMemoryStore,
│   │   │                         #   VerifiedLearningLoop, DeterministicMathTool, WeeklyAutonomousAuditRunner
│   │   ├── memory/               # Bi-Temporal Knowledge Graph (SOTA 4) & Episodic Memory
│   │   └── sandbox/              # Transactional Git Worktree Sandbox (SOTA 3)
│   ├── sanitizer/                # State Sanitizer 2.3a (64KB Cap & Canonical JSON)
│   ├── guard/                    # Token Budget Guard & Instant-Fail Exclusion
│   ├── routing/                  # Deterministic Controller & Fast-Path Policy Router
│   ├── planning/                 # Meta-Planner & Async TaskGraph Engine
│   ├── security/                 # Dual-Stage Firewall, TaintTrackingWarden (SOTA 2) & MissionControlAuth
│   ├── recovery/                 # Error Classification & Self-Healing Replanner
│   └── verification/             # Layered Verification Graph (L1-L4) & Physical Verifier
├── data/                         # Sovereign Data & Immutable Ledgers
│   ├── eval/                     # Exam Suites (weekly_exam_A, weekly_exam_B, paraphrased_challenge, sealed_C)
│   ├── knowledge/                # Verified Experience Store (verified_experience_store.jsonl)
│   └── telemetry/                # Chained SHA-256 Ledgers & Raw Live GPU Inference Traces (Phases A0–A6)
├── intelligence/                 # Ring 3: User Space Capabilities, Identity & Skills
│   ├── identity/                 # GLOBAL_SYSTEM_CONTEXT.md (Chronological Cognitive Memory Log)
│   ├── capabilities/             # Drive, Office, MikroTik, MariaDB, Postgres, SMTP
│   └── skills/                   # 139 Versioned Physical Skills + DEVOPS / SYSTEM_CORE_EXECUTOR (M0 & M1)
├── services/                     # Autonomous Microservices & Gateways (Scoped Subpath Mounts)
│   ├── ai-brain/                 # Cognitive Planner & Critic, Reasoning Engine (Port 8001)
│   ├── ai-browser/               # Visual Satellite — CloakBrowser v2 + Crawl4AI + SSRFGuard (Port 8003)
│   ├── ai-control-plane/         # Task Board, GPU Scheduler & Worker Orchestration (Port 7000)
│   ├── ai-executor/              # Grant-Verified Physical Execution Engine (Ports 8002, 8007)
│   ├── ai-telegram/              # Resilient Telegram Bot Gateway with HTTPAdapter retry
│   └── mission-control/          # Authenticated Live Mission Control Web Dashboard (Port 9999)
├── docs/                         # IEEE/ISO 42010 Architecture Specs, Objectives & ADRs (ADR 0001-0006)
└── tests/                        # Comprehensive Verification Suite (219 Passed, 1 Skipped)
```

---

## 🚀 Strategic Development Roadmap

```text
  Phase 1–2: Deterministic Microkernel, Neural Reflex Engine & Embodied Runtime (M0–M2)
  [==================================================] 100% SEALED & OPERATIONAL
  • FSM & Zero-Trust Gate 0 Invariants, State Sanitizer 2.3a & Token Budget Guard
  • Pluggable Tier 2 Backend Protocol & Embodied Runtime Actuators M0, M1, M2 (21/21 Pass)

  Phase 3–4: Asynchronous Shadow Evaluation & RSIL-L3 Dual-Key Promotion Loop
  [==================================================] 100% COMPLETED
  • RSIL-L3 Core Orchestrator, Tier 1/2 Autonomous Loops & Tier 3 Master Handshake Gate
  • 3-Fold Golden Vault, 10-Mission Canary Monitor (< 10ms Auto-Rollback) & Chained SHA-256 Journal

  Phase 5–6: Sovereign Learning Constitution, Weekly Exam Suite & 6-Step Quarterly Roadmap
  [==================================================] 100% COMPLETED
  • 3-Tier Physical Exam Isolation (`sealed_C`), Live Baseline 0.45 on `qwen2.5-coder:3b`
  • Real PyTorch+PEFT LoRA Harness, Tier 2 Calibration (ECE 0.1083), Skill Sunset & 15/15 Recovery Drills
  • P0/P1/P2 Security Hardening & SOTA 1–4 Upgrades (GPU A/B, Taint Warden, Git Worktree, Bi-Temporal Graph)

  Phase 7 (Phases A0–A8 & Cloud Discuss Protocol): Small-Model Architecture & Sovereign Egress Gateway
  [==================================================] 100% COMPLETED & SIGNED OFF
  • Phase A1–A3: 5-Stage Telemetry + `AdaptiveController` + 3-State `MissionCompletionGate` (TCR 0.45 -> 0.55)
  • Phase A4: `VerifiedMemoryStore` with 2-Door Anti-Leak Guard (< 0.40 4-gram) (TCR 0.55 -> 0.90)
  • Phase A5: `VerifiedLearningLoop` + `DeterministicMathTool` Offloading (Live OOD TCR -> 20/20 = 1.00)
  • Phase A6: Bilingual Semantic Generalization (9/10 = 0.90; Combined 29/30 = 96.67%) & 6-Gate Weekly Audit
  • Phase A7–A8: Hardened Web Retrieval, SSRF Guard, 4-Tier Search Cascade & Live Partial Replan Drill
  • Sovereign Cloud Discuss Protocol v1.0: Multi-Agent Council (Gemini/OpenAI/DeepSeek/Grok) & Dynamic Model Resolver (21/21 Pass)

  Phase 8: Sovereign Distributed Capability Fabric & Controlled LoRA Weight Distillation
  [                                                  ] FUTURE VISION
  • Single-LoRA Distillation once >= 100 Verified Gold Traces are accumulated under Master review
  • M3 Desktop GUI Automation (Screen Capture + VLM + Human-in-the-loop Gate)
```

---

## ⚡ Quick Start & Verification

### 1. Verify Small-Model-Centric Cognitive Architecture (Phases A1–A6)
Run the complete Phase A1–A6 verification suite (Telemetry, Adaptive Controller, Verified Memory Store, Verified Learning Loop, Paraphrase Generalization & 6-Gate Weekly Audit):
```bash
python -m pytest tests/test_phase_a1_completion_and_telemetry.py tests/test_phase_a2_adaptive_controller.py tests/test_phase_a3_decision_lora_and_benchmark.py tests/test_phase_a4_verified_memory_scaffolding.py tests/test_phase_a5_verified_learning_loop.py tests/test_phase_a6_paraphrase_and_weekly_audit.py -v
```

### 2. Run the 6-Gate Weekly Autonomous Audit Runner
```bash
python -c "from core.os.cognition.weekly_autonomous_audit import WeeklyAutonomousAuditRunner; r = WeeklyAutonomousAuditRunner().run_weekly_audit(live_ollama=False); print(r['verdict'])"
```

### 3. Verify Embodied OS Runtime (M0 + M1 + M2) & P0 Security Hardening
```bash
python -m pytest tests/test_m0_file_primitives.py tests/test_m1_command_sandbox.py tests/test_m2_browser_actuator.py tests/test_p0_security_hardening.py -v
```

### 4. Launch Standing Production Daemon & Mission Control
```bash
python scripts/run_standing_production_os.py
# Navigate to: http://localhost:9999/dashboard.html
```

---

## 📜 International Documentation & Governance Hierarchy

JKAI Zenith adheres to international open-source and enterprise software documentation standards (IEEE/ISO 42010, Keep a Changelog 1.1.0, SemVer 2.0.0) with strict separation of concerns as mandated by [`/.keywork.md`](file:///d:/Docker/JKAI/.keywork.md):

| Layer | Canonical Location | Description & Scope |
|:---|:---|:---|
| **AI Agent Working Principles (SSoT)** | [`/.keywork.md`](file:///d:/Docker/JKAI/.keywork.md) & [`/.keyword.md`](file:///d:/Docker/JKAI/.keyword.md) | **Strictly for AI Assistants (Antigravity, OpenCode, Sub-agents)**: Boot-on-start protocol, root philosophy, 4-step self-audit protocol, 6 Red Lines, IP/brand honesty rules, and 5-Pillar operational invariants. |
| **Strategic Objectives & Direction** | [`/docs/JKAI_ZENITH_OBJECTIVES_AND_DIRECTION.md`](file:///d:/Docker/JKAI/docs/JKAI_ZENITH_OBJECTIVES_AND_DIRECTION.md) | Vision, 5 Core Capability Pillars, 7 Operating Principles, 5-Stage Roadmap, Mandatory Acceptance Thresholds, and Empirical Validation Matrix (Phases A0–A6). |
| **System Architecture Specification** | [`/docs/architecture/SYSTEM_ARCHITECTURE.md`](file:///d:/Docker/JKAI/docs/architecture/SYSTEM_ARCHITECTURE.md) | High-level system architecture (IEEE/ISO 42010), 3-Layer separation, 5-Pillar Small-Model Cognitive Scaffolding, Event-Sourced Runtime, RSIL-L3, and SOTA 1–4 subsystems. |
| **Hardware Affinity Architecture** | [`/docs/architecture/HARDWARE_AFFINITY.md`](file:///d:/Docker/JKAI/docs/architecture/HARDWARE_AFFINITY.md) | NCNN-inspired hardware affinity, dual Xeon E5 NUMA memory pinning, AMD RX 6600 GPU VRAM ceiling (`<= 7,680 MB`), and INT8 KV Cache acceleration (`rule_hardware.md`). |
| **Topology & Codebase Graph** | [`/docs/architecture/TOPOLOGY.md`](file:///d:/Docker/JKAI/docs/architecture/TOPOLOGY.md) & [`/docs/architecture/JKAI_MAP_GRAPH.md`](file:///d:/Docker/JKAI/docs/architecture/JKAI_MAP_GRAPH.md) | Microservices network topology, ports, databases (Postgres, Redis, Qdrant), and comprehensive module dependency graph. |
| **Architectural Decision Records** | [`/docs/adr/`](file:///d:/Docker/JKAI/docs/adr/) | Chronological immutable architectural decision records (ADR-001 through ADR-006: RSIL-L3 Autonomous Promotion). |
| **System Release Changelog** | [`/CHANGELOG.md`](file:///d:/Docker/JKAI/CHANGELOG.md) | Official release history, version milestones (Keep a Changelog 1.1.0 & SemVer 2.0.0 standard), and empirical verification metrics (`v28.15.0`). |
| **Internal Cognitive Memory Log** | [`/intelligence/identity/GLOBAL_SYSTEM_CONTEXT.md`](file:///d:/Docker/JKAI/intelligence/identity/GLOBAL_SYSTEM_CONTEXT.md) | Long-term cumulative episodic evolution log utilized directly by the AI cognitive runtime (`v59.0` / `SDS v28.15.0`). |

---
*JKAI Zenith Sovereign Cognitive OS — Master LeeTrung.*
