import json
import logging
from typing import TypeVar, Type, Any, Dict, Optional
from pydantic import BaseModel, ValidationError
from core.utils.regex import extract_json

logger = logging.getLogger("JKAI.StructuredOutput")

T = TypeVar("T", bound=BaseModel)

class OutputSchema(BaseModel):
    """Base schema for all structured JKAI outputs."""
    pass

class LookupOutput(OutputSchema):
    answer: str
    sources: list[str] = []
    confidence: float = 1.0

class PlanOutput(OutputSchema):
    steps: list[dict[str, Any]]
    reasoning: str = ""

class CriticOutput(OutputSchema):
    passed: bool
    issues: list[str] = []
    suggestions: list[str] = []

class ExecuteOutput(OutputSchema):
    action: str
    params: dict[str, Any] = {}
    result: Optional[str] = None

SCHEMA_REGISTRY: dict[str, type[BaseModel]] = {
    "LOOKUP": LookupOutput,
    "PLANNER": PlanOutput,
    "CRITIC": CriticOutput,
    "EXECUTOR": ExecuteOutput,
}

class StructuredOutputWrapper:
    def __init__(self, engine):
        self.engine = engine
        self.max_retries = 2

    async def call(
        self,
        model_class: Type[T],
        messages: list,
        role: str = "RECEPTIONIST",
        task_id: str = "sys",
        **kwargs
    ) -> T:
        schema = model_class.model_json_schema()
        schema_str = json.dumps(schema, ensure_ascii=False, indent=2)

        last_error = None
        for attempt in range(self.max_retries + 1):
            attempt_messages = list(messages)
            if attempt > 0 and last_error:
                attempt_messages.append({
                    "role": "user",
                    "content": f"Previous JSON parse error: {last_error}\nFix and return valid JSON matching this schema:\n{schema_str}"
                })

            raw = await self.engine.call_chat(
                messages=attempt_messages,
                role=role,
                json_mode=True,
                task_id=task_id,
                **kwargs
            )

            parsed = self._try_parse(raw, model_class)
            if parsed is not None:
                return parsed

            last_error = str(raw)[:500]
            logger.warning(f"[STRUCTURED-OUTPUT] Attempt {attempt + 1} failed for {role}: {last_error}")

        raise ValueError(f"Structured output failed after {self.max_retries + 1} attempts for role={role}")

    def _try_parse(self, raw: Any, model_class: Type[T]) -> Optional[T]:
        if isinstance(raw, dict):
            try:
                return model_class.model_validate(raw)
            except ValidationError:
                pass
        
        try:
            if isinstance(raw, dict):
                raw_str = json.dumps(raw, ensure_ascii=False)
            else:
                raw_str = str(raw)
            data = extract_json(raw_str)
            if isinstance(data, dict):
                return model_class.model_validate(data)
        except Exception:
            pass
        return None

structured_output = None

def init_structured_output(engine):
    global structured_output
    structured_output = StructuredOutputWrapper(engine)
    return structured_output
