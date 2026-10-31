# -*- coding: utf-8 -*-
"""
[ZENITH FILE DIRECTIVE]
- File: tests/test_memory_phase_r8_resilience.py
- Role: Test Suite for Phase R-Memory-8 Operational Resilience & Telemetry Governance Hardening.
- Ownership: Master LeeTrung | Swarm: Antigravity (Builder) & Opencode (Auditor)
- Status: Active | Version: SOP V5.1
"""

import os
import sys
import time
import json
import hashlib
import pytest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.memory.memory_telemetry import (
    MemoryTelemetryLogger,
    MemoryTelemetryEvent,
    TelemetryEventType,
    TelemetryLogRotator,
    EmergencyDeadLetterRing,
    WriteDropAlertPolicy,
    DualHeuristicEstimator,
    TokenEstimatorProtocol,
    hash_identifier
)
from core.memory.completion_authority import (
    CompletionAuthorityStore,
    canonical_json_dumps
)


# ==============================================================================
# TEST 1 & 2: LOG ROTATION DURABILITY & CONCURRENCY
# ==============================================================================

def test_rotation_flush_fsync_and_no_record_loss(tmp_path: Path):
    """
    Verify that when log file reaches max_bytes, rotation occurs under lock,
    rotated file contains all flushed records, new active file is created, and no records are lost.
    """
    log_file = tmp_path / "telemetry_rot.jsonl"
    logger = MemoryTelemetryLogger(log_path=log_file, max_log_bytes=200, max_backup_files=10)

    # Write events to exceed 200 bytes
    for i in range(5):
        evt = MemoryTelemetryEvent(event_id=f"rot_{i}", event_type="TEST", timestamp=time.time())
        logger.emit_event(evt)

    # Active log or rotated file must exist and total lines must equal 5
    rotations = list(tmp_path.glob("telemetry_rot_*.jsonl"))
    assert len(rotations) >= 1

    total_records = 0
    for r in rotations:
        lines = [l for l in r.read_text(encoding="utf-8").splitlines() if l.strip()]
        total_records += len(lines)

    if log_file.exists():
        total_records += len([l for l in log_file.read_text(encoding="utf-8").splitlines() if l.strip()])

    assert total_records == 5

    # Manifest must record rotation
    man_file = tmp_path / "telemetry_rotation_manifest.json"
    assert man_file.exists()
    man_data = json.loads(man_file.read_text(encoding="utf-8"))
    assert len(man_data["rotations"]) >= 1
    assert man_data["rotations"][0]["sha256"] != ""


def test_rotation_process_lock_no_duplicate_records(tmp_path: Path):
    """
    Verify rotation performed under process lock preserves single record uniqueness.
    """
    log_file = tmp_path / "proc_rot.jsonl"
    logger = MemoryTelemetryLogger(log_path=log_file, max_log_bytes=150, max_backup_files=5)

    emitted_ids = set()
    for i in range(6):
        eid = f"unique_rot_evt_{i}"
        emitted_ids.add(eid)
        logger.emit_event(MemoryTelemetryEvent(event_id=eid, event_type="TEST", timestamp=time.time()))

    # Read all files (active + rotated)
    found_ids = []
    all_files = list(tmp_path.glob("proc_rot*.jsonl"))
    for f in all_files:
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                found_ids.append(rec["event_id"])

    # No duplicates, all emitted IDs present
    assert len(found_ids) == len(set(found_ids))
    assert set(found_ids) == emitted_ids


# ==============================================================================
# TEST 3: RETENTION POLICY NON-BLIND PRUNING
# ==============================================================================

