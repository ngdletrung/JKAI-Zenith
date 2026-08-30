"""
JKAI AI OS — COGNITIVE SCHEDULER
File: core/kernel/cognitive_scheduler.py

Provides Priority-Driven Preemptive Scheduling across Cognitive Processes.
Handles Resource Contention, Process Preemption, Time-Slicing, and Resumption.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid
import time
import os
import shutil
import asyncio

class ProcessState(str, Enum):
    NEW = "NEW"
    READY = "READY"
    RUNNING = "RUNNING"
    PREEMPTED = "PREEMPTED"
    WAITING = "WAITING"
    COMMITTED = "COMMITTED"
    TERMINATED = "TERMINATED"

class ProcessPriority(int, Enum):
    IDLE = 0
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class ProcessControlBlock:
    pid: str = field(default_factory=lambda: f"proc-{uuid.uuid4().hex[:8]}")
    name: str = "cognitive_proc"
    priority: ProcessPriority = ProcessPriority.NORMAL
    state: ProcessState = ProcessState.NEW
    cpu_share: float = 1.0
    memory_mb: float = 128.0
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def transition(self, new_state: ProcessState):
        self.state = new_state

class CognitiveResourceManager:
    """Quản lý hạn mức tài nguyên CPU & RAM cho các tiến trình nhận thức."""
    def __init__(self, max_cpu: float = 4.0, max_ram_mb: float = 4096.0):
        self.max_cpu = max_cpu
        self.max_ram_mb = max_ram_mb
        self.used_cpu = 0.0
        self.used_ram_mb = 0.0

    def allocate(self, pcb: ProcessControlBlock) -> bool:
        if self.used_cpu + pcb.cpu_share <= self.max_cpu and self.used_ram_mb + pcb.memory_mb <= self.max_ram_mb:
            self.used_cpu += pcb.cpu_share
            self.used_ram_mb += pcb.memory_mb
            return True
        return False

    def release(self, pcb: ProcessControlBlock):
        self.used_cpu = max(0.0, self.used_cpu - pcb.cpu_share)
        self.used_ram_mb = max(0.0, self.used_ram_mb - pcb.memory_mb)

cognitive_resource_manager = CognitiveResourceManager()


class CognitiveScheduler:
    """Schedules, preempts, and dispatches cognitive processes."""

    def __init__(self, resource_manager: Optional[CognitiveResourceManager] = None):
        self.rm = resource_manager or cognitive_resource_manager
        self.ready_queue: List[ProcessControlBlock] = []
        self.running_processes: Dict[str, ProcessControlBlock] = {}
        self.preempted_queue: List[ProcessControlBlock] = []

    def admit_process(self, pcb: ProcessControlBlock) -> None:
        """Admits a new process into the ready queue."""
        pcb.transition(ProcessState.READY)
        self.ready_queue.append(pcb)
        # Sort ready queue descending by priority
        self.ready_queue.sort(key=lambda p: p.priority.value, reverse=True)

    def schedule_next(self) -> Optional[ProcessControlBlock]:
        """Dispatches the next highest-priority process that fits in resource capacity."""
        if not self.ready_queue and not self.preempted_queue:
            return None

        # Check preempted queue first
        for i, pcb in enumerate(self.preempted_queue):
            if self.rm.allocate(pcb):
                self.preempted_queue.pop(i)
                pcb.transition(ProcessState.RUNNING)
                self.running_processes[pcb.pid] = pcb
                return pcb

        # Then check ready queue
        for i, pcb in enumerate(self.ready_queue):
            if self.rm.allocate(pcb):
                self.ready_queue.pop(i)
                pcb.transition(ProcessState.RUNNING)
                self.running_processes[pcb.pid] = pcb
                return pcb

        # Resource contention: Check if highest priority ready process can preempt lower priority running process
        if self.ready_queue:
            highest_ready = self.ready_queue[0]
            for pid, running in list(self.running_processes.items()):
                if running.priority.value < highest_ready.priority.value:
                    # Preempt running process
                    self.preempt_process(running)
                    if self.rm.allocate(highest_ready):
                        self.ready_queue.pop(0)
                        highest_ready.transition(ProcessState.RUNNING)
                        self.running_processes[highest_ready.pid] = highest_ready
                        return highest_ready

        return None

    def preempt_process(self, pcb: ProcessControlBlock) -> None:
        """Preempts a running process to reclaim resource quota."""
        if pcb.pid in self.running_processes:
            del self.running_processes[pcb.pid]
            self.rm.release(pcb)
            pcb.transition(ProcessState.PREEMPTED)
            self.preempted_queue.append(pcb)

    def complete_process(self, pcb: ProcessControlBlock) -> None:
        """Marks a process committed and releases its hardware allocation."""
        if pcb.pid in self.running_processes:
            del self.running_processes[pcb.pid]
        self.ready_queue = [p for p in self.ready_queue if p.pid != pcb.pid]
        self.preempted_queue = [p for p in self.preempted_queue if p.pid != pcb.pid]
        self.rm.release(pcb)
        pcb.transition(ProcessState.COMMITTED)


# =====================================================================
# 🛡️ 2. TRANSACTION & SAFETY ROLLBACK (COGNITIVE TRANSACTION MANAGER)
# =====================================================================
from enum import Enum
import os
import shutil
import asyncio
from typing import Callable, Any

class TransactionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMMITTED = "COMMITTED"
    ROLLED_BACK = "ROLLED_BACK"

class CognitiveTransaction:
    def __init__(self, tx_id: str, task_id: str):
        self.tx_id = tx_id
        self.task_id = task_id
        self.status = TransactionStatus.ACTIVE
        self.backups: Dict[str, str] = {}
        self.compensating_actions: List[Callable[[], Any]] = []

class CognitiveTransactionManager:
    """Quản lý các giao dịch tự cải tiến và sao lưu .bak khôi phục an toàn."""
    def __init__(self):
        self._active_txs: Dict[str, CognitiveTransaction] = {}
        self._lock = asyncio.Lock()

    async def begin_transaction(self, tx_id: str, task_id: str) -> CognitiveTransaction:
        async with self._lock:
            tx = CognitiveTransaction(tx_id, task_id)
            self._active_txs[tx_id] = tx
            return tx

    async def register_backup(self, tx_id: str, file_path: str):
        async with self._lock:
            tx = self._active_txs.get(tx_id)
            if not tx:
                return
            if file_path not in tx.backups:
                if os.path.exists(file_path):
                    backup_path = f"{file_path}.bak"
                    try:
                        shutil.copy2(file_path, backup_path)
                        tx.backups[file_path] = backup_path
                    except Exception:
                        pass
                else:
                    tx.backups[file_path] = "NEW_FILE"

    async def commit_transaction(self, tx_id: str):
        async with self._lock:
            tx = self._active_txs.pop(tx_id, None)
            if not tx:
                return
            for orig, bkp in tx.backups.items():
                if bkp != "NEW_FILE" and os.path.exists(bkp):
                    try:
                        os.remove(bkp)
                    except Exception:
                        pass
            tx.status = TransactionStatus.COMMITTED

    async def rollback_transaction(self, tx_id: str):
        async with self._lock:
            tx = self._active_txs.pop(tx_id, None)
            if not tx:
                return
            for orig, bkp in tx.backups.items():
                try:
                    if bkp == "NEW_FILE":
                        if os.path.exists(orig):
                            os.remove(orig)
                    elif os.path.exists(bkp):
                        shutil.move(bkp, orig)
                except Exception:
                    pass
            tx.status = TransactionStatus.ROLLED_BACK

cognitive_transaction_manager = CognitiveTransactionManager()
