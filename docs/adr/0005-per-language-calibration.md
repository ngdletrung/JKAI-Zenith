# ADR 0005: Per-Language Calibration State & Evaluation Routing

## Status
Proposed

## Context

Empirical studies on multilingual foundation models and classifiers demonstrate that calibration varies substantially across languages (e.g. sweeping 51 languages reveals significant variance in Expected Calibration Error, from low error in high-resource training sets to elevated error in low-resource or code-switched contexts).

Treating calibration as a single scalar or global boolean (`calibration_state = "calibrated"`) across all languages is flawed: a model can be well-calibrated on English yet uncalibrated on Vietnamese or code-switched Vietnamese-English prompts.

## Decision

### D1. Per-language metadata schema

`BackendMetadata.calibration_state` evolves from a flat string into a language-keyed map:

    calibration_state: Mapping[str, str]   # BCP-47 -> "calibrated" | "uncalibrated" | "unknown"

`BackendMetadata.ece` evolves into a language-keyed map:

    ece: Mapping[str, Optional[float]]

The `"*"` wildcard key acts as the default fallback for languages without distinct calibration evaluations.

### D2. Integration with ADR 0003 Confidence Policy

`confidence_policy.decide()` accepts an optional `language: str = "*"` parameter:
1. Lookup: `calibration_state.get(language, calibration_state.get("*", "unknown"))`.
2. If resolved state is `"unknown"`, it is treated strictly as `"uncalibrated"` (fail-closed principle).

### D3. Operational consequence

- ADR 0003 safety policies apply per-language: READ actions in English may authorize under `θ_read = 0.70` if English is calibrated, while Vietnamese queries concurrently require `θ_read_uncal = 0.85` or escalate to Tier 3.
- Master host empirical evaluations must record separate calibration sets ($n \ge 200$ samples per language per primitive class).

## Non-goals

- Does NOT implement custom language detection algorithms within the adapter. Language detection is the responsibility of the local model router.
- Does NOT alter Gate 0 invariants or the Sovereign Zero-Cloud killswitch.
