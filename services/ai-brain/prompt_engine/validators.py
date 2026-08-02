import json
import logging
from typing import TypeVar, Type, Any, Optional
from pydantic import BaseModel, ValidationError

logger = logging.getLogger("JKAI.PromptEngine.Validators")

T = TypeVar("T", bound=BaseModel)


class SchemaValidator:
    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries

    def try_parse(self, raw: Any, model_class: Type[T]) -> Optional[T]:
        if isinstance(raw, dict):
            try:
                return model_class.model_validate(raw)
            except ValidationError as e:
                logger.debug("[VALIDATOR] dict validation failed: %s", e)
                return None
        if isinstance(raw, str):
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.strip("`").strip()
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:].strip()
            try:
                data = json.loads(cleaned)
                return model_class.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as e:
                logger.debug("[VALIDATOR] str validation failed: %s", e)
                return None
        return None

    def build_error_feedback(self, raw: Any, model_class: Type[T]) -> str:
        schema = model_class.model_json_schema()
        error_detail = ""
        if isinstance(raw, str):
            error_detail = f"Phản hồi nhận được không phải JSON hợp lệ: {raw[:200]}"
        elif isinstance(raw, dict):
            try:
                model_class.model_validate(raw)
            except ValidationError as e:
                error_detail = f"Lỗi schema: {e}"
        return (
            f"<error_feedback_retry>\n"
            f"  <attempt_info>\n"
            f"    {error_detail}\n"
            f"  </attempt_info>\n"
            f"  <schema_requirement>\n{json.dumps(schema, ensure_ascii=False, indent=2)}\n"
            f"  </schema_requirement>\n"
            f"  <instruction>Hãy sửa lại phản hồi và chỉ xuất ra JSON hợp lệ theo schema trên.</instruction>\n"
            "</error_feedback_retry>"
        )

    async def validate_with_retry(
        self,
        model_class: Type[T],
        messages: list,
        engine_call_fn,
        role: str = "RECEPTIONIST",
        task_id: str = "sys",
        **kwargs
    ) -> T:
        last_raw = None
        for attempt in range(self.max_retries + 1):
            attempt_messages = list(messages)
            if attempt > 0 and last_raw is not None:
                feedback = self.build_error_feedback(last_raw, model_class)
                attempt_messages.append({"role": "user", "content": feedback})

            raw = await engine_call_fn(
                messages=attempt_messages,
                role=role,
                json_mode=True,
                task_id=task_id,
                **kwargs
            )

            parsed = self.try_parse(raw, model_class)
            if parsed is not None:
                if attempt > 0:
                    logger.info("[VALIDATOR-RETRY] Success on attempt %d for %s", attempt + 1, role)
                return parsed

            last_raw = raw
            logger.warning("[VALIDATOR] Attempt %d failed for %s", attempt + 1, role)

        raise ValueError(f"Validation failed after {self.max_retries + 1} attempts for role={role}")


schema_validator = SchemaValidator()
