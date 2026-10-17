import os
import sys
import time
import json
import re
import argparse
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
try:
    from file_lock import (
        file_lock,
        atomic_write,
        is_file_busy,
        compute_turn_content_hash,
        has_incomplete_turn_block,
    )
except ImportError:
    import hashlib
    from contextlib import contextmanager

    @contextmanager
    def file_lock(filepath, timeout=30):
        yield

    def atomic_write(filepath, content):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    def is_file_busy(filepath, max_age_seconds=30.0):
        return False

    def compute_turn_content_hash(body: str) -> str:
        return hashlib.sha256((body or "").strip().replace("\r\n", "\n").encode("utf-8")).hexdigest()[:16]

    def has_incomplete_turn_block(content: str) -> bool:
        return False


DISCUSSION_FILE = SCRIPT_DIR / "Noi dung thao luan.md"
STATE_FILE = SCRIPT_DIR / "state.json"
STATE_BAK_FILE = SCRIPT_DIR / "state.json.bak"

# Standardized Exit Codes v2.3
EXIT_SUCCESS_NORMAL = 0      # Valid reply received, no stop marker -> Proceed to next turn
EXIT_PROTOCOL_STOP = 10      # Valid reply received + PROTOCOL STOP MARKER -> Stop & evaluate mode
EXIT_TIMEOUT = 20            # Hard timeout exceeded (>400s)
EXIT_INVALID_BLOCK = 30      # New content found but invalid signature / corrupted Turn Block / TOCTOU
EXIT_FILE_BUSY = 40          # File is locked / .tmp in use for too long (>30s)


SIGNATURE_REGEX = re.compile(
    r"^—\s*K[ýy]\s*t[êe]n:\s*\*{0,2}(Antigravity|Opencode)\*{0,2}\s*\([^)]+\)\s*\|\s*(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}(?::\d{2})?)?)\s*\(GMT\+7\)\s*$",
    re.IGNORECASE,
)

TURN_BEGIN_REGEX = re.compile(
    r"<!--\s*TURN_BEGIN\s*\n(.*?)\n\s*-->", re.DOTALL
)

TURN_END_REGEX = re.compile(
    r"<!--\s*TURN_END\s*\n(.*?)\n\s*-->", re.DOTALL
)

HEX_HASH_REGEX = re.compile(r"^[0-9a-fA-F]{16,64}$")

# Mốc dừng giao thức (Protocol Stop Markers)
STOP_MARKERS = [
    ("✅ Code audit passed", "CODE_AUDIT_PASSED"),
    ("🎉 NGHIỆM THU", "SESSION_COMPLETED"),
]

