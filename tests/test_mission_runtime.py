import pytest
import shutil
from pathlib import Path
from datetime import datetime
import uuid
import threading
import time
import asyncio

from core.kernel.models import (
    MissionContext,
    MissionPlan,
    MissionNode,
    MissionEdge,
    MissionNodeState,
    MissionEvent,
    EventType
)
from core.kernel.event_store import EventStore
from core.kernel.mission_state_machine import reduce_state, InvalidNodeStateTransition
from core.kernel.snapshot_engine import SnapshotEngine
from core.kernel.capability_broker import CapabilityBroker
from core.kernel.dag_scheduler import DAGScheduler, ValidationFailedException
from core.kernel.mission_runtime import MissionRuntime

TEST_DATA_DIR = "data/test_missions"

@pytest.fixture(autouse=True)
def setup_and_teardown():
    if Path(TEST_DATA_DIR).exists():
        shutil.rmtree(TEST_DATA_DIR)
    yield
    if Path(TEST_DATA_DIR).exists():
        shutil.rmtree(TEST_DATA_DIR)


def test_mission_lifecycle_and_persistence():
    mission_id = f"test-mission-{uuid.uuid4()}"
    event_store = EventStore(base_dir=TEST_DATA_DIR)
    snapshot_engine = SnapshotEngine(base_dir=TEST_DATA_DIR, event_store=event_store)

    # 1. Khởi tạo Mission
    context = MissionContext(
        goal="Tối ưu hóa mã nguồn Python",
        constraints=["Không dùng thư viện ngoài", "Chạy dưới 1s"],
        budget_tokens=10000,
        budget_usd=0.5
    )
    
    event_1 = MissionEvent(
        mission_id=mission_id,
        event_type=EventType.MISSION_CREATED,
        payload={"context": context.model_dump(), "metadata": {"created_by": "pytest"}}
    )
    event_store.append_event(event_1)

    state = snapshot_engine.get_latest_state(mission_id)
    assert state.status == "CREATED"

    # 2. Sinh Kế hoạch (Plan / DAG)
    node_a = MissionNode(name="Đọc file", capability="read_file")
    node_b = MissionNode(name="Tối ưu", capability="optimize_code")
    edge = MissionEdge(source=node_a.id, target=node_b.id)
    
    plan = MissionPlan(
        nodes={node_a.id: node_a, node_b.id: node_b},
        edges=[edge]
    )

    event_2 = MissionEvent(
        mission_id=mission_id,
        event_type=EventType.PLANNER_FINISHED,
        payload={"plan": plan.model_dump()}
    )
    event_store.append_event(event_2)

    # Chạy Node A
    event_3 = MissionEvent(
        mission_id=mission_id,
        event_type=EventType.NODE_STARTED,
        payload={"node_id": node_a.id}
    )
    event_store.append_event(event_3)
    
    # Node A hoàn thành
    event_4 = MissionEvent(
        mission_id=mission_id,
        event_type=EventType.NODE_COMPLETED,
        payload={"node_id": node_a.id, "output": "content of file"}
    )
    event_store.append_event(event_4)

    state = snapshot_engine.get_latest_state(mission_id)
    
    # 3. Lưu Snapshot tại event_4
    snapshot_engine.save_snapshot(state, event_4.event_id, event_4.timestamp)

    # 4. Tiếp tục thêm sự kiện sau Snapshot
    event_5 = MissionEvent(
        mission_id=mission_id,
        event_type=EventType.NODE_STARTED,
        payload={"node_id": node_b.id}
    )
    event_store.append_event(event_5)

    # Tải lại trạng thái để xác thực Snapshot + Event Log hoạt động chuẩn xác
    restored_state = snapshot_engine.get_latest_state(mission_id)
    
    assert restored_state.plan.nodes[node_a.id].state == MissionNodeState.SUCCESS
    assert restored_state.plan.nodes[node_b.id].state == MissionNodeState.RUNNING


