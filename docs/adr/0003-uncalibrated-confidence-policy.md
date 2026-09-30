# ADR 0003: Kernel Policy for Uncalibrated Confidence

## Status
Accepted

## Context

Local System-1 neural classifiers and reasoners frequently ship WITHOUT fitted temperatures. Their raw confidence output is therefore **uncalibrated**: a stated 0.90 does not mean 90% empirical accuracy on local tasks.

JKAI's `TriTierDecisionAdapter` treats confidence as a first-class field:
1. `all_passed_confidence_floor` decides whether a Tier 2 result is accepted or falls through to Tier 3.
2. `TypedJudgementPacket.confidence` is surfaced for downstream consumption (shadow telemetry, policy verification).

Question: **when a Tier 2 backend declares `calibration_state = "uncalibrated"`, how should the Kernel authorize actions based on its confidence?**

This is a safety and governance policy decision.

## Decision

### D1. Three action classes

Defined at the kernel boundary by the Action Firewall:

| Class | Definition | Examples |
|---|---|---|
| **READ** | No persistent state change. Idempotent. Reversible at zero cost. | `read_file`, `SELECT`, `GET /status`, `list_*` |
| **MUTATE_REVERSIBLE** | State change, but rollback exists and is cheap. | `write_file` to temp, `INSERT` to staging, `UPDATE` with backup |
| **MUTATE_IRREVERSIBLE** | State change with no cheap rollback. | `DELETE`, `DROP`, firewall rule change, send email, `POST /payment` |

Classification is conservative: **unknown action -> MUTATE_IRREVERSIBLE**.

### D2. Policy table

| Action class | Calibrated backend (ECE <= 0.15) | Uncalibrated backend |
|---|---|---|
| **READ** | Authorize if `confidence >= θ_read` | Authorize if `confidence >= θ_read_uncal` |
| **MUTATE_REVERSIBLE** | Authorize if `confidence >= θ_mut` | **Escalate to Tier 3 always** |
| **MUTATE_IRREVERSIBLE** | Authorize if `confidence >= θ_irrev` **AND** Tier 3 agrees | **Escalate to Tier 3 always** |

Threshold placeholders (UNFITTED):
- `THETA_READ_FIT_PLACEHOLDER: float = 0.70`
- `THETA_READ_UNCAL_FIT_PLACEHOLDER: float = 0.85`
- `THETA_MUT_FIT_PLACEHOLDER: float = 0.90`
- `THETA_IRREV_FIT_PLACEHOLDER: float = 0.95`

### D3. "Escalate to Tier 3" semantics

Tier 3 deterministic rule engine runs in addition to Tier 2. Both results are recorded in shadow telemetry. The authorization comes from Tier 3. If Tier 3 also cannot decide, the action is queued for operator review. Fail-closed.

### D4. Confidence is advisory, never authoritative

Regardless of calibration state, `TypedJudgementPacket.confidence` is a signal, not a credential. The kernel never authorizes based on confidence alone.

### D5. Calibration state promotion

Backend self-declaration is NOT sufficient. Transition to `"calibrated"` requires:
1. Measured ECE on Master on Vietnamese eval set ($n \ge 200$ per class).
2. ECE <= 0.15.
3. Provenance record in `results/tier2/`.

## Consequences

- **Positive**: Safe to deploy local models immediately for READ paths; fail-closed protection on all mutations.
- **Negative**: Mutations always incur Tier 3 evaluation overhead until calibration is complete.
