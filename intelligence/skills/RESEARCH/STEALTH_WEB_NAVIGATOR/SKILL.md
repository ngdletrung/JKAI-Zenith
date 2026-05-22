---
id: STEALTH_WEB_NAVIGATOR
name_vn: "Đặc Vụ Ẩn Danh Zenith"
version: 1.0.0
author: "Antigravity Architect"
domain: RESEARCH
intent_pairs:
  - ["BROWSE", "STEALTH"]
  - ["NAVIGATE", "ANTIBOT"]
  - ["SCRAPE", "CLOUDFLARE"]
  - ["ACCESS", "PROTECTED"]
  - ["BYPASS", "CAPTCHA"]
  - ["RESEARCH", "PROTECTED_SITE"]
aliases_vn: ["duyệt ẩn danh", "vượt cloudflare", "vượt captcha", "trình duyệt ẩn", "stealth browse", "dò đường ẩn danh", "đặc vụ web"]
priority: HIGH
related_skills: ["SEARCH_WEB_GLOBAL", "WEB_PATHFINDER"]
hardware_role: PLANNER
---

# 🕵️ ĐẶC VỤ ẨN DANH ZENITH (STEALTH_WEB_NAVIGATOR)

## 📖 TỔNG QUAN
Kỹ năng này triển khai trình duyệt ẩn danh cấp cao nhất thông qua dịch vụ Visual Satellite
(`ai-browser`), sử dụng nhân Chromium stealth của **CloakBrowser** — đã được vá trực tiếp
ở tầng C++ để qua mặt toàn bộ hệ thống phát hiện bot tân tiến.

**Khả năng vượt qua:**
- Cloudflare Turnstile / Bot Management
- reCAPTCHA v3 Enterprise
- DataDome
- Akamai Bot Manager
- PerimeterX / Human Security

**Tính năng tự dò đường:** Agent `browser_use` tự động điều hướng, click, scroll,
xử lý form, và tổng hợp dữ liệu — mà không cần chỉ định từng bước thủ công.

## 🛠️ CÔNG CỤ TÁC CHIẾN
- `stealth_browse`: Duyệt web ẩn danh qua CloakBrowser + agent tự dò đường.
- `stealth_screenshot`: Chụp ảnh trang web qua CloakBrowser (zero bot-detection penalty).

## ⚙️ GIAO THỨC VẬN HÀNH (OPERATIONAL PROTOCOL)

### Phase 1: Threat Assessment (Đánh giá mức độ bảo vệ)
- Kiểm tra xem trang mục tiêu có yêu cầu bảo vệ cao không (Cloudflare, reCAPTCHA).
- Nếu không có bot-protection đặc biệt → dùng `SEARCH_WEB_GLOBAL.web_scraper` (nhẹ hơn).
- Nếu có bot-protection → kích hoạt `STEALTH_WEB_NAVIGATOR`.

### Phase 2: Stealth Navigation (Điều hướng ẩn danh)
- Gọi `stealth_browse(url, objective)` để khởi động CloakBrowser.
- Agent tự động dò đường: tìm kiếm → click → scroll → điền form → trích xuất.
- Fingerprint được randomize mỗi phiên: platform, timezone, WebRTC, canvas, fonts.

### Phase 3: Data Extraction (Trích xuất dữ liệu)
- Thu thập kết quả từ agent sau khi hoàn thành nhiệm vụ.
- Gọi `stealth_screenshot` nếu cần bằng chứng thị giác.
- Đóng phiên browser để giải phóng tài nguyên hệ thống.

### Quy tắc kích hoạt:
- Chỉ kích hoạt khi các phương pháp nhẹ hơn (Jina/Tavily) đã thất bại.
- Ưu tiên tốc độ: đặt `headless=True` cho tác vụ nền.
- Đặt `humanize=True` khi cần vượt qua CAPTCHA phức tạp (Bézier mouse curves).

---
*VƯỢT TƯỜNG LỬA - THÁM HIỂM VÔ HÌNH!* 🕵️🛡️🔥