# Mốc đồng thuận pha / nghị trình
CONSENSUS_MARKERS = [
    ("🤝 [ĐỒNG THUẬN QUY TRÌNH THẢO LUẬN]", "PROTOCOL_ALIGNMENT_CONSENSUS"),
    ("🤝 [ĐỒNG THUẬN KIẾN TRÚC]", "ARCHITECTURE_CONSENSUS"),
]


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            if STATE_BAK_FILE.exists():
                try:
                    with open(STATE_BAK_FILE, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    pass
    return {}


def save_state(state: dict):
    with file_lock(str(STATE_FILE)):
        state["last_updated_at"] = datetime.now().isoformat()
        if STATE_FILE.exists():
            try:
                STATE_BAK_FILE.write_text(STATE_FILE.read_text(encoding="utf-8"), encoding="utf-8")
            except Exception:
                pass
        atomic_write(str(STATE_FILE), json.dumps(state, indent=2, ensure_ascii=False))


def get_file_content_and_lines(filepath: Path):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return content, content.splitlines()
    except Exception as e:
        print(f"[WARN] Lỗi khi đọc tệp {filepath.name}: {e}", file=sys.stderr)
        return "", []


def extract_body_signature(body: str):
    """
    Checks whether a valid signature line exists inside the Turn Block body.
    Returns (signature_valid: bool, signer: str | None, sig_time: str | None).
    """
    lines = [l.strip() for l in (body or "").splitlines() if l.strip() and not l.strip().startswith(">")]
    for line in reversed(lines[-8:]):
        clean_line = line.replace("*", "").strip()
        m = SIGNATURE_REGEX.match(clean_line)
        if m:
            return True, m.group(1), m.group(2)
    return False, None, None


def parse_turn_blocks(content: str):
    """
    Parses structured Turn Blocks from markdown content.
    Returns list of parsed turn dicts with completeness and computed SHA-256 hash.
    """
    blocks = []
    begin_matches = list(TURN_BEGIN_REGEX.finditer(content))
    end_matches = list(TURN_END_REGEX.finditer(content))

    for i, b_match in enumerate(begin_matches):
        raw_meta = b_match.group(1)
        meta = {}
        for line in raw_meta.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()

        content_start = b_match.end()
        content_end = len(content)
        end_meta = {}
        is_complete = False

        if i < len(end_matches) and end_matches[i].start() > content_start:
            e_match = end_matches[i]
            content_end = e_match.start()
            is_complete = True
            for line in e_match.group(1).splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    end_meta[k.strip()] = v.strip()

        turn_body = content[content_start:content_end].strip()
        sig_valid, sig_signer, sig_time = extract_body_signature(turn_body)
        computed_hash = compute_turn_content_hash(turn_body)
        blocks.append({
            "meta": meta,
            "end_meta": end_meta,
            "body": turn_body,
            "is_complete": is_complete,
            "signature_valid": sig_valid,
            "signature_signer": sig_signer,
            "signature_time": sig_time,
            "computed_hash": computed_hash,
            "start_pos": b_match.start(),
            "end_pos": content_end,
        })

    return blocks


def validate_turn_block(
    block: dict,
    expected_next_turn: int = None,
    expected_parent_turn: int = None,
    expected_session_id: str = None,
    live_session_id: str = None,
    expected_speaker: str = "opencode",
    strict_hash: bool = False,
) -> dict:
    """
    Protocol v2.3 P0-1 & P0-4 Four-Condition Anti-Replay & Integrity Validator:
    1. format_valid: Complete TURN_BEGIN..TURN_END block + valid signature inside body + speaker match.
    2. turn_chain_valid: turn_id == expected_next_turn AND parent_turn_id == expected_parent_turn.
    3. session_match: block session_id matches expected_session_id AND no mid-flight TOCTOU session switch.
    4. content_hash_valid: computed SHA-256 matches declared hex hash (or non-empty semantic tag when strict_hash=False).
    """
    meta = block.get("meta", {})
    end_meta = block.get("end_meta", {})
    reasons = []

    speaker = meta.get("speaker", "").strip()
    end_speaker = end_meta.get("speaker", speaker).strip()
    is_complete = bool(block.get("is_complete"))
    sig_valid = bool(block.get("signature_valid"))

    # 1. Format & Signature check
    format_valid = (
        is_complete
        and sig_valid
        and speaker.lower() == expected_speaker.lower()
        and end_speaker.lower() == expected_speaker.lower()
    )
    if not is_complete:
        reasons.append("INCOMPLETE_TURN_END")
    if not sig_valid:
        reasons.append("INVALID_OR_MISSING_SIGNATURE")
    if speaker.lower() != expected_speaker.lower():
        reasons.append(f"SPEAKER_MISMATCH({speaker}!={expected_speaker})")

    # 2. Turn chain check
    turn_id_str = str(meta.get("turn_id", "")).strip()
    parent_id_str = str(meta.get("parent_turn_id", "")).strip()
    end_turn_id_str = str(end_meta.get("turn_id", turn_id_str)).strip()

    turn_chain_valid = True
    if not turn_id_str.isdigit() or end_turn_id_str != turn_id_str:
        turn_chain_valid = False
        reasons.append(f"INVALID_TURN_ID({turn_id_str}/{end_turn_id_str})")
    else:
        turn_num = int(turn_id_str)
        if expected_next_turn is not None and turn_num != int(expected_next_turn):
            turn_chain_valid = False
            reasons.append(f"TURN_ID_MISMATCH(got={turn_num},expected={expected_next_turn})")

    if expected_parent_turn is not None:
        if not parent_id_str.isdigit() or int(parent_id_str) != int(expected_parent_turn):
            turn_chain_valid = False
            reasons.append(f"PARENT_TURN_MISMATCH(got={parent_id_str},expected={expected_parent_turn})")

    # 3. Session match & TOCTOU check
    block_session = meta.get("session_id", "").strip()
    session_match = True
    if expected_session_id and live_session_id and expected_session_id != live_session_id:
        session_match = False
        reasons.append(f"TOCTOU_SESSION_CHANGED_MID_FLIGHT({expected_session_id}->{live_session_id})")
    if expected_session_id:
        if not block_session or block_session != expected_session_id:
            session_match = False
            reasons.append(f"SESSION_ID_MISMATCH(got={block_session},expected={expected_session_id})")

    # 4. Content hash check
    declared_hash = end_meta.get("content_hash", "").strip()
    computed_hash = block.get("computed_hash") or compute_turn_content_hash(block.get("body", ""))
    content_hash_valid = True
    if not declared_hash:
        content_hash_valid = False
        reasons.append("MISSING_CONTENT_HASH")
    elif HEX_HASH_REGEX.match(declared_hash):
        if not computed_hash.lower().startswith(declared_hash[:16].lower()) and not declared_hash.lower().startswith(computed_hash.lower()):
            content_hash_valid = False
            reasons.append(f"SHA256_HASH_MISMATCH(declared={declared_hash[:16]},computed={computed_hash})")
    elif strict_hash:
        content_hash_valid = False
        reasons.append(f"NON_HEX_CONTENT_HASH_IN_STRICT_MODE({declared_hash})")

    valid = format_valid and turn_chain_valid and session_match and content_hash_valid
    return {
        "valid": valid,
        "format_valid": format_valid,
        "turn_chain_valid": turn_chain_valid,
        "session_match": session_match,
        "content_hash_valid": content_hash_valid,
        "computed_hash": computed_hash,
        "declared_hash": declared_hash,
        "reasons": reasons,
    }


def diagnose_timeout_reason(
    baseline_line_count: int,
    current_content: str,
    current_lines: list,
    expected_session_id: str = None,
) -> str:
    """
    P1-5 Post-Timeout Diagnostic Classifier:
    Distinguishes partial write, unformatted output, missing session/API, vs slow thinking.
    """
    if has_incomplete_turn_block(current_content):
        return "PARTIAL_WRITE_INCOMPLETE_BLOCK"
    if len(current_lines) > baseline_line_count:
        return "UNFORMATTED_NEW_CONTENT_WITHOUT_VALID_BLOCK"
    return "OPENCODE_NO_FILE_WRITE_WITHIN_400S"


def get_legacy_last_signature(lines: list, baseline_line_count: int):
    """
    Fallback (Controlled Compatibility Only): Scans the last 15 non-empty, non-quote lines.
    """
    if len(lines) <= baseline_line_count:
        return None, None, None

    non_quote_lines = [
        l.strip() for l in lines[-15:]
        if l.strip() and not l.strip().startswith(">")
    ]

    for line in reversed(non_quote_lines[-5:]):
        clean_line = line.replace("*", "").strip()
        match = SIGNATURE_REGEX.match(clean_line)
        if match:
            signer_name = match.group(1)
            sig_time = match.group(2)
            return signer_name, line, sig_time

    return None, None, None


def detect_stop_and_consensus(tail_text: str):
    for marker, reason in STOP_MARKERS:
        if marker in tail_text:
            return True, reason, "STOP"
    for marker, reason in CONSENSUS_MARKERS:
        if marker in tail_text:
            return True, reason, "CONSENSUS"
    return False, None, None


def determine_wait_tier(elapsed_sec: int):
    if elapsed_sec < 60:
        return "NORMAL_WAIT"
    elif elapsed_sec < 180:
        return "DEEP_WAIT"
    elif elapsed_sec < 300:
        return "EXTENDED_WAIT"
    else:
        return "FINAL_WAIT"


def wait_for_reply(
    timeout_sec: int = 400,
    poll_interval_sec: int = 5,
    allow_legacy_fallback: bool = False,
    strict_hash: bool = False,
):
    print("[WAITER v2.3] Bắt đầu lắng nghe phản biện từ OpenCode theo Protocol v2.3...")
    print(f"             Hard Timeout: {timeout_sec}s | Chu kỳ kiểm tra: {poll_interval_sec}s")
    print("             Tầng Chờ: NORMAL_WAIT (0-60s) | DEEP_WAIT (60-180s) | EXTENDED_WAIT (180-300s) | FINAL_WAIT (300-400s)")
    print(f"             Tệp theo dõi: {DISCUSSION_FILE.name}")
    print("             Exit Codes: 0 (Normal) | 10 (Protocol Stop) | 20 (Timeout) | 30 (Invalid Block) | 40 (File Busy)")
    sys.stdout.flush()

    busy_wait_start = time.time()
    while is_file_busy(str(DISCUSSION_FILE)):
        if time.time() - busy_wait_start > 30:
            print("[FILE_BUSY] Tệp đang bị khóa hoặc có tệp .tmp quá lâu (>30s).", file=sys.stderr)
            sys.exit(EXIT_FILE_BUSY)
        time.sleep(1)

    initial_state = load_state()
    expected_parent_turn = initial_state.get("turn", {}).get("current_turn")
    expected_next_turn = initial_state.get("turn", {}).get("expected_next_turn")
    expected_session_id = initial_state.get("session", {}).get("opencode_session_id")

    initial_content, initial_lines = get_file_content_and_lines(DISCUSSION_FILE)
    baseline_line_count = len(initial_lines)
    baseline_blocks = parse_turn_blocks(initial_content)
    baseline_block_count = len(baseline_blocks)

    start_time = time.time()
    last_tier = "NORMAL_WAIT"
    last_heartbeat_minute = 0
    partial_write_first_seen = None

    while True:
        elapsed = int(time.time() - start_time)

        if elapsed >= timeout_sec:
            current_content, current_lines = get_file_content_and_lines(DISCUSSION_FILE)
            diag = diagnose_timeout_reason(
                baseline_line_count, current_content, current_lines, expected_session_id
            )
            print(
                f"\n[TIMEOUT] Đã vượt quá Hard Timeout {timeout_sec}s ({diag}). OpenCode chưa hoàn tất phản hồi hợp lệ.",
                file=sys.stderr,
            )
            state = load_state()
            if "recovery" in state and isinstance(state["recovery"], dict):
                state["recovery"]["last_error"] = f"HARD_TIMEOUT_EXCEEDED:{diag}"
                state["recovery"]["timeout_diagnosis"] = diag
                state["recovery"]["error_count"] = state["recovery"].get("error_count", 0) + 1
            state["status"] = "ERROR_RECOVERY"
            save_state(state)
            sys.exit(EXIT_TIMEOUT)

        current_tier = determine_wait_tier(elapsed)
        current_minute = elapsed // 60
        if current_tier != last_tier:
            last_tier = current_tier
            if current_tier == "DEEP_WAIT":
                print(f"\n[HEARTBEAT - DEEP_WAIT] ({elapsed}s/{timeout_sec}s) OpenCode đang rà soát mã nguồn & suy luận Red Team chuyên sâu...")
            elif current_tier == "EXTENDED_WAIT":
                print(f"\n[HEARTBEAT - EXTENDED_WAIT] ({elapsed}s/{timeout_sec}s) OpenCode đang soạn thảo phản biện phức tạp & thao tác tệp...")
            elif current_tier == "FINAL_WAIT":
                print(f"\n[HEARTBEAT - FINAL_WAIT] ({elapsed}s/{timeout_sec}s) Giai đoạn nước rút hoàn tất lượt (còn <100s)...")
            sys.stdout.flush()
        elif current_minute > last_heartbeat_minute and elapsed % 60 < poll_interval_sec:
            last_heartbeat_minute = current_minute
            print(f"[PULSE] ({elapsed}s/{timeout_sec}s - {current_tier}) Đang kiên nhẫn lắng nghe tệp thảo luận...")
            sys.stdout.flush()

        time.sleep(poll_interval_sec)

        if is_file_busy(str(DISCUSSION_FILE)):
            print("[INFO] Phát hiện tệp đang được ghi (.tmp hoặc .lock). Tạm chờ ghi hoàn tất...")
            time.sleep(2)
            continue

        current_content, current_lines = get_file_content_and_lines(DISCUSSION_FILE)
        current_line_count = len(current_lines)

        # P0-3: Detect partial/interrupted Turn Block write in Noi dung thao luan.md
        if has_incomplete_turn_block(current_content):
            if partial_write_first_seen is None:
                partial_write_first_seen = time.time()
                print("[PARTIAL_WRITE] Phát hiện TURN_BEGIN chưa đóng TURN_END. Đang chờ tiến trình ghi hoàn tất...")
                continue
            elif time.time() - partial_write_first_seen <= 30:
                continue
            else:
                print(
                    "\n[ERROR] Phát hiện Turn Block ghi dở quá 30s (thiếu TURN_END đóng)!",
                    file=sys.stderr,
                )
                state = load_state()
                if "recovery" in state and isinstance(state["recovery"], dict):
                    state["recovery"]["last_error"] = "INCOMPLETE_TURN_BLOCK_PARTIAL_WRITE"
                    state["recovery"]["error_count"] = state["recovery"].get("error_count", 0) + 1
                state["status"] = "ERROR_RECOVERY"
                save_state(state)
                sys.exit(EXIT_INVALID_BLOCK)
        else:
            partial_write_first_seen = None

        current_blocks = parse_turn_blocks(current_content)
        if len(current_blocks) > baseline_block_count:
            latest_block = current_blocks[-1]
            speaker = latest_block["meta"].get("speaker", "").strip()
            turn_id_str = latest_block["meta"].get("turn_id", "")
            parent_turn_id_str = latest_block["meta"].get("parent_turn_id", "")

            if speaker.lower() == "opencode":
                live_state = load_state()
                live_session_id = live_state.get("session", {}).get("opencode_session_id")
                verdict = validate_turn_block(
                    latest_block,
                    expected_next_turn=expected_next_turn,
                    expected_parent_turn=expected_parent_turn,
                    expected_session_id=expected_session_id,
                    live_session_id=live_session_id,
                    expected_speaker="opencode",
                    strict_hash=strict_hash,
                )
                if not verdict["valid"]:
                    err_detail = ", ".join(verdict["reasons"])
                    print(
                        f"\n[INVALID_BLOCK] Turn Block mới từ OpenCode vi phạm kiểm định v2.3: {err_detail}",
                        file=sys.stderr,
                    )
                    if "recovery" in live_state and isinstance(live_state["recovery"], dict):
                        live_state["recovery"]["last_error"] = f"INVALID_TURN_BLOCK:{err_detail}"
                        live_state["recovery"]["error_count"] = live_state["recovery"].get("error_count", 0) + 1
                    live_state["status"] = "ERROR_RECOVERY"
                    save_state(live_state)
                    sys.exit(EXIT_INVALID_BLOCK)

                print(
                    f"\n[SUCCESS v2.3] Phát hiện Turn Block hợp lệ từ OpenCode "
                    f"(Turn ID: {turn_id_str}, Parent: {parent_turn_id_str}, Hash: {verdict['computed_hash']})!"
                )
                sys.stdout.flush()

                new_content = latest_block["body"]
                has_marker, marker_reason, marker_type = detect_stop_and_consensus(new_content)

                state = live_state
                exec_mode = "INTERACTIVE"
                if "execution" in state and isinstance(state["execution"], dict):
                    exec_mode = state["execution"].get("mode", "INTERACTIVE")

                turn_num = int(turn_id_str) if turn_id_str.isdigit() else (state.get("turn", {}).get("current_turn", 1) + 1)
                if "turn" in state and isinstance(state["turn"], dict):
                    state["turn"]["current_turn"] = turn_num
                    state["turn"]["expected_next_turn"] = turn_num + 1
                    state["turn"]["last_speaker"] = "Opencode"
                state["status"] = "WAITING_FOR_ANTIGRAVITY"

                print("\n" + "=" * 75)
                print("TOÀN VĂN NỘI DUNG PHẢN BIỆN MỚI CỦA OPENCODE (TURN BLOCK v2.3):")
                print("=" * 75)
                print(new_content)
                print("=" * 75)
                sys.stdout.flush()

                if has_marker and marker_type == "STOP":
                    print(f"\n[PROTOCOL STOP] Phát hiện mốc dừng: {marker_reason}!")
                    state["stop_condition_reached"] = True
                    state["stop_reason"] = marker_reason
                    if exec_mode == "AUTONOMOUS" and marker_reason == "SESSION_COMPLETED":
                        state["status"] = "COMPLETED"
                        print("[MODE: AUTONOMOUS] Phiên làm việc đã nghiệm thu toàn diện! Chuyển trạng thái COMPLETED.")
                    else:
                        state["status"] = "WAITING_FOR_USER_APPROVAL"
                        print(f"[MODE: {exec_mode}] Dừng lại chờ Người Dùng duyệt. Exit code {EXIT_PROTOCOL_STOP}.")
                    save_state(state)
                    sys.exit(EXIT_PROTOCOL_STOP)
                elif has_marker and marker_type == "CONSENSUS":
                    print(f"\n[CONSENSUS REACHED] Phát hiện {marker_reason}!")
                    if marker_reason == "PROTOCOL_ALIGNMENT_CONSENSUS":
                        print(">>> Hai AI đã đạt ĐỒNG THUẬN QUY TRÌNH THẢO LUẬN! Sẵn sàng bước vào Vòng 1.")
                        if "phase" in state and isinstance(state["phase"], dict):
                            state["phase"]["current_phase"] = "BUSINESS_BOUNDARIES_ROUND_1"
                            state["phase"]["phase_turn"] = 1
                    elif marker_reason == "ARCHITECTURE_CONSENSUS":
                        if exec_mode == "AUTONOMOUS":
                            print(">>> Chế độ Tự Trị: Tự động chuyển sang thi công code (không dừng trung gian).")
                            if "phase" in state and isinstance(state["phase"], dict):
                                state["phase"]["current_phase"] = "CODING_EXECUTION"
                        else:
                            print(">>> Chế độ Tương Tác: Dừng lại xin ý kiến duyệt OK DO từ Người Dùng.")
                            state["status"] = "WAITING_FOR_USER_APPROVAL"
                            save_state(state)
                            sys.exit(EXIT_PROTOCOL_STOP)
                    save_state(state)
                    sys.exit(EXIT_SUCCESS_NORMAL)
                else:
                    save_state(state)
                    print(f"[WAITER] Hoàn thành lượt nhận phản biện sau {elapsed}s. Exit code {EXIT_SUCCESS_NORMAL}.")
                    sys.exit(EXIT_SUCCESS_NORMAL)

        # Controlled Compatibility Fallback (only if explicitly enabled via --allow-legacy-fallback)
        elif current_line_count > baseline_line_count:
            signer_name, sig_line, sig_time = get_legacy_last_signature(current_lines, baseline_line_count)
            if signer_name == "Opencode" and allow_legacy_fallback:
                print(f"\n[SUCCESS LEGACY COMPAT] Phát hiện chữ ký regex từ OpenCode ({sig_time})!")
                sys.stdout.flush()

                new_lines = current_lines[baseline_line_count:]
                new_content = "\n".join(new_lines)
                state = load_state()
                curr_turn = state.get("turn", {}).get("current_turn", 1)
                next_turn = curr_turn + 1
                if "turn" in state and isinstance(state["turn"], dict):
                    state["turn"]["current_turn"] = next_turn
                    state["turn"]["expected_next_turn"] = next_turn + 1
                    state["turn"]["last_speaker"] = "Opencode"
                state["status"] = "WAITING_FOR_ANTIGRAVITY"
                save_state(state)
                sys.exit(EXIT_SUCCESS_NORMAL)
            elif signer_name == "Antigravity":
                pass
            else:
                if current_line_count - baseline_line_count >= 15 or signer_name == "Opencode":
                    time.sleep(3)
                    retry_content, retry_lines = get_file_content_and_lines(DISCUSSION_FILE)
                    retry_blocks = parse_turn_blocks(retry_content)
                    if len(retry_blocks) <= baseline_block_count:
                        print(
                            f"\n[WARN] Phát hiện nội dung mới ({current_line_count - baseline_line_count} dòng) "
                            "nhưng thiếu Turn Block v2.3 hợp lệ (Fallback bị khóa mặc định)!",
                            file=sys.stderr,
                        )
                        state = load_state()
                        if "recovery" in state and isinstance(state["recovery"], dict):
                            state["recovery"]["last_error"] = "MISSING_STRUCTURED_TURN_BLOCK"
                            state["recovery"]["error_count"] = state["recovery"].get("error_count", 0) + 1
                        state["status"] = "ERROR_RECOVERY"
                        save_state(state)
                        sys.exit(EXIT_INVALID_BLOCK)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tiered Waiter v2.3 for OpenCode reply with strict Turn Block verification")
    parser.add_argument("--timeout", type=int, default=400, help="Hard timeout in seconds (default: 400)")
    parser.add_argument("--interval", type=int, default=5, help="Polling interval in seconds (default: 5)")
    parser.add_argument(
        "--allow-legacy-fallback",
        action="store_true",
        help="Allow legacy regex-only turn without TURN_BEGIN/TURN_END (disabled by default in v2.3)",
    )
    parser.add_argument(
        "--strict-hash",
        action="store_true",
        help="Require content_hash to be an exact SHA-256 hex prefix of the Turn Block body",
    )
    args = parser.parse_args()

    wait_for_reply(
        timeout_sec=args.timeout,
        poll_interval_sec=args.interval,
        allow_legacy_fallback=args.allow_legacy_fallback,
        strict_hash=args.strict_hash,
    )
