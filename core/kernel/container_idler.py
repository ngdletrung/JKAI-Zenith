# -*- coding: utf-8 -*-
"""
🏛️ JKAI ZENITH — CONTAINER IDLER & WAKE-ON-DEMAND GOVERNOR
File: core/kernel/container_idler.py

Purpose:
    Manages dynamic Docker container lifecycles (Wake-on-Demand & Auto-Sleep)
    to prevent idle background containers from wasting RAM and CPU threads.

Constitutional Principles:
    1. Core containers (ai-brain, redis-ai, qdrant, postgres, mission-control, ai-executor-1) are ALWAYS ON.
    2. Satellite tool containers (ai-browser, ai-telegram, n8n, etc.) are started ON-DEMAND when invoked.
    3. If an on-demand container is idle for > IDLE_TIMEOUT_SEC (default 15 mins), it gracefully stops.
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import time
from typing import Dict, List, Optional, Set

logger = logging.getLogger("JKAI.ContainerIdler")

IDLE_TIMEOUT_SEC: float = 900.0  # 15 minutes


class ContainerIdler:
    """
    Singleton manager for Docker container power states.
    """

    _instance: Optional[ContainerIdler] = None

    # Mapping from tool name prefix or action to required Docker container
    TOOL_TO_CONTAINER: Dict[str, str] = {
        "browse_web": "ai-browser",
        "browser_action": "ai-browser",
        "scrape_url": "ai-browser",
        "telegram_send": "ai-telegram",
        "telegram_poll": "ai-telegram",
        "n8n_trigger": "n8n-main",
        "file_warden_scan": "jkai-file-warden",
    }

    # Core containers that MUST NEVER be stopped
    CORE_CONTAINERS: Set[str] = {
        "postgres",
        "redis-ai",
        "qdrant",
        "ai-brain",
        "mission-control",
        "ai-executor-1",
    }

    # On-demand containers eligible for Auto-Sleep
    ON_DEMAND_CONTAINERS: Set[str] = {
        "ai-browser",
        "ai-telegram",
        "n8n-main",
        "n8n-worker",
        "redis-queue",
        "backup-scheduler",
        "jkai-file-warden",
        "ai-executor-2",
        "ai-worker",
    }

    def __init__(self):
        self._last_active: Dict[str, float] = {}
        self._is_running: bool = False
        self._bg_task: Optional[asyncio.Task] = None

    @classmethod
    def get_instance(cls) -> ContainerIdler:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def record_activity(self, container_name: str) -> None:
        """Record activity timestamp for a container."""
        self._last_active[container_name] = time.monotonic()
        logger.debug("[IDLER] Activity recorded for container: %s", container_name)

    async def ensure_tool_container_ready(self, tool_name: str) -> bool:
        """
        Wake-on-Demand: Checks if tool requires a container.
        If container is stopped, starts it before returning.
        """
        tool_lower = (tool_name or "").lower().strip()
        target_container: Optional[str] = None

        for prefix, c_name in self.TOOL_TO_CONTAINER.items():
            if tool_lower.startswith(prefix) or prefix in tool_lower:
                target_container = c_name
                break

        if not target_container:
            return True  # No specific container needed (handled locally or by core executor)

        self.record_activity(target_container)
        return await self.wake_container_async(target_container)

    async def wake_container_async(self, container_name: str) -> bool:
        """Asynchronously checks and starts a container if not running."""
        try:
            # Check running state via docker inspect
            is_running = await self._is_container_running(container_name)
            if is_running:
                return True

            logger.info("[WAKE-ON-DEMAND] Container '%s' is stopped. Waking up...", container_name)
            t0 = time.perf_counter()
            proc = await asyncio.create_subprocess_exec(
                "docker", "start", container_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            elapsed_s = time.perf_counter() - t0

            if proc.returncode == 0:
                logger.info("[WAKE-ON-DEMAND] Container '%s' woke up successfully in %.2fs!", container_name, elapsed_s)
                # Brief grace period for container service to bind port
                await asyncio.sleep(1.5)
                return True
            else:
                logger.error("[WAKE-ON-DEMAND] Failed to start '%s' (exit code %s)", container_name, proc.returncode)
                return False
        except Exception as e:
            logger.warning("[WAKE-ON-DEMAND] Error waking container '%s': %s", container_name, e)
            return False

    async def _is_container_running(self, container_name: str) -> bool:
        """Checks if a container is currently running."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "inspect", "-f", "{{.State.Running}}", container_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            return stdout.decode().strip().lower() == "true"
        except Exception:
            return False

    async def check_idle_containers(self, timeout_sec: float = IDLE_TIMEOUT_SEC) -> List[str]:
        """
        Scans all on-demand containers. Stops any container idle for > timeout_sec.
        Returns list of stopped container names.
        """
        now = time.monotonic()
        stopped: List[str] = []

        for c_name in self.ON_DEMAND_CONTAINERS:
            # Never stop core containers
            if c_name in self.CORE_CONTAINERS:
                continue

            last_used = self._last_active.get(c_name, 0.0)
            idle_duration = now - last_used

            if last_used > 0 and idle_duration > timeout_sec:
                if await self._is_container_running(c_name):
                    logger.info(
                        "[AUTO-SLEEP] Container '%s' has been idle for %.1f mins (>%.0fm). Gracefully stopping...",
                        c_name, idle_duration / 60.0, timeout_sec / 60.0
                    )
                    try:
                        proc = await asyncio.create_subprocess_exec(
                            "docker", "stop", "-t", "5", c_name,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        await proc.communicate()
                        if proc.returncode == 0:
                            stopped.append(c_name)
                            logger.info("[AUTO-SLEEP] Container '%s' stopped successfully (RAM released).", c_name)
                    except Exception as ex:
                        logger.error("[AUTO-SLEEP] Error stopping '%s': %s", c_name, ex)

        return stopped

    def start_background_monitor(self, check_interval_sec: float = 60.0) -> None:
        """Starts background idle monitoring loop."""
        if self._is_running:
            return
        self._is_running = True

        async def _loop():
            while self._is_running:
                try:
                    await self.check_idle_containers()
                except Exception as e:
                    logger.debug("[IDLER-LOOP-ERR] %s", e)
                await asyncio.sleep(check_interval_sec)

        try:
            loop = asyncio.get_running_loop()
            self._bg_task = loop.create_task(_loop())
        except RuntimeError:
            pass


container_idler = ContainerIdler.get_instance()
