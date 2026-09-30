# Tier 2 Backend Comparison Report

- Backend A: **fake-tier2** v1.0
  - calibration: calibrated, ECE measured: 0.77
- Backend B: **fake-tier2** v1.0
  - calibration: calibrated, ECE measured: 0.77

## Environment (A)
- host: AdminPC-MMO
- gpu: 32.0.21045.5002  AMD Radeon RX 6600
- git: 1c19ff5f826f (dirty=True)

## Environment (B)
- host: AdminPC-MMO
- gpu: 32.0.21045.5002  AMD Radeon RX 6600
- git: 1c19ff5f826f (dirty=True)

## Metrics
| Metric | Backend A | Backend B | Δ (B - A) |
|---|---|---|---|
| n_cases | 5 | 5 | - |
| n_errors | 0 | 0 | - |
| accuracy | 0.2000 | 0.2000 | +0.0000 |
| ECE | 0.7700 | 0.7700 | +0.0000 |
| p50 latency (ms) | 0.01 | 0.02 | +0.01 |
| p95 latency (ms) | 0.01 | 0.03 | +0.02 |
| p99 latency (ms) | 0.01 | 0.03 | +0.02 |

## Not Measured
_Anything not shown above was not measured. Do not infer._
