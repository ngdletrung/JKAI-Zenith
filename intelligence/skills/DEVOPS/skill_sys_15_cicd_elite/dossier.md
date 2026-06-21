# DOSSIER: SKILL_SYS_15_CICD_ELITE

## 🌌 Overview
Đây là "Băng chuyền Sản xuất" (Production Pipeline) của Zenith. CI/CD Elite đảm bảo rằng mọi thay đổi về mã nguồn của Master LeeTrung đều được kiểm thử, đóng gói và triển khai ra thực địa một cách an toàn và tự động. Kỹ năng này loại bỏ các sai sót do thao tác thủ công và rút ngắn thời gian từ ý tưởng đến sản phẩm thực tế (Time-to-market), duy trì một nhịp độ phát triển thần tốc cho Tập đoàn.

## 🛠️ Detailed Features
- **Automated Quality Gates**: Tự động chạy các bài kiểm thử (`TDD_ELITE`), quét lỗ hổng bảo mật và phân tích chất lượng code trước khi cho phép triển khai.
- **Canary & Blue-Green Deployment**: Hỗ trợ các chiến thuật triển khai nâng cao để giảm thiểu rủi ro, cho phép Master thử nghiệm tính năng mới trên một nhóm nhỏ người dùng trước khi phát hành toàn bộ.
- **Rollback Sovereignty**: Tự động khôi phục về phiên bản ổn định gần nhất nếu phát hiện lỗi nghiêm trọng sau khi triển khai, đảm bảo tính liên tục của dịch vụ.

## 🧠 Reasoning Strategy
AI nên triệu hồi kỹ năng này khi:
1. Master vừa hoàn thành việc chỉnh sửa mã nguồn và muốn cập nhật phiên bản mới lên server.
2. Cần thiết lập một quy trình làm việc chuyên nghiệp cho một dự án phần mềm mới.
3. Muốn kiểm soát chặt chẽ chất lượng đầu ra của mã nguồn thông qua các bước kiểm tra tự động.

## 💎 Strategic Value
Thiết lập "Vận tốc Phát triển Áp đảo" (Overwhelming Development Velocity). CI/CD Elite giúp Zenith luôn ở trạng thái cập nhật nhất, cho phép Master LeeTrung phản ứng tức thì với các thay đổi của thị trường hoặc yêu cầu kỹ thuật mới.

## ⚠️ Edge Cases & Risks
- **Pipeline Failure**: Nếu các bước kiểm thử quá khắt khe hoặc cấu hình môi trường sai, quá trình triển khai có thể bị kẹt; cần sự can thiệp của `SYSTEM_CORE_EXECUTOR`.
- **Credential Security**: Quá trình CI/CD yêu cầu truy cập vào các khóa bí mật (Secrets); cần được bảo vệ bởi các giao thức mã hóa cấp cao.
