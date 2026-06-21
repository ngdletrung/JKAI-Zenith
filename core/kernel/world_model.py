"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — CENTRAL TYPED WORLD MODEL                        ║
║   Bản Đồ Thực Tại, Ngôn Ngữ Ràng Buộc DSL & Mô Phỏng Nhân Quả    ║
╚══════════════════════════════════════════════════════════════════╝
*Thuộc Ban Quản Trị Mô Hình Thực Tại & Ràng Buộc Hệ Thống của JKAI. 🌌📐🗺️*
"""

import copy
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple, Set, Optional

from core.kernel.state_machine import TaskState

logger = logging.getLogger("WorldModel")

class NodeType(str, Enum):
    CONTAINER = "CONTAINER"  # Các Docker containers (redis, qdrant, postgres, n8n)
    FILE = "FILE"            # Các tệp tin mã nguồn cốt lõi
    PORT = "PORT"            # Các cổng mạng vật lý/logic
    DATABASE = "DATABASE"    # Kết nối cơ sở dữ liệu

@dataclass
class WorldNode:
    node_id: str
    node_type: NodeType
    properties: Dict[str, Any] = field(default_factory=dict)
    status: str = "HEALTHY"

@dataclass
class WorldEdge:
    source_id: str
    target_id: str
    relation_type: str # ví dụ: "RUNS_ON", "WRITES_TO", "CONNECTS_TO"


class TypedWorldGraph:
    """
    🗺️ [TYPED-WORLD-GRAPH]: Đồ thị Thực tại có Cấu trúc thưa Tổng Giám Đốc.
    Lưu trữ cấu hình thực tế của hệ thống để so khớp chính xác ontology của mô hình.
    """
    def __init__(self):
        self.nodes: Dict[str, WorldNode] = {}
        self.edges: List[WorldEdge] = []

    def add_node(self, node_id: str, node_type: NodeType, properties: Dict[str, Any] = None, status: str = "HEALTHY"):
        self.nodes[node_id] = WorldNode(node_id=node_id, node_type=node_type, properties=properties or {}, status=status)

    def add_edge(self, source_id: str, target_id: str, relation_type: str):
        if source_id in self.nodes and target_id in self.nodes:
            self.edges.append(WorldEdge(source_id=source_id, target_id=target_id, relation_type=relation_type))

    def get_node(self, node_id: str) -> Optional[WorldNode]:
        return self.nodes.get(node_id)

    def get_neighbors(self, node_id: str) -> List[Tuple[WorldNode, str]]:
        """ Trả về danh sách láng giềng và loại mối quan hệ thưa Master. """
        neighbors = []
        for edge in self.edges:
            if edge.source_id == node_id:
                neighbors.append((self.nodes[edge.target_id], edge.relation_type))
            elif edge.target_id == node_id:
                neighbors.append((self.nodes[edge.source_id], edge.relation_type))
        return neighbors

    def clone(self) -> 'TypedWorldGraph':
        """ Tạo bản sao sâu phục vụ mô phỏng phản thực tế thưa Master. """
        return copy.deepcopy(self)


# =====================================================================
# 📐 2. CONSTRAINT DSL RULES ENGINE
# =====================================================================

class ConstraintRule:
    """ Khai báo luật cấu hình DSL dạng declarative thưa Tổng Giám Đốc. """
    def __init__(self, rule_id: str, description: str, check_fn: Any):
        self.rule_id = rule_id
        self.description = description
        self.check_fn = check_fn

    def validate(self, graph: TypedWorldGraph) -> Tuple[bool, str]:
        return self.check_fn(graph)


class ConstraintDSLEngine:
    """
    📐 [CONSTRAINT-DSL-ENGINE]: Động cơ Ràng buộc Hệ thống Tĩnh Bất Biến thưa Master.
    Đảm bảo các luật cốt lõi của doanh nghiệp luôn được duy trì chính xác 100%.
    """
    def __init__(self):
        self.rules: List[ConstraintRule] = []
        self._init_core_rules()

    def add_rule(self, rule_id: str, description: str, check_fn: Any):
        self.rules.append(ConstraintRule(rule_id, description, check_fn))

    def _init_core_rules(self):
        # 1. Luật độc bản cổng mạng (Port Uniqueness)
        def _check_port_uniqueness(graph: TypedWorldGraph) -> Tuple[bool, str]:
            ports: Dict[int, str] = {}
            for node_id, node in graph.nodes.items():
                if node.node_type == NodeType.PORT:
                    port_val = node.properties.get("value")
                    if port_val in ports:
                        return False, f"Vi phạm độc bản cổng: Cổng mạng `{port_val}` đang bị chiếm chấp bởi cả `{ports[port_val]}` và `{node_id}` thưa Master!"
                    ports[port_val] = node_id
            return True, "Xác minh độc bản cổng mạng hoàn hảo thưa Tổng Giám Đốc."

        # 2. Luật ràng buộc tệp tin hệ điều hành không bị xâm hại (Core Integrity)
        def _check_core_integrity(graph: TypedWorldGraph) -> Tuple[bool, str]:
            for node_id, node in graph.nodes.items():
                if node.node_type == NodeType.FILE and node.properties.get("is_kernel", False):
                    if node.status == "CORRUPTED":
                        return False, f"CẢNH BÁO NGUY HIỂM: Tệp tin hạt nhân `{node_id}` bị hỏng hoặc lỗi cú pháp!"
            return True, "Tính toàn vẹn của tệp hạt nhân được bảo toàn."

        # 3. Luật bắt buộc các dịch vụ Docker cốt lõi phải hoạt động (Survival Docker Services)
        def _check_essential_services(graph: TypedWorldGraph) -> Tuple[bool, str]:
            essentials = ["redis-ai", "qdrant"]
            for s in essentials:
                node = graph.get_node(s)
                if not node or node.status != "HEALTHY":
                    return False, f"Vi phạm sinh tồn: Dịch vụ Docker cốt lõi `{s}` bị sập hoặc không tồn tại!"
            return True, "Các dịch vụ sinh tồn lõi đang vận hành ổn định."

        self.add_rule("PORT_UNIQUENESS", "Đảm bảo không trùng lặp cổng mạng vật lý thưa Master.", _check_port_uniqueness)
        self.add_rule("CORE_INTEGRITY", "Đảm bảo tính toàn vẹn của mã nguồn hạt nhân.", _check_core_integrity)
        self.add_rule("ESSENTIAL_SERVICES", "Đảm bảo dịch vụ Docker cốt lõi luôn chạy.", _check_essential_services)

    def validate_graph(self, graph: TypedWorldGraph) -> List[Tuple[str, bool, str]]:
        """ Chạy quét toàn bộ các ràng buộc DSL thưa Master. """
        results = []
        for r in self.rules:
            ok, msg = r.validate(graph)
            results.append((r.rule_id, ok, msg))
        return results


# =====================================================================
# 🔮 3. TRÌNH MÔ PHỎNG PHẢN THỰC TẾ (TEMPORAL SIMULATOR)
# =====================================================================

class TemporalSimulator:
    """
    🔮 [TEMPORAL-SIMULATOR]: Động cơ mô phỏng tương lai phản thực tế thưa Master.
    Cho phép hệ thống dự báo: "Nếu thực hiện hành động A, thì 3 giờ sau tài nguyên ra sao?"
    """
    def __init__(self, dsl_engine: ConstraintDSLEngine):
        self.dsl_engine = dsl_engine

    def simulate_action(self, 
                       graph: TypedWorldGraph, 
                       action_type: str, 
                       target_node_id: str, 
                       proposed_properties: Dict[str, Any]) -> Tuple[bool, str, TypedWorldGraph]:
        """
        🧬 [CHẠY GIẢ LẬP NHÂN QUẢ]:
        Sao chép sâu đồ thị thực tại, áp dụng thay đổi giả định và quét kiểm tra Constraint DSL.
        """
        sim_graph = graph.clone()
        node = sim_graph.get_node(target_node_id)
        
        if not node:
            return False, f"Không tìm thấy thực thể `{target_node_id}` để mô phỏng hành động.", sim_graph

        # Áp dụng thay đổi giả thiết
        if action_type == "UPDATE_PROPERTIES":
            node.properties.update(proposed_properties)
        elif action_type == "CORRUPT_FILE":
            node.status = "CORRUPTED"
        elif action_type == "SHUTDOWN":
            node.status = "DOWN"

        # Quét kiểm tra Constraint DSL trên Đồ thị mô phỏng thưa Master
        results = self.dsl_engine.validate_graph(sim_graph)
        
        for rule_id, ok, msg in results:
            if not ok:
                return False, f"🚨 [MÔ PHỎNG PHÁT HIỆN LỖI] Hành động `{action_type}` trên `{target_node_id}` bị từ chối do vi phạm luật `{rule_id}`! Chi tiết: {msg}", sim_graph

        return True, f"✨ [MÔ PHỎNG THÔNG QUA] Hành động `{action_type}` an toàn. Không phát hiện bất kỳ xung đột hệ thống nào thưa Tổng Giám Đốc.", sim_graph


# =====================================================================
# 🛡️ 4. ĐỘNG CƠ KIỂM CHỨNG ĐIỀU KIỆN BẤT BIẾN (FORMAL INVARIANT ENGINE)
# =====================================================================

class FormalInvariantEngine:
    """
    🛡️ [FORMAL-INVARIANT-ENGINE]: Bộ kiểm chứng điều kiện bất biến toán học thưa Master.
    Đảm bảo các trạng thái pre-conditions và post-conditions của máy trạng thái luôn đúng.
    """
    @staticmethod
    def assert_precondition(state: TaskState, graph: TypedWorldGraph):
        """ Xác định điều kiện bắt buộc trước khi chuyển sang trạng thái mới thưa Master. """
        if state == TaskState.EXECUTING:
            # Precondition: Các dịch vụ lưu trữ phải HEALTHY thì mới được chạy
            redis = graph.get_node("redis-ai")
            if not redis or redis.status != "HEALTHY":
                raise AssertionError("Formal Precondition Violation: Không thể chạy EXECUTING vì Redis-AI đang sập!")
        
        elif state == TaskState.COMMITTING:
            # Precondition: Tuyệt đối không được phép cam kết nếu có file hạt nhân bị CORRUPTED
            for node_id, node in graph.nodes.items():
                if node.node_type == NodeType.FILE and node.properties.get("is_kernel", False):
                    if node.status == "CORRUPTED":
                        raise AssertionError(f"Formal Precondition Violation: Không thể COMMITTING vì tệp hạt nhân `{node_id}` bị hỏng!")

    @staticmethod
    def assert_postcondition(state: TaskState, graph: TypedWorldGraph):
        """ Xác định điều kiện bắt buộc phải đạt được sau khi chuyển sang trạng thái mới thưa Master. """
        if state == TaskState.COMPLETED:
            # Postcondition: Mọi dịch vụ thiết yếu phải hoạt động hoàn hảo sau khi hoàn tất tác vụ
            for s in ["redis-ai", "qdrant"]:
                node = graph.get_node(s)
                if not node or node.status != "HEALTHY":
                    raise AssertionError(f"Formal Postcondition Violation: Tác vụ kết thúc nhưng dịch vụ sinh tồn `{s}` không HEALTHY!")


# =====================================================================
# 🚀 KHỞI TẠO BẢN ĐỒ THỰC TẠI MẶC ĐỊNH
# =====================================================================

def create_default_world_graph() -> TypedWorldGraph:
    """ Tạo bản đồ mặc định của hệ thống phục vụ khởi động thưa Master. """
    wg = TypedWorldGraph()
    # 1. Khai báo các Docker containers
    wg.add_node("redis-ai", NodeType.CONTAINER, {"port": 6379})
    wg.add_node("qdrant", NodeType.CONTAINER, {"port": 6333})
    wg.add_node("postgres-db", NodeType.CONTAINER, {"port": 5432})
    
    # 2. Khai báo các cổng mạng tương ứng thưa Master
    wg.add_node("port-6379", NodeType.PORT, {"value": 6379})
    wg.add_node("port-6333", NodeType.PORT, {"value": 6333})
    wg.add_node("port-5432", NodeType.PORT, {"value": 5432})
    
    # Thiết lập mối quan hệ chạy trên cổng thưa Tổng Giám Đốc
    wg.add_edge("redis-ai", "port-6379", "RUNS_ON")
    wg.add_edge("qdrant", "port-6333", "RUNS_ON")
    wg.add_edge("postgres-db", "port-5432", "RUNS_ON")
    
    # 3. Khai báo các file hạt nhân
    wg.add_node("state_machine.py", NodeType.FILE, {"is_kernel": True})
    wg.add_node("cognitive_scheduler.py", NodeType.FILE, {"is_kernel": True})
    wg.add_node("cognitive_event_bus.py", NodeType.FILE, {"is_kernel": True})
    
    return wg
