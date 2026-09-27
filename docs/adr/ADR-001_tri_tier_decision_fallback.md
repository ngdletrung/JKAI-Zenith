# ADR-001: Tri-Tier Decision Fallback Architecture

## Status
**ACCEPTED & SEALED** (Turn 75, Commit `6a2e5f4`)

## Context
JKAI Zenith requires low-latency, highly available decision-making primitives (`BOOLEAN`, `CHOICE`, `SCORE`) for task routing, fast-path verification, and risk assessment. 
Relying solely on external cloud LLMs violates the Zero-Egress Sovereign mandate and introduces unacceptable network latency and single-point-of-failure risks. Conversely, relying solely on heavy local LLMs (e.g., 4B–12B models) introduces GPU contention, high inference latency (hundreds of milliseconds to seconds), and potential token budget exhaustion.

## Decision
We implement a **Tri-Tier Decision Adapter** (`core/cognitive_bus/decision_substrate_adapter.py`):
1. **Tier 1 (Local Reflex Substrate)**: Non-autoregressive fast neural classification ($< 40\text{ms}$) running locally.
2. **Tier 2 (Local Model Reasoner)**: Structured inference via local Ollama LLM (Qwen/Gemma) when reflex confidence falls below threshold.
3. **Tier 3 (Deterministic Rule Fallback)**: In-process keyword & deterministic heuristic engine ($0.13\text{ms}$ P95 latency) ensuring guaranteed continuous operation even if all neural runtimes crash or exhaust resources.

## Consequences
- **Positive**: 
  - Complete operational continuity: The system never hard-crashes on decision failure; it cascades deterministically to Tier 3.
  - Sub-millisecond worst-case fallback latency.
- **Negative / Constraints**:
  - Tier 3 heuristics require strict maintenance and must be acknowledged as a rule baseline, not a generalized learner.
