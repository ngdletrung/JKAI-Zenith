class RuntimeScheduler:
    """
    ⚖️ Quản lý Băng thông & Công bằng (Fairness & Budget)
    Ngăn chặn một Planner hoặc Tool nuốt trọn Kernel.
    """
    def __init__(self):
        self.MAX_STEPS_PER_TRACE = 20
        self.MAX_TOOL_CALLS = 8
        self.MAX_RETRIES = 2
        
        # State tracking (In memory for now, move to Redis for distributed)
        self._trace_stats = {}

    def init_trace(self, trace_id: str):
        self._trace_stats[trace_id] = {
            "steps": 0,
            "tool_calls": 0,
            "retries": 0
        }

    def record_step(self, trace_id: str):
        if trace_id not in self._trace_stats:
            self.init_trace(trace_id)
        stats = self._trace_stats[trace_id]
        stats["steps"] += 1
        
        if stats["steps"] > self.MAX_STEPS_PER_TRACE:
            raise Exception("Quota Exceeded: Too many steps in a single trace (Infinite Loop detected?)")

    def record_tool_call(self, trace_id: str):
        stats = self._trace_stats.get(trace_id, {"tool_calls": 0})
        stats["tool_calls"] += 1
        
        if stats["tool_calls"] > self.MAX_TOOL_CALLS:
            raise Exception("Quota Exceeded: Too many tool calls in this trace.")
