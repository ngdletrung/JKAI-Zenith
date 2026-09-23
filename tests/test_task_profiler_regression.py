# -*- coding: utf-8 -*-
"""
tests/test_task_profiler_regression.py
Regression test ensuring prior mission context packs (e.g. 'xin chào')
do not contaminate new action/coding goals into GREETING_SOCIAL reflex.
"""

import pytest
from core.os.cognition.task_profiler import profile_task, strip_context_pack


def test_strip_context_pack():
    raw_goal = (
        "<MISSION_CONTEXT_PACK>\n"
        "[PRIOR_CONTEXT]: User: xin chào! Agent: Chào bạn.\n"
        "</MISSION_CONTEXT_PACK>\n"
        "Hãy tạo file test.txt với nội dung Hello World"
    )
    stripped = strip_context_pack(raw_goal)
    assert "<MISSION_CONTEXT_PACK>" not in stripped
    assert "Hãy tạo file test.txt với nội dung Hello World" == stripped


def test_prior_greeting_context_does_not_hijack_coding_goal():
    contaminated_goal = (
        "<MISSION_CONTEXT_PACK>\n"
        "[LAST_INTERACTION]: User greeted 'xin chào bạn'\n"
        "</MISSION_CONTEXT_PACK>\n"
        "Hãy tạo file src/main.py và chạy thử nghiệm"
    )
    profile = profile_task(contaminated_goal)
    assert "GREETING_SOCIAL" not in profile.reason_codes
    assert profile.target_entity != "USER_INTERACTION_GREETING"


def test_pure_greeting_without_action_intent_is_reflex():
    pure_greeting = "Xin chào bạn, hôm nay thế nào?"
    profile = profile_task(pure_greeting)
    assert "GREETING_SOCIAL" in profile.reason_codes
