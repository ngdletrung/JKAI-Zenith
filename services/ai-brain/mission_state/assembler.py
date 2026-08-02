# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/mission_state/assembler.py
# - Role: Prompt Assembler, Token Budgeting & Priority Truncator
# - Ownership: Mr LeeTrung
# - Status: Active | Version: ZenithOS v1.0

import hashlib
import logging
from typing import List, Dict, Any, Tuple
from .schema import MissionState

logger = logging.getLogger("JKAI.PromptAssembler")

class PromptAssembler:
    """Assembles prompt payload prioritizing elements by critical importance."""
    
    @staticmethod
    def get_fingerprint(prompt: str) -> str:
        """Computes SHA256 signature of prompt for response caching optimization."""
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    def assemble(self, state: MissionState, system_rules: str, extra_kb: List[str] = None, token_limit: int = 4000) -> Tuple[str, str]:
        """
        Assembles prompt under a token limit constraint.
        Components are structured using Priority Queue concept:
        - Priority 4 (Critical): Mission Goal, System Rules (Never cut)
        - Priority 3 (High): Valid Facts
        - Priority 2 (Medium): Memory and Citations
        - Priority 1 (Low): Extra KB / context chunks
        """
        kb_chunks = extra_kb or []
        
        # 1. Prepare components
        goal_xml = f"<goal>\n{state.metadata.user_goal}\n</goal>"
        rules_xml = f"<rules>\n{system_rules}\n</rules>"
        
        valid_facts = [content for content in state.facts.facts_db.values() if content.valid]
        facts_str = "\n".join([f"- {f.content}" for f in valid_facts])
        facts_xml = f"<facts>\n{facts_str}\n</facts>" if facts_str else ""
        
        memory_str = "\n".join([f"{k}: {v}" for k, v in state.memory.mission_memory.items()])
        memory_xml = f"<memory>\n{memory_str}\n</memory>" if memory_str else ""
        
        citations_str = "\n".join([f"- {c.source_path} ({c.line_range or 'Full'})" for c in state.references.citations.values()])
        citations_xml = f"<citations>\n{citations_str}\n</citations>" if citations_str else ""
        
        kb_str = "\n---\n".join(kb_chunks)
        kb_xml = f"<context_chunks>\n{kb_str}\n</context_chunks>" if kb_str else ""

        active_ents = [f"- {ent['entity']} (confidence: {ent['confidence']})" for ent in state.active_entity_stack]
        active_ents_str = "\n".join(active_ents)
        active_ents_xml = f"<active_entities>\n{active_ents_str}\n</active_entities>" if active_ents_str else ""

        # Simple character-based estimation helper (1 token ~= 4 chars)
        def estimate_tokens(text: str) -> int:
            return len(text) // 4

        # Compile in order of priority: 4, 3, 2, 1
        critical_section = f"{rules_xml}\n{goal_xml}"
        high_section = facts_xml
        medium_section = f"{memory_xml}\n{citations_xml}\n{active_ents_xml}".strip()
        low_section = kb_xml

        assembled_sys_prompt = critical_section
        
        # Add High Priority
        if estimate_tokens(assembled_sys_prompt + "\n" + high_section) <= token_limit:
            assembled_sys_prompt += "\n" + high_section
        else:
            logger.warning("⚠️ [BUDGET-LIMIT]: High-priority facts excluded/truncated due to token budget constraint.")

        # Add Medium Priority
        if estimate_tokens(assembled_sys_prompt + "\n" + medium_section) <= token_limit:
            assembled_sys_prompt += "\n" + medium_section
        else:
            logger.warning("⚠️ [BUDGET-LIMIT]: Medium-priority memory/citations truncated due to token budget constraint.")

        # Add Low Priority
        if estimate_tokens(assembled_sys_prompt + "\n" + low_section) <= token_limit:
            assembled_sys_prompt += "\n" + low_section
        else:
            logger.warning("⚠️ [BUDGET-LIMIT]: Low-priority KB chunks truncated due to token budget constraint.")

        fingerprint = self.get_fingerprint(assembled_sys_prompt)
        logger.info(f"🔑 [PROMPT-ASSEMBLED]: Fingerprint: {fingerprint[:8]}... Under limit: {estimate_tokens(assembled_sys_prompt)}/{token_limit} tokens.")
        
        return assembled_sys_prompt, fingerprint
