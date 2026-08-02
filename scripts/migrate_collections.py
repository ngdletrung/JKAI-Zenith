"""
One-time migration: 12 old Qdrant collections → 4 new collections.

Old collections:
  jkai_zenith_intel, jkai_wiki, jkai_docs, jkai_skills, jkai_reflections,
  universal_graph, n8n_knowledge, jkai_agent_profiles
  → jkai_knowledge (source: docs/wiki/skills/agents/reflections/cache/universal/n8n)

  jkai_memory, jkai_tasks, zenith_missions
  → jkai_memory (memory_type: task/mission/wisdom/lesson)

  jkai_reasoning_bank
  → jkai_reasoning_bank (pattern_type: reasoning/failure)

Run: python scripts/migrate_collections.py
"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.qdrant_client import qdrant_client


COLLECTION_MAP = {
    "jkai_knowledge": {
        "sources": [
            "jkai_zenith_intel",
            "jkai_wiki",
            "jkai_docs",
            "jkai_skills",
            "jkai_reflections",
            "universal_graph",
            "n8n_knowledge",
            "jkai_agent_profiles",
        ],
        "source_tag": "source",
        "default_value": "docs",
        "value_map": {
            "jkai_zenith_intel": "cache",
            "jkai_wiki": "wiki",
            "jkai_docs": "docs",
            "jkai_skills": "skills",
            "jkai_reflections": "reflections",
            "universal_graph": "universal",
            "n8n_knowledge": "n8n",
            "jkai_agent_profiles": "agents",
        },
    },
    "jkai_memory": {
        "sources": ["jkai_memory", "jkai_tasks", "zenith_missions"],
        "source_tag": "memory_type",
        "default_value": "memory",
        "value_map": {
            "jkai_memory": "memory",
            "jkai_tasks": "task",
            "zenith_missions": "mission",
        },
    },
    "jkai_reasoning_bank": {
        "sources": ["jkai_reasoning_bank"],
        "source_tag": "pattern_type",
        "default_value": "reasoning",
        "value_map": {
            "jkai_reasoning_bank": "reasoning",
        },
    },
}


async def migrate():
    print("=" * 60)
    print("JKAI Collection Migration: 12 → 4")
    print("=" * 60)

    for target_collection, config in COLLECTION_MAP.items():
        print(f"\n--- Migrating to {target_collection} ---")
        await qdrant_client.ensure_collection(target_collection)

        for old_collection in config["sources"]:
            print(f"  Reading from {old_collection}...", end=" ")
            try:
                points = await _scroll_all(old_collection)
                if not points:
                    print(f"empty")
                    continue
                print(f"{len(points)} points")

                source_tag = config["source_tag"]
                default_value = config["default_value"]
                value_map = config["value_map"]
                source_label = value_map.get(old_collection, default_value)

                batch = []
                for p in points:
                    payload = p.get("payload", {}) or {}
                    payload[source_tag] = source_label
                    payload["_migrated"] = True
                    batch.append({
                        "id": p.get("id"),
                        "vector": p.get("vector"),
                        "payload": payload,
                    })

                # Upsert in batches of 100
                for i in range(0, len(batch), 100):
                    chunk = batch[i : i + 100]
                    await qdrant_client.upsert_batch(chunk, collection=target_collection)

                print(f"  -> Migrated {len(batch)} points to {target_collection}")

            except Exception as e:
                print(f"ERROR: {e}")

    print("\n--- Migration complete ---")
    print("\nOld collections can now be deleted via Qdrant UI or API:")
    for target_collection, config in COLLECTION_MAP.items():
        for old in config["sources"]:
            print(f"  DELETE /collections/{old}")


async def _scroll_all(collection: str, limit: int = 1000) -> list:
    """Scroll all points from a Qdrant collection."""
    import httpx

    url = qdrant_client.url
    all_points = []
    offset = None

    async with httpx.AsyncClient(timeout=60.0) as client:
        while True:
            payload = {
                "limit": limit,
                "with_payload": True,
                "with_vector": True,
            }
            if offset:
                payload["offset"] = offset

            try:
                resp = await client.post(f"{url}/collections/{collection}/points/scroll", json=payload)
                if resp.status_code != 200:
                    break
                data = resp.json().get("result", {})
                pts = data.get("points", [])
                all_points.extend(pts)
                offset = data.get("next_page_offset")
                if not offset:
                    break
            except Exception:
                break

    return all_points


if __name__ == "__main__":
    asyncio.run(migrate())
