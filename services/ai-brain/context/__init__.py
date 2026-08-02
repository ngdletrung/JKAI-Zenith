from .mission_context import MissionContext, MissionContextManager
from .entity_resolver import EntityResolver
from .reference_resolver import ReferenceResolver
from .working_memory import WorkingMemory, WorkingRecord
from .fact_extractor import FactExtractor
from .context_assembler import ContextAssembler
from .context_prompt_builder import ContextPromptBuilder

mission_context = MissionContextManager()
entity_resolver = EntityResolver()
reference_resolver = ReferenceResolver()
working_memory = WorkingMemory()
fact_extractor = FactExtractor()
context_assembler = ContextAssembler()
context_prompt_builder = ContextPromptBuilder()
