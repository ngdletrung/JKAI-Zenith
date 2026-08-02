#!/usr/bin/env python3
"""
📜 Telemetry & Execution Trace Logger for JKAI Zenith.
Records step-by-step reasoning trajectories, tool executions, and system events
into JSON-Lines (.jsonl) files under brain/traces/ for post-mortem analysis and debugging.
"""

import os
import time
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger("TraceLogger")


class TraceLogger:
    """
    Trajectory Trace & Observability Logger for Autonomous Agents.
    """
    def __init__(self, trace_dir: Optional[str] = None):
        default_dir = os.path.join(os.getenv("WORKSPACE_ROOT", r"D:\Docker\JKAI"), "brain", "traces")
        self.trace_dir = Path(trace_dir or default_dir)
        self.trace_dir.mkdir(parents=True, exist_ok=True)

    def log_step(
        self,
        task_id: str,
        step_index: int,
        agent_name: str,
        action_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Logs a single execution step to brain/traces/{task_id}.jsonl.
        """
        try:
            trace_file = self.trace_dir / f"{task_id}.jsonl"
            entry = {
                "timestamp": time.time(),
                "task_id": task_id,
                "step_index": step_index,
                "agent_name": agent_name,
                "action_type": action_type,
                "content": content,
                "metadata": metadata or {}
            }

            with open(trace_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

            return str(trace_file)
        except Exception as e:
            logger.warning(f"[TRACE-LOGGER] Failed to write step log for task {task_id}: {e}")
            return ""

    def get_task_trace(self, task_id: str) -> List[Dict[str, Any]]:
        """Reads and returns all logged steps for a specific task."""
        trace_file = self.trace_dir / f"{task_id}.jsonl"
        if not trace_file.exists():
            return []

        steps = []
        try:
            with open(trace_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        steps.append(json.loads(line))
        except Exception as e:
            logger.warning(f"[TRACE-LOGGER] Failed to read trace file {trace_file}: {e}")

        return steps


trace_logger = TraceLogger()