def test_node_state_transitions_validation():
    """Kiểm tra xem hệ thống có ngăn chặn các chuyển đổi trạng thái Node bất hợp lệ không"""
    mission_id = f"test-mission-{uuid.uuid4()}"
    event_store = EventStore(base_dir=TEST_DATA_DIR)
    
    node = MissionNode(name="Kiểm thử", capability="run_test")
    plan = MissionPlan(nodes={node.id: node}, edges=[])
    
    # Nạp plan
    event_store.append_event(MissionEvent(
        mission_id=mission_id,
        event_type=EventType.PLANNER_FINISHED,
        payload={"plan": plan.model_dump()}
    ))

    # Thử nhảy trạng thái bất hợp lệ: PENDING -> SUCCESS (bỏ qua RUNNING)
    event_store.append_event(MissionEvent(
        mission_id=mission_id,
        event_type=EventType.NODE_COMPLETED,
        payload={"node_id": node.id}
    ))

    with pytest.raises(InvalidNodeStateTransition):
        all_events = event_store.get_events(mission_id)
        reduce_state(mission_id, all_events)


def test_cancel_mission():
    """Xác nhận khi hủy Mission, toàn bộ các Node dang hoạt động/chờ phải chuyển sang CANCELLED"""
    mission_id = f"test-mission-{uuid.uuid4()}"
    event_store = EventStore(base_dir=TEST_DATA_DIR)
    
    node_a = MissionNode(name="Node A", capability="task_a")
    node_b = MissionNode(name="Node B", capability="task_b")
    plan = MissionPlan(nodes={node_a.id: node_a, node_b.id: node_b}, edges=[])
    
    event_store.append_event(MissionEvent(
        mission_id=mission_id,
        event_type=EventType.PLANNER_FINISHED,
        payload={"plan": plan.model_dump()}
    ))
    
    # Chạy Node A, Node B vẫn PENDING
    event_store.append_event(MissionEvent(
        mission_id=mission_id,
        event_type=EventType.NODE_STARTED,
        payload={"node_id": node_a.id}
    ))
    
    # Hủy Mission
    event_store.append_event(MissionEvent(
        mission_id=mission_id,
        event_type=EventType.MISSION_CANCELLED
    ))
    
    state = reduce_state(mission_id, event_store.get_events(mission_id))
    assert state.status == "CANCELLED"
    assert state.plan.nodes[node_a.id].state == MissionNodeState.CANCELLED
    assert state.plan.nodes[node_b.id].state == MissionNodeState.CANCELLED


def test_retry_loop():
    """Kiểm tra luồng FAILED -> RETRY_REQUESTED -> PENDING -> RUNNING"""
    mission_id = f"test-mission-{uuid.uuid4()}"
    event_store = EventStore(base_dir=TEST_DATA_DIR)
    
    node = MissionNode(name="Retry Task", capability="task_x")
    plan = MissionPlan(nodes={node.id: node}, edges=[])
    
    event_store.append_event(MissionEvent(
        mission_id=mission_id,
        event_type=EventType.PLANNER_FINISHED,
        payload={"plan": plan.model_dump()}
    ))
    
    # Khởi động
    event_store.append_event(MissionEvent(
        mission_id=mission_id,
        event_type=EventType.NODE_STARTED,
        payload={"node_id": node.id}
    ))
    # Thất bại
    event_store.append_event(MissionEvent(
        mission_id=mission_id,
        event_type=EventType.NODE_FAILED,
        payload={"node_id": node.id, "error": "Fatal Error"}
    ))
    
    state = reduce_state(mission_id, event_store.get_events(mission_id))
    assert state.plan.nodes[node.id].state == MissionNodeState.FAILED
    assert state.plan.nodes[node.id].retries_count == 0
    
    # Yêu cầu Retry
    event_store.append_event(MissionEvent(
        mission_id=mission_id,
        event_type=EventType.RETRY_REQUESTED,
        payload={"node_id": node.id}
    ))
    
    state = reduce_state(mission_id, event_store.get_events(mission_id))
    assert state.plan.nodes[node.id].state == MissionNodeState.PENDING
    assert state.plan.nodes[node.id].retries_count == 1
    assert state.plan.nodes[node.id].error is None


