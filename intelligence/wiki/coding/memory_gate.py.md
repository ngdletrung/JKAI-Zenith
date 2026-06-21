---
type: python_file
file: memory_gate.py
tags: []
---

# memory_gate

from models.task import Task

class MemoryWriteGate:
    async def _is_repeated_pattern(self, step_result: dict) -> bool:
        # Check qdrant or postgres if this pattern appeared >= 2 times
        return True

    async def _contains_pii(self, step_result: dict) -> bool:
        # Run local NER/

## Links to
- [[models.task]]
