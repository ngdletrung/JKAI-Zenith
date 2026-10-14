import os
import sys
import time
import json
import base64
import urllib.request
import urllib.error
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
try:
    from file_lock import file_lock, atomic_write, is_file_busy, has_incomplete_turn_block
    from wait_for_opencode_reply import parse_turn_blocks
except ImportError:
    from contextlib import contextmanager

    @contextmanager
    def file_lock(filepath, timeout=30):
        yield

    def atomic_write(filepath, content):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    def is_file_busy(filepath, max_age_seconds=30.0):
        return False

    def has_incomplete_turn_block(content: str) -> bool:
        return False

    def parse_turn_blocks(content: str):
        return []

CONFIG_PATH = Path.home() / ".config" / "opencode" / "service.json"
STATE_FILE = SCRIPT_DIR / "state.json"
STATE_BAK_FILE = SCRIPT_DIR / "state.json.bak"
DISCUSSION_FILE = SCRIPT_DIR / "Noi dung thao luan.md"
DISPATCH_LOG_FILE = SCRIPT_DIR / "dispatch_history.log"


def log_dispatch_command(session_id: str, current_turn: int, message_text: str):
    try:
        clean_msg = (message_text or "").encode("utf-8", errors="replace").decode("utf-8")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cmd_str = f'python "Thao luan AI/trigger_opencode.py" --session {session_id} --force "{clean_msg}"'
        log_entry = (
            f"[{now_str}] Turn {current_turn} | Session: {session_id}\n"
            f"Command: {cmd_str}\n"
            f"Message: {clean_msg}\n"
            f"{'-'*80}\n"
        )
        with open(DISPATCH_LOG_FILE, "a", encoding="utf-8", newline="\n") as f:
            f.write(log_entry)
        print(f"[LOGGED] Đã lưu câu lệnh điều phối UTF-8 vào '{DISPATCH_LOG_FILE.name}'!")
    except Exception as e:
        print(f"[WARN] Không thể ghi dispatch log: {e}", file=sys.stderr)


