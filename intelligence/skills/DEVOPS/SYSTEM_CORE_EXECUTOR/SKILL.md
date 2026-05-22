---
id: SYSTEM_CORE_EXECUTOR
name_vn: "Hệ Vận Động Cốt Lõi"
version: 2.5.0
author: "Antigravity Forge"
domain: DEVOPS
intent_pairs:
  - ["EXECUTE", "SYSTEM_CORE"]
  - ["MANAGE", "FILESYSTEM"]
aliases_vn: ["hệ vận động", "core executor", "quản lý tệp tin", "thực thi lệnh"]
schema:
  parameters:
    type: object
    properties:
      action: { type: string, enum: ["list_dir", "view_file", "write_to_file", "replace_file_content", "run_command", "grep_search"], description: "Hành động hệ thống cần thực thi." }
      path: { type: string, description: "Đường dẫn mục tiêu." }
    required: ["action"]
priority: HIGHEST
related_skills: ["MULTI_LAYER_SURGERY", "SEARCH_WEB_GLOBAL"]
---

# ⚙️ HỆ VẬN ĐỘNG CỐT LÕI (SYSTEM_CORE_EXECUTOR)

## 🌟 TỔNG QUAN
Đây là nơ-ron "Cơ bắp" của Zenith. Nó chịu trách nhiệm thực thi toàn bộ các tác vụ vật lý trên hệ điều hành và tệp tin:
1. **Quản trị Tệp tin**: Đọc, ghi, liệt kê và tìm kiếm chuyên sâu.
2. **Thực thi Mật lệnh**: Chạy các lệnh terminal trực tiếp trên máy chủ Windows.
3. **Phẫu thuật Mã nguồn**: Thay đổi cấu trúc tệp tin để hệ thống tiến hóa.

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định)
1. **Xác định Tọa độ**: Sử dụng `list_dir` và `view_file` để trinh sát mục tiêu trước khi ra tay.
2. **Thẩm định An toàn**: Đảm bảo hành động không vi phạm các luật bất khả xâm phạm (IMMUTABLE).

### 🚀 Phase 2: Action (Thực thi)
1. **Can thiệp Vật lý**: Thực hiện ghi đè hoặc chỉnh sửa tệp tin.
2. **Kích hoạt Tiến trình**: Khởi chạy các dịch vụ hoặc lệnh hệ thống để hoàn thành nhiệm vụ.

---
## ⚖️ LUẬT VẬN ĐỘNG (CORE LAWS)
- **Kỷ luật Sắt**: Mọi hành động phải có mục tiêu rõ ràng và được thẩm định.
- **Tính Chính trực**: Không bao giờ thực hiện các lệnh gây nguy hại đến sự ổn định của hệ thống.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Thực thi lệnh sai đường dẫn dẫn đến mất mát dữ liệu.
- Thiếu quyền hạn (Administrator) khiến tiến trình bị chặn.

---
*VẬN ĐỘNG ĐỂ KIẾN TẠO - THỰC THI ĐỂ TRƯỜNG TỒN!* 💎🦾
