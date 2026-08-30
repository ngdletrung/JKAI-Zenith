# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — DEMS v1.0: BELIEF GOVERNOR                       ║
│   Quản Trị Niềm Tin Vận Hành & Khắc Chế Ảo Giác Xác Định         │
╚══════════════════════════════════════════════════════════════════╝
Tuân thủ 7 Bất biến DEMS:
  I-DEMS-03: Claim != Belief
  I-DEMS-04: No Silent Resolution
  I-DEMS-05: Unknown Is Valid
  I-DEMS-06: LLM Has No Authority
"""

from __future__ import annotations
import time
import uuid
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple

from core.governor.claim_ledger import ClaimLedger, ClaimItem, ClaimStatus, ClaimScope, claim_ledger
from core.governor.evidence_debt import EvidenceDebt
from core.kernel.decision_ledger import decision_ledger

logger = logging.getLogger("JKAI.DEMS.BeliefGovernor")


@dataclass
class BeliefItem:
    belief_id: str
    subject: str
    predicate: str
    effective_object: Optional[str]
    scope: ClaimScope
    confidence: float
    status: ClaimStatus
    supporting_claims: List[str]
    conflicting_claims: List[str]
    evidence_debt: Optional[EvidenceDebt]
    updated_at: float = field(default_factory=time.time)


class BeliefGovernor:
    """
    🧠 Bộ Điều Hành Niềm Tin Vận Hành (Belief Governor)
    - Quản lý trạng thái niềm tin đang hoạt động (Operational State).
    - Phân xử giữa các Claim để tạo ra Belief có căn cứ xác thực.
    - Đánh giá nợ bằng chứng (Evidence Debt) và kích hoạt Next Best Action.
    """
    def __init__(self, ledger: Optional[ClaimLedger] = None):
        self.ledger = ledger or claim_ledger
        self.active_beliefs: Dict[Tuple[str, str, str], BeliefItem] = {}

    def resolve_belief(
        self,
        subject: str,
        predicate: str,
        scope: ClaimScope = ClaimScope.GENERAL,
        required_dimensions: Optional[List[str]] = None,
        mission_id: str = "sys"
    ) -> BeliefItem:
        """
        Phân xử niềm tin dựa trên toàn bộ Claims trong ClaimLedger.
        """
        subj_clean = subject.strip().lower()
        pred_clean = predicate.strip().lower()
        key = (subj_clean, pred_clean, scope.value if isinstance(scope, ClaimScope) else str(scope))

        claims = self.ledger.get_claims_by_predicate(subj_clean, pred_clean, scope)

        if not claims:
            # Không có bất kỳ Claim nào -> UNKNOWN (I-DEMS-05)
            debt = EvidenceDebt(
                mission_id=mission_id,
                missing_dimensions=[f"{subj_clean}.{pred_clean}"]
            )
            b = BeliefItem(
                belief_id=f"bel_{uuid.uuid4().hex[:12]}",
                subject=subj_clean,
                predicate=pred_clean,
                effective_object=None,
                scope=scope,
                confidence=0.0,
                status=ClaimStatus.UNKNOWN,
                supporting_claims=[],
                conflicting_claims=[],
                evidence_debt=debt,
                updated_at=time.time()
            )
            self.active_beliefs[key] = b
            return b

        active_claims = [c for c in claims if c.status == ClaimStatus.ACTIVE]
        contested_claims = [c for c in claims if c.status == ClaimStatus.CONTESTED]

        if contested_claims and not active_claims:
            # Xung đột ngang quyền -> CONTESTED (I-DEMS-04)
            debt = EvidenceDebt(
                mission_id=mission_id,
                contested_claims=[c.claim_id for c in contested_claims]
            )
            decision_ledger.record_decision(
                decision_type="BELIEF_CONTESTED",
                task_id=mission_id,
                input_summary=f"Conflicting claims for {subj_clean}.{pred_clean}",
                output_decision="CONTESTED",
                reason=f"{len(contested_claims)} claims of equal authority conflict without verification."
            )
            b = BeliefItem(
                belief_id=f"bel_{uuid.uuid4().hex[:12]}",
                subject=subj_clean,
                predicate=pred_clean,
                effective_object=None,
                scope=scope,
                confidence=0.5,
                status=ClaimStatus.CONTESTED,
                supporting_claims=[],
                conflicting_claims=[c.claim_id for c in contested_claims],
                evidence_debt=debt,
                updated_at=time.time()
            )
            self.active_beliefs[key] = b
            return b

        if active_claims:
            # Chọn active claim có điểm arbitration cao nhất
            best_claim = max(active_claims, key=lambda c: c.calculate_score(scope_target=scope))
            conf = best_claim.calculate_score(scope_target=scope)

            # Tính toán missing dimensions nếu có
            missing = []
            if required_dimensions:
                for dim in required_dimensions:
                    dim_claims = self.ledger.get_claims_by_predicate(subj_clean, dim.strip().lower(), scope)
                    if not any(c.status == ClaimStatus.ACTIVE for c in dim_claims):
                        missing.append(f"{subj_clean}.{dim}")

            debt = EvidenceDebt(mission_id=mission_id, missing_dimensions=missing) if missing else None

            b = BeliefItem(
                belief_id=f"bel_{uuid.uuid4().hex[:12]}",
                subject=subj_clean,
                predicate=pred_clean,
                effective_object=best_claim.object_val,
                scope=scope,
                confidence=conf,
                status=ClaimStatus.ACTIVE,
                supporting_claims=best_claim.evidence_refs,
                conflicting_claims=[c.claim_id for c in claims if c.status == ClaimStatus.SUPERSEDED],
                evidence_debt=debt,
                updated_at=time.time()
            )
            self.active_beliefs[key] = b
            return b

        # Fallback UNKNOWN
        debt = EvidenceDebt(mission_id=mission_id, missing_dimensions=[f"{subj_clean}.{pred_clean}"])
        b = BeliefItem(
            belief_id=f"bel_{uuid.uuid4().hex[:12]}",
            subject=subj_clean,
            predicate=pred_clean,
            effective_object=None,
            scope=scope,
            confidence=0.0,
            status=ClaimStatus.UNKNOWN,
            supporting_claims=[],
            conflicting_claims=[],
            evidence_debt=debt,
            updated_at=time.time()
        )
        self.active_beliefs[key] = b
        return b


belief_governor = BeliefGovernor()
