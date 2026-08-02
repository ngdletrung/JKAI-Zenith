import asyncio
import json
import time
from redis_client import redis_safe
from core.utils.crdt_engine import ZenithCRDT


class DAGExecutor:
    """
    ⚡ JKAI ZENITH: DAG PARALLEL EXECUTOR
    Thực thi các bước độc lập song song để tối ưu tốc độ.
    Các bước có `parallel: true` sẽ được nhóm và chạy cùng lúc.
    """

    def __init__(self, executor_instance):
        self.executor = executor_instance

    def _log(self, tag: str, msg: str, task_id: str = "dag"):
        try:
            log_payload = json.dumps(
                {"tag": tag, "msg": msg, "ts": time.time(), "task_id": task_id},
                ensure_ascii=False,
            )
            def _redis_op(r):
                r.lpush("monitor:log_history", log_payload)
                r.ltrim("monitor:log_history", 0, 499)
                r.publish("monitor:log_channel", log_payload)
            redis_safe(_redis_op)
        except Exception as e:
            print(f"[DAG-LOG-ERR] {e}")

    def _group_steps(self, steps: list) -> list:
        """
        Phân tích và nhóm các bước thành các 'đợt' thực thi.
        Bước có `parallel: true` sẽ được gom cùng nhóm với các bước parallel liên tiếp.
        Bước tuần tự (`parallel: false` hoặc không có flag) sẽ tạo một nhóm riêng.
        """
        groups = []
        current_parallel_group = []

        for step in steps:
            is_parallel = step.get("parallel", False) or "[PARALLEL]" in step.get("description", "")
            if is_parallel:
                current_parallel_group.append(step)
            else:
                # Flush parallel group trước
                if current_parallel_group:
                    groups.append({"type": "parallel", "steps": current_parallel_group})
                    current_parallel_group = []
                # Thêm bước tuần tự
                groups.append({"type": "sequential", "steps": [step]})

        # Flush nhóm parallel cuối cùng nếu còn
        if current_parallel_group:
            groups.append({"type": "parallel", "steps": current_parallel_group})

        return groups

    async def _execute_step(self, step: dict, task_id: str) -> dict:
        """Thực thi một bước đơn lẻ thông qua Executor."""
        tool_name = step.get("tool")
        args = step.get("args", {})
        desc = step.get("description", "Executing step")

        if not tool_name:
            return {"step": step.get("id"), "status": "skipped", "output": "No tool specified"}

        profile = step.get("profile")
        if profile:
            args["profile"] = profile

        res = await self.executor.call_tool(tool_name, args, task_id, expert_mindset=step.get("expert_mindset"))
        
        if res.get("status") != "success":
            # Kích hoạt Self-Healing nếu có lỗi trong DAG
            res = await self.executor._self_heal_step(step, res.get("msg") or str(res), task_id)
            
        return {
            "step": step.get("id"),
            "description": desc,
            "status": res.get("status", "unknown"),
            "output": res.get("output") or res.get("msg"),
        }

    async def run(self, steps: list, task_id: str = "dag") -> dict:
        """
        Điều phối toàn bộ luồng thực thi DAG.
        - Bước song song → asyncio.gather()
        - Bước tuần tự → await tuần tự
        """
        if not steps:
            return {"status": "completed", "results": [], "summary": "No steps to execute."}

        groups = self._group_steps(steps)
        total_steps = len(steps)
        parallel_steps = sum(len(g["steps"]) for g in groups if g["type"] == "parallel")
        sequential_steps = total_steps - parallel_steps

        self._log(
            "EXECUTOR",
            f"⚡ [DAG ENGINE]: Khởi động lộ trình tối ưu — "
            f"{total_steps} bước tổng | {parallel_steps} song song | {sequential_steps} tuần tự",
            task_id,
        )

        all_results = []
        start_time = time.time()

        for i, group in enumerate(groups):
            group_type = group["type"]
            group_steps = group["steps"]

            if group_type == "parallel" and len(group_steps) > 1:
                self._log(
                    "EXECUTOR",
                    f"[DAG-PARALLEL]: Kich hoat {len(group_steps)} buoc song song - Nhat the hoa CRDT (Nhom {i+1}/{len(groups)})...",
                    task_id,
                )

                # [CRDT-LOCK]: Dang ky cac file se bi tac dong boi nhom nay de tranh ghi de
                affected_files = set()
                for step in group_steps:
                    file_path = str(step.get("args", {}).get("file_path", "") or step.get("args", {}).get("path", ""))
                    if file_path:
                        affected_files.add(file_path)
                        ZenithCRDT.sync_state(f"lock:{file_path}", {"locked_by": task_id, "status": "in_progress"})

                if affected_files:
                    self._log("EXECUTOR", f"[CRDT-LOCK]: Da khoa {len(affected_files)} file cho giai doan song song thua Master.", task_id)

                # Chay song song voi asyncio.gather
                tasks = [
                    self._execute_step(step, f"{task_id}_p{j}")
                    for j, step in enumerate(group_steps)
                ]
                group_results = await asyncio.gather(*tasks, return_exceptions=True)

                # [CRDT-UNLOCK]: Giai phong khoa sau khi hoan thanh
                for file_path in affected_files:
                    ZenithCRDT.sync_state(f"lock:{file_path}", {"locked_by": None, "status": "released"})

                for res in group_results:
                    if isinstance(res, Exception):
                        all_results.append({"status": "error", "output": str(res)})
                    else:
                        all_results.append(res)
                        if res.get("status") == "needs_auth":
                            return {"status": "needs_auth", "results": all_results, "summary": "Phat hien thao tac nhay cam song song. Dung de xac thuc thua Master."}

                self._log(
                    "EXECUTOR",
                    f"[DAG-PARALLEL]: Nhom {i+1} hoan tat - {len(group_steps)} buoc da chay song song an toan qua CRDT.",
                    task_id,
                )
            else:
                # Tuần tự (sequential hoặc parallel nhóm 1 bước)
                for step in group_steps:
                    desc = step.get("description", "...")
                    self._log("EXECUTOR", f"🔹 [DAG-SEQ]: Đang thực thi: {desc}", task_id)
                    res = await self._execute_step(step, task_id)
                    all_results.append(res)
                    if res.get("status") == "needs_auth":
                         return {"status": "needs_auth", "results": all_results, "summary": "Dừng để xác thực."}

        total_time = time.time() - start_time
        success_count = sum(1 for r in all_results if r.get("status") == "success")

        self._log(
            "EXECUTOR",
            f"🏁 [DAG ENGINE]: Lộ trình hoàn tất trong {total_time:.2f}s — "
            f"{success_count}/{total_steps} bước thành công. 💎🫡",
            task_id,
        )

        return {
            "status": "completed",
            "results": all_results,
            "summary": f"DAG hoàn tất: {success_count}/{total_steps} bước thành công trong {total_time:.2f}s.",
            "elapsed": total_time,
        }

# *Sovereign Property of Master LeeTrung. Developed by Antigravity AI. Optimized for Eternal Excellence. 🌌🏛️🔥🦾👑🔗*
