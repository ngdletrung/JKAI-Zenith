# -*- coding: utf-8 -*-
"""
scripts/label_telemetry.py
JKAI Zenith — Master Interactive Question-by-Question Labeling Tool.

Allows Master to grade each decision point individually with nuanced scoring:
  [1] Đúng hoàn toàn (Correct - label: 1.0)
  [2] Chưa chuẩn / Đúng một phần (Partially Correct - label: 0.5)
  [0] Sai hoàn toàn (Completely Wrong - label: 0.0)
  [a] Đúng hết tất cả câu hỏi trong lệnh này (Quick All Correct)
  [s] Bỏ qua câu hỏi này (Skip)
  [q] Lưu & Thoát (Quit)

Usage:
    python scripts/label_telemetry.py
    python scripts/label_telemetry.py --target-session 30
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TELEMETRY_DIR = PROJECT_ROOT / "storage" / "shadow_telemetry"
DEFAULT_OUTPUT_FILE = TELEMETRY_DIR / "labeled_telemetry.jsonl"


def find_latest_telemetry() -> Optional[Path]:
    if not TELEMETRY_DIR.exists():
        return None
    candidates = sorted(TELEMETRY_DIR.glob("shadow_telemetry_*.jsonl"))
    candidates = [c for c in candidates if "archive" not in c.name]
    return candidates[-1] if candidates else None


def load_existing_labeled_ids(labeled_path: Path) -> Set[str]:
    labeled_ids = set()
    if labeled_path.exists():
        with open(labeled_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rec = json.loads(line)
                        if "record_id" in rec:
                            labeled_ids.add(rec["record_id"])
                    except Exception:
                        pass
    return labeled_ids


def positive_int(s: str) -> int:
    v = int(s)
    if v <= 0:
        raise argparse.ArgumentTypeError("Giá trị phải lớn hơn 0")
    return v


def main() -> int:
    parser = argparse.ArgumentParser(description="JKAI Master Nuanced Telemetry Labeling Tool")
    parser.add_argument("--file", type=Path, default=None, help="Đường dẫn file telemetry (mặc định file mới nhất)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT_FILE, help="File lưu kết quả đã chấm")
    parser.add_argument("--target-session", type=positive_int, default=50, help="Số lượng lệnh muốn chấm trong phiên này")
    args = parser.parse_args()

    telemetry_file = args.file or find_latest_telemetry()
    if not telemetry_file or not telemetry_file.exists():
        print(f"❌ Không tìm thấy file telemetry nào trong: {TELEMETRY_DIR}")
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    already_labeled = load_existing_labeled_ids(args.out)

    all_records: List[Dict[str, Any]] = []
    with open(telemetry_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    all_records.append(json.loads(line))
                except Exception:
                    pass

    unlabeled = [r for r in all_records if r.get("record_id") not in already_labeled]

    print("=" * 75)
    print("🎯 JKAI ZENITH — BẢNG CHẤM BÀI TRỰC TIẾP TỪNG CÂU LỆNH CHO MASTER")
    print(f"📁 Nguồn dữ liệu:     {telemetry_file.name}")
    print(f"💾 File kết quả:      {args.out.name}")
    print(f"📊 Đã chấm trước đây: {len(already_labeled)} lệnh | Mục tiêu phiên này: {args.target_session} lệnh")
    print(f"⚡ Còn lại trong kho: {len(unlabeled)} lệnh")
    print("=" * 75)
    print("Thang điểm chấm:")
    print("  [1]: ĐÚNG HOÀN TOÀN (Điểm: 1.0)")
    print("  [2]: CHƯA CHUẨN / ĐÚNG MỘT PHẦN (Điểm: 0.5)")
    print("  [0]: SAI HOÀN TOÀN (Điểm: 0.0)")
    print("  [a]: ĐÚNG HẾT TẤT CẢ câu hỏi của lệnh này (Duyệt nhanh)")
    print("  [s]: BỎ QUA câu hỏi này (Skip)")
    print("  [q]: LƯU TIẾN ĐỘ VÀ THOÁT")
    print("=" * 75)

    session_commands = 0
    total_questions_graded = 0
    grade_distribution = {"correct": 0, "partial": 0, "wrong": 0, "skipped": 0}

    with open(args.out, "a", encoding="utf-8") as out_f:
        for rec in unlabeled:
            if session_commands >= args.target_session:
                print(f"\n🎉 Chúc mừng Master! Đã hoàn thành mục tiêu {args.target_session} lệnh trong phiên này!")
                break

            rid = rec.get("record_id", "N/A")
            raw_state = rec.get("sanitized_state")
            state: Dict[str, Any] = raw_state if isinstance(raw_state, dict) else {"_raw": raw_state}
            draft = rec.get("reflex_draft", {})
            receipt = rec.get("execution_receipt", {})

            query = state.get("query") or state.get("body") or state.get("intent") or json.dumps(state, ensure_ascii=False)
            context = state.get("context", "default")
            action_type = state.get("action_type", "UNKNOWN")

            print(f"\n───────────────────────────────────────────────────────────────────────────")
            print(f"📌 [Lệnh {session_commands + 1}/{args.target_session}] (ID: {rid} | Ngữ cảnh: {context})")
            print(f"📝 Câu lệnh/Đầu vào: \"{query}\"")
            
            rec_status = receipt.get("status", "N/A")
            rec_evidence = receipt.get("evidence", {})
            if rec_evidence:
                print(f"🛡️ Thực tế hệ thống:  status={rec_status} | bằng chứng={json.dumps(rec_evidence, ensure_ascii=False)}")

            questions = list(draft.keys())
            graded_questions: Dict[str, Dict[str, Any]] = {}

            # Nếu có nhiều hơn 1 câu, cho phép duyệt nhanh [a] nếu thấy đúng hết
            skip_record = False
            auto_pass_all = False

            if len(questions) > 1:
                print(f"🤖 Model đưa ra {len(questions)} phán đoán cho lệnh này:")
                for idx, q_name in enumerate(questions, 1):
                    q_val = draft[q_name]
                    print(f"   [{idx}] {q_name:<16}: {q_val.get('result')} (độ tự tin: {q_val.get('confidence', 0.0):.2f})")
                
                quick_choice = input("\n👉 Chấm lệnh này [a=Đúng hết luôn, Enter=Chấm từng câu, s=Bỏ qua, q=Thoát]: ").strip().lower()
                if quick_choice == "q":
                    print(f"\n💾 Đã lưu phiên làm việc. Master đã chấm: {session_commands} lệnh.")
                    _print_summary(session_commands, total_questions_graded, grade_distribution, len(already_labeled) + session_commands, args.out)
                    return 0
                elif quick_choice == "s":
                    print("⏭️ Đã bỏ qua lệnh này.")
                    continue
                elif quick_choice in ("a", "1", "all"):
                    auto_pass_all = True

            # Chấm từng câu hỏi
            for q_idx, q_name in enumerate(questions, 1):
                q_val = draft[q_name]
                model_result = q_val.get("result")
                model_conf = q_val.get("confidence", 0.0)
                model_tier = q_val.get("tier", "N/A")

                if auto_pass_all:
                    graded_questions[q_name] = {
                        "score": 1.0,
                        "verdict": "CORRECT",
                        "model_result": model_result,
                        "model_confidence": model_conf
                    }
                    grade_distribution["correct"] += 1
                    total_questions_graded += 1
                    continue

                print(f"\n   🔹 Câu hỏi [{q_idx}/{len(questions)}]: [{q_name}]")
                print(f"      Model dự đoán:  {model_result} (Độ tự tin: {model_conf:.2f} | {model_tier})")

                while True:
                    prompt = "      👉 Chấm: [1=Đúng, 2=Chưa chuẩn/1 phần, 0=Sai hoàn toàn, s=Skip, q=Thoát]: "
                    c = input(prompt).strip().lower()

                    if c in ("1", "d", "y"):
                        graded_questions[q_name] = {
                            "score": 1.0,
                            "verdict": "CORRECT",
                            "model_result": model_result,
                            "model_confidence": model_conf
                        }
                        grade_distribution["correct"] += 1
                        total_questions_graded += 1
                        print("      ✅ -> Đúng hoàn toàn (1.0)")
                        break
                    elif c in ("2", "p", "part"):
                        note = input("      Lý do chưa chuẩn (Enter để bỏ qua): ").strip()
                        graded_questions[q_name] = {
                            "score": 0.5,
                            "verdict": "PARTIALLY_CORRECT",
                            "notes": note,
                            "model_result": model_result,
                            "model_confidence": model_conf
                        }
                        grade_distribution["partial"] += 1
                        total_questions_graded += 1
                        print("      ⚠️ -> Chưa chuẩn / Đúng 1 phần (0.5)")
                        break
                    elif c in ("0", "s0", "wrong", "n"):
                        note = input("      Lý do sai (Enter để bỏ qua): ").strip()
                        graded_questions[q_name] = {
                            "score": 0.0,
                            "verdict": "COMPLETELY_WRONG",
                            "notes": note,
                            "model_result": model_result,
                            "model_confidence": model_conf
                        }
                        grade_distribution["wrong"] += 1
                        total_questions_graded += 1
                        print("      ❌ -> Sai hoàn toàn (0.0)")
                        break
                    elif c == "s":
                        grade_distribution["skipped"] += 1
                        print("      ⏭️ -> Đã bỏ qua câu hỏi này.")
                        break
                    elif c == "q":
                        print(f"\n💾 Đã lưu phiên làm việc.")
                        _print_summary(session_commands, total_questions_graded, grade_distribution, len(already_labeled) + session_commands, args.out)
                        return 0
                    else:
                        print("      ⚠️ Vui lòng chỉ gõ: 1 (Đúng), 2 (Chưa chuẩn), 0 (Sai), s (Bỏ qua), q (Thoát).")

            # Ghi nhãn cho lệnh này nếu có ít nhất 1 câu được chấm
            if graded_questions:
                all_correct = all(v.get("score") == 1.0 for v in graded_questions.values())
                now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
                label_entry = {
                    "schema_version": "1.2",
                    "record_id": rid,
                    "timestamp_utc": now_utc,
                    "timestamp_unix": time.time(),
                    "state_fingerprint": rec.get("state_fingerprint"),
                    "is_all_correct": all_correct,
                    "graded_questions": graded_questions,
                    "execution_receipt": rec.get("execution_receipt"),
                    "labeled_by": "Master"
                }
                out_f.write(json.dumps(label_entry, ensure_ascii=False) + "\n")
                out_f.flush()
                session_commands += 1
                print(f"💾 Đã lưu kết quả lệnh {session_commands}/{args.target_session}")

    _print_summary(session_commands, total_questions_graded, grade_distribution, len(already_labeled) + session_commands, args.out)
    return 0


def _print_summary(session_commands: int, total_q: int, grades: Dict[str, int], total_cum: int, out_file: Path):
    print("\n" + "=" * 75)
    print("📊 BÁO CÁO TỔNG KẾT PHIÊN CHẤM BÀI CỦA MASTER")
    print("=" * 75)
    print(f"• Số lệnh đã chấm trong phiên này:       {session_commands}")
    print(f"• Tổng số câu hỏi/phán đoán đã chấm:     {total_q}")
    print(f"• Tổng số lệnh đã tích lũy trong kho:    {total_cum}")
    if total_q > 0:
        c_pct = (grades['correct'] / total_q) * 100.0
        p_pct = (grades['partial'] / total_q) * 100.0
        w_pct = (grades['wrong'] / total_q) * 100.0
        print(f"   ✅ Đúng hoàn toàn (1.0):              {grades['correct']} ({c_pct:.1f}%)")
        print(f"   ⚠️ Chưa chuẩn / Đúng 1 phần (0.5):    {grades['partial']} ({p_pct:.1f}%)")
        print(f"   ❌ Sai hoàn toàn (0.0):               {grades['wrong']} ({w_pct:.1f}%)")
        if grades['skipped'] > 0:
            print(f"   ⏭️ Bỏ qua (Skip):                     {grades['skipped']}")
    print(f"\n💾 Dữ liệu lưu an toàn tại: {out_file}")
    print("=" * 75)


if __name__ == "__main__":
    raise SystemExit(main())
