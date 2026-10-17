# -*- coding: utf-8 -*-
"""
JKAI Cloud Discuss Orchestrator (JKAI Discuss Protocol v1.0).
Coordinates the full end-to-end multi-agent dialectic debate,
enforcing security gates, consensus tracking, and compiling the 4-part Executive Briefing.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.security.trigger_parser import TriggerParser
from core.security.egress_gate import CentralizedEgressGate
from core.security.data_leak_guard import data_leak_guard
from core.security.egress_log import egress_ledger
from core.security.role_contract import RoleContractManager
from core.security.delphi_protocol import (
    ClaimState,
    ConsensusTracker,
    DelphiDebateManager,
)
from core.security.cloud_provider_client import (
    CloudProviderClient,
    cloud_provider_client,
)

logger = logging.getLogger("JKAI.Cognition.CloudDiscussOrchestrator")


@dataclass
class ExecutiveBriefing:
    mission_id: str
    status: str  # "COMPLETED", "SIMULATED_COMPLETED", "LOCAL_ONLY", "BLOCKED", "BLOCKED_MISSING_CREDENTIALS"
    participants: List[str]
    rounds_conducted: int
    total_tokens: int
    verified_findings: List[str] = field(default_factory=list)
    model_consensus: List[str] = field(default_factory=list)
    disagreements_and_hypotheses: List[str] = field(default_factory=list)
    learning_candidates: List[str] = field(default_factory=list)
    raw_transcript: List[Dict[str, Any]] = field(default_factory=list)
    refusal_reason: Optional[str] = None
    is_simulated: bool = False
    security_alert_banner: Optional[str] = None

    def render_markdown_report(self) -> str:
        """Renders the standard 4-part Executive Briefing for Master."""
        lines = [
            f"# 🏛️ BÁO CÁO THẢO LUẬN HỘI ĐỒNG AI (JKAI DISCUSS PROTOCOL v1.0)",
            f"> **Mission ID**: `{self.mission_id}` | **Trạng thái**: `{self.status}`",
            f"> **Thành viên tham gia**: {', '.join(self.participants)} | **Số vòng**: `{self.rounds_conducted}` | **Tổng Token**: `{self.total_tokens}`",
        ]
        if self.is_simulated:
            lines.append(
                "> ⚠️ **[CHẾ ĐỘ MÔ PHỎNG / SIMULATED]**: Phản hồi dưới đây là dữ liệu mô phỏng kiểm thử, không phải kết quả gọi API đám mây thật."
            )
        if self.security_alert_banner:
            lines.extend(["", self.security_alert_banner.strip()])

        lines.extend([
            "",
            "---",
            "",
            "### 1. 🟢 VERIFIED FINDINGS (Kết luận đã xác minh độc lập)",
        ])
        if self.verified_findings:
            for item in self.verified_findings:
                lines.append(f"- {item}")
        else:
            lines.append("*(Chưa có kết luận nào được xác minh độc lập hoàn toàn trong phiên này)*")

        lines.extend([
            "",
            "### 2. 🟡 MODEL CONSENSUS (Đồng thuận - Chưa chứng minh)",
        ])
        if self.model_consensus:
            for item in self.model_consensus:
                lines.append(f"- {item}")
        else:
            lines.append("*(Không có điểm đồng thuận chưa kiểm chứng)*")

        lines.extend([
            "",
            "### 3. 🔴 DISAGREEMENTS & HYPOTHESES (Bất đồng & Giả thuyết đa chiều)",
        ])
        if self.disagreements_and_hypotheses:
            for item in self.disagreements_and_hypotheses:
                lines.append(f"- {item}")
        else:
            lines.append("*(Không phát sinh bất đồng lớn giữa các chuyên gia)*")

        lines.extend([
            "",
            "### 4. 🧠 LEARNING CANDIDATES (Đề xuất hành động & Tri thức chờ nạp)",
        ])
        if self.learning_candidates:
            for item in self.learning_candidates:
                lines.append(f"- {item}")
        else:
            lines.append("*(Cần chạy bài kiểm thử thực tế trước khi đưa vào Memory)*")

        lines.append("\n---\n*Bảo vệ bởi JKAI Egress Gate & Hash-Chain Ledger* 🛡️")
        return "\n".join(lines)


class CloudDiscussOrchestrator:
    """
    Main controller executing dialectic debate missions.
    """

    def __init__(
        self,
        client: Optional[CloudProviderClient] = None,
        tracker: Optional[ConsensusTracker] = None,
    ):
        self.client = client or cloud_provider_client
        self.tracker = tracker or ConsensusTracker()
        self.debate_mgr = DelphiDebateManager(self.tracker)

    def execute_session(
        self,
        user_command: str,
        source: str = "master_cli",
        mission_id: str = "mission_discuss_live",
        allow_cloud: bool = True,
        simulate: bool = False,
    ) -> ExecutiveBriefing:
        parser = TriggerParser()
        gate = CentralizedEgressGate()

        # Step 1: Parse intent and enforce source isolation
        trigger_res = parser.parse(user_command, source=source)
        if not trigger_res.allowed:
            return ExecutiveBriefing(
                mission_id=mission_id,
                status="LOCAL_ONLY",
                participants=[],
                rounds_conducted=0,
                total_tokens=0,
                refusal_reason=trigger_res.reason,
            )

        # Determine target models
        models = list(trigger_res.models)
        if "default_group" in models:
            models = ["gemini", "deepseek"]  # Default 2-model council
        elif len(models) == 1:
            models.append("deepseek")  # Provide a dialectic sparring partner

        # Step 2: Egress Gate Inspection
        payload = {
            "mission_id": mission_id,
            "allow_cloud": allow_cloud,
            "mode": "discuss",
            "prompt": user_command,
            "target_models": models,
        }
        decision = gate.inspect_and_authorize(payload)
        if not decision.allowed:
            return ExecutiveBriefing(
                mission_id=mission_id,
                status="BLOCKED",
                participants=models,
                rounds_conducted=0,
                total_tokens=0,
                refusal_reason=decision.reason,
            )

        # Step 3: Multi-Round Dialectic Loop
        transcript = []
        total_tokens = 0
        current_round = 1
        max_rounds = min(self.debate_mgr.MAX_ROUNDS, 3)
        any_mock = False
        valid_response_count = 0
        provider_errors: List[str] = []

        while current_round <= max_rounds:
            # Re-verify Egress Gate at the start of each round (catches active security alerts or mosaic buildup)
            round_decision = gate.inspect_and_authorize(payload)
            if not round_decision.allowed:
                return ExecutiveBriefing(
                    mission_id=mission_id,
                    status="BLOCKED",
                    participants=models,
                    rounds_conducted=current_round - 1,
                    total_tokens=total_tokens,
                    raw_transcript=transcript,
                    refusal_reason=round_decision.reason,
                    is_simulated=any_mock,
                )

            order = self.debate_mgr.plan_round_speaker_order(models)
            round_responses = {}

            for model_name in order:
                system_prompt = RoleContractManager.build_neutral_contract(
                    role_name=f"Senior Specialist in {model_name.capitalize()}",
                    domain="System Architecture & Scalability",
                    task_objective=decision.sanitized_prompt,
                )

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": decision.sanitized_prompt},
                ]

                res = self.client.call_chat_completion(
                    provider=model_name,
                    messages=messages,
                    simulate=simulate,
                )

                if res.error:
                    provider_errors.append(f"{model_name}:{res.error}")
                    continue

                if res.is_mock:
                    any_mock = True

                actual_tokens = (
                    res.total_tokens
                    if res.total_tokens > 0
                    else max(1, len(decision.sanitized_prompt.split()) + len(res.content.split()))
                )
                total_tokens += actual_tokens

                # Record actual token count in cryptographic egress hash-chain ledger
                egress_ledger.record_egress(
                    mission_id=mission_id,
                    model=model_name,
                    sanitized_payload=decision.sanitized_prompt,
                    token_count=actual_tokens,
                )

                # Hard-block immediately if reverse prompt probing is detected (G1)
                alert = data_leak_guard.inspect_cloud_response(
                    res.content, model_name=model_name, mission_id=mission_id
                )
                if alert:
                    banner = data_leak_guard.format_master_alert_banner(alert)
                    logger.critical(
                        "Reverse solicitation hard-blocked from %s (mission=%s): %s",
                        model_name,
                        mission_id,
                        alert.threat_type,
                    )
                    return ExecutiveBriefing(
                        mission_id=mission_id,
                        status="BLOCKED",
                        participants=models,
                        rounds_conducted=current_round,
                        total_tokens=total_tokens,
                        raw_transcript=transcript,
                        refusal_reason=f"reverse_solicitation_blocked:{alert.threat_type}",
                        is_simulated=any_mock,
                        security_alert_banner=banner,
                    )

                valid_response_count += 1
                claim_id = f"claim_{mission_id}_r{current_round}_{model_name}"
                self.tracker.register_or_update_claim(
                    claim_id=claim_id,
                    statement=res.content[:200],
                    proposing_model=model_name,
                    has_independent_evidence=("[FACT]" in res.content and not res.is_mock),
                )

                round_responses[model_name] = res.content

            if not round_responses and provider_errors:
                return ExecutiveBriefing(
                    mission_id=mission_id,
                    status="BLOCKED_MISSING_CREDENTIALS",
                    participants=models,
                    rounds_conducted=0,
                    total_tokens=0,
                    disagreements_and_hypotheses=[f"Provider error: {err}" for err in provider_errors],
                    refusal_reason=";".join(provider_errors),
                    is_simulated=False,
                )

            transcript.append({
                "round": current_round,
                "order": order,
                "responses": round_responses,
            })

            if self.debate_mgr.check_should_stop(current_round):
                break
            current_round += 1

        # Step 4: Synthesize 4-Part Report
        verified = []
        consensus = []
        conflicts = []
        candidates = []

        for cid, claim in self.tracker.claims.items():
            if claim.state == ClaimState.VERIFIED:
                verified.append(f"[{', '.join(claim.supporting_models)}]: {claim.statement}")
            elif claim.state in (ClaimState.AGREED_UNVERIFIED, ClaimState.INSUFFICIENT_EVIDENCE):
                consensus.append(f"[{', '.join(claim.supporting_models)}]: {claim.statement}")
            elif claim.state == ClaimState.CONFLICTED:
                conflicts.append(f"Mâu thuẫn giữa {claim.supporting_models} và {claim.opposing_models}: {claim.statement}")

        if provider_errors:
            for err in provider_errors:
                conflicts.append(f"Cảnh báo kết nối nhà cung cấp: {err}")

        candidates.append("Tạo bài benchmark local kiểm định độ trễ và khả năng chịu tải trước khi nâng cấp skill.")

        return ExecutiveBriefing(
            mission_id=mission_id,
            status="COMPLETED",
            participants=models,
            rounds_conducted=current_round,
            total_tokens=total_tokens,
            verified_findings=verified,
            model_consensus=consensus,
            disagreements_and_hypotheses=conflicts,
            learning_candidates=candidates,
            raw_transcript=transcript,
            is_simulated=any_mock,
        )


cloud_discuss_orchestrator = CloudDiscussOrchestrator()
