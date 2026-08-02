# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/artifact_tracker.py
# - Role: Hệ thống Artifacts Minh bạch — ghi lại toàn bộ những gì agent thực hiện trong mỗi task
# - Ownership: Mr LeeTrung
# - Status: Active | Version: v1.0

"""
ArtifactTracker — Triết lý thiết kế:

Mỗi task mà JKAI thực hiện phải để lại một "dấu vết" minh bạch:
  - Những file nào đã được tạo / sửa / xóa?
  - Những kỹ năng nào đã được gọi và kết quả ra sao?
  - Kế hoạch gồm những bước nào và bước nào thành công / thất bại?
  - Tổng thời gian và chi phí token là bao nhiêu?

Artifact được lưu vào Redis với TTL 7 ngày và truy xuất qua GET /artifact/{task_id}.
"""

import json
import time
import logging
from typing import Literal, Optional
from redis_client import redis_safe

logger = logging.getLogger("jkai.artifact_tracker")

_TTL_SECONDS = 7 * 24 * 3600  # 7 ngày
_REDIS_KEY_PREFIX = "artifact:"
_MAX_OUTPUT_PREVIEW = 500   # ký tự tối đa cho output preview của mỗi tool
_MAX_DIFF_PREVIEW = 300     # ký tự tối đa cho diff preview


def _redis_key(task_id: str) -> str:
    return f"{_REDIS_KEY_PREFIX}{task_id}"


