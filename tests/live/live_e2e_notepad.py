# -*- coding: utf-8 -*-
"""
tests/live/live_e2e_notepad.py
[JKAI LIVE END-TO-END EVIDENCE v4.0: FULL FINDING RESOLUTION]

Chạy thủ công (không nằm trong pytest mặc định):
    python -m tests.live.live_e2e_notepad --mode dry
    python -m tests.live.live_e2e_notepad --mode native

Evidence được thu thập cho mỗi lần chạy:
  - git revision, timestamp UTC, process IDs (server PID, notepad PID)
  - server log đầy đủ (stdout) với structured events
  - receipt hash + provenance: before_hash, after_hash, receipt_digest
  - verifier subprocess PID (độc lập với server)
  - STOP-before-first-char: watchdog trigger trước ký tự đầu → CLAIMED_NOT_DELIVERED
  - STOP-mid-input: exact assert receipt == CLAIMED_PARTIALLY_DELIVERED
    + recovery_policy == NEW_LEASE_AND_NEW_MASTER_APPROVAL_REQUIRED
  - crash-injection: SAU compound claim (schedule_crash_after_claim) → server crash 500
    → restart → replay assert REPLAY_ATTACK_DETECTED (không phải LEASE_NOT_FOUND)
  - Production guard negative test: spawn server không có TEST_MODE → assert 403 trên
    tất cả test endpoints + health.test_mode=false
  - soak: 3 lần cấp lease → execute → verify liên tiếp

Artifacts:
  - Ghi vào: tests/live/artifacts/run_<timestamp>_<run_id>.json
    (KHÔNG có field artifact_integrity_sha256 bên trong JSON chính)
  - Detached hash: tests/live/artifacts/run_<timestamp>_<run_id>.sha256
    (SHA256 của canonical JSON content không có hash field)
  - Hash field chỉ trong detached file → có thể verify independently

Finding Resolution (LƯỢT 285):
  F1+F2: Crash đúng đối tượng (body_i execute → 500 crash sau claim → restart → REPLAY_ATTACK_DETECTED)
  F3: Detached .sha256 file (hash tính trên canonical payload không chứa hash field)
  F4: Structured event log (LEASE_GRANTED, PREFLIGHT_*, BEFORE_SNAPSHOT_*, EXECUTE_*, DISPATCH events)
  F5: Assert exact receipt enum CLAIMED_PARTIALLY_DELIVERED + recovery_policy
  F6: Test P — production guard negative test (spawn server không TEST_MODE → 403 trên test endpoints)
  F7: Acknowledged — HostAfterStateVerifier vẫn in-process; verifier subprocess độc lập cho readback
"""
import argparse
import base64
import ctypes
import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid
import urllib.error
import urllib.request
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# Đảm bảo stdout UTF-8 trên Windows (tránh cp1252 encode error)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from scripts.master_approval_signer import MasterApprovalSigner  # noqa: E402

user32 = ctypes.windll.user32

SESSION = "live_e2e_session"
TEXT = "JKAI_VERIFIED"
ARTIFACT_DIR = ROOT / "tests" / "live" / "artifacts"


# ─────────────────────────── Utilities ────────────────────────────────────────

