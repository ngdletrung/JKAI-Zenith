#!/usr/bin/env python3
"""Regenerate intelligence/agents/agent_index.json from agent_*.md files."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "intelligence" / "agents"
OUT = AGENTS / "agent_index.json"


def main() -> int:
    items = []
    for p in sorted(AGENTS.glob("agent_*.md")):
        if not p.is_file():
            continue
        title = p.stem.replace("agent_", "").replace("_", " ").title()
        items.append({
            "id": p.name,
            "file": p.name,
            "title": title,
            "path": f"agents/{p.name}",
        })
    payload = {
        "category": "agents",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
        "items": items,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[AGENT-INDEX] {len(items)} agents -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
