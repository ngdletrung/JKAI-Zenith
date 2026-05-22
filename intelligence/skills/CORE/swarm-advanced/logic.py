"""
🧬 [ZENITH-LOGIC]: swarm-advanced
"""
import asyncio

async def swarm_advanced(**kwargs):
    """Thuc thi ky nang dong hoa tu Ruflo thua Master."""
    from core.utils.knowledge_brain import knowledge_brain
    task_id = kwargs.get("task_id", "manual")
    prompt = f"Executing swarm-advanced with params: {kwargs}"
    return await knowledge_brain.ask(prompt, tier=2, task_id=task_id)
