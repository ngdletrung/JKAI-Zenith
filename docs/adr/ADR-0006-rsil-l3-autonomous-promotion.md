# ADR-0006: Recursive Self-Improvement Level 3 (RSIL-L3) & Dual-Key Autonomous Promotion

## Status
**ACCEPTED & OPERATIONAL** (Phase 4 / Turn 308, Verified by Antigravity & OpenCode)

## Context
Prior to Phase 4, JKAI Zenith contained several isolated learning loops (Memory Reflect, RAG Harness, Code ACI, System 1 Shadow, Cost Ledger). However, these loops operated as fragmented islands without an end-to-end autonomous coordinator. More critically, true cognitive intelligence (Endogenous Intelligence) resided primarily in external pretrained model weights, while system improvements required manual human review for every adjustment.

Master posed two foundational architectural questions:
1. *"Why can't the system approve improvements autonomously instead of waiting for me to approve?"*
2. *"Is current intelligence residing in the external model rather than in the JKAI architecture itself?"*

To achieve endogenous intelligence while strictly preserving safety, a recursive self-improvement protocol was needed that enables machine autonomy for safe parameter and model tuning, while guaranteeing absolute human custody over security boundaries.

## Decision
We implement **RSIL-L3 (Recursive Self-Improvement Level 3)** across four core components:

1. **3-Tier Mutation Taxonomy (`core/os/cognition/rsil_orchestrator.py`)**:
   - **Tier 1 (Parameters & Memory)**: RAG hyperparameters (RRF $k=60$ gain $\Delta \ge +0.05$), KV-Cache prefix alignment, and weak-supervision dataset ingestion. Automatically evaluated and promoted into Canary under `Operational Witness Key`.
   - **Tier 2 (Models & Routers)**: LoRA adapters and routing thresholds evaluated across a 3-fold held-out Golden Vault ($H_1, H_2, H_3$). Requires Gain $\Delta \ge +0.05$, repeat drift $\le 10\%$, and zero safety regressions. Guarded by CPU load $\le 70\%$ and quota limits (max 3/week).
   - **Tier 3 (Security & Boundaries)**: Any diff touching security paths (`security/`, `auth/`, `sanitizer/`, `egress/`) or sensitive symbols (`validate_egress_url_ssrf_safe`, `CompletionAuthority`...). Autonomous promotion is **STRICTLY FORBIDDEN**. Requires an out-of-band challenge-response signed by the Master.

2. **Dual-Key Invariant**:
   $$\text{Autonomous Promotion} \iff \text{Operational Witness Key (Checks-Passed)} \wedge \text{Master Authority Key (Boundary Expansion)}$$
   The machine signs `CHECKS_PASSED` across 4 orthogonal constitutional gates (Gain, Safety, AST Invariant, Resource Ceiling $\le 30\%$). The Master retains exclusive custody over `MASTER_AUTHORITY_KEY`.

3. **Zero-Secret-in-Code & Fail-Closed Gate (`core/os/cognition/rsil_tier3_cross_stage_engine.py`)**:
   Production core code contains zero hardcoded secrets (`master_secret=None`). When `JKAI_MASTER_AUTHORITY_KEY` is absent from the environment, the gate remains in `AWAITING_MASTER_SIGNATURE` and all verification attempts fail closed (`REJECTED_MISSING_MASTER_KEY`). Signing occurs strictly out-of-band via `sign_master_challenge_out_of_band`.

4. **10-Mission Canary Monitor & Instant Auto-Rollback (`core/os/cognition/rsil_tier2_lora_loop.py`)**:
   Monitors rolling 10-mission performance in Canary. If measured drift $> 15\%$, active adapters are rolled back to baseline in $< 10\text{ms}$ ($0.018\text{ms}$ measured). Two consecutive rollbacks trigger a fail-closed freeze (`FROZEN_CONSECUTIVE_ROLLBACKS`).

5. **Chained SHA-256 Promotion Journal**:
   Every promotion, refusal, challenge, rollback, and freeze event is committed into an append-only cryptographic journal (`prev_sha256 -> curr_sha256`), providing tamper-evident auditability.

## Consequences
- **Positive**:
  - Closed-loop recursive autonomy: The system autonomously diagnoses bottlenecks via `StageAttribution` (6 stages), generates targeted proposals, benchmarks them, promotes to Canary, and rolls back upon degradation.
  - Zero privilege escalation: Machine cannot self-authorize security boundary expansions or escape sandbox constraints.
  - Sub-millisecond rollback safety ($0.018\text{ms}$) guarantees zero production downtime upon model degradation.
- **Negative / Constraints**:
  - Master must maintain and securely inject `JKAI_MASTER_AUTHORITY_KEY` when authorizing Tier 3 security mutations.
  - LoRA fine-tuning is throttled by CPU/GPU resource guards to avoid disrupting production missions.