def load_state(state_path: Path = STATE_FILE) -> dict:
    bak_path = state_path.with_suffix(state_path.suffix + ".bak")
    if state_path.exists():
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            if bak_path.exists():
                try:
                    with open(bak_path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    pass
    return {}


def recover_state(
    discussion_path: Path = DISCUSSION_FILE,
    state_path: Path = STATE_FILE,
    force_unlock: bool = False,
) -> dict:
    """
    Protocol v2.3 P0-2 Safe State Recovery:
    1. Checks if discussion_path or state_path is busy or has an incomplete Turn Block.
    2. Reads the actual last completed Turn Block from Noi dung thao luan.md.
    3. Refuses to reset a live WAITING_FOR_OPENCODE state unless OpenCode has already written
       its reply block or force_unlock=True is explicitly passed.
    4. Reconciles turn.current_turn, turn.expected_next_turn, turn.last_speaker, and
       clears stale stop_condition_reached / stop_reason / recovery errors cleanly.
    """
    if is_file_busy(str(discussion_path)) or is_file_busy(str(state_path)):
        raise RuntimeError("Tệp thảo luận hoặc state.json đang bận (.tmp/.lock). Không thể recover lúc này.")

    disc_content = discussion_path.read_text(encoding="utf-8") if discussion_path.exists() else ""
    if has_incomplete_turn_block(disc_content):
        raise RuntimeError(
            "Phát hiện Turn Block đang ghi dở trong Noi dung thao luan.md (thiếu TURN_END). "
            "Không reset state để tránh hỏng chuỗi lượt."
        )

    blocks = parse_turn_blocks(disc_content)
    with file_lock(str(state_path)):
        state = load_state(state_path)
        current_status = state.get("status", "")

        if blocks:
            last_block = blocks[-1]
            meta = last_block.get("meta", {})
            actual_turn = int(meta["turn_id"]) if str(meta.get("turn_id", "")).isdigit() else state.get("turn", {}).get("current_turn", 1)
            actual_speaker = meta.get("speaker", "Antigravity").strip()
            actual_session = meta.get("session_id", "").strip()
        else:
            actual_turn = state.get("turn", {}).get("current_turn", 1)
            actual_speaker = state.get("turn", {}).get("last_speaker", "Antigravity")
            actual_session = ""

        if current_status == "WAITING_FOR_OPENCODE" and actual_speaker.lower() != "opencode" and not force_unlock:
            raise RuntimeError(
                "Trạng thái hiện tại đang là WAITING_FOR_OPENCODE và chưa có Turn Block phản hồi từ OpenCode. "
                "Dùng --force nếu bạn chắc chắn tiến trình OpenCode đã dừng để cho phép kích hoạt lại lượt hiện tại."
            )

        state.setdefault("turn", {})
        state["turn"]["current_turn"] = actual_turn
        state["turn"]["expected_next_turn"] = actual_turn + 1
        state["turn"]["last_speaker"] = actual_speaker
        # Only allow re-triggering the current un-replied Antigravity turn (never reset blindly to 0)
        if actual_speaker.lower() == "antigravity":
            state["turn"]["last_triggered_turn"] = max(0, actual_turn - 1)
            state["status"] = "READY_TO_TRIGGER"
        else:
            state["turn"]["last_triggered_turn"] = actual_turn
            state["status"] = "WAITING_FOR_ANTIGRAVITY"

        if actual_session:
            state.setdefault("session", {})
            state["session"]["opencode_session_id"] = actual_session

        state.setdefault("recovery", {})
        state["recovery"]["error_count"] = 0
        state["recovery"]["last_error"] = None
        state["recovery"].pop("timeout_diagnosis", None)

        state.pop("stop_condition_reached", None)
        state.pop("stop_reason", None)
        state["last_updated_at"] = datetime.now().isoformat()

        atomic_write(str(state_path), json.dumps(state, indent=2, ensure_ascii=False))
        return state


def update_state_after_trigger(current_turn: int, opencode_session_id: str):
    with file_lock(str(STATE_FILE)):
        state = load_state()
        if not state:
            return

        if STATE_FILE.exists():
            try:
                STATE_BAK_FILE.write_text(STATE_FILE.read_text(encoding="utf-8"), encoding="utf-8")
            except Exception:
                pass

        if "turn" in state:
            state["turn"]["last_speaker"] = "Antigravity"
            state["turn"]["last_triggered_turn"] = current_turn
        else:
            state["last_signer"] = "Antigravity"
            state["last_triggered_turn"] = current_turn

        old_session = None
        if "session" in state and isinstance(state["session"], dict):
            old_session = state["session"].get("opencode_session_id")
            state["session"]["opencode_session_id"] = opencode_session_id
        else:
            old_session = state.get("opencode_session_id")
            state["opencode_session_id"] = opencode_session_id

        if old_session and old_session != opencode_session_id:
            switch_record = {
                "session_id": old_session,
                "switched_at": datetime.now().isoformat(),
                "turn": current_turn,
            }
            if "history" in state and isinstance(state["history"], dict):
                hist = state["history"].get("opencode_sessions", [])
                hist.append(switch_record)
                state["history"]["opencode_sessions"] = hist
            else:
                hist = state.get("opencode_session_history", [])
                hist.append(switch_record)
                state["opencode_session_history"] = hist
            print(f"[SESSION SWITCH] Đã chuyển từ session cũ '{old_session}' sang session mới '{opencode_session_id}'!")

        if "recovery" in state and isinstance(state["recovery"], dict):
            state["recovery"]["error_count"] = 0
            state["recovery"]["last_error"] = None

        state["status"] = "WAITING_FOR_OPENCODE"
        state["last_updated_at"] = datetime.now().isoformat()

        atomic_write(str(STATE_FILE), json.dumps(state, indent=2, ensure_ascii=False))


def get_opencode_password():
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            return data.get("password")
        except Exception:
            pass
    return None


def find_opencode_port():
    try:
        out = subprocess.check_output("netstat -ano", shell=True).decode(errors="replace")
        for line in out.splitlines():
            if "LISTENING" in line and "127.0.0.1:" in line:
                parts = line.strip().split()
                addr = parts[1]
                port = int(addr.split(":")[-1])
                if port > 1024 and port != 3000:
                    try:
                        req = urllib.request.Request(f"http://127.0.0.1:{port}/doc", headers={"User-Agent": "curl/8.0"})
                        with urllib.request.urlopen(req, timeout=1) as resp:
                            if resp.status in (200, 401):
                                return port
                    except urllib.error.HTTPError as e:
                        if e.code == 401:
                            return port
                    except Exception:
                        continue
    except Exception:
        pass
    return 49374


def get_active_session_id(port, auth_header, explicit_session=None):
    """
    Protocol v2.3: Robust 4-step Session Resolution without dead hardcoded fallback.
    State -> Validate -> Verify Workspace -> Discover
    """
    if explicit_session:
        return explicit_session

    ws_dir = os.path.abspath(str(SCRIPT_DIR.parent)).lower()

    # Step 1: STATE — Read candidate session_id from state.json
    state = load_state()
    candidate_session = None
    if "session" in state and isinstance(state["session"], dict):
        candidate_session = state["session"].get("opencode_session_id")
    if not candidate_session:
        candidate_session = state.get("opencode_session_id")

    # Step 2, 3 & 4: VALIDATE, VERIFY WORKSPACE & AUTO-DETECT NEWER ROOT SESSION
    try:
        url = f"http://127.0.0.1:{port}/api/session"
        req = urllib.request.Request(url, headers={
            "Authorization": f"Basic {auth_header}",
            "User-Agent": "Antigravity/2.3",
        })
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("data", [])
            # Only consider root sessions (exclude subagent child sessions that have parentID)
            root_items = [s for s in items if not s.get("parentID")]
            ws_root_items = [
                s for s in root_items
                if s.get("location", {}).get("directory", "").lower() == ws_dir
            ]
            target_items = ws_root_items if ws_root_items else root_items

            candidate_obj = None
            if candidate_session:
                for s in root_items:
                    if s.get("id") == candidate_session:
                        s_dir = s.get("location", {}).get("directory", "").lower()
                        if s_dir == ws_dir or not s_dir:
                            candidate_obj = s
                        else:
                            print(
                                f"[SESSION VALIDATION] Session {candidate_session} thuộc thư mục khác ({s_dir}), cần discovery lại..."
                            )
                        break

            if target_items:
                # Sort by created time descending first, then updated time descending
                sorted_by_created = sorted(
                    target_items,
                    key=lambda x: (
                        x.get("time", {}).get("created", 0),
                        x.get("time", {}).get("updated", 0),
                    ),
                    reverse=True,
                )
                newest_root = sorted_by_created[0]
                if candidate_obj is not None:
                    cand_created = candidate_obj.get("time", {}).get("created", 0)
                    newest_created = newest_root.get("time", {}).get("created", 0)
                    if newest_root.get("id") != candidate_session and newest_created > cand_created:
                        print(
                            f"[SESSION AUTO-SWITCH] Phát hiện Master đã mở session mới hơn '{newest_root.get('id')}' "
                            f"('{newest_root.get('title')}') thay cho session cũ '{candidate_session}'!"
                        )
                        return newest_root["id"]
                    return candidate_session

                discovered_id = newest_root["id"]
                print(f"[DISCOVERY] Tìm thấy session phù hợp mới nhất: {discovered_id} (workspace: {ws_dir})")
                return discovered_id
    except Exception as e:
        print(f"[WARN] Không thể truy vấn danh sách session qua API: {e}", file=sys.stderr)

    # Fallback only to candidate_session from state.json if present; never fall back to a hardcoded dead ID
    if candidate_session:
        return candidate_session
    return None


def trigger_opencode(message_text: str, explicit_session: str = None, force: bool = False):
    state = load_state()

    current_turn = 1
    if "turn" in state and isinstance(state["turn"], dict):
        current_turn = state["turn"].get("current_turn", 1)
        last_triggered = state["turn"].get("last_triggered_turn", 0)
    else:
        current_turn = state.get("total_turn", 1)
        last_triggered = state.get("last_triggered_turn", 0)

    # 1. Check Stop Condition Precedence
    if state.get("stop_condition_reached") and not force:
        stop_reason = state.get("stop_reason", "STOP_CONDITION")
        print(f"[STOPPED] Vòng lặp đang dừng ở mốc an toàn ({stop_reason}).")
        print("          Luật tối thượng: Stop Condition LUÔN THẮNG Auto-Trigger. Chờ Người Dùng duyệt.")
        return False

    # 2. Client-side Deduplication Guard (Anti Double-Send)
    if last_triggered == current_turn and not force:
        print(f"[DEDUP] Lượt {current_turn} đã được kích hoạt trước đó (last_triggered_turn = {last_triggered}).")
        print("        Bỏ qua gửi trùng lặp (dùng --force nếu thực sự muốn kích hoạt lại).")
        return True

    pwd = get_opencode_password()
    if not pwd:
        print("[ERROR] Không tìm thấy mật khẩu OpenCode tại ~/.config/opencode/service.json", file=sys.stderr)
        sys.exit(1)

    auth_header = base64.b64encode(f"opencode:{pwd}".encode("utf-8")).decode("utf-8")
    port = find_opencode_port()
    opencode_session_id = get_active_session_id(port, auth_header, explicit_session=explicit_session)
    if not opencode_session_id:
        print("[ERROR] SESSION_DISCOVERY_FAILED: Không tìm thấy session hợp lệ trong state.json hoặc qua API.", file=sys.stderr)
        sys.exit(1)

    url = f"http://127.0.0.1:{port}/api/session/{opencode_session_id}/prompt"
    payload = {"text": message_text}
    data = json.dumps(payload).encode("utf-8")

    max_retries = 3
    delays = [2, 6, 18]

    for attempt in range(1, max_retries + 1):
        req = urllib.request.Request(url, data=data, headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_header}",
            "User-Agent": "Antigravity/2.3",
        })
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status in (200, 201, 202):
                    print(f"[SUCCESS] Đã kích hoạt OpenCode thành công! (Session: {opencode_session_id}, Turn: {current_turn}, Port: {port})")
                    update_state_after_trigger(current_turn, opencode_session_id)
                    log_dispatch_command(opencode_session_id, current_turn, message_text)
                    return True
                else:
                    print(f"[WARN] Lần thử {attempt}/{max_retries}: OpenCode API trả về mã {resp.status}", file=sys.stderr)
        except urllib.error.HTTPError as e:
            if e.code == 409:
                print(f"[SUCCESS] OpenCode báo nhận trùng lặp (HTTP 409 Conflict) -> Đã được xử lý! (Turn: {current_turn})")
                update_state_after_trigger(current_turn, opencode_session_id)
                log_dispatch_command(opencode_session_id, current_turn, message_text)
                return True
            print(f"[WARN] Lần thử {attempt}/{max_retries} lỗi HTTP {e.code}: {e.reason}", file=sys.stderr)
        except Exception as e:
            print(f"[WARN] Lần thử {attempt}/{max_retries} thất bại: {e}", file=sys.stderr)

        if attempt < max_retries:
            delay = delays[attempt - 1]
            print(f"[INFO] Tạm nghỉ {delay}s trước khi thử lại...")
            time.sleep(delay)

    print("[ERROR] Không thể gửi tin nhắn sang OpenCode sau 3 lần thử.", file=sys.stderr)
    with file_lock(str(STATE_FILE)):
        state = load_state()
        if "recovery" in state and isinstance(state["recovery"], dict):
            state["recovery"]["error_count"] = state["recovery"].get("error_count", 0) + 1
            state["recovery"]["last_error"] = "OPENCODE_API_UNREACHABLE"
        state["status"] = "ERROR_RECOVERY"
        if STATE_FILE.exists():
            atomic_write(str(STATE_FILE), json.dumps(state, indent=2, ensure_ascii=False))
    sys.exit(1)


