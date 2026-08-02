import os
from typing import Dict, Any, List
from core.utils.repo_surgeon import grep_repo

class CodeGrep:
    async def execute_grep(self, query: str, max_hits: int = 25, **kwargs) -> Dict[str, Any]:
        """
        Fast grep utility to search keywords across files in the workspace.
        """
        if not query:
            return {"status": "error", "msg": "Query parameter cannot be empty."}

        try:
            keywords = [query]
            hits = grep_repo(keywords, max_hits=int(max_hits))

            if not hits:
                return {
                    "status": "success",
                    "output": "No matches found in the workspace.",
                    "metadata": {"query": query, "hits_count": 0}
                }

            formatted_lines = []
            for h in hits:
                formatted_lines.append(f"File: {h['path']}:{h['line']}\nMatch: {h['snippet']}\n")

            return {
                "status": "success",
                "output": "\n".join(formatted_lines),
                "metadata": {
                    "query": query,
                    "hits_count": len(hits)
                }
            }
        except Exception as e:
            return {"status": "error", "msg": f"Grep execution failed: {str(e)}"}

_instance = CodeGrep()
execute_grep = _instance.execute_grep
