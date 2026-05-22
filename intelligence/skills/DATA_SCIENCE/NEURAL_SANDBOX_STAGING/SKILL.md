---
id: NEURAL_SANDBOX_STAGING
name_vn: "Phòng Thử Nghiệm Cô Lập Sandbox"
version: 1.0.0
author: "Antigravity Forge"
domain: DATA_SCIENCE
intent_pairs:
  - ["RUN", "SANDBOX"]
  - ["TEST", "CODE"]
aliases_vn: ["sandbox", "thử nghiệm code", "môi trường cô lập", "test surgery"]
schema:
  parameters:
    type: object
    properties:
      code_snippet: { type: string, description: "Đoạn mã cần thực thi thử nghiệm." }
      action: { type: string, enum: ["create", "execute", "destroy"], default: "execute", description: "Hành động sandbox." }
    required: ["code_snippet"]
priority: HIGH
related_skills: ["SKILL_SYSTEM_CORE", "NEURAL_LINK_AGGREGATOR"]
---

# 🧪 PHÒNG THỬ NGHIỆM CÔ LẬP (NEURAL_SANDBOX_STAGING)

## 🌟 TỔNG QUAN
Đây là nơ-ron "Bảo an" cho các tiến trình thực thi mã nguồn. Nó tạo ra một "Phòng thí nghiệm" ảo hoàn toàn cô lập (Docker Sandbox) không có kết nối mạng, cho phép thực thi và kiểm tra các đoạn mã lạ hoặc nguy hiểm mà không gây ảnh hưởng đến hệ thống chính.

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định)
1. **Rà soát Mã nguồn**: Kiểm tra sơ bộ đoạn mã để tìm các lệnh phá hoại tiềm tàng.
2. **Khởi tạo Vùng đệm**: Triệu hồi Docker để dựng lên một Container `python:3.11-slim` hoàn toàn mới và ngắt kết nối mạng.

### 🚀 Phase 2: Action (Thực thi)
1. **Thực thi Biệt lập**: Đẩy đoạn mã vào trong Sandbox và theo dõi kết quả trả về (stdout/stderr).
2. **Thu thập Kết quả**: Ghi lại mọi biến động và lỗi cú pháp nếu có.
3. **Hủy diệt Bằng chứng**: Sau khi có kết quả, hệ thống sẽ tự động tiêu hủy Container để giải phóng tài nguyên và xóa sạch mọi dấu vết thực thi.

---
## ⚖️ LUẬT CÔ LẬP (SANDBOX LAWS)
- **Cấm mạng lưới**: Tuyệt đối không cho phép Sandbox kết nối ra internet.
- **Tiêu hủy Tức thì**: Không bao giờ để Container Sandbox tồn tại quá lâu sau khi hoàn thành nhiệm vụ.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Thiếu tài nguyên Docker khiến việc khởi tạo Sandbox bị thất bại.
- Đoạn mã thực hiện các vòng lặp vô tận gây treo Container.

---
*AN TOÀN LÀ NỀN TẢNG CỦA SỨC MẠNH!* 💎🦾
