"""
🏛️ ADAPTIVE MODEL GOVERNOR (AMG) v2 — EXECUTION POLICY
File: core/governor/execution_policy.py

Purpose:
    Maps raw rule_hardware.md role config → final ExecutionProfile,
    applying PortfolioGovernor for "auto" model requests and direct
    profile construction for explicit model assignments.

    This is the bridge between rule_hardware.md parsing (ModelRouter)
    and the AMG pipeline (PortfolioGovernor).
"""

from __future__ import annotations
import logging
from typing import Any, Dict, Optional, List

from core.governor.model_capabilities import (
    ExecutionProfile, GovernorDecision, ROLE_REQUIREMENTS
)

logger = logging.getLogger("AMG_ExecutionPolicy")


class ExecutionPolicy:
    """
    Converts a parsed role configuration dict into a final ExecutionProfile.

    Input from ModelRouter:
        {
            "role": "PLANNER",
            "model": "auto",               # or "qwen3.6:35b-a3b"
            "capability": ["reasoning"],   # only for auto
            "quality": "high",             # only for auto
            "hardware": "auto",            # or "GPU" / "CPU" / "CPU/RAM"
            "num_ctx": 8192,
            "temperature": 0.05,
            "num_predict": 1024,
            ... (raw Ollama options)
        }

    Output:
        ExecutionProfile (model-agnostic, consumed by Engine)
    """

    def __init__(self, governor=None):
        # Import here to avoid circular import at module load time
        self._governor = governor  # PortfolioGovernor — injected or lazy-loaded

    def _get_governor(self):
        if self._governor is None:
            from core.governor.portfolio_governor import PortfolioGovernor
            self._governor = PortfolioGovernor()
        return self._governor

    def derive_profile(
        self,
        role_config: Dict[str, Any],
    ) -> ExecutionProfile:
        """
        Main entry point.
        Delegates to PortfolioGovernor for auto routing,
        or builds a direct ExecutionProfile for explicit model.
        """
        role    = role_config.get("role", "RECEPTIONIST").upper()
        model   = role_config.get("model", "").strip()
        quality = role_config.get("quality", "medium").lower()
        hw_tag  = role_config.get("hardware", "auto")
        ctx     = int(role_config.get("num_ctx", 4096))

        # Capability requirements (for auto routing)
        cap_raw = role_config.get("capability", [])
        capabilities: List[str] = (
            [c.strip() for c in cap_raw.split(",") if c.strip()]
            if isinstance(cap_raw, str)
            else [str(c).strip() for c in (cap_raw or [])]
        )

        # Raw options passthrough (temperature, num_predict, etc.)
        raw_options = self._extract_raw_options(role_config)

        gov = self._get_governor()
        profile = gov.resolve(
            role=role,
            requested_model=model or "auto",
            capability_requirements=capabilities,
            quality=quality,
            context_len=ctx,
            requested_hardware=hw_tag,
        )

        # Merge raw_options from rule_hardware.md (highest precedence)
        if raw_options:
            profile.raw_options.update(raw_options)
            # Also apply specific fields directly
            if "temperature" in raw_options:
                profile.temperature = raw_options.pop("temperature")
            if "num_predict" in raw_options:
                profile.num_predict = raw_options.pop("num_predict")
            if "num_ctx" in raw_options:
                profile.num_ctx = raw_options.pop("num_ctx")
            if "num_thread" in raw_options:
                profile.num_thread = raw_options.pop("num_thread")

        return profile

    @staticmethod
    def _extract_raw_options(config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract Ollama-passthrough options from role config dict."""
        _SKIP_KEYS = {"role", "model", "quality", "hardware", "capability",
                      "profile", "gpu_layers", "backend"}
        result = {}
        for k, v in config.items():
            if k not in _SKIP_KEYS and v is not None and v != "":
                try:
                    result[k] = type(v)(v) if not isinstance(v, (int, float, bool, str)) else v
                except Exception:
                    result[k] = str(v)
        return result

    @staticmethod
    def build_legacy_profile(
        model_name: str,
        role: str,
        backend: str,
        raw_options: Dict[str, Any],
    ) -> ExecutionProfile:
        """
        Backward-compatible profile builder for explicit model configs
        that bypass the auto-routing path entirely.
        Called by ModelRouter for non-auto legacy entries in rule_hardware.md.
        """
        role_req = ROLE_REQUIREMENTS.get(role.upper())

        # Map legacy hardware tags → backend + memory_layout
        backend_clean, layout = ExecutionPolicy._map_hardware_tag(backend)
        gpu_layers = raw_options.pop("gpu_layers", 32 if backend_clean == "GPU" else 0)

        return ExecutionProfile(
            model_name=model_name,
            role_name=role.upper(),
            backend=backend_clean,
            memory_layout=layout,
            num_gpu_layers=gpu_layers,
            num_predict=int(raw_options.pop("num_predict", role_req.max_output_tokens if role_req else 512)),
            num_ctx=int(raw_options.pop("num_ctx", 4096)),
            num_thread=int(raw_options.pop("num_thread", 20)),
            temperature=float(raw_options.pop("temperature", role_req.default_temp if role_req else 0.2)),
            top_p=float(raw_options.pop("top_p", 0.9)),
            repeat_penalty=float(raw_options.pop("repeat_penalty", 1.1)),
            use_mmap=bool(raw_options.pop("use_mmap", True)),
            keep_alive=str(raw_options.pop("keep_alive", "-1")),
            raw_options=raw_options,
            resolved_via="explicit",
        )

    @staticmethod
    def _map_hardware_tag(tag: str) -> tuple[str, str]:
        """Map legacy hardware tag strings to (backend, memory_layout)."""
        t = tag.upper().replace(" ", "").replace("/", "_")
        mapping = {
            "GPU":          ("GPU",    "VRAM_ONLY"),
            "HYBRID":       ("HYBRID", "VRAM_RAM_SPLIT"),
            "CPU":          ("CPU",    "RAM_ONLY"),
            "CPU_RAM":      ("CPU",    "RAM_ONLY"),
            "CPURAM":       ("CPU",    "RAM_ONLY"),
            "VRAM":         ("GPU",    "VRAM_ONLY"),
            "RAM":          ("CPU",    "RAM_ONLY"),
            "VRAM_RAM":     ("HYBRID", "VRAM_RAM_SPLIT"),
        }
        return mapping.get(t, ("CPU", "RAM_ONLY"))
