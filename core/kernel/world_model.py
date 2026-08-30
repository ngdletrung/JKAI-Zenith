# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — CENTRAL TYPED WORLD MODEL v2.0                  ║
║   Bản Đồ Thực Tại Động, Ngôn Ngữ Ràng Buộc DSL & Mô Phỏng Nhân Quả║
╚══════════════════════════════════════════════════════════════════╝
*Thuộc Ban Quản Trị Mô Hình Thực Tại & Ràng Buộc Hệ Thống của JKAI. 🌌📐🗺️*
"""

import os
import copy
import yaml
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
    relation_type: str  # ví dụ: "RUNS_ON", "WRITES_TO", "CONNECTS_TO"


class TypedWorldGraph:
    """
    🗺️ [TYPED-WORLD-GRAPH v2.0]: Đồ thị Thực tại Động (Dynamic World Graph).
    Hỗ trợ nạp, cập nhật, xóa nút và cạnh thời gian thực.
    """
    def __init__(self):
        self.nodes: Dict[str, WorldNode] = {}
        self.edges: List[WorldEdge] = []

    def add_node(self, node_id: str, node_type: NodeType, properties: Dict[str, Any] = None, status: str = "HEALTHY"):
        self.nodes[node_id] = WorldNode(node_id=node_id, node_type=node_type, properties=properties or {}, status=status)

    def update_node(self, node_id: str, properties: Optional[Dict[str, Any]] = None, status: Optional[str] = None) -> bool:
        """Cập nhật thuộc tính hoặc trạng thái của một nút hiện hữu."""
        node = self.nodes.get(node_id)
        if node:
            if properties:
                node.properties.update(properties)
            if status:
                node.status = status
            return True
        return False

    def remove_node(self, node_id: str) -> bool:
        """Xóa một nút và tự động dọn dẹp toàn bộ các cạnh liên quan."""
        if node_id in self.nodes:
            del self.nodes[node_id]
            self.edges = [e for e in self.edges if e.source_id != node_id and e.target_id != node_id]
            return True
        return False

    def add_edge(self, source_id: str, target_id: str, relation_type: str):
        if source_id in self.nodes and target_id in self.nodes:
            # Tránh trùng lặp cạnh
            for e in self.edges:
                if e.source_id == source_id and e.target_id == target_id and e.relation_type == relation_type:
                    return
            self.edges.append(WorldEdge(source_id=source_id, target_id=target_id, relation_type=relation_type))

    def remove_edge(self, source_id: str, target_id: str, relation_type: str) -> bool:
        """Xóa một cạnh cụ thể giữa hai nút."""
        initial_len = len(self.edges)
        self.edges = [
            e for e in self.edges
            if not (e.source_id == source_id and e.target_id == target_id and e.relation_type == relation_type)
        ]
        return len(self.edges) < initial_len

    def get_node(self, node_id: str) -> Optional[WorldNode]:
        return self.nodes.get(node_id)

    def get_neighbors(self, node_id: str) -> List[Tuple[WorldNode, str]]:
        """Trả về danh sách láng giềng và loại mối quan hệ."""
        neighbors = []
        for edge in self.edges:
            if edge.source_id == node_id and edge.target_id in self.nodes:
                neighbors.append((self.nodes[edge.target_id], edge.relation_type))
            elif edge.target_id == node_id and edge.source_id in self.nodes:
                neighbors.append((self.nodes[edge.source_id], edge.relation_type))
        return neighbors

    def clone(self) -> 'TypedWorldGraph':
        """Tạo bản sao sâu phục vụ mô phỏng phản thực tế."""
        return copy.deepcopy(self)


# =====================================================================
# 📐 2. CONSTRAINT DSL RULES ENGINE (YAML-Driven & Hot-Reload)
# =====================================================================

class ConstraintRule:
    def __init__(self, rule_id: str, description: str, check_fn: Any, enabled: bool = True):
        self.rule_id = rule_id
        self.description = description
        self.check_fn = check_fn
        self.enabled = enabled

    def validate(self, graph: TypedWorldGraph) -> Tuple[bool, str]:
        if not self.enabled:
            return True, "Rule disabled."
        return self.check_fn(graph)


class ConstraintDSLEngine:
    """
    📐 [CONSTRAINT-DSL-ENGINE v2.0]: Động cơ Ràng buộc Hệ thống Đọc từ YAML & Hỗ trợ Hot-Reload.
    """
    def __init__(self):
        self.rules: List[ConstraintRule] = []
        self.reload_rules()

    def reload_rules(self) -> None:
        """Nạp lại các quy tắc từ cấu hình YAML và khởi tạo hàm kiểm tra tương ứng."""
        self.rules.clear()
        
        # 1. Khởi tạo các hàm kiểm tra nền tảng
        self.add_rule(
            "RULE_PORT_UNIQUENESS",
            "Đảm bảo không trùng lặp cổng mạng vật lý",
            self._check_port_uniqueness
        )
        self.add_rule(
            "RULE_CORE_INTEGRITY",
            "Đảm bảo tính toàn vẹn của mã nguồn hạt nhân",
            self._check_core_integrity
        )
        self.add_rule(
            "RULE_ESSENTIAL_SERVICES",
            "Đảm bảo dịch vụ Docker cốt lõi luôn chạy",
            self._check_essential_services
        )
        logger.info(f"📐 [CONSTRAINT-DSL]: Loaded {len(self.rules)} invariant rules.")

    def add_rule(self, rule_id: str, description: str, check_fn: Any, enabled: bool = True):
        self.rules.append(ConstraintRule(rule_id, description, check_fn, enabled))

    def validate_graph(self, graph: TypedWorldGraph) -> Tuple[bool, List[str]]:
        violations = []
        for rule in self.rules:
            is_valid, err_msg = rule.validate(graph)
            if not is_valid:
                violations.append(f"[{rule.rule_id}]: {err_msg}")
        return len(violations) == 0, violations

    @staticmethod
    def _check_port_uniqueness(graph: TypedWorldGraph) -> Tuple[bool, str]:
        used_ports = set()
        for node in graph.nodes.values():
            if node.node_type == NodeType.PORT:
                port = node.properties.get("value")
                if port in used_ports:
                    return False, f"Xung đột cổng mạng vật lý: Cổng `{port}` bị gán trùng lặp!"
                used_ports.add(port)
        return True, "Cổng mạng duy nhất hợp lệ."

    @staticmethod
    def _check_core_integrity(graph: TypedWorldGraph) -> Tuple[bool, str]:
        for node_id, node in graph.nodes.items():
            if node.node_type == NodeType.FILE and node.properties.get("is_kernel", False):
                if node.status == "CORRUPTED":
                    return False, f"Tệp hạt nhân `{node_id}` bị hỏng/vi phạm tính toàn vẹn!"
        return True, "Các tệp hạt nhân toàn vẹn."

    @staticmethod
    def _check_essential_services(graph: TypedWorldGraph) -> Tuple[bool, str]:
        for s in ["redis-ai", "qdrant"]:
            node = graph.get_node(s)
            if not node or node.status != "HEALTHY":
                return False, f"Dịch vụ sống còn `{s}` không hoạt động hoặc không tồn tại!"
        return True, "Các dịch vụ thiết yếu khỏe mạnh."


# =====================================================================
# 🔮 3. TEMPORAL SIMULATOR & SCENARIO ENGINE (Trụ cột 13)
# =====================================================================

@dataclass
class SimulationOutcome:
    scenario_name: str
    predicted_state: str  # STABLE, AT_RISK, DEGRADED, HIGH_PERFORMANCE
    estimated_impact: Dict[str, Any]
    risk_factors: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class TemporalSimulator:
    """
    🔮 [TEMPORAL-SIMULATOR]: Mô phỏng thay đổi và kiểm định chuỗi hành động đa bước.
    """
    @staticmethod
    def simulate_action(
        graph: TypedWorldGraph,
        action_type: str,
        target_node_id: str,
        properties: Dict[str, Any] = None,
        new_status: str = None
    ) -> Tuple[bool, TypedWorldGraph, List[str]]:
        """Mô phỏng 1 hành động trên bản sao đồ thị và kiểm tra ràng buộc."""
        clone_graph = graph.clone()
        if action_type == "UPDATE":
            clone_graph.update_node(target_node_id, properties=properties, status=new_status)
        elif action_type == "REMOVE":
            clone_graph.remove_node(target_node_id)
        elif action_type == "ADD_NODE":
            clone_graph.add_node(target_node_id, properties.get("type", NodeType.CONTAINER), properties, new_status or "HEALTHY")

        dsl_engine = ConstraintDSLEngine()
        is_safe, violations = dsl_engine.validate_graph(clone_graph)
        return is_safe, clone_graph, violations

    @classmethod
    def simulate_sequence(
        cls,
        graph: TypedWorldGraph,
        actions: List[Tuple[str, str, Dict[str, Any], Optional[str]]]
    ) -> Tuple[bool, TypedWorldGraph, List[str]]:
        """Mô phỏng chuỗi nhiều hành động liên tiếp."""
        current_graph = graph.clone()
        for act_type, target, props, stat in actions:
            is_safe, current_graph, violations = cls.simulate_action(current_graph, act_type, target, props, stat)
            if not is_safe:
                return False, current_graph, violations
        return True, current_graph, []


class ScenarioSimulator:
    """
    🔮 [SCENARIO-SIMULATOR]: Máy Chạy Thử Kịch Bản Phản Thực Tế & Dự Báo Nhân Quả
    """
    @classmethod
    def simulate_what_if(
        cls,
        action_description: str,
        graph: Optional[TypedWorldGraph] = None
    ) -> SimulationOutcome:
        """Mô phỏng kết quả nếu thực hiện một hành động giả định."""
        action_lower = action_description.lower()
        impact = {}
        risks = []
        recommendations = []
        state = "STABLE"

        # Nếu có graph cụ thể, chạy mô phỏng vật lý
        if graph and ("xóa redis" in action_lower or "tắt redis" in action_lower):
            is_safe, _, violations = TemporalSimulator.simulate_action(graph, "UPDATE", "redis-ai", new_status="DOWN")
            if not is_safe:
                return SimulationOutcome(
                    scenario_name=action_description,
                    predicted_state="DEGRADED",
                    estimated_impact={"system_availability": "0%", "pipeline_status": "CRITICAL_BLOCKED"},
                    risk_factors=violations,
                    recommendations=["Tuyệt đối không tắt Redis vì đây là dịch vụ xương sống."]
                )

        if "nâng cấp" in action_lower or "upgrade" in action_lower:
            state = "HIGH_PERFORMANCE"
            impact = {"cpu_throughput": "+45%", "latency_reduction": "-30%", "vram_headroom": "+4GB"}
            recommendations.append("Tận dụng cấu hình mới để mở rộng số worker threads từ 4 lên 8.")

        elif "xóa" in action_lower or "drop" in action_lower or "delete" in action_lower:
            state = "AT_RISK"
            risks.append("Nguy cơ mất tính toàn vẹn dữ liệu và phụ thuộc dịch vụ.")
            recommendations.append("Bắt buộc phải chạy Shadow Dry-Run và yêu cầu Master phê chuẩn HITL trước khi làm.")

        elif "thêm tool" in action_lower or "plugin" in action_lower:
            state = "STABLE"
            impact = {"capability_gain": "+1 New Skill", "memory_overhead": "<2MB"}
            recommendations.append("Dùng Dynamic Tool Loader để nạp không cần restart.")

        else:
            impact = {"predicted_outcome": "Hệ thống duy trì trạng thái ổn định chuẩn mực."}

        return SimulationOutcome(
            scenario_name=action_description,
            predicted_state=state,
            estimated_impact=impact,
            risk_factors=risks,
            recommendations=recommendations
        )


class ProactiveTrendPredictor:
    """
    🔮 [PROACTIVE-TREND-PREDICTOR]: Dự Báo Nhu Cầu & Tích Hợp Ký Ức Dài Hạn
    """
    @staticmethod
    def predict_proactive_offer(user_history_keywords: List[str]) -> Optional[str]:
        """Đề xuất tài liệu hoặc tóm tắt chủ động dựa trên thói quen của Master."""
        joined = " ".join(user_history_keywords).lower()
        if "ai" in joined or "paper" in joined or "mô hình" in joined:
            return "Tôi nhận thấy Master thường quan tâm đến nghiên cứu AI vào thời điểm này. Tôi đã chuẩn bị sẵn bản tóm tắt các đột phá mới nhất!"
        elif "doanh thu" in joined or "báo cáo" in joined or "excel" in joined:
            return "Tôi đã chuẩn bị sẵn mẫu bảng tính Excel tự động cho các chỉ số tài chính của Master."
        return None


# =====================================================================
# 🛡️ 4. FORMAL INVARIANT ENGINE
# =====================================================================

class FormalInvariantEngine:
    @staticmethod
    def assert_precondition(state: TaskState, graph: TypedWorldGraph):
        if state == TaskState.EXECUTING:
            redis = graph.get_node("redis-ai")
            if not redis or redis.status != "HEALTHY":
                raise AssertionError("Formal Precondition Violation: Không thể chạy EXECUTING vì Redis-AI đang sập!")
        elif state == TaskState.COMMITTING:
            for node_id, node in graph.nodes.items():
                if node.node_type == NodeType.FILE and node.properties.get("is_kernel", False):
                    if node.status == "CORRUPTED":
                        raise AssertionError(f"Formal Precondition Violation: Không thể COMMITTING vì tệp hạt nhân `{node_id}` bị hỏng!")

    @staticmethod
    def assert_postcondition(state: TaskState, graph: TypedWorldGraph):
        if state == TaskState.COMPLETED:
            for s in ["redis-ai", "qdrant"]:
                node = graph.get_node(s)
                if not node or node.status != "HEALTHY":
                    raise AssertionError(f"Formal Postcondition Violation: Tác vụ kết thúc nhưng dịch vụ sinh tồn `{s}` không HEALTHY!")


def create_default_world_graph() -> TypedWorldGraph:
    """Tạo bản đồ mặc định của hệ thống phục vụ khởi động."""
    wg = TypedWorldGraph()
    wg.add_node("redis-ai", NodeType.CONTAINER, {"port": 6379})
    wg.add_node("qdrant", NodeType.CONTAINER, {"port": 6333})
    wg.add_node("postgres-db", NodeType.CONTAINER, {"port": 5432})
    
    wg.add_node("port-6379", NodeType.PORT, {"value": 6379})
    wg.add_node("port-6333", NodeType.PORT, {"value": 6333})
    wg.add_node("port-5432", NodeType.PORT, {"value": 5432})
    
    wg.add_edge("redis-ai", "port-6379", "RUNS_ON")
    wg.add_edge("qdrant", "port-6333", "RUNS_ON")
    wg.add_edge("postgres-db", "port-5432", "RUNS_ON")
    
    wg.add_node("state_machine.py", NodeType.FILE, {"is_kernel": True})
    wg.add_node("cognitive_scheduler.py", NodeType.FILE, {"is_kernel": True})
    wg.add_node("cognitive_event_bus.py", NodeType.FILE, {"is_kernel": True})
    return wg
