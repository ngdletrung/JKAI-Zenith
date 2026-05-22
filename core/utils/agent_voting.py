# ============================================================
# 🧠 AGENT VOTING SYSTEM (REAL MULTI-AGENT)
# ============================================================

import logging
from utils.llm import call_llm

logger = logging.getLogger("agent_voting")


def generate_candidates(task, context):

    agents = [
        ("A", "Viết code nhanh"),
        ("B", "Viết code tối ưu"),
        ("C", "Viết code an toàn, ít lỗi")
    ]

    outputs = {}

    for name, role in agents:
        prompt = f"""
{role}

Task:
{task}

Context:
{context}
"""
        outputs[name] = call_llm(prompt, mode="code")

    return outputs


def critic_agents(outputs):

    critiques = {}

    for name, code in outputs.items():
        prompt = f"""
Phân tích code sau:

{code}

Ưu / Nhược điểm
"""
        critiques[name] = call_llm(prompt, mode="reason")

    return critiques


def judge_vote(outputs, critiques):

    prompt = f"""
Có 3 phương án:

{outputs}

Phân tích:

{critiques}

Chọn phương án tốt nhất: A, B hoặc C
Chỉ trả 1 chữ.
"""

    decision = call_llm(prompt, mode="reason")

    if "B" in decision:
        return outputs["B"]
    elif "C" in decision:
        return outputs["C"]
    else:
        return outputs["A"]