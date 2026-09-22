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
    from file_lock import file_lock, atomic_write
except ImportError:
    from contextlib import contextmanager
    @contextmanager
    def file_lock(filepath, timeout=30): yield
    def atomic_write(filepath, content):
        with open(filepath, "w", encoding="utf-8") as f: f.write(content)

CONFIG_PATH = Path.home() / ".config" / "opencode" / "service.json"
STATE_FILE = SCRIPT_DIR / "state.json"
STATE_BAK_FILE = SCRIPT_DIR / "state.json.bak"
DISPATCH_LOG_FILE = SCRIPT_DIR / "dispatch_history.log"

def log_dispatch_command(session_id: str, current_turn: int, message_text: str):
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cmd_str = f'python "Thao luan AI/trigger_opencode.py" --session {session_id} --force "{message_text}"'
        log_entry = (
            f"[{now_str}] Turn {current_turn} | Session: {session_id}\n"
            f"Command: {cmd_str}\n"
            f"Message: {message_text}\n"
            f"{'-'*80}\n"
        )
        with open(DISPATCH_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
        print(f"[LOGGED] Đã lưu câu lệnh điều phối vào '{DISPATCH_LOG_FILE.name}'!")
    except Exception as e:
        print(f"[WARN] Không thể ghi dispatch log: {e}", file=sys.stderr)

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

def update_state_after_trigger(current_turn: int, opencode_session_id: str):
    with file_lock(str(STATE_FILE)):
        state = load_state()
        if not state:
            return
        
        # Backup before updating
        if STATE_FILE.exists():
            try:
                STATE_BAK_FILE.write_text(STATE_FILE.read_text(encoding="utf-8"), encoding="utf-8")
            except Exception:
                pass
                
        # Schema v2.0 support
        if "turn" in state:
            state["turn"]["last_speaker"] = "Antigravity"
            state["turn"]["last_triggered_turn"] = current_turn
        else:
            state["last_signer"] = "Antigravity"
            state["last_triggered_turn"] = current_turn

        # Session ID Tracking & History
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
                "turn": current_turn
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
        out = subprocess.check_output("netstat -ano", shell=True).decode()
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
    Protocol v2.0: Robust 4-step Session Resolution
    State -> Validate -> Discover -> Persist
    """
    # 1. Explicit override via CLI argument
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

    # Step 2 & 3: VALIDATE & VERIFY WORKSPACE — Check if candidate session exists and matches workspace
    if candidate_session:
        try:
            url = f"http://127.0.0.1:{port}/api/session"
            req = urllib.request.Request(url, headers={
                "Authorization": f"Basic {auth_header}",
                "User-Agent": "Antigravity/2.0"
            })
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                items = data.get("data", [])
                for s in items:
                    if s.get("id") == candidate_session:
                        s_dir = s.get("location", {}).get("directory", "").lower()
                        if s_dir == ws_dir or not s_dir:
                            # Candidate is completely valid! Reuse it.
                            return candidate_session
                        else:
                            print(f"[SESSION VALIDATION] Session {candidate_session} thuộc thư mục khác ({s_dir}), cần discovery lại...")
                            break
        except Exception as e:
            print(f"[WARN] Lỗi khi xác thực session {candidate_session}: {e}", file=sys.stderr)

    # Step 4: DISCOVER & PERSIST FALLBACK — Find newest session belonging to this workspace
    try:
        url = f"http://127.0.0.1:{port}/api/session"
        req = urllib.request.Request(url, headers={
            "Authorization": f"Basic {auth_header}",
            "User-Agent": "Antigravity/2.0"
        })
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("data", [])
            ws_items = [s for s in items if s.get("location", {}).get("directory", "").lower() == ws_dir]
            target_items = ws_items if ws_items else items
            if target_items:
                sorted_items = sorted(target_items, key=lambda x: x.get("time", {}).get("updated", 0), reverse=True)
                discovered_id = sorted_items[0]["id"]
                print(f"[DISCOVERY] Tìm thấy session phù hợp mới nhất: {discovered_id} (workspace: {ws_dir})")
                return discovered_id
    except Exception as e:
        print(f"[WARN] Không thể discovery session qua API: {e}", file=sys.stderr)

    # Ultimate fallback
    if candidate_session:
        return candidate_session
    return "ses_f43206275ffeABN08FeBbr2fgw"

def trigger_opencode(message_text: str, explicit_session: str = None, force: bool = False):
    state = load_state()
    
    # Check current turn from v2.0 or v1 schema
    current_turn = 1
    if "turn" in state and isinstance(state["turn"], dict):
        current_turn = state["turn"].get("current_turn", 1)
        last_triggered = state["turn"].get("last_triggered_turn", 0)
    else:
        current_turn = state.get("total_turn", 1)
        last_triggered = state.get("last_triggered_turn", 0)
        
    session_id_val = "phien_19"
    if "session" in state and isinstance(state["session"], dict):
        session_id_val = state["session"].get("id", "phien_19")
    
    # 1. Check Stop Condition Precedence
    if state.get("stop_condition_reached") and not force:
        stop_reason = state.get("stop_reason", "STOP_CONDITION")
        print(f"[STOPPED] Vòng lặp đang dừng ở mốc an toàn ({stop_reason}).")
        print(f"          Luật tối thượng: Stop Condition LUÔN THẮNG Auto-Trigger. Chờ Người Dùng duyệt.")
        return False

    # 2. Client-side Deduplication Guard (Anti Double-Send)
    if last_triggered == current_turn and not force:
        print(f"[DEDUP] Lượt {current_turn} đã được kích hoạt trước đó (last_triggered_turn = {last_triggered}).")
        print(f"        Bỏ qua gửi trùng lặp (dùng --force nếu thực sự muốn kích hoạt lại).")
        return True

    pwd = get_opencode_password()
    if not pwd:
        print("[ERROR] Không tìm thấy mật khẩu OpenCode tại ~/.config/opencode/service.json", file=sys.stderr)
        sys.exit(1)
        
    auth_header = base64.b64encode(f"opencode:{pwd}".encode("utf-8")).decode("utf-8")
    port = find_opencode_port()
    opencode_session_id = get_active_session_id(port, auth_header, explicit_session=explicit_session)
    
    url = f"http://127.0.0.1:{port}/api/session/{opencode_session_id}/prompt"
    
    # OpenCode prompt payload (Pure text payload for immediate agent loop execution)
    payload = {
        "text": message_text
    }
    data = json.dumps(payload).encode("utf-8")
    
    # Retry with Exponential Backoff (2s, 6s, 18s)
    max_retries = 3
    delays = [2, 6, 18]
    
    for attempt in range(1, max_retries + 1):
        req = urllib.request.Request(url, data=data, headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_header}",
            "User-Agent": "Antigravity/2.0"
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trigger OpenCode with Protocol v2.0 resolution")
    parser.add_argument("message", nargs="?", default="Kính gửi OpenCode: Antigravity đã cập nhật nội dung tại 'Thao luan AI/Noi dung thao luan.md'. Mời bạn đọc phần cuối file và thực hiện lượt tiếp theo theo quy trình.", help="Message to send")
    parser.add_argument("--session", default=None, help="Explicit OpenCode Session ID to target")
    parser.add_argument("--force", action="store_true", help="Force trigger ignoring stop conditions or dedup")
    args = parser.parse_args()
    
    trigger_opencode(args.message, explicit_session=args.session, force=args.force)
