import os
from typing import Dict, Any

class FileWriter:
    def __init__(self):
        self.workspace_root = os.getenv("WORKSPACE_ROOT", "d:\\Docker\\JKAI")

    async def execute_write_file(self, file_path: str, content: str, overwrite: bool = False, **kwargs) -> Dict[str, Any]:
        """
        Lightweight file writer. Creates or overwrites a file at a specific path.
        """
        target_path = file_path
        if not os.path.isabs(target_path):
            target_path = os.path.join(self.workspace_root, target_path)

        # Safety check: avoid writing outside workspace
        target_path = os.path.abspath(target_path)
        workspace_abs = os.path.abspath(self.workspace_root)
        if not target_path.startswith(workspace_abs):
            return {"status": "error", "msg": "Security Violation: Cannot write files outside the workspace directory."}

        if os.path.exists(target_path) and not overwrite:
            return {"status": "error", "msg": f"File already exists: {file_path}. Set overwrite=true to replace it."}

        try:
            # Create parent directories if they don't exist
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(content)

            return {
                "status": "success",
                "output": f"Successfully wrote {len(content)} characters to {file_path}.",
                "metadata": {
                    "file_path": file_path,
                    "content_length": len(content),
                    "overwrite": overwrite
                }
            }
        except Exception as e:
            return {"status": "error", "msg": f"Error writing file: {str(e)}"}

_instance = FileWriter()
execute_write_file = _instance.execute_write_file
