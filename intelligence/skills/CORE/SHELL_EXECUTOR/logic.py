import os
import subprocess
from typing import Dict, Any


def _enforce_terminal_policy(command: str):
    """
    Enforce centralized terminal_policy from .jkairules.json.
    Returns None if allowed, or (status, msg) error dict if blocked.
    """
    try:
        from core.guardrails.terminal_enforcer import check_command
    except Exception:
        return None

    allowed, reason = check_command(command)
    if not allowed:
        return {"status": "error", "msg": f"Security Violation: {reason}"}

    return None


class ShellExecutor:
    def __init__(self):
        self.workspace_root = os.getenv("WORKSPACE_ROOT", "/workspace")
        if not os.path.exists(self.workspace_root):
            self.workspace_root = "d:\\Docker\\JKAI"

    async def execute_command(self, command: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a shell command inside the workspace container.
        """
        # Centralized terminal policy from .jkairules.json
        policy_error = _enforce_terminal_policy(command)
        if policy_error:
            return policy_error

        # Hard fail-safe blacklist (extra layer independent of rules file)
        blacklisted_words = ["rm -rf /", "mkfs", "dd if=", "shutdown", "reboot"]
        if any(w in command for w in blacklisted_words):
            return {"status": "error", "msg": "Security Violation: High-risk command execution blocked."}

        try:
            # Run command inside workspace root directory
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.workspace_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=120
            )

            status = "success" if result.returncode == 0 else "error"
            
            output = result.stdout
            if result.stderr:
                output += f"\nStderr:\n{result.stderr}"

            return {
                "status": status,
                "output": output or "Command executed successfully with no output.",
                "metadata": {
                    "command": command,
                    "exit_code": result.returncode,
                    "cwd": self.workspace_root
                }
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "msg": "Execution Timeout: The command took longer than 120 seconds to execute."}
        except Exception as e:
            return {"status": "error", "msg": f"Error running command: {str(e)}"}

_instance = ShellExecutor()
execute_command = _instance.execute_command
