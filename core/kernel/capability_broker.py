import os
import sys
import uuid
import time
import subprocess
import logging
from enum import Enum
from typing import Dict, Any, List, Set, Tuple, Optional
from pydantic import BaseModel, Field
from core.kernel.models import MissionContext

logger = logging.getLogger("CapabilityBroker")

class CapabilityType(str, Enum):
    FILESYSTEM = "FILESYSTEM"
    NETWORK = "NETWORK"
    EXECUTION = "EXECUTION"


class CapabilityToken(BaseModel):
    """🎫 Vé quyền hạn do CapabilityBroker phát hành cho một tác vụ."""
    token_id: str = Field(default_factory=lambda: f"cap-{uuid.uuid4().hex[:12]}")
    task_id: str = "sys"
    cap_type: CapabilityType = CapabilityType.EXECUTION
    scope: str = ""
    issued_at: float = Field(default_factory=time.time)

class CapabilityProvider(BaseModel):
    """
    🏢 CapabilityProvider: Đại diện cho một nhà cung cấp công cụ/dịch vụ cụ thể
    """
    name: str = Field(..., description="Tên nhà cung cấp, ví dụ: 'Tavily', 'Brave', 'LocalFS'")
    capability: str = Field(..., description="Năng lực hỗ trợ, ví dụ: 'web_search'")
    latency_score: float = Field(default=1.0, description="Điểm đánh giá độ trễ (thấp là tốt)")
    cost_per_call: float = Field(default=0.0, description="Chi phí ước tính cho mỗi lần gọi (USD)")
    is_offline: bool = Field(default=False, description="Có khả năng chạy ngoại tuyến không")
    required_api_keys: List[str] = Field(default_factory=list, description="Các API keys cần thiết")
    tool_callable_path: str = Field(..., description="Đường dẫn đến file/module thực thi tool")


class CapabilityRegistry:
    """
    📚 CapabilityRegistry: Danh bạ trung tâm quản lý các Capabilities và Providers của JKAI
    """
    def __init__(self):
        self._providers: Dict[str, List[CapabilityProvider]] = {}
        self._initialize_default_registry()

    def _initialize_default_registry(self):
        """Khởi tạo các công cụ mặc định của hệ thống"""
        # Capability: web_search
        self.register_provider(CapabilityProvider(
            name="Tavily",
            capability="web_search",
            latency_score=0.8,
            cost_per_call=0.005,
            is_offline=False,
            required_api_keys=["TAVILY_API_KEY"],
            tool_callable_path="tools.web.tavily_search"
        ))
        self.register_provider(CapabilityProvider(
            name="LocalSearch",
            capability="web_search",
            latency_score=0.2,
            cost_per_call=0.0,
            is_offline=True,
            required_api_keys=[],
            tool_callable_path="tools.web.local_search"
        ))
        
        # Capability: read_code
        self.register_provider(CapabilityProvider(
            name="LocalReader",
            capability="read_code",
            latency_score=0.1,
            cost_per_call=0.0,
            is_offline=True,
            required_api_keys=[],
            tool_callable_path="tools.file.read_file"
        ))

        # Capability: write_code
        self.register_provider(CapabilityProvider(
            name="LocalWriter",
            capability="write_code",
            latency_score=0.1,
            cost_per_call=0.0,
            is_offline=True,
            required_api_keys=[],
            tool_callable_path="tools.file.write_file"
        ))

    def register_provider(self, provider: CapabilityProvider):
        cap = provider.capability
        if cap not in self._providers:
            self._providers[cap] = []
        self._providers[cap].append(provider)
        logger.info(f"➕ Đã đăng ký Provider '{provider.name}' cho Capability '{cap}'")

    def get_providers_for(self, capability: str) -> List[CapabilityProvider]:
        return self._providers.get(capability, [])


class PolicyEngine:
    """
    🛡️ PolicyEngine: Động cơ kiểm chứng chính sách an toàn (Formal Safety Engine)
    """
    @staticmethod
    def prove_static_safety(code_content: str, allowed_scopes: List[str]) -> Tuple[bool, str]:
        """Phân tích tĩnh mã nguồn trước khi thực thi (AST validation cơ bản)"""
        dangerous_calls = ["shutil.rmtree", "os.remove", "os.rmdir", "subprocess.Popen", "os.system"]
        
        # 1. Chặn việc thực thi shell tự do hoặc xóa file nếu nằm ngoài scope cho phép
        if "*" not in allowed_scopes:
            for call in dangerous_calls:
                if call in code_content:
                    return False, f"Vi phạm Chính sách An Toàn: Phát hiện lệnh cấm `{call}`"
                    
            if "open(" in code_content and "w" in code_content:
                # Ngăn chặn ghi file ra ngoài thư mục sandbox/scratch được chỉ định
                if ".." in code_content or "/" in code_content or "\\" in code_content:
                    if not any(folder in code_content for folder in ["scratch", "sandbox", "test"]):
                        return False, "Vi phạm Chính sách An Toàn: Cố gắng ghi file ngoài phạm vi Sandbox cho phép."
                        
        return True, "Approved"

    @staticmethod
    def enforce_dynamic_policy(capability: str, provider: CapabilityProvider, context: MissionContext) -> Tuple[bool, str]:
        """Kiểm tra chính sách an toàn động dựa trên ngữ cảnh chạy thực tế"""
        # 1. Kiểm tra chính sách Offline Mode
        is_offline_mode = context.preferences.get("offline_mode", False)
        if is_offline_mode and not provider.is_offline:
            return False, f"Chính sách Offline: Trình cung cấp '{provider.name}' yêu cầu kết nối mạng nhưng hệ thống đang ở Offline Mode."

        # 2. Kiểm tra chính sách cấm truy cập mạng (Network Policy)
        if "no_network" in context.policies and not provider.is_offline:
            return False, f"Chính sách Bảo Mật: Tác vụ '{capability}' bị chặn kết nối mạng theo chính sách 'no_network'."

        # 3. Kiểm tra chính sách ghi đĩa (Disk Write Policy)
        if "read_only" in context.policies and capability in ["write_code", "delete_file"]:
            return False, "Chính sách Bảo Mật: Hệ thống đang chạy ở chế độ Read-Only, cấm thực thi thao tác ghi đĩa."

        return True, "Approved"


