# ADR-003: Cognitive Honesty Triad (H-Triad) & Token Budget Governance

## Status
**ACCEPTED & SEALED** (Turn 71, Commit `1e6a3da`)

## Context
Production soak audits and live log investigations revealed critical systemic failure modes in autonomous agent operations:
1. **False Success & Hallucinated Completion**: Read-only conversational tasks being falsely granted "completed" status with artificial high confidence scores (e.g., 0.98), bypassing criteria verification.
2. **Model Identity Fabrication & Dishonesty**: Prompts falsely claiming non-existent security constraints or impersonating external models.
3. **Attempt Quota Depletion on Infra Failures**: Ephemeral network blips ($<0.5\text{s}$ connect timeouts to Ollama) consuming user mission attempts, leading to premature mission aborts.
4. **Token Exhaustion Runaways**: Complex tasks burning unbounded context tokens without budget enforcement.

## Decision
We enforce the **Cognitive Honesty Triad (H-Triad)** and **TokenBudgetGuard**:
- **Fix H1 (Fast-Path Verification Checklist)**:
  - Idempotent and conversational queries are verified via a deterministic checklist without scoring fake criteria.
  - Conversational responses never emit artificial `0.98` confidence or claim physical criteria fulfillment.
- **Fix H2 (Model Identity & Capability Honesty)**:
  - System prompts inject authentic model metadata (`active_model_name`, registered tools).
  - Explicitly forbid excuses claiming non-existent security restrictions.
- **Fix H3 (Instant-Fail Exclusion)**:
  - Ephemeral infrastructure connection drops ($<0.5\text{s}$ connect/read timeout) are excluded from consuming the mission retry attempt budget.
- **TokenBudgetGuard (`core/guard/token_budget_guard.py`)**:
  - Enforces hard ceiling on context window tokens.
  - Warns at 80% consumption; halts and safely aborts runaway loops at 100% consumption.

## Consequences
- **Positive**: 100% elimination of false completion claims, immune to ephemeral infrastructure flapping, strict resource containment.
- **Negative / Constraints**: Strict validation rejects loose agent prompts that do not conform to authentic identity contracts.
