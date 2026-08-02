from .mission_context import MissionContext
from .context_assembler import ContextAssembler

_context_assembler = ContextAssembler()


class ContextPromptBuilder:
    def build_from_context(self, mc: MissionContext, question: str, kb_context: str = "") -> str:
        ctx = _context_assembler.assemble(mc, question, kb_context)
        parts = []
        if ctx.get("goal"):
            parts.append(f"Mục tiêu: {ctx['goal']}")
        if ctx.get("current_topic"):
            parts.append(f"Chủ đề: {ctx['current_topic']}")
        if ctx.get("previous_question"):
            parts.append(f"Câu hỏi trước: {ctx['previous_question']}")
        if ctx.get("previous_answer"):
            parts.append(f"Câu trả lời trước: {ctx['previous_answer']}")
        if ctx.get("known_facts"):
            fact_lines = [f"  - {f['type']}: {f['value']} (từ {f.get('source', 'unknown')})" for f in ctx["known_facts"]]
            parts.append("Sự kiện đã biết:\n" + "\n".join(fact_lines))
        if ctx.get("kb_context"):
            parts.append(f"Tài liệu tham khảo:\n{ctx['kb_context']}")
        parts.append(f"Câu hỏi hiện tại: {question}")
        return "\n\n".join(parts)
