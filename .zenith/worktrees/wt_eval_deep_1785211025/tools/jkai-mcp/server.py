#!/usr/bin/env python3
"""
JKAI MCP Server — bridge Cursor / VS Code agents to JKAI Docker stack.

Transport: stdio (default for Cursor MCP).
Env:
  JKAI_BRAIN_URL          default http://localhost:8001
  JKAI_CONTROL_PLANE_URL  default http://localhost:7000
  JKAI_MCP_TIMEOUT        seconds, default 600
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "JKAI",
    instructions=(
        "JKAI Zenith AI OS. Use jkai_ping first if unsure connectivity. "
        "jkai_chat for direct answers (receptionist / AI OS kernel). "
        "jkai_submit_task for full mission queue (async, Mission Control logs). "
        "Include file paths and constraints in goal (read-only, scratch/projects, etc.)."
    ),
)


def _brain_url() -> str:
    return os.getenv("JKAI_BRAIN_URL", "http://localhost:8001").rstrip("/")


def _control_plane_url() -> str:
    return os.getenv("JKAI_CONTROL_PLANE_URL", "http://localhost:7000").rstrip("/")


def _timeout() -> float:
    try:
        return float(os.getenv("JKAI_MCP_TIMEOUT", "600"))
    except ValueError:
        return 600.0


def _new_task_id(prefix: str = "mcp") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


async def _get_health(client: httpx.AsyncClient, base: str) -> dict:
    try:
        r = await client.get(f"{base}/health", timeout=10.0)
        return {"ok": r.status_code == 200, "status": r.status_code, "body": r.text[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
async def jkai_ping() -> str:
    """Check JKAI ai-brain and ai-control-plane reachability from this machine."""
    async with httpx.AsyncClient() as client:
        brain = await _get_health(client, _brain_url())
        cp = await _get_health(client, _control_plane_url())
    payload = {
        "brain_url": _brain_url(),
        "control_plane_url": _control_plane_url(),
        "brain": brain,
        "control_plane": cp,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


@mcp.tool()
async def jkai_chat(
    goal: str,
    mode: str = "auto",
    mission_id: Optional[str] = None,
    parent_mission_id: Optional[str] = None,
    history_json: Optional[str] = None,
) -> str:
    """
    Send a message to JKAI receptionist (AI OS kernel). Best for Q&A, analysis, planning.

    goal: Full instruction (Vietnamese or English). Include paths like services/ai-brain/planner.py.
    mode: auto | fast | deep
    mission_id: Optional mission bucket for context pack (e.g. vscode_myproject).
    parent_mission_id: Optional prior mission to continue context.
    history_json: Optional JSON array of {role, content} messages.
    """
    if not goal or not goal.strip():
        return json.dumps({"status": "error", "error": "goal is required"}, ensure_ascii=False)

    history = []
    if history_json:
        try:
            history = json.loads(history_json)
            if not isinstance(history, list):
                history = []
        except json.JSONDecodeError as e:
            return json.dumps(
                {"status": "error", "error": f"invalid history_json: {e}"},
                ensure_ascii=False,
            )

    task_id = _new_task_id("chat")
    body = {
        "goal": goal.strip(),
        "task_id": task_id,
        "mode": (mode or "auto").lower(),
        "history": history,
    }
    if mission_id:
        body["mission_id"] = mission_id
    if parent_mission_id:
        body["parent_mission_id"] = parent_mission_id

    url = f"{_brain_url()}/receptionist"
    try:
        async with httpx.AsyncClient(timeout=_timeout()) as client:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        return json.dumps(
            {
                "status": "error",
                "error": f"timeout after {_timeout()}s — try mode=fast or shorter goal",
                "task_id": task_id,
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return json.dumps(
            {"status": "error", "error": str(e), "url": url, "task_id": task_id},
            ensure_ascii=False,
            indent=2,
        )

    answer = data.get("answer", "")
    if isinstance(answer, dict):
        answer = answer.get("content") or json.dumps(answer, ensure_ascii=False)

    out = {
        "status": data.get("status", "ok"),
        "task_id": data.get("task_id", task_id),
        "answer": answer,
        "pipeline": data.get("pipeline"),
        "mode": data.get("mode"),
    }
    return json.dumps(out, ensure_ascii=False, indent=2)


@mcp.tool()
async def jkai_submit_task(
    goal: str,
    mode: str = "auto",
    mission_id: str = "vscode",
    source: str = "MCP",
) -> str:
    """
    Enqueue a full JKAI mission (control-plane). Async — watch Mission Control / Redis logs.

    Use for long DEEP jobs. For quick chat prefer jkai_chat.
    """
    if not goal or not goal.strip():
        return json.dumps({"status": "error", "error": "goal is required"}, ensure_ascii=False)

    task_id = f"{mission_id}_{uuid.uuid4().hex[:8]}"
    trace_id = f"trace_{uuid.uuid4().hex[:10]}"
    body = {
        "goal": goal.strip(),
        "task_id": task_id,
        "trace_id": trace_id,
        "mode": (mode or "auto").lower(),
        "mission_id": mission_id,
        "source": source,
    }
    url = f"{_control_plane_url()}/api/submit_task"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        return json.dumps(
            {"status": "error", "error": str(e), "url": url},
            ensure_ascii=False,
            indent=2,
        )

    return json.dumps(
        {
            "status": data.get("status", "queued"),
            "task_id": data.get("task_id", task_id),
            "trace_id": trace_id,
            "answer": data.get("answer"),
            "note": "Mission queued — open Mission Control for live logs if not inline answer.",
            "raw": data,
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
async def jkai_plan(
    goal: str,
    mode: str = "deep",
) -> str:
    """
    Request a strategic blueprint only (planner endpoint), without full execution.
    """
    if not goal or not goal.strip():
        return json.dumps({"status": "error", "error": "goal is required"}, ensure_ascii=False)

    task_id = _new_task_id("plan")
    body = {"goal": goal.strip(), "task_id": task_id, "mode": mode}
    url = f"{_brain_url()}/plan"
    try:
        async with httpx.AsyncClient(timeout=_timeout()) as client:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e), "url": url}, ensure_ascii=False)

    return json.dumps(
        {"status": "ok", "task_id": task_id, "plan": data},
        ensure_ascii=False,
        indent=2,
    )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