def list_opencode_sessions(limit: int = 8) -> dict:
    """List recent root OpenCode sessions and highlight the active workspace session."""
    pwd = get_opencode_password()
    if not pwd:
        raise RuntimeError("Không tìm thấy mật khẩu OpenCode tại ~/.config/opencode/service.json")
    auth_header = base64.b64encode(f"opencode:{pwd}".encode("utf-8")).decode("utf-8")
    port = find_opencode_port()
    ws_dir = os.path.abspath(str(SCRIPT_DIR.parent)).lower()
    state = load_state()
    state_sess = state.get("session", {}).get("opencode_session_id") or state.get("opencode_session_id")
    resolved_sess = get_active_session_id(port, auth_header)

    url = f"http://127.0.0.1:{port}/api/session"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Basic {auth_header}",
        "User-Agent": "Antigravity/2.3",
    })
    with urllib.request.urlopen(req, timeout=3) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        items = data.get("data", [])

    root_items = [s for s in items if not s.get("parentID")]
    sorted_roots = sorted(
        root_items,
        key=lambda x: (x.get("time", {}).get("created", 0), x.get("time", {}).get("updated", 0)),
        reverse=True,
    )[:limit]

    print(f"[OPENCODE DESKTOP] Port: {port} | Workspace: {ws_dir}")
    print(f"  - Session trong state.json : {state_sess}")
    print(f"  - Session sẽ được chọn     : {resolved_sess}")
    print("-" * 88)
    for s in sorted_roots:
        sid = s.get("id")
        title = s.get("title", "")
        s_dir = s.get("location", {}).get("directory", "")
        created = s.get("time", {}).get("created", 0)
        updated = s.get("time", {}).get("updated", 0)
        marker = "👉 [ACTIVE TARGET]" if sid == resolved_sess else "                  "
        print(f"{marker} {sid} | {title} | dir={s_dir} | created={created} | updated={updated}")
    return {
        "port": port,
        "workspace": ws_dir,
        "state_session_id": state_sess,
        "resolved_session_id": resolved_sess,
        "sessions": sorted_roots,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trigger OpenCode with Protocol v2.3 resolution & safe recovery")
    parser.add_argument(
        "message",
        nargs="?",
        default="Kính gửi OpenCode: Antigravity đã cập nhật nội dung tại 'Thao luan AI/Noi dung thao luan.md'. Mời bạn đọc phần cuối file và thực hiện lượt tiếp theo theo quy trình.",
        help="Message to send",
    )
    parser.add_argument("--session", default=None, help="Explicit OpenCode Session ID to target")
    parser.add_argument("--force", action="store_true", help="Force trigger ignoring stop conditions or dedup")
    parser.add_argument(
        "--recover-state",
        action="store_true",
        help="Safely recover state.json by reconciling with the last valid Turn Block in Noi dung thao luan.md",
    )
    parser.add_argument(
        "--list-sessions",
        action="store_true",
        help="List active OpenCode root sessions and show which session will be targeted",
    )
    args = parser.parse_args()

    if args.list_sessions:
        list_opencode_sessions()
        sys.exit(0)

    if args.recover_state:
        recovered = recover_state(force_unlock=args.force)
        print(
            f"[RECOVERED] Đã đồng bộ state.json an toàn (Turn: {recovered['turn']['current_turn']}, "
            f"Speaker: {recovered['turn']['last_speaker']}, Status: {recovered['status']})"
        )
        sys.exit(0)

    trigger_opencode(args.message, explicit_session=args.session, force=args.force)

