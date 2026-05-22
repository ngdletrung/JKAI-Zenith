import os
from dotenv import load_dotenv
from typing import Optional
from pathlib import Path

# 🛡️ JKAI ZENITH: INFRASTRUCTURE CONFIGURATION v3.2
# TRIẾT LÝ: CHỈ CẤU HÌNH HẠ TẦNG. Không cấu hình trí tuệ tại đây.

load_dotenv()

# --- [DYNAMIC PATH RESOLUTION] ---
# Phát hiện môi trường Docker hoặc Host
IS_DOCKER = os.path.exists('/.dockerenv')
if IS_DOCKER:
    WORKSPACE_ROOT = "/workspace" if os.path.exists("/workspace") else "/shared"
    INTELLIGENCE_DIR = "/intelligence"
else:
    # 💎 [DYNAMIC-RESOLVER]: Ưu tiên .env -> Tự động nhận diện
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    AUTO_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
    WORKSPACE_ROOT = os.getenv("WORKSPACE_ROOT", AUTO_ROOT)
    INTELLIGENCE_DIR = os.getenv("INTELLIGENCE_DIR", os.path.join(WORKSPACE_ROOT, "intelligence"))

class Settings:
    # Project Info
    PROJECT_NAME: str = "JKAI"
    VERSION: str = "3.2"
    BASE_DIR: str = WORKSPACE_ROOT # Đồng bộ hóa tọa độ cơ sở

    # --- [INFRASTRUCTURE & NETWORK] ---
    _ollama_default = "http://localhost:11434" if not IS_DOCKER else "http://host.docker.internal:11434"
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", f"{_ollama_default}/api/generate")
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", _ollama_default)
    CONTROL_PLANE_URL: Optional[str] = os.getenv("CONTROL_PLANE_URL")
    RAG_API_URL: str = os.getenv("RAG_API_URL", "http://rag-service:8000")

    # Redis (Dùng cho Log & Task Queue)
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost" if not IS_DOCKER else "redis-ai")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))

    # --- [SECURITY & SOVEREIGNTY] ---
    # 🛡️ [PROTECTED]: Mật mã Chủ quyền (HASH-ONLY)
    SOVEREIGN_HASH: str = os.getenv("SOVEREIGN_HASH", "0e94b3de1477fd760e485cf448efbbe3471497d807861eed47ae8295c2f446a2")

    # Timeouts
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "120"))
    EMBED_TIMEOUT: int = int(os.getenv("EMBED_TIMEOUT", "30"))

    # --- [FILESYSTEM PATHS - INTERNAL STORAGE] ---
    _input_dir: str = os.getenv("FILES_INPUT_DIR", os.path.join(WORKSPACE_ROOT, "files/Input"))
    _output_dir: str = os.getenv("FILES_OUTPUT_DIR", os.path.join(WORKSPACE_ROOT, "files/Output"))
    WORKSPACE_ROOT: str = WORKSPACE_ROOT
    INTELLIGENCE_DIR: str = INTELLIGENCE_DIR
    _last_sync: float = 0

    def load_mission_config(self, force=False):
        """💎 [DYNAMIC-SYNC]: Đồng bộ cấu hình từ Workspace tức thì."""
        config_path = os.path.join(self.WORKSPACE_ROOT, "mission_control.json")
        if not os.path.exists(config_path): return False
        
        mtime = os.path.getmtime(config_path)
        if not force and mtime <= self._last_sync: return False

        try:
            import json
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            
            paths = config.get("paths", {})
            if "inputs" in paths: self._input_dir = paths["inputs"]
            if "outputs" in paths: self._output_dir = paths["outputs"]
            
            self._last_sync = mtime
            # print(f"✅ [CONFIG-HOT-RELOAD]: Đã cập nhật lộ trình từ {config_path}")
            return True
        except: return False

    @property
    def INPUT_DIR(self) -> str:
        self.load_mission_config()
        return self._input_dir

    @property
    def OUTPUT_DIR(self) -> str:
        self.load_mission_config()
        return self._output_dir

    def __post_init__(self):
        """Kiểm tra các biến hạ tầng bắt buộc"""
        required = ["OLLAMA_HOST", "REDIS_HOST"]
        missing = [var for var in required if not getattr(self, var)]
        
        if missing:
            raise EnvironmentError(
                f"❌ [CONFIG-ERR] Missing required infrastructure variables: {', '.join(missing)}\n"
                "Vui lòng kiểm tra file .env (Chỉ dành cho Hạ tầng)."
            )
        
        self.load_mission_config(force=True)

settings = Settings()