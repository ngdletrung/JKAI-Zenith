import os
import sys
import json
import logging

logger = logging.getLogger("OfficeCLIIntegration")

# Import OfficeCLI SDK from local repository path
OFFICECLI_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "files", "OfficeCLI-main", "sdk", "python"))
if OFFICECLI_DIR not in sys.path:
    sys.path.insert(0, OFFICECLI_DIR)

def execute_officecli_command(file_path: str, commands: list = None) -> dict:
    """
    🏢 Native OfficeCLI Pipe Engine Integration Tool.
    Cho phép tác tử gửi trực tiếp các lệnh batch (set, get, add_chart, save) qua Pipe thời gian thực.
    """
    commands = commands or []
    try:
        import officecli
        is_new = not os.path.exists(file_path)
        ctx_manager = officecli.create(file_path, "--force") if is_new else officecli.open(file_path)
        
        with ctx_manager as doc:
            results = []
            for cmd in commands:
                res = doc.send(cmd)
                results.append(res)
            doc.send({"command": "save"})
            
        return {
            "status": "success",
            "file_path": file_path,
            "results": results
        }
    except Exception as e:
        logger.error(f"[OFFICECLI-ERR] OfficeCLI resident pipe error: {e}")
        return {
            "status": "error",
            "message": f"OfficeCLI error: {e}"
        }
