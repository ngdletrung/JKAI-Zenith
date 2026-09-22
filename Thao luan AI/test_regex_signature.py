import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from wait_for_opencode_reply import get_last_signature, SIGNATURE_REGEX

def test_signature_matching():
    print("[TEST 1] Kiểm tra regex chữ ký chuẩn...")
    valid_sig = "— Ký tên: Opencode (AI Thẩm tra & Phản biện Độc lập) | 2026-09-20 15:10 (GMT+7)"
    m = SIGNATURE_REGEX.match(valid_sig)
    assert m is not None, "Chữ ký chuẩn bị từ chối!"
    assert m.group(1) == "Opencode"
    assert m.group(2) == "2026-09-20 15:10"
    print("  ✅ Chữ ký chuẩn match thành công!")

def test_quote_filtering_in_get_last_sig():
    print("[TEST 2] Kiểm tra hàm get_last_signature loại bỏ trích dẫn blockquote ('>')...")
    lines = [
        "Đoạn văn thảo luận cũ...",
        "> — Ký tên: Opencode (Trích dẫn cũ) | 2026-09-20 14:00 (GMT+7)",
        "Lời bình luận tiếp theo không có chữ ký mới."
    ]
    signer, line, sig_time = get_last_signature(lines, baseline_line_count=1)
    assert signer is None, "Chữ ký trong trích dẫn quote bị nhận nhầm!"
    print("  ✅ Trích dẫn blockquote được bỏ qua hoàn toàn!")

def test_reverse_5_lines_detection():
    print("[TEST 3] Kiểm tra chỉ quét 5 dòng cuối cùng theo thứ tự đảo ngược...")
    lines = [
        "Dòng 1",
        "Dòng 2",
        "— Ký tên: Opencode (Lượt cũ) | 2026-09-20 14:30 (GMT+7)",
        "Nội dung mới của Antigravity:",
        "Dòng phân tích 1",
        "Dòng phân tích 2",
        "Dòng phân tích 3",
        "Dòng phân tích 4",
        "Dòng phân tích 5",
        "Dòng phân tích 6",
        "— Ký tên: Antigravity (Chủ tọa) | 2026-09-20 15:00 (GMT+7)"
    ]
    signer, line, sig_time = get_last_signature(lines, baseline_line_count=2)
    assert signer == "Antigravity", f"Phải nhận diện Antigravity là người ký cuối, thực tế: {signer}"
    print("  ✅ Nhận diện đúng chữ ký cuối cùng của Antigravity!")

def test_opencode_final_signature():
    print("[TEST 4] Kiểm tra OpenCode ký ở cuối văn bản có dòng trống đệm...")
    lines = [
        "Dòng 1",
        "Dòng 2",
        "### Phản biện của OpenCode",
        "Tôi hoàn toàn đồng thuận.",
        "— Ký tên: Opencode (Red Team Audit) | 2026-09-20 15:20 (GMT+7)",
        "",
        ""
    ]
    signer, line, sig_time = get_last_signature(lines, baseline_line_count=2)
    assert signer == "Opencode"
    assert sig_time == "2026-09-20 15:20"
    print("  ✅ Nhận diện chuẩn xác chữ ký OpenCode kể cả khi có dòng trống phía sau!")

def test_bold_asterisks_signature():
    print("[TEST 5] Kiểm tra chữ ký có dấu markdown bold (**) như Phiên 06 Turn 2...")
    lines = [
        "Nội dung phản biện của OpenCode...",
        "> Câu hỏi 1",
        "> Câu hỏi 2",
        "",
        "— Ký tên: **Opencode (AI Thẩm tra & Phản biện Độc lập)** | 2026-09-20 15:30 (GMT+7)"
    ]
    signer, line, sig_time = get_last_signature(lines, baseline_line_count=1)
    assert signer == "Opencode", f"Phải nhận diện được Opencode, thực tế: {signer}"
    assert sig_time == "2026-09-20 15:30"
    print("  ✅ Chữ ký có định dạng markdown bold (**) match chuẩn xác 100%!")

if __name__ == "__main__":
    test_signature_matching()
    test_quote_filtering_in_get_last_sig()
    test_reverse_5_lines_detection()
    test_opencode_final_signature()
    test_bold_asterisks_signature()
    print("\n🎉 TẤT CẢ TEST CASES CỦA REGEX SIGNATURE ĐÃ PASS 100%!")

