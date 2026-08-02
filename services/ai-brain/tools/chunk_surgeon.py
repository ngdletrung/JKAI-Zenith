import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger("ChunkSurgeon")

class ChunkSurgeon:
    """
    [CHUNK SURGEON ENGINE]
    Mô-đun can thiệp mã nguồn phi liên tục theo từng cụm đoạn ngắn (Multi-Chunk Surgery).
    Giải pháp thay thế cho phương pháp sinh lại toàn bộ tệp tin, tối ưu cho mô hình Qwen3-30B
    hoạt động trên phần cứng AMD RX6600 8GB VRAM (gián đoạn sampling token và giảm trễ hệ thống).
    """

    @classmethod
    def apply_chunk_edits(cls, file_path: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Thực hiện phẫu thuật cắt/vá từng chuỗi mã nguồn trên tệp chỉ định.
        Mỗi chunk yêu cầu các trường:
            - StartLine (int): Dòng bắt đầu tìm kiếm (1-indexed)
            - EndLine (int): Dòng kết thúc tìm kiếm (1-indexed, inclusive)
            - TargetContent (str): Chuỗi chính xác cần được thay thế
            - ReplacementContent (str): Chuỗi mã mới thay thế
        """
        if not os.path.exists(file_path):
            return {"status": "error", "error": f"Tệp tin không tồn tại: {file_path}"}
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return {"status": "error", "error": f"Không thể đọc tệp tin {file_path}: {str(e)}"}

        lines = content.splitlines(keepends=True)
        total_lines = len(lines)

        applied_chunks = 0
        modified_lines_count = 0

        current_content = content

        for i, chunk in enumerate(chunks):
            start_line = max(1, int(chunk.get("StartLine", 1))) - 1
            end_line = min(total_lines, int(chunk.get("EndLine", total_lines)))
            target = chunk.get("TargetContent", "")
            replacement = chunk.get("ReplacementContent", "")

            if not target:
                continue

            range_content = "".join(lines[start_line:end_line])
            if target not in range_content and target not in current_content:
                if target not in current_content:
                    return {
                        "status": "error",
                        "error": f"Chunk #{i+1}: Không tìm thấy 'TargetContent' trong phạm vi dòng [{start_line+1}-{end_line}]. Phẫu thuật bị từ chối để bảo vệ toàn vẹn tệp.",
                        "failed_chunk_index": i
                    }

            if current_content.count(target) > 1 and target in range_content:
                new_range = range_content.replace(target, replacement, 1)
                prefix = "".join(lines[:start_line])
                suffix = "".join(lines[end_line:])
                current_content = prefix + new_range + suffix
                lines = current_content.splitlines(keepends=True)
                total_lines = len(lines)
            else:
                current_content = current_content.replace(target, replacement, 1)
                lines = current_content.splitlines(keepends=True)
                total_lines = len(lines)

            applied_chunks += 1
            modified_lines_count += abs(len(replacement.splitlines()) - len(target.splitlines())) + len(replacement.splitlines())

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(current_content)
        except Exception as write_err:
            return {"status": "error", "error": f"Lỗi ghi tệp tin sau phẫu thuật: {str(write_err)}"}

        summary_msg = f"[CHUNK-SURGEON-SUCCESS]: Đã phẫu thuật thành công {applied_chunks}/{len(chunks)} chuỗi khối. Biến đổi ~{modified_lines_count} dòng mã trên {os.path.basename(file_path)}."
        logger.info(summary_msg)

        return {
            "status": "success",
            "chunks_applied": applied_chunks,
            "file_path": file_path,
            "summary": summary_msg
        }
