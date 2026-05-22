"""
🧬 [ZENITH-LOGIC]: agent-v3-memory-specialist
"""
import asyncio

async def agent_v3_memory_specialist(**kwargs):
    """Thuc thi ky nang dong hoa tu Ruflo thua Master."""
    from core.utils.knowledge_brain import knowledge_brain
    task_id = kwargs.get("task_id", "manual")
    prompt = f"Executing agent-v3-memory-specialist with params: {kwargs}"
    return await knowledge_brain.ask(prompt, tier=2, task_id=task_id)
