from models.task import Task

class MemoryWriteGate:
    async def _is_repeated_pattern(self, step_result: dict) -> bool:
        # Check qdrant or postgres if this pattern appeared >= 2 times
        return True

    async def _contains_pii(self, step_result: dict) -> bool:
        # Run local NER/Regex for PII detection
        return False

    async def should_write(self, step_result: dict, task: Task) -> bool:
        # Điều kiện 1: Confidence đủ cao
        if step_result.get("confidence", 0) < 0.8: return False
        # Điều kiện 2: Pattern đã thấy ≥ 2 lần (không phải one-off)
        if not await self._is_repeated_pattern(step_result): return False
        # Điều kiện 3: Không phải transient error
        if step_result.get("failure_type"): return False
        # Điều kiện 4: Không chứa PII
        if await self._contains_pii(step_result): return False
        return True

    async def write_if_qualified(self, step_result: dict, task: Task, qdrant_client):
        if not await self.should_write(step_result, task): return
        # await qdrant_client.upsert_skill_pattern(step_result, task)
        pass