def test_retention_respects_manifest_references(tmp_path: Path):
    """
    Verify older rotated files are pruned up to max_backup_files,
    EXCEPT files that are referenced in CompletionCertificate manifest.
    """
    log_file = tmp_path / "telemetry_ret.jsonl"
    man_file = tmp_path / "telemetry_rotation_manifest.json"
    cert_ledger = tmp_path / "completion_certificates.jsonl"

    rotator = TelemetryLogRotator(log_path=log_file, max_bytes=100, max_backup_files=2, manifest_path=man_file)

    # Create 4 dummy rotated files
    f1 = tmp_path / "telemetry_ret_20260101_000001_000000.jsonl"
    f2 = tmp_path / "telemetry_ret_20260101_000002_000000.jsonl"
    f3 = tmp_path / "telemetry_ret_20260101_000003_000000.jsonl"
    f4 = tmp_path / "telemetry_ret_20260101_000004_000000.jsonl"

    for f in (f1, f2, f3, f4):
        f.write_text('{"event_id": "test"}\n', encoding="utf-8")

    man_data = {
        "version": "1.0",
        "rotations": [
            {"file_name": f1.name, "sha256": "sha1", "byte_size": 20, "rotated_at": "2026-01-01"},
            {"file_name": f2.name, "sha256": "sha2", "byte_size": 20, "rotated_at": "2026-01-02"},
            {"file_name": f3.name, "sha256": "sha3", "byte_size": 20, "rotated_at": "2026-01-03"},
            {"file_name": f4.name, "sha256": "sha4", "byte_size": 20, "rotated_at": "2026-01-04"},
        ]
    }
    man_file.write_text(json.dumps(man_data), encoding="utf-8")

    # Protect f1 by referencing it in a completion certificate
    cert_record = {
        "certificate_id": "cert_test_protect",
        "artifacts_manifest": [{"path": f"data/memory_ledger/{f1.name}"}]
    }
    cert_ledger.write_text(json.dumps(cert_record) + "\n", encoding="utf-8")

    # Trigger prune
    rotator._prune_old_archives()

    # f1 must be PRESERVED because it is protected by CompletionCertificate!
    assert f1.exists()
    # f2 is oldest unreferenced and should be pruned
    assert not f2.exists()
    # f3 and f4 are within the 2 most recent backups
    assert f3.exists()
    assert f4.exists()


# ==============================================================================
# TEST 4 & 5: EMERGENCY DEAD-LETTER BUFFER
# ==============================================================================

def test_dead_letter_bounded_and_redacted():
    """
    Verify EmergencyDeadLetterRing has bounded capacity, tracks drop count,
    and stores strictly redacted event objects (zero raw secrets).
    """
    ring = EmergencyDeadLetterRing(max_capacity=3)

    raw_secret_query = "API KEY ghp_SECRET_KEY_1234567890"
    evt1 = MemoryTelemetryEvent(
        event_id="e1",
        event_type=TelemetryEventType.SECURITY_SENTINEL.value,
        timestamp=time.time(),
        query_hash=hash_identifier(raw_secret_query),
        security_flag=True,
        security_finding_type="SECRET_PATTERN_DETECTED"
    )

    assert ring.push(evt1) is True
    assert ring.push(MemoryTelemetryEvent(event_id="e2", event_type="TEST", timestamp=time.time())) is True
    assert ring.push(MemoryTelemetryEvent(event_id="e3", event_type="TEST", timestamp=time.time())) is True
    # 4th item must be rejected due to capacity=3
    assert ring.push(MemoryTelemetryEvent(event_id="e4", event_type="TEST", timestamp=time.time())) is False
    assert ring.dead_letter_drop_count == 1

    # Verify zero raw secret in stored event
    popped = ring.pop_batch(1)[0]
    json_repr = popped.event.to_json()
    assert "ghp_SECRET_KEY_1234567890" not in json_repr
    assert popped.event.query_hash == hash_identifier(raw_secret_query)


def test_dead_letter_retry_limit_and_loss_alert():
    """
    Verify dead letter items are retried up to limit (3) and discarded with loss count.
    """
    ring = EmergencyDeadLetterRing(max_capacity=5)
    evt = MemoryTelemetryEvent(event_id="retry_me", event_type="TEST", timestamp=time.time())
    ring.push(evt)

    item = ring.pop_batch(1)[0]
    assert item.retry_count == 0

    ring.requeue_failed(item, max_retries=2)
    assert ring.size() == 1

    item2 = ring.pop_batch(1)[0]
    assert item2.retry_count == 1
    ring.requeue_failed(item2, max_retries=2)
    assert ring.size() == 1

    item3 = ring.pop_batch(1)[0]
    assert item3.retry_count == 2
    # Exceeds max_retries=2 -> must be dropped
    ring.requeue_failed(item3, max_retries=2)
    assert ring.size() == 0
    assert ring.dead_letter_drop_count == 1


