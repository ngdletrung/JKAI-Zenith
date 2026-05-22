import os
# =================================================================
# 🧬 JKAI ZENITH: LOGIC PHẪU THUẬT ĐA TẦNG v31.0 (QUANTUM SURGERY)
# =================================================================

def phau_thuat_datang(path: str, chunks: list, validate_syntax: bool = True):
    """
    🏥 [QUANTUM-SURGERY]: Thực hiện phẫu thuật chính xác đến từng nơ-ron.
    Giao thức v31.0: Backup -> Diff -> Surgery -> Syntax Check -> Atomic Commit
    """
    # 🏛️ [IRON LAW OF SOVEREIGNTY]: Cấm AI chỉnh sửa các file kiểm soát tối cao
    IMMUTABLE_FILES = ["watchdog.py", "main.py", "hitl_manager.py", "SOVEREIGN_CORE.py", "skill_phauthuat_datang"]
    for forbidden in IMMUTABLE_FILES:
        if forbidden in path:
            return {"status": "error", "msg": "⛔ [VI PHẠM ĐỊNH LUẬT SẮT]: Tệp tin này thuộc Giao thức Kiểm soát Tối cao. AI không có quyền chỉnh sửa!"}

    try:
        if not os.path.exists(path):
            return {"status": "error", "msg": f"Tệp tin không tồn tại: {path}"}

        import ast
        import shutil
        from pathlib import Path

        with open(path, "r", encoding="utf-8") as f:
            original_content = f.read()

        new_content = original_content
        changes_made = 0
        failed_chunks = []

        for i, chunk in enumerate(chunks):
            target = chunk.get("target", "").strip("\n")
            replacement = chunk.get("replacement", "").strip("\n")

            if not target: continue

            # 🧬 [SMART-MATCH v31.0]: Tìm kiếm chính xác bao gồm cả Indentation
            if target in new_content:
                # Kiểm tra an toàn: Nếu target quá ngắn, yêu cầu thêm context
                if len(target) < 10 and new_content.count(target) > 1:
                    failed_chunks.append({"index": i + 1, "error": "Target quá ngắn và bị trùng lặp. Cần thêm bối cảnh."})
                    continue
                
                new_content = new_content.replace(target, replacement, 1)
                changes_made += 1
            else:
                failed_chunks.append({"index": i + 1, "error": "Không tìm thấy đoạn mã mục tiêu (Mismatched context)."})

        if changes_made == 0:
            return {"status": "error", "msg": "Phẫu thuật thất bại: Không tìm thấy mục tiêu.", "details": failed_chunks}

        # 🛡️ [SYNTAX-GUARD]: Kiểm tra tính toàn vẹn của mã nguồn
        if validate_syntax and path.endswith(".py"):
            try:
                ast.parse(new_content)
            except Exception as syntax_err:
                return {
                    "status": "blocked",
                    "msg": "❌ [SYNTAX-BLOCK]: Phẫu thuật bị hủy bỏ vì gây lỗi cú pháp Python.",
                    "error": str(syntax_err)
                }

        # 💾 [ATOMIC-COMMIT]: Ghi file an toàn tuyệt đối
        backup_dir = Path(os.getenv("WORKSPACE_ROOT", "D:/Docker/N8N") + "/archive/backups")
        backup_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        backup_file = backup_dir / f"{Path(path).name}.{ts}.bak"
        
        # Sao lưu bản gốc
        Path(backup_file).write_text(original_content, encoding="utf-8")

        # Ghi bản mới qua tệp tạm để tránh hỏng file
        temp_file = Path(path).with_suffix(".tmp")
        temp_file.write_text(new_content, encoding="utf-8")
        shutil.move(str(temp_file), path)

        return {
            "status": "success",
            "version": "31.0",
            "changes": changes_made,
            "backup": str(backup_file),
            "msg": f"💎 [QUANTUM-OK]: Đã phẫu thuật thành công {changes_made} điểm. Hệ thống đã được kiểm định cú pháp."
        }

    except Exception as e:
        return {"status": "error", "msg": f"Sự cố phẫu thuật Quantum: {str(e)}"}
