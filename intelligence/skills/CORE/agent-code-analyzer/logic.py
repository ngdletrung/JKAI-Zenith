"""
🧬 [ZENITH-LOGIC]: agent-code-analyzer
"""
import asyncio

async def agent_code_analyzer(**kwargs):
    """Thuc thi ky nang dong hoa tu Ruflo thua Master."""
    from core.utils.knowledge_brain import knowledge_brain
    task_id = kwargs.get("task_id", "manual")
    prompt = f"Executing agent-code-analyzer with params: {kwargs}"
    return await knowledge_brain.ask(prompt, tier=2, task_id=task_id)