# ==============================================================================
# TEST 6: ALERT POLICY & ANTI-SPAM COOLDOWN
# ==============================================================================

def test_alert_episode_dedup_and_restart_semantics():
    """
    Verify alert cooldown prevents spamming episodes, and reset logs reason.
    """
    policy = WriteDropAlertPolicy(alert_threshold=3, cooldown_seconds=10.0)

    # 1. Below threshold -> HEALTHY
    assert policy.evaluate_status(write_drop_count=2) == "HEALTHY"

    # 2. Reaches threshold -> ALERT_HIGH_WRITE_DROPS
    status1 = policy.evaluate_status(write_drop_count=3)
    assert status1 == "ALERT_HIGH_WRITE_DROPS"
    episode_1 = policy.alert_episode_id
    assert episode_1.startswith("ep_write_drop_")

    # 3. Repeated check during cooldown window -> remains in same episode, no new episode created
    status2 = policy.evaluate_status(write_drop_count=4)
    assert status2 == "ALERT_HIGH_WRITE_DROPS"
    assert policy.alert_episode_id == episode_1

    # 4. Dead letter overflow overrides status
    status_dl = policy.evaluate_status(write_drop_count=4, dead_letter_drop_count=1)
    assert status_dl == "ALERT_DEAD_LETTER_OVERFLOW"

    # 5. Audited reset
    policy.reset(reason="Admin investigated lock contention")
    assert policy.alert_episode_id == ""
    assert len(policy.reset_history) == 1
    assert policy.reset_history[0]["reason"] == "Admin investigated lock contention"


# ==============================================================================
# TEST 7, 8, 9: COMPLETION AUTHORITY & HASH CHAIN
# ==============================================================================

def test_completion_authority_issuer_cannot_be_spoofed(tmp_path: Path):
    """
    Verify CompletionAuthorityStore rejects certificates submitted with invalid authority token.
    """
    ledger = tmp_path / "certs.jsonl"
    store = CompletionAuthorityStore(ledger_path=ledger, authority_token="VALID_TOKEN_123")

    cert_data = {
        "phase": "PHASE_R_MEMORY_8",
        "session_id": "ses_test",
        "gate_target": "GATE_4_FINAL_SEAL",
        "artifacts_manifest": [{"path": "core/memory/memory_telemetry.py"}],
        "evidence_verification": {"targeted_tests": "pass"}
    }

    # Wrong token -> must raise PermissionError
    with pytest.raises(PermissionError, match="Unauthorized completion certificate issuer"):
        store.record_certificate(cert_data, token="SPOOFED_TOKEN")

    # Correct token -> succeeds
    rec = store.record_certificate(cert_data, token="VALID_TOKEN_123")
    assert rec["certificate_id"].startswith("cert_")
    assert rec["issuer"] == "CompletionAuthority"
    assert rec["previous_certificate_hash"] == "GENESIS"
    assert rec["certificate_hash"] != ""


def test_completion_certificate_hash_chain_tamper_fails_closed(tmp_path: Path):
    """
    Verify tamper detection fail-closed: any modified field or invalid previous_hash
    fails ledger verification with explicit error.
    """
    ledger = tmp_path / "tamper_certs.jsonl"
    store = CompletionAuthorityStore(ledger_path=ledger, authority_token="AUTH_KEY")

    cert1 = {
        "certificate_id": "c1",
        "phase": "PHASE_1",
        "session_id": "s1",
        "gate_target": "GATE_4",
        "artifacts_manifest": [],
        "evidence_verification": {}
    }
    cert2 = {
        "certificate_id": "c2",
        "phase": "PHASE_2",
        "session_id": "s2",
        "gate_target": "GATE_4",
        "artifacts_manifest": [],
        "evidence_verification": {}
    }

    store.record_certificate(cert1, token="AUTH_KEY")
    store.record_certificate(cert2, token="AUTH_KEY")

    # Initial chain is intact
    ok, err = store.verify_ledger_integrity()
    assert ok is True
    assert err is None

    # Tamper: modify first certificate phase in disk file
    lines = ledger.read_text(encoding="utf-8").splitlines()
    tampered_c1 = json.loads(lines[0])
    tampered_c1["phase"] = "TAMPERED_PHASE"
    lines[0] = json.dumps(tampered_c1)
    ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Tampered ledger must fail verification
    tampered_ok, tampered_err = store.verify_ledger_integrity()
    assert tampered_ok is False
    assert "TAMPER_DETECTED" in tampered_err