class ResourceManager:
    """
    💰 ResourceManager: Quản lý ngân sách tài nguyên (Tokens, API costs, v.v.)
    """
    def __init__(self):
        self.used_tokens = 0
        self.used_cost_usd = 0.0

    def check_budget(self, context: MissionContext, estimated_cost: float = 0.0) -> Tuple[bool, str]:
        """Kiểm tra xem hệ thống có bị vượt quá Budget đã định sẵn không (bao gồm chi phí ước tính)"""
        if context.budget_tokens and self.used_tokens >= context.budget_tokens:
            return False, f"Vượt quá ngân sách: Đã dùng {self.used_tokens} tokens (Giới hạn: {context.budget_tokens})"
            
        projected_cost = self.used_cost_usd + estimated_cost
        if context.budget_usd and projected_cost > context.budget_usd:
            return False, f"Vượt quá ngân sách: Chi phí dự kiến {projected_cost:.4f} USD vượt hạn mức {context.budget_usd} USD"
            
        return True, "Ok"

    def record_usage(self, tokens: int, cost: float):
        self.used_tokens += tokens
        self.used_cost_usd += cost


class CapabilityBroker:
    """
    🏢 CapabilityBroker: Điều phối, chọn lựa nhà cung cấp và phát hành vé quyền hạn
    """
    def __init__(self, registry: Optional[CapabilityRegistry] = None):
        self.registry = registry or CapabilityRegistry()
        self.resource_manager = ResourceManager()
        self._issued_tokens: Dict[str, CapabilityToken] = {}

    def select_provider(self, capability: str, context: MissionContext) -> CapabilityProvider:
        """
        🎯 Chọn Provider tốt nhất phù hợp với Context và Policy hiện tại
        """
        providers = self.registry.get_providers_for(capability)
        if not providers:
            raise ValueError(f"Lỗi: Không tìm thấy bất kỳ Provider nào hỗ trợ năng lực '{capability}'")

        valid_providers = []
        for p in providers:
            # 1. Kiểm tra API Keys yêu cầu
            has_keys = True
            for key in p.required_api_keys:
                if not os.getenv(key):
                    has_keys = False
                    break
            
            if not has_keys and not p.is_offline:
                # Nếu thiếu API key và không phải offline tool thì bỏ qua
                continue

            # 2. Kiểm tra Policy
            allowed, _ = PolicyEngine.enforce_dynamic_policy(capability, p, context)
            if allowed:
                valid_providers.append(p)

        if not valid_providers:
            raise PermissionError(f"Chính sách bảo mật chặn toàn bộ các nhà cung cấp cho năng lực '{capability}'")

        # 3. Lựa chọn tối ưu: ưu tiên offline nếu được yêu cầu, sau đó ưu tiên chi phí thấp nhất, rồi đến latency tốt nhất
        # Sắp xếp các provider dựa trên chi phí (tăng dần) và độ trễ (tăng dần)
        valid_providers.sort(key=lambda x: (x.cost_per_call, x.latency_score))
        return valid_providers[0]

    def issue_token(self, task_id: str, cap_type: CapabilityType, scope: str = "") -> CapabilityToken:
        """🎫 Cấp phát vé quyền hạn (Capability Token) cho tác vụ trong phạm vi scope."""
        token = CapabilityToken(task_id=task_id, cap_type=cap_type, scope=scope)
        self._issued_tokens[token.token_id] = token
        return token

    def verify_privilege(self, token_id: str, cap_type: CapabilityType, resource: str = "") -> bool:
        """
        🛡️ Xác minh vé quyền hạn: token tồn tại và khớp loại năng lực.
        Nếu resource nằm ngoài scope đã cấp thì từ chối.
        """
        token = self._issued_tokens.get(token_id)
        if token is None:
            return False
        if token.cap_type != cap_type:
            return False
        if token.scope and resource:
            res_norm = resource.replace("\\", "/").lower().rstrip("/")
            scope_norm = token.scope.replace("\\", "/").lower().rstrip("/")
            if not res_norm.startswith(scope_norm):
                return False
        return True


capability_broker = CapabilityBroker()
