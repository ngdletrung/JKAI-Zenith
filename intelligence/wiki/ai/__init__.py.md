---
type: python_file
file: __init__.py
tags: []
---

# __init__

"""
Core package cho JKAI v3 - Shared library
"""

from .logger import setup_logger
from .exceptions import *

__version__ = "6.0"
__all__ = ["setup_logger"]

## Links to
- [[logger]]
- [[exceptions]]

## Linked by
- [[postgres_client.py - PostgresClient]]
- [[qdrant_client.py - QdrantClientWrapper]]
- [[rate_limiter.py - RateLimiter]]
- [[redis_client.py - RedisClient]]
- [[utils/claim_manager.py - ClaimManager]]
- [[utils/cognitive_guardrails.py - GuardrailException.__init__]]
- [[utils/cognitive_guardrails.py - GuardrailException]]
- [[utils/cognitive_guardrails.py - CognitiveGuardrails]]
- [[utils/cognitive_guardrails.py - GuardrailRegistry]]
- [[utils/crdt_engine.py - ZenithCRDT]]
- [[utils/engine.py - JKAIIntelligenceEngine]]
- [[utils/event_store.py - EventStore]]
- [[utils/execution_policy.py - ExecutionPolicyEngine]]
- [[utils/failure_memory.py - FailureMemory]]
- [[utils/hlc.py - HlcTimestamp]]
- [[utils/hlc.py - LocalHlc]]
- [[utils/hook_manager.py - HookManager]]
- [[utils/knowledge_brain.py - KnowledgeBrain]]
- [[utils/knowledge_manager.py - JKAIKnowledgeOrchestrator]]
- [[utils/neural_bridge.py - NeuralBridge]]
- [[utils/orchestrator.py - NeuralOrchestrator]]
- [[utils/path_manager.py - PathManager]]
- [[utils/reasoning_bank.py - ReasoningBank]]
- [[utils/security.py - SecurityEngine]]
- [[utils/sovereign_guard.py - SovereignGuard]]
- [[utils/state_machine.py - ZenithStateMachine]]
- [[utils/trajectory.py - TrajectoryRecorder]]
