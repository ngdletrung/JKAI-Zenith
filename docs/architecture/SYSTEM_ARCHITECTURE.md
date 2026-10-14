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
*JKAI Zenith Sovereign Architecture Specification — Master LeeTrung.*
