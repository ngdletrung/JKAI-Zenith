# -*- coding: utf-8 -*-
"""
core/os/cognition/epistemic_auditor.py
JKAI DEMS v1.0 — Post-Mission Epistemic Auditor & Reality Comparator.

Compares final synthesized response against the Goal Contract and Raw Evidence.
Produces objective audit verdicts:
- FULFILLED (100% criteria satisfied)
- PARTIALLY_FULFILLED (Covered some topics, but missed primary domain)
- OFF_TOPIC (Dominated by excluded scopes, e.g. Horoscope instead of World News)
- EVIDENCE_INSUFFICIENT (Lacking grounding evidence)
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from core.os.cognition.goal_contract import GoalContract
from core.os.cognition.scope_classifier import scope_classifier


class AuditVerdict(str, Enum):
    FULFILLED = "FULFILLED"
    PARTIALLY_FULFILLED = "PARTIALLY_FULFILLED"
    OFF_TOPIC = "OFF_TOPIC"
    EVIDENCE_INSUFFICIENT = "EVIDENCE_INSUFFICIENT"


@dataclass(frozen=True)
class EpistemicAuditReport:
    verdict: AuditVerdict
    confidence: float
    satisfied_criteria: List[str]
    missing_criteria: List[str]
    detected_scopes: List[str]
    contains_excluded_noise: bool
    rationale: str


class EpistemicAuditor:
    """Post-Mission Epistemic Auditor (< 2ms)."""

    def audit(self, response_text: str, contract: GoalContract, raw_evidence_text: str = "") -> EpistemicAuditReport:
        if not response_text or len(response_text.strip()) < 10:
            return EpistemicAuditReport(
                verdict=AuditVerdict.EVIDENCE_INSUFFICIENT,
                confidence=0.0,
                satisfied_criteria=[],
                missing_criteria=contract.success_criteria,
                detected_scopes=[],
                contains_excluded_noise=False,
                rationale="Response text is empty or trivially short."
            )

        resp_lower = response_text.lower()
        classified = scope_classifier.classify(response_text)

        satisfied: List[str] = []
        missing: List[str] = []

        # 1. Check Date Anchor if required
        if "CURRENT_DATE_ANCHOR" in contract.success_criteria:
            if contract.required_time and (contract.required_time in response_text or "2026" in response_text):
                satisfied.append("CURRENT_DATE_ANCHOR")
            else:
                missing.append("CURRENT_DATE_ANCHOR")

        # 2. Check World Event Coverage
        if "WORLD_EVENT_COVERAGE" in contract.success_criteria:
            if classified.primary_scope in ("POLITICS", "GEOPOLITICS") or any(s in ("POLITICS", "GEOPOLITICS") for s in classified.secondary_scopes):
                satisfied.append("WORLD_EVENT_COVERAGE")
            elif any(w in resp_lower for w in ["quốc tế", "thế giới", "ukraine", "nga", "mỹ", "chiến sự", "ngoại giao"]):
                satisfied.append("WORLD_EVENT_COVERAGE")
            else:
                missing.append("WORLD_EVENT_COVERAGE")

        # 3. Check Exclude Noise Scopes
        has_noise = classified.is_noise or any(kw in resp_lower for kw in ["tử vi", "con giáp", "cung hoàng đạo", "bói toán"])
        if "EXCLUDE_NOISE_SCOPES" in contract.success_criteria:
            if not has_noise:
                satisfied.append("EXCLUDE_NOISE_SCOPES")
            else:
                missing.append("EXCLUDE_NOISE_SCOPES")

        # 4. Check Depth & Minimum Content Coverage (Dynamic from GoalContract)
        is_shallow = False
        if contract.is_realtime_news:
            lines = [l.strip() for l in response_text.splitlines() if len(l.strip()) > 15]
            if len(response_text.strip()) < contract.min_length or len(lines) < contract.min_paragraphs:
                is_shallow = True
                missing.append("MINIMUM_CONTENT_COVERAGE")
            else:
                satisfied.append("MINIMUM_CONTENT_COVERAGE")

        # 5. Determine Verdict
        if has_noise and "WORLD_EVENT_COVERAGE" in missing:
            verdict = AuditVerdict.OFF_TOPIC
            conf = 0.95
            rationale = "Response is dominated by excluded entertainment/horoscope noise rather than requested world events."
        elif is_shallow and "WORLD_EVENT_COVERAGE" in satisfied:
            verdict = AuditVerdict.PARTIALLY_FULFILLED
            conf = 0.65
            rationale = "Core topic mentioned but response is too shallow/terse (LOW_COVERAGE). Needs richer details."
        elif not missing:
            verdict = AuditVerdict.FULFILLED
            conf = 0.98
            rationale = "All objective acceptance criteria and depth requirements successfully verified."
        elif "WORLD_EVENT_COVERAGE" in satisfied:
            verdict = AuditVerdict.PARTIALLY_FULFILLED
            conf = 0.75
            rationale = f"Core topic fulfilled but minor criteria missing: {missing}"
        else:
            verdict = AuditVerdict.PARTIALLY_FULFILLED
            conf = 0.50
            rationale = f"Criteria unsatisfied: {missing}"

        detected_scopes = [classified.primary_scope] + classified.secondary_scopes

        return EpistemicAuditReport(
            verdict=verdict,
            confidence=conf,
            satisfied_criteria=satisfied,
            missing_criteria=missing,
            detected_scopes=detected_scopes,
            contains_excluded_noise=has_noise,
            rationale=rationale
        )


epistemic_auditor = EpistemicAuditor()
