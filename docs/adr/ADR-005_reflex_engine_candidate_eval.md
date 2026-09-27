# ADR-005: Local Reflex Engine Candidate Evaluation & Hardware Verification Options

## Status
**PROPOSED & UNDER REVIEW** (Turn 84: Empirical measurements recorded for 12M and 110M; 395M declared UNMEASURED; linear extrapolation strictly rejected)

## Context
JKAI Zenith seeks to transition from the current deterministic rule baseline (Tier 3 fallback) to an authentic local neural reflex engine (Tier 1) capable of non-autoregressive decision classification (`BOOLEAN`, `CHOICE`, `SCORE`).
Per Senior Red Team Auditor mandate (Turns 82 & 84), **no theoretical or literature-quoted latency/VRAM numbers may be accepted as architecture decisions. Linear extrapolation across architectures is explicitly rejected.** All decisions must be grounded in committed probe artifacts.

## Candidate Architectural Options for Tier 1

### Option A: ModernBERT-Large (Bidirectional Encoder, ~395M Parameters)
- **Description**: Use a ModernBERT-Large backbone with task-specific classification heads for non-autoregressive 1-pass decision scoring.
- **Hypothesized Advantages**: 8,192 token context window, RoPE, native handling of long JSON schema state.
- **Hardware Status**:
  - **Latency Status on Master Host**: **UNMEASURED**.
  - Host Python environment runs `torch 2.12.0+cpu` (4 threads).
  - Any theoretical claim of "<5ms" or linear extrapolation from 110M is strictly rejected per Turn 84 audit.
  - Requires loading real physical checkpoint on target accelerator (Vulkan / DirectML / ROCm) before entering consideration.

### Option B: Compact Distilled Encoder (e.g. 4-Layer / ~12M–33M Parameters)
- **Description**: Distill classification knowledge into a lightweight encoder specifically tuned for routing and risk assessment.
- **Measured Hardware Artifact** (`core/benchmark/probe_hardware_raw_output.json`):
  - **P50 Latency**: **16.90 ms** (PyTorch CPU, seq=64, $n=50$).
  - **P95 Latency**: **19.32 ms**.
  - **Process RSS**: **412.87 MB** (delta: $0.00\text{ MB}$).
  - Fully in-process on CPU, zero contention with Ollama GPU VRAM.
- **Constraints**: Shorter context window (e.g. 64–256 tokens), requires pre-sanitized compact state payloads via StateSanitizer 2.3a.

### Option C: Hybrid Fast-Path Speculative Probe (Quantized Linear/MLP Head over Frozen Embeddings)
- **Description**: Pre-compute state embeddings or use a frozen ultra-fast feature extractor paired with a lightweight quantized linear/MLP classifier head (<5M parameters).
- **Hypothesized Advantages**: Sub-millisecond CPU inference time, minimal memory overhead.
- **Hardware Concerns**: Lower generalization capacity for complex multi-intent tasks compared to full attention transformers.

## Decision Criteria & Evaluation Protocol
Before adopting any candidate option for Tier 1:
1. **Committed Physical Probe Artifacts**: All claims must be reproducible via committed scripts (`core/benchmark/probe_encoder_hardware.py`) and raw outputs (`core/benchmark/probe_hardware_raw_output.json`).
2. **Held-Out Evaluation Dataset**: Evaluate against an independent, adversarial held-out dataset ($n \ge 50$) not generated from keyword heuristic dictionaries.
3. **Calibrated Confidence**: Confidence must be measured via empirical calibration error (ECE) with explicit sample size $n$, confidence intervals, and environment seeds, or conformal prediction sets with coverage guarantees, rather than decorative ungrounded figures.

## Current Sealed Artifacts
- Probe script: `core/benchmark/probe_encoder_hardware.py`
- Raw measurement output: `core/benchmark/probe_hardware_raw_output.json`
