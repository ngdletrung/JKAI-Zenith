from core.utils.skill_deck_run_guide import (
    build_skill_run_guide,
    goal_is_skill_run_help,
    resolve_deck_ids,
)


def test_run_help_detected():
    assert goal_is_skill_run_help("vậy tôi cần phải cung cấp gì để chạy skill nay")


def test_resolve_from_goal():
    assert "7001" in resolve_deck_ids("chạy skill #7001 cần gì", None)


def test_guide_hueic():
    text = build_skill_run_guide(["7001"])
    assert "file mẫu" in text.lower() or "File mẫu" in text
    assert "/run_skill #7001" in text
    assert "deepseek" not in text.lower() or "Tools API" in text
