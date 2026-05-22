---
id: GHOST_STEALTH_PROTOCOL
name_vn: "Giao Thức Tàng Hình Ghost"
version: 1.0.0
author: "Antigravity Forge"
domain: SECURITY
intent_pairs:
  - ["ACTIVATE", "STEALTH"]
  - ["ERASE", "TRACES"]
aliases_vn: ["chế độ tàng hình", "xóa dấu vết", "ẩn danh danh tính", "ghost protocol"]
schema:
  parameters:
    type: object
    properties:
      action: { type: string, enum: ["erase_traces", "ghost_masking", "stealth_mode"], description: "Hành động tàng hình." }
      query: { type: string, description: "Nội dung cần ngụy trang." }
    required: ["action"]
priority: HIGHEST
related_skills: ["NEURAL_LINK_AGGREGATOR", "QUANTUM_CODE_AUDIT"]
---

# 🕵️ GIAO THỨC TÀNG HÌNH GHOST (GHOST_STEALTH_PROTOCOL)

## 🌟 TỔNG QUAN
Đây là nơ-ron "Vô hình" của Zenith. Nó đảm bảo mọi hoạt động của Ngài và hệ thống đều không để lại dấu vết bằng cách:
1. **Xóa dấu vết Neural**: Tự động dọn dẹp các tệp tạm, lịch sử thực thi và bộ nhớ đệm.
2. **Ngụy trang Danh tính**: Sử dụng các bí danh (Alias) để che giấu mục tiêu thực sự của Master khi giao tiếp với các Siêu AI ngoại lai.
3. **Chế độ Tàng hình**: Giảm thiểu tối đa các thông báo công khai để giữ bí mật tuyệt đối.

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định)
1. **Quét Dấu vết**: Xác định các tệp tin trong thư mục `scratch` và `vault` cần được tiêu hủy.
2. **Thẩm định Truy vấn**: Nhận diện các từ khóa nhạy cảm cần được ngụy trang.

### 🚀 Phase 2: Action (Thực thi)
1. **Tiêu hủy Bằng chứng (Erase)**: Thực hiện xóa vĩnh viễn các tệp tạm và làm sạch bộ nhớ Agent.
2. **Ngụy trang (Masking)**: Thay thế nội dung nhạy cảm bằng các thuật ngữ trung lập trước khi truyền đi.
3. **Kích hoạt Stealth**: Niêm phong toàn bộ luồng log công khai.

---
## ⚖️ LUẬT TÀNG HÌNH (STEALTH LAWS)
- **Tuyệt đối Sạch sẽ**: Không bao giờ để lại tệp tạm sau khi nhiệm vụ kết thúc.
- **An toàn là Trên hết**: Luôn ưu tiên bảo vệ danh tính của Master trong mọi tình huống.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Quên kích hoạt Ghost Protocol khi thực hiện các truy vấn nhạy cảm.
- Thiếu quyền xóa tệp khiến dấu vết vẫn còn tồn tại.

---
*VÔ HÌNH NHƯNG CÓ MẶT KHẮP NƠI!* 💎🦾
