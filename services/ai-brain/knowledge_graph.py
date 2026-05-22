from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from pathlib import Path
import uuid
from typing import Any

from omni_parser import UniversalNode, scan_omni_directory

sys_path_base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
import sys; sys.path.append(sys_path_base)
from core.qdrant_client import qdrant_client
from core.utils.engine import engine

logger = logging.getLogger(__name__)

BATCH_SIZE = 100


# ═══════════════════════════════════════════════════════
# FIX 6: Obsidian writer không block event loop
# ═══════════════════════════════════════════════════════

def _build_obsidian_content(node: UniversalNode) -> str:
    """Build nội dung .md cho một node — pure function, dễ test."""
    lines: list[str] = [
        f"---\n"
        f"type: {node.file_type}\n"
        f"file: {node.file}\n"
        f"tags: [{', '.join(node.tags)}]\n"
        f"---\n\n"
        f"# {node.name}\n\n"
        f"{node.content_summary}\n\n"
    ]
    if node.tags:
        lines.append("## Tags\n")
        lines.append(" ".join(f"#{t}" for t in node.tags) + "\n\n")
    if node.links_to:
        lines.append("## Links to\n")
        lines += [f"- [[{ref}]]\n" for ref in node.links_to]
    if node.linked_by:
        lines.append("\n## Linked by\n")
        lines += [f"- [[{ref}]]\n" for ref in node.linked_by]
    return "".join(lines)


def _make_safe_filename(node_id: str, max_len: int = 200) -> str:
    """
    Chuyển node_id thành tên file an toàn cho hệ điều hành.
    - Thay thế ký tự đặc biệt bằng '_'.
    - Giới hạn độ dài tối đa là max_len ký tự.
    - Gắn hash md5 ngắn (8 ký tự) làm suffix để đảm bảo tính duy nhất khi bị truncate.
    """
    safe = node_id.replace("/", "_").replace("\\", "_").replace(":", "_")
    safe = "".join(c if c.isalnum() or c in ("_", "-", ".") else "_" for c in safe)
    hash_suffix = hashlib.md5(node_id.encode("utf-8")).hexdigest()[:8]
    if len(safe) > max_len:
        safe = safe[:max_len]
    return f"{safe}_{hash_suffix}"


def _write_obsidian_sync(nodes: list[UniversalNode], vault_path: str) -> int:
    """
    Synchronous write — dipanggil via run_in_executor agar không block event loop.
    Chỉ ghi file nếu mtime thay đổi.
    """
    vault = Path(vault_path)
    vault.mkdir(parents=True, exist_ok=True)
    count = 0
    for node in nodes:
        safe = _make_safe_filename(node.node_id)
        target_file = vault / f"{safe}.md"
        
        # 🛡️ [INCREMENTAL-OBSIDIAN]: Kiểm tra mtime để tránh ghi đè vô ích
        source_mtime = node.metadata.get("file_mtime", 0)
        if target_file.exists():
            if target_file.stat().st_mtime >= source_mtime:
                continue

        try:
            target_file.write_text(
                _build_obsidian_content(node), encoding="utf-8"
            )
            count += 1
        except OSError as e:
            logger.warning(f"Obsidian write failed for {node.node_id}: {e}")
    return count


# ═══════════════════════════════════════════════════════
# UNIVERSAL GRAPH — orchestrator chính
# ═══════════════════════════════════════════════════════

