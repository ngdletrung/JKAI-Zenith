# ADR 0001: Sovereign Tier 2 Backend Interface & Pluggability

## Status
Accepted

## Context
`TriTierDecisionAdapter` previously declared three tiers, but Tier 2 was delegating to the same internal rule heuristic as Tier 3 without an active neural substrate. The documentation claimed Tier 2 local reasoning, but in code, no modular backend existed.

Furthermore, per JKAI IP Honesty Policy (`.keywork.md`), all architecture, class names, and interfaces must remain strictly sovereign and independent without borrowing third-party model brand names.

## Decision
1. Introduce a strict `Tier2Backend` Protocol in `core/cognitive_bus/tier2_backend.py`.
2. Centralize backend selection and discovery in `core/cognitive_bus/backends/__init__.py` via `ACTIVE_BACKEND` and a factory registry.
3. Swapping a local decision model (Fake test-double, Local Ollama, Sovereign Reflex Classifier) requires only updating `ACTIVE_BACKEND` or injecting into `TriTierDecisionAdapter(tier2_backend=...)`.
4. Defensively validate backend output (`_validate_tier2_output`) prior to any downstream mission authorization.
5. Zero external cloud egress: all Tier 2 backends are strictly restricted to localhost or in-process.

## Consequences
- **Positive**:
  - Truthful separation: Tier 2 is a distinct, pluggable interface with real measured latencies and probability distributions.
  - Testability: Unit and integration tests can exercise all edge cases (timeouts, circuit breaker, distribution sum violations) via `FakeTier2Backend`.
  - Zero lock-in: Swapping model implementations does not require changing core kernel logic.
- **Negative**:
  - Adds one level of indirection between adapter and backend implementation.
- **Neutral**:
  - Sovereign classifier weights can be dropped in when calibration dataset reaches target volume.
