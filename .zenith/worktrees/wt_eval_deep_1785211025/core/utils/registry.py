import os

class NeuralRegistry:
    """
    🧬 JKAI ZENITH - NEURAL SERVICE REGISTRY
    Sổ Đăng Ký Tập Trung: Cung cấp URL chính xác cho mọi Dịch vụ nội bộ.
    Tránh hardcode URL rải rác trên toàn hệ thống.
    """
    def __init__(self):
        # Thiết lập các Fallback mặc định cho môi trường Docker Desktop (host.docker.internal)
        # Các biến môi trường sẽ được ưu tiên nếu có.
        self._services = {
            "executor": os.getenv("EXECUTOR_URL", "http://host.docker.internal:8002"),
            "executor_2": os.getenv("EXECUTOR_2_URL", "http://host.docker.internal:8003"),
            "brain": os.getenv("AI_BRAIN_URL", "http://host.docker.internal:8001"),
            "control_plane": os.getenv("AI_CONTROL_PLANE_URL", "http://host.docker.internal:7000"),
            "ollama_gpu": os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434"),
            "ollama_cpu": os.getenv("OLLAMA_CPU_HOST", "http://host.docker.internal:11435"),
            "qdrant": os.getenv("QDRANT_URL", "http://qdrant:6333"),
            "rag": os.getenv("RAG_API_URL", "http://rag-service:8000"),
            "n8n": os.getenv("N8N_HOST", "http://n8n-main:5678"),
        }

    def get_service_url(self, service_name: str) -> str:
        """Lấy URL chuẩn xác cho một service."""
        url = self._services.get(service_name.lower())
        if not url:
            raise ValueError(f"⚠️ [REGISTRY ERROR]: Dịch vụ '{service_name}' chưa được đăng ký trong NeuralRegistry!")
        return url

# Khởi tạo instance độc nhất (Singleton) để mọi file có thể import
registry = NeuralRegistry()
