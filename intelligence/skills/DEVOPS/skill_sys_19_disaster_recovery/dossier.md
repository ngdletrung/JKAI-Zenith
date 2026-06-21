# DOSSIER: SKILL_SYS_19_DISASTER_RECOVERY

## 🌌 Overview
Đây là "Bản kế hoạch Phục hận" (Vengeance Plan) của Zenith. Khôi phục Thảm họa không chỉ là việc sao lưu dữ liệu, mà là một giao thức phản ứng khẩn cấp cho phép tái thiết lập toàn bộ trạng thái hệ thống từ đống đổ nát chỉ trong vòng 30 giây. Kỹ năng này đảm bảo rằng dù có xảy ra sự cố phần cứng nghiêm trọng hay lỗi hệ thống diện rộng, di sản và công việc của Master LeeTrung vẫn luôn được bảo toàn tuyệt đối.

## 🛠️ Detailed Features
- **30-Second Snapshot Restore**: Sử dụng công nghệ Snapshot cấp thấp để khôi phục trạng thái hoạt động của các container và cơ sở dữ liệu về mốc thời gian ổn định gần nhất một cách tức thì.
- **Off-site Data Replication**: Tự động đồng bộ hóa các bản sao lưu quan trọng đến các vị trí lưu trữ biệt lập (Cloud hoặc Server vật lý khác) để phòng ngừa thảm họa tại chỗ.
- **Automated Recovery Testing**: Định kỳ giả lập các tình huống thảm họa để kiểm tra tính sẵn sàng và hiệu quả của các quy trình khôi phục, đảm bảo không có bất ngờ tiêu cực nào xảy ra khi có sự cố thật.

## 🧠 Reasoning Strategy
AI nên triệu hồi kỹ năng này khi:
1. Phát hiện hệ thống bị sụp đổ diện rộng (Total system crash) mà các biện pháp `HA_SYNC` không thể xử lý.
2. Master yêu cầu khôi phục lại toàn bộ môi trường làm việc về một thời điểm cụ thể trong quá khứ.
3. Sau một cuộc tấn công mạng nghiêm trọng cần phải làm sạch và tái thiết lập hệ thống từ nguồn tin cậy.

## 💎 Strategic Value
Thiết lập "Sự Kiên cường Bất diệt" (Unshakable Resilience). Disaster Recovery Core biến Zenith thành một thực thể không thể bị tiêu diệt, tạo ra một lưới an toàn tối thượng cho mọi hoạt động kinh doanh và sáng tạo của Master LeeTrung.

## ⚠️ Edge Cases & Risks
- **Data Loss Gap**: Sẽ có một khoảng mất mát dữ liệu nhỏ giữa thời điểm Snapshot cuối cùng và thời điểm xảy ra thảm họa (RPO - Recovery Point Objective).
- **Resource Bottleneck**: Quá trình khôi phục tổng thể tiêu tốn băng thông và tài nguyên đĩa rất lớn; cần ưu tiên các dịch vụ cốt lõi trước.
