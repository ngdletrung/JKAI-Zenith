# ADR-002: Zero-Egress Sovereign Isolation & Brand Independence

## Status
**ACCEPTED & SEALED** (Turn 73, Commit `7eb6be7`)

## Context
JKAI Zenith is designed as a sovereign, self-contained AI Operating System. Sending prompts, telemetry, or internal state variables to third-party commercial APIs (OpenAI, Anthropic, Google Cloud, TypeSafe) poses severe risks:
1. Data leakage of enterprise credentials, network architecture, and private databases.
2. Fragility under internet outages, API rate limits, or external policy deprecation.
3. IP contamination: Embedding third-party brand names into source code or file structures damages project sovereignty and violates trademark boundaries.

## Decision
1. **Sovereign Cloud Killswitch (`SOVEREIGN-NO-CLOUD-KILLSWITCH`)**:
   Enforced in `core/utils/engine.py` via `JKAI_LOCAL_ONLY=1`. Any attempt to dispatch prompts to cloud endpoints is blocked unconditionally and redirected to local Ollama/in-process models.
2. **Brand & Trademark Independence ([.keyword.md](file:///d:/Docker/JKAI/.keyword.md))**:
   - Strictly prohibit third-party model branding (`jev`, `laya`, `typesafe`, `claude`, `openai`) as file, class, or module names.
   - Standardize internal JKAI naming: `Decision Engine`, `Reflex Substrate`, `TriTierDecisionAdapter`, `DecisionPrimitive`.
   - Grant a temporary shim-only deprecation grace period for `core/cognitive_bus/jev_substrate_adapter.py` until Phase 2 completion without internal logic.

## Consequences
- **Positive**: 100% offline operational sovereignty, zero network egress leakage, clean IP ownership.
- **Negative / Constraints**: All intelligence capabilities must be provisioned on Master's physical hardware (Dual Xeon E5-2699 v4 + AMD Radeon RX 6600).
