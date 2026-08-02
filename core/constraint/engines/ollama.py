import json
import logging
from typing import Any
from pydantic import BaseModel, ValidationError

from core.constraint.base import ConstraintEngine, ConstraintResult
from core.utils.regex import extract_json

logger = logging.getLogger(__name__)


class OllamaEngine(ConstraintEngine):
    name = "ollama"

    def generate(
        self,
        prompt: str,
        schema: type[BaseModel],
        system: str | None = None,
        temperature: float = 0.1,
        **kwargs,
    ) -> ConstraintResult:
        import httpx

        host = kwargs.get("ollama_host") or "http://host.docker.internal:11434"
        model = kwargs.get("model") or "qwen2.5:7b"

        schema_json = schema.model_json_schema()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "format": schema_json,
            "options": {"temperature": temperature, "num_predict": kwargs.get("max_tokens", 4096)},
            "stream": False,
        }

        try:
            resp = httpx.post(
                f"{host}/api/chat",
                json=payload,
                timeout=kwargs.get("timeout", 120),
            )
            resp.raise_for_status()
            body = resp.json()
            raw = body.get("message", {}).get("content", "")
        except Exception as e:
            raise RuntimeError(f"Ollama request failed: {e}") from e

        try:
            parsed = extract_json(raw)
            data = schema.model_validate(parsed)
        except (json.JSONDecodeError, ValueError, ValidationError) as e:
            raise RuntimeError(f"Ollama output did not match schema {schema.__name__}: {e}\nRaw: {raw[:500]}") from e

        return ConstraintResult(data=data, raw=raw, engine=self.name)
