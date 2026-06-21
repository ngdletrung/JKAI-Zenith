import asyncio

from core.os.intent_taxonomy import OSIntent, classify_os_intent, default_pipeline_for_intent
from core.os.request_orchestrator import orchestrate_request


def test_classify_analyze():
    g = "Phân tích https://github.com/foo/bar so với JKAI"
    assert classify_os_intent(g, {}) == OSIntent.ANALYZE


def test_classify_social():
    assert classify_os_intent("xin chào", {}) == OSIntent.SOCIAL


def test_orchestrate_no_early_crash():
    plan = asyncio.run(
        orchestrate_request(
            "xin chào",
            "t1",
            check_reflex=False,
        )
    )
    assert plan.goal
    assert plan.os_intent in ("social", "general")


def test_default_pipeline_analyze():
    from core.os.intent_taxonomy import capability_tags

    tags = capability_tags("phân tích repo", {"jkai_cloned_repos": ["scratch/projects/x-ref"]})
    assert default_pipeline_for_intent(OSIntent.ANALYZE, tags) == "deep_full"