class ArtifactTracker:
    """
    Theo dõi và ghi lại toàn bộ hành động của agent trong một task.
    Thiết kế: stateless từ phía caller — mọi state đều lưu trong Redis.
    """

    # ── PUBLIC API ──────────────────────────────────────────────────────────

    @staticmethod
    def start_session(task_id: str, goal: str, mode: str = "fast") -> None:
        """Khởi tạo artifact session cho task mới."""
        artifact = {
            "task_id": task_id,
            "goal": goal[:300],
            "mode": mode,
            "started_at": time.time(),
            "finished_at": None,
            "status": "running",
            "plan_steps": [],
            "tool_calls": [],
            "files_changed": [],
            "summary": None,
            "token_estimate": 0,
            "error": None,
        }
        _write(task_id, artifact)
        logger.debug("[ARTIFACT] Session started: %s", task_id)

    @staticmethod
    def record_step(
        task_id: str,
        step_id: str,
        description: str,
        status: Literal["running", "completed", "failed", "skipped"],
        detail: Optional[str] = None,
    ) -> None:
        """Ghi lại trạng thái một bước trong kế hoạch thực thi."""
        artifact = _read(task_id)
        if not artifact:
            return
        # Cập nhật nếu step đã tồn tại, thêm mới nếu chưa có
        for s in artifact["plan_steps"]:
            if s["step_id"] == step_id:
                s["status"] = status
                s["finished_at"] = time.time()
                if detail:
                    s["detail"] = detail[:200]
                _write(task_id, artifact)
                return
        artifact["plan_steps"].append({
            "step_id": step_id,
            "description": description,
            "status": status,
            "started_at": time.time(),
            "finished_at": time.time() if status != "running" else None,
            "detail": (detail or "")[:200],
        })
        _write(task_id, artifact)

    @staticmethod
    def record_tool_call(
        task_id: str,
        skill_id: str,
        args_summary: str,
        output: str,
        duration_ms: float,
        success: bool = True,
    ) -> None:
        """Ghi lại một lần gọi kỹ năng (tool call) và kết quả."""
        artifact = _read(task_id)
        if not artifact:
            return
        output_preview = output[:_MAX_OUTPUT_PREVIEW] + ("..." if len(output) > _MAX_OUTPUT_PREVIEW else "")
        artifact["tool_calls"].append({
            "skill_id": skill_id,
            "args_summary": args_summary[:150],
            "output_preview": output_preview,
            "output_length": len(output),
            "duration_ms": round(duration_ms, 1),
            "success": success,
            "timestamp": time.time(),
        })
        _write(task_id, artifact)

    @staticmethod
    def record_file_change(
        task_id: str,
        file_path: str,
        change_type: Literal["created", "modified", "deleted"],
        diff_preview: Optional[str] = None,
        size_bytes: Optional[int] = None,
    ) -> None:
        """Ghi lại một file đã được tạo / sửa / xóa trong quá trình thực thi."""
        artifact = _read(task_id)
        if not artifact:
            return
        # Tránh duplicate
        existing_paths = [f["path"] for f in artifact["files_changed"]]
        if file_path in existing_paths:
            # Cập nhật record đã có
            for f in artifact["files_changed"]:
                if f["path"] == file_path:
                    f["change_type"] = change_type
                    if diff_preview:
                        f["diff_preview"] = diff_preview[:_MAX_DIFF_PREVIEW]
                    break
        else:
            artifact["files_changed"].append({
                "path": file_path,
                "change_type": change_type,
                "diff_preview": (diff_preview or "")[:_MAX_DIFF_PREVIEW],
                "size_bytes": size_bytes,
                "timestamp": time.time(),
            })
        _write(task_id, artifact)

    @staticmethod
    def record_file_diff(task_id: str, before_snap: dict, after_snap: dict, workspace_root: str) -> None:
        """
        So sánh 2 snapshot workspace và tự động ghi lại các file thay đổi.
        Dùng sau khi chạy S2_FORGE xong.
        """
        artifact = _read(task_id)
        if not artifact:
            return

        import os
        added   = [k for k in after_snap  if k not in before_snap]
        removed = [k for k in before_snap if k not in after_snap]
        modified = [k for k in before_snap if k in after_snap and before_snap[k] != after_snap[k]]

        for path in added:
            full_path = os.path.join(workspace_root, path)
            size = os.path.getsize(full_path) if os.path.exists(full_path) else None
            # Preview 3 dòng đầu
            preview = ""
            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as fh:
                    preview = "".join(fh.readlines()[:3])
            except Exception:
                pass
            ArtifactTracker.record_file_change(task_id, path, "created",
                                               diff_preview=preview, size_bytes=size)
        for path in modified:
            ArtifactTracker.record_file_change(task_id, path, "modified")
        for path in removed:
            ArtifactTracker.record_file_change(task_id, path, "deleted")

    @staticmethod
    def finalize(
        task_id: str,
        status: Literal["completed", "failed", "aborted"] = "completed",
        summary: Optional[str] = None,
        token_estimate: int = 0,
        error: Optional[str] = None,
    ) -> None:
        """Đóng session và tổng kết artifact."""
        artifact = _read(task_id)
        if not artifact:
            return
        artifact["finished_at"] = time.time()
        artifact["status"] = status
        artifact["token_estimate"] = token_estimate
        artifact["error"] = (error or "")[:300] if error else None

        # Tự tạo summary nếu không được cung cấp
        if summary:
            artifact["summary"] = summary[:500]
        else:
            n_tools = len(artifact["tool_calls"])
            n_files = len(artifact["files_changed"])
            n_steps = len(artifact["plan_steps"])
            duration = round(artifact["finished_at"] - artifact["started_at"], 1)
            artifact["summary"] = (
                f"Hoàn tất trong {duration}s. "
                f"{n_steps} bước kế hoạch, {n_tools} lượt gọi kỹ năng, {n_files} file thay đổi."
            )
        _write(task_id, artifact)
        logger.debug("[ARTIFACT] Session finalized: %s | status=%s", task_id, status)

    @staticmethod
    def get(task_id: str) -> Optional[dict]:
        """Truy xuất artifact của một task theo task_id."""
        return _read(task_id)

    @staticmethod
    def render_markdown(task_id: str) -> str:
        """
        Render artifact thành Markdown có cấu trúc — dùng cho API response
        hoặc hiển thị trong dashboard.
        """
        artifact = _read(task_id)
        if not artifact:
            return f"Không tìm thấy artifact cho task `{task_id}`."

        started = time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(artifact["started_at"]))
        finished = time.strftime("%H:%M:%S", time.localtime(artifact["finished_at"])) if artifact["finished_at"] else "đang chạy"
        duration = round((artifact["finished_at"] or time.time()) - artifact["started_at"], 1)
        status_icon = {"completed": "[DONE]", "failed": "[FAIL]", "aborted": "[ABORTED]", "running": "[RUNNING]"}.get(artifact["status"], "")

        lines = [
            f"# Artifact Report — Task `{task_id}`",
            f"",
            f"**Mục tiêu:** {artifact['goal']}",
            f"**Chế độ:** `{artifact['mode']}` | **Trạng thái:** {status_icon} `{artifact['status']}`",
            f"**Bắt đầu:** {started} | **Kết thúc:** {finished} | **Thời gian:** {duration}s",
            f"",
        ]

        if artifact.get("summary"):
            lines += [f"**Tóm tắt:** {artifact['summary']}", ""]

        if artifact.get("error"):
            lines += [f"> **Lỗi:** {artifact['error']}", ""]

        # Kế hoạch thực thi
        if artifact["plan_steps"]:
            lines += ["## Kế hoạch thực thi", ""]
            lines += ["| Bước | Mô tả | Trạng thái |", "|------|-------|-----------|"]
            for s in artifact["plan_steps"]:
                icon = {"completed": "DONE", "failed": "FAIL", "running": "...", "skipped": "SKIP"}.get(s["status"], s["status"])
                lines.append(f"| `{s['step_id']}` | {s['description']} | {icon} |")
            lines.append("")

        # Các kỹ năng đã gọi
        if artifact["tool_calls"]:
            lines += ["## Kỹ năng đã chạy", ""]
            for tc in artifact["tool_calls"]:
                ok = "OK" if tc["success"] else "FAIL"
                lines.append(f"**`{tc['skill_id']}`** — {tc['duration_ms']}ms | {ok} | Output: {tc['output_length']} ký tự")
                if tc.get("output_preview"):
                    lines.append(f"```\n{tc['output_preview']}\n```")
            lines.append("")

        # Files thay đổi
        if artifact["files_changed"]:
            lines += ["## Files thay đổi", ""]
            created  = [f for f in artifact["files_changed"] if f["change_type"] == "created"]
            modified = [f for f in artifact["files_changed"] if f["change_type"] == "modified"]
            deleted  = [f for f in artifact["files_changed"] if f["change_type"] == "deleted"]
            if created:
                lines.append(f"**Tạo mới ({len(created)} file):**")
                for f in created:
                    sz = f" ({f['size_bytes']} bytes)" if f.get("size_bytes") else ""
                    lines.append(f"- `{f['path']}`{sz}")
            if modified:
                lines.append(f"\n**Sửa đổi ({len(modified)} file):**")
                for f in modified:
                    lines.append(f"- `{f['path']}`")
            if deleted:
                lines.append(f"\n**Xóa ({len(deleted)} file):**")
                for f in deleted:
                    lines.append(f"- `{f['path']}`")
            lines.append("")

        return "\n".join(lines)


# ── INTERNAL HELPERS ────────────────────────────────────────────────────────

def _read(task_id: str) -> Optional[dict]:
    try:
        raw = redis_safe(lambda r: r.get(_redis_key(task_id)), None)
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.warning("[ARTIFACT] Read error for %s: %s", task_id, e)
    return None


def _write(task_id: str, data: dict) -> None:
    try:
        payload = json.dumps(data, ensure_ascii=False)
        redis_safe(lambda r: r.setex(_redis_key(task_id), _TTL_SECONDS, payload))
    except Exception as e:
        logger.warning("[ARTIFACT] Write error for %s: %s", task_id, e)