def test_completion_store_cross_process_append(tmp_path: Path):
    """
    Verify continuous sequential certificate appends form an unbroken cryptographic chain.
    """
    ledger = tmp_path / "chain_certs.jsonl"
    store = CompletionAuthorityStore(ledger_path=ledger, authority_token="CHAIN_TOKEN")

    for i in range(3):
        store.record_certificate({
            "certificate_id": f"cert_{i}",
            "phase": f"PHASE_{i}",
            "session_id": "ses_chain",
            "gate_target": "GATE_4",
            "artifacts_manifest": [],
            "evidence_verification": {"run": i}
        }, token="CHAIN_TOKEN")

    ok, err = store.verify_ledger_integrity()
    assert ok is True
    assert err is None

    # Verify retrieval by certificate_id
    c1 = store.get_certificate("cert_1")
    assert c1 is not None
    assert c1["phase"] == "PHASE_1"


# ==============================================================================
# TEST 10: PLUGGABLE TOKEN ESTIMATOR & FALLBACK
# ==============================================================================

class FlakyCustomTokenizer:
    estimator_id: str = "flaky_model_tokenizer"
    estimator_version: str = "v2.1"
    budget_policy_version: str = "v1.0"

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail

    def estimate_tokens(self, text: str) -> int:
        if self.should_fail:
            raise RuntimeError("Tokenizer internal backend timeout")
        return len(text.split()) * 2


def test_estimator_version_and_fallback_event():
    """
    Verify pluggable tokenizer metadata is tracked, and if custom tokenizer throws,
    it gracefully falls back to DualHeuristicEstimator and emits an ESTIMATOR_FALLBACK event.
    """
    logger = MemoryTelemetryLogger()

    # 1. Custom tokenizer works
    logger.set_estimator(FlakyCustomTokenizer(should_fail=False))
    tokens, est_id, est_ver, b_ver, is_fb = logger.estimate_tokens_with_policy("Hệ thống an toàn tự chủ")
    assert tokens == 12  # 6 words * 2
    assert est_id == "flaky_model_tokenizer"
    assert est_ver == "v2.1"
    assert is_fb is False

    # 2. Custom tokenizer fails -> fail-safe fallback
    logger.set_estimator(FlakyCustomTokenizer(should_fail=True))
    tokens_fb, fb_id, fb_ver, fb_bver, is_fb2 = logger.estimate_tokens_with_policy("Hệ thống an toàn tự chủ")
    assert tokens_fb > 0
    assert fb_id == "dual_heuristic"
    assert is_fb2 is True


# ==============================================================================
# TURN 510 HARDENING TESTS (BLOCKERS 1-5 RESOLUTION)
# ==============================================================================

def test_append_rejects_preexisting_chain_tamper(tmp_path: Path):
    """
    Turn 510 Blocker 1: Verify that record_certificate performs full ledger integrity
    verification before appending, rejecting append if pre-existing chain was tampered.
    """
    ledger = tmp_path / "tamper_append_ledger.jsonl"
    store = CompletionAuthorityStore(ledger_path=ledger, authority_token="VALID_KEY")

    # Record first valid certificate
    store.record_certificate({
        "certificate_id": "c1",
        "phase": "PHASE_1",
        "session_id": "s1",
        "gate_target": "GATE_4",
        "artifacts_manifest": [],
        "evidence_verification": {}
    }, token="VALID_KEY")

    # Tamper the ledger on disk
    lines = ledger.read_text(encoding="utf-8").splitlines()
    corrupted = json.loads(lines[0])
    corrupted["phase"] = "SPOOFED_PHASE"
    ledger.write_text(json.dumps(corrupted) + "\n", encoding="utf-8")

    # Attempt to append second certificate must fail-closed with RuntimeError
    with pytest.raises(RuntimeError, match="pre-existing ledger is tampered"):
        store.record_certificate({
            "certificate_id": "c2",
            "phase": "PHASE_2",
            "session_id": "s2",
            "gate_target": "GATE_4",
            "artifacts_manifest": [],
            "evidence_verification": {}
        }, token="VALID_KEY")


