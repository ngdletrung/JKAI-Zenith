# 📋 Changelog — JKAI Zenith
All notable changes to the JKAI Zenith Cognitive Operating System are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and adheres to Semantic Versioning.

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
