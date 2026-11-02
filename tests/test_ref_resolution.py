# -*- coding: utf-8 -*-
"""
tests/test_ref_resolution.py
[UNIT TESTS FOR THE THREE-STATE REF RESOLVER]

Unreadable is not absent: a scan that could not read every candidate must
report INCOMPLETE, and a hash tie-break only ever selects among matches.
"""

import sys
import unittest

sys.path.insert(0, ".")

from services.ai_desktop.ref_resolution import (
    AMBIGUOUS,
    INCOMPLETE,
    MATCHED,
    REFUTED,
    resolve_identifier,
    select_by_element_hash,
)


def _node(name="", automation_id="", element_hash=None):
    return {
        "name": name,
        "automation_id": automation_id,
        "element_hash": element_hash,
    }


class TestResolutionVerdicts(unittest.TestCase):
    def test_01_matches_name_case_insensitively(self):
        result = resolve_identifier("line down", [_node(name="Line down", automation_id="x")])
        self.assertEqual(result.verdict, MATCHED)
        self.assertEqual(result.index, 0)

    def test_02_matches_automation_id(self):
        result = resolve_identifier("SCROLLDOWN", [_node(name="Line down", automation_id="ScrollDown")])
        self.assertEqual(result.verdict, MATCHED)
        self.assertEqual(result.index, 0)

    def test_03_no_match_with_full_read_is_refuted(self):
        result = resolve_identifier("Save", [_node(name="Open"), _node(name="Close")])
        self.assertEqual(result.verdict, REFUTED)
        self.assertIsNone(result.index)

    def test_04_no_match_with_unreadable_candidate_is_incomplete(self):
        result = resolve_identifier("Save", [_node(name="Open")], unreadable_indices=[1])
        self.assertEqual(result.verdict, INCOMPLETE)
        self.assertIn("could not be read", result.reason)

    def test_05_two_matches_are_ambiguous(self):
        result = resolve_identifier("Save", [_node(name="Save"), _node(name="save")])
        self.assertEqual(result.verdict, AMBIGUOUS)
        self.assertIsNone(result.index)

    def test_06_empty_identifier_is_refuted(self):
        self.assertEqual(resolve_identifier("   ", [_node(name="Save")]).verdict, REFUTED)

    def test_07_readable_match_wins_even_with_unreadable_candidates(self):
        result = resolve_identifier(
            "Save", [_node(name="Open"), _node(name="Save")], unreadable_indices=[2, 3]
        )
        self.assertEqual(result.verdict, MATCHED)
        self.assertEqual(result.index, 1)


class TestHashTieBreak(unittest.TestCase):
    def test_08_unique_stored_hash_selects_the_candidate(self):
        candidates = [
            _node(name="Save", element_hash="a"),
            _node(name="Save", element_hash="b"),
        ]
        result = resolve_identifier("Save", candidates, expected_element_hash="b")
        self.assertEqual(result.verdict, MATCHED)
        self.assertEqual(result.index, 1)

    def test_09_no_stored_hash_stays_ambiguous(self):
        candidates = [_node(name="Save", element_hash="a"), _node(name="Save", element_hash="b")]
        self.assertEqual(resolve_identifier("Save", candidates).verdict, AMBIGUOUS)

    def test_10_duplicate_stored_hashes_stay_ambiguous(self):
        candidates = [_node(name="Save", element_hash="a"), _node(name="Save", element_hash="a")]
        result = resolve_identifier("Save", candidates, expected_element_hash="a")
        self.assertEqual(result.verdict, AMBIGUOUS)

    def test_11_hash_never_turns_no_match_into_a_match(self):
        result = resolve_identifier(
            "Save", [_node(name="Open", element_hash="a")], expected_element_hash="a"
        )
        self.assertEqual(result.verdict, REFUTED)

    def test_12_hash_equal_to_none_does_not_match_unhashed_candidates(self):
        candidates = [_node(name="Save"), _node(name="Save")]
        self.assertEqual(
            resolve_identifier("Save", candidates, expected_element_hash="a").verdict,
            AMBIGUOUS,
        )


class TestSelectByElementHash(unittest.TestCase):
    def test_13_sole_hit_resolves(self):
        selection = select_by_element_hash(["a", "b", "c"], "b")
        self.assertTrue(selection.resolved)
        self.assertEqual(selection.index, 1)

    def test_14_missing_or_ambiguous_hash_does_not_resolve(self):
        self.assertFalse(select_by_element_hash(["a"], None).resolved)
        self.assertFalse(select_by_element_hash(["a", "a"], "a").resolved)
        self.assertFalse(select_by_element_hash(["a", "b"], "z").resolved)
        self.assertFalse(select_by_element_hash([], "a").resolved)


class TestMatchSerialization(unittest.TestCase):
    def test_15_as_dict_carries_verdict_and_index(self):
        payload = resolve_identifier("Save", [_node(name="Save")]).as_dict()
        self.assertEqual(payload, {"verdict": MATCHED, "index": 0, "reason": ""})

    def test_16_object_candidates_are_supported(self):
        class Node:
            def __init__(self, name, automation_id, element_hash):
                self.name = name
                self.automation_id = automation_id
                self.element_hash = element_hash

        result = resolve_identifier("Save", [Node("Save", "btnSave", "h")])
        self.assertEqual(result.verdict, MATCHED)
        self.assertEqual(result.index, 0)


if __name__ == "__main__":
    unittest.main()