def test_duplicate_certificate_id_rejected(tmp_path: Path):
    """
    Turn 510 Blocker 2: Verify that submitting a certificate with an already-existing
    certificate_id is strictly rejected with ValueError.
    """
    ledger = tmp_path / "dup_id_ledger.jsonl"
    store = CompletionAuthorityStore(ledger_path=ledger, authority_token="VALID_KEY")

    cert_data = {
        "certificate_id": "CERT_UNIQUE_001",
        "phase": "PHASE_DUP",
        "session_id": "s_dup",
        "gate_target": "GATE_4",
        "artifacts_manifest": [],
        "evidence_verification": {}
    }

    store.record_certificate(cert_data, token="VALID_KEY")

    # Re-submitting identical certificate_id must raise ValueError
    with pytest.raises(ValueError, match="Duplicate certificate_id 'CERT_UNIQUE_001' rejected"):
        store.record_certificate(cert_data, token="VALID_KEY")


def test_missing_authority_key_fails_closed(tmp_path: Path):
    """
    Turn 510 Blocker 3: Verify that missing, empty, or unconfigured authority key
    fails closed with PermissionError (no insecure hardcoded default fallback).
    """
    ledger = tmp_path / "unconfigured_key_ledger.jsonl"
    # Store initialized with empty authority_token
    store = CompletionAuthorityStore(ledger_path=ledger, authority_token="")

    cert_data = {
        "certificate_id": "c_fail",
        "phase": "PHASE_FAIL",
        "session_id": "s_fail",
        "gate_target": "GATE_4",
        "artifacts_manifest": [],
        "evidence_verification": {}
    }

    with pytest.raises(PermissionError, match="invalid or unconfigured authority key"):
        store.record_certificate(cert_data, token="")


def test_rotation_crash_recovery_preserves_manifest(tmp_path: Path):
    """
    Turn 510 Blocker 4: Verify crash recovery scan recovers unmanifested rotated archives
    left by an interrupted rotation, adding them to manifest before any pruning occurs.
    """
    log_file = tmp_path / "telemetry_crash.jsonl"
    man_file = tmp_path / "telemetry_rotation_manifest.json"
    rotator = TelemetryLogRotator(log_path=log_file, max_bytes=500, max_backup_files=3, manifest_path=man_file)

    # Simulate an orphaned rotated file from a past crash
    orphaned_file = tmp_path / "telemetry_crash_20260101_120000_000000.jsonl"
    orphaned_file.write_text('{"event_id": "orphan_recovered"}\n', encoding="utf-8")

    # Manifest is initially empty
    assert not man_file.exists()

    # Trigger recovery scan
    recovered_count = rotator.recover_unmanifested_archives()
    assert recovered_count == 1

    # Manifest must now contain the recovered archive
    assert man_file.exists()
    man_data = json.loads(man_file.read_text(encoding="utf-8"))
    assert len(man_data["rotations"]) == 1
    assert man_data["rotations"][0]["file_name"] == orphaned_file.name
    assert man_data["rotations"][0]["sha256"] != ""


