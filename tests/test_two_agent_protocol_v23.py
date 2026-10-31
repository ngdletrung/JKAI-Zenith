# -*- coding: utf-8 -*-
"""
[ZENITH FILE DIRECTIVE]
- File: tests/test_two_agent_protocol_v23.py
- Role: Protocol Conformance Test Suite for Two-Agent Cooperative Execution Protocol v2.3.
- Ownership: Master LeeTrung
- Status: Active | Version: SDS v28.4.1
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
PROTOCOL_DIR = ROOT_DIR / "Thao luan AI"
if str(PROTOCOL_DIR) not in sys.path:
    sys.path.insert(0, str(PROTOCOL_DIR))

from file_lock import (
    BUSY_MAX_AGE_SECONDS,
    MAX_DISCUSSION_BYTES,
    MAX_DISCUSSION_LINES,
    append_turn_block_atomic,
    compute_turn_content_hash,
    has_incomplete_turn_block,
    is_file_busy,
    verify_and_archive_discussion,
)
from trigger_opencode import get_active_session_id, recover_state
from wait_for_opencode_reply import (
    diagnose_timeout_reason,
    parse_turn_blocks,
    validate_turn_block,
)


class TestTwoAgentProtocolV23:
    """Verifies P0-1..P0-4 and P1-5..P1-8 of Two-Agent Cooperative Execution Protocol v2.3."""

    def test_validate_turn_block_four_conditions_and_toctou(self):
        body = (
            "### Luot 252: Opencode (Senior Red Team Auditor) — Phan bien\n\n"
            "Noi dung kiem toan thuc chung.\n\n"
            "— Ký tên: Opencode (AI Thẩm tra & Phản biện Độc lập) | 2026-10-11 18:40 (GMT+7)"
        )
        valid_sha = compute_turn_content_hash(body)
        md = (
            "<!-- TURN_BEGIN\n"
            "turn_id: 252\n"
            "parent_turn_id: 251\n"
            "speaker: Opencode\n"
            "phase: ARCHITECTURE_REVIEW\n"
            "session_id: ses_ed7498d55ffe8w9PokqHBhaxI4\n"
            "-->\n\n"
            f"{body}\n\n"
            "<!-- TURN_END\n"
            "turn_id: 252\n"
            "speaker: Opencode\n"
            f"content_hash: {valid_sha}\n"
            "-->\n"
        )
        blocks = parse_turn_blocks(md)
        assert len(blocks) == 1
        blk = blocks[0]

        # 1. All 4 conditions valid
        ok = validate_turn_block(
            blk,
            expected_next_turn=252,
            expected_parent_turn=251,
            expected_session_id="ses_ed7498d55ffe8w9PokqHBhaxI4",
            live_session_id="ses_ed7498d55ffe8w9PokqHBhaxI4",
            expected_speaker="opencode",
            strict_hash=True,
        )
        assert ok["valid"] is True
        assert ok["format_valid"] is True
        assert ok["turn_chain_valid"] is True
        assert ok["session_match"] is True
        assert ok["content_hash_valid"] is True

        # 2. Replay / wrong parent_turn_id rejected
        bad_parent = validate_turn_block(
            blk,
            expected_next_turn=252,
            expected_parent_turn=250,
            expected_session_id="ses_ed7498d55ffe8w9PokqHBhaxI4",
        )
        assert bad_parent["valid"] is False
        assert bad_parent["turn_chain_valid"] is False

        # 3. TOCTOU session switch mid-flight rejected
        bad_toctou = validate_turn_block(
            blk,
            expected_next_turn=252,
            expected_parent_turn=251,
            expected_session_id="ses_ed7498d55ffe8w9PokqHBhaxI4",
            live_session_id="ses_NEW_CHANGED_MID_FLIGHT",
        )
        assert bad_toctou["valid"] is False
        assert bad_toctou["session_match"] is False
        assert any("TOCTOU" in r for r in bad_toctou["reasons"])

        # 4. Tampered body fails SHA-256 verification
        blk_tampered = dict(blk)
        blk_tampered["end_meta"] = dict(blk["end_meta"], content_hash="0000111122223333")
        bad_hash = validate_turn_block(
            blk_tampered,
            expected_next_turn=252,
            expected_parent_turn=251,
            expected_session_id="ses_ed7498d55ffe8w9PokqHBhaxI4",
        )
        assert bad_hash["valid"] is False
        assert bad_hash["content_hash_valid"] is False

    def test_partial_write_detection_and_atomic_turn_append(self, tmp_path: Path):
        assert BUSY_MAX_AGE_SECONDS == 30.0
        disc = tmp_path / "Noi dung thao luan.md"
        disc.write_text("# Header\n", encoding="utf-8")

        incomplete_text = (
            "<!-- TURN_BEGIN\n"
            "turn_id: 1\n"
            "parent_turn_id: 0\n"
            "speaker: Antigravity\n"
            "-->\n"
            "Dang viet do giua chung..."
        )
        assert has_incomplete_turn_block(incomplete_text) is True
        with pytest.raises(ValueError, match="Turn Block không hoàn chỉnh"):
            append_turn_block_atomic(str(disc), incomplete_text)

        body = "### Lượt 1\n\n— Ký tên: Antigravity (Builder) | 2026-10-11 18:40 (GMT+7)"
        h = compute_turn_content_hash(body)
        complete_text = (
            "<!-- TURN_BEGIN\n"
            "turn_id: 1\n"
            "parent_turn_id: 0\n"
            "speaker: Antigravity\n"
            "session_id: ses_test\n"
            "-->\n\n"
            f"{body}\n\n"
            "<!-- TURN_END\n"
            "turn_id: 1\n"
            "speaker: Antigravity\n"
            f"content_hash: {h}\n"
            "-->"
        )
        assert has_incomplete_turn_block(complete_text) is False
        append_turn_block_atomic(str(disc), complete_text)
        saved = disc.read_text(encoding="utf-8")
        assert has_incomplete_turn_block(saved) is False
        assert len(parse_turn_blocks(saved)) == 1

    def test_safe_recover_state_reconciles_from_discussion_and_blocks_live_wait(self, tmp_path: Path):
        disc = tmp_path / "Noi dung thao luan.md"
        state_file = tmp_path / "state.json"

        body = "### Lượt 10\n\n— Ký tên: Antigravity (Builder) | 2026-10-11 18:40 (GMT+7)"
        h = compute_turn_content_hash(body)
        disc.write_text(
            "<!-- TURN_BEGIN\n"
            "turn_id: 10\n"
            "parent_turn_id: 9\n"
            "speaker: Antigravity\n"
            "session_id: ses_live_10\n"
            "-->\n\n"
            f"{body}\n\n"
            "<!-- TURN_END\n"
            "turn_id: 10\n"
            "speaker: Antigravity\n"
            f"content_hash: {h}\n"
            "-->\n",
            encoding="utf-8",
        )
        state_file.write_text(
            json.dumps(
                {
                    "protocol_version": "2.0",
                    "session": {"id": "phien_23", "opencode_session_id": "ses_old"},
                    "turn": {"current_turn": 8, "expected_next_turn": 9, "last_speaker": "Opencode", "last_triggered_turn": 8},
                    "recovery": {"error_count": 3, "last_error": "HARD_TIMEOUT_EXCEEDED"},
                    "stop_condition_reached": True,
                    "stop_reason": "OLD_STOP",
                    "status": "WAITING_FOR_OPENCODE",
                }
            ),
            encoding="utf-8",
        )

        # Without force_unlock, WAITING_FOR_OPENCODE with Antigravity as last speaker blocks blind reset
        with pytest.raises(RuntimeError, match="WAITING_FOR_OPENCODE"):
            recover_state(discussion_path=disc, state_path=state_file, force_unlock=False)

        # With force_unlock=True (or when status is ERROR_RECOVERY), reconciles cleanly without resetting last_triggered_turn to 0
        recovered = recover_state(discussion_path=disc, state_path=state_file, force_unlock=True)
        assert recovered["turn"]["current_turn"] == 10
        assert recovered["turn"]["expected_next_turn"] == 11
        assert recovered["turn"]["last_speaker"] == "Antigravity"
        assert recovered["turn"]["last_triggered_turn"] == 9  # Never 0!
        assert recovered["session"]["opencode_session_id"] == "ses_live_10"
        assert recovered["recovery"]["error_count"] == 0
        assert recovered["recovery"]["last_error"] is None
        assert "stop_condition_reached" not in recovered
        assert "stop_reason" not in recovered
        assert recovered["status"] == "READY_TO_TRIGGER"

    def test_diagnose_timeout_reason_categories(self):
        assert (
            diagnose_timeout_reason(10, "<!-- TURN_BEGIN\nturn_id: 2\n-->\nhalf", ["a"] * 12)
            == "PARTIAL_WRITE_INCOMPLETE_BLOCK"
        )
        assert (
            diagnose_timeout_reason(10, "plain text without blocks", ["a"] * 15)
            == "UNFORMATTED_NEW_CONTENT_WITHOUT_VALID_BLOCK"
        )
        assert (
            diagnose_timeout_reason(10, "unchanged", ["a"] * 10)
            == "OPENCODE_NO_FILE_WRITE_WITHIN_400S"
        )

    def test_verified_archive_manifest_sha256_and_rollback_on_limit_violation(self, tmp_path: Path):
        disc = tmp_path / "Noi dung thao luan.md"
        arch = tmp_path / "archive_Phien_23_Test.md"
        man = tmp_path / "archive_manifest.json"

        old_content = "# Full History\n" + "\n".join(f"Line {i}" for i in range(820))
        disc.write_text(old_content, encoding="utf-8")

        # Violating 800-line limit must raise ValueError and keep original file intact
        too_long_pruned = "\n".join(f"Pruned {i}" for i in range(805))
        with pytest.raises(ValueError, match="vi phạm trần"):
            verify_and_archive_discussion(
                discussion_path=disc,
                archive_path=arch,
                pruned_content=too_long_pruned,
                turn_range="241-248",
                manifest_path=man,
            )
        assert len(disc.read_text(encoding="utf-8").splitlines()) == 821

        # Valid pruned content (<800 lines and <80KB) archives and updates manifest with SHA-256
        valid_pruned = "# Pruned Header\n\nSummary table\n"
        rec = verify_and_archive_discussion(
            discussion_path=disc,
            archive_path=arch,
            pruned_content=valid_pruned,
            turn_range="241-248",
            manifest_path=man,
        )
        assert arch.exists()
        assert rec["sha256"] == hashlib.sha256(old_content.encode("utf-8")).hexdigest()
        assert disc.read_text(encoding="utf-8") == valid_pruned
        man_data = json.loads(man.read_text(encoding="utf-8"))
        assert len(man_data["archives"]) == 1

    def test_inventory_hygiene_deprecated_poll_and_ssot_intact(self):
        # 1. Noi dung thao luan.md obeys BOTH <300 lines AND <40KB
        live_disc = PROTOCOL_DIR / "Noi dung thao luan.md"
        disc_text = live_disc.read_text(encoding="utf-8")
        assert len(disc_text.splitlines()) < MAX_DISCUSSION_LINES
        assert len(disc_text.encode("utf-8")) < MAX_DISCUSSION_BYTES
        assert has_incomplete_turn_block(disc_text) is False

        # 2. poll_reply.py is marked DEPRECATED
        poll_text = (PROTOCOL_DIR / "poll_reply.py").read_text(encoding="utf-8")
        assert "DEPRECATED" in poll_text

        # 3. trigger_opencode.py no longer contains dead fallback session ID
        trig_text = (PROTOCOL_DIR / "trigger_opencode.py").read_text(encoding="utf-8")
        assert "ses_f43206275ffeABN08FeBbr2fgw" not in trig_text

        # 4. Both .keyword.md and .keywork.md are full SSoT files (>300 lines)
        kw1 = (ROOT_DIR / ".keyword.md").read_text(encoding="utf-8")
        kw2 = (ROOT_DIR / ".keywork.md").read_text(encoding="utf-8")
        assert len(kw1.splitlines()) >= 340
        assert len(kw2.splitlines()) >= 340

        # 5. SOP v3.1 (hoac v3.0/v2.4/v2.3) contains mandatory first-contact briefing rule in Section II
        sop_text = (PROTOCOL_DIR / "Quy trinh & Nguyen tac thao luan AI.md").read_text(encoding="utf-8")
        assert "PROTOCOL V3.1" in sop_text or "PROTOCOL V3.0" in sop_text or "PROTOCOL V2.4" in sop_text or "PROTOCOL V2.3" in sop_text
        assert "Mandatory First-Contact Protocol Briefing" in sop_text

    def test_exit_code_constants_and_state_precedence_contract(self):
        from wait_for_opencode_reply import (
            EXIT_FILE_BUSY,
            EXIT_INVALID_BLOCK,
            EXIT_PROTOCOL_STOP,
            EXIT_SUCCESS_NORMAL,
            EXIT_TIMEOUT,
        )
        assert (EXIT_SUCCESS_NORMAL, EXIT_PROTOCOL_STOP, EXIT_TIMEOUT, EXIT_INVALID_BLOCK, EXIT_FILE_BUSY) == (
            0,
            10,
            20,
            30,
            40,
        )

    def test_concurrent_partial_write_on_disk_blocks_atomic_append(self, tmp_path: Path):
        disc = tmp_path / "Noi dung thao luan.md"
        disc.write_text("<!-- TURN_BEGIN\nturn_id: 5\n-->\ndang viet do...", encoding="utf-8")
        body = "### Lượt 6\n\n— Ký tên: Antigravity (Builder) | 2026-10-11 18:45 (GMT+7)"
        h = compute_turn_content_hash(body)
        valid_block = (
            "<!-- TURN_BEGIN\nturn_id: 6\nparent_turn_id: 5\nspeaker: Antigravity\n-->\n\n"
            f"{body}\n\n"
            f"<!-- TURN_END\nturn_id: 6\nspeaker: Antigravity\ncontent_hash: {h}\n-->"
        )
        with pytest.raises(RuntimeError, match="Turn Block ghi dở"):
            append_turn_block_atomic(str(disc), valid_block)

    def test_determine_wait_tier_four_stages(self):
        from wait_for_opencode_reply import determine_wait_tier
        assert determine_wait_tier(10) == "NORMAL_WAIT"
        assert determine_wait_tier(90) == "DEEP_WAIT"
        assert determine_wait_tier(220) == "EXTENDED_WAIT"
        assert determine_wait_tier(350) == "FINAL_WAIT"

    def test_detect_stop_and_consensus_markers(self):
        from wait_for_opencode_reply import detect_stop_and_consensus
        has_m, reason, m_type = detect_stop_and_consensus("🤝 [ĐỒNG THUẬN QUY TRÌNH THẢO LUẬN]")
        assert (has_m, reason, m_type) == (True, "PROTOCOL_ALIGNMENT_CONSENSUS", "CONSENSUS")
        has_arch, r_arch, t_arch = detect_stop_and_consensus("🤝 [ĐỒNG THUẬN KIẾN TRÚC]")
        assert (has_arch, r_arch, t_arch) == (True, "ARCHITECTURE_CONSENSUS", "CONSENSUS")
        has_stop, r_stop, t_stop = detect_stop_and_consensus("🎉 NGHIỆM THU")
        assert (has_stop, r_stop, t_stop) == (True, "SESSION_COMPLETED", "STOP")

