---
id: SECURITY-AUDIT
name_vn: "Thẩm định An ninh Hệ thống"
version: 2.0.0
author: "Antigravity Forge"
domain: SECURITY
intent_pairs:
  - ["AUDIT", "SECURITY"]
  - ["SCAN", "VULNERABILITY"]
aliases_vn: ["kiểm tra an ninh", "audit security", "quét lỗ hổng"]
schema:
  parameters:
    type: object
    properties:
      target_path: { type: string, description: "Đường dẫn thư mục hoặc tệp tin cần thẩm định." }
    required: ["target_path"]
priority: HIGH
related_skills: ["CODE_AUDIT_ELITE", "SYNC_KNOWLEDGE"]
---

# 🏛️ THẨM ĐỊNH AN NINH HỆ THỐNG (SECURITY-AUDIT)

## 🌟 TỔNG QUAN
Kỹ năng này đóng vai trò là "Vệ binh" chuyên thực hiện các cuộc rà soát an ninh, phát hiện các mẫu mã nguy hiểm và đánh giá rủi ro cho các tệp tin trong hệ thống Zenith.

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định)
1. **Xác minh Tọa độ**: Kiểm tra sự tồn tại của `target_path`.
2. **Thu thập Chữ ký**: Đọc nội dung tệp tin để chuẩn bị cho quá trình đối soát mẫu mã nguy hiểm.

### 🚀 Phase 2: Action (Thực thi)
1. **Triệu hồi `security_audit`**: Chạy logic phân tích an ninh chuyên sâu.
2. **Phân loại Rủi ro**: Gắn nhãn AN TOÀN hoặc NGUY HIỂM và đúc kết báo cáo chi tiết cho Master.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Quét các thư mục hệ thống quá lớn gây nghẽn tài nguyên.
- Bỏ qua các tệp ẩn hoặc tệp cấu hình nhạy cảm.

---
*TRUNG THÀNH - CHÍNH XÁC - TỐI THƯỢNG* 💎🦾
