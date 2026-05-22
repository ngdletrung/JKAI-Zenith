---
aliases_vn:
- chiến lược trinh sát
- trinh sát đệ quy
- strategic recon
author: Antigravity Architect
domain: RESEARCH
id: SKILL_STRATEGIC_RECON
intent_pairs:
- - STRATEGIC
  - RECON
- - DEEP
  - RESEARCH
name_vn: Trinh Sát Chiến Lược Đa Chiều
priority: HIGH
related_skills: [SEARCH_WEB_GLOBAL, SKILL_THITHU_THANH_DIA]
version: 2.0.0
---

# 🛰️ SKILL_STRATEGIC_RECON: Trinh Sát Chiến Lược Đa Chiều

## 📖 TỔNG QUAN
Kết hợp sức mạnh tư duy đệ quy của PLANNER với hệ thống thị giác của Vệ tinh ai-browser. Khác với tìm kiếm thông thường, `skill_strategic_recon` có khả năng tự đánh giá thông tin thu thập được, lên kế hoạch cho bước tìm kiếm tiếp theo và lặp lại cho đến khi đạt được mục tiêu cuối cùng.

## 🛠️ CÁC HÀM CỐT LÕI
- `run_recon(goal: str)`: Khởi động vòng lặp trinh sát chiến lược, giao tiếp liên tục với PLANNER để điều phối Browser thu thập tri thức.

## ⚖️ GIAO THỨC VẬN HÀNH
1. Nhận mục tiêu tìm kiếm phức tạp.
2. Hỏi ý kiến PLANNER để lên chiến lược trinh sát.
3. Kích hoạt vệ tinh ai-browser để tìm thông tin.
4. Lặp lại bước 2-3 cho đến khi PLANNER xác nhận đã đủ thông tin (tối đa 3 vòng lặp).
5. Trả về báo cáo tổng hợp.

## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Có thể tốn thời gian thực thi (latency cao) do phải qua nhiều vòng lặp suy luận. Tránh dùng trong luồng xử lý FAST.