class UniversalGraph:
    """
    Quản lý luồng: Scan → Batch Upsert (Qdrant) → Obsidian export.

    Thay đổi so với bản gốc:
      - FIX 1: asyncio.run() trong __init__ → lazy _ensure_initialized()
      - FIX 2: Module-level singleton → get_universal_graph() factory
      - FIX 3: Sequential upsert → asyncio.gather theo chunk
      - FIX 4: Payload thiếu field → full payload từ node.to_payload()
      - FIX 5: except: pass → log lỗi cụ thể
      - FIX 6: Blocking export_to_obsidian → run_in_executor
    """

    COLLECTION  = "universal_graph"
    VECTOR_SIZE = 768

    def __init__(self):
        self._initialized = False
        # FIX 1: Lock ngăn race condition khi nhiều coroutine init cùng lúc
        self._init_lock   = asyncio.Lock()

    # ── FIX 1: Lazy async init ──────────────────────────────

    async def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            
            logger.info(f"UniversalGraph: ensuring collection '{self.COLLECTION}'...")
            # Kiểm tra collection
            try:
                await qdrant_client.init_collection(self.COLLECTION, vector_size=self.VECTOR_SIZE)
                self._initialized = True
                logger.info(f"UniversalGraph: collection '{self.COLLECTION}' ready.")
            except Exception as e:
                logger.error(f"UniversalGraph: Qdrant init failed: {e}", exc_info=True)
                raise

    # ── Logic nạp tri thức ──────────────────────────────────

    async def _batch_upsert(self, nodes: list[UniversalNode]) -> int:
        """
        Upsert BATCH_SIZE nodes song song mỗi chunk.
        Chỉ upsert nếu file_mtime thay đổi.
        """
        from core.utils.embed import embed 

        async def _upsert_batch(batch: list[UniversalNode]) -> int:
            # 1. Map stable UUIDs
            node_map = {
                str(uuid.uuid5(uuid.NAMESPACE_DNS, n.node_id)): n 
                for n in batch
            }
            ids = list(node_map.keys())
            
            # 2. Fetch existing from Qdrant
            existing_points = await qdrant_client.get_points(self.COLLECTION, ids)
            existing_mtimes = {}
            for p in existing_points:
                payload = p.get("payload", {})
                existing_mtimes[p["id"]] = payload.get("metadata", {}).get("file_mtime")

            # 3. Filter nodes that need update
            to_update = []
            for p_id, node in node_map.items():
                current_mtime = node.metadata.get("file_mtime")
                if p_id not in existing_mtimes or existing_mtimes[p_id] != current_mtime:
                    to_update.append((p_id, node))
            
            if not to_update:
                return 0

            # 4. Embed and Upsert song song
            async def _process_one(p_id: str, node: UniversalNode) -> bool:
                embed_text = node.to_embed_text()
                vector = await embed.get_embedding_async(embed_text)
                if not vector: return False
                
                try:
                    await qdrant_client.add_intel(
                        self.COLLECTION, embed_text, vector, 
                        node.to_payload(), point_id=p_id
                    )
                    return True
                except Exception as e:
                    logger.error(f"Upsert failed for {node.node_id}: {e}")
                    return False

            results = await asyncio.gather(
                *[_process_one(p_id, n) for p_id, n in to_update],
                return_exceptions=True
            )
            return sum(1 for r in results if r is True)

        success = 0
        chunks  = [nodes[i:i + BATCH_SIZE] for i in range(0, len(nodes), BATCH_SIZE)]

        for idx, chunk in enumerate(chunks):
            ok = await _upsert_batch(chunk)
            success += ok
            logger.info(
                f"Sync chunk {idx + 1}/{len(chunks)}: "
                f"{ok}/{len(chunk)} updated."
            )
            # 🛡️ [CONCURRENCY-GUARD]: Nhường đường cho Master gõ lệnh
            await asyncio.sleep(0.01)

        return success

    # ── Orchestrator chính ──────────────────────────────────

    async def build_and_sync(
        self,
        directories: list[str],
        *,
        obsidian_vault: str | None = None,
        max_scan_concurrency: int  = 20,
        task_id: str = "graph_sync"
    ) -> dict[str, Any]:
        """
        Full pipeline: Scan → Qdrant → Obsidian.
        Trả về stats dict để caller biết kết quả.
        """
        engine.publish_mission_log("SYNC", "🚀 [UNIVERSAL-GRAPH]: Bắt đầu chiến dịch vẽ lại Bản đồ Hệ thống...", task_id)
        try:
            await self._ensure_initialized()
        except Exception as e:
            engine.publish_mission_log("CRITICAL", f"❌ [GRAPH-INIT-ERR]: Không thể khởi tạo Qdrant: {e}", task_id)
            raise

        # Scan các directory song song
        existing = [d for d in directories if os.path.exists(d)]
        missing  = [d for d in directories if not os.path.exists(d)]
        if missing:
            logger.warning(f"Directories not found (skipped): {missing}")

        scan_tasks = [
            scan_omni_directory(d, max_concurrency=max_scan_concurrency)
            for d in existing
        ]
        scan_results = await asyncio.gather(*scan_tasks, return_exceptions=True)

        all_nodes: list[UniversalNode] = []
        for d, result in zip(existing, scan_results):
            if isinstance(result, Exception):
                logger.error(f"scan_omni_directory failed for {d}: {result}")
            else:
                all_nodes.extend(result)
                logger.info(f"Scanned {d}: {len(result)} nodes.")

        if not all_nodes:
            logger.warning("No nodes found. Aborting sync.")
            return {"nodes": 0, "upserted": 0, "obsidian": 0}

        # Upsert vào Qdrant
        logger.info(f"Starting batch upsert: {len(all_nodes)} nodes...")
        try:
            upserted = await self._batch_upsert(all_nodes)
        except Exception as e:
            engine.publish_mission_log("ERROR", f"❌ [GRAPH-UPSERT-ERR]: Lỗi trong quá trình nạp nơ-ron: {e}", task_id)
            upserted = 0

        # FIX 6: Export Obsidian trên thread pool — không block event loop
        obsidian_count = 0
        if obsidian_vault:
            try:
                loop = asyncio.get_running_loop()
                obsidian_count = await loop.run_in_executor(
                    None, _write_obsidian_sync, all_nodes, obsidian_vault
                )
                logger.info(f"Obsidian export: {obsidian_count} files → {obsidian_vault}")
            except Exception as e:
                engine.publish_mission_log("WARNING", f"⚠️ [OBSIDIAN-EXPORT-ERR]: Lỗi khi xuất bản đồ Obsidian: {e}", task_id)

        stats = {
            "nodes":    len(all_nodes),
            "upserted": upserted,
            "obsidian": obsidian_count,
            "types":    list({n.file_type for n in all_nodes}),
        }
        logger.info(f"build_and_sync complete: {stats}")
        engine.publish_mission_log("SYNC", f"✅ [GRAPH-SYNC-COMPLETE]: Đã vẽ xong bản đồ với {upserted} nơ-ron mới!", task_id)
        return stats

    async def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Semantic search trên universal graph."""
        from core.utils.embed import embed
        await self._ensure_initialized()
        
        # 🛡️ [ASYNC-GUARD]: Chuyển sang async để không block event loop
        vector = await embed.get_embedding_async(query)
        if not vector:
            return []
        return await qdrant_client.search_similar(
            vector, limit=limit, collection=self.COLLECTION
        )


# ═══════════════════════════════════════════════════════
# FIX 2: Factory function — không chạy khi import
# ═══════════════════════════════════════════════════════

_instance: UniversalGraph | None = None

def get_universal_graph() -> UniversalGraph:
    """Singleton lazy — an toàn khi import, chỉ tạo khi cần."""
    global _instance
    if _instance is None:
        _instance = UniversalGraph()
    return _instance


# ═══════════════════════════════════════════════════════
# ENTRYPOINT
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    from collections import Counter

    logging.basicConfig(
        level  = logging.INFO,
        format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    async def main():
        base = Path(__file__).parent.parent.parent
        dirs = [
            str(base / "core"),
            str(base / "services"),
            str(base / "agents"),
        ]
        vault = str(base / "intelligence" / "vault" / "01_Knowledge")

        graph = get_universal_graph()
        stats = await graph.build_and_sync(dirs, obsidian_vault=vault)
        logger.info(f"📊 [GRAPH-STATS]: Nodes: {stats['nodes']} | Upserted: {stats['upserted']} | Obsidian: {stats['obsidian']}")

    asyncio.run(main())
