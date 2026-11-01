# -*- coding: utf-8 -*-
"""
C30 — Sweep of "reports success without proof" defaults.

C29 fixed one fabricated verdict. The same failure class lived in two more places:

1. ai-control-plane could not reach the critic -> it returned
   {"approved": True, "feedback": "Critic error, auto-approved."} and the plan
   was approved *because* the quality gate was down.
2. MaintenanceRunner.execute_maintenance_task logged "Executing ... on ..." and
   returned success=True while never touching the file.

Contract:
1. No component may fail open: an unreachable gate must not return a pass.
2. A permission gate must say it authorised, not that it executed.
"""

import asyncio
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROL_PLANE = ROOT / "services" / "ai-control-plane"
ROUTER = CONTROL_PLANE / "router.py"
RUNNER = ROOT / "core" / "recovery" / "maintenance_runner.py"


def test_router_never_approves_on_failure(monkeypatch):
    if str(CONTROL_PLANE) not in sys.path:
        sys.path.insert(0, str(CONTROL_PLANE))
    from router import ServiceRouter

    router = ServiceRouter()

    async def brain_down(*args, **kwargs):
        raise RuntimeError("brain unreachable")

    monkeypatch.setattr(router, "_post_with_retry", brain_down)
    result = asyncio.run(router.route_to_brain_critic({"goal": "rename file"}))

    assert result["approved"] is False
    assert "error" in result["feedback"].lower()


def test_router_5xx_fallback_is_fail_closed():
    if str(CONTROL_PLANE) not in sys.path:
        sys.path.insert(0, str(CONTROL_PLANE))
    from router import ServiceRouter

    router = ServiceRouter()

    class Boom:
        status_code = 503
        text = "service unavailable"

    fallback = router._safe_json(Boom(), {"approved": False, "feedback": "Critic unavailable; plan not approved."})
    assert fallback["approved"] is False

    source = ROUTER.read_text(encoding="utf-8")
    assert '"approved": True' not in source, "the router must not contain a fail-open approval"


def test_maintenance_runner_authorizes_instead_of_claiming_execution():
    spec = importlib.util.spec_from_file_location("c30_maintenance_runner", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    runner = module.MaintenanceRunner
    assert not hasattr(runner, "execute_maintenance_task"), "the method name promised execution it never did"

    result = runner.authorize_maintenance_task("rotate_audit_logs", "Thao luan AI/dispatch_history.log")
    assert result["authorized"] is True
    assert result["token_verified"] is True
    assert "success" not in result

    source = RUNNER.read_text(encoding="utf-8")
    assert "Executing" not in source
