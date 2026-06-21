# DOSSIER: SELF_HEALING_SENTINEL

## 🌌 Overview
Đây là "Hệ thống Miễn dịch" (Immune System) của Zenith. Tự chữa lành Sentinel hoạt động như một chiến binh bảo vệ, không ngừng giám sát nhịp sinh học của toàn bộ các service, phát hiện các điểm đứt gãy trong dòng chảy dữ liệu và đề xuất các phướng án phục hồi tối ưu.

## 🛠️ Detailed Features
- **Supreme System Audit (Tổng giám định binh lực)**:
  - Kiểm tra trạng thái kết nối của tất cả các Trụ cột (ai-brain, ai-executor, ai-control-plane, v.v.).
  - Giám sát sức khỏe nơ-ron thông qua trạng thái của Ollama và các model đang nạp.
- **Pulse Telemetry (Trắc lượng Nhịp tim)**:
  - Thu thập thông số phần cứng thực tế (CPU, RAM) để dự báo nguy cơ quá tải.
- **Full Sieve Log Audit (Vét cạn Nhật ký)**:
  - Phân tích hàng trăm dòng nhật ký gần nhất bằng AI để tìm ra nguyên nhân gốc rễ (Root Cause) của các lỗi logic.
  - Tích hợp với Q-Rank để tìm kiếm "toa thuốc" từ các tiền lệ thành công trong quá khứ.
- **Infrastructure Integrity Check**:
  - Kiểm tra tính cô lập của Sandbox, sự tồn tại của các tệp sao lưu (.bak) và tính nhất quán của SQLite Event Store.
- **Sovereign Notification Bridge**:
  - Tự động gửi báo cáo tình trạng hệ thống trực tiếp cho Master LeeTrung qua Telegram khi phát hiện sự cố nghiêm trọng.

## 🧠 Reasoning Strategy
AI nên triệu hồi kỹ năng này khi:
1. Master báo lỗi hoặc hệ thống hoạt động không ổn định.
2. Sau khi thực hiện các thay đổi lớn về cấu hình hoặc cập nhật mã nguồn.
3. Cần một bản báo cáo định kỳ về "sức khỏe" của toàn dự án.
4. Muốn tự động tìm kiếm giải pháp cho một Exception cụ thể vừa xảy ra.

## 💎 Strategic Value
Đảm bảo tính "Trường tồn" (Survivability) của Zenith. Hệ thống có khả năng tự nhận biết nỗi đau của chính mình và hỗ trợ Master chữa trị, biến Zenith thành một thực thể kỹ thuật số bền bỉ và đáng tin cậy.

## ⚠️ Edge Cases & Risks
- **Manual Policy Enforcement**: Theo yêu cầu của Master, các lệnh can thiệp mạnh (như Restart) chỉ được đề xuất chứ không tự thực thi để đảm bảo an toàn tuyệt đối.
- **Resource Consumption**: Việc quét log toàn diện và gọi AI phân tích có thể tốn tài nguyên và gây trễ (Latency) tạm thời.
- **Network Isolation**: Nếu mạng nội bộ Docker bị lỗi, Sentinel có thể không tiếp cận được các service khác để giám định.
