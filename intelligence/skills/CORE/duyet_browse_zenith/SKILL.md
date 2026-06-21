---
aliases_vn:
- thiên nhãn
- browser vision
- quan sát trình duyệt
- chụp màn hình web
- tương tác giao diện
author: Antigravity Architect
domain: CORE
id: BROWSER_VISION_OPS
intent_pairs:
- - OBSERVE
  - WEB_PAGE
- - INTERACT
  - BROWSER
- - SCREENSHOT
  - WEB
- - NAVIGATE
  - BROWSER
name_vn: Browser Vision Ops (Thiên Nhãn)
priority: HIGH
related_skills: [SEARCH_WEB_GLOBAL, SKILL_STRATEGIC_RECON]
version: 2.1.0
---

# 👁️ BROWSER_VISION_OPS: Browser Vision Ops (Thiên Nhãn)

## 📖 TỔNG QUAN
Sử dụng công nghệ AI Browser Use để tương tác trực tiếp với các trang web như con người. Thay vì chỉ cào văn bản thô, Thiên Nhãn có khả năng "nhìn" bằng Vision Models, tự động click, cuộn trang và xử lý tương tác giao diện người dùng.

## 🛠️ CÁC HÀM CỐT LÕI
- `quan_sat_thi_giac(objective: str, url: str)`: Khởi tạo vệ tinh Thiên Nhãn đến mục tiêu, quan sát, tương tác và chụp ảnh bằng chứng gửi về tổng hành dinh.

## ⚖️ GIAO THỨC VẬN HÀNH
1. Khi có yêu cầu tương tác giao diện, chụp ảnh màn hình, hoặc vượt Captcha.
2. Hệ thống sẽ khởi động Headless Browser thông qua vệ tinh `ai-browser`.
3. Gửi lại kết quả phân tích cùng đường dẫn hình ảnh bằng chứng (nếu có).

## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Không nên dùng để đọc nội dung text tĩnh đơn giản. Đối với text tĩnh, ưu tiên sử dụng `read_url_content` để tiết kiệm tài nguyên.
