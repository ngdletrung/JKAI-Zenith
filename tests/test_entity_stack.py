# -*- coding: utf-8 -*-
"""
tests/test_entity_stack.py
JKAI DEMS v1.0 — Epistemic Entity Stack & Multi-Turn Coreference Test Suite.
"""

import pytest
from core.os.cognition.entity_stack import EntityStack, get_entity_stack, reset_entity_stack


class TestEntityStackSuite:

    def test_01_add_and_lifo_retrieval(self):
        """Vector 1: LIFO retrieval gets the most recent high-confidence entity."""
        reset_entity_stack()
        stack = get_entity_stack()
        stack.add_entity("Chiến sự Ukraine", category="WAR", confidence=0.9)
        stack.add_entity("Giá vàng SJC", category="ECONOMY", confidence=0.95)
        
        latest = stack.get_latest_entity()
        assert latest is not None
        assert latest.name == "Giá vàng SJC"

    def test_02_turn_expiry_decay(self):
        """Vector 2: Entities expire after MAX_TURNS_EXPIRY (3 turns) if not re-referenced."""
        reset_entity_stack()
        stack = get_entity_stack()
        stack.current_turn = 0
        stack.add_entity("Chủ đề A")
        stack.add_entity("Chủ đề B")
        
        # Advance 4 turns
        stack.current_turn = 4
        stack._clean_expired()
        
        assert len(stack.stack) == 0
        assert stack.get_latest_entity() is None

    def test_03_pronoun_coreference_resolution(self):
        """Vector 3: Resolves ambiguous pronouns ('nó', 'hậu quả của nó') to active entity."""
        reset_entity_stack()
        stack = get_entity_stack()
        stack.add_entity("Chiến sự Ukraine")
        
        raw_query = "Hậu quả của nó đối với kinh tế là gì?"
        resolved = stack.resolve_coreference(raw_query)
        
        assert "Chiến sự Ukraine" in resolved
        assert "của nó" not in resolved

    def test_04_confidence_filtering(self):
        """Vector 4: Ignores low-confidence noise entities."""
        reset_entity_stack()
        stack = get_entity_stack()
        stack.add_entity("Tin chính thống", confidence=0.9)
        stack.add_entity("Tin đồn mơ hồ", confidence=0.3)
        
        latest = stack.get_latest_entity(min_confidence=0.6)
        assert latest is not None
        assert latest.name == "Tin chính thống"

    def test_05_multi_pronoun_patterns(self):
        """Vector 5: Resolves multiple Vietnamese pronoun variations."""
        reset_entity_stack()
        stack = get_entity_stack()
        stack.add_entity("Nga")
        
        q1 = "Tình hình ở nước đó hiện nay ra sao?"
        res1 = stack.resolve_coreference(q1)
        assert "Nga" in res1
        assert "nước đó" not in res1