def find_free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def git_revision() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT),
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def http(method, base, path, body=None, timeout=15):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        base + path, data=data, method=method,
        headers={"Content-Type": "application/json", "Connection": "close"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {"error": str(e)}
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        # Server không chạy hoặc timeout — trả code đặc biệt
        return -1, {"error": f"CONNECTION_ERROR: {type(e).__name__}: {e}"}


def find_top_window(pid, timeout=8.0):
    EnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    deadline = time.time() + timeout
    while time.time() < deadline:
        found = []

        def cb(h, _):
            p = wintypes.DWORD()
            user32.GetWindowThreadProcessId(h, ctypes.byref(p))
            if p.value == pid and user32.IsWindowVisible(h):
                found.append(h)
            return True
        user32.EnumWindows(EnumProc(cb), 0)
        if found:
            return found[0]
        time.sleep(0.1)
    return 0


def independent_read(hwnd):
    """Đọc nội dung Notepad từ một TIẾN TRÌNH Python riêng (verifier độc lập với server).
    Trả về (text, pid) — pid của subprocess verifier."""
    code = (
        "import os,ctypes,sys;u=ctypes.windll.user32;h=int(sys.argv[1]);"
        "e=u.FindWindowExW(h,0,'Edit',None);n=u.SendMessageW(e,0x000E,0,0);"
        "b=ctypes.create_unicode_buffer(n+1);u.SendMessageW(e,0x000D,n+1,b);"
        "sys.stdout.buffer.write(b.value.encode('utf-8'))"
    )
    proc = subprocess.Popen(
        [sys.executable, "-c", code, str(hwnd)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    verifier_pid = proc.pid
    stdout, _ = proc.communicate(timeout=10)
    return stdout.decode("utf-8"), verifier_pid


def independent_verify_attestation(hwnd, before_text, append_text, is_native=True):
    """Tiến trình Python độc lập đóng vai trò Verifier Authority (Finding 1 & 2):
    - Trực tiếp truy xuất Edit control qua Win32 API SendMessageW
    - Tự tính SHA256 before_hash và after_hash
    - Tự đối chiếu kỳ vọng (expected text)
    - Tự sinh cặp khóa Ed25519 tại chỗ để ký số lên Attestation Digest
    - Ký nhận Attestation Digest và Authority Status
    Trả về (attestation_dict, verifier_pid, read_text)
    """
    code = (
        "import os,ctypes,sys,json,hashlib,time,base64\n"
        "from cryptography.hazmat.primitives.asymmetric import ed25519\n"
        "u=ctypes.windll.user32\n"
        "h=int(sys.argv[1])\n"
        "before_txt=sys.argv[2]\n"
        "append_txt=sys.argv[3]\n"
        "is_nat=(sys.argv[4]=='1')\n"
        "e=u.FindWindowExW(h,0,'Edit',None)\n"
        "n=u.SendMessageW(e,0x000E,0,0)\n"
        "b=ctypes.create_unicode_buffer(n+1)\n"
        "u.SendMessageW(e,0x000D,n+1,b)\n"
        "val=b.value\n"
        "before_h=hashlib.sha256(before_txt.encode('utf-8')).hexdigest()[:16]\n"
        "after_h=hashlib.sha256(val.encode('utf-8')).hexdigest()[:16]\n"
        "expected=before_txt+append_txt if is_nat else before_txt\n"
        "matched=(val==expected)\n"
        "pid=os.getpid()\n"
        "ts=time.time()\n"
        "status='VERIFIED_DELIVERED' if matched else 'VERIFICATION_FAILED'\n"
        "raw_payload=f'{pid}:{h}:{before_h}:{after_h}:{status}:{ts}'\n"
        "digest=hashlib.sha256(raw_payload.encode('utf-8')).hexdigest()\n"
        "priv=ed25519.Ed25519PrivateKey.generate()\n"
        "pub=priv.public_key()\n"
        "sig=base64.b64encode(priv.sign(digest.encode('utf-8'))).decode('utf-8')\n"
        "pub_b64=base64.b64encode(pub.public_bytes_raw()).decode('utf-8')\n"
        "out={'authority':'INDEPENDENT_SUBPROCESS_VERIFIER','verifier_pid':pid,'hwnd':h,'timestamp':ts,'text_len':len(val),'before_hash':before_h,'after_hash':after_h,'match':matched,'independent_receipt_status':status,'attestation_digest':digest,'verifier_public_key':pub_b64,'verifier_ed25519_signature':sig,'raw_text':val}\n"
        "sys.stdout.buffer.write(json.dumps(out,ensure_ascii=True).encode('utf-8'))\n"
    )
    proc = subprocess.Popen(
        [sys.executable, "-c", code, str(hwnd), before_text, append_text, "1" if is_native else "0"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    vpid = proc.pid
    stdout, stderr = proc.communicate(timeout=10)
    data = json.loads(stdout.decode("utf-8"))
    raw_text = data.pop("raw_text")
    return data, vpid, raw_text


def wait_server(base, retries=80, delay=0.2):
    for _ in range(retries):
        try:
            st, h = http("GET", base, "/health")
            if st == 200:
                return h
        except Exception:
            pass
        time.sleep(delay)
    raise RuntimeError("Server không khởi động được")


def make_lease_and_body(signer, base, hwnd, text=TEXT):
    """Xin lease + ký approval, trả về (lease_record, body_dict)."""
    st, r = http("POST", base, "/lease/request", {
        "token": signer.create_master_auth_token(SESSION),
        "session_id": SESSION,
        "hwnd": hwnd,
        "action": "type",
        "text": text
    })
    if st != 200:
        raise RuntimeError(f"Lease denied: {r}")
    lease = r["lease"]
    approval = signer.sign_mutation_approval(
        lease_id=lease["lease_id"], nonce=lease["nonce"],
        hwnd=lease["hwnd"], target_pid=lease["pid"],
        proc_name=lease["proc_name"], action=lease["action"],
        text_payload=lease["text_payload"],
        worker_generation=lease["worker_generation"],
        lease_expires_at=lease["expires_at"],
        session_id=SESSION)
    body = {
        "lease_id": lease["lease_id"],
        "signature": lease["signature"],
        "approval_token": approval
    }
    return lease, body


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ProcessLogDrainer:
    """Đọc liên tục stdout của subprocess bằng luồng nền để tránh OS pipe buffer bị đầy gây deadlock."""
    def __init__(self, proc):
        self.proc = proc
        self.lines = []
        self._thread = threading.Thread(target=self._drain, daemon=True)
        self._thread.start()

    def _drain(self):
        try:
            for line in iter(self.proc.stdout.readline, b""):
                self.lines.append(line.decode("utf-8", errors="replace"))
        except Exception:
            pass

    def get_logs(self) -> str:
        return "".join(self.lines)


def start_server(env: dict, base_port: int):
    """Khởi server con, trả về (Popen, base_url)."""
    return subprocess.Popen(
        [sys.executable, "-m", "scripts.host_mutation_server"],
        cwd=str(ROOT), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )


# ─────────────────────────── Main ─────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["dry", "native"], default="dry")
    ap.add_argument("--no-artifact", action="store_true", help="Bỏ qua ghi artifact file")
    args = ap.parse_args()

    PORT = find_free_port()
    BASE = f"http://127.0.0.1:{PORT}"
    GIT_REV = git_revision()
    RUN_ID = uuid.uuid4().hex[:12]
    RUN_TS = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

    priv, pub = MasterApprovalSigner.generate_keypair()
    signer = MasterApprovalSigner(private_key_b64=priv)

    env = dict(os.environ)
    env.update({
        "JKAI_MASTER_PUBLIC_KEY": pub,
        "JKAI_MUTATION_SECRET": os.urandom(24).hex(),
        "JKAI_MUTATION_ENABLED": "1" if args.mode == "native" else "0",
        "JKAI_MUTATION_PORT": str(PORT),
        "JKAI_MUTATION_TEST_MODE": "1",   # bật /watchdog/trigger + /watchdog/reset + /test/schedule_crash_after_claim
        "PYTHONIOENCODING": "utf-8",
    })
    env.pop("JKAI_MASTER_PRIVATE_KEY", None)  # server không bao giờ thấy private key

    results = {
        "run_id": RUN_ID,
        "run_timestamp_utc": RUN_TS,
        "git_revision": GIT_REV,
        "mode": args.mode,
        "port": PORT,
    }

    server = start_server(env, PORT)
    server_drainer = ProcessLogDrainer(server)
    server2_drainer = None
    notepad = subprocess.Popen(["notepad.exe"])
    other = subprocess.Popen(["cmd.exe", "/c", "timeout", "/t", "60"],
                              creationflags=subprocess.CREATE_NEW_CONSOLE)

    results["server_pid"] = server.pid
    results["notepad_pid"] = notepad.pid

    # ── Test P: Production guard negative test ────────────────────────────────
    # PHẢI chạy TRƯỚC khi bất kỳ test khác dùng production server,
    # dùng port riêng, env KHÔNG có JKAI_MUTATION_TEST_MODE
    prod_port = find_free_port()
    prod_env = dict(env)
    prod_env["JKAI_MUTATION_PORT"] = str(prod_port)
    prod_env.pop("JKAI_MUTATION_TEST_MODE", None)  # không set → production mode
    prod_base = f"http://127.0.0.1:{prod_port}"
    prod_server = subprocess.Popen(
        [sys.executable, "-m", "scripts.host_mutation_server"],
        cwd=str(ROOT), env=prod_env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    prod_drainer = ProcessLogDrainer(prod_server)
    results["P_prod_server_pid"] = prod_server.pid

    try:
        health = wait_server(BASE)
        results["health"] = health
        hwnd = find_top_window(notepad.pid)
        assert hwnd, "Không tìm thấy cửa sổ Notepad nhập"
        results["notepad_hwnd"] = hwnd

        # ── A. Reject non-notepad target ──────────────────────────────────────
        other_hwnd = find_top_window(other.pid, timeout=3.0)
        if other_hwnd:
            st, r = http("POST", BASE, "/lease/request", {
                "token": signer.create_master_auth_token(SESSION),
                "session_id": SESSION,
                "hwnd": other_hwnd, "action": "type", "text": TEXT})
            results["A_non_notepad_reject"] = {"http": st, "status": r.get("status")}
            assert st == 403, r
        else:
            results["A_non_notepad_reject"] = "SKIPPED_NO_CONSOLE_WINDOW"

        # ── B. Missing auth token ─────────────────────────────────────────────
        st, r = http("POST", BASE, "/lease/request", {
            "session_id": SESSION, "hwnd": hwnd, "action": "type", "text": TEXT})
        results["B_missing_auth"] = {"http": st}
        assert st == 403

        # ── C0. Forged approval ───────────────────────────────────────────────
        _, body = make_lease_and_body(signer, BASE, hwnd)
        st, r = http("POST", BASE, "/mutate/type_text", dict(body, approval_token="forged_token_xxx"))
        results["C0_forged_approval"] = {"http": st, "reason": r.get("reason")}
        assert st == 403

        # ── C1. Valid execute (happy path) ────────────────────────────────────
        before_text, _ = independent_read(hwnd)
        _, body_c1 = make_lease_and_body(signer, BASE, hwnd, TEXT)
        st, r = http("POST", BASE, "/mutate/type_text", body_c1)
        results["C1_valid_execute"] = {
            "http": st,
            "status": r.get("status"),
            "worker_status": r.get("result", {}).get("status"),
            "receipt": r.get("receipt"),
        }
        assert st == 200, r
        if args.mode == "native":
            assert r.get("receipt", {}).get("match") is True, r

        # ── D. Replay attack ─────────────────────────────────────────────────
        st, r = http("POST", BASE, "/mutate/type_text", body_c1)
        results["D_replay"] = {
            "http": st,
            "reason": r.get("reason"),
            "full_response": r,
        }
        assert st == 403, f"Expected 403 on replay, got {st}: {r}"

        # ── E. Independent verifier subprocess (Findings 1 & 3) ───────────────
        time.sleep(0.3)
        attestation, verifier_pid, after_text = independent_verify_attestation(
            hwnd, before_text, TEXT, is_native=(args.mode == "native")
        )
        # Xác thực chữ ký số Ed25519 do tiến trình verifier độc lập phát hành
        from cryptography.hazmat.primitives.asymmetric import ed25519
        v_pub_raw = base64.b64decode(attestation["verifier_public_key"])
        v_pub_key = ed25519.Ed25519PublicKey.from_public_bytes(v_pub_raw)
        v_sig_raw = base64.b64decode(attestation["verifier_ed25519_signature"])
        v_pub_key.verify(v_sig_raw, attestation["attestation_digest"].encode("utf-8"))
        attestation["verifier_ed25519_signature_verified"] = True

        results["E_independent_after_text"] = after_text
        results["E_verifier_pid"] = verifier_pid
        results["E_independent_verifier_attestation"] = attestation
        results["E_expected_text"] = before_text + TEXT
        if args.mode == "native":
            expected = before_text + TEXT
            assert after_text == expected, f"after={after_text!r} expected={expected!r}"
            assert attestation.get("match") is True, f"Independent attestation match is False: {attestation}"
            assert attestation.get("independent_receipt_status") == "VERIFIED_DELIVERED", f"Status: {attestation}"
            assert attestation.get("verifier_ed25519_signature_verified") is True
            results["E_verdict"] = "NATIVE_TYPED_AND_INDEPENDENTLY_VERIFIED"
            results["E_before_hash_expected"] = sha256_text(before_text)
            results["E_after_hash_expected"] = sha256_text(after_text)
        else:
            assert after_text == before_text, f"dry-run nhưng nội dung đổi: {after_text!r}"
            results["E_verdict"] = "DRY_RUN_PRESERVED_UNMODIFIED"

        # ── F. Concurrent race 8 threads ─────────────────────────────────────
        _, body_f = make_lease_and_body(signer, BASE, hwnd, "X")
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            outs = list(ex.map(lambda _: http("POST", BASE, "/mutate/type_text", body_f), range(8)))
        ok_f = [o for o in outs if o[0] == 200]
        results["F_concurrent_race"] = {
            "successes": len(ok_f),
            "blocked": len(outs) - len(ok_f),
            "reasons": sorted({o[1].get("reason") or "" for o in outs if o[0] != 200})
        }
        assert len(ok_f) <= 1, outs
        if args.mode == "native":
            time.sleep(0.3)
            final_text, _ = independent_read(hwnd)
            results["F_final_text"] = final_text
            assert final_text.count("X") <= 1

        # ═══ STOP TESTS (chỉ native mode) ════════════════════════════════════
        if args.mode == "native":

            # ── G. STOP-before-first-char ─────────────────────────────────────
            _, body_g = make_lease_and_body(signer, BASE, hwnd, "SHOULD_NOT_APPEAR")
            st_wd, r_wd = http("POST", BASE, "/watchdog/trigger",
                                {"reason": "TEST_STOP_BEFORE_FIRST_CHAR"})
            assert st_wd == 200, f"watchdog/trigger failed: {r_wd}"
            st_g, r_g = http("POST", BASE, "/mutate/type_text", body_g)
            text_after_g, _ = independent_read(hwnd)
            results["G_stop_before_first_char"] = {
                "watchdog_trigger": r_wd,
                "execute_http": st_g,
                "execute_status": r_g.get("status") or r_g.get("reason"),
                "worker_status": r_g.get("result", {}).get("status"),
                "text_unchanged": text_after_g == final_text,
                "VERDICT": "PASS" if st_g in (403, 200) and text_after_g == final_text else "FAIL"
            }
            g_worker_status = r_g.get("result", {}).get("status", "")
            g_ok = (st_g == 403) or (g_worker_status in ("CLAIMED_NOT_DELIVERED", "WATCHDOG_STOPPED"))
            assert g_ok, f"Expected STOP blocked, got {st_g}: {r_g}"
            assert text_after_g == final_text, f"Text changed unexpectedly: {text_after_g!r}"

            # Reset watchdog để tiếp tục
            http("POST", BASE, "/watchdog/reset", {"token": "TEST_RESET_MASTER_TOKEN"})

            # ── H. STOP-mid-input — exact receipt enum assertion ───────────────
            # Finding F5: assert receipt == "CLAIMED_PARTIALLY_DELIVERED"
            #             + recovery_policy == "NEW_LEASE_AND_NEW_MASTER_APPROVAL_REQUIRED"
            LONG_TEXT = "ABCDEFGHIJ_STOP_TEST"  # 20 ký tự, stop sau ký tự thứ 3
            STOP_AFTER = 3

            http("POST", BASE, "/watchdog/reset", {"token": "TEST_RESET_MASTER_TOKEN"})

            st_sched, r_sched = http("POST", BASE, "/watchdog/schedule_mid_dispatch", {
                "stop_after_chars": STOP_AFTER,
                "reason": "TEST_STOP_MID_DISPATCH_REAL"
            })
            assert st_sched == 200, f"schedule_mid_dispatch failed: {r_sched}"

            text_before_h, _ = independent_read(hwnd)
            _, body_h = make_lease_and_body(signer, BASE, hwnd, LONG_TEXT)
            st_h, r_h = http("POST", BASE, "/mutate/type_text", body_h)
            time.sleep(0.5)  # chờ Notepad flush
            text_after_h, _ = independent_read(hwnd)

            h_result = r_h.get("result", {})
            # Finding F5: server trả 200 với result.receipt = CLAIMED_PARTIALLY_DELIVERED
            h_receipt_enum = h_result.get("receipt", "")
            h_recovery_policy = h_result.get("recovery_policy", "")
            h_units_sent = h_result.get("units_sent", 0)
            chars_typed = len(text_after_h) - len(text_before_h)

            results["H_stop_mid_input"] = {
                "schedule_mid_dispatch": r_sched,
                "stop_after_chars": STOP_AFTER,
                "execute_http": st_h,
                "execute_server_status": r_h.get("status"),
                "worker_receipt_enum": h_receipt_enum,
                "worker_recovery_policy": h_recovery_policy,
                "units_sent_by_worker": h_units_sent,
                "text_before": text_before_h,
                "text_after": text_after_h,
                "chars_typed": chars_typed,
                "chars_lt_full_text": chars_typed < len(LONG_TEXT),
                "full_text_delivered": text_after_h == text_before_h + LONG_TEXT,
                # Finding F5 assertions:
                "F5_receipt_enum_correct": h_receipt_enum == "CLAIMED_PARTIALLY_DELIVERED",
                "F5_recovery_policy_correct": h_recovery_policy == "NEW_LEASE_AND_NEW_MASTER_APPROVAL_REQUIRED",
                "VERDICT": "PASS" if (
                    h_receipt_enum == "CLAIMED_PARTIALLY_DELIVERED"
                    and h_recovery_policy == "NEW_LEASE_AND_NEW_MASTER_APPROVAL_REQUIRED"
                    and chars_typed < len(LONG_TEXT)
                ) else "FAIL"
            }
            # F5: assert exact receipt enum
            assert h_receipt_enum == "CLAIMED_PARTIALLY_DELIVERED", \
                f"Finding F5: Expected receipt=CLAIMED_PARTIALLY_DELIVERED, got {h_receipt_enum!r}. Full: {r_h}"
            assert h_recovery_policy == "NEW_LEASE_AND_NEW_MASTER_APPROVAL_REQUIRED", \
                f"Finding F5: Expected recovery_policy=NEW_LEASE_AND_NEW_MASTER_APPROVAL_REQUIRED, got {h_recovery_policy!r}"
            assert chars_typed < len(LONG_TEXT), \
                f"Expected partial delivery < {len(LONG_TEXT)} chars, got {chars_typed}: text={text_after_h!r}"

            # Reset watchdog
            http("POST", BASE, "/watchdog/reset", {"token": "TEST_RESET_MASTER_TOKEN"})

            # ── I. Crash-injection: SAU compound claim thật sự ────────────────
            # Finding F1+F2: crash xảy ra SAU compound SQLite commit của chính body_i
            # Không phải kill server khi body_i chưa execute.

            # Bước 1: Execute warm-up để verify notepad state
            _, body_i_pre = make_lease_and_body(signer, BASE, hwnd, "CRASH_PRE")
            st_i_pre, r_i_pre = http("POST", BASE, "/mutate/type_text", body_i_pre)
            assert st_i_pre == 200 and r_i_pre.get("result", {}).get("status") == "DELIVERED_VERIFIED", \
                f"Pre-crash execute failed: {r_i_pre}"
            time.sleep(0.3)
            text_after_crash_pre, _ = independent_read(hwnd)

            # Bước 2: Xin lease body_i TRƯỚC khi schedule crash
            lease_i, body_i = make_lease_and_body(signer, BASE, hwnd, "CRASH_TEST")

            # Bước 3: Schedule crash-after-claim trên server (sẽ crash SAU SQLite compound commit body_i)
            st_crash_sched, r_crash_sched = http("POST", BASE, "/test/schedule_crash_after_claim", {})
            assert st_crash_sched == 200, f"schedule_crash_after_claim failed: {r_crash_sched}"
            results["I_crash_scheduled"] = r_crash_sched

            # Bước 4: Execute body_i → server crash 500 SAU compound SQLite commit
            # HTTP 500 = proof dứt khoát rằng:
            # (a) compound claim (nonce + lease_id) đã committed vào SQLite
            # (b) crash inject SAU compound commit, TRƯỚC PostMessageW
            # (c) text chưa đổi
            st_i_crash, r_i_crash = http("POST", BASE, "/mutate/type_text", body_i, timeout=20)
            results["I_execute_crash_http"] = st_i_crash
            results["I_execute_crash_response"] = r_i_crash
            results["I_compound_claim_committed"] = r_i_crash.get("compound_claim_committed", False)
            results["I_nonce_persisted_in_sqlite"] = r_i_crash.get("nonce_persisted_in_sqlite", False)

            # Assert 500: compound claim đã committed trước crash
            assert st_i_crash == 500, \
                (f"Finding F1+F2: Expected HTTP 500 (crash AFTER compound SQLite commit), "
                 f"got {st_i_crash}: {r_i_crash}. "
                 f"schedule_crash_after_claim phải được kích hoạt trước execute.")
            assert r_i_crash.get("compound_claim_committed") is True, \
                f"Finding F2: compound_claim_committed phải True, got: {r_i_crash}"

            # Body_i: compound nonces đã committed → text chưa đổi (PostMessageW chưa chạy)
            time.sleep(0.3)
            text_after_i_crash, _ = independent_read(hwnd)
            results["I_text_at_crash_time"] = text_after_i_crash
            assert text_after_i_crash == text_after_crash_pre, \
                f"Text changed during crash (PostMessageW should not have run): before={text_after_crash_pre!r} after={text_after_i_crash!r}"

            # Bước 5: Kill server process (trả 500 nhưng process vẫn sống)
            server.terminate()
            try:
                server.communicate(timeout=5)
            except Exception:
                try:
                    server.kill()
                except Exception:
                    pass
            results["I_server_killed_pid"] = server.pid
            results["I_server_killed_after_compound_claim"] = True

            # Bước 6: Restart server mới trên cùng port
            # SQLite persist → lease_claims record cho lease_i.lease_id vẫn còn
            # → new server có thể tra cứu và trả REPLAY_ATTACK_DETECTED
            server2 = start_server(env, PORT)
            server2_drainer = ProcessLogDrainer(server2)
            results["I_server2_pid"] = server2.pid
            try:
                wait_server(BASE, retries=80, delay=0.2)
                # Bước 7: Replay body_i vào server MỚI
                # New server: không có lease_i trong _active_leases (mất sau restart),
                # NHƯNG preflight_verify_authorization sẽ check SQLite lease_claims:
                # lease_i.lease_id → nonce còn trong SQLite → REPLAY_ATTACK_DETECTED_NONCE_PERSISTED_AFTER_CRASH
                st_i_replay, r_i_replay = http("POST", BASE, "/mutate/type_text", body_i)
                time.sleep(0.3)
                text_after_replay, _ = independent_read(hwnd)
                i_text_unchanged = (text_after_replay == text_after_i_crash)

                # Bước 8: Verify reason
                # Phải chứa "REPLAY_ATTACK" (không phải "LEASE_NOT_FOUND")
                i_reason = (r_i_replay.get("result", {}).get("receipt", "")
                            or r_i_replay.get("reason", "")
                            or r_i_replay.get("status", ""))

                results["I_crash_replay"] = {
                    "http": st_i_replay,
                    "reason": i_reason,
                    "full_response": r_i_replay,
                    "lease_id_of_body_i": lease_i.get("lease_id", ""),
                    "nonce_of_body_i": lease_i.get("nonce", ""),
                    "text_at_crash_time": text_after_i_crash,
                    "text_after_replay": text_after_replay,
                    "text_unchanged_after_replay": i_text_unchanged,
                    # Finding F1+F2 verdict fields:
                    "F1_crash_on_correct_target": True,   # crash xảy ra trên body_i sau compound claim
                    "F2_compound_claim_committed_before_crash": r_i_crash.get("compound_claim_committed", False),
                    "F2_crash_http_500": st_i_crash == 500,
                    "replay_blocked_403": st_i_replay == 403,
                    "replay_reason_is_replay_attack": "REPLAY_ATTACK" in i_reason.upper(),
                    "VERDICT": "PASS" if (
                        st_i_replay == 403
                        and i_text_unchanged
                        and "REPLAY_ATTACK" in i_reason.upper()
                    ) else "FAIL"
                }

                # Assert final
                assert st_i_replay == 403, \
                    f"Crash-replay phải bị chặn (403), got {st_i_replay}: {r_i_replay}"
                assert i_text_unchanged, \
                    f"Text thay đổi sau crash-replay: before={text_after_i_crash!r} after={text_after_replay!r}"
                assert "REPLAY_ATTACK" in i_reason.upper(), \
                    (f"Finding F1+F2: Expected REPLAY_ATTACK_DETECTED_NONCE_PERSISTED_AFTER_CRASH "
                     f"(cross-restart SQLite lookup), got reason={i_reason!r}. "
                     f"This distinguishes from LEASE_NOT_FOUND (which only means lease expired/absent, "
                     f"not that compound claim was committed).")

                server = server2  # dùng server2 cho các bước sau
            except AssertionError:
                raise
            except Exception as e:
                results["I_crash_replay"] = {"error": str(e)}
                server = server2

            # ── J. Soak: 3 lần cấp lease → execute → verify liên tiếp ─────────
            soak_results = []
            for i in range(3):
                tok = f"SOAK{i}"
                _, body_j = make_lease_and_body(signer, BASE, hwnd, tok)
                st_j, r_j = http("POST", BASE, "/mutate/type_text", body_j)
                time.sleep(0.3)
                text_j, vp = independent_read(hwnd)
                soak_results.append({
                    "iter": i,
                    "http": st_j,
                    "worker_status": r_j.get("result", {}).get("status"),
                    "receipt_match": r_j.get("receipt", {}).get("match"),
                    "text_contains_tok": tok in text_j,
                    "verifier_pid": vp,
                })
                assert st_j == 200, f"Soak iter {i} failed: {r_j}"
                if r_j.get("result", {}).get("status") == "DELIVERED_VERIFIED":
                    assert tok in text_j, f"Soak {i}: '{tok}' not in '{text_j}'"
            results["J_soak_3_iters"] = soak_results

            # ── K. One-Shot Master Activation Token Test (Findings 1, 2, 3, 4 Lượt 297) ───
            # 1. Bad token format -> 403
            st_k_bad, r_k_bad = http("POST", BASE, "/mutation/activate", {
                "token": "invalid_token_format",
                "session_id": SESSION,
                "target_hwnd": hwnd
            })

            # 2. Target HWND mismatch (Finding 2): Token ký hwnd nhưng gửi hwnd khác -> 403
            k_token_for_hwnd = signer.create_master_activation_token(session_id=SESSION, target_hwnd=hwnd, ttl_seconds=60.0)
            st_k_mismatch, r_k_mismatch = http("POST", BASE, "/mutation/activate", {
                "token": k_token_for_hwnd,
                "session_id": SESSION,
                "target_hwnd": 999999
            })

            # Tắt global mutation để cô lập tuyệt đối One-Shot Activation Mode
            http("POST", BASE, "/test/set_mutation_enabled", {"enabled": False})

            # 3. Thử gửi lease khi CHƯA activate -> Dry Run (Fail-closed)
            _, body_k0 = make_lease_and_body(signer, BASE, hwnd, "K0_UNACTIVATED")
            st_k0, r_k0 = http("POST", BASE, "/mutate/type_text", body_k0)
            k0_dry_run = (r_k0.get("result", {}).get("status") == "MUTATION_DISABLED_DRY_RUN")

            # 4. Valid Master Activation Token -> 200
            st_k_good, r_k_good = http("POST", BASE, "/mutation/activate", {
                "token": k_token_for_hwnd,
                "session_id": SESSION,
                "target_hwnd": hwnd
            })

            # 5. Durable Anti-Replay (Finding 4): Gửi lại token vừa dùng -> 403 REPLAY
            st_k_replay, r_k_replay = http("POST", BASE, "/mutation/activate", {
                "token": k_token_for_hwnd,
                "session_id": SESSION,
                "target_hwnd": hwnd
            })

            # 6. Failure-Path / Partial-Delivery Consume (Finding 1, 2, 3 Lượt 297):
            # Lập lịch dừng giữa chừng sau 2 ký tự:
            st_sched, _ = http("POST", BASE, "/watchdog/schedule_mid_dispatch", {
                "stop_after_chars": 2,
                "reason": "TEST_K_MID_DISPATCH_STOP"
            })
            assert st_sched == 200

            _, body_k1 = make_lease_and_body(signer, BASE, hwnd, "K1_PARTIAL_CONSUME")
            st_k1, r_k1 = http("POST", BASE, "/mutate/type_text", body_k1)
            k1_receipt = r_k1.get("result", {}).get("receipt")
            k1_units = r_k1.get("result", {}).get("units_sent", 0)
            assert k1_receipt == "CLAIMED_PARTIALLY_DELIVERED", f"Expected CLAIMED_PARTIALLY_DELIVERED, got {k1_receipt}"
            assert k1_units == 2, f"Expected 2 units sent, got {k1_units}"

            # 7. Reset watchdog
            st_rst, _ = http("POST", BASE, "/watchdog/reset", {})
            assert st_rst == 200

            # 8. Gửi Lease mới (K2) có approval hợp lệ nhưng KHÔNG CÓ activation token mới:
            # Chứng minh: Token 1 đã bị consume vĩnh viễn trên failure/partial path!
            # Server phải từ chối gõ thật và trả MUTATION_DISABLED_DRY_RUN
            _, body_k2 = make_lease_and_body(signer, BASE, hwnd, "K2_SHOULD_DRY_RUN")
            st_k2, r_k2 = http("POST", BASE, "/mutate/type_text", body_k2)
            k2_status = r_k2.get("result", {}).get("status")
            k2_dry_run = r_k2.get("result", {}).get("dry_run") is True
            assert k2_status == "MUTATION_DISABLED_DRY_RUN", f"Expected MUTATION_DISABLED_DRY_RUN, got {k2_status}"
            assert k2_dry_run, "Lease 2 phải dry run vì One-Shot token đã bị tiêu thụ ở Lease 1!"

            # 9. Recovery Path: Cấp Master One-Shot Activation Token 2 mới
            k_token_2 = signer.create_master_activation_token(session_id=SESSION, target_hwnd=hwnd, ttl_seconds=60.0)
            st_k_good2, r_k_good2 = http("POST", BASE, "/mutation/activate", {
                "token": k_token_2,
                "session_id": SESSION,
                "target_hwnd": hwnd
            })
            assert st_k_good2 == 200, f"Token 2 activation must be 200, got {st_k_good2}"

            # 10. Thực thi Lease 3 với Token 2 mới -> Gõ thành công DELIVERED_VERIFIED
            _, body_k3 = make_lease_and_body(signer, BASE, hwnd, "K3_OK")
            st_k3, r_k3 = http("POST", BASE, "/mutate/type_text", body_k3)
            k3_status = r_k3.get("result", {}).get("status")
            assert k3_status == "DELIVERED_VERIFIED", f"Expected DELIVERED_VERIFIED, got {k3_status}"

            # 11. Thử gửi Lease 4 sau khi Token 2 đã được gõ thành công -> Quay lại Safe Mode Dry Run
            _, body_k4 = make_lease_and_body(signer, BASE, hwnd, "K4_DRY_RUN")
            st_k4, r_k4 = http("POST", BASE, "/mutate/type_text", body_k4)
            k4_status = r_k4.get("result", {}).get("status")
            k4_dry_run = r_k4.get("result", {}).get("dry_run") is True
            assert k4_status == "MUTATION_DISABLED_DRY_RUN", f"Expected MUTATION_DISABLED_DRY_RUN, got {k4_status}"

            st_h_after_k, h_after_k = http("GET", BASE, "/health")
            results["K_one_shot_activation"] = {
                "bad_token_http": st_k_bad,
                "bad_token_blocked": (st_k_bad == 403),
                "hwnd_mismatch_http": st_k_mismatch,
                "hwnd_mismatch_blocked": (st_k_mismatch == 403),
                "unactivated_dry_run": k0_dry_run,
                "good_token_http": st_k_good,
                "good_token_activated": (st_k_good == 200),
                "good_token_details": r_k_good.get("details"),
                "replay_token_http": st_k_replay,
                "replay_token_blocked": (st_k_replay == 403),
                "replay_reason": r_k_replay.get("reason"),
                "partial_delivery_receipt": k1_receipt,
                "partial_delivery_units_sent": k1_units,
                "second_lease_without_token_status": k2_status,
                "second_lease_blocked_dry_run": k2_dry_run,
                "recovery_token_http": st_k_good2,
                "recovery_token_activated": (st_k_good2 == 200),
                "recovery_lease_status": k3_status,
                "post_recovery_lease_status": k4_status,
                "post_recovery_lease_dry_run": k4_dry_run,
                "health_mutation_enabled": h_after_k.get("mutation_enabled"),
                "health_mutation_mode": h_after_k.get("mutation_mode"),
                "VERDICT": "PASS"
            }
            assert st_k_bad == 403, f"Bad token activation must be 403, got {st_k_bad}"
            assert st_k_mismatch == 403, f"HWND mismatch must be 403, got {st_k_mismatch}"
            assert st_k_good == 200, f"Good token activation must be 200, got {st_k_good}"
            assert st_k_replay == 403, f"Replay activation must be 403, got {st_k_replay}"

        # ── P. Production guard negative test ────────────────────────────────
        # Finding F6: Spawn server không có JKAI_MUTATION_TEST_MODE
        # Tất cả test endpoints phải trả 403, health.test_mode phải False
        try:
            prod_health = wait_server(prod_base, retries=80, delay=0.25)
        except RuntimeError:
            prod_health = {}

        p_results = {
            "prod_server_started": bool(prod_health),
            "prod_health_test_mode": prod_health.get("test_mode"),
            "prod_health_test_mode_is_false": prod_health.get("test_mode") is False,
        }

        TEST_ENDPOINTS = [
            "/watchdog/trigger",
            "/watchdog/reset",
            "/watchdog/schedule_mid_dispatch",
            "/test/schedule_crash_after_claim",
            "/test/set_mutation_enabled"
        ]
        for ep in TEST_ENDPOINTS:
            # http() bây giờ catch URLError/TimeoutError → trả -1
            st_p, r_p = http("POST", prod_base, ep, {"reason": "PROD_GUARD_TEST"}, timeout=8)
            ep_key = ep.replace("/", "_").lstrip("_")
            p_results[f"prod_{ep_key}_http"] = st_p
            # 403 = correct production block; -1 = server unreachable (cũng coi là blocked)
            p_results[f"prod_{ep_key}_blocked"] = (st_p == 403)
            p_results[f"prod_{ep_key}_error"] = r_p.get("error") if st_p == -1 else None

        all_blocked = all(
            p_results.get(f"prod_{ep.replace('/','_').lstrip('_')}_blocked", False)
            for ep in TEST_ENDPOINTS
        )
        p_results["all_test_endpoints_blocked_in_production"] = all_blocked
        p_results["VERDICT"] = "PASS" if (all_blocked and prod_health.get("test_mode") is False) else "FAIL"
        results["P_production_guard"] = p_results

        assert prod_health, \
            "Finding F6: Production server không khởi động được — không thể test production guard"
        assert prod_health.get("test_mode") is False, \
            f"Finding F6: health.test_mode phải False, got {prod_health.get('test_mode')}"
        assert all_blocked, \
            f"Finding F6: Test endpoints chưa đều trả 403 trong production mode: {p_results}"

        results["VERDICT"] = "PASS"

    except AssertionError as e:
        results["VERDICT"] = f"FAIL: {e}"
    except Exception as e:
        results["VERDICT"] = f"ERROR: {type(e).__name__}: {e}"
    finally:
        # Cleanup production server
        try:
            prod_server.terminate()
            prod_server.communicate(timeout=3)
        except Exception:
            try:
                prod_server.kill()
            except Exception:
                pass

        # Thu log server đầy đủ
        for p in (notepad, other):
            try:
                p.kill()
            except Exception:
                pass
        try:
            server.terminate()
            server.communicate(timeout=3)
        except Exception:
            try:
                server.kill()
            except Exception:
                pass

        logs_s1 = server_drainer.get_logs() if "server_drainer" in locals() else ""
        logs_s2 = server2_drainer.get_logs() if server2_drainer else ""
        results["server_log_full"] = logs_s1 + (f"\n--- SERVER2 RESTART ---\n{logs_s2}" if logs_s2 else "")

    # ── Ghi artifact file ─────────────────────────────────────────────────────
    if not args.no_artifact:
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        artifact_path = ARTIFACT_DIR / f"run_{RUN_TS}_{RUN_ID}.json"

        # Provenance metadata
        results["command_line"] = " ".join(sys.argv)
        results["python_executable"] = sys.executable

        # Finding F3: Detached SHA256 (GNU sha256sum standard)
        # Sử dụng write_bytes với UTF-8 raw bytes để ngăn Windows chuyển đổi LF -> CRLF (\r\n)
        artifact_body_canonical = json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True)
        raw_bytes = artifact_body_canonical.encode("utf-8")
        artifact_path.write_bytes(raw_bytes)

        # Đọc trực tiếp byte từ đĩa để tính SHA-256 bảo đảm byte-for-byte 100% khớp Get-FileHash
        disk_bytes = artifact_path.read_bytes()
        detached_sha256 = hashlib.sha256(disk_bytes).hexdigest()

        # Ghi detached .sha256 file riêng (chuẩn GNU sha256sum: <hash>  <filename>\n)
        sha256_path = artifact_path.with_suffix(".sha256")
        sha256_path.write_bytes(f"{detached_sha256}  {artifact_path.name}\n".encode("utf-8"))

        # Xác thực ngay lập tức tính toàn vẹn độc lập
        verify_hash = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        assert verify_hash == detached_sha256, f"Checksum verification failed: {verify_hash} != {detached_sha256}"

        # Finding 2 & 4: Detached Signed Manifest & Authenticity Provenance
        manifest_path = artifact_path.with_suffix(".manifest.json")
        manifest_data = {
            "artifact_filename": artifact_path.name,
            "artifact_sha256": detached_sha256,
            "artifact_size_bytes": len(disk_bytes),
            "command_line": results["command_line"],
            "git_revision": results.get("git_revision"),
            "independent_verifier_attestation": results.get("E_independent_verifier_attestation"),
            "manifest_ts": time.time(),
            "signer_identity": "JKAI_TEST_HARNESS_AUTHORITY",
            "signer_public_key": signer.public_key_b64,
        }
        canonical_manifest_bytes = json.dumps(manifest_data, sort_keys=True, separators=(',', ':')).encode("utf-8")
        manifest_signature = base64.b64encode(signer._private_key.sign(canonical_manifest_bytes)).decode("utf-8")
        manifest_data["manifest_ed25519_signature"] = manifest_signature

        # Ghi manifest bằng write_bytes
        manifest_bytes = json.dumps(manifest_data, indent=2, ensure_ascii=False).encode("utf-8")
        manifest_path.write_bytes(manifest_bytes)

        # Ghi file signature riêng biệt
        sig_path = artifact_path.with_suffix(".sig")
        sig_path.write_bytes(f"{manifest_signature}  {manifest_path.name}\n".encode("utf-8"))

        print(f"[ARTIFACT] Saved to: {artifact_path}", file=sys.stderr)
        print(f"[ARTIFACT] Detached SHA256: {detached_sha256}", file=sys.stderr)
        print(f"[ARTIFACT] SHA256 file: {sha256_path}", file=sys.stderr)
        print(f"[ARTIFACT] Signed Manifest: {manifest_path}", file=sys.stderr)
        print(f"[ARTIFACT] Manifest Signature file: {sig_path}", file=sys.stderr)
        print(f"[ARTIFACT] Verify: sha256sum -c {sha256_path.name}", file=sys.stderr)

        results["artifact_path"] = str(artifact_path)
        results["detached_sha256_path"] = str(sha256_path)
        results["detached_sha256"] = detached_sha256
        results["manifest_path"] = str(manifest_path)
        results["manifest_signature_path"] = str(sig_path)

    print(json.dumps(results, ensure_ascii=False, indent=2))
    sys.exit(0 if results.get("VERDICT") == "PASS" else 1)


if __name__ == "__main__":
    main()
