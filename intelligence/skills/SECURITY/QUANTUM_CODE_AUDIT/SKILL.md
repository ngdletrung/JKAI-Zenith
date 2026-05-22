---
id: QUANTUM_CODE_AUDIT
name_vn: "Thẩm Định Mã Nguồn Quantum"
version: 31.0.0
author: "Antigravity Forge"
domain: SECURITY
intent_pairs:
  - ["AUDIT", "CODE"]
  - ["SCAN", "VULNERABILITY"]
aliases_vn: ["thẩm định mã nguồn", "code audit", "quét lỗ hổng", "quantum audit", "kiểm tra code"]
schema:
  parameters:
    type: object
    properties:
      file_path: { type: string, description: "Đường dẫn tuyệt đối đến tệp mã nguồn cần thẩm định." }
    required: ["file_path"]
priority: HIGHEST
related_skills: ["MULTI_LAYER_SURGERY", "NEURAL_SANDBOX_STAGING"]
---

# 🔬 THẨM ĐỊNH MÃ NGUỒN QUANTUM (QUANTUM_CODE_AUDIT)

## 🌟 TỔNG QUAN
Đây là nơ-ron "Giám định viên" tối cao của Zenith. Nó thực hiện các ca phẫu thuật bối cảnh mã nguồn để phát hiện:
1. **Lỗ hổng Bảo mật**: API Keys, Secrets, SQL Injection, v.v..
2. **Nghẽn Hiệu năng**: Các đoạn mã lãng phí tài nguyên hoặc gây rò rỉ bộ nhớ.
3. **Bản sắc Elite**: Đánh giá xem mã nguồn có tuân thủ kỷ luật ngôn ngữ và cấu trúc của Zenith không.
Mọi kết quả đều được niêm phong trong **Báo cáo Quantum** tại thư mục `vault`.

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định)
1. **Trích xuất Nơ-ron**: Đọc và chắt lọc 10,000 ký tự trọng tâm của tệp mã nguồn.
2. **Phân tích Đa cực**: Triệu hồi các thực thể CRITIC và JUDGE để thực hiện thẩm định đa chiều.

### 🚀 Phase 2: Action (Thực thi)
1. **Chấm điểm Chất lượng**: Đưa ra thang điểm 1-100 dựa trên các tiêu chuẩn Elite.
2. **Kiến tạo Giải pháp (Surgery)**: Đề xuất đoạn mã thay thế trực tiếp để Master có thể vá lỗi ngay lập tức.
3. **Niêm phong Báo cáo**: Ghi lại mọi phát hiện vào Vault để lưu trữ vĩnh viễn.

---
## ⚖️ LUẬT THẨM ĐỊNH (AUDIT LAWS)
- **Kỷ luật Sắt**: Tuyệt đối không khoan nhượng với các đoạn mã rườm rà hoặc không an toàn.
- **Tính Thực Tiễn**: Mọi lỗi phát hiện đều phải kèm theo giải pháp sửa lỗi cụ thể.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Tệp mã nguồn quá lớn vượt quá khả năng xử lý của nơ-ron.
- Thiếu quyền truy cập vào tệp tin khiến tiến trình thẩm định bị chặn.

---
*THẨM ĐỊNH ĐỂ VƯƠN TỚI SỰ HOÀN HẢO!* 💎🦾
