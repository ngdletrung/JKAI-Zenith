from core.utils.deep_routing import (
    goal_should_force_deep,
    goal_should_force_deep_for_analysis,
    effective_ingress_mode,
)


def test_error_trace_forces_deep():
    assert goal_should_force_deep("Traceback (most recent call last):\n  File planner.py")
    assert goal_should_force_deep("ai-brain báo lỗi import planner")


def test_greeting_not_deep():
    assert not goal_should_force_deep("xin chào")
    assert not goal_should_force_deep("/tusualoi")


def test_ingress_mode_upgrade():
    assert effective_ingress_mode("lỗi executor no output", "fast") == "deep"
    assert effective_ingress_mode("thời tiết hôm nay", "fast") == "fast"


def test_analysis_forces_deep():
    assert goal_should_force_deep_for_analysis("Phân tích harness so với JKAI")
    assert goal_should_force_deep("Phân tích harness so với JKAI")


def test_analysis_ingress_upgrade():
    assert effective_ingress_mode("báo cáo đánh giá kiến trúc", "fast") == "deep"


def test_scratch_project_forces_deep():
    from core.utils.project_workspace import detect_project_path, enrich_goal_for_project_workspace

    g = "hãy kiểm tra và xem lỗi scratch/projects/app_loi_di"
    assert detect_project_path(g) == "scratch/projects/app_loi_di"
    enriched, proj, mode = enrich_goal_for_project_workspace(g)
    assert proj == "scratch/projects/app_loi_di"
    assert mode == "audit"
    assert "JKAI PROJECT" in enriched
    assert goal_should_force_deep(g)
