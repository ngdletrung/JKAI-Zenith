# DOSSIER: SYSTEM_AUDITOR

## 🌌 Overview
Đây là "Thanh tra Chính phủ" (Regulatory Auditor) của Zenith. Nó chịu trách nhiệm giám sát tính tuân thủ của toàn bộ hệ thống đối với các tiêu chuẩn kiến trúc Z-SOS. Auditor đảm bảo rằng không có bất kỳ sai lệch nào giữa thực địa (File System) và lý thuyết (Registry/Map), giữ cho bộ máy Zenith luôn vận hành với kỷ luật cao nhất.

## 🛠️ Detailed Features
- **Registry Alignment Audit**:
  - Đối soát danh sách kỹ năng trong `registry_Map_skills.json` với thực tế thư mục `intelligence/skills`.
  - Phát hiện các kỹ năng "lậu" (có file nhưng không có trong registry) hoặc kỹ năng "rỗng" (có trong registry nhưng mất file).
- **Z-SOS Compliance Check**:
  - Rà soát từng kỹ năng để đảm bảo sự hiện diện đầy đủ của "Bộ tứ Quyền lực": `logic.py`, `SKILL.md`, `manifest.json`, và `dossier.md`.
  - Đánh giá chất lượng của các tệp Manifest và Dossier để đảm bảo chúng cung cấp đủ ngữ nghĩa cho Đặc vụ Dispatcher.
- **Automated Structural Repair**:
  - Có khả năng tự động sửa chữa các lỗi cấu trúc nhẹ như: Cập nhật lại đường dẫn sai, khôi phục các tệp manifest mặc định bị thiếu.
- **System Integrity Reporting**:
  - Xuất bản các báo cáo kiểm toán chi tiết, chỉ ra các "điểm mù" hoặc rủi ro trong kiến trúc hiện tại của dự án.

## 🧠 Reasoning Strategy
AI nên triệu hồi kỹ năng này khi:
1. Vừa thực hiện một cuộc đại tu lớn cho kho tri thức.
2. Hệ thống gặp các lỗi kỳ lạ liên quan đến việc triệu hồi kỹ năng.
3. Cần đảm bảo hệ thống đã sẵn sàng 100% trước khi bàn giao cho Master.
4. Muốn kiểm tra xem các Đặc vụ mới cài đặt có tuân thủ đúng giao thức của Zenith hay không.

## 💎 Strategic Value
Duy trì "Trật tự và Kỷ cương" (Order & Discipline) cho Zenith. Một hệ thống càng lớn càng dễ rơi vào trạng thái hỗn loạn (Entropy). `SYSTEM_AUDITOR` chính là công cụ chống lại sự hỗn loạn đó, giữ cho Zenith luôn sắc bén và tinh gọn.

## ⚠️ Edge Cases & Risks
- **Over-Correction**: Trong chế độ `fix_issues=True`, Auditor có thể tự ý thay đổi cấu hình mà Master đang thử nghiệm (Experimentation).
- **Read-Only Environments**: Nếu chạy trong môi trường bị giới hạn quyền ghi, Auditor sẽ chỉ báo cáo mà không thể sửa lỗi.
- **Registry Locking**: Quá trình kiểm toán sâu có thể tạm thời khóa Registry, gây trễ cho các tiến trình đồng bộ khác.
