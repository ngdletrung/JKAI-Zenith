# ADR-002: Default-Deny Egress with Scoped Audit & Sovereign Isolation

## Status
**ACCEPTED & SEALED** (Turn 73, Commit `7eb6be7`, Revised Phase R1-R5)

## Context
JKAI Zenith is designed as a sovereign, evidence-governed AI Operating System. Uncontrolled dispatching of prompts, telemetry, or internal state variables to third-party commercial APIs poses severe risks:
1. Data leakage of enterprise credentials, network architecture, and private databases.
2. Fragility under internet outages, API rate limits, or external policy deprecation.
3. IP contamination: Embedding third-party brand names into source code or file structures damages project sovereignty and violates trademark boundaries.

## Decision
1. **Default-Deny Sovereign Policy (`SOVEREIGN-NO-CLOUD-KILLSWITCH`)**:
   Enforced via `JKAI_LOCAL_ONLY=1`. All unsolicited outbound traffic is blocked by default. External actuation (such as visual web browsing, search engines, or sovereign cloud discussion) is strictly scoped to explicit user directives and cryptographically audited.
2. **Brand & Trademark Independence ([.keyword.md](file:///d:/Docker/JKAI/.keyword.md))**:
   - Strictly prohibit third-party model branding (`jev`, `laya`, `typesafe`, `claude`, `openai`) as file, class, or module names.
   - Standardize internal JKAI naming: `Decision Engine`, `Reflex Substrate`, `TriTierDecisionAdapter`, `DecisionPrimitive`.
   - Grant a temporary shim-only deprecation grace period for `core/cognitive_bus/jev_substrate_adapter.py` until Phase 2 completion without internal logic.

## Consequences
- **Positive**: Strict on-premise operational sovereignty, default-deny egress protection, cryptographically audited external actuation, clean IP ownership.
- **Negative / Constraints**: Intelligence inference is provisioned on Master's physical hardware (Dual Xeon E5-2699 v4 + AMD Radeon RX 6600).
