import os
import json
from typing import Dict, Any, List
from core.utils.repo_surgeon import apply_repo_patches

class RepoSurgeon:
    async def execute_repo_patch(self, patches: Any, dry_run: bool = False, task_id: str = "sys", **kwargs) -> Dict[str, Any]:
        """
        Safely applies AST-validated and test-verified code edits to files.
        """
        if isinstance(patches, str):
            try:
                parsed_patches = json.loads(patches)
            except Exception as e:
                return {"status": "error", "msg": f"Failed to parse patches JSON string: {str(e)}"}
        else:
            parsed_patches = patches

        if not isinstance(parsed_patches, list):
            return {"status": "error", "msg": "Patches parameter must be a list of objects, e.g. [{'path': '...', 'content': '...'}]"}

        try:
            report, promoted = await apply_repo_patches(parsed_patches, dry_run=dry_run, task_id=task_id)
            
            status = "success"
            if "❌" in report or "Error" in report:
                status = "error"

            return {
                "status": status,
                "output": report,
                "metadata": {
                    "promoted_files": promoted,
                    "dry_run": dry_run,
                    "patches_count": len(parsed_patches)
                }
            }
        except Exception as e:
            return {"status": "error", "msg": f"RepoSurgeon execution failed: {str(e)}"}

_instance = RepoSurgeon()
execute_repo_patch = _instance.execute_repo_patch
