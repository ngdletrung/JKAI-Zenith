import os
import json
import subprocess
import urllib.request
from typing import Dict, Any

class OfficeAutomator:
    def __init__(self):
        # Resolve workspace root to absolute path on the running OS
        self.workspace_root = os.getenv("WORKSPACE_ROOT", "/workspace")
        self.workspace_root = os.path.abspath(self.workspace_root)
            
        self.bin_dir = os.path.join(self.workspace_root, "bin")
        self.binary_path = os.path.abspath(os.path.join(self.bin_dir, "officecli"))

    def _ensure_binary(self) -> bool:
        """
        Ensures the officecli binary is downloaded and executable.
        """
        if os.path.exists(self.binary_path):
            return True

        os.makedirs(self.bin_dir, exist_ok=True)
        url = "https://github.com/iOfficeAI/OfficeCLI/releases/latest/download/officecli-linux-x64"
        
        try:
            print(f"Downloading OfficeCLI binary from {url}...")
            urllib.request.urlretrieve(url, self.binary_path)
            
            # Set executable permissions (chmod +x)
            os.chmod(self.binary_path, 0o755)
            print(f"OfficeCLI binary successfully downloaded and set to executable at {self.binary_path}.")
            return True
        except Exception as e:
            print(f"Error downloading OfficeCLI: {e}")
            return False

    async def execute_office_cmd(self, action: str, file_path: str, output_path: str = None, data: Any = None, **kwargs) -> Dict[str, Any]:
        """
        Call OfficeCLI to perform create, dump, or merge actions on office files.
        """
        if not self._ensure_binary():
            return {"status": "error", "msg": "Failed to download or configure OfficeCLI binary."}

        # Resolve paths to absolute paths
        target_file = os.path.abspath(os.path.join(self.workspace_root, file_path))
            
        target_output = None
        if output_path:
            target_output = os.path.abspath(os.path.join(self.workspace_root, output_path))

        # Build command list
        cmd = [self.binary_path]
        
        if action == "create":
            cmd.extend(["create", target_file])
            
        elif action == "dump":
            cmd.extend(["dump", target_file, "/"])
            if target_output:
                cmd.extend(["-o", target_output])
                
        elif action == "merge":
            if not target_output:
                return {"status": "error", "msg": "Merge action requires an output_path parameter."}
            if not data:
                return {"status": "error", "msg": "Merge action requires data parameter."}
                
            if isinstance(data, (dict, list)):
                data_str = json.dumps(data)
            else:
                data_str = str(data)
                
            cmd.extend(["merge", target_file, target_output, "--data", data_str])
            
        else:
            return {"status": "error", "msg": f"Unsupported action: {action}. Supported: create, dump, merge."}

        try:
            # Enforce .NET Globalization Invariant mode to avoid ICU dependencies on Debian
            subprocess_env = os.environ.copy()
            subprocess_env["DOTNET_SYSTEM_GLOBALIZATION_INVARIANT"] = "1"

            print(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60,
                cwd=self.workspace_root,
                env=subprocess_env
            )
            
            status = "success" if result.returncode == 0 else "error"
            output = result.stdout
            if result.stderr:
                output += f"\nStderr:\n{result.stderr}"
                
            return {
                "status": status,
                "output": output or "Command completed with no output.",
                "metadata": {
                    "action": action,
                    "file_path": file_path,
                    "output_path": output_path,
                    "exit_code": result.returncode
                }
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "msg": "OfficeCLI command timed out after 60 seconds."}
        except Exception as e:
            return {"status": "error", "msg": f"Error executing OfficeCLI command: {str(e)}"}

_instance = OfficeAutomator()
execute_office_cmd = _instance.execute_office_cmd
