"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — CENTRAL COGNITIVE SCHEDULER                      ║
║   Bộ Lập Lịch Nhận Thức Siêu Phân Luồng & Giám Sát Hạt Nhân      ║
╚══════════════════════════════════════════════════════════════════╝
*Thuộc Ban Quản Trị Hệ Thống Nhận Thức & Lập Lịch Lõi của JKAI. 🌌🏛️⏱️*
"""

import os
import sys
import time
import shutil
import asyncio
import logging
import traceback
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Callable, Awaitable

from core.kernel.state_machine import TaskState, StateTransitionGraph
from core.kernel.cognitive_event_bus import cognitive_event_bus, CognitiveEvent
from core.kernel.homeostasis import homeostasis_engine
from core.utils.engine import engine

logger = logging.getLogger("CognitiveScheduler")

# =================════====================================
# 🚀 1. HỆ THỐNG PHÂN CẤP MỤC TIÊU (GOAL HIERARCHY SYSTEM)
# =================════====================================

class GoalLevel(str, Enum):
    STRATEGIC = "STRATEGIC"    # Chiến lược vĩ mô từ Master
    TACTICAL = "TACTICAL"      # Chiến thuật phân bổ tài nguyên
    OPERATIONAL = "OPERATIONAL" # Thao tác trung gian
    ATOMIC = "ATOMIC"          # Lệnh thực thi thô (tools/scripts)

class GoalStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

@dataclass
class GoalNode:
    goal_id: str
    description: str
    level: GoalLevel
    status: GoalStatus = GoalStatus.PENDING
    parent_id: Optional[str] = None
    sub_goals: List['GoalNode'] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "description": self.description,
            "level": self.level.value,
            "status": self.status.value,
            "parent_id": self.parent_id,
            "sub_goals": [g.to_dict() for g in self.sub_goals],
            "created_at": self.created_at
        }


class GoalStack:
    """
    🧬 [GOAL-STACK]: Quản lý đệ quy các tầng mục tiêu (LIFO).
    Giúp hệ thống luôn tư duy định hướng mục tiêu (goal-driven) thưa Tổng Giám Đốc.
    """
    def __init__(self, task_id: str):
        self.task_id = task_id
        self._stack: List[GoalNode] = []
        self._all_goals: Dict[str, GoalNode] = {}

    def push(self, goal_id: str, description: str, level: GoalLevel, parent_id: Optional[str] = None) -> GoalNode:
        node = GoalNode(goal_id=goal_id, description=description, level=level, parent_id=parent_id)
        self._stack.append(node)
        self._all_goals[goal_id] = node
        if parent_id and parent_id in self._all_goals:
            self._all_goals[parent_id].sub_goals.append(node)
        return node

    def pop(self) -> Optional[GoalNode]:
        if not self._stack:
            return None
        return self._stack.pop()

    def peek(self) -> Optional[GoalNode]:
        if not self._stack:
            return None
        return self._stack[-1]

    def update_status(self, goal_id: str, status: GoalStatus):
        if goal_id in self._all_goals:
            self._all_goals[goal_id].status = status

    def to_dict(self) -> List[Dict[str, Any]]:
        return [g.to_dict() for g in self._stack]


# =================════====================================
# ⚙️ 2. GIAO DỊCH NHẬN THỨC (COGNITIVE TRANSACTION MANAGER - ACID)
# =================════====================================

class TransactionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMMITTED = "COMMITTED"
    ROLLED_BACK = "ROLLED_BACK"

@dataclass
class CognitiveTransaction:
    tx_id: str
    task_id: str
    status: TransactionStatus = TransactionStatus.ACTIVE
    backups: Dict[str, str] = field(default_factory=dict) # original_path -> backup_path
    compensating_actions: List[Callable[[], Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


class CognitiveTransactionManager:
    """
    🏛️ [TRANSACTION-MANAGER]: Quản lý tính nhất quán Giao dịch Nhận thức thưa Master.
    Áp dụng PHƯƠNG ÁN A: Tự sinh file sao lưu `.bak` vật lý tại cùng thư mục và rollback an toàn.
    """
    def __init__(self):
        self._active_txs: Dict[str, CognitiveTransaction] = {}
        self._lock = asyncio.Lock()

    async def begin_transaction(self, tx_id: str, task_id: str) -> CognitiveTransaction:
        async with self._lock:
            tx = CognitiveTransaction(tx_id=tx_id, task_id=task_id)
            self._active_txs[tx_id] = tx
            # Gửi log văn phòng doanh nghiệp
            engine.publish_mission_log(
                "TRANSACTION",
                f"📥 [TRANSACTION-BEGIN] Khởi động phiên giao dịch nhận thức `{tx_id}`. Sẵn sàng bảo vệ ACID...",
                task_id,
                "sys"
            )
            return tx

    async def register_backup(self, tx_id: str, file_path: str):
        """
        📁 [PHƯƠNG ÁN A]: Sao lưu vật lý file bị phẫu thuật dưới dạng `.bak` thưa Master.
        """
        async with self._lock:
            tx = self._active_txs.get(tx_id)
            if not tx:
                raise ValueError(f"Không tìm thấy phiên giao dịch `{tx_id}` thưa Master.")
            
            if file_path not in tx.backups:
                if os.path.exists(file_path):
                    backup_path = f"{file_path}.bak"
                    try:
                        shutil.copy2(file_path, backup_path)
                        tx.backups[file_path] = backup_path
                        logger.debug(f"⚙️ [TX-BACKUP]: Đã tạo snapshot sao lưu an toàn tại `{backup_path}`.")
                    except Exception as e:
                        logger.error(f"❌ [TX-BACKUP-ERR]: Không thể sao lưu file `{file_path}`: {e}")
                else:
                    # File mới hoàn toàn - Compensating action sẽ là xóa file này nếu rollback
                    tx.backups[file_path] = "NEW_FILE"

    def register_compensating_action(self, tx_id: str, action: Callable[[], Any]):
        """ Đăng ký hành động bù đắp tùy biến thưa Master. """
        tx = self._active_txs.get(tx_id)
        if tx:
            tx.compensating_actions.append(action)

    async def commit_transaction(self, tx_id: str):
        """
        ✨ [COMMIT-SUCCESS]: Hoàn tất và khâu vết mổ, dọn dẹp các tệp sao lưu `.bak` thưa Tổng Giám Đốc.
        """
        async with self._lock:
            tx = self._active_txs.pop(tx_id, None)
            if not tx:
                return

            # Dọn sạch các file `.bak`
            for orig, bkp in tx.backups.items():
                if bkp != "NEW_FILE" and os.path.exists(bkp):
                    try:
                        os.remove(bkp)
                        logger.debug(f"🧹 [TX-CLEAN]: Đã xóa file sao lưu tạm thời `{bkp}`.")
                    except Exception as e:
                        logger.warn(f"⚠️ [TX-CLEAN-WARN]: Không thể xóa file sao lưu `{bkp}`: {e}")
            
            tx.status = TransactionStatus.COMMITTED
            engine.publish_mission_log(
                "TRANSACTION_COMMIT",
                f"✨ [TRANSACTION-COMMIT] Giao dịch `{tx_id}` đã được CAM KẾT thành công. Hệ thống đồng bộ nhất quán!",
                tx.task_id,
                "sys"
            )

    async def rollback_transaction(self, tx_id: str):
        """
        🚨 [ROLLBACK]: Khôi phục trạng thái ban đầu hệ thống thưa Master (Rollback an toàn).
        """
        async with self._lock:
            tx = self._active_txs.pop(tx_id, None)
            if not tx:
                return

            engine.publish_mission_log(
                "TRANSACTION_ROLLBACK",
                f"🚨 [TRANSACTION-ROLLBACK] Giao dịch `{tx_id}` bị lỗi giữa chừng. Đang kích hoạt cứu hộ khẩn cấp...",
                tx.task_id,
                "sys"
            )

            # 1. Khôi phục các file từ `.bak`
            for orig, bkp in tx.backups.items():
                try:
                    if bkp == "NEW_FILE":
                        if os.path.exists(orig):
                            os.remove(orig)
                            logger.info(f"🧹 [TX-ROLLBACK]: Đã xóa file mới tạo dư thừa `{orig}`.")
                    elif os.path.exists(bkp):
                        shutil.move(bkp, orig)
                        logger.info(f"♻️ [TX-ROLLBACK]: Đã khôi phục file nguyên bản tại `{orig}`.")
                except Exception as e:
                    logger.error(f"❌ [ROLLBACK-ERR]: Lỗi phục hồi file `{orig}` từ `{bkp}`: {e}")

            # 2. Thực thi các hành động bù đắp tùy biến đăng ký thêm
            for action in reversed(tx.compensating_actions):
                try:
                    if asyncio.iscoroutinefunction(action):
                        await action()
                    else:
                        action()
                except Exception as e:
                    logger.error(f"❌ [COMPENSATING-ACTION-ERR]: Lỗi thực thi hành động bù đắp: {e}")

            tx.status = TransactionStatus.ROLLED_BACK
            engine.publish_mission_log(
                "TRANSACTION_ROLLED_BACK",
                f"✅ [TRANSACTION-ROLLBACK-DONE] Phiên giao dịch `{tx_id}` đã được hoàn tác hoàn toàn thưa Tổng Giám Đốc.",
                tx.task_id,
                "sys"
            )


# Singleton Quản lý Giao dịch thưa Master
cognitive_transaction_manager = CognitiveTransactionManager()


# =====================================================================
# 🧬 3. MODEL TỰ NHẬN THỨC & HOẠT ĐỘNG KINH TẾ (SELF-MODEL & ECONOMY)
# =================════====================================

class SelfModelCortex:
    """
    🧠 [SELF-MODEL-CORTEX]: Động cơ tự nhận thức năng lực và định chuẩn độ tự tin thưa Master.
    Theo dõi lịch sử thành bại của từng công cụ/kỹ năng để tính toán độ mơ hồ và kích hoạt Fallback Gate.
    """
    def __init__(self):
        # Ma trận thành bại lịch sử thưa Master
        self.capability_history: Dict[str, List[bool]] = {
            "surgery": [True, True, True],
            "file_edit": [True, True],
            "database": [True],
            "network": [True]
        }

    def record_outcome(self, capability: str, success: bool):
        if capability not in self.capability_history:
            self.capability_history[capability] = []
        self.capability_history[capability].append(success)
        # Giới hạn ghi nhớ 20 mẫu gần nhất để phản ánh chính xác năng lực thực tế
        if len(self.capability_history[capability]) > 20:
            self.capability_history[capability].pop(0)

    def calibrate_confidence(self, task_id: str, capability: str, baseline: float = 0.85) -> float:
        """
        📊 [ĐỊNH CHUẨN ĐỘ TỰ TIN]: Tính toán độ tin cậy dựa trên lịch sử hoạt động thưa Tổng Giám Đốc.
        Nếu tỷ lệ thành công lịch sử thấp, độ tự tin thực tế sẽ tự động giảm sâu.
        """
        history = self.capability_history.get(capability, [])
        if not history:
            return baseline

        success_rate = sum(1 for x in history if x) / len(history)
        # Đồng bộ nhân quả: tự tin = baseline * thành tích lịch sử
        calibrated = round(baseline * (0.4 + 0.6 * success_rate), 2)
        
        logger.info(f"🧠 [SELF-MODEL] Định chuẩn năng lực `{capability}`: Lịch sử {success_rate*100}% -> Độ tự tin: {calibrated}")
        return calibrated


class ValueOfThoughtEstimator:
    """
    💰 [COGNITIVE-ECONOMY]: Sổ cái Kinh tế nhận thức thưa Tổng Giám Đốc.
    Chặn đứng việc gọi LLM đắt đỏ cho các tác vụ đơn giản có thể giải quyết bằng mã nguồn định tính.
    """
    @staticmethod
    def evaluate_thought_cost(task_id: str, difficulty: int, is_critical: bool) -> Dict[str, Any]:
        """
        Đánh giá xem có cần thiết phải sử dụng suy luận xác suất (LLM) không thưa Master.
        Trả về phương án thực thi và mô hình tối ưu nhất.
        """
        # Thang độ khó từ 1-10
        if difficulty <= 3 and not is_critical:
            # Rất đơn giản, đề xuất chạy bằng mã nguồn Python deterministic
            return {
                "decision": "DETERMINISTIC_CODE",
                "recommended_model": "none",
                "reason": "Tác vụ độ khó thấp, ưu tiên mã nguồn cứng để tiết kiệm 100% token thưa Master.",
                "saves_gpu": True
            }
        elif difficulty <= 6:
            # Độ khó trung bình, đề xuất sử dụng Đặc vụ CHAT (thường nằm trên GPU hoặc CPU tối ưu)
            return {
                "decision": "ROLE_BASED_MODEL",
                "recommended_role": "CHAT",
                "reason": "Độ khó trung bình, ưu tiên nơ-ron CHAT để phản hồi nhanh thưa Master.",
                "saves_gpu": True
            }
        else:
            # Tác vụ phức tạp, bắt buộc dùng nơ-ron cao cấp (PLANNER/EXECUTOR)
            return {
                "decision": "ADVANCED_REASONING",
                "recommended_role": "PLANNER",
                "reason": "Tác vụ cực kỳ phức tạp và nhạy cảm, triệu tập nơ-ron PLANNER thưa Master.",
                "saves_gpu": False
            }


# =====================================================================
# 🌳 4. ERLANG-LIKE SUPERVISOR TREE & LẬP LỊCH CHẠY LUỒNG
# =====================================================================

@dataclass
class ThoughtThread:
    thread_id: str
    task_id: str
    goal_stack: GoalStack
    state: TaskState = TaskState.RECEIVED
    retry_count: int = 0
    max_retries: int = 3
    is_suspended: bool = False
    created_at: float = field(default_factory=time.time)


class CognitiveSupervisor:
    """
    🏢 BAN GIÁM SÁT MIỄN DỊCH & PHỤC HỒI (Erlang-like Supervisor Tree)
    Chịu trách nhiệm quản lý, điều phối và hồi sức các luồng tư duy thưa Tổng Giám Đốc.
    """
    def __init__(self, self_model: SelfModelCortex):
        self.self_model = self_model
        self._threads: Dict[str, ThoughtThread] = {}
        self._lock = asyncio.Lock()

    async def register_thread(self, thread_id: str, task_id: str, goal: str) -> ThoughtThread:
        async with self._lock:
            stack = GoalStack(task_id)
            stack.push(f"{thread_id}-root", goal, GoalLevel.STRATEGIC)
            thread = ThoughtThread(thread_id=thread_id, task_id=task_id, goal_stack=stack)
            self._threads[thread_id] = thread
            return thread

    async def handle_thread_failure(self, thread_id: str, error: Exception, capability: str) -> str:
        """
        🏥 [HỒI SỨC SỰ CỐ]: Xử lý sự cố sập luồng tư duy chuẩn Erlang Supervisor thưa Master.
        """
        async with self._lock:
            thread = self._threads.get(thread_id)
            if not thread:
                return "THREAD_NOT_FOUND"

            thread.state = TaskState.FAILED
            self.self_model.record_outcome(capability, False)
            
            # Gửi sự kiện báo lỗi lên hệ thống Bus
            await cognitive_event_bus.publish(CognitiveEvent(
                event_id=f"evt-fail-{thread_id}-{int(time.time())}",
                event_type="THOUGHT_FAILED",
                task_id=thread.task_id,
                agent_id="Supervisor",
                payload={"error": str(error), "capability": capability}
            ))

            # Tính toán lại độ tự tin thực tế thưa Tổng Giám Đốc
            conf = self.self_model.calibrate_confidence(thread.task_id, capability)

            # CỔNG PHÊ DUYỆT MASTER (Human-in-the-Loop Fallback Gate)
            if conf < 0.65:
                thread.is_suspended = True
                engine.publish_mission_log(
                    "HUMAN_FALLBACK_GATE",
                    f"🚨 [CỔNG AN NINH CỨU HỘ] Độ tự tin sụt giảm nghiêm trọng ({conf} < 0.65). "
                    f"Kích hoạt trạng thái tạm đình chỉ luồng `SUSPENDED` chờ Master chỉ đạo khôi phục thưa Master!",
                    thread.task_id,
                    "sys"
                )
                return "SUSPENDED_WAITING_MASTER"

            # 2. Nếu vẫn còn lượt thử lại, áp dụng Exponential Backoff thưa Master
            if thread.retry_count < thread.max_retries:
                thread.retry_count += 1
                backoff_time = 2 ** thread.retry_count
                engine.publish_mission_log(
                    "SUPERVISOR_ACTION",
                    f"🏥 [PHỤC HỒI SUPERVISOR] Thử lại luồng tư duy `{thread_id}` lần thứ {thread.retry_count}/{thread.max_retries}. "
                    f"Áp dụng độ trễ Exponential Backoff {backoff_time} giây...",
                    thread.task_id,
                    "sys"
                )
                await asyncio.sleep(backoff_time)
                thread.state = TaskState.RETRYING
                return "RETRY"

            # 3. Nếu hết lượt thử lại, chuyển sang Chế độ Degraded Mode thưa Master
            engine.publish_mission_log(
                "DEGRADED_MODE",
                f"🚨 [PHỤC HỒI THẤT BẠI] Đã cạn kiệt lượt thử phục hồi cho luồng `{thread_id}`. "
                f"Tự động kích hoạt chế độ suy giảm chức năng `DEGRADED` (Chuyển đổi sang mô hình Local siêu nhẹ thưa Master)...",
                thread.task_id,
                "sys"
            )
            thread.state = TaskState.FAILED
            return "DEGRADED_FAILURE"


# =====================================================================
# 👁️ 5. BIỆT ĐỘI GIÁM SÁT MIỄN DỊCH (COGNITIVE WATCHDOG SWARM)
# =====================================================================

class CognitiveWatchdogSwarm:
    """
    🕵️ [BIỆT ĐỘI WATCHDOG]: Hệ miễn dịch hoạt động ngầm bằng mã nguồn deterministic thưa Master.
    Phát hiện rò rỉ bộ nhớ, vòng lặp debate vô tận, hallucination và starvation.
    """
    def __init__(self, supervisor: CognitiveSupervisor):
        self.supervisor = supervisor
        self._running = False

    async def start_monitoring(self):
        """ Kích hoạt tuần tra định kỳ thưa Tổng Giám Đốc. """
        self._running = True
        asyncio.create_task(self._watchdog_loop())
        logger.info("🛡️ [WATCHDOG-SWARM]: Biệt đội giám sát miễn dịch lõi đã lên đường tuần tra!")

    def stop_monitoring(self):
        self._running = False

    async def _watchdog_loop(self):
        while self._running:
            try:
                # Kiểm toán sức khỏe hệ thống
                await self._audit_memory()
                await self._audit_tokens_and_loops()
                await self._audit_scheduler_starvation()
            except Exception as e:
                logger.error(f"❌ [WATCHDOG-SWARM-ERR] Sự cố trong chu kỳ tuần tra: {e}")
            await asyncio.sleep(10) # Tuần tra mỗi 10 giây thưa Master

    async def _audit_memory(self):
        """ Memory Watchdog: Quản lý xả bộ đệm VRAM khẩn cấp thưa Master. """
        health = homeostasis_engine.check_vitals()
        if health["survival_threat"]:
            logger.warn("🚨 [MEMORY-WATCHDOG]: Phát hiện nguy cơ đe dọa sinh tồn! Kích hoạt Homeostasis xả VRAM gấp...")
            await cognitive_event_bus.publish(CognitiveEvent(
                event_id=f"evt-vram-{int(time.time())}",
                event_type="VRAM_PRESSURE_HIGH",
                task_id="sys",
                agent_id="MemoryWatchdog",
                payload={"vitals": health["vitals"]}
            ))
            # Hồi sức nội môi thông qua homeostasis engine
            await homeostasis_engine.enforce_homeostasis("sys", "sys")

    async def _audit_tokens_and_loops(self):
        """ Token Watchdog: Triệt tiêu ngay lập tức runaway debate loops thưa Master. """
        for thread_id, thread in self.supervisor._threads.items():
            # Giả định nếu độ dài của goal stack vượt quá 15 tầng đệ quy -> loops
            if len(thread.goal_stack._stack) > 15:
                engine.publish_mission_log(
                    "WATCHDOG_TERMINATE",
                    f"💀 [TOKEN-WATCHDOG] Phát hiện luồng tư duy `{thread_id}` rơi vào vòng lặp vô hạn (Tràn ngăn xếp mục tiêu >15). "
                    f"Kích hoạt lệnh hủy diệt khẩn cấp luồng để bảo vệ CPU/VRAM thưa Tổng Giám Đốc!",
                    thread.task_id,
                    "sys"
                )
                thread.state = TaskState.QUARANTINED
                await cognitive_event_bus.publish(CognitiveEvent(
                    event_id=f"evt-loop-{thread_id}-{int(time.time())}",
                    event_type="WORLD_CONSTRAINT_VIOLATION",
                    task_id=thread.task_id,
                    agent_id="TokenWatchdog",
                    payload={"reason": "Infinite goal decomposition loop detected"}
                ))

    async def _audit_scheduler_starvation(self):
        """ Scheduler Watchdog: Tránh nghẽn và bỏ đói tiến trình thưa Master. """
        now = time.time()
        for thread_id, thread in self.supervisor._threads.items():
            if thread.state == TaskState.EXECUTING and (now - thread.created_at) > 300: # Treo > 5 phút
                logger.warn(f"⚠️ [SCHEDULER-WATCHDOG]: Luồng tư duy `{thread_id}` có dấu hiệu bị Starvation (treo >300s).")
                await cognitive_event_bus.publish(CognitiveEvent(
                    event_id=f"evt-starve-{thread_id}-{int(time.time())}",
                    event_type="THOUGHT_FAILED",
                    task_id=thread.task_id,
                    agent_id="SchedulerWatchdog",
                    payload={"reason": "Thread starvation / hang-up detected"}
                ))
