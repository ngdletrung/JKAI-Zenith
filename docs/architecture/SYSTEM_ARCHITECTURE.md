# 🏛️ JKAI Zenith: System Architecture Specification
**Platform: Governed Adaptive Cognitive Agent Operating System**  
*Architecture Standards: IEEE/ISO 42010 Architecture Description*  
*Conceived & Designed by: Master LeeTrung | JKAI Sovereign Core*

---

## 1. Executive Summary & Core Philosophy

JKAI Zenith is an autonomous, self-governing Cognitive Agent Operating System engineered to run 100% locally on sovereign consumer/workstation hardware.

### Foundational Invariant:
> **"Thân là Cốt lõi — Đầu là Linh kiện" (Substrate is Core — Model is Compute Provider)**  
> Small local models (0.5B to 14B) achieve enterprise-grade reliability not by inflating prompt context or endless external scaffolding, but through **strict authority boundaries, native embodied actuators, deterministic kernel offloading, and physical evidence verification**.

---

## 2. The 3-Layer Separation Architecture

```text
┌───────────────────────────────────────────────────────────┐
│                    COGNITIVE LAYER                        │
│  Model (Agnostic: 3B / 14B / Cloud Provider)              │
│  "Understand intent, generate hypotheses & propose plan"  │
└─────────────────────────────┬─────────────────────────────┘
                              │ Proposal (Untrusted LLM Output)
                              ▼
┌───────────────────────────────────────────────────────────┐
│                    AUTHORITY LAYER                        │
│  JKAI Microkernel + 4-Tier Policy Gate + Completion Auth  │
│  "Is this safe? Authorized? Compliant with Red Lines?"    │
│  ALLOW | DENY | REQUIRE_APPROVAL (Default: Fail-Closed)   │
└─────────────────────────────┬─────────────────────────────┘
                              │ Authorized Action (Approved Payload)
                              ▼
┌───────────────────────────────────────────────────────────┐
│                    EXECUTION LAYER                        │
│  Embodied OS Actuators (M0-M3) + Event Sourced Ledger     │
│  "Execute physical side-effect, capture hardware truth"   │
│  Filesystem, Shell Sandbox, Browser Engine, Desktop GUI   │
└───────────────────────────────────────────────────────────┘
```

- **Cognitive Scaling Law**:
  $$\text{Model Intelligence } \uparrow \quad \Rightarrow \quad \text{Cognitive Efficiency } \uparrow \quad \text{AND} \quad \text{Execution Authority = CONSTANT}$$
  Regardless of how smart the model is, runtime boundaries and authorization contracts remain rigid and immutable.

---

## 3. Hybrid Cognitive Router & Gateway (FAST vs. DEEP)

```text
Incoming Query
     │
     ▼
[Reflex Matcher] ──(Exact intent match, deterministic regex)──► [0.1s FAST Return]
     │ (Uncertain / Complex)
     ▼
[Receptionist Core / ReAct Loop] ──► [Native Tool Calling via execute_skill]
     │ (Autonomous Execution: Retrieve missing info before responding)
     ▼
[Planning Pipeline / DEEP DAG]
```

1. **Reflex Matcher (Spinal Reflex)**: Queries with clear system keywords or standard status queries execute in sub-100ms without touching the LLM.
2. **ReAct Loop & Native Tool Calling (Autonomous Brain)**: If the Reflex Matcher cannot resolve the prompt, execution transfers to `receptionist_core.py`. The model leverages tools to autonomously gather necessary data (e.g. system state, IP, disk health) rather than asking the user for trivial details.
3. **Streaming Tool Parsing**: `engine.py` listens to and parses `tool_calls` directly from Ollama/OpenAI-compatible streaming chunks with zero round-trip buffering.

---

## 4. Event-Sourced Mission Runtime & DAG Scheduler

1. **Event-Sourced State Machine**:
   - Replaces fragile in-memory task states with an immutable JSONL Event Store.
   - Every mutation is committed as a discrete event (`TaskInitialized`, `StepScheduled`, `ToolExecuted`, `ArtifactProduced`).
   - Supports instantaneous O(1) state recovery via snapshotting, allowing seamless resume after host reboots or power loss.
