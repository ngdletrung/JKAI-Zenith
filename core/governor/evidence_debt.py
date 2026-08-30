# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — DEMS v1.0: EVIDENCE DEBT TRACKER                 ║
│   Theo Dõi Nợ Bằng Chứng & Điều Hướng Next Best Cognitive Action │
╚══════════════════════════════════════════════════════════════════╝
Tuân thủ 7 Bất biến DEMS:
  I-DEMS-05: Unknown Is Valid (Thiếu bằng chứng -> UNKNOWN -> Sinh Evidence Debt)
  I-DEMS-06: LLM Has No Authority (Không cho phép LLM bịa/đoán khi nợ bằng chứng > 0)
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

logger = logging.getLogger("JKAI.DEMS.EvidenceDebt")


@dataclass
class EvidenceDebt:
    mission_id: str
    missing_dimensions: List[str] = field(default_factory=list)
    contested_claims: List[str] = field(default_factory=list)
    stale_evidence: List[str] = field(default_factory=list)
    unverified_claims: List[str] = field(default_factory=list)

    @property
    def total_debt_count(self) -> int:
        return (
            len(self.missing_dimensions) +
            len(self.contested_claims) +
            len(self.stale_evidence) +
            len(self.unverified_claims)
        )

    @property
    def has_debt(self) -> bool:
        return self.total_debt_count > 0

    def recommend_next_action(self) -> Optional[Dict[str, Any]]:
        """
        Đưa ra khuyến nghị hành động nhận thức tiếp theo (Next Best Action)
        cho FAST/DEEP Controller dựa trên tính chất của nợ bằng chứng.
        """
        if self.contested_claims:
            return {
                "action": "CROSS_VERIFY",
                "target": self.contested_claims[0],
                "reason": "Resolving contested claim with independent observation"
            }
        if self.missing_dimensions:
            return {
                "action": "RECON_PROBE",
                "target": self.missing_dimensions[0],
                "reason": f"Gathering missing factual dimension: {self.missing_dimensions[0]}"
            }
        if self.unverified_claims:
            return {
                "action": "VERIFY_SCHEMA",
                "target": self.unverified_claims[0],
                "reason": "Executing deterministic readback verification"
            }
        if self.stale_evidence:
            return {
                "action": "REFRESH_EVIDENCE",
                "target": self.stale_evidence[0],
                "reason": "Refreshing stale observational evidence"
            }
        return None
