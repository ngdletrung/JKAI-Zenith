import os
import sys
import json
import time
import importlib
from typing import Optional

CONNECTIONS_PATH = os.path.join(os.path.dirname(__file__), "connections.json")
KM_ROOT = os.path.dirname(__file__)


def _import_connector_module(conn_type: str):
    module_name = f"connectors.{conn_type}"
    if KM_ROOT not in sys.path:
        sys.path.insert(0, KM_ROOT)
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError:
        return None


class ConnectionManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._connectors = {}

    def _load_connections(self) -> list:
        if not os.path.exists(CONNECTIONS_PATH):
            return []
        try:
            with open(CONNECTIONS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_connections(self, connections: list):
        os.makedirs(os.path.dirname(CONNECTIONS_PATH), exist_ok=True)
        with open(CONNECTIONS_PATH, "w", encoding="utf-8") as f:
            json.dump(connections, f, indent=2, ensure_ascii=False)

    def register_connection(self, conn_id: str, name: str, conn_type: str, config: dict) -> dict:
        connections = self._load_connections()
        entry = {
            "id": conn_id,
            "name": name,
            "type": conn_type,
            "config": config,
            "status": "active",
            "created_at": time.time(),
            "last_sync": None,
            "error": None,
        }
        connections = [c for c in connections if c.get("id") != conn_id]
        connections.append(entry)
        self._save_connections(connections)
        self._connectors.pop(conn_id, None)
        return entry

    def remove_connection(self, conn_id: str):
        connections = self._load_connections()
        connections = [c for c in connections if c.get("id") != conn_id]
        self._save_connections(connections)
        self._connectors.pop(conn_id, None)

    def get_connection(self, conn_id: str) -> Optional[dict]:
        if conn_id.startswith("rclone_"):
            remote_name = conn_id[7:]
            return {
                "id": conn_id,
                "name": f"{remote_name} (Rclone)",
                "type": "rclone",
                "config": {
                    "remote": remote_name,
                    "folder_path": "",
                }
            }
        for c in self._load_connections():
            if c.get("id") == conn_id:
                return c
        return None

    def list_connections(self) -> list:
        return self._load_connections()

    def _build_connector(self, entry: dict):
        conn_id = entry["id"]
        conn_type = entry.get("type", "local")
        config = entry.get("config", {})
        if conn_id in self._connectors:
            return self._connectors[conn_id]

        if KM_ROOT not in sys.path:
            sys.path.insert(0, KM_ROOT)

        class_name_map = {
            "local": "LocalFileConnector",
            "web": "WebConnector",
            "onedrive": "OneDriveConnector",
            "gdrive": "GDriveConnector",
            "sharepoint": "SharePointConnector",
            "dropbox": "DropboxConnector",
            "rclone": "RCloneConnector",
        }
        class_name = class_name_map.get(conn_type)
        if not class_name:
            return None
        try:
            module = importlib.import_module(f"connectors.{conn_type}")
            cls = getattr(module, class_name)
            self._connectors[conn_id] = cls(conn_id, config)
            return self._connectors[conn_id]
        except Exception:
            return None

    async def sync_connection(self, conn_id: str, progress_cb=None) -> dict:
        entry = self.get_connection(conn_id)
        if not entry:
            return {"status": "error", "msg": "Connection not found"}
        connector = self._build_connector(entry)
        if not connector:
            return {"status": "error", "msg": "Connector not available"}
        try:
            try:
                from core.knowledge_sources.metadata import metadata_db
            except Exception:
                metadata_db = None
            try:
                from core.utils.embed import embed
            except Exception:
                embed = None
            try:
                from core.qdrant_client import qdrant_client
            except Exception:
                qdrant_client = None

            try:
                from core.knowledge_sources.pipeline import SUPPORTED_EXTS
            except ImportError:
                SUPPORTED_EXTS = {
                    ".md", ".txt", ".pdf", ".docx", ".doc",
                    ".csv", ".json", ".yaml", ".toml",
                    ".py", ".js", ".ts", ".html", ".css", ".sh",
                    ".xlsx", ".xls", ".pptx", ".ppt",
                    ".eml", ".msg", ".rtf", ".odt",
                }

            import asyncio
            raw_files = await asyncio.to_thread(connector.list_files)
            # Lọc các file có định dạng được hỗ trợ thưa Master
            files = [f for f in raw_files if os.path.splitext(f.rel_path)[1].lower() in SUPPORTED_EXTS]

            # Tối ưu hóa: Nạp trước toàn bộ metadata của nguồn này trong 1 câu SQL thưa Master
            existing_files = {}
            import logging
            logger = logging.getLogger("jkai.intelligence.Knowledge_Manager.manager")
            if metadata_db:
                try:
                    db_files = metadata_db.get_all_files(conn_id)
                    existing_files = {f["rel_path"]: f for f in db_files}
                except Exception as e:
                    logger.warning(f"Failed to load metadata cache: {e}")

            # Lọc danh sách file thực tế cần đồng bộ (loại bỏ file đã trùng checksum) thưa Master
            to_process = []
            skipped_count = len(raw_files) - len(files)
            for f in files:
                existing = existing_files.get(f.rel_path)
                if existing and existing.get("status") == "indexed" and existing.get("checksum") == f.checksum:
                    skipped_count += 1
                else:
                    to_process.append(f)

            total = len(to_process)
            stats = {"scanned": len(raw_files), "imported": 0, "skipped": skipped_count, "failed": 0}

            if metadata_db:
                metadata_db.register_source(
                    conn_id, entry.get("name", conn_id),
                    entry.get("type", "local"), entry.get("config", {}),
                )

            async def _embed_chunks_batch(chunks):
                """Embed nhiều chunks với throttle semaphore thưa Master."""
                sem = asyncio.Semaphore(10)  # max 10 concurrent embed calls thưa Master

                async def _embed_one(text):
                    async with sem:
                        try:
                            return await asyncio.wait_for(embed.get_embedding_async(text[:4000]), timeout=25)
                        except asyncio.TimeoutError:
                            logger.warning(f"Embedding chunk timed out (25s limit reached)")
                            return None
                        except Exception as e:
                            logger.warning(f"Embedding chunk failed: {e}")
                            return None

                extract = lambda c: c["text"] if isinstance(c, dict) else c
                return await asyncio.gather(*[_embed_one(extract(c)) for c in chunks])

            async def _upsert_batch_async(points):
                try:
                    await qdrant_client.upsert_batch(points, "jkai_external")
                except Exception as e:
                    logger.warning(f"Failed to upsert points to Qdrant: {e}")

            def _read_cgroup_int(path: str, default: int) -> int:
                import os
                if os.path.exists(path):
                    try:
                        with open(path, 'r') as f:
                            val = f.read().strip()
                            if val == "max":
                                return default
                            return int(val)
                    except Exception:
                        return default
                return default

            async def _run_all_files():
                all_points_buffer = []  # buffer gom điểm để upsert theo batch 200
                buffer_lock = asyncio.Lock()  # Khóa bảo vệ buffer khi chạy song song thưa Master
                processed_count = 0

                # 1. Khởi tạo queue chứa các file cần xử lý thưa Master
                queue = asyncio.Queue()
                for f in to_process:
                    queue.put_nowait(f)

                # 2. Định nghĩa hàm xử lý một file
                async def _process_one_file(f):
                    nonlocal processed_count
                    # Tối ưu hóa: Bỏ qua file quá lớn (> 30MB) để tránh OOM thưa Master
                    if f.file_size > 30 * 1024 * 1024:
                        logger.warning(f"Skipping oversized file: {f.rel_path} ({f.file_size} bytes)")
                        async with buffer_lock:
                            stats["skipped"] += 1
                        if metadata_db:
                            metadata_db.mark_indexed(conn_id, f.rel_path, f.checksum)
                        # Cập nhật tiến trình thưa Master
                        async with buffer_lock:
                            processed_count += 1
                            if progress_cb:
                                try:
                                    progress_cb(processed_count, total, f.rel_path)
                                except Exception:
                                    pass
                        return

                    if metadata_db:
                        metadata_db.upsert_file(
                            conn_id, f.rel_path, f.abs_path,
                            f.file_type, f.checksum, f.file_size, f.mtime,
                        )

                    try:
                        file_bytes = await asyncio.to_thread(connector.read_file_bytes, f.rel_path)
                    except Exception as e:
                        logger.warning(f"Failed to download file {f.rel_path}: {e}")
                        async with buffer_lock:
                            stats["failed"] += 1
                        if metadata_db:
                            metadata_db.mark_indexed(conn_id, f.rel_path, f.checksum)
                        async with buffer_lock:
                            processed_count += 1
                            if progress_cb:
                                try:
                                    progress_cb(processed_count, total, f.rel_path)
                                except Exception:
                                    pass
                        return

                    if not file_bytes:
                        async with buffer_lock:
                            stats["failed"] += 1
                        if metadata_db:
                            metadata_db.mark_indexed(conn_id, f.rel_path, f.checksum)
                        async with buffer_lock:
                            processed_count += 1
                            if progress_cb:
                                try:
                                    progress_cb(processed_count, total, f.rel_path)
                                except Exception:
                                    pass
                        return

                    try:
                        from core.knowledge_sources.pipeline import _parse_bytes, _chunk_text
                    except ImportError:
                        _parse_bytes = lambda b, n: b.decode('utf-8', errors='replace')
                        _chunk_text = lambda t: [t[i:i+512] for i in range(0, len(t), 512) if t[i:i+512].strip()]

                    try:
                        content = await asyncio.to_thread(_parse_bytes, file_bytes, os.path.basename(f.rel_path))
                    except Exception as e:
                        logger.warning(f"Failed to parse file {f.rel_path}: {e}")
                        async with buffer_lock:
                            stats["failed"] += 1
                        if metadata_db:
                            metadata_db.mark_indexed(conn_id, f.rel_path, f.checksum)
                        async with buffer_lock:
                            processed_count += 1
                            if progress_cb:
                                try:
                                    progress_cb(processed_count, total, f.rel_path)
                                except Exception:
                                    pass
                        return

                    if not content or len(content.strip()) < 50:
                        async with buffer_lock:
                            stats["skipped"] += 1
                        if metadata_db:
                            metadata_db.mark_indexed(conn_id, f.rel_path, f.checksum)
                        async with buffer_lock:
                            processed_count += 1
                            if progress_cb:
                                try:
                                    progress_cb(processed_count, total, f.rel_path)
                                except Exception:
                                    pass
                        return

                    chunks = _chunk_text(content)
                    if not chunks or not embed or not qdrant_client:
                        async with buffer_lock:
                            stats["skipped"] += 1
                        if metadata_db:
                            metadata_db.mark_indexed(conn_id, f.rel_path, f.checksum)
                        async with buffer_lock:
                            processed_count += 1
                            if progress_cb:
                                try:
                                    progress_cb(processed_count, total, f.rel_path)
                                except Exception:
                                    pass
                        return

                    # Embed toàn bộ chunks của file này song song (throttled)
                    try:
                        vectors = await _embed_chunks_batch(chunks)
                    except Exception as e:
                        logger.warning(f"Failed to embed chunks for {f.rel_path}: {e}")
                        async with buffer_lock:
                            stats["failed"] += len(chunks)
                        if metadata_db:
                            metadata_db.mark_indexed(conn_id, f.rel_path, f.checksum)
                        async with buffer_lock:
                            processed_count += 1
                            if progress_cb:
                                try:
                                    progress_cb(processed_count, total, f.rel_path)
                                except Exception:
                                    pass
                        return

                    import uuid
                    file_points = []
                    for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
                        if vector:
                            if isinstance(chunk, dict):
                                chunk_text = chunk["text"]
                                start_idx = chunk.get("start_char_idx", 0)
                                end_idx = chunk.get("end_char_idx", 0)
                            else:
                                chunk_text = chunk
                                start_idx = 0
                                end_idx = 0
                            file_points.append({
                                "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{conn_id}:{f.rel_path}:chunk_{i}")),
                                "vector": vector,
                                "payload": {
                                    "text": chunk_text,
                                    "source": "external",
                                    "source_path": f.abs_path,
                                    "rel_path": f.rel_path,
                                    "filename": os.path.basename(f.rel_path),
                                    "file_type": f.file_type,
                                    "chunk_index": i,
                                    "start_char_idx": start_idx,
                                    "end_char_idx": end_idx,
                                    "mtime": f.mtime,
                                    "file_size": f.file_size,
                                    "checksum": f.checksum,
                                    "indexed_at": time.time(),
                                },
                            })

                    async with buffer_lock:
                        stats["failed"] += len(chunks) - len(file_points)
                        all_points_buffer.extend(file_points)

                        # Flush buffer mỗi 200 points để tránh memory spike
                        if len(all_points_buffer) >= 200:
                            await _upsert_batch_async(all_points_buffer[:200])
                            all_points_buffer[:] = all_points_buffer[200:]

                    # Tối ưu hóa: Luôn đánh dấu indexed để lần sau bỏ qua thưa Master
                    if metadata_db:
                        metadata_db.mark_indexed(conn_id, f.rel_path, f.checksum)
                        async with buffer_lock:
                            if file_points:
                                stats["imported"] += 1
                            else:
                                stats["skipped"] += 1

                    # Cập nhật tiến trình thưa Master
                    async with buffer_lock:
                        processed_count += 1
                        if progress_cb:
                            try:
                                progress_cb(processed_count, total, f.rel_path)
                            except Exception:
                                pass

                # 3. Định nghĩa hàm Worker thích ứng (Adaptive Worker) thưa Master
                active_workers = 0
                worker_tasks = []
                pool_lock = asyncio.Lock()

                async def _worker():
                    nonlocal active_workers
                    while not queue.empty():
                        try:
                            f = queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break

                        # Kiểm tra tài nguyên cgroup trước khi xử lý
                        mem_max = _read_cgroup_int("/sys/fs/cgroup/memory.max", 16*1024*1024*1024)
                        mem_curr = _read_cgroup_int("/sys/fs/cgroup/memory.current", 0)
                        mem_ratio = mem_curr / mem_max if mem_max > 0 else 0

                        # Nếu RAM sử dụng vượt quá 85% và đang có nhiều hơn 2 worker, tự hủy luồng này để nhường RAM thưa Master
                        async with pool_lock:
                            if mem_ratio > 0.85 and active_workers > 2:
                                logger.warning(f"Memory high ({mem_ratio:.2f}). Scaling down worker...")
                                active_workers -= 1
                                # Đẩy trả file lại hàng đợi để xử lý sau
                                await queue.put(f)
                                break

                        await _process_one_file(f)
                        queue.task_done()

                # 4. Định nghĩa hàm giám sát Autoscale (Tự động nâng luồng khi RAM rỗi)
                async def _monitor_autoscale():
                    nonlocal active_workers
                    while not queue.empty():
                        await asyncio.sleep(2)
                        mem_max = _read_cgroup_int("/sys/fs/cgroup/memory.max", 16*1024*1024*1024)
                        mem_curr = _read_cgroup_int("/sys/fs/cgroup/memory.current", 0)
                        mem_ratio = mem_curr / mem_max if mem_max > 0 else 0

                        # Nếu RAM trống nhiều (< 50%) và số worker hiện tại dưới 25, nâng số lượng worker thưa Master
                        async with pool_lock:
                            if mem_ratio < 0.50 and active_workers < 25 and not queue.empty():
                                scale_up_by = min(5, 25 - active_workers)
                                for _ in range(scale_up_by):
                                    active_workers += 1
                                    task = asyncio.create_task(_worker())
                                    worker_tasks.append(task)
                                logger.info("[AUTOSCALER] Scaled UP worker pool to %s (RAM ratio: %.2f)", active_workers, mem_ratio)

                # 5. Khởi tạo số lượng worker ban đầu thích ứng với bộ nhớ hiện tại thưa Master
                mem_max = _read_cgroup_int("/sys/fs/cgroup/memory.max", 16*1024*1024*1024)
                mem_curr = _read_cgroup_int("/sys/fs/cgroup/memory.current", 0)
                mem_ratio = mem_curr / mem_max if mem_max > 0 else 0

                initial_workers = 5
                if mem_ratio < 0.40:
                    initial_workers = 15  # Bộ nhớ còn trống nhiều -> Chạy ngay 15 luồng thưa Master

                active_workers = initial_workers
                logger.info("[AUTOSCALER] Initializing worker pool with %s workers (RAM ratio: %.2f)", initial_workers, mem_ratio)

                # Tạo các task worker ban đầu
                for _ in range(initial_workers):
                    task = asyncio.create_task(_worker())
                    worker_tasks.append(task)

                # Chạy monitor song song
                monitor_task = asyncio.create_task(_monitor_autoscale())

                # Chờ cho đến khi hàng đợi hoàn thành
                await queue.join()

                # Dọn dẹp các task worker
                for t in worker_tasks:
                    if not t.done():
                        t.cancel()
                if not monitor_task.done():
                    monitor_task.cancel()

                # Flush phần còn lại trong buffer
                if all_points_buffer:
                    await _upsert_batch_async(all_points_buffer)

            await _run_all_files()

            connections = self._load_connections()
            for c in connections:
                if c.get("id") == conn_id:
                    c["last_sync"] = time.time()
                    c["status"] = "active"
                    c["error"] = None
            self._save_connections(connections)
            return {"status": "ok", "stats": stats}
        except Exception as e:
            msg = str(e)[:200]
            connections = self._load_connections()
            for c in connections:
                if c.get("id") == conn_id:
                    c["status"] = "error"
                    c["error"] = msg
            self._save_connections(connections)
            return {"status": "error", "msg": msg}


    def sync_all(self) -> dict:
        results = {}
        for entry in self._load_connections():
            if entry.get("status") != "disabled":
                results[entry["id"]] = self.sync_connection(entry["id"])
        return results


connection_manager = ConnectionManager()
