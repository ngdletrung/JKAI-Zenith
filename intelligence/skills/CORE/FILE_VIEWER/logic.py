import os
from typing import Dict, Any

class FileViewer:
    def __init__(self):
        self.workspace_root = os.getenv("WORKSPACE_ROOT", "d:\\Docker\\JKAI")

    async def execute_view_file(self, file_path: str, start_line: int = 1, end_line: int = None, **kwargs) -> Dict[str, Any]:
        """
        Precise, lightweight file viewer. Returns file content with line numbers.
        """
        target_path = file_path
        if not os.path.isabs(target_path):
            target_path = os.path.join(self.workspace_root, target_path)

        if not os.path.exists(target_path) or not os.path.isfile(target_path):
            return {"status": "error", "msg": f"File does not exist: {target_path}"}

        try:
            with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            total_lines = len(lines)
            start = max(1, int(start_line))
            
            if end_line is None:
                end = min(total_lines, start + 200)
            else:
                end = min(total_lines, max(start, int(end_line)))

            selected_lines = lines[start - 1:end]
            formatted_content = "".join([f"{i}: {line}" for i, line in enumerate(selected_lines, start)])

            return {
                "status": "success",
                "output": formatted_content,
                "metadata": {
                    "file_path": file_path,
                    "start_line": start,
                    "end_line": end,
                    "total_lines": total_lines
                }
            }
        except Exception as e:
            return {"status": "error", "msg": f"Error reading file: {str(e)}"}

_instance = FileViewer()
execute_view_file = _instance.execute_view_file
