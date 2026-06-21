from core.kernel.project_agent_loop import _guard_path, _workspace_abs
from core.utils.project_workspace import (
    detect_workspace_target,
    enrich_goal_for_workspace_target,
    goal_forces_web_analysis_pipeline,
    goal_is_external_repo_url_analysis,
    goal_should_use_workspace_agent,
    is_allowed_workspace_rel,
    workspace_scope_exists,
    workspace_task_mode,
)


def test_scratch_project():
    g = "hãy kiểm tra và xem lỗi scratch/projects/app_loi_di"
    assert detect_workspace_target(g) == "scratch/projects/app_loi_di"


def test_services_path():
    g = "kiểm tra lỗi services/ai-brain/receptionist"
    t = detect_workspace_target(g)
    assert t and t.startswith("services/ai-brain")


def test_py_file_parent():
    g = "sửa lỗi core/utils/skill_deck_index.py"
    t = detect_workspace_target(g)
    assert t == "core/utils"


def test_guard_inside_scope():
    scope = "scratch/projects/app_loi_di"
    assert _guard_path(scope, "main.py")
    assert _guard_path(scope, "../services/ai-brain/main.py") is None


def test_allowed_under_workspace():
    assert is_allowed_workspace_rel("demo/my_app")
    assert not is_allowed_workspace_rel(".env")


def test_enrich():
    _, scope, mode = enrich_goal_for_workspace_target("xem lỗi demo/test")
    assert scope == "demo/test"
    assert mode == "audit"


def test_github_url_not_local_workspace():
    g = (
        "Phân tích https://github.com/revfactory/harness so với JKAI. "
        "Không sửa code."
    )
    assert detect_workspace_target(g) is None
    assert goal_is_external_repo_url_analysis(g) is True
    assert workspace_task_mode(g) == "audit"


def test_github_plus_local_path():
    g = "So sánh https://github.com/foo/bar với scratch/projects/app_loi_di"
    assert detect_workspace_target(g) == "scratch/projects/app_loi_di"
    assert goal_is_external_repo_url_analysis(g) is False


def test_web_readme_path_not_real_dir():
    assert not workspace_scope_exists("web/readme")


def test_github_harness_prompt_no_web_readme_workspace():
    g = (
        "Phân tích https://github.com/revfactory/harness so với kiến trúc JKAI. "
        "Chỉ đọc web/README — không sửa code JKAI, không list_dir workspace."
    )
    assert detect_workspace_target(g) is None
    assert goal_forces_web_analysis_pipeline(g) is True
    assert goal_should_use_workspace_agent(g) is False


def test_github_analysis_not_forced_web_only_by_default():
    g = "Phân tích https://github.com/revfactory/harness so với JKAI. Không sửa code."
    assert goal_forces_web_analysis_pipeline(g) is False
    assert goal_is_external_repo_url_analysis(g) is True


def test_vietnamese_prepositions_and_dossier_paths():
    # 1. Test Vietnamese prepositions with words that are not directories
    assert detect_workspace_target("Hãy kiểm tra lỗi trong bối cảnh này") is None
    assert detect_workspace_target("Tại sao hệ thống chạy chậm?") is None
    assert detect_workspace_target("Sửa lỗi trong lâu dài") is None

    # 2. Test Vietnamese prepositions with existing directories
    assert detect_workspace_target("Sửa lỗi trong core/utils") == "core/utils"
    assert detect_workspace_target("Xem thư mục core") == "core"

    # 3. Test dossier path (should be resolved by original goal, not enriched)
    # The detect_workspace_target should find None for a goal that doesn't mention a real directory,
    # even if it matches the general format.
    assert detect_workspace_target("Hãy rà soát lại code hệ thống xem bị nghẽn chổ nào ?") is None
