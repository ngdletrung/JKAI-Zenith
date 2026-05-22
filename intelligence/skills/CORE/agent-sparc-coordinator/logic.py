"""
🧬 [ZENITH-LOGIC]: agent-sparc-coordinator
"""
import asyncio

async def agent_sparc_coordinator(**kwargs):
    """Thuc thi ky nang dong hoa tu Ruflo thua Master."""
    from core.utils.knowledge_brain import knowledge_brain
    task_id = kwargs.get("task_id", "manual")
    prompt = f"Executing agent-sparc-coordinator with params: {kwargs}"
    return await knowledge_brain.ask(prompt, tier=2, task_id=task_id)
