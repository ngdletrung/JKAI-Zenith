import sys
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Tuple, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REQUIRED_KEYS = [
    "attempt_id",
    "task_id",
    "steps",
    "final_answer",
    "self_verification",
    "trace_sha256",
]

VALID_STEP_TYPES = {"PLAN", "TOOL_CALL", "VERIFY"}


def validate_trace_dict(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors = []
    for k in REQUIRED_KEYS:
        if k not in data:
            errors.append(f"Thiếu trường bắt buộc MTS: '{k}'")

    steps = data.get("steps")
    if not isinstance(steps, list):
        errors.append("Trường 'steps' phải là một danh sách (list) các bước thực thi.")
    else:
        for idx, step in enumerate(steps):
            if not isinstance(step, dict):
                errors.append(f"Bước index {idx} không phải là dictionary.")
                continue
            stype = step.get("type")
            if stype not in VALID_STEP_TYPES:
                errors.append(f"Bước {step.get('step', idx)} có type không hợp lệ: '{stype}' (chỉ cho phép {VALID_STEP_TYPES})")

    self_ver = data.get("self_verification")
    if not isinstance(self_ver, dict):
        errors.append("Trường 'self_verification' phải là dictionary {'performed': bool, 'evidence': str}.")
    elif "performed" not in self_ver:
        errors.append("Trường 'self_verification' thiếu thuộc tính 'performed'.")

    # Verify self-seal trace_sha256
    claimed_sha = data.get("trace_sha256", "")
    if claimed_sha:
        body = {k: v for k, v in data.items() if k != "trace_sha256"}
        recomputed = hashlib.sha256(json.dumps(body, indent=2, ensure_ascii=False).encode("utf-8")).hexdigest()
        raw_claimed = claimed_sha.replace("sha256:", "").strip()
        if raw_claimed != recomputed:
            errors.append(f"Sai mã băm tự niêm phong trace_sha256: khai '{raw_claimed}', thực tế tính lại '{recomputed}'")

    return len(errors) == 0, errors


def validate_trace_file(file_path: str) -> bool:
    p = Path(file_path)
    if not p.exists():
        print(f"[ERROR] Tệp trace không tồn tại: {file_path}", file=sys.stderr)
        return False
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[ERROR] Không thể parse JSON tệp trace {file_path}: {e}", file=sys.stderr)
        return False

    valid, errors = validate_trace_dict(data)
    if not valid:
        print(f"[INVALID] Tệp trace {file_path} vi phạm chuẩn Minimum Trace Schema (MTS):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return False

    print(f"[VALID] Tệp trace {file_path} đạt chuẩn Minimum Trace Schema (MTS) 100%.")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Sử dụng: python scripts/validate_trace_schema.py <path_to_trace.json>")
        sys.exit(1)
    ok = validate_trace_file(sys.argv[1])
    sys.exit(0 if ok else 1)
