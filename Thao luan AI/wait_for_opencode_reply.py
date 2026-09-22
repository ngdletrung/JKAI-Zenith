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
    from file_lock import file_lock, atomic_write, is_file_busy
except ImportError:
    from contextlib import contextmanager
    @contextmanager
    def file_lock(filepath, timeout=30): yield
    def atomic_write(filepath, content):
        with open(filepath, "w", encoding="utf-8") as f: f.write(content)
    def is_file_busy(filepath, max_age_seconds=15.0): return False

DISCUSSION_FILE = SCRIPT_DIR / "Noi dung thao luan.md"
STATE_FILE = SCRIPT_DIR / "state.json"
STATE_BAK_FILE = SCRIPT_DIR / "state.json.bak"

# Standardized Exit Codes v2.0
EXIT_SUCCESS_NORMAL = 0      # Valid reply received, no stop marker -> Proceed to next turn
EXIT_PROTOCOL_STOP = 10     # Valid reply received + PROTOCOL STOP MARKER -> Stop & evaluate mode
EXIT_TIMEOUT = 20           # Hard timeout exceeded (>400s)
EXIT_INVALID_BLOCK = 30     # New content found but invalid signature / corrupted Turn Block
EXIT_FILE_BUSY = 40         # File is locked / .tmp in use for too long (>30s)

SIGNATURE_REGEX = re.compile(
    r"^— Ký tên:\s*\*{0,2}(Antigravity|Opencode)\*{0,2}\s*\([^)]+\)\s*\|\s*(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}(?::\d{2})?)?)\s*\(GMT\+7\)\s*$"
)

TURN_BEGIN_REGEX = re.compile(
    r"<!--\s*TURN_BEGIN\s*\n(.*?)\n\s*-->", re.DOTALL
)

TURN_END_REGEX = re.compile(
    r"<!--\s*TURN_END\s*\n(.*?)\n\s*-->", re.DOTALL
)

# Mốc dừng giao thức (Protocol Stop Markers)
STOP_MARKERS = [
    ("✅ Code audit passed", "CODE_AUDIT_PASSED"),
    ("🎉 NGHIỆM THU", "SESSION_COMPLETED")
]

