"""
JKAI ZENITH AI OS — RESOURCE RESERVATION ACCOUNTING & CAPABILITY GOVERNOR (PHASE 7)
File: core/os/cognition/resource_accounting.py

Implements:
- Resource Reservation Accounting (C1, D12, D32, P0-2)
- Capability Token Authority (D7, D18, C7, P0-8)
"""

from __future__ import annotations
import logging
import time
import uuid
from typing import Dict, List, Optional, Tuple

from core.os.cognition.deep_schemas import CapabilityType, CapabilityGrant, ActionIntent
from core.os.cognition.event_model import emit_contract_violation, event_store

logger = logging.getLogger("jkai.cognition.resource_accounting")


class ResourceReservationManager:
    """
    Manages GPU/VRAM & token reservation lifecycle:
    Available Capacity = Total - Committed - Reserved - SafetyMargin (P0-2, C1, D32).
    """

    def __init__(self, total_vram_mb: int = 8192, safety_margin_mb: int = 1024):
        self.total_vram_mb = total_vram_mb
        self.safety_margin_mb = safety_margin_mb
        self.committed_vram_mb = 0
        self.reserved_vram_mb = 0
        self._active_reservations: Dict[str, int] = {} # reservation_id -> mb

    @property
    def available_capacity_mb(self) -> int:
        return max(0, self.total_vram_mb - (self.committed_vram_mb + self.reserved_vram_mb + self.safety_margin_mb))

    def request_reservation(self, wave_id: str, requested_vram_mb: int, mission_id: str, trace_id: str) -> Tuple[bool, Optional[str]]:
        """C1: Checks capacity and transitions to RESERVED state."""
        if requested_vram_mb > self.available_capacity_mb:
            logger.warning("[ResourceAdmission] DENIED: Requested %d MB > Available %d MB",
                           requested_vram_mb, self.available_capacity_mb)
            emit_contract_violation(
                contract_id="C1",
                mission_id=mission_id,
                trace_id=trace_id,
                expected=f"requested_vram <= {self.available_capacity_mb} MB",
                actual=f"requested = {requested_vram_mb} MB",
                recovery_policy="PRUNE",
                enforcement_point="ResourceReservationManager.request_reservation"
            )
            return False, None

        res_id = f"res_{uuid.uuid4().hex[:8]}"
        self.reserved_vram_mb += requested_vram_mb
        self._active_reservations[res_id] = requested_vram_mb
        event_store.append(
            aggregate_id=mission_id,
            event_type="RESOURCE_RESERVED",
            payload={"reservation_id": res_id, "amount_mb": requested_vram_mb, "remaining_available": self.available_capacity_mb}
        )
        return True, res_id

    def release_reservation(self, res_id: str, mission_id: str) -> None:
        """Releases reserved VRAM back to the available pool."""
        if res_id in self._active_reservations:
            amount = self._active_reservations.pop(res_id)
            self.reserved_vram_mb = max(0, self.reserved_vram_mb - amount)
            event_store.append(
                aggregate_id=mission_id,
                event_type="RESOURCE_RELEASED",
                payload={"reservation_id": res_id, "released_mb": amount, "now_available": self.available_capacity_mb}
            )


class CapabilityTokenAuthority:
    """
    Issues and verifies scoped capability tokens for tool side-effects (D7, D18, C7).
    """

    def __init__(self):
        self._active_grants: Dict[str, CapabilityGrant] = {}

    def issue_grant(
        self,
        mission_id: str,
        node_id: str,
        capabilities: List[CapabilityType],
        resource_scope: str,
        duration_s: float = 60.0
    ) -> CapabilityGrant:
        grant_id = f"grant_{uuid.uuid4().hex[:8]}"
        token = f"tok_{uuid.uuid4().hex[:16]}"
        grant = CapabilityGrant(
            grant_id=grant_id,
            token=token,
            mission_id=mission_id,
            node_id=node_id,
            granted_capabilities=capabilities,
            resource_scope=resource_scope,
            expires_at=time.time() + duration_s,
            single_use=True
        )
        self._active_grants[token] = grant
        return grant

    def verify_and_consume(self, token: str, required_cap: CapabilityType, target: str) -> bool:
        """D18: Strict validation of capability token before tool execution."""
        if token not in self._active_grants:
            return False
        grant = self._active_grants[token]

        if grant.consumed or time.time() > grant.expires_at:
            return False
        if required_cap not in grant.granted_capabilities:
            return False

        grant.consumed = True
        return True


# Global Singletons
resource_manager = ResourceReservationManager()
capability_authority = CapabilityTokenAuthority()
