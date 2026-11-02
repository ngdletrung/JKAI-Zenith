# -*- coding: utf-8 -*-
"""
services/ai_desktop/ref_resolution.py
[THREE-STATE REF RESOLUTION - D14]

Ported from agent-desktop (crates/windows/src/tree/resolve/resolve_match.rs;
Apache-2.0 - see NOTICE.md / CREDITS.md). agent-desktop measured that a ref
search which treats an unreadable candidate as "not a match" silently resolves
onto the wrong element. The port keeps that distinction:

  MATCHED     exactly one readable candidate matched.
  REFUTED     no readable candidate matched and every candidate was read.
  INCOMPLETE  no readable candidate matched, but at least one candidate could
              not be read. Never reported as "not found": a re-read may match.
  AMBIGUOUS   more than one readable candidate matched and no unique tie-break
              existed.

Ties are broken only by an exact stored element hash (the bounds-sensitive
hash captured at preflight). The hash never turns a refutation into a match;
it only picks among several evidence-equal candidates, and only when exactly
one of them carries the stored hash. Retry pacing stays with the caller: the
host worker re-runs a whole lease rather than looping inside one scan.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional, Sequence

MATCHED = "MATCHED"
REFUTED = "REFUTED"
INCOMPLETE = "INCOMPLETE"
AMBIGUOUS = "AMBIGUOUS"


@dataclass(frozen=True)
class CandidateMatch:
    verdict: str
    index: Optional[int] = None
    reason: str = ""

    @property
    def matched(self) -> bool:
        return self.verdict == MATCHED

    def as_dict(self) -> dict:
        return {"verdict": self.verdict, "index": self.index, "reason": self.reason}


@dataclass(frozen=True)
class Selection:
    """Bounds-hash tie-break outcome; `index` is set only for a unique hit."""

    index: Optional[int]

    @property
    def resolved(self) -> bool:
        return self.index is not None


def _identity(node: Any, name: str) -> str:
    if isinstance(node, dict):
        return str(node.get(name, "") or "")
    return str(getattr(node, name, "") or "")


def _hash_of(node: Any) -> Optional[str]:
    value = node.get("element_hash") if isinstance(node, dict) else getattr(node, "element_hash", None)
    return str(value) if value else None


def select_by_element_hash(
    candidate_hashes: Sequence[Optional[str]],
    expected_hash: Optional[str],
) -> Selection:
    """Pick the sole candidate whose hash equals `expected_hash`.

    Pure over the hashes so it is testable without live elements. No expected
    hash, no match, or more than one match stays ambiguous - guessing is never
    preferred over reporting ambiguity.
    """
    if not expected_hash:
        return Selection(None)
    hits = [index for index, value in enumerate(candidate_hashes) if value == expected_hash]
    if len(hits) == 1:
        return Selection(hits[0])
    return Selection(None)


def resolve_identifier(
    identifier: str,
    candidates: Sequence[Any],
    unreadable_indices: Iterable[int] = (),
    expected_element_hash: Optional[str] = None,
) -> CandidateMatch:
    """Resolve `identifier` (Name or AutomationId, case-insensitive).

    `candidates` are the readable elements in scan order; `unreadable_indices`
    counts elements whose identity could not be read at all. The returned
    index is a position in `candidates`.
    """
    key = str(identifier or "").strip().casefold()
    if not key:
        return CandidateMatch(REFUTED, reason="EMPTY_IDENTIFIER")

    matches = [
        index
        for index, node in enumerate(candidates)
        if _identity(node, "name").strip().casefold() == key
        or _identity(node, "automation_id").strip().casefold() == key
    ]

    if len(matches) == 1:
        return CandidateMatch(MATCHED, matches[0])

    if len(matches) > 1:
        if expected_element_hash:
            hashes = [_hash_of(candidates[index]) for index in matches]
            selection = select_by_element_hash(hashes, expected_element_hash)
            if selection.resolved:
                return CandidateMatch(MATCHED, matches[selection.index])
        return CandidateMatch(
            AMBIGUOUS,
            reason=f"{len(matches)} readable elements match {identifier!r}",
        )

    unreadable = sum(1 for _ in unreadable_indices)
    if unreadable:
        return CandidateMatch(
            INCOMPLETE,
            reason=f"no readable match and {unreadable} candidate(s) could not be read",
        )
    return CandidateMatch(REFUTED, reason="no candidate matches")
