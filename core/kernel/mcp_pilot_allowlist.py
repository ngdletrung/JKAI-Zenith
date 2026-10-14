# -*- coding: utf-8 -*-
"""
core/kernel/mcp_pilot_allowlist.py
==================================
Slice 2.3 — Local MCP Pilot Allowlist & Endpoint Governor.

Đảm bảo mọi lệnh gọi MCP trong chế độ Pilot:
1. Chỉ cho phép kết nối tới các máy chủ MCP nằm trong `allowed_servers` (`DEFAULT_ALLOWED_MCP_SERVERS`).
2. Chỉ cho phép thực thi các công cụ MCP nằm trong `allowed_tools` (`DEFAULT_ALLOWED_MCP_TOOLS`).
3. Khi `local_only=True` (hoặc `LOCAL_ONLY_MODE=1`), chặn tuyệt đối các endpoint MCP không phải loopback
   (`localhost`, `127.0.0.1`, `::1`, `stdio://`), trả về cấu trúc từ chối minh bạch gắn nhãn
   `stage_attribution="CONTROLLER_GATE"`.
"""

from __future__ import annotations

import os
from typing import Any, Dict, FrozenSet, Iterable, Optional
from urllib.parse import urlparse

from core.utils.repo_map import StageAttribution


DEFAULT_ALLOWED_MCP_SERVERS: FrozenSet[str] = frozenset(
    {
        "jkai",
        "filesystem_local",
        "git_local",
        "sqlite_local",
    }
)

DEFAULT_ALLOWED_MCP_TOOLS: FrozenSet[str] = frozenset(
    {
        "jkai_ping",
        "jkai_chat",
        "jkai_submit_task",
        "jkai_plan",
        "jkai_repo_map",
        "read_file",
        "list_dir",
        "git_status",
        "git_diff",
    }
)

_LOOPBACK_HOSTS: FrozenSet[str] = frozenset({"localhost", "127.0.0.1", "::1", "[::1]"})


class LocalMCPPilotGovernor:
    """Bộ kiểm soát an ninh & allowlist cho Local MCP Pilot (Slice 2.3)."""

    def __init__(
        self,
        allowed_servers: Optional[Iterable[str]] = None,
        allowed_tools: Optional[Iterable[str]] = None,
    ) -> None:
        env_servers = os.getenv("JKAI_MCP_SERVER_ALLOWLIST", "").strip()
        if allowed_servers is not None:
            self.allowed_servers = frozenset(str(s).strip().lower() for s in allowed_servers if str(s).strip())
        elif env_servers:
            self.allowed_servers = frozenset(s.strip().lower() for s in env_servers.split(",") if s.strip())
        else:
            self.allowed_servers = DEFAULT_ALLOWED_MCP_SERVERS

        env_tools = os.getenv("JKAI_MCP_TOOL_ALLOWLIST", "").strip()
        if allowed_tools is not None:
            self.allowed_tools = frozenset(str(t).strip().lower() for t in allowed_tools if str(t).strip())
        elif env_tools:
            self.allowed_tools = frozenset(t.strip().lower() for t in env_tools.split(",") if t.strip())
        else:
            self.allowed_tools = DEFAULT_ALLOWED_MCP_TOOLS

    @staticmethod
    def _is_loopback_endpoint(endpoint_url: str) -> bool:
        raw = str(endpoint_url or "").strip()
        if not raw or raw.startswith("stdio://") or raw == "stdio":
            return True
        parsed = urlparse(raw)
        host = (parsed.hostname or "").strip().lower()
        return host in _LOOPBACK_HOSTS

    def authorize_mcp_call(
        self,
        server_name: str,
        tool_name: str,
        endpoint_url: str = "stdio://local",
        local_only: Optional[bool] = None,
    ) -> Dict[str, Any]:
        srv = str(server_name or "").strip().lower()
        tl = str(tool_name or "").strip().lower()
        if local_only is None:
            env_flag = os.getenv("JKAI_LOCAL_ONLY_MODE", os.getenv("LOCAL_ONLY_MODE", "0")).strip().lower()
            is_local_only = env_flag in ("1", "true", "yes", "on")
        else:
            is_local_only = bool(local_only)

        if srv not in self.allowed_servers:
            return {
                "status": "refused",
                "allowed": False,
                "error_code": "MCP_NOT_IN_ALLOWLIST",
                "server_name": srv,
                "tool_name": tl,
                "endpoint_url": endpoint_url,
                "stage_attribution": StageAttribution.CONTROLLER_GATE.value,
                "message": (
                    f"[MCP-PILOT-REFUSED] Máy chủ MCP '{server_name}' không nằm trong danh sách cho phép "
                    f"(allowed_servers={sorted(self.allowed_servers)})."
                ),
            }

        if tl not in self.allowed_tools:
            return {
                "status": "refused",
                "allowed": False,
                "error_code": "MCP_TOOL_NOT_IN_ALLOWLIST",
                "server_name": srv,
                "tool_name": tl,
                "endpoint_url": endpoint_url,
                "stage_attribution": StageAttribution.CONTROLLER_GATE.value,
                "message": (
                    f"[MCP-PILOT-REFUSED] Công cụ MCP '{tool_name}' trên server '{server_name}' không nằm trong "
                    f"danh sách cho phép (allowed_tools={sorted(self.allowed_tools)})."
                ),
            }

        if is_local_only and not self._is_loopback_endpoint(endpoint_url):
            return {
                "status": "refused",
                "allowed": False,
                "error_code": "MCP_REMOTE_BLOCKED_IN_LOCAL_ONLY_MODE",
                "server_name": srv,
                "tool_name": tl,
                "endpoint_url": endpoint_url,
                "stage_attribution": StageAttribution.CONTROLLER_GATE.value,
                "message": (
                    f"[MCP-PILOT-REFUSED] Endpoint MCP '{endpoint_url}' bị chặn do chế độ LOCAL_ONLY_MODE chỉ cho phép "
                    f"kết nối cục bộ (localhost / 127.0.0.1 / stdio)."
                ),
            }

        return {
            "status": "allowed",
            "allowed": True,
            "error_code": None,
            "server_name": srv,
            "tool_name": tl,
            "endpoint_url": endpoint_url,
            "stage_attribution": StageAttribution.CONTROLLER_GATE.value,
        }


mcp_pilot_governor = LocalMCPPilotGovernor()
