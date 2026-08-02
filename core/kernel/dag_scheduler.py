import asyncio
import logging
from typing import Dict, List, Set, Any, Callable, Coroutine, Optional
from core.kernel.models import (
    MissionPlan,
    MissionNode,
    MissionNodeState,
    MissionEvent,
    EventType,
    MissionContext
)
from core.kernel.event_store import EventStore
from core.kernel.capability_broker import CapabilityBroker

logger = logging.getLogger("DAGScheduler")

class ValidationFailedException(Exception):
    """
    ⚠️ Ngoại lệ ném ra khi một Validation Node phát hiện kết quả của node cha không đạt yêu cầu.
    target_node_id: ID của node cần được yêu cầu chạy lại (Retry).
    """
    def __init__(self, target_node_id: str, reason: str):
        super().__init__(f"Validation failed for node {target_node_id}: {reason}")
        self.target_node_id = target_node_id
        self.reason = reason


class DAGScheduler:
    """
    📅 DAGScheduler: Bộ lập lịch thực thi song song các node trong đồ thị MissionPlan (DAG).
    Hỗ trợ Context Policy, Validation Nodes và Self-Correction Loop.
    """
    def __init__(self, event_store: EventStore, capability_broker: CapabilityBroker):
        self.event_store = event_store
        self.broker = capability_broker

    async def execute_plan(
        self, 
        mission_id: str, 
        plan: MissionPlan, 
        context: MissionContext,
        executor_func: Callable[[MissionNode, Dict[str, Any]], Coroutine[Any, Any, Any]]
    ) -> bool:
        """
        🚀 Chạy toàn bộ đồ thị MissionPlan theo dependencies.
        """
        nodes = plan.nodes
        edges = plan.edges

        # 1. Xây dựng đồ thị kề (adjacency list) và in-degree map
        adj_list: Dict[str, List[str]] = {nid: [] for nid in nodes}
        in_degree: Dict[str, int] = {nid: 0 for nid in nodes}
        parents: Dict[str, List[str]] = {nid: [] for nid in nodes}

        for edge in edges:
            adj_list[edge.source].append(edge.target)
            in_degree[edge.target] += 1
            parents[edge.target].append(edge.source)

        # Trạng thái khôi phục (Resume): Đối với các node đã SUCCESS ở phiên trước,
        # ta giảm in-degree của các node con tương ứng ngay lập tức để scheduler không lập lịch chạy lại node đã thành công.
        for nid, node in nodes.items():
            if node.state == MissionNodeState.SUCCESS:
                for child_id in adj_list[nid]:
                    if in_degree[child_id] > 0:
                        in_degree[child_id] -= 1

        # Trạng thái theo dõi
        running_tasks: Set[asyncio.Task] = set()
        node_futures: Dict[str, asyncio.Future] = {nid: asyncio.Future() for nid in nodes}
        
        # Hàng đợi các node đã sẵn sàng chạy (in-degree == 0 và chưa chạy hoàn tất - PENDING)
        ready_queue = [nid for nid in nodes if in_degree[nid] == 0 and nodes[nid].state == MissionNodeState.PENDING]
        
        # Khóa bảo vệ ghi nhận in-degree
        lock = asyncio.Lock()

        # Sự kiện thông báo khi hàng đợi có thay đổi hoặc task hoàn thành
        queue_event = asyncio.Event()

        # Lưu log bắt đầu lập lịch
        self.event_store.append_event(MissionEvent(
            mission_id=mission_id,
            event_type=EventType.NODE_SCHEDULED,
            payload={"message": "Kích hoạt Scheduler lập lịch chạy DAG song song."}
        ))

        async def run_node(node_id: str):
            node = nodes[node_id]
            
            # Đánh dấu Bắt đầu
            self.event_store.append_event(MissionEvent(
                mission_id=mission_id,
                event_type=EventType.NODE_STARTED,
                payload={"node_id": node_id}
            ))

            # 2. Context Policy: Thu thập dữ liệu từ các node cha
            input_context = {}
            for p_id in parents[node_id]:
                parent_node: MissionNode = nodes[p_id]
                parent_output = parent_node.output
                
                if isinstance(parent_output, dict):
                    if node.input_context_keys:
                        for k in node.input_context_keys:
                            if k in parent_output:
                                input_context[k] = parent_output[k]
                    else:
                        input_context.update(parent_output)
                else:
                    if parent_output is not None:
                        input_context[p_id] = parent_output

            # 3. Thực thi
            try:
                # Kiểm tra budget & chọn provider (Chỉ làm với node thường, validation node chạy trực tiếp)
                provider = None
                if node.capability != "critic_validation":
                    provider = self.broker.select_provider(node.capability, context)
                    budget_ok, budget_msg = self.broker.resource_manager.check_budget(context, estimated_cost=provider.cost_per_call)
                    if not budget_ok:
                        raise PermissionError(f"Chặn do vượt ngân sách: {budget_msg}")
                
                # Thực thi tác vụ qua handler
                output = await executor_func(node, input_context)
                
                # Cập nhật state và output vào RAM
                node.state = MissionNodeState.SUCCESS
                node.output = output

                if provider:
                    self.broker.resource_manager.record_usage(100, provider.cost_per_call)

                # Cập nhật kết quả thành công
                self.event_store.append_event(MissionEvent(
                    mission_id=mission_id,
                    event_type=EventType.NODE_COMPLETED,
                    payload={"node_id": node_id, "output": output}
                ))
                node_futures[node_id].set_result(True)

            except ValidationFailedException as vfe:
                # Validation Node báo cáo thất bại ➔ Kích hoạt cơ chế tự động sửa lỗi (Self-Correction Loop)
                node.state = MissionNodeState.FAILED
                node.error = str(vfe)
                
                target_node = nodes[vfe.target_node_id]
                
                # Ghi nhận sự kiện Validation Failed
                self.event_store.append_event(MissionEvent(
                    mission_id=mission_id,
                    event_type=EventType.VALIDATION_FAILED,
                    payload={"node_id": vfe.target_node_id, "reason": vfe.reason}
                ))

                # Kiểm tra giới hạn Retry
                if target_node.retries_count >= target_node.max_retries:
                    err_msg = f"Đạt giới hạn retry tối đa ({target_node.max_retries}) cho node '{target_node.name}'. Dừng mission."
                    self.event_store.append_event(MissionEvent(
                        mission_id=mission_id,
                        event_type=EventType.NODE_FAILED,
                        payload={"node_id": node_id, "error": err_msg}
                    ))
                    node_futures[node_id].set_result(False)
                    raise RuntimeError(err_msg)

                # Yêu cầu chạy lại (Retry) node cha
                self.event_store.append_event(MissionEvent(
                    mission_id=mission_id,
                    event_type=EventType.RETRY_REQUESTED,
                    payload={"node_id": vfe.target_node_id}
                ))

                # Yêu cầu chạy lại (Retry) chính validation node (chuyển về PENDING trong State Machine)
                self.event_store.append_event(MissionEvent(
                    mission_id=mission_id,
                    event_type=EventType.RETRY_REQUESTED,
                    payload={"node_id": node_id}
                ))
                
                # Chuyển trạng thái của node cha và node validation hiện tại về PENDING
                target_node.state = MissionNodeState.PENDING
                target_node.error = None
                target_node.output = None
                target_node.retries_count += 1
                
                node.state = MissionNodeState.PENDING
                node.error = None
                node.output = None

                # Reset futures để có thể set lại sau khi chạy lại
                node_futures[vfe.target_node_id] = asyncio.Future()
                node_futures[node_id] = asyncio.Future()

                # Cập nhật lại in-degree của validation node (phải chờ node cha chạy lại)
                async with lock:
                    in_degree[node_id] += 1
                    # Đưa node cha trở lại ready queue
                    ready_queue.append(vfe.target_node_id)
                    queue_event.set()

                raise vfe

            except Exception as e:
                node.state = MissionNodeState.FAILED
                node.error = str(e)

                logger.error(f"❌ Node '{node.name}' chạy thất bại: {str(e)}")
                self.event_store.append_event(MissionEvent(
                    mission_id=mission_id,
                    event_type=EventType.NODE_FAILED,
                    payload={"node_id": node_id, "error": str(e)}
                ))
                node_futures[node_id].set_result(False)
                raise e

            # 4. Cập nhật in-degree của các node con (Chỉ khi node chạy SUCCESS thực sự)
            async with lock:
                for child_id in adj_list[node_id]:
                    in_degree[child_id] -= 1
                    if in_degree[child_id] == 0:
                        ready_queue.append(child_id)
                        queue_event.set()

        # Luồng điều khiển chính của Scheduler
        success = True
        try:
            while ready_queue or running_tasks:
                while ready_queue:
                    next_node_id = ready_queue.pop(0)
                    task = asyncio.create_task(run_node(next_node_id))
                    running_tasks.add(task)
                
                if not running_tasks:
                    break

                done, pending = await asyncio.wait(
                    running_tasks, 
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                for task in done:
                    running_tasks.remove(task)
                    try:
                        await task  # Bắt exception
                    except ValidationFailedException:
                        # Đây là lỗi validation có kiểm soát ➔ Không dừng hệ thống, tiếp tục chạy loop để chạy lại node cha
                        logger.info("⚠️ Phát hiện lỗi Validation. Kích hoạt luồng tự động sửa lỗi (Self-Correction loop)...")
                        continue
                    except Exception:
                        success = False
                        for t in running_tasks:
                            t.cancel()
                        ready_queue.clear()
                        break
                
                if not success:
                    break
                    
                queue_event.clear()

        except Exception as e:
            logger.error(f"Lỗi lập lịch Scheduler: {e}")
            success = False

        # Ghi sự kiện hoàn thành/thất bại Mission
        self.event_store.append_event(MissionEvent(
            mission_id=mission_id,
            event_type=EventType.MISSION_COMPLETED if success else EventType.MISSION_CANCELLED,
            payload={"success": success}
        ))
        
        return success
