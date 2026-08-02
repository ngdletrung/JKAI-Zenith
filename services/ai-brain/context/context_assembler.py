from typing import Optional
from .mission_context import MissionContext


class ContextAssembler:
    def assemble(self, mc: MissionContext, question: str, kb_context: str = "") -> dict:
        sections = {}
        sections["goal"] = mc.meta.get("goal", "")
        sections["current_topic"] = mc.derived.get("current_topic", "")
        if mc.conversation.get("last_answer"):
            sections["previous_answer"] = mc.conversation["last_answer"]
        if mc.conversation.get("last_query"):
            sections["previous_question"] = mc.conversation["last_query"]
        if mc.conversation.get("facts"):
            sections["known_facts"] = mc.conversation["facts"]
        if kb_context:
            sections["kb_context"] = kb_context
        sections["question"] = question
        return sections