2. **DAG Scheduler & Context Pruning**:
   - Decomposes multi-step tasks into a Directed Acyclic Graph (DAG).
   - Independent nodes execute concurrently in asynchronous waves (`asyncio`).
   - Applies strict Context Policies, filtering output keys of parent nodes before passing them to dependent children, drastically reducing token consumption.
3. **Critic Validation Node & Closed-Loop Self-Correction**:
   - The Critic is modeled as a first-class validation node in the execution graph.
   - If validation fails, `ValidationFailedException` is raised, triggering an autonomous repair loop: the offending parent node is reset to `PENDING` and re-scheduled with failure context.
4. **Thread-Safety Double Locking**:
   - Concurrency is guarded via dual-lock mechanisms (`threading.Lock` + OS file locks `portalocker`), preventing race conditions across worker processes.

---

## 5. Evidence Execution Contract (EEC) & Completion Authority

**Constitutional Invariant**: `NO_EVIDENCE_NO_COMPLETION`

```text
Model Proposes Action
        │
        ▼
Actuators (M0-M3) Execute
        │
        ▼
Evidence Ledger (Exit code, File path, SHA-256 Checksum, AST syntax)
        │
        ▼
Evidence Gate Audit (4-Tier Semantic Verification)
        │
        ▼
Completion Authority (Issues cryptographic/signed completion verdict)
        │
        ▼
Kernel State Transition: COMPLETED
```

### 4-Tier Semantic Verification:
- **Tier 1 (Physical Existence)**: File exists on disk and is non-empty ($>0$ bytes).
- **Tier 2 (Syntactic Validity)**: AST parseable (Python), valid JSON/YAML syntax.
- **Tier 3 (Semantic Structure)**: Required classes, functions, and exports are present.
- **Tier 4 (Acceptance Criteria)**: Independent test harness passes 100%.

---

## 6. Embodied OS Agent Actuators (M0–M3)

- **M0 (File Actuators & Code Sensor)**:
  * Atomic writes (`.tmp.<pid>.<time_ns>` $\to$ target rename)
  * Automated `.bak` file versioning
  * SHA-256 content verification
  * 3-Tier Resilient `replace_file_content` (Exact $\to$ CRLF/LF normalized $\to$ whitespace-stripped fuzzy matching).
- **M1 (Execution Sandbox)**:
  * 4-Tier Policy Gate (`READ_ONLY`, `MUTATION_LOCAL`, `DANGEROUS_SYSTEM`, `AMBIGUOUS_HIGH_IMPACT`)
  * Subprocess tree termination (zero zombie processes)
  * Output buffering cap at 16KB.
- **M2 (Browser Sensor & Actuator)**:
  * Docker service `services/ai-browser` on host port 8003.
  * CloakBrowser Stealth Engine v2.0 (fingerprint masking), Crawl4AI fast scraping, Playwright engine.
- **M3 (Computer Use / OS GUI)**:
  * Desktop mouse/keyboard interaction paired with VLM vision targeting.
  * Governed by mandatory Human-in-the-Loop (HITL) confirmation gates.

---

## 7. Recursive Self-Improvement Level 3 (RSIL-L3) & Dual-Key Promotion Framework

JKAI Zenith introduces **RSIL-L3 (Recursive Self-Improvement Level 3)**, an autonomous multi-stage feedback and promotion loop that transitions the system from outsourced model dependence to endogenous cognitive sovereignty.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                       RSIL-L3 RECURSIVE ARCHITECTURE                        │
│                                                                             │
│   StageAttribution Telemetry (6 Stages) ──► CrossStageProposalEngine        │
│                                                       │                     │
│                                                       ▼                     │
│                                            2-Layer Safety Taxonomy          │
│                                                       │                     │
│             ┌────────────────────────┬────────────────┴────────────────┐    │
│             │                        │                                 │    │
│             ▼                        ▼                                 ▼    │
│      [ Tier 1 Loop ]          [ Tier 2 Loop ]                   [ Tier 3 Gate ]
│     Hyperparameters/RAG        LoRA & Router                    Security/Bounds
│             │                        │                                 │    │
│             ▼                        ▼                                 ▼    │
│     Autonomous Optimizer     3-Fold Golden Vault               Master Handshake
│     Gain $\Delta \ge 0.05$   Gain + Drift + Zero Reg           Token Challenge
│             │                        │                                 │    │
│             ▼                        ▼                                 ▼    │
│      Operational Key          Operational Key                   Master Secret
│       AUTO-PROMOTE             AUTO-PROMOTE                      (Out-of-band)
│             │                        │                                 │    │
│             └────────────────────────┼─────────────────────────────────┘    │
│                                      │                                      │
│                                      ▼                                      │
│                        10-Mission Canary Monitor                            │
│                     (Rollback < 10ms if drift > 15%)                        │
│                                      │                                      │
│                                      ▼                                      │
│                    Chained SHA-256 Promotion Journal                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Core Invariants of RSIL-L3:
1. **Dual-Key Constitutional Invariant**:
   $$\text{Autonomous Promotion} \iff \text{Operational Witness Key (Checks-Passed)} \wedge \text{Master Authority Key (Boundary Expansion)}$$
   The autonomous engine holds the operational witness key confirming empirical test passage. The Master retains absolute, out-of-band cryptographic custody over system boundaries and security mutations.
