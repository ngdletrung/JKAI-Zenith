<!-- 
[ZENITH FILE DIRECTIVE]
- File: ZENITH_VAULT.md
- Role: L1 Cache & Session Register Specification.
- Ownership: Mr LeeTrung
- Status: Active | Version: SDS v20.1
[WORKING PRINCIPLES]:
1. [VOLATILITY-AWARE]: VAULT quản lý dữ liệu ngắn hạn và trạng thái phiên.
2. [L1-EFFICIENCY]: Tối ưu hóa tốc độ truy xuất tri thức dự án hiện hành.
3. [NO-EMOJI]: Cấm tuyệt đối emoji trong đặc tả kỹ thuật.
-->
# 🔒 ZENITH VAULT: L1 CACHE & SESSION REGISTERS (v1.0)
**"Phân vùng Thanh ghi và Bộ nhớ đệm Tác vụ ngắn hạn"**

> [!NOTE]
> **VAULT (Chỉ mục số 10)** là phân vùng lưu trữ trung gian giữa trí nhớ dài hạn (Knowledge) và hành động thực thi. Nó hoạt động như một bộ nhớ đệm L1 (Level 1 Cache), chứa các thông tin cực kỳ quan trọng về phiên làm việc hiện tại để các Đặc vụ có thể truy xuất với độ trễ tối thiểu.

---

## ⚡ 1. CẤU TRÚC BỘ NHỚ ĐỆM (CACHE STRUCTURE)

### 1.1 Thanh ghi phiên (Session Registers)
- **Active Goals**: Danh sách các mục tiêu đang thực thi trên Goal Stack.
- **Mission Context**: Bối cảnh cụ thể của sứ mệnh hiện tại (đường dẫn dự án, các biến môi trường tạm thời).
- **Execution State**: Trạng thái cuối cùng của các tiến trình đang chạy dở.

### 1.2 Tri thức dự án ngắn hạn (Project-Specific Vault)
- Lưu trữ các quy định, logic hoặc tài liệu đặc thù của dự án đang được xử lý (nằm trong thư mục `intelligence/vault/`).
- Tự động nạp (Load) khi bắt đầu sứ mệnh và giải phóng (Flush) khi hoàn thành.

---

## 🛠️ 2. CƠ CHẾ VẬN HÀNH (OPERATIONAL MECHANISM)

- **Read Policy**: Đặc vụ luôn tra cứu VAULT trước khi truy vấn Knowledge DB để tiết kiệm tài nguyên.
- **Write Policy**: Mọi thay đổi trong phiên làm việc phải được ghi nhận vào VAULT trước khi được "đúc kết" (Distill) vào bộ nhớ dài hạn.
- **Eviction Policy**: Dữ liệu trong VAULT sẽ bị ghi đè hoặc xóa bỏ sau khi Master xác nhận hoàn thành nhiệm vụ (Mission Accomplished).

---

## 🏛️ 3. PHÂN VÙNG VẬT LÝ (PHYSICAL MAPPING)

- **Vault Registry**: `intelligence/vault/vault_index.json`
- **Dynamic Memory**: `intelligence/vault/active_memory/`
- **Project Artifacts**: `intelligence/vault/Output/`

---
*Sovereign Property of Master LeeTrung. Optimized for High-Speed Reasoning.* 🔒⚡🏛️
