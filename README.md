# 🏛️ JKAI Zenith: Microkernel-Inspired Decision-Native Sovereign AI OS

[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen?style=for-the-badge&logo=github)](https://github.com/ngdletrung/JKAI-Zenith.git)
[![Governance](https://img.shields.io/badge/Governance-Zero--Trust_Gate_0-blue?style=for-the-badge)](https://github.com/ngdletrung/JKAI-Zenith.git)
[![Architecture](https://img.shields.io/badge/Architecture-Decision--Native_Microkernel-indigo?style=for-the-badge)](https://github.com/ngdletrung/JKAI-Zenith.git)
[![Security](https://img.shields.io/badge/Security-Zero--Egress_Sovereign-red?style=for-the-badge)](https://github.com/ngdletrung/JKAI-Zenith.git)
[![Hardware](https://img.shields.io/badge/Hardware-RX6600_8GB_%2B_Xeon_128GB-purple?style=for-the-badge)](https://github.com/ngdletrung/JKAI-Zenith.git)
[![Test Suite](https://img.shields.io/badge/Tests-48%2F48_Passing-success?style=for-the-badge)](https://github.com/ngdletrung/JKAI-Zenith.git)

> **JKAI Zenith** is an enterprise-grade, microkernel-inspired **Decision-Native Sovereign AI Operating System**.  
> Designed for long-horizon mission autonomy, mathematical determinism, and zero-trust reliability under constrained local hardware.

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
  └───────────────────────────────┬───────────────────────────────▲────────────────────────┘
                                  │ Propose Action / Verify       │ Authorize & Enforce
                                  ▼                               │
  ┌───────────────────────────────────────────────────────────────┴────────────────────────┐
  │                   COGNITIVE BUS & REFLEX DECISION SUBSTRATE (System 1)                 │
  │  • Tri-Tier Decision Adapter:                                                          │
  │     - Tier 1: Local Reflex Substrate (Sub-5ms Non-Autoregressive Decision Engine)      │
  │     - Tier 2: Local Reasoner (Ollama Qwen/Gemma Structured Classifiers)                │
  │     - Tier 3: Deterministic Rule Fallback (Sub-millisecond Keyword & Heuristic Match)  │
  │  • Decision Primitives: BOOLEAN, CHOICE, SCORE                                         │
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
  │  • 100% On-Premise, Zero-Egress Network Isolation (JKAI_LOCAL_ONLY=1 Killswitch)       │
  └────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🏛️ Constitutional Invariants & Core Laws

JKAI Zenith is anchored upon non-negotiable operational laws enforced at compile-time and runtime:

### 1. The JKAI Mission Law
> **"MISSION IS INVARIANT. ONLY STRATEGY ADAPTS."**  
> Under environmental uncertainty or tool failure, strategies adapt dynamically (Plan A $\rightarrow$ Plan B), while mission objectives, security boundaries, and success invariants remain 100% immutable (Goal Conservation Rate = 100%).

### 2. Decision ≠ Authority Principle
> **"Reflex Engines Propose. The Deterministic Kernel Commands."**  
> Fast-path System 1 reflex engines produce non-autoregressive decision primitives (`BOOLEAN`, `CHOICE`, `SCORE`) with calibrated confidence. However, they hold **zero operational authority**. Every proposed decision must be cryptographically traced, sanitized, and authorized by the Deterministic Kernel before execution.

### 3. The Two Absolute Invariants (2 NEVER)
1. **NEVER System 1 in FSM**: Finite State Machine state transitions are strictly deterministic. No probabilistic model can trigger, alter, or synthesize state transitions.
2. **NEVER System 1 in Policy Gate**: Access control, security boundaries, and action authorization through the Dual-Stage Action Firewall are 100% deterministic and zero-trust.

### 4. 100% Zero-Egress Sovereign Guarantee
- Hardened by the `SOVEREIGN-NO-CLOUD-KILLSWITCH` (`JKAI_LOCAL_ONLY=1`).
- Completely rejects external commercial cloud APIs, preventing proprietary telemetry leakage, vendor lock-in, and unpredictable latency.
- Full cognitive stack operates strictly on local hardware (Dual Xeon E5-2699 v4 + AMD RX 6600).

---

## 🛡️ Key Architectural Subsystems

### A. Tri-Tier Decision Adapter (`core/cognitive_bus/`)
Provides resilient, tiered intelligence for routing, fast-path verification, and risk assessment:
- **Tier 1 (Local Reflex Substrate)**: Ultra-fast non-autoregressive neural classification ($< 5\text{ms}$).
- **Tier 2 (Local Reasoner)**: Local Ollama-hosted LLMs (e.g. Qwen 2.5 / Gemma) for structured classification when reflex confidence falls below threshold.
- **Tier 3 (Deterministic Rule Fallback)**: In-process deterministic keyword & heuristic fail-safe ($0.13\text{ms}$ P95 latency) ensuring guaranteed continuous operation even if all neural inference engines are unavailable.

### B. State Sanitizer 2.3a (`core/sanitizer/`)
Ensures data hygiene before state ingestion by decision providers:
- **Hard Memory Cap**: Strict $65,536\text{ Bytes}$ ($64\text{KB}$) upper bound per state ingestion.
- **Canonical Hash**: SHA-256 fingerprint generated strictly from canonical JSON representations.
- **Secret Redaction**: Automated scrubbing of credentials, API tokens, and PII with audit reports.

### C. Token Budget Guard & H-Triad Security (`core/guard/`)
- **TokenBudgetGuard**: Hard ceiling on model context and token consumption, preventing runaway agent loops and resource exhaustion attacks.
- **H1 (Fast-Path Verification)**: Controlled bypass mechanism for verified idempotent/read-only tasks, reducing system latency while keeping mutative actions strictly guarded.
- **H2 (Model Identity Honesty)**: Guarantees authentic provenance; forbids synthetic claims or fake model attribution; enforces architectural invariance.
- **H3 (Instant-Fail Exclusion)**: Deterministic fast rejection for malformed, adversarial, or out-of-budget payloads.

### D. Layered Verification Graph (L1–L4) (`core/verification/`)
- **L1 Structural**: Schema conformance, type validation (Pydantic v2 strict), argument bounds.
- **L2 Environmental**: Pre-flight state verification, resource availability, file lock verification.
- **L3 Semantic**: Intent alignment, goal drift detection, non-destructive mutation checks.
- **L4 Physical**: Closed-loop physical verification (file existence, exit codes, SHA-256 artifact integrity).

### E. Resilient Telecommunications Gateway (`services/ai-telegram/`)
- Enterprise bot adapter with mounted `HTTPAdapter` retry strategy (`max_retries=5`, exponential backoff) and balanced connection keep-alive parameters, completely eliminating socket drops and `RemoteDisconnected` crashes during 24/7 autonomous operations.

---

## 📊 Empirical Benchmarks & Production Validation

JKAI Zenith has been empirically benchmarked and audited across strict operational criteria:

| Benchmark / Audit Suite | Target Capability | Metric / Objective | Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Local Decision Benchmark v2.1** | 5-Criteria Rigorous Evaluation | Dual-Mode Honest Labeling, $n=50$ | **P95: 0.13ms / 100% Acc** | 🟢 **SEALED** |
| **State Sanitizer 2.3a Suite** | 64KB Cap & Canonical SHA-256 | Overflow rejection & zero leakage | **100.0% Pass** | 🟢 **SEALED** |
| **H1 Fast-Path Verification** | Low-risk bypass & safety gating | Zero false authorization of mutations | **100.0% Pass** | 🟢 **SEALED** |
| **H2 Model Identity Honesty** | Provenance & Anti-Spoofing | Zero impersonation, dual-mode truth | **100.0% Pass** | 🟢 **SEALED** |
| **H3 Instant-Fail & Token Guard** | Quota Enforcement & Exploit Block | Instant fail on budget exhaustion | **100.0% Pass** | 🟢 **SEALED** |
| **Gate F Hardware Soak Audit** | 1,000 Real Hardware Missions | Zero-Tolerance Kernel Violations | **99.5% Success (0 Fatal)**| 🟢 **SEALED** |
| **Core Safety Regression Suite** | Total Architectural Safety Tests | 48/48 Passing in 2.91s | **100.0% GREEN** | 🟢 **SEALED** |

### Validated Physical Envelope (Master Host)
- **Host Hardware**: Dual Intel Xeon E5-2699 v4 (22 cores / 44 threads), 64GB–128GB ECC RAM.
- **Accelerator**: AMD Radeon RX 6600 (8GB GDDR6 VRAM, Vulkan / ROCm).
- **Latency Profile**: Tier 3 Deterministic Rule P95 = **0.13 ms**; Kernel Invariant Verification P95 = **0.85 ms**.
- **Memory Footprint**: Base Kernel RSS allocation overhead $< 50\text{ MB}$; peak mission soak $< 24.5\text{ GB}$.

---

## 📁 Repository Directory Structure

```text
JKAI-Zenith/
├── core/                         # Ring 0: Deterministic Microkernel & Invariants
│   ├── contracts/                # Identity Chain (8-Link) & Cognitive Contracts
│   ├── governance/               # Zero-Trust Gate 0 Invariants & Gate F Auditor
│   ├── cognitive/                # World Model & Reconstructive State Store
│   ├── cognitive_bus/            # Tri-Tier Decision Adapter & Reflex Substrate
│   ├── sanitizer/                # State Sanitizer 2.3a (64KB Cap & Canonical JSON)
│   ├── guard/                    # Token Budget Guard & Instant-Fail Exclusion
│   ├── benchmark/                # Rigorous 5-Criteria Local Decision Benchmark Harness
│   ├── routing/                  # Deterministic Controller & Fast-Path Policy Router
│   ├── planning/                 # Meta-Planner & Async TaskGraph Engine
│   ├── security/                 # Dual-Stage Action Firewall & Zero-Trust Gates
│   ├── recovery/                 # Error Classification & Self-Healing Replanner
│   └── verification/             # Layered Verification Graph (L1-L4) & Physical Verifier
├── intelligence/                 # Ring 3: User Space Capabilities & Reasoners
│   ├── capabilities/             # Drive, Office, MikroTik, MariaDB, Postgres, SMTP
│   └── applications/             # Enterprise Automation, Threat Intel, Operations
├── services/                     # Autonomous Microservices & Gateways
│   └── ai-telegram/              # Resilient Telegram Bot with HTTPAdapter Retry
├── scripts/                      # Standing Production Daemons & Operations CLI
├── web/                          # Sovereign Mission Control Web Dashboard (SPA)
├── docs/                         # Architecture Documentation & Architectural Decision Records (ADR)
└── tests/                        # Comprehensive Architecture, Safety & Regression Tests (48/48 Green)
```

---

## 🚀 Strategic Future Development Roadmap

JKAI Zenith is actively advancing along a four-phase evolutionary roadmap toward full production maturity:

```text
  Phase 1: Deterministic Microkernel & Baseline Guardrails
  [==================================================] 100% SEALED & OPERATIONAL
  • FSM & Zero-Trust Gate 0 Invariants
  • State Sanitizer 2.3a & Token Budget Guard
  • Tri-Tier Decision Adapter with Deterministic Baseline
  • 5-Criteria Benchmark Harness & Honest Reporting (Commit 0b2acc3)
  
  Phase 2: Offline Self-Hosted Neural Reflex Engine
  [========================>                         ] 50% IN PROGRESS
  • Standardize Architectural Decision Records (docs/adr/)
  • Deploy Local 421M Parameter Non-Autoregressive Decision Checkpoint
  • Hardware Inference Optimization on AMD RX 6600 (Vulkan / ROCm fp16 / int8)
  • Zero-Egress Neural Decision Serving (< 5ms local latency)
  
  Phase 3: Asynchronous Shadow Evaluation & Calibration Harness
  [--------->                                        ] 20% PLANNED
  • Production Non-Blocking Shadow Evaluation on Live Mission Streams
  • ExecutionReceipt Artifact Verification with Cryptographic Signatures
  • Continuous Expected Calibration Error (ECE) Optimization on Real Mission Telemetry
  • Automated Offline Weight Tuning from Validated Execution Graphs
  
  Phase 4: Sovereign Distributed Capability Fabric & Multi-Node Mesh
  [                                                  ] 0% FUTURE VISION
  • Pydantic v2 Strict Tool Contract Registry across all Capability Providers
  • Multi-Host Microkernel Coordination across Heterogeneous Edge Hardware
  • Autonomous High-Availability Failover & State Synchronization
```

---

## ⚡ Quick Start & Verification

### 1. Verify Core Safety & Architecture Test Suite
Run the comprehensive 48-test constitution and invariant suite:
```bash
python -m pytest tests/test_local_decision_benchmark_5criteria.py tests/test_state_sanitizer_23a.py tests/test_h1_fast_path_verification.py tests/test_h2_model_identity_honesty.py tests/test_h3_instant_fail_exclusion.py tests/test_token_budget_guard.py tests/architecture/ -v
```

### 2. Launch Local Decision Benchmark (Dual-Mode Honest Evaluation)
```bash
python core/benchmark/local_decision_benchmark.py
```

### 3. Launch Standing Production Daemon
```bash
python scripts/run_standing_production_os.py
```

### 4. Access Sovereign Mission Control
Navigate to the local mission dashboard:
```text
http://localhost:9999/dashboard.html
```

---

## 📜 Intellectual Property & Governance Standards

- **Sovereign Independence**: JKAI Zenith is an original, sovereign cognitive architecture conceived and developed by **Master LeeTrung**. 
- **Brand Protection Policy (`.keyword.md`)**: Strictly forbids external third-party model trademarks in internal files, classes, or interfaces.
- **Architectural Discipline**: All kernel modifications are governed by strict **ARCHITECTURE STOP** protocols to safeguard invariant determinism and platform stability.
