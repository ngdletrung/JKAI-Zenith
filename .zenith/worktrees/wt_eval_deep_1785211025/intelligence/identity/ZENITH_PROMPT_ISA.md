<!-- 
[ZENITH FILE DIRECTIVE]
- File: ZENITH_PROMPT_ISA.md
- Role: Prompt Instruction Set Architecture Specification.
- Ownership: Mr LeeTrung
- Status: Active | Version: SDS v20.1
[WORKING PRINCIPLES]:
1. [ISA-DETERMINISM]: Prompt phải mang tính chỉ lệnh tuyệt đối, không có văn phong thừa.
2. [DYNAMIC-FORGING]: Sử dụng Prompt Forge Engine để biên dịch ngữ cảnh thời gian thực.
3. [NO-EMOJI]: Cấm tuyệt đối emoji trong đặc tả tập lệnh.
-->
# ✍️ ZENITH PROMPTS: INSTRUCTION SET ARCHITECTURE (v1.0)
**"Đặc tả Kiến trúc tập lệnh tư duy và Prompt Forge Engine"**

> [!TIP]
> **PROMPTS (Chỉ mục số 5)** đóng vai trò là Kiến trúc tập lệnh tư duy (ISA - Instruction Set Architecture). Đây là lớp "biên dịch" ý chí của Master thành các chỉ lệnh kỹ thuật mà mô hình AI có thể thực thi chính xác nhất.

---

## ⚒️ 1. PROMPT FORGE ENGINE (XƯỞNG ĐÚC LINH HỒN)

### 1.1 Nguyên lý biên dịch (Compilation Principle)
- Hệ thống không sử dụng System Prompts tĩnh.
- **Prompt Forge Engine** (`prompt_forge.py`) sẽ thực hiện "đúc" Prompt dựa trên:
    - **Identity Base**: Bản sắc Sovereign từ `ZENITH_IDENTITY.md`.
    - **Mission Context**: Dữ liệu từ VAULT về nhiệm vụ hiện tại.
    - **Role Specs**: Đặc tả vai trò từ `ZENITH_AGENT_PROFILES.md`.
    - **Guardrails**: Các quy tắc bảo mật từ `ZENITH_SOVEREIGN_RULES.md`.

### 1.2 Cấu trúc XML chuẩn hóa
- Mọi Prompt được đóng gói trong các thẻ XML để mô hình AI dễ dàng bóc tách cấu trúc:
    - `<sovereign_identity>`: Bản sắc tối cao.
    - `<mission_objective>`: Mục tiêu sứ mệnh.
    - `<constraints>`: Các rào chắn và quy tắc.
    - `<available_tools>`: Danh mục công cụ được phép dùng.

---

## 🏛️ 2. QUẢN LÝ TẬP LỆNH (INSTRUCTION MANAGEMENT)

- **Template Registry**: Các biểu mẫu Prompt được lưu trữ tại `intelligence/prompts/`.
- **Zero-Noise Standard**: Loại bỏ hoàn toàn các từ ngữ xã giao, biểu cảm trong Prompt để tối ưu hóa nơ-ron và giảm chi phí token.

---

## 🔄 3. CHU KỲ CẬP NHẬT (UPDATE CYCLE)

- Prompt ISA được cập nhật ngay khi Master thay đổi triết lý tại `.keywork.md` hoặc khi hệ thống đúc rút được các "Antipatterns" mới từ quá trình thực thi.

---
*Sovereign Property of Master LeeTrung. Defined for Cognitive Precision.* ✍️⚒️🏛️
