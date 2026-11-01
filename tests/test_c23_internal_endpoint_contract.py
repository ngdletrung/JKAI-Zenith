# -*- coding: utf-8 -*-
"""
C23 — Internal endpoint contract (fail-first).

Audit findings, same failure class as C13/C19 (callers pointing at wiring that
does not exist):

- `receptionist/planner_gateway.py` POSTed to `http://ai-control-plane:8000/plan`.
  control-plane never exposed `/plan` (its planner lives in ai-brain), and the
  class was never called — the receptionist uses the in-process `Planner`.
- `SELF_HEALING_SENTINEL` probed `http://ai-executor:8000/health`; the compose
  network only resolves `ai-executor-1` / `ai-executor-2`, so the fallback could
  never report a healthy executor.
- The same map probed `http://mission-control:5173`; mission-control serves the
  API on 9998 and Vite on 9999 — nothing listens on 5173, so the audit table
  always showed mission-control as disconnected.
- `ai-telegram` carried an unused `DASHBOARD_URL` pointing at the dead 5173.

Guards here are static: they resolve internal service URLs (direct literals and
`var = os.getenv(..., "http://svc:port")` bases) and assert the targeted path is
actually defined by the target service.
"""

import os
import re
from functools import lru_cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

SERVICE_DIRS = {
    "ai-brain": ("services/ai-brain",),
    "ai-control-plane": ("services/ai-control-plane",),
    "ai-executor": ("services/ai-executor",),
    "ai-executor-1": ("services/ai-executor",),
    "ai-executor-2": ("services/ai-executor",),
    "ai-browser": ("services/ai-browser",),
    "rag-service": ("rag",),
    "mission-control": ("services/mission-control/backend",),
    "ai-telegram": ("services/ai-telegram",),
    "jkai-file-warden": ("services/zenith-file-warden",),
    "zenith-file-warden": ("services/zenith-file-warden",),
}

SCAN_ROOTS = ("services", "core", "rag", "intelligence", "scripts", "tools")

SKIP_PARTS = {
    "__pycache__", "node_modules", "AI_TEAM", "clean-repo", ".git",
    ".venv", "venv", "site-packages", "stable-diffusion",
}

HOSTS = "|".join(sorted(SERVICE_DIRS, key=len, reverse=True))
ROUTE = re.compile(r"""@(?:app|router)\.(?:get|post|put|delete|patch|route)\(\s*['"]([^'"]+)['"]""")
CALL = re.compile(rf"""https?://({HOSTS})(?::\d+)?(/[^'"\s)]*)?""")
ASSIGN = re.compile(
    rf"""(\w+)\s*=\s*(?:os\.getenv\(\s*['"][^'"]+['"]\s*,\s*)?['"]http://({HOSTS})(?::\d+)?"""
)
USAGE = re.compile(r"""(?:\{\s*(\w+)\s*\}|(\w+)\s*\+)\s*['"]?(/[A-Za-z0-9_\-./{}$]*)?['"]?""")


def _norm(path):
    path = path.rstrip("/") or "/"
    path = re.sub(r"\{[^}]*\}", "{}", path)
    return re.sub(r"<[^>]*>", "{}", path)


def _py_files():
    for root in SCAN_ROOTS:
        base = ROOT / root
        if not base.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_PARTS]
            for name in filenames:
                if name.endswith(".py"):
                    yield Path(dirpath) / name


@lru_cache(maxsize=1)
def _defined_routes():
    routes = {}
    for host, dirs in SERVICE_DIRS.items():
        paths = set()
        for rel in dirs:
            base = ROOT / rel
            for fp in base.rglob("*.py") if base.is_dir() else ():
                if any(p in fp.parts for p in SKIP_PARTS):
                    continue
                text = fp.read_text(encoding="utf-8", errors="ignore")
                paths.update(_norm(m) for m in ROUTE.findall(text))
        routes[host] = paths
    return routes


@lru_cache(maxsize=1)
def _calls():
    found = []
    for fp in _py_files():
        if fp.name == "ui_test.py":
            continue
        text = fp.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()

        bases = {}
        for line in lines:
            for m in ASSIGN.finditer(line):
                bases[m.group(1)] = m.group(2)

        rel = fp.relative_to(ROOT).as_posix()
        for lineno, line in enumerate(lines, 1):
            if "http" in line:
                for m in CALL.finditer(line):
                    host, path = m.group(1), m.group(2) or ""
                    if path:
                        found.append((rel, lineno, host, _norm(path), line.strip()))
            if bases and ("{" in line or "+" in line):
                for m in USAGE.finditer(line):
                    var, path = m.group(1) or m.group(2), m.group(3)
                    if var in bases and path:
                        found.append((rel, lineno, bases[var], _norm(path), line.strip()))
    return found


def _offenders(calls=None):
    routes = _defined_routes()
    bad = []
    for rel, lineno, host, path, line in (_calls() if calls is None else calls):
        known = routes[host]
        if "{}" in path:
            static = path.split("{}")[0] or "/"
            if not any(p.startswith(static) for p in known):
                bad.append((rel, lineno, host, path, "no route under prefix", line))
        elif path not in known:
            bad.append((rel, lineno, host, path, "route not defined", line))
    return bad


def test_scanner_flags_an_undefined_target():
    """Negative control: the guard must fail when a caller points at a missing route."""
    bad = _offenders([("fake.py", 1, "ai-control-plane", "/plan", 'post("http://ai-control-plane:8000/plan")')])
    assert [b[3] for b in bad] == ["/plan"]
    good = _offenders([("fake.py", 1, "ai-brain", "/warmup", 'post("http://ai-brain:8000/warmup")')])
    assert good == []


def test_every_internal_call_targets_a_defined_route():
    offenders = _offenders()
    detail = "\n".join(
        f"{rel}:{lineno} -> {host}{path} [{why}]\n    {line[:140]}"
        for rel, lineno, host, path, why, line in offenders
    )
    assert not offenders, f"Internal callers point at routes that do not exist:\n{detail}"


def test_no_reference_to_nonexistent_executor_host():
    pattern = re.compile(r"https?://ai-executor(?::\d+)?(?=[/\"'\s])")
    hits = []
    for fp in _py_files():
        for lineno, line in enumerate(fp.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            if pattern.search(line):
                hits.append(f"{fp.relative_to(ROOT).as_posix()}:{lineno}: {line.strip()[:120]}")
    assert not hits, (
        "Compose only defines ai-executor-1 / ai-executor-2; bare 'ai-executor' does not resolve:\n"
        + "\n".join(hits)
    )


def test_no_reference_to_dead_dashboard_port():
    hits = []
    for fp in _py_files():
        for lineno, line in enumerate(fp.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            if "mission-control:5173" in line:
                hits.append(f"{fp.relative_to(ROOT).as_posix()}:{lineno}: {line.strip()[:120]}")
    assert not hits, (
        "mission-control serves the API on 9998 and Vite on 9999; nothing listens on 5173:\n"
        + "\n".join(hits)
    )


def test_planner_gateway_is_gone():
    assert not (ROOT / "services" / "ai-brain" / "receptionist" / "planner_gateway.py").exists()
    container_src = (ROOT / "services" / "ai-brain" / "infrastructure" / "container.py").read_text(encoding="utf-8")
    assert "PlannerGateway" not in container_src
    assert "planner_gateway" not in container_src


def test_self_healing_probes_answerable_targets():
    src = (ROOT / "intelligence" / "skills" / "CORE" / "SELF_HEALING_SENTINEL" / "logic.py").read_text(encoding="utf-8")
    assert "mission-control:9998" in src
    assert "ai-executor-1:8000/health" in src
