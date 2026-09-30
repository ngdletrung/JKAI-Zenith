# -*- coding: utf-8 -*-
"""
core/cognitive_bus/backends/ollama_backend.py
JKAI Zenith - Local Ollama Structured Classifier Backend (v2.0)
Architecture: System-1 Local Reasoning via In-Process Ollama HTTP API

Invariants:
  - 100% Localhost Egress: strictly 127.0.0.1:11434.
  - Model: qwen3:0.6b (default, fast local inference) or via JKAI_OLLAMA_MODEL.
  - JSON structured output enforcement.
"""

from __future__ import annotations

import os
import json
import time
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, Tuple

from core.cognitive_bus.decision_substrate_adapter import (
    DecisionPrimitive,
    ExecutionTier,
    TypedJudgementPacket,
)
from core.cognitive_bus.tier2_backend import BackendMetadata


class LocalOllamaTier2Backend:
    """
    Tier 2 backend adapter for local Ollama server running on 127.0.0.1:11434.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: float = 2.0,
    ):
        self.base_url = (base_url or os.getenv("JKAI_OLLAMA_HOST", "http://127.0.0.1:11434")).rstrip("/")
        self.model_name = model_name or os.getenv("JKAI_OLLAMA_MODEL", "qwen3:0.6b")
        self.timeout_seconds = timeout_seconds
        self._loaded = False

    def load(self) -> None:
        """Verifies local Ollama server connectivity."""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m.get("name", "") for m in data.get("models", [])]
                self._loaded = any(self.model_name in m for m in models) or len(models) > 0
        except Exception:
            self._loaded = False

    def unload(self) -> None:
        self._loaded = False

    def is_loaded(self) -> bool:
        return self._loaded

    def metadata(self) -> BackendMetadata:
        return BackendMetadata(
            name=f"ollama-{self.model_name}",
            version="1.0",
            is_deterministic=False,
            is_local_only=True,
            supported_languages=("en", "vi", "*"),
            calibration_state="uncalibrated",
            ece=None,
            notes="Local Ollama inference substrate running on localhost:11434.",
        )

    def predict(
        self,
        state: Dict[str, Any],
        questions: List[Tuple[DecisionPrimitive, str, Optional[List[str]]]],
        timeout_ms: int = 2000,
    ) -> Dict[str, TypedJudgementPacket]:
        if not self._loaded:
            self.load()
            if not self._loaded:
                raise RuntimeError("Local Ollama backend is not accessible on localhost.")

        results: Dict[str, TypedJudgementPacket] = {}
        timeout_sec = min(float(timeout_ms) / 1000.0, self.timeout_seconds)

        for prim, question, options in questions:
            t0 = time.perf_counter()
            prompt = self._build_prompt(state, prim, question, options)
            payload = json.dumps({
                "model": self.model_name,
                "prompt": prompt,
                "format": "json",
                "stream": False,
                "options": {
                    "temperature": 0.0,
                    "num_predict": 128
                }
            }).encode("utf-8")

            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"}
            )

            with urllib.request.urlopen(req, timeout=timeout_sec) as response:
                raw_bytes = response.read()
                resp_json = json.loads(raw_bytes.decode("utf-8"))
                output_str = resp_json.get("response", "{}")
                parsed_output = json.loads(output_str)

            latency = (time.perf_counter() - t0) * 1000.0
            packet = self._parse_to_packet(prim, question, options, parsed_output, latency)
            results[question] = packet

        return results

    def _build_prompt(
        self,
        state: Dict[str, Any],
        prim: DecisionPrimitive,
        question: str,
        options: Optional[List[str]]
    ) -> str:
        state_repr = json.dumps(state, ensure_ascii=False)
        if prim == DecisionPrimitive.BOOLEAN:
            return (
                f"You are a strict binary evaluator. Based on the state: {state_repr}\n"
                f"Question: {question}\n"
                f'Respond ONLY with JSON: {{"result": true/false, "confidence": float between 0.0 and 1.0}}'
            )
        elif prim == DecisionPrimitive.CHOICE:
            opts_str = json.dumps(options or ["none_of_the_above"])
            return (
                f"You are a strict categorical router. Based on the state: {state_repr}\n"
                f"Question: {question}\n"
                f"Options: {opts_str}\n"
                f'Respond ONLY with JSON: {{"winner": "<one of options>", "confidence": float between 0.0 and 1.0}}'
            )
        else:  # SCORE
            lvls = options or ["0", "1", "2", "3", "4"]
            return (
                f"You are a strict score evaluator. Based on the state: {state_repr}\n"
                f"Question: {question}\n"
                f"Levels: {lvls}\n"
                f'Respond ONLY with JSON: {{"score": float, "confidence": float between 0.0 and 1.0}}'
            )

    def _parse_to_packet(
        self,
        prim: DecisionPrimitive,
        question: str,
        options: Optional[List[str]],
        output: Dict[str, Any],
        latency_ms: float
    ) -> TypedJudgementPacket:
        conf = float(output.get("confidence", 0.95))
        conf = max(0.0, min(1.0, conf))

        if prim == DecisionPrimitive.BOOLEAN:
            raw_res = output.get("result", False)
            res_val = 1.0 if (raw_res is True or raw_res == 1 or raw_res == "true") else 0.0
            dist = {"true": res_val, "false": round(1.0 - res_val, 6)}
            return TypedJudgementPacket(
                primitive=prim,
                question=question,
                result=res_val,
                confidence=conf,
                distribution=dist,
                execution_tier=ExecutionTier.TIER_2_LOCAL,
                latency_ms=latency_ms,
                metadata={"backend": "ollama", "model": self.model_name}
            )
        elif prim == DecisionPrimitive.CHOICE:
            opts = options or ["none_of_the_above"]
            winner = output.get("winner", opts[0])
            if winner not in opts:
                winner = opts[0]
            rest = (1.0 - conf) / max(1, len(opts) - 1)
            dist = {o: (conf if o == winner else round(rest, 6)) for o in opts}
            residual = 1.0 - sum(dist.values())
            if residual != 0.0:
                dist[winner] = round(dist[winner] + residual, 6)
            return TypedJudgementPacket(
                primitive=prim,
                question=question,
                result=winner,
                confidence=conf,
                distribution=dist,
                execution_tier=ExecutionTier.TIER_2_LOCAL,
                latency_ms=latency_ms,
                metadata={"backend": "ollama", "model": self.model_name}
            )
        else:  # SCORE
            levels = options or ["0", "1", "2", "3", "4"]
            score = float(output.get("score", 0.0))
            n = len(levels)
            base = round(1.0 / n, 6)
            dist = {str(i): base for i in range(n)}
            residual = 1.0 - sum(dist.values())
            dist[str(0)] = round(dist[str(0)] + residual, 6)
            return TypedJudgementPacket(
                primitive=prim,
                question=question,
                result=score,
                confidence=conf,
                distribution=dist,
                execution_tier=ExecutionTier.TIER_2_LOCAL,
                latency_ms=latency_ms,
                metadata={"backend": "ollama", "model": self.model_name}
            )
