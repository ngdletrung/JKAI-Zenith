<!-- 
[ZENITH FILE DIRECTIVE]
- File: ZENITH_SOVEREIGN_RULES.md
- Role: System-wide Policies & Security Guardrails.
- Ownership: Mr LeeTrung
- Status: Active | Version: SDS v20.1
[WORKING PRINCIPLES]:
1. [POLICY-SUPREMACY]: Mọi đặc vụ phải đối chiếu với tệp này trước khi thực thi lệnh ghi (Write).
2. [SDS-COMPLIANCE]: Duy trì cấu trúc đặc tả kỹ thuật nghiêm ngặt.
3. [NO-EMOJI]: Cấm tuyệt đối emoji trong nội dung quy tắc.
-->
# ⚖️ ZENITH SOVEREIGN RULES: SYSTEM POLICIES & GUARDRAILS (v1.0)
**"Hiến chương Vận hành và Bảo mật tối cao cho Nhân hệ thống JKAI"**

> [!IMPORTANT]
> Đây là tập hợp các quy tắc định tính chi phối hành vi của toàn bộ bộ máy JKAI Zenith. Mọi Đặc vụ (Agents) và Trình điều khiển (Skills) bắt buộc phải tuân thủ các rào chắn## [SOVEREIGN-SECURITY-PROTOCOL] (Bảo mật tối thượng)

1. [NO-SECRETS]: Cấm tuyệt đối hardcode API Keys, Passwords, Tokens vào mã nguồn. Sử dụng `.env` hoặc Vault.
2. [INPUT-SANITY]: Mọi dữ liệu từ bên ngoài (Master, API, Web) phải được khử khuẩn (Sanitize) trước khi xử lý.
3. [SILENT-FAIL]: Thông báo lỗi không được tiết lộ cấu trúc hệ thống hoặc dữ liệu nhạy cảm.
4. [RECON-FIRST]: Luôn sử dụng kỹ năng `ZENITH_SECURITY_SCAN` trước khi triển khai các dịch vụ công khai.
5. [TRIPLE-LOCK]: Các lệnh `rm -rf`, `docker system prune` hoặc các lệnh hủy diệt dữ liệu phải được Master xác nhận 3 lần.

---
*Tập hợp Quy chế này là Hiến chương vận hành của JKAI Zenith. Vi phạm quy chế là vi phạm Bản sắc.* 🛡️🏛️⚙️

---

## 🛡️ 1. CHÍNH SÁCH BẢO MẬT TỐI CAO (SECURITY POLICIES)

### 1.1 Quyền lực duy nhất (Single Source of Authority)
- Master LeeTrung là thực thể duy nhất có quyền thay đổi các tham số cốt lõi.
- Đặc vụ không được phép tự ý sửa đổi `rule_hardware.md` hoặc các tệp trong `/intelligence/identity/` nếu không có lệnh trực tiếp.

### 1.2 Kiểm soát thực thi (Execution Guardrails)
- **Zero-Trust Input**: Mọi dữ liệu từ bên ngoài (Web, API) phải được coi là không an toàn cho đến khi được `PolicyProofEngine` thẩm định.
- **Surgical Discipline**: Cấm tuyệt đối việc ghi đè (Overwrite) toàn bộ tệp tin lớn nếu chỉ cần sửa đổi một phần nhỏ. Phải sử dụng `multi_replace_file_content`.

---

## ⚙️ 2. QUY CHẾ VẬN HÀNH HỆ THỐNG (OPERATIONAL RULES)

### 2.1 Quản lý mã nguồn (Code Governance)
- **No Placeholder Policy**: Cấm sử dụng các đoạn code giả định hoặc `...`. Mọi đoạn code phải hoàn chỉnh và thực thi được.
- **Header Preservation**: Mọi file mới tạo ra bắt buộc phải có khối SDS Header chuẩn hóa.
- **Anti-Redundancy**: Phải thực hiện `grep_search` toàn bộ codebase trước khi khởi tạo bất kỳ logic mới nào để tránh trùng lặp.

### 2.2 Quản lý tài nguyên (Resource Governance)
- **Token Economy**: Ưu tiên các giải pháp tiết kiệm token và tối ưu hóa ngữ cảnh.
- **Hardware Affinity**: Tuân thủ nghiêm ngặt định tuyến model lên CPU/GPU theo đặc tả tại `rule_hardware.md`.

### 2.3 Quy trình Phê duyệt Tối thượng (Supreme Approval Protocol)
- **Plan-First Mandate**: Mọi thay đổi nòng cốt, cải tiến hệ thống hoặc vá lỗi logic bắt buộc phải thông qua Implementation Plan được JKAI Zenith soạn thảo và Master phê duyệt.
- **Autonomous De-escalation**: Các module tự trị (Distiller, Evolve, Surgeon) không được phép tự ý kích hoạt lệnh phê duyệt HẠT NHÂN. Chúng chỉ được phép lưu đề xuất (Proposal) vào Vault.
- **JKAI Mediation**: Chỉ có Đặc vụ điều hành (Antigravity) đại diện cho JKAI mới có quyền thẩm định đề xuất từ Vault và chuyển đổi chúng thành Kế hoạch thực thi chính thức.

---

## 🏛️ 3. GIAO THỨC TỰ CHỮA LÀNH (SELF-HEALING RULES)

- **Atomic Recovery**: Khi một giao dịch sửa đổi file thất bại, hệ thống phải thực hiện rollback (hoàn tác) ngay lập tức về trạng thái ổn định gần nhất.
- **Audit Logging**: Mọi lỗi hệ thống phải được ghi nhận vào `GLOBAL_SYSTEM_CONTEXT.md` kèm theo mã lỗi và giải pháp khắc phục.

---

## 🔄 4. QUY TẮC TIẾN HÓA (EVOLUTION RULES)

- **Knowledge Distillation**: Chỉ những kinh nghiệm đã qua kiểm chứng (Verified) mới được phép nạp vào 12 Trụ cột.
- **Map Alignment**: Sau mỗi thay đổi về cấu trúc tệp tin, `MAP_INTELLIGENCE.md` và các bản đồ liên quan phải được cập nhật đồng bộ ngay lập tức.

---
*Sovereign Property of Master LeeTrung. Defined for Operational Integrity.* ⚖️🏛️🛡️
