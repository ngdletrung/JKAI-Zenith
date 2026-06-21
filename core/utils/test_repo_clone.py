from core.utils.project_workspace import goal_forces_web_analysis_pipeline
from core.utils.repo_clone import (
    alias_from_url,
    clone_rel_path,
    extract_git_remote_urls,
    goal_should_clone_external_repo,
)


def test_extract_github_url():
    g = "Phân tích https://github.com/revfactory/harness so với JKAI"
    urls = extract_git_remote_urls(g)
    assert urls and "revfactory" in urls[0]


def test_clone_alias():
    assert alias_from_url("https://github.com/revfactory/harness") == "revfactory-harness-ref"
    assert clone_rel_path("https://github.com/revfactory/harness") == "scratch/projects/revfactory-harness-ref"


def test_default_analysis_wants_clone():
    g = "Phân tích https://github.com/revfactory/harness so với JKAI. Không sửa code."
    assert goal_should_clone_external_repo(g)
    assert not goal_forces_web_analysis_pipeline(g)


def test_web_only_blocks_clone():
    g = (
        "Phân tích https://github.com/revfactory/harness. "
        "Chỉ đọc web/README — không list_dir workspace."
    )
    assert goal_forces_web_analysis_pipeline(g)
    assert not goal_should_clone_external_repo(g)
