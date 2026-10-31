# ADR-0007: Master Triad Embodied Actuation & Deterministic Terminal Approval Ladder

## Status
**ACCEPTED & OPERATIONAL** (Phase 5 / Turn 312, Verified by Antigravity & OpenCode)

## Context
Per Master LeeTrung's directive:
> *"Chỉ khi nào JKAI có thể tương tác được browser, terminal, File một cách thuần phục thì khi đó JKAI mới đủ năng lực."*

Previously, JKAI's tool execution substrate was fragmented:
1. File operations had rudimentary replace logic susceptible to indentation and whitespace discrepancies.
2. Terminal execution lacked a deterministic approval and cryptographic audit layer, presenting potential security surface or privilege escalation risks.
3. Browser interactions existed as isolated prototypes without unified contract integration in the primary agent loop (`ProjectAgentLoop`).
4. Small local language models (SLMs, e.g. `qwen2.5-coder:3b`, `qwen3.5:4b` on AMD RX 6600 8GB) suffered high cognitive strain when forced to generate brittle shell one-liners or complex CSS selectors.

## Decision
We implement the **Master Triad Embodied Actuation** architecture across three core pillars:

1. **Master Triad Gateway & Unified Contracts (`core/kernel/tool_contracts.py`, `core/kernel/project_agent_loop.py`, `services/ai-brain/receptionist/executor_gateway.py`)**:
   - **File (M0)**: Controlled filesystem operations bounded by workspace scope (`scoped_directory`), eliminating traversal attacks.
   - **Terminal (M1)**: Controlled shell execution bounded by a 4-tier approval ladder.
   - **Browser (M2)**: Semantic browser interaction via `observe`, `act`, `extract`, `read_doc`, `navigate`, and `screenshot`.

2. **Deterministic Terminal Approval Ladder & Chained Audit Ledger (`core/security/terminal_approval_ladder.py`)**:
   - Pre-execution deterministic classification into 4 discrete tiers:
     - `READ_ONLY`: Passive querying commands (`ls`, `dir`, `cat`, `git status`, `git log`, `pwd`...). Auto-approved.
     - `REVERSIBLE`: State modifications with trivial undo path (`mkdir`, `touch`, `git checkout -b`, `git stash`...). Basic confirmation.
     - `IRREVERSIBLE`: State modifications without automatic rollback (`rm`, `del`, `drop`, `git reset --hard`, `git push --force`...). Explicit dual-confirmation required.
     - `PRIVILEGED`: System-level root elevation (`sudo`, `chmod`, `chown`, `systemctl`, `mkfs`...). Direct Master authorization required.
   - **Chained Cryptographic Audit Ledger (`data/telemetry/terminal_audit.jsonl`)**: Append-only log where every executed command is hashed with SHA-256 (`prev_hash -> entry_hash`), recording command, approval tier, exit code, and execution metadata.

3. **Smart Multi-Format Patch Engine (`core/utils/smart_patch_engine.py`)**:
   - 3-tier resilient surgical code editing:
     - Tier 1: Exact match.
     - Tier 2: Whitespace and indentation normalized matching that calculates indentation deltas and reconstructs the target file's indentation style, protecting Python AST structure.
     - Tier 3: Unified diff hunk parser and patch applicator.
   - Fully integrated into both `SYSTEM_CORE_EXECUTOR/logic.py` and `project_agent_loop.py`.

4. **Sovereign Local Architecture ("Thân là Cốt lõi — Đầu là Linh kiện")**:
   - 100% offline, local-first execution.
   - Scaffolding performs deterministic classification, validation, diff calculation, and logging on CPU, keeping the local SLM unburdened by repetitive syntactic formatting.

## Consequences
- **Positive**:
  - Unified multi-domain tool execution enables the agent to autonomously coordinate between editing code, executing tests in terminal, and reading documentation in browser within a single loop.
  - Hardened security: no shell command can run unclassified, unapproved, or unlogged.
  - Zero AST corruption from whitespace mismatch during code patches.
  - Zero non-localhost egress during tool actuation.
- **Negative / Constraints**:
  - Commands classified as `IRREVERSIBLE` or `PRIVILEGED` must be explicitly confirmed or run in autonomous test environments.
  - Audit log must be periodically rotated or archived per telemetry policy.