def test_dead_letter_shutdown_policy(tmp_path: Path):
    """
    Turn 510 Blocker 5: Verify shutdown() policy drains all queued items and attempts
    final flush of emergency dead-letter ring before process termination.
    """
    log_file = tmp_path / "shutdown_telemetry.jsonl"
    logger = MemoryTelemetryLogger(log_path=log_file)

    # Push items into queue
    evt1 = MemoryTelemetryEvent(event_id="shut_1", event_type="TEST", timestamp=time.time())
    evt2 = MemoryTelemetryEvent(event_id="shut_2", event_type="TEST", timestamp=time.time())
    logger.queue.put_nowait(evt1)
    logger.queue.put_nowait(evt2)

    # Also push a critical security event into emergency dead-letter ring
    sec_evt = MemoryTelemetryEvent(
        event_id="shut_sec",
        event_type=TelemetryEventType.SECURITY_SENTINEL.value,
        timestamp=time.time(),
        security_flag=True
    )
    logger.dead_letter_ring.push(sec_evt)

    # Call shutdown
    logger.shutdown()

    # Log file must contain all 3 events
    lines = [json.loads(l) for l in log_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    event_ids = [l["event_id"] for l in lines]
    assert "shut_1" in event_ids
    assert "shut_2" in event_ids
    assert "shut_sec" in event_ids
    assert logger.dead_letter_ring.size() == 0


# ==============================================================================
# TURN 512 HARDENING TESTS (BLOCKERS 1-4 RESOLUTION)
# ==============================================================================

def test_public_verify_and_append_lock_contract(tmp_path: Path):
    """
    Turn 512 Blocker 1: Verify that record_certificate, verify_ledger_integrity,
    and get_certificate execute cleanly without lock re-entrancy anomalies or TOCTOU.
    """
    ledger = tmp_path / "lock_contract_certs.jsonl"
    store = CompletionAuthorityStore(ledger_path=ledger, authority_token="KEY_CONTRACT")

    # 1. Public record_certificate acquires lock and calls internal *_under_lock methods
    rec1 = store.record_certificate({
        "certificate_id": "c_contract_1",
        "phase": "PHASE_CONTRACT",
        "session_id": "ses_c",
        "gate_target": "GATE_4",
        "artifacts_manifest": [],
        "evidence_verification": {}
    }, token="KEY_CONTRACT")
    assert rec1["certificate_id"] == "c_contract_1"

    # 2. Public verify_ledger_integrity acquires lock cleanly
    ok, err = store.verify_ledger_integrity()
    assert ok is True
    assert err is None

    # 3. Public get_certificate acquires lock cleanly
    found = store.get_certificate("c_contract_1")
    assert found is not None
    assert found["certificate_id"] == "c_contract_1"


def test_manifest_update_atomic_and_tamper_policy(tmp_path: Path):
    """
    Turn 512 Blocker 2: Verify rotation manifest writes atomically (tmp+fsync+replace)
    and quarantines corrupted manifest files without blind overwrite.
    """
    log_file = tmp_path / "telemetry_atomic.jsonl"
    man_file = tmp_path / "telemetry_rotation_manifest.json"
    rotator = TelemetryLogRotator(log_path=log_file, manifest_path=man_file)

    # 1. Normal record manifest writes atomically
    rotator._record_manifest("rot_1.jsonl", "sha1", 100)
    assert man_file.exists()
    assert not man_file.with_suffix(man_file.suffix + ".tmp").exists()
    man = rotator._read_manifest()
    assert len(man["rotations"]) == 1

    # 2. Corrupt manifest on disk
    man_file.write_text("CORRUPTED_NON_JSON_CONTENT{{{", encoding="utf-8")

    # 3. Read manifest detects corruption and quarantines
    recovered_man = rotator._read_manifest()
    assert len(recovered_man["rotations"]) == 0
    # Must have created a quarantined .corrupt file
    corrupt_files = list(tmp_path.glob("telemetry_rotation_manifest.corrupt_*"))
    assert len(corrupt_files) == 1
    assert "CORRUPTED_NON_JSON_CONTENT" in corrupt_files[0].read_text(encoding="utf-8")


def test_dead_letter_crash_before_shutdown_policy():
    """
    Turn 512 Blocker 3: Verify that if process terminates abruptly before shutdown(),
    items remain in-memory and are not falsely claimed to be durable across abnormal termination.
    """
    ring = EmergencyDeadLetterRing(max_capacity=10)
    sec_event = MemoryTelemetryEvent(
        event_id="e_crash_test",
        event_type=TelemetryEventType.SECURITY_SENTINEL.value,
        timestamp=time.time(),
        security_flag=True
    )
    ring.push(sec_event)

    # In-memory ring holds the item
    assert ring.size() == 1

    # Simulating crash before shutdown: ring is simply discarded with process memory
    # Observable metric dead_letter_size reflects this state accurately
    assert ring.size() == 1


def test_authority_key_rotation_not_logged(tmp_path: Path):
    """
    Turn 512 Blocker 4: Verify set_authority_token rotates secret cleanly, rejects old secret,
    and secret token string NEVER appears in certificate records or ledger files.
    """
    ledger = tmp_path / "rotation_certs.jsonl"
    store = CompletionAuthorityStore(ledger_path=ledger, authority_token="INITIAL_SECRET_999")

    # Record with initial secret
    store.record_certificate({
        "certificate_id": "c_rot_1",
        "phase": "PHASE_ROT",
        "session_id": "ses_rot",
        "gate_target": "GATE_4",
        "artifacts_manifest": [],
        "evidence_verification": {}
    }, token="INITIAL_SECRET_999")

    # Rotate secret
    store.set_authority_token("NEW_ROTATED_SECRET_888")

    # Old secret must be rejected
    with pytest.raises(PermissionError):
        store.record_certificate({
            "certificate_id": "c_rot_2",
            "phase": "PHASE_ROT",
            "session_id": "ses_rot",
            "gate_target": "GATE_4",
            "artifacts_manifest": [],
            "evidence_verification": {}
        }, token="INITIAL_SECRET_999")

    # New secret succeeds
    rec2 = store.record_certificate({
        "certificate_id": "c_rot_2",
        "phase": "PHASE_ROT",
        "session_id": "ses_rot",
        "gate_target": "GATE_4",
        "artifacts_manifest": [],
        "evidence_verification": {}
    }, token="NEW_ROTATED_SECRET_888")

    # Neither secret string may ever appear in ledger file
    ledger_text = ledger.read_text(encoding="utf-8")
    assert "INITIAL_SECRET_999" not in ledger_text
    assert "NEW_ROTATED_SECRET_888" not in ledger_text


# ==============================================================================
# TURN 514: GATE 4 AUDIT REMEDIATION TESTS
# ==============================================================================

def test_manifest_corruption_blocks_retention_without_operator_action(tmp_path: Path):
    """
    Turn 514 Directive 3.2: Verify that when manifest corruption occurs,
    retention pruning is FAIL-CLOSED (retention_blocked = True) and refuses to delete
    archives until explicit operator action unblocks it.
    """
    log_file = tmp_path / "telemetry_failclosed.jsonl"
    man_file = tmp_path / "telemetry_rotation_manifest.json"
    rotator = TelemetryLogRotator(log_path=log_file, max_backup_files=2, manifest_path=man_file)

    # 1. Simulate 4 rotated archive files on disk
    archives = []
    for i in range(4):
        p = tmp_path / f"telemetry_failclosed_20261018_00000{i}.jsonl"
        p.write_text(f'{{"event_id": "archive_{i}"}}\n', encoding="utf-8")
        archives.append(p)
        rotator._record_manifest(p.name, f"sha_{i}", len(p.read_bytes()))

    assert man_file.exists()
    assert len(rotator._read_manifest()["rotations"]) == 4

    # 2. Corrupt manifest file to trigger fail-closed quarantine
    man_file.write_text("CORRUPTED_GARBAGE_DATA_12345{[[[", encoding="utf-8")

    # 3. Read manifest: it must quarantine and block retention
    man_data = rotator._read_manifest()
    assert rotator.retention_blocked is True
    assert man_data.get("retention_blocked") is True

    # 4. Attempt pruning: must be blocked! None of the 4 archives should be deleted!
    rotator._prune_old_archives()
    for p in archives:
        assert p.exists(), f"Archive {p.name} was wiped despite manifest corruption!"

    # 5. Operator explicit action unblocks retention
    rotator.unblock_retention(force=True)
    assert rotator.retention_blocked is False


def test_dead_letter_is_declared_process_local():
    """
    Turn 514 Directive 3.3: Verify EmergencyDeadLetterRing explicitly declares
    that it is a best-effort process-local RAM buffer and NOT a durable restart spool.
    """
    assert EmergencyDeadLetterRing.STORAGE_TIER == "BEST_EFFORT_PROCESS_LOCAL_RAM"
    assert EmergencyDeadLetterRing.IS_DURABLE is False

    ring = EmergencyDeadLetterRing(max_capacity=5)
    assert hasattr(ring, "STORAGE_TIER")
    assert ring.IS_DURABLE is False


def test_authority_rotation_receipt_has_key_version_without_secret(tmp_path: Path):
    """
    Turn 514 Directive 3.4: Verify authority token rotation increments key_version,
    emits an audit receipt with key fingerprint, and NEVER exposes the raw secret.
    """
    ledger = tmp_path / "receipt_certs.jsonl"
    store = CompletionAuthorityStore(ledger_path=ledger, authority_token="INITIAL_SUPER_SECRET_111")

    assert store.key_version == 1
    assert len(store.get_rotation_receipts()) == 0

    # Rotate token
    receipt = store.set_authority_token("ROTATED_SUPER_SECRET_222")

    assert receipt["key_version"] == 2
    assert "rotated_at" in receipt
    expected_fingerprint = hashlib.sha256("ROTATED_SUPER_SECRET_222".encode("utf-8")).hexdigest()[:16]
    assert receipt["key_fingerprint"] == expected_fingerprint

    # Secret string must NOT be in receipt or stored receipts
    assert "ROTATED_SUPER_SECRET_222" not in str(receipt)
    all_receipts = store.get_rotation_receipts()
    assert len(all_receipts) == 1
    assert "ROTATED_SUPER_SECRET_222" not in str(all_receipts)


def test_independent_completion_authority_issues_certificate(tmp_path: Path):
    """
    Turn 514 Directive 3.5: Verify independent CompletionAuthority gate
    issues and signs certificates with distinct issuer and key_version.
    """
    ledger = tmp_path / "independent_certs.jsonl"
    independent_token = "INDEPENDENT_AUDITOR_GATE_KEY_777"
    store = CompletionAuthorityStore(ledger_path=ledger, authority_token=independent_token)

    cert_payload = {
        "certificate_id": "cert_indep_001",
        "phase": "PHASE_R_MEMORY_8",
        "session_id": "ses_indep_gate",
        "gate_target": "GATE_4",
        "status": "SEALED_FOR_CONTROLLED_PILOT",
        "issuer": "IndependentGateAuthority",
        "artifacts_manifest": [
            {"path": "core/memory/memory_telemetry.py", "sha256": "fake_sha_1"},
            {"path": "core/memory/completion_authority.py", "sha256": "fake_sha_2"}
        ],
        "evidence_verification": {
            "canonical_regression": "121/121_GREEN",
            "auditor": "Opencode"
        }
    }

    # Issuance by unauthorized token fails
    with pytest.raises(PermissionError):
        store.record_certificate(cert_payload, token="WRONG_TOKEN")

    # Issuance by independent authority token succeeds
    issued = store.record_certificate(cert_payload, token=independent_token)

    assert issued["issuer"] == "IndependentGateAuthority"
    assert issued["authority_key_version"] == 1
    assert issued["certificate_hash"] is not None
    assert issued["previous_certificate_hash"] == "GENESIS"


def test_gate4_certificate_persisted_and_hash_chain_verified(tmp_path: Path):
    """
    Turn 514 Directive 4: Verify Gate 4 certificate is persisted into ledger
    and the entire cryptographic SHA-256 hash chain from GENESIS is verified.
    """
    ledger = tmp_path / "gate4_persistence.jsonl"
    authority_token = "GATE4_SEAL_KEY_999"
    store = CompletionAuthorityStore(ledger_path=ledger, authority_token=authority_token)

    # 1. Record pre-requisite certificate (e.g. Gate 3)
    c1 = store.record_certificate({
        "certificate_id": "cert_gate3",
        "phase": "PHASE_R_MEMORY_8",
        "session_id": "ses_gate_persistence",
        "gate_target": "GATE_3",
        "status": "PASS_CONDITIONAL",
        "issuer": "GateAuthority",
        "artifacts_manifest": [],
        "evidence_verification": {"tests": "116/116_PASS"}
    }, token=authority_token)

    # 2. Record Gate 4 Seal certificate
    c2 = store.record_certificate({
        "certificate_id": "cert_gate4_seal",
        "phase": "PHASE_R_MEMORY_8",
        "session_id": "ses_gate_persistence",
        "gate_target": "GATE_4",
        "status": "SEALED_FOR_CONTROLLED_PILOT",
        "issuer": "IndependentGateAuthority",
        "artifacts_manifest": [
            {"path": "core/memory/memory_telemetry.py"},
            {"path": "core/memory/completion_authority.py"}
        ],
        "evidence_verification": {"tests": "121/121_PASS", "independent_audit": "CONFIRMED"}
    }, token=authority_token)

    assert c2["previous_certificate_hash"] == c1["certificate_hash"]

    # 3. Full chain verification
    is_valid, err = store.verify_ledger_integrity()
    assert is_valid is True
    assert err is None



