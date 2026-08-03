# JKAI Zenith — Architecture Ownership Map

## Overview
JKAI Zenith is structured into 4 distinct architectural planes. Each plane has strict responsibility boundaries and zero responsibility overlap.

```
                         ┌───────────────────────────┐
                         │           USER            │
                         │  Goal / Intent / Mission  │
                         └─────────────┬─────────────┘
                                       │
╔══════════════════════════════════════════════════════════════════╗
║                    COGNITIVE OS / JKAI KERNEL                  ║
║                                                                  ║
║  PLANE 1 — COGNITIVE PLANE                                       ║
║  - Mission Machine, Intent Detection, ReAct Loop, Skills        ║
║  - Module: services/ai-brain/, core/kernel/                      ║
║  - Responsibility: WHAT must happen?                            ║
║                                                                  ║
║  PLANE 2 — KNOWLEDGE / WORLD PLANE                              ║
║  - RAG, Qdrant Memory, World Model, Entity Resolver             ║
║  - Module: core/qdrant_client.py, core/kernel/world_model.py     ║
║  - Responsibility: WHAT does JKAI know about the world?         ║
║                                                                  ║
║  PLANE 3 — GOVERNOR PLANE (AMG v2)                              ║
║  - ModelRegistry, ModelInspector, ResourceGov, PortfolioGov     ║
║  - Module: core/governor/                                       ║
║  - Interface: ExecutionPolicy → AMG → ExecutionProfile          ║
║  - Responsibility: WHICH compute resource to use? (Model-Blind) ║
║                                                                  ║
║  PLANE 4 — EXECUTION PLANE                                       ║
║  - RuntimeAdapter, NeuralRuntime, HardwareScheduler             ║
║  - Module: core/runtime/, core/utils/neural_runtime.py          ║
║  - Contract: ResourceRequest → HardwareScheduler.acquire()      ║
║  - Responsibility: HOW to execute the profile on hardware?      ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## Single-Responsibility Matrix

| Decision / Function | Responsible Module | Anti-Pattern (FORBIDDEN) |
|---|---|---|
| Parse `rule_hardware.md` | `ModelRouter` (`core/utils/model_router.py`) | Reading rules in `engine.py` or `.bat` |
| Inspect model capabilities | `ModelInspector` (`core/governor/model_inspector.py`) | Inspecting model name string in Python |
| Select model for role | `PortfolioGovernor` (`core/governor/portfolio_governor.py`) | Hardcoding model names in `.py` or `.bat` |
| Enforce VRAM / CPU budget | `HardwareScheduler` (`core/utils/hardware_scheduler.py`) | Inspecting `model_name` inside Scheduler |
| Execute inference | `NeuralRuntime` (`core/utils/neural_runtime.py`) | Deciding model choice inside Runtime |
| Cognitive Orchestration | `JKAIIntelligenceEngine` (`core/utils/engine.py`) | Assembling model options manually |

---

## Data Contracts (ABI)

1. **`RoleRequirement`** (`core/governor/model_capabilities.py`):
   Task requirements produced by `ExecutionPolicy` from user intent & role mapping.

2. **`ModelCapabilityProfile`** (`core/governor/model_capabilities.py`):
   Intrinsic model capability classification produced by `ModelInspector` from Ollama `/api/show`.

3. **`ExecutionProfile`** (`core/governor/model_capabilities.py`):
   Standard execution ABI produced by `AMG` / `ModelRouter.resolve_execution_profile()`.
   Consumed by `Engine` and `NeuralRuntime`.

4. **`ResourceRequest`** (`core/utils/models.py`):
   Hardware resource reservation contract produced by `ExecutionProfile.to_resource_request()`.
   Consumed by `HardwareScheduler.acquire()`.

5. **`DecisionTrace`** (`core/governor/decision_trace.py`):
   Structured, append-only audit trail recorded per AMG decision for full human observability.
