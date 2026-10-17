# -*- coding: utf-8 -*-
"""
JKAI Universal Cloud Provider Client (JKAI Discuss Protocol v1.0).
Provides a unified, secure OpenAI-compatible REST client for Gemini, DeepSeek,
OpenAI, and Grok, adhering strictly to pre-send inspection and timeout limits.
"""

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import urllib.request
import urllib.error

logger = logging.getLogger("JKAI.Security.CloudProviderClient")


@dataclass
class CloudResponse:
    provider: str
    model: str
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    is_mock: bool = False
    error: Optional[str] = None


class CloudProviderClient:
    """
    Universal OpenAI-compatible client for multi-model deliberation.
    """

    DEFAULT_ENDPOINTS = {
        "gemini": {
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
            "env_key": "GEMINI_API_KEY",
            "default_model": "gemini-2.5-flash",
        },
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "env_key": "OPENAI_API_KEY",
            "default_model": "gpt-4o-mini",
        },
        "chatgpt": {
            "base_url": "https://api.openai.com/v1",
            "env_key": "OPENAI_API_KEY",
            "default_model": "gpt-4o-mini",
        },
        "deepseek": {
            "base_url": "https://api.deepseek.com",
            "env_key": "DEEPSEEK_API_KEY",
            "default_model": "deepseek-chat",
        },
        "grok": {
            "base_url": "https://api.x.ai/v1",
            "env_key": "GROK_API_KEY",
            "default_model": "grok-beta",
        },
    }

    def __init__(self, rules_file_path: Optional[str] = None):
        # SSoT: Keys are strictly resolved from runtime environment variables (os.getenv)
        self.rules_file_path = rules_file_path

    def get_api_key(self, provider: str) -> Optional[str]:
        cfg = self.DEFAULT_ENDPOINTS.get(provider.lower())
        if not cfg:
            return None
        env_var = cfg["env_key"]
        val = os.getenv(env_var, "").strip()
        return val if val else None

    def call_chat_completion(
        self,
        provider: str,
        messages: List[Dict[str, str]],
        model_name: Optional[str] = None,
        temperature: float = 0.3,
        timeout: int = 15,
        simulate: bool = False,
    ) -> CloudResponse:
        """
        Executes chat completion via OpenAI-compatible REST API.
        """
        prov_key = provider.lower()
        cfg = self.DEFAULT_ENDPOINTS.get(prov_key)
        if not cfg:
            return CloudResponse(
                provider=provider,
                model=model_name or "unknown",
                content="",
                error=f"Unsupported provider: {provider}",
            )

        from core.security.dynamic_model_resolver import dynamic_model_resolver
        target_model = dynamic_model_resolver.resolve_model(prov_key, model_name)

        if simulate:
            # Explicit simulation mode ONLY when simulate=True is requested by test harness
            user_topic = messages[-1].get("content", "")[:120] if messages else "general_topic"
            simulated_text = (
                f"[FACT] [SIMULATED] Analysis generated in test simulation mode for: {user_topic}\n"
                f"[INFERENCE] Deterministic boundary checks and fallback cascades reduce failure blast radius.\n"
                f"[HYPOTHESIS] Adjusting concurrency limits improves throughput stability.\n"
                f"[UNKNOWN] Real-world tail latency requires live benchmark verification."
            )
            return CloudResponse(
                provider=provider,
                model=target_model,
                content=simulated_text,
                prompt_tokens=max(10, len(user_topic.split()) * 2),
                completion_tokens=48,
                total_tokens=max(58, len(user_topic.split()) * 2 + 48),
                is_mock=True,
            )

        api_key = self.get_api_key(prov_key)
        if not api_key:
            return CloudResponse(
                provider=provider,
                model=target_model,
                content="",
                is_mock=False,
                error=f"missing_api_key:{cfg['env_key']}",
            )

        # Build request
        candidate_models = [target_model] + dynamic_model_resolver.get_fallback_chain(prov_key, target_model)
        last_error = None

        for candidate in candidate_models:
            url = f"{cfg['base_url'].rstrip('/')}/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }
            payload = {
                "model": candidate,
                "messages": messages,
                "temperature": temperature,
            }

            try:
                req_data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    res_body = response.read().decode("utf-8")
                    res_json = json.loads(res_body)

                    choices = res_json.get("choices", [])
                    content = choices[0]["message"]["content"] if choices else ""
                    usage = res_json.get("usage", {})

                    return CloudResponse(
                        provider=provider,
                        model=candidate,
                        content=content,
                        prompt_tokens=usage.get("prompt_tokens", 0),
                        completion_tokens=usage.get("completion_tokens", 0),
                        total_tokens=usage.get("total_tokens", 0),
                        is_mock=False,
                    )
            except urllib.error.HTTPError as e:
                last_error = str(e)
                # If 404 (model deprecated) or 503 (high demand), try next candidate model
                if e.code in (404, 503) and candidate != candidate_models[-1]:
                    logger.warning("Model %s returned HTTP %s, trying fallback...", candidate, e.code)
                    continue
                break
            except Exception as e:
                last_error = str(e)
                break

        return CloudResponse(
            provider=provider,
            model=target_model,
            content="",
            error=last_error,
        )


cloud_provider_client = CloudProviderClient()
