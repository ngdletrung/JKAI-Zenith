# ADR 0002: Tier 2 Schema Mapping (JKAI DecisionPrimitives ↔ Local Classifiers)

## Status
Accepted

## Context

JKAI's `TriTierDecisionAdapter` presents questions as canonical tuples:

    (DecisionPrimitive, question: str, options: Optional[List[str]])

Local multi-lingual reflex and classifier backends expect structured decision schemas:

    state: dict
    questions: {
        <question_key>: {
            "type": "choice" | "score" | "noul",
            "instructions": str,      # what to decide
            "criteria": {label: description}   # for choice
            # or "levels": [...]              # for score
        }
    }

The mapping is nontrivial because:
1. JKAI passes flat option labels; structured classifiers expect label -> description map.
2. JKAI's `DecisionPrimitive.BOOLEAN` aliases `NOUL`; classifiers name it `noul` or binary.
3. JKAI's `question` is a plain string; classifiers want `instructions` separate from the question key.
4. Confidence semantics differ: JKAI expects [0, 1]; uncalibrated raw models return un-temperature-scaled logits.

## Decision

### D1. Primitive mapping

| JKAI `DecisionPrimitive` | Classifier `type` |
|--------------------------|-------------------|
| `BOOLEAN`                | `noul`            |
| `CHOICE`                 | `choice`          |
| `SCORE`                  | `score`           |

`NOUL` in JKAI is a backward-compatibility alias of `BOOLEAN`. This ADR treats them as identical.

### D2. Question key vs instructions

- JKAI `question` string -> classifier `instructions` verbatim.
- Classifier `question_key` = SHA-256 of JKAI `question` (first 12 hex chars).
  This guarantees byte-identical keys across runs and languages.
- The reverse map (hash -> original question) is preserved in
  `TypedJudgementPacket.metadata["source_question"]` so callers never see the hash.

### D3. Options -> criteria

For `CHOICE`, JKAI passes `["billing", "technical", "other"]`.
Classifiers benefit from `{"billing": "...", "technical": "...", "other": "..."}`.

Two paths:

**Path A (label-as-description, lossy baseline):**
    `criteria = {label: label for label in options}`

Acceptable when labels are self-describing (e.g. `fast_path`, `deep_path`).

**Path B (caller-supplied descriptions):**
    `options = ["billing", "technical", "other"]`
    `option_descriptions = {`
        `"billing": "hóa đơn, thanh toán, hoàn tiền",`
        `"technical": "lỗi, sự cố, lỗi hệ thống",`
        `"other": "mọi thứ khác",`
    `}`

Supported via optional `descriptions` map. Backward compatible: `descriptions=None` -> Path A.
The adapter records which path was taken into `metadata["mapping_path"]`.

### D4. For `SCORE`

JKAI `options` = level labels (e.g. `["0", "1", "2", "3", "4"]`).
Classifier `levels` = list of level labels, same order. Mapping is 1:1, order-preserving.

Classifiers return a normalized probability distribution over levels. JKAI expects a scalar `result`.
Decision: `result` = argmax level index (as float). Full distribution preserved in `TypedJudgementPacket.distribution`.

### D5. Confidence handling

Uncalibrated local models ship WITHOUT fitted temperatures.
Therefore:
- Backend MUST set `metadata().calibration_state = "uncalibrated"`.
- Backend MUST set `metadata().ece = None` until measured on Master host.
- `TypedJudgementPacket.confidence` = raw top-1 probability, marked via `metadata["calibrated"] = False`.
- Kernel policy: uncalibrated confidence follows ADR 0003 fail-closed policy.

### D6. State mapping

JKAI `state` (dict) -> classifier `state` (dict) verbatim.
Fingerprint computed BEFORE passing to backend, using JKAI's own `StateSanitizer`, so byte-identical guarantees hold.

### D7. Language routing

Local router selects model checkpoint. JKAI MUST NOT duplicate language routing in the adapter.
Record routing metadata in `TypedJudgementPacket.metadata["routed_model"]`.

## Consequences

- **Positive**: byte-identical input guaranteed; hash-keyed questions prevent cross-language collisions; uncalibrated confidence is surfaced, not hidden.
- **Negative**: Path A (default) is lossy compared to rich descriptive criteria.
- **Neutral**: adds one clean indirection layer (question -> hash -> question).
