<!-- 
[ZENITH FILE DIRECTIVE]
- File: SKILL.md
- Role: System Readiness Auditor (Pillar 1).
- Ownership: Mr LeeTrung
- Status: Active | Version: SDS v20.1
[WORKING PRINCIPLES]:
1. [DETERMINISTIC-AUDIT]: Kết quả kiểm toán phải dựa trên bằng chứng vật lý (File/Service).
2. [SCORE-DRIVEN]: Chấm điểm năng lực theo thang 100 để Master dễ dàng theo dõi.
3. [NO-EMOJI]: Cấm tuyệt đối emoji trong nội dung kỹ năng.
-->
# 🛡️ ZENITH HARNESS AUDIT (v1.0)
**"Trình kiểm toán Năng lực và Độ sẵn sàng của Hệ thống JKAI"**

Kỹ năng này thực hiện kiểm tra toàn diện 12 Chỉ mục Chủ quyền và các dịch vụ Docker để đảm bảo JKAI Zenith đang ở trạng thái hoạt động tối ưu.

## 🛠️ Khi nào sử dụng

- Khi Master yêu cầu kiểm tra sức khỏe hệ thống ("Check health", "Audit system").
- Trước khi thực hiện một nhiệm vụ phức tạp để đảm bảo đủ "vũ khí" (Skills/Tools).
- Sau khi cập nhật kiến trúc hoặc cài đặt nơ-ron mới.

## 📐 Tiêu chuẩn kiểm toán (Audit Rubric)

Hệ thống sẽ quét qua các hạng mục sau:
1. **Core Identity**: Kiểm tra sự tồn tại của 12 file DNA trong `/identity/`.
2. **Skill Coverage**: Đếm số lượng kỹ năng Elite và tính hợp lệ của Manifest.
3. **Service Health**: Kiểm tra tình trạng 18 dịch vụ Docker (N8N, Qdrant, Ollama, v.v.).
4. **Hardware Affinity**: Xác minh định tuyến CPU/GPU có khớp với `rule_hardware.md`.
5. **Security Gates**: Kiểm tra sự hiện diện của `ZENITH_SOVEREIGN_RULES.md`.

## 🚀 Lệnh thực thi

```powershell
# Chạy kiểm toán toàn diện
python core/utils/harness_audit.py --format text

# Xuất báo cáo JSON cho hệ thống
python core/utils/harness_audit.py --format json
```

## 📊 Thang điểm (Score Grading)
- **90-100 (Sovereign)**: Hệ thống hoàn hảo, sẵn sàng cho mọi nhiệm vụ.
- **70-89 (Operational)**: Hoạt động tốt, cần tối ưu hóa một số nơ-ron phụ.
- **<70 (Critical)**: Cảnh báo! Hệ thống đang mất kết nối nòng cốt.

---
*Sovereign Property of Master LeeTrung. Optimized for System Reliability.* 🛡️🏛️⚙️