# Mốc đồng thuận pha / nghị trình
CONSENSUS_MARKERS = [
    ("🤝 [ĐỒNG THUẬN QUY TRÌNH THẢO LUẬN]", "PROTOCOL_ALIGNMENT_CONSENSUS"),
    ("🤝 [ĐỒNG THUẬN KIẾN TRÚC]", "ARCHITECTURE_CONSENSUS")
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

def parse_turn_blocks(content: str):
    """
    Parses structured Turn Blocks from markdown content.
    Returns list of parsed turn dicts.
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
                
        # Find corresponding end block
        content_start = b_match.end()
        content_end = len(content)
        end_meta = {}
        
        if i < len(end_matches):
            e_match = end_matches[i]
            content_end = e_match.start()
            for line in e_match.group(1).splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    end_meta[k.strip()] = v.strip()
                    
        turn_body = content[content_start:content_end].strip()
        blocks.append({
            "meta": meta,
            "end_meta": end_meta,
            "body": turn_body,
            "start_pos": b_match.start(),
            "end_pos": content_end
        })
        
    return blocks

def get_legacy_last_signature(lines: list, baseline_line_count: int):
    """
    Fallback: Scans the last 15 non-empty, non-quote lines in reverse order.
    Returns: (signer_name, full_sig_line, sig_time) or (None, None, None)
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

def wait_for_reply(timeout_sec: int = 400, poll_interval_sec: int = 5):
    print(f"[WAITER v2.0] Bắt đầu lắng nghe phản biện từ OpenCode theo Protocol v2.0...")
    print(f"             Hard Timeout: {timeout_sec}s | Chu kỳ kiểm tra: {poll_interval_sec}s")
    print(f"             Tầng Chờ: NORMAL_WAIT (0-60s) | DEEP_WAIT (60-180s) | EXTENDED_WAIT (180-300s) | FINAL_WAIT (300-400s)")
    print(f"             Tệp theo dõi: {DISCUSSION_FILE.name}")
    print(f"             Exit Codes: 0 (Normal) | 10 (Protocol Stop) | 20 (Timeout) | 30 (Invalid Block) | 40 (File Busy)")
    sys.stdout.flush()

    # Initial file busy check
    busy_wait_start = time.time()
    while is_file_busy(str(DISCUSSION_FILE)):
        if time.time() - busy_wait_start > 30:
            print("[FILE_BUSY] Tệp đang bị khóa hoặc có tệp .tmp quá lâu (>30s).", file=sys.stderr)
            sys.exit(EXIT_FILE_BUSY)
        time.sleep(1)

    initial_content, initial_lines = get_file_content_and_lines(DISCUSSION_FILE)
    baseline_line_count = len(initial_lines)
    baseline_blocks = parse_turn_blocks(initial_content)
    baseline_block_count = len(baseline_blocks)
    
    start_time = time.time()
    last_tier = "NORMAL_WAIT"
    last_heartbeat_minute = 0

    while True:
        elapsed = int(time.time() - start_time)
        
        # Hard Timeout Check (>400s)
        if elapsed >= timeout_sec:
            print(f"\n[TIMEOUT] Đã vượt quá Hard Timeout {timeout_sec}s. OpenCode chưa phản hồi vào tệp.", file=sys.stderr)
            state = load_state()
            if "recovery" in state and isinstance(state["recovery"], dict):
                state["recovery"]["last_error"] = "HARD_TIMEOUT_EXCEEDED"
                state["recovery"]["error_count"] = state["recovery"].get("error_count", 0) + 1
            state["status"] = "ERROR_RECOVERY"
            save_state(state)
            sys.exit(EXIT_TIMEOUT)

        # Heartbeat & Tier Transition
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

        # Check if file is currently being written
        if is_file_busy(str(DISCUSSION_FILE)):
            print("[INFO] Phát hiện tệp đang được ghi (.tmp hoặc .lock). Tạm chờ ghi hoàn tất...")
            time.sleep(2)
            continue

        current_content, current_lines = get_file_content_and_lines(DISCUSSION_FILE)
        current_line_count = len(current_lines)

        # Check for new structured Turn Blocks first (Protocol v2.0)
        current_blocks = parse_turn_blocks(current_content)
        if len(current_blocks) > baseline_block_count:
            latest_block = current_blocks[-1]
            speaker = latest_block["meta"].get("speaker", "").strip()
            turn_id_str = latest_block["meta"].get("turn_id", "")
            parent_turn_id_str = latest_block["meta"].get("parent_turn_id", "")

            if speaker.lower() == "opencode":
                print(f"\n[SUCCESS v2.0] Phát hiện Turn Block hợp lệ từ OpenCode (Turn ID: {turn_id_str}, Parent: {parent_turn_id_str})!")
                sys.stdout.flush()

                new_content = latest_block["body"]
                has_marker, marker_reason, marker_type = detect_stop_and_consensus(new_content)

                state = load_state()
                exec_mode = "INTERACTIVE"
                if "execution" in state and isinstance(state["execution"], dict):
                    exec_mode = state["execution"].get("mode", "INTERACTIVE")

                # Update Turn & Speaker in state
                turn_num = int(turn_id_str) if turn_id_str.isdigit() else (state.get("turn", {}).get("current_turn", 1) + 1)
                if "turn" in state and isinstance(state["turn"], dict):
                    state["turn"]["current_turn"] = turn_num
                    state["turn"]["expected_next_turn"] = turn_num + 1
                    state["turn"]["last_speaker"] = "Opencode"
                state["status"] = "WAITING_FOR_ANTIGRAVITY"

                print("\n" + "="*75)
                print("TOÀN VĂN NỘI DUNG PHẢN BIỆN MỚI CỦA OPENCODE (TURN BLOCK v2.0):")
                print("="*75)
                print(new_content)
                print("="*75)
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

        # Fallback Check: Line count increase + Legacy regex signature
        elif current_line_count > baseline_line_count:
            signer_name, sig_line, sig_time = get_legacy_last_signature(current_lines, baseline_line_count)
            if signer_name == "Opencode":
                print(f"\n[SUCCESS LEGACY] Phát hiện chữ ký regex từ OpenCode ({sig_time})!")
                sys.stdout.flush()

                new_lines = current_lines[baseline_line_count:]
                new_content = "\n".join(new_lines)
                has_marker, marker_reason, marker_type = detect_stop_and_consensus(new_content)

                state = load_state()
                exec_mode = "INTERACTIVE"
                if "execution" in state and isinstance(state["execution"], dict):
                    exec_mode = state["execution"].get("mode", "INTERACTIVE")

                curr_turn = state.get("turn", {}).get("current_turn", 1) if "turn" in state else state.get("total_turn", 1)
                next_turn = curr_turn + 1
                if "turn" in state and isinstance(state["turn"], dict):
                    state["turn"]["current_turn"] = next_turn
                    state["turn"]["expected_next_turn"] = next_turn + 1
                    state["turn"]["last_speaker"] = "Opencode"
                state["status"] = "WAITING_FOR_ANTIGRAVITY"

                print("\n" + "="*75)
                print("TOÀN VĂN NỘI DUNG PHẢN BIỆN CỦA OPENCODE:")
                print("="*75)
                print(new_content)
                print("="*75)
                sys.stdout.flush()

                if has_marker and marker_type == "STOP":
                    print(f"\n[PROTOCOL STOP] Phát hiện mốc dừng: {marker_reason}!")
                    state["stop_condition_reached"] = True
                    state["stop_reason"] = marker_reason
                    state["status"] = "WAITING_FOR_USER_APPROVAL"
                    save_state(state)
                    sys.exit(EXIT_PROTOCOL_STOP)
                elif has_marker and marker_type == "CONSENSUS":
                    print(f"\n[CONSENSUS REACHED] Phát hiện {marker_reason}!")
                    if marker_reason == "PROTOCOL_ALIGNMENT_CONSENSUS":
                        if "phase" in state and isinstance(state["phase"], dict):
                            state["phase"]["current_phase"] = "BUSINESS_BOUNDARIES_ROUND_1"
                    save_state(state)
                    sys.exit(EXIT_SUCCESS_NORMAL)
                else:
                    save_state(state)
                    print(f"[WAITER] Hoàn thành lượt nhận phản biện sau {elapsed}s. Exit code {EXIT_SUCCESS_NORMAL}.")
                    sys.exit(EXIT_SUCCESS_NORMAL)
            elif signer_name == "Antigravity":
                pass
            else:
                if current_line_count - baseline_line_count >= 15:
                    time.sleep(3)
                    _, retry_lines = get_file_content_and_lines(DISCUSSION_FILE)
                    retry_signer, _, _ = get_legacy_last_signature(retry_lines, baseline_line_count)
                    if not retry_signer:
                        print(f"\n[WARN] Phát hiện nội dung mới ({current_line_count - baseline_line_count} dòng) nhưng chưa khớp Turn Block hoặc chữ ký chuẩn!", file=sys.stderr)
                        state = load_state()
                        if "recovery" in state and isinstance(state["recovery"], dict):
                            state["recovery"]["last_error"] = "INVALID_SIGNATURE_OR_BLOCK"
                        state["status"] = "ERROR_RECOVERY"
                        save_state(state)
                        sys.exit(EXIT_INVALID_BLOCK)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tiered Waiter v2.0 for OpenCode reply with Turn Block support")
    parser.add_argument("--timeout", type=int, default=400, help="Hard timeout in seconds (default: 400)")
    parser.add_argument("--interval", type=int, default=5, help="Polling interval in seconds (default: 5)")
    args = parser.parse_args()
    
    wait_for_reply(timeout_sec=args.timeout, poll_interval_sec=args.interval)