def test_event_store_thread_safety():
    """Kiểm thử tính năng Thread-safety của EventStore khi ghi song song từ nhiều luồng"""
    mission_id = f"test-mission-{uuid.uuid4()}"
    event_store = EventStore(base_dir=TEST_DATA_DIR)
    
    threads = []
    num_threads = 20
    events_per_thread = 10
    
    def worker(worker_id):
        for j in range(events_per_thread):
            event = MissionEvent(
                mission_id=mission_id,
                event_type=EventType.NODE_SCHEDULED,
                payload={"thread": worker_id, "index": j}
            )
            event_store.append_event(event)
            time.sleep(0.001)

    for i in range(num_threads):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    all_events = event_store.get_events(mission_id)
    # Tổng số event phải chính xác là num_threads * events_per_thread
    assert len(all_events) == num_threads * events_per_thread


@pytest.mark.asyncio
async def test_dag_scheduler_parallelism():
    """Kiểm toán tốc độ thực thi song song của DAG Scheduler"""
    mission_id = f"test-mission-{uuid.uuid4()}"
    event_store = EventStore(base_dir=TEST_DATA_DIR)
    broker = CapabilityBroker()
    scheduler = DAGScheduler(event_store, broker)

    # Đăng ký 2 node chạy song song không phụ thuộc nhau
    node_a = MissionNode(name="Task A", capability="read_code")
    node_b = MissionNode(name="Task B", capability="read_code")
    plan = MissionPlan(nodes={node_a.id: node_a, node_b.id: node_b}, edges=[])
    context = MissionContext(goal="Test Parallel")

    # Mock handler thực thi: Mỗi node ngủ 0.4 giây
    async def mock_execute(node, input_ctx):
        await asyncio.sleep(0.4)
        return {"output_data": f"result_{node.name}"}

    start_time = time.time()
    # Chạy kế hoạch
    success = await scheduler.execute_plan(mission_id, plan, context, mock_execute)
    duration = time.time() - start_time

    assert success
    # Nếu chạy song song, thời gian chạy của cả 2 node ngủ 0.4s chỉ mất khoảng 0.4 - 0.6s
    # Nếu chạy tuần tự, nó sẽ mất hơn 0.8s
    assert duration < 0.7, f"Thời gian chạy quá lâu ({duration}s), có thể Scheduler đã chạy tuần tự!"


@pytest.mark.asyncio
async def test_policy_engine_enforcement():
    """Xác nhận Policy Engine chặn đứng các tool vi phạm chính sách"""
    import os
    os.environ["TAVILY_API_KEY"] = "mock_tavily_key"
    
    mission_id = f"test-mission-{uuid.uuid4()}"
    event_store = EventStore(base_dir=TEST_DATA_DIR)
    broker = CapabilityBroker()
    
    # Loại bỏ LocalSearch khỏi registry để ép hệ thống chọn Tavily (Online)
    broker.registry._providers["web_search"] = [
        p for p in broker.registry._providers["web_search"] if p.name != "LocalSearch"
    ]
    
    scheduler = DAGScheduler(event_store, broker)

    # Đăng ký node yêu cầu kết nối mạng (Tavily)
    node = MissionNode(name="Search internet", capability="web_search")
    plan = MissionPlan(nodes={node.id: node}, edges=[])
    
    # Nạp plan vào event_store
    event_store.append_event(MissionEvent(
        mission_id=mission_id,
        event_type=EventType.PLANNER_FINISHED,
        payload={"plan": plan.model_dump()}
    ))
    
    # Kích hoạt chính sách chặn mạng 'no_network'
    context = MissionContext(
        goal="Test Policy",
        policies=["no_network"]
    )

    async def mock_execute(node, input_ctx):
        return {}

    # Chạy scheduler, mong đợi bị từ chối/thất bại do chính sách bảo mật
    success = await scheduler.execute_plan(mission_id, plan, context, mock_execute)
    assert not success
    
    # Kiểm tra log sự kiện xem có ghi nhận lỗi Policy không
    state = reduce_state(mission_id, event_store.get_events(mission_id))
    assert state.plan.nodes[node.id].state == MissionNodeState.FAILED
    assert "Policy" in state.plan.nodes[node.id].error or "Chính sách" in state.plan.nodes[node.id].error


