<!-- 
[ZENITH FILE DIRECTIVE]
- File: SKILL.md
- Role: Elite Skill - Cognitive Council (Hội Đồng Chuyên Gia AI).
- Ownership: Mr LeeTrung
- Status: Active | Version: SDS v1.0
-->
# 🧠 SKILL: HỘI ĐỒNG CHUYÊN GIA AI (hoi_dong_chuyen_gia_ai)

Kỹ năng triệu hồi Hội đồng Chuyên gia đa mô hình (Gemini, ChatGPT, DeepSeek, Grok) cùng thảo luận, phản biện và đúc rút giải pháp tối ưu cho một bài toán phức tạp.

---

## 📥 DỮ LIỆU ĐẦU VÀO (INPUT SCHEMA)

Skill yêu cầu các tham số đầu vào sau:
- `question` (str, bắt buộc): Câu hỏi hoặc bài toán phức tạp cần hội đồng giải quyết.
- `focus_area` (str, tùy chọn): Lĩnh vực chuyên sâu (ví dụ: `architecture`, `security`, `coding`, `business`).
- `rounds` (int, mặc định `1`): Số vòng thảo luận phản biện nếu có xung đột lớn.

---

## 📤 DỮ LIỆU ĐẦU RA (OUTPUT SCHEMA)

Skill trả về báo cáo đồng thuận chuẩn hóa dưới dạng JSON:
```json
{
  "consensus_reached": true,
  "conflict_score": 0.15,
  "final_decision": "Giải pháp cuối cùng được đồng thuận...",
  "expert_opinions": {
    "architect": {
      "model": "gpt-4o",
      "claims": ["..."],
      "evidence": ["..."],
      "confidence": 0.95
    },
    "researcher": {
      "model": "gemini-1.5-pro",
      "claims": ["..."],
      "evidence": ["..."],
      "confidence": 0.90
    }
  },
  "merged_claims": [
    {
      "claim": "Thiết kế kiến trúc dạng hướng sự kiện",
      "consensus_level": "HIGH",
      "confidence_avg": 0.92,
      "supporting_models": ["gpt-4o", "gemini-1.5-pro"]
    }
  ]
}
```

---

## 🛡️ VAI TRÒ CỦA CÁC CHUYÊN GIA (ROLE DEFINITIONS)

| Vai trò | Mô hình đảm nhiệm | Chuyên môn tập trung |
| :--- | :--- | :--- |
| **Architect** (Kiến trúc sư) | **OpenAI (GPT-4o)** | Thiết kế cấu trúc hệ thống, quy trình dữ liệu, sơ đồ vận hành. |
| **Researcher** (Nhà nghiên cứu) | **Google (Gemini 1.5 Pro)** | Thu thập thông tin, quét rủi ro, phân tích edge cases và lập luận. |
| **Coder** (Lập trình viên) | **DeepSeek (V3/R1)** | Viết mã nguồn tối ưu, đánh giá giải thuật, cấu trúc logic. |
| **Critic** (Phản biện khách quan) | **Grok (xAI)** | Đánh giá tính thực tiễn, so sánh thị trường, phản biện các lỗ hổng. |
