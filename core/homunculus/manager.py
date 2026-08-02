import os
import hashlib
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict

class HomunculusManager:
    """
    Manages project-scoped intelligence (Homunculus) and workspace isolation.
    Inspired by ECC-main architecture.
    """
    
    VAULT_DIR = Path(os.getenv("JKAI_VAULT_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "intelligence", "vault")))
    REGISTRY_FILE = VAULT_DIR / "projects.json"
    
    def __init__(self, current_path: str = "."):
        self.current_path = Path(current_path).resolve()
        self.project_root = self._detect_project_root()
        self.zenith_dir = self.project_root / ".zenith"
        self.project_id = self._generate_project_id()
        
        # Ensure base directories exist
        self.VAULT_DIR.mkdir(parents=True, exist_ok=True)
        
    def _detect_project_root(self) -> Path:
        """Detects the project root (Git top-level or current directory)."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=str(self.current_path),
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                return Path(result.stdout.strip()).resolve()
        except FileNotFoundError:
            pass
        
        # Fallback to current directory if not a git repo
        return self.current_path

    def _generate_project_id(self) -> str:
        """Generates a unique project ID or reads from existing DNA."""
        dna_file = self.zenith_dir / "dna.json"
        if dna_file.exists():
            try:
                with open(dna_file, "r", encoding="utf-8") as f:
                    dna = json.load(f)
                    return dna.get("project_id")
            except Exception:
                pass

        hash_source = str(self.project_root)
        
        # Try to get git remote origin URL for a more stable ID
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                hash_source = result.stdout.strip()
        except FileNotFoundError:
            pass
            
        return hashlib.sha256(hash_source.encode("utf-8")).hexdigest()[:12]

    def init_workspace(self):
        """Initializes the .zenith workspace structure."""
        subdirs = [
            "instincts/personal",
            "instincts/inherited",
            "evolved/skills",
            "evolved/commands",
            "evolved/agents",
            "logs",
            "steering"
        ]
        
        for subdir in subdirs:
            (self.zenith_dir / subdir).mkdir(parents=True, exist_ok=True)
            
        # Create a basic DNA file
        dna_file = self.zenith_dir / "dna.json"
        if not dna_file.exists():
            dna = {
                "project_id": self.project_id,
                "project_name": self.project_root.name,
                "project_root": str(self.project_root),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            with open(dna_file, "w", encoding="utf-8") as f:
                json.dump(dna, f, indent=4)
                
        self._update_registry()

    def _update_registry(self):
        """Updates the global projects registry in the Vault."""
        registry = {}
        if self.REGISTRY_FILE.exists():
            try:
                with open(self.REGISTRY_FILE, "r", encoding="utf-8") as f:
                    registry = json.load(f)
            except (json.JSONDecodeError, OSError):
                registry = {}
                
        registry[self.project_id] = {
            "name": self.project_root.name,
            "root": str(self.project_root),
            "last_seen": datetime.now(timezone.utc).isoformat(),
            "zenith_path": str(self.zenith_dir)
        }
        
        with open(self.REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=4)

    def get_project_context(self) -> Dict:
        """Returns the project-scoped context for prompt forging."""
        return {
            "project_id": self.project_id,
            "project_root": str(self.project_root),
            "zenith_dir": str(self.zenith_dir),
            "instincts_dir": str(self.zenith_dir / "instincts"),
            "skills_dir": str(self.zenith_dir / "evolved" / "skills")
        }

if __name__ == "__main__":
    # Self-test
    manager = HomunculusManager()
    print(f"Project Root: {manager.project_root}")
    print(f"Project ID: {manager.project_id}")
    manager.init_workspace()
    print("Workspace initialized.")
