# -*- coding: utf-8 -*-
import pytest
from core.kernel.working_memory_eviction import WorkingMemoryEvictionEngine, SymbolSkeleton
from core.kernel.error_signature import ErrorSignatureEngine, ErrorSignature


def test_working_memory_eviction_extraction():
    engine = WorkingMemoryEvictionEngine(cache_dir="data/cache/test_evicted")
    sample_code = """
import os

class DatabaseGuard:
    def __init__(self):
        pass

    def check_connection(self):
        return True

class SecurityGate:
    async def evaluate_payload(self, payload):
        return {"allowed": False}

def helper_util():
    pass
"""
    skeleton = engine.extract_skeleton("core/security/guard.py", sample_code)
    assert skeleton.file_path == "core/security/guard.py"
    assert skeleton.line_count > 10
    assert len(skeleton.sha256_16) == 16
    assert "DatabaseGuard" in skeleton.classes
    assert "SecurityGate" in skeleton.classes
    assert "check_connection" in skeleton.functions
    assert "evaluate_payload" in skeleton.functions


def test_working_memory_eviction_render_observation():
    engine = WorkingMemoryEvictionEngine(cache_dir="data/cache/test_evicted")
    long_code = "\n".join([f"# line {i}: print('code {i}')" for i in range(200)])
    obs = engine.evict_and_render_observation("core/security/big_module.py", long_code, max_retain_lines=10)
    
    assert "[SYMBOL-SKELETON (Working Memory Eviction Active)]" in obs
    assert "Tổng số dòng: 200 dòng" in obs
    assert len(obs) < len(long_code)  # Token count substantially reduced


def test_error_signature_clustering_and_recording(tmp_path):
    test_file = str(tmp_path / "test_error_signatures.jsonl")
    engine = ErrorSignatureEngine(ledger_path=test_file)
    
    sig1 = engine.record_failure(
        error_type="CONFIRMATION_BIAS_FABRICATION",
        trigger_pattern="view_file_failed",
        automated_invariant="Phải trả về needs_validation khi không đọc được tệp",
        task_id="TASK-TEST-1"
    )
    assert sig1.occurrences == 1
    
    # Ghi nhận lần 2 cùng error_type và trigger_pattern -> Tự động gom cụm tăng occurrences
    sig2 = engine.record_failure(
        error_type="CONFIRMATION_BIAS_FABRICATION",
        trigger_pattern="view_file_failed",
        automated_invariant="Phải trả về needs_validation khi không đọc được tệp",
        task_id="TASK-TEST-2"
    )
    assert sig2.signature_id == sig1.signature_id
    assert sig2.occurrences == 2


def test_error_signature_dynamic_awareness_prompt(tmp_path):
    test_file = str(tmp_path / "test_error_signatures.jsonl")
    engine = ErrorSignatureEngine(ledger_path=test_file)
    goal = "Kiểm toán 2 tệp core/security/egress_gate.py và core/security/data_leak_guard.py"
    prompt = engine.render_dynamic_awareness_prompt(goal)
    
    assert "META CCA ERROR SIGNATURES" in prompt
    assert "ERR-SIG-" in prompt
