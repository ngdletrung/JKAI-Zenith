#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ [E2E-EVALUATION-FRAMEWORK]: Benchmark toàn diện cho JKAI Zenith.

Chuyển từ đo tốc độ tok/s thuần sang End-to-End Evaluation:
  1. Inference Speed    - tok/s, latency cho từng kích cỡ prompt
  2. Intent Detection   - model chọn đúng skill/tool không? (%)
  3. Planning Quality   - plan có đủ Understand -> Plan -> Execute -> Verify? (%)
  4. JSON Adherence     - khi yêu cầu JSON, model có trả JSON hợp lệ không? (%)

Yêu cầu: Ollama đang chạy (mặc định http://localhost:11434).
"""
import urllib.request
import json
import time
import sys
import os

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("JKAI_BENCH_MODEL", "qwen3.5:4b")
STRESS_BANK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stress_test_bank.json")


class OllamaClient:
    def __init__(self, model: str = DEFAULT_MODEL, url: str = OLLAMA_URL):
        self.model = model
        self.url = url

    def generate(self, prompt: str, num_ctx: int = 8192, temperature: float = 0.1) -> dict:
        data = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "options": {"num_ctx": num_ctx, "temperature": temperature},
            "stream": False
        }).encode()
        t0 = time.time()
        req = urllib.request.Request(
            f"{self.url}/api/generate", data=data, headers={"Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req, timeout=300)
        result = json.loads(resp.read())
        result["wall_sec"] = time.time() - t0
        return result

    def chat(self, messages: list, temperature: float = 0.1) -> str:
        data = json.dumps({
            "model": self.model,
            "messages": messages,
            "options": {"temperature": temperature},
            "stream": False
        }).encode()
        req = urllib.request.Request(
            f"{self.url}/api/chat", data=data, headers={"Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req, timeout=300)
        result = json.loads(resp.read())
        return result.get("message", {}).get("content", "")


def fmt_tok_speed(result: dict) -> str:
    ec = result.get("eval_count", 0)
    ed = result.get("eval_duration", 0) / 1e9
    tok_s = ec / ed if ed > 0 else 0
    return f"{ec} tokens in {ed:.1f}s model = {tok_s:.1f} tok/s | wall={result.get('wall_sec', 0):.1f}s"


# ── Phase 1: Inference Speed ────────────────────────────────────────────────
def bench_inference(client: OllamaClient):
    print("\n═══ [PHASE 1] INFERENCE SPEED ═══")
    prompts = {
        "simple": "Xin chao, ban co khoe khong?",
        "medium": (
            "Hay phan tich yeu cau cua Master: Toi can giup do.\n"
            "Tra ve JSON voi cac truong: skill, mode, confidence, reasoning.\n"
            "Chi tra ve JSON, khong co text khac."
        ),
        "large": (
            "He thong co 182 ky nang. Phan tich yeu cau va chon ky nang phu hop nhat.\n"
            "Yeu cau: Toi can giup do.\n\n"
            "Cac ky nang tieu bieu:\n"
            "- SEARCH_WEB_GLOBAL: Tim kiem thong tin truc tuyen\n"
            "- search_memory: Tra cuu di san tri thuc qua khu\n"
            "- ZENITH_STRATEGIC_PLANNER: Len ke hoach chien luoc\n"
            "- jkai_code_analysis: Phan tich ma nguon\n\n"
            "Hay chon 01 ky nang DUY NHAT va giai thich ly do."
        ),
    }
    for label, prompt in prompts.items():
        r = client.generate(prompt)
        print(f"[{label}] {fmt_tok_speed(r)}")


# ── Phase 2: Intent Detection Accuracy ──────────────────────────────────────
INTENT_PROMPT = (
    "Bạn là bộ định tuyến intent của JKAI. Phân loại câu sau vào 1 trong các nhóm:\n"
    "FAST_PATH (chào hỏi / hỏi thông tin tĩnh), AMBIGUOUS (thiếu ngữ cảnh, cần hỏi lại), "
    "DEEP_PLANNING (cần lập kế hoạch và thực thi).\n"
    "Chỉ trả về JSON duy nhất: {{\"category\": \"FAST_PATH|AMBIGUOUS|DEEP_PLANNING\", \"confidence\": 0.0-1.0}}\n"
    "Câu hỏi: {question}"
)


def bench_intent_detection(client: OllamaClient, bank: list, sample: int = 20):
    print("\n═══ [PHASE 2] INTENT DETECTION ACCURACY ═══")
    correct = 0
    total = 0
    by_cat = {}
    for item in bank[:sample]:
        category = item["category"]
        question = item["question"]
        total += 1
        try:
            resp = client.generate(INTENT_PROMPT.format(question=question), temperature=0.0)
            text = resp.get("response", "")
            predicted = None
            for c in ("FAST_PATH", "AMBIGUOUS", "DEEP_PLANNING"):
                if c in text.upper():
                    predicted = c
                    break
            ok = predicted == category
            if ok:
                correct += 1
            by_cat.setdefault(category, [0, 0])[0] += 1
            by_cat[category][1] += 1 if ok else 0
            status = "PASS" if ok else f"FAIL (pred={predicted})"
            print(f"  [{status}] [{category}] {question[:50]}")
        except Exception as e:
            print(f"  [ERROR] {question[:50]}: {e}")
    acc = correct / total * 100 if total else 0
    print(f"Intent Detection Accuracy: {acc:.1f}% ({correct}/{total})")
    for cat, (n, ok) in by_cat.items():
        print(f"  - {cat}: {ok}/{n} correct")
    return acc


# ── Phase 3: Planning Quality ────────────────────────────────────────────────
PLAN_PROMPT = (
    "Bạn là Planner của JKAI. Lập kế hoạch thực hiện yêu cầu sau. Kế hoạch PHẢI chứa đủ 4 giai đoạn:\n"
    "1. Understand (hiểu rõ yêu cầu, xác định ràng buộc)\n"
    "2. Plan (phân rã công việc thành các bước cụ thể)\n"
    "3. Execute (bước thực thi, dùng tool cụ thể)\n"
    "4. Verify (cách kiểm tra kết quả)\n"
    "Trả lời dạng danh sách đánh số.\n\nYêu cầu: {question}"
)


def bench_planning_quality(client: OllamaClient, bank: list, sample: int = 10):
    print("\n═══ [PHASE 3] PLANNING QUALITY ═══")
    stages = ["understand", "plan", "execute", "verify"]
    passed = 0
    total = 0
    for item in bank[:sample]:
        if item["category"] != "DEEP_PLANNING":
            continue
        total += 1
        resp = client.chat([{"role": "user", "content": PLAN_PROMPT.format(question=item["question"])}])
        low = resp.lower()
        found = [s for s in stages if s in low]
        ok = len(found) == len(stages)
        if ok:
            passed += 1
        print(f"  [{'PASS' if ok else 'FAIL'}] stages_found={found} | {item['question'][:40]}")
    acc = passed / total * 100 if total else 0
    print(f"Planning Quality (Understand->Plan->Execute->Verify): {acc:.1f}% ({passed}/{total})")
    return acc


# ── Phase 4: JSON Adherence ──────────────────────────────────────────────────
JSON_PROMPT = (
    "Chỉ trả về JSON hợp lệ, không thêm text khác. JSON phải có 2 trường: "
    "skill (string), confidence (number 0-1).\nYêu cầu: {question}"
)


def bench_json_adherence(client: OllamaClient, sample: int = 10):
    print("\n═══ [PHASE 4] JSON ADHERENCE ═══")
    questions = [
        "Tìm kiếm thông tin về Docker",
        "Kiểm tra trạng thái hệ thống",
        "Viết báo cáo tài chính",
        "Phân tích lỗi server",
        "Tạo hình ảnh minh họa",
        "Dịch tài liệu sang tiếng Anh",
        "Tối ưu hóa truy vấn SQL",
        "Đọc file cấu hình",
        "Gửi email cho khách hàng",
        "Soạn thảo hợp đồng",
    ]
    passed = 0
    for i, q in enumerate(questions[:sample]):
        resp = client.generate(JSON_PROMPT.format(question=q), temperature=0.0)
        text = resp.get("response", "")
        try:
            data = json.loads(text)
            ok = isinstance(data, dict) and "skill" in data and "confidence" in data
        except Exception:
            ok = False
        if ok:
            passed += 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {q}")
    acc = passed / sample * 100 if sample else 0
    print(f"JSON Adherence: {acc:.1f}% ({passed}/{sample})")
    return acc


def main():
    sample = int(os.getenv("JKAI_BENCH_SAMPLE", "20"))
    client = OllamaClient()
    bank = []
    if os.path.exists(STRESS_BANK):
        with open(STRESS_BANK, "r", encoding="utf-8") as f:
            bank = json.load(f)
        print(f"Loaded {len(bank)} stress test cases from stress_test_bank.json")
    else:
        print("[WARN] stress_test_bank.json not found. Some phases will use built-in cases.")

    # Kiểm tra Ollama sẵn sàng
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags", timeout=10)
        tags = json.loads(urllib.request.urlopen(req).read())
        models = [m["name"] for m in tags.get("models", [])]
        print(f"Ollama OK. Models: {models}")
        if client.model not in models:
            print(f"[WARN] Model '{client.model}' not in list. Using anyway (Ollama may pull it).")
    except Exception as e:
        print(f"[FATAL] Cannot reach Ollama at {OLLAMA_URL}: {e}")
        print("Start Docker + Ollama first. Aborting.")
        sys.exit(1)

    # Model warmup
    client.generate("ping", num_ctx=2048)

    scores = []
    bench_inference(client)
    if bank:
        scores.append(("intent_detection", bench_intent_detection(client, bank, sample)))
        scores.append(("planning_quality", bench_planning_quality(client, bank, sample)))
    scores.append(("json_adherence", bench_json_adherence(client, sample)))

    print("\n═══ SUMMARY ═══")
    for name, score in scores:
        print(f"  {name}: {score:.1f}%")

    if scores:
        avg = sum(s for _, s in scores) / len(scores)
        print(f"  OVERALL E2E SCORE: {avg:.1f}%")


if __name__ == "__main__":
    main()
