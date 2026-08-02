from core.utils.team_patterns import (
    PATTERN_FAN_OUT_IN,
    PATTERN_PIPELINE,
    PATTERN_PRODUCER_REVIEWER,
    annotate_blueprint_dict,
    infer_team_pattern,
    pattern_prompt_block,
)
from core.utils.deep_routing import goal_should_force_deep_for_analysis


def test_analysis_infers_producer_reviewer():
    g = "Phân tích https://github.com/revfactory/harness so với JKAI"
    assert infer_team_pattern(g).id == PATTERN_PRODUCER_REVIEWER


def test_parallel_infers_fan_out():
    assert infer_team_pattern("Thu thập song song từ nhiều nguồn web").id == PATTERN_FAN_OUT_IN


def test_greeting_pipeline():
    assert infer_team_pattern("xin chào").id == PATTERN_PIPELINE


def test_analysis_forces_deep():
    assert goal_should_force_deep_for_analysis("So sánh kiến trúc harness và JKAI")
    assert not goal_should_force_deep_for_analysis("/fast hello")


def test_annotate_sets_critic_flag():
    out = annotate_blueprint_dict({"rationale": "ok"}, infer_team_pattern("phân tích repo"))
    assert out["team_pattern"] == PATTERN_PRODUCER_REVIEWER
    assert out.get("recommended_critic") is True


def test_pattern_prompt_contains_id():
    block = pattern_prompt_block(infer_team_pattern("đánh giá harness"))
    assert PATTERN_PRODUCER_REVIEWER in block
    assert "TEAM_PATTERN_LAYER" in block