@pytest.mark.asyncio
async def test_resource_manager_budget_limit():
    """Đảm bảo Resource Manager chặn đứng chạy node khi vượt Budget"""
    import os
    os.environ["TAVILY_API_KEY"] = "mock_tavily_key"

    mission_id = f"test-mission-{uuid.uuid4()}"
    event_store = EventStore(base_dir=TEST_DATA_DIR)
    broker = CapabilityBroker()
    
    # Loại bỏ LocalSearch để ép chọn Tavily (cost = 0.005 USD -> vượt quá 0.001 USD)
    broker.registry._providers["web_search"] = [
        p for p in broker.registry._providers["web_search"] if p.name != "LocalSearch"
    ]

    scheduler = DAGScheduler(event_store, broker)

    # Cấu hình budget USD cực thấp
    context = MissionContext(
        goal="Test Budget",
        budget_usd=0.001  # 0.001 USD
    )

    # Node yêu cầu web_search (Tavily cost = 0.005 USD)
    node = MissionNode(name="Costly Task", capability="web_search")
    plan = MissionPlan(nodes={node.id: node}, edges=[])

    # Nạp plan vào event_store
    event_store.append_event(MissionEvent(
        mission_id=mission_id,
        event_type=EventType.PLANNER_FINISHED,
        payload={"plan": plan.model_dump()}
    ))

    async def mock_execute(node, input_ctx):
        return {}

    success = await scheduler.execute_plan(mission_id, plan, context, mock_execute)
    assert not success
    
    state = reduce_state(mission_id, event_store.get_events(mission_id))
    assert state.plan.nodes[node.id].state == MissionNodeState.FAILED
    assert "Budget" in state.plan.nodes[node.id].error or "ngân sách" in state.plan.nodes[node.id].error


@pytest.mark.asyncio
async def test_context_policy_filtering():
    """Kiểm tra Context Policy: Chỉ truyền các key được yêu cầu từ node cha cho node con"""
    mission_id = f"test-mission-{uuid.uuid4()}"
    event_store = EventStore(base_dir=TEST_DATA_DIR)
    broker = CapabilityBroker()
    scheduler = DAGScheduler(event_store, broker)

    # Node A trả về dict gồm nhiều key
    node_a = MissionNode(name="Producer", capability="read_code")
    # Node B phụ thuộc Node A nhưng chỉ muốn lấy key "important_key"
    node_b = MissionNode(
        name="Consumer", 
        capability="write_code", 
        input_context_keys=["important_key"]
    )
    edge = MissionEdge(source=node_a.id, target=node_b.id)
    plan = MissionPlan(nodes={node_a.id: node_a, node_b.id: node_b}, edges=[edge])
    context = MissionContext(goal="Test Context Policy")

    received_context = {}

    async def mock_execute(node, input_ctx):
        if node.name == "Producer":
            return {"important_key": "secret", "garbage_key": "spam"}
        elif node.name == "Consumer":
            nonlocal received_context
            received_context = input_ctx
            return {}

    success = await scheduler.execute_plan(mission_id, plan, context, mock_execute)
    assert success
    
    # Consumer chỉ nhận được "important_key", "garbage_key" phải bị lọc bỏ
    assert "important_key" in received_context
    assert "garbage_key" not in received_context


