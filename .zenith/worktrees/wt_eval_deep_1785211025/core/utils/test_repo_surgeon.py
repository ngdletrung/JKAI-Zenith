"""Tests for repo_surgeon (no LLM)."""
import tempfile
from pathlib import Path

from core.utils import repo_surgeon as rs


def test_is_allowed_repo_path():
    assert rs.is_allowed_repo_path("services/ai-brain/planner.py")
    assert rs.is_allowed_repo_path("core/utils/foo.py")
    assert not rs.is_allowed_repo_path(".env")
    assert not rs.is_allowed_repo_path("intelligence/registry_Map_skills.json")


def test_scan_syntax_detects_error():
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        bad = ws / "services" / "x"
        bad.mkdir(parents=True)
        (bad / "broken.py").write_text("def foo(\n", encoding="utf-8")
        errs = rs.scan_python_syntax(ws, max_files=50)
        assert any(e["path"].endswith("broken.py") for e in errs)


def test_candidate_and_promote():
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        rel = "core/utils/sample.py"
        prod = ws / rel.replace("/", "\\") if False else ws / "core" / "utils" / "sample.py"
        prod.parent.mkdir(parents=True, exist_ok=True)
        prod.write_text("x = 1\n", encoding="utf-8")
        cand, msg = rs.write_repo_candidate(rel, "x = 2\n", ws)
        assert msg == "OK"
        ok, pmsg = rs.promote_repo_candidate(cand, prod)
        assert ok
        assert prod.read_text(encoding="utf-8") == "x = 2\n"
