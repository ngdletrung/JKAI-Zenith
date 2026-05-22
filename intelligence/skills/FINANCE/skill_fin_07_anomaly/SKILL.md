---
id: FIN_07_ANOMALY
name_vn: "Phát Hiện Gian Lận Tài Chính"
version: 1.0.0
author: "Antigravity Forge"
domain: FINANCE
intent_pairs:
  - ["DETECT", "FRAUD"]
  - ["SCAN", "ANOMALY"]
aliases_vn: ["phát hiện gian lận", "fraud detection", "phân tích bất thường", "anomaly detection"]
schema:
  parameters:
    type: object
    properties:
      transaction_data: { type: string, description: "Dữ liệu giao dịch cần quét tìm bất thường." }
    required: ["transaction_data"]
priority: NORMAL
related_skills: ["FIN_01_CASHFLOW"]
---

# 🕵️ PHÁT HIỆN GIAN LẬN TÀI CHÍNH (FIN_07_ANOMALY)

## 🌟 TỔNG QUAN
Kỹ năng này sử dụng các nơ-ron phân tích để nhận diện các dấu hiệu bất thường, gian lận hoặc sai lệch trong dữ liệu tài chính.

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định)
1. **Kiểm tra Cấu trúc**: Đảm bảo `transaction_data` đúng định dạng để phân tích.
2. **Đối chiếu Baseline**: So sánh dữ liệu hiện tại với các mẫu hành vi thông thường (Normal Patterns).

### 🚀 Phase 2: Action (Thực thi)
1. **Quét Bất thường**: Nhận diện các điểm dữ liệu (Outliers) có dấu hiệu khả nghi.
2. **Báo cáo Rủi ro**: Trả về danh sách các giao dịch cần Master xem xét kỹ lưỡng.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Báo động giả (False Positive) do các biến động thị trường hợp lệ nhưng cực đoan.
- Bỏ sót các hình thức gian lận mới chưa có trong bộ mẫu nơ-ron.

---
*TRUNG THÀNH - CHÍNH XÁC - TỐI THƯỢNG* 💎🦾