@pytest.mark.asyncio
async def test_critic_integration_and_self_correction():
    """Kiểm thử tích hợp Validation Node (Critic) kích hoạt Self-Correction Loop tự sửa lỗi"""
    mission_id = f"test-mission-{uuid.uuid4()}"
    event_store = EventStore(base_dir=TEST_DATA_DIR)
    broker = CapabilityBroker()
    scheduler = DAGScheduler(event_store, broker)

    # 1. Đồ thị: Producer (Sinh code) -> Critic (Thẩm định) -> Consumer (Deploy)
    node_producer = MissionNode(name="Producer", capability="read_code", max_retries=2)
    node_critic = MissionNode(name="Critic", capability="critic_validation")
    node_consumer = MissionNode(name="Consumer", capability="write_code")

    edges = [
        MissionEdge(source=node_producer.id, target=node_critic.id),
        MissionEdge(source=node_critic.id, target=node_consumer.id)
    ]
    plan = MissionPlan(
        nodes={node_producer.id: node_producer, node_critic.id: node_critic, node_consumer.id: node_consumer},
        edges=edges
    )
    context = MissionContext(goal="Test Self-Correction Loop")

    # Nạp plan vào log
    event_store.append_event(MissionEvent(
        mission_id=mission_id,
        event_type=EventType.PLANNER_FINISHED,
        payload={"plan": plan.model_dump()}
    ))

    producer_calls = 0

    async def mock_execute(node, input_ctx):
        nonlocal producer_calls
        if node.name == "Producer":
            producer_calls += 1
            if producer_calls == 1:
                # Lần 1: Sinh code bị lỗi
                return {"code": "def foo() -> syntax_error"}
            else:
                # Lần 2: Sinh code chuẩn
                return {"code": "def foo() -> int: return 42"}
                
        elif node.name == "Critic":
            # Thẩm định code của Producer truyền qua input_ctx
            code_content = input_ctx.get("code", "")
            if "syntax_error" in code_content:
                # Không đạt yêu cầu ➔ Kích hoạt chạy lại Producer
                raise ValidationFailedException(target_node_id=node_producer.id, reason="Code có lỗi cú pháp")
            return {"status": "approved"}
            
        elif node.name == "Consumer":
            return {"status": "deployed"}

    # Thực thi
    success = await scheduler.execute_plan(mission_id, plan, context, mock_execute)
    assert success
    
    # Xác nhận Producer đã được gọi đúng 2 lần (lần 1 lỗi, lần 2 sửa thành công)
    assert producer_calls == 2
    
    state = reduce_state(mission_id, event_store.get_events(mission_id))
    assert state.status == "COMPLETED"
    assert state.plan.nodes[node_producer.id].state == MissionNodeState.SUCCESS
    assert state.plan.nodes[node_producer.id].retries_count == 1
    assert state.plan.nodes[node_consumer.id].state == MissionNodeState.SUCCESS


@pytest.mark.asyncio
async def test_mission_runtime_resume_after_crash():
    """Kiểm thử tính năng MissionRuntime.resume_mission khôi phục hoàn hảo sau crash"""
    # 1. Khởi tạo MissionRuntime
    runtime = MissionRuntime(base_dir=TEST_DATA_DIR)
    
    context = MissionContext(goal="Test Resume Crash")
    mission_id = runtime.submit_mission(context)

    # Đồ thị: Node A -> Node B
    node_a = MissionNode(name="Task A", capability="read_code")
    node_b = MissionNode(name="Task B", capability="write_code")
    edges = [MissionEdge(source=node_a.id, target=node_b.id)]
    plan = MissionPlan(nodes={node_a.id: node_a, node_b.id: node_b}, edges=edges)

    node_a_executed = 0
    node_b_executed = 0

    async def mock_execute_before_crash(node, input_ctx):
        nonlocal node_a_executed
        if node.name == "Task A":
            node_a_executed += 1
            return {"result": "success_a"}
        elif node.name == "Task B":
            # Giả lập crash khi vừa chạy xong Node A và bắt đầu chạy Node B (ném lỗi)
            raise RuntimeError("Hệ thống bị tắt đột ngột (Crash)")

    # Chạy lần đầu ➔ Mong đợi thất bại (do Node B bị crash)
    success = await runtime.execute_mission(mission_id, plan, mock_execute_before_crash)
    assert not success
    assert node_a_executed == 1

    # 2. Khôi phục (Resume) từ Runtime mới
    new_runtime = MissionRuntime(base_dir=TEST_DATA_DIR)

    async def mock_execute_after_resume(node, input_ctx):
        nonlocal node_a_executed, node_b_executed
        if node.name == "Task A":
            # Không được phép gọi lại Node A vì nó đã SUCCESS ở phiên trước
            node_a_executed += 1
            return {"result": "success_a"}
        elif node.name == "Task B":
            node_b_executed += 1
            return {"result": "success_b"}

    # Tiếp tục chạy (Resume)
    success_resume = await new_runtime.resume_mission(mission_id, mock_execute_after_resume)
    
    assert success_resume
    # Xác nhận Task A chỉ chạy 1 lần duy nhất trước crash (không chạy lại lần 2)
    assert node_a_executed == 1
    # Xác nhận Task B chạy thành công sau khi resume
    assert node_b_executed == 1

    # Kiểm tra trạng thái cuối cùng
    state = new_runtime.snapshot_engine.get_latest_state(mission_id)
    assert state.status == "COMPLETED"
    assert state.plan.nodes[node_a.id].state == MissionNodeState.SUCCESS
    assert state.plan.nodes[node_b.id].state == MissionNodeState.SUCCESS


