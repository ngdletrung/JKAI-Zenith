# ADR-004: State Sanitizer Contract & Memory Hygiene (v2.3a)

## Status
**ACCEPTED & SEALED** (Turn 73, Commit `7eb6be7`)

## Context
When passing application state to cognitive decision substrates, unstructured state dumps introduce severe vulnerabilities:
1. **Unbounded Memory Allocation (DoS)**: Ingesting megabytes of raw logs or state structures causes memory spikes and degrades latency.
2. **Hash Instability & Cache Invalidation**: Non-deterministic dictionary serialization yields divergent fingerprints for identical semantic states.
3. **Sensitive Credential Leakage**: Raw states may inadvertently contain API keys, database credentials, passwords, or bearer tokens.

## Decision
We enforce **StateSanitizer 2.3a** (`core/sanitizer/state_sanitizer.py`):
1. **Hard Upper Bound (`MAX_STATE_BYTES = 65,536` / 64KB)**:
   Any incoming state representation exceeding 64KB is strictly rejected or safely truncated before ingestion.
2. **Deterministic Canonical Fingerprint**:
   The state SHA-256 fingerprint is computed strictly from the `canonical_json` representation (sorted keys, compact delimiters `,` and `:`).
3. **Automated Secret Redaction & Redaction Report**:
   `sanitize_with_report()` automatically scrubs bearer tokens, private keys, API secrets, and sensitive credentials, producing an audit log of redacted entities per DecisionProvider specification.

## Consequences
- **Positive**: Strict bounded memory footprint, reliable caching, complete leak prevention.
- **Negative / Constraints**: Tasks requiring massive state payloads must pre-summarize or split state before querying the decision substrate.