2. **2-Layer Safety Taxonomy**:
   Any proposed mutation touching protected paths (`core/security/`, `auth/`, `sanitizer/`, `egress/`) or protected symbols (`validate_egress_url_ssrf_safe`, `CompletionAuthority`...) is forced into **Tier 3 (Master Approval Required)**.
3. **Zero-Secret-in-Code**:
   Production core code contains zero static secrets or keys (`master_secret=None` fail-closed). Verification requires dynamic environment injection or out-of-band HMAC-SHA256 signature from the Master.
4. **Instant Canary Auto-Rollback**:
   Canary deployments are monitored on a rolling 10-mission sliding window. A measured drift $> 15\%$ triggers an automated rollback to baseline in $< 10\text{ms}$ ($0.018\text{ms}$ measured). Two consecutive rollbacks initiate a fail-closed freeze.
5. **Chained SHA-256 Journal**:
   Every promotion, refusal, challenge, rollback, and freeze event is committed into an append-only cryptographic journal (`prev_sha256 -> curr_sha256`) ensuring immutable auditability.

---

## 8. Small-Model-Centric 5-Pillar Cognitive Architecture & Continuous Verified Learning Loop (`core/os/cognition/`)

In accordance with [`docs/JKAI_ZENITH_OBJECTIVES_AND_DIRECTION.md`](file:///d:/Docker/JKAI/docs/JKAI_ZENITH_OBJECTIVES_AND_DIRECTION.md), JKAI Zenith operates a **5-Pillar Cognitive Architecture** that enables a local small language model (`qwen2.5-coder:3b`) to achieve **96.67% (29/30) Live OOD Task Completion Rate** on an AMD Radeon RX 6600 GPU without inflating model weights:

```text
User / Mission Prompt
        │
        ▼
[1. Proposal Stage] ──► Bilingual Concept Normalization + Verified Memory Retrieval (`top_k=1`, <=120 tok)
        │
        ▼
[2. Controller Stage] ──► `AdaptiveController` (4 Strategies: DIRECT / RETRIEVAL / STEPWISE / CLARIFY_OR_REFUSE)
        │
        ▼
[3. Execution Stage] ──► `DeterministicMathTool` Offloading (Exact Arithmetic) + Live Local Model (`qwen2.5-coder:3b`)
        │
        ▼
[4. Verification Stage] ──► `MissionCompletionGate` (3-State Verdict: COMPLETE | INCOMPLETE | BLOCKED)
        │
        ▼
[5. Outcome & Learning Loop] ──► `VerifiedLearningLoop` + `WeeklyAutonomousAuditRunner` (6 Mandatory Gates)
```

1. **Full-Chain 5-Stage Telemetry (`full_chain_telemetry.py`)**:
   - Every task execution emits a structured trace spanning `Proposal → Controller → Execution → Verification → Outcome`.
   - Unverified failures cannot be assigned a root cause without a full 5-stage trace (`MODEL_REASONING_ERROR`, `CONTROLLER_STRATEGY_ERROR`, `EXECUTION_TOOL_ERROR`, `VERIFICATION_GATE_REJECTION`).
2. **Adaptive Controller & 3-State Completion Authority (`adaptive_controller.py`)**:
   - Dynamically selects among `DIRECT_REASONING`, `RETRIEVAL_FIRST`, `STEPWISE_VERIFIED`, and `CLARIFY_OR_REFUSE_FIRST`.
   - `MissionCompletionGate` strictly decouples tool invocation success from task completion, issuing `COMPLETE` only when 100% of domain and rubric criteria are satisfied (`INCOMPLETE` when criteria are missing, `BLOCKED` when safety/clarification boundaries are triggered).
3. **Verified Memory Store & Bilingual Concept Normalization (`verified_memory_store.py`)**:
   - Enforces 4-tier provenance (`RAW`, `HYPOTHESIS`, `VERIFIED`, `DEPRECATED`) over `data/knowledge/verified_experience_store.jsonl`.
   - Maps Vietnamese and English paraphrases onto canonical semantic concepts (`CONCEPT_SYNONYM_GROUPS`) and enforces a **2-Door Anti-Leak Guard** (`4-gram overlap < 0.40` against all 4 exam suites).
4. **Continuous Verified Learning Loop & Deterministic Math Tool (`verified_learning_loop.py`)**:
   - Offloads exact floating-point and large-integer calculations (`PERCENTAGE_CHANGE`, `TOKEN_THROUGHPUT`, `UNIT_MULTIPLICATION`) to `DeterministicMathTool`, supporting directional operand parsing (`"từ X lên Y"` / `"from X to Y"` vs `"Y so với X"` / `"Y compared to X"`).
   - Evaluates candidate memory updates on held-out tasks and automatically rolls back any update that introduces a single regression (`regressions_count == 0`).
5. **6-Gate Weekly Autonomous Audit Runner (`weekly_autonomous_audit.py`)**:
   - Audits the entire cognitive loop across 6 mandatory gates: (1) Held-out OOD TCR $\ge 0.95$; (2) Paraphrase & Bilingual Generalization TCR $\ge 0.85$; (3) Zero 4-gram Anti-Leak Violations; (4) Hardware Envelope Compliance (VRAM $\le 7,680\text{ MB}$, Latency $\le 15\text{s}$); (5) Zero Regression across Phases A0–A5; and (6) Pure LF + SHA-256 Artifact Parity.

---

## 9. SOTA 1–4 Sovereign Governance, Security & Memory Subsystems

1. **SOTA 1 — Live GPU A/B Shadow Harness (`core/governance/ab_shadow_harness.py`)**:
   - Executes paired baseline vs. candidate inference on the local AMD Radeon RX 6600 (`qwen2.5-coder:3b`), enforcing the hardware VRAM ceiling (`<= 7,680 MB`) and recording SHA-256 chained verdicts in `data/telemetry/ab_shadow_ledger.jsonl`.
2. **SOTA 2 — Information-Flow Taint Tracking Warden (`core/security/taint_tracking_warden.py`)**:
   - Propagates provenance labels (`TRUSTED_SYSTEM`, `TRUSTED_MASTER`, `UNTRUSTED_EXTERNAL`) across data transformations and blocks `UNTRUSTED_EXTERNAL` content (e.g., scraped web pages or unverified RAG chunks) from invoking high-impact actuators (`terminal_exec`, `write_file`, `delete_file`).
3. **SOTA 3 — Transactional Git Worktree Sandbox (`core/os/sandbox/transactional_worktree.py`)**:
   - Executes autonomous code modifications inside isolated Git worktrees (`begin -> apply -> test -> commit | rollback`), guaranteeing zero dirty state in the primary workspace if verification fails.
4. **SOTA 4 — Bi-Temporal Knowledge Graph (`core/os/memory/bi_temporal_graph.py`)**:
   - Tracks both transaction time (`t_created`, `t_expired`) and valid time (`t_valid_from`, `t_valid_to`), preventing silent overwrites of historical facts and enabling deterministic point-in-time queries (`query_as_of`).

---

## 10. Hardened Native Web Retrieval Subsystem (Phase A7)

JKAI Zenith implements a sovereign, zero-external-dependency **Tầng 2 Safe Direct Web Fetch & Verbatim Retrieval Subsystem**, bridging the gap between Search APIs (Tavily/DDG) and heavy Headless Browsers (`ai-browser`/Playwright) without sacrificing zero-trust determinism:

```text
Target URL / Query
        │
        ▼
[1. SSRFResolveAndPinGuard] ──(Per-hop DNS resolution, IP pinning, userinfo & RFC1918/CGNAT blocks)
        │ (Validated Public Egress)
        ▼
[2. Unified Single Fetch Pipeline] ──(HTTP GET with follow_redirects=False, per-hop revalidation)
        │ (Raw Response)
        ▼
[3. DeterministicWebSanitizer]
        ├─ Layer 1: Stealth CSS & Hidden DOM Stripper (display:none, visibility:hidden, opacity:0, font-size:0)
        ├─ Layer 2: Invisible Character Sanitizer (strictly preserving ZWNJ \u200c, ZWJ \u200d, NFC diacritics & emoji)
        └─ Layer 3: Delimiter Neutralizer & Base64 Prompt Injection Defuser ([DEFUSED_ENCODED_PAYLOAD])
        │
        ▼
[4. Pure-Python BM25-CP Selector] ──► Top-K Verbatim Passages with exact char_start, char_end, and SHA-256
        │
        ▼
[5. TaintTrackingWarden] ──► Tagged Envelope [UNTRUSTED_WEB_CONTENT] with blocked high-impact sink execution
```

### Architectural Guarantees:
1. **Single Egress Pipeline & Revalidation (`core/security/ssrf_resolve_pin_guard.py`)**:
   - Outbound fetches enforce `follow_redirects=False` at the transport layer.
   - Every redirect target is independently resolved and revalidated against SSRF blocklists (blocking `127.0.0.1`, cloud metadata `169.254.169.254`, IPv4-mapped IPv6 `::ffff:127.0.0.1`, and CGNAT `100.64.0.0/10`), eliminating DNS rebinding and TOCTOU redirect attacks.
2. **Three-Layer Deterministic Sanitization (`core/sanitizer/deterministic_web_sanitizer.py`)**:
   - Zero LLM involvement in the sanitization pipeline, ensuring byte-level determinism and immunity to System 1 manipulation.
   - Cleans invisible/bidi characters while strictly preserving linguistic formatting (ZWNJ for Persian/Indic scripts, ZWJ for multi-person emojis, and Unicode NFC normalization for accented Vietnamese text).
3. **Pure-Python BM25-CP Verbatim Passage Selection**:
   - Implements Okapi BM25 with contiguous phrase matching boosts (1.5x for bigrams, 2.0x for trigrams) using only the Python standard library.
   - Returns structured `VerbatimPassage` records whose slices match character-for-character with the sanitized canonical text, accompanied by individual SHA-256 hashes.
4. **Information-Flow Taint Enforcement (`core/security/taint_tracking_warden.py`)**:
   - Untrusted web content is assigned `ProvenanceLevel.UNTRUSTED_EXTERNAL` and enclosed within cryptographic tracking envelopes.
   - The Policy Gate rejects any execution flow attempting to feed untrusted external content directly into privileged sinks (`terminal_exec`, `write_file`) without explicit Master authorization.

---

## 11. Sovereign 4-Tier Search Cascade & Canonical Web Interfaces (Phase A7.1)

JKAI Zenith standardizes sovereign, privacy-preserving web exploration across 4 cascading tiers with canonical international tool interfaces:

```text
Incoming Query
      │
      ▼
[Tier 1: RSS Direct Poller] ──(In-tree RSS 2.0 / Atom 1.0, local disk cache, strict 50% token coverage)──► [Instant Fresh Match]
      │ (Miss)
      ▼
[Tier 2: SearXNG Self-Hosted] ──(Containerized metasearch port 8888, zero telemetry, private aggregation)──► [Sovereign Metasearch]
      │ (Miss / Unreachable)
      ▼
[Tier 3: Tavily Commercial Fallback] ──(Direct JSON API when TAVILY_API_KEY is configured)──► [Commercial Structured Results]
      │ (Key missing or exhausted)
      ▼
[Tier 4: DuckDuckGo Hardened Direct] ──(Direct HTML + DDGBotDetectionError on 403/429/challenges + DDGS fallback)──► [Free Web Results]
```

### Standardized Tool Interfaces:
- **`webfetch`** (`fetch_url_content`): Canonical safe fetch pipeline with DNS pinning, per-hop SSRF revalidation, and three-layer sanitization. Completely eradicates external proxy dependencies (`r.jina.ai`).
- **`websearch`** (`execute_real_web_search_sync`): Structured 4-tier cascade returning unified JSON schemas with temporal freshness labeling.

---

## 12. Live End-to-End PARTIAL Replan Subsystem (Phase A8)

To eliminate unverified completion claims and blind retry loops, JKAI Zenith enforces a closed-loop Adaptive Replan architecture:

```text
Step 1: Execution
      │
      ▼
[MissionCompletionGate] ──(Evaluates 100% of criteria)──► Status: INCOMPLETE (e.g. 2/5 verified)
      │
      ├─► [CheckpointStore] ──► Captures StepCheckpoint(status="PARTIAL", verified_facts=[...])
      │
      ▼
[AdaptiveController] ──► Detects INCOMPLETE + unresolved_criteria_ids
      │
      ├─► Strategy: ERROR_ADAPTIVE_RECOVERY
      └─► Branch: TARGETED_REPAIR
      │
      ▼
[Time-Travel Backtracking] ──► Restores consolidated facts from best checkpoint (preserves 2/5)
      │
      ▼
Step 2: Targeted Repair ──► Worker repairs strictly the 3 remaining criteria
      │
      ▼
[MissionCompletionGate Re-Evaluation] ──► Status: COMPLETE (5/5 verified)
      │
      ▼
[RecoveryDrillLedger & FullChainTracer] ──► Persists physical trace with pure LF line endings
```

---

## 13. Multi-Agent Cloud Discussion Subsystem (JKAI Discuss Protocol v1.0 & Dynamic Model Resolver)

To enable strategic multi-model deliberation (Gemini, ChatGPT, DeepSeek, Grok) while preserving absolute local sovereignty, zero unverified auto-escalation, and zero data leakage, JKAI Zenith establishes the **JKAI Discuss Protocol v1.0**:

```text
[Master Direct Command (master_cli / master_ui)]
      │
      ▼
[Deterministic Trigger Parser] ──(Source Isolation + Negation Defense + Unicode NFKD)──► [Match: Discuss Intent]
      │
      ▼
[Centralized Egress Gate]
      ├─► Dual Killswitch Invariant: [JKAI_LOCAL_ONLY=1] (Immutable Baseline) & [JKAI_DISCUSS_ALLOWED=1] (Mission Scoped)
      ├─► Pre-send Hardened Scrubber: Strips paths, internal IPs, keys (sk-, tvly-, xai-, AIzaSy), and citizen IDs
      ├─► Virtual Canary Guard: In-memory UUID mapping; hard-blocks outbound payload if internal canary token found
      └─► Context Canary: 100% rule-based Jaccard overlap & Architecture Gazetteer scan (Active Mosaic Prevention)
      │
      ▼ (All Security Gates Passed)
[Egress Hash-Chain Ledger] ──► Records prev_hash -> entry_hash (Tamper-evident cryptographically linked audit)
      │
      ▼
[Delphi Protocol & Multi-Round Dialectic Engine] (Max 10 Rounds, Order Randomized)
      ├─► Neutral Role Contract: Zero metadata leakage (never mentions 'Master', 'JKAI', 'kín')
      ├─► Universal Cloud Client: OpenAI-compatible REST pipeline with Dynamic Model Resolver
      │     └─► Semantic Version Ranking (3.8 > 2.5 > 1.5) + Fallback Cascade (resilient to 503/404)
      ├─► Data Leak Guard: Intercepts reverse prompt probes demanding code/secrets -> Emits MasterSecurityAlert
      └─► Claim-Level Consensus Tracker:
            [VERIFIED] | [AGREED_UNVERIFIED] | [CONFLICTED] | [INSUFFICIENT_EVIDENCE] | [REJECTED]
      │
      ▼
[Executive Briefing Generator] ──► Synthesizes Standard 4-Part Report (Verified, Consensus, Disagreements, Candidates)
```

---
*JKAI Zenith Sovereign Architecture Specification (SDS v28.19.0) — Master LeeTrung.*
