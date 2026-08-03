"""
JKAI ZENITH — TEST SUITE: WORLD MODEL & PROMOTION GATE
tests/test_world_model_and_promotion_gate.py
"""

import pytest
from core.knowledge.world_model import WorldModel, EntityRelation
from core.governance.promotion_gate import PromotionGate, LearningProposal, PromotionResult


class TestWorldModelAndPromotionGate:

    def test_world_model_entity_state_and_relations(self):
        wm = WorldModel()
        wm.set_entity_state("Ollama", {"status": "degraded", "active_models": 2})

        rel = EntityRelation(
            source_entity="CapabilityBroker",
            relation_type="depends_on",
            target_entity="Ollama",
            confidence=0.95
        )
        wm.add_relation(rel)

        state = wm.get_entity_state("Ollama")
        assert state["status"] == "degraded"

        rels = wm.get_relations_for_entity("Ollama")
        assert len(rels) == 1
        assert rels[0].relation_type == "depends_on"

    def test_promotion_gate_validates_proposals_cleanly(self):
        gate = PromotionGate()

        # Valid proposal
        valid_prop = LearningProposal(
            proposal_id="p1",
            target_registry="skill",
            proposal_type="ADD_SKILL",
            payload={"name": "python_refactor"},
            confidence_score=0.90
        )
        res1 = gate.evaluate_proposal(valid_prop)
        assert res1.approved is True

        # Invalid proposal attempting to mutate MissionContract
        invalid_prop = LearningProposal(
            proposal_id="p2",
            target_registry="security",
            proposal_type="MUTATE_SECURITY",
            payload={"target": "MissionContract"},
            confidence_score=0.95
        )
        res2 = gate.evaluate_proposal(invalid_prop)
        assert res2.approved is False
        assert "Forbidden keyword" in res2.reason
