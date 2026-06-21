# DOSSIER: GITHUB_RELEASE_MANAGEMENT

## 🌌 Overview
Đây là "Nhà Điều phối Phát hành" (Release Orchestrator) của Zenith. Kỹ năng này chịu trách nhiệm cho giai đoạn cuối cùng của vòng đời phần mềm: đưa sản phẩm đến tay người dùng. Nó tự động hóa việc đánh số phiên bản, tạo bản ghi thay đổi (Changelog) và quản lý các tệp tin đính kèm (Assets) cho mỗi đợt phát hành trên GitHub.

## 🛠️ Detailed Features
- **Semantic Versioning Management**: Tự động hóa việc tăng số phiên bản (Major, Minor, Patch) dựa trên mức độ thay đổi của mã nguồn.
- **Automated Changelog Synthesis**: Phân tích các Commit và Pull Requests để tạo ra các bản báo cáo thay đổi chuyên nghiệp và dễ hiểu cho người dùng.
- **Release Asset Deployment**: Tự động đóng gói và đẩy các tệp tin thực thi, tài liệu hoặc các gói cài đặt lên trang Release của GitHub.
- **Tag & Branch Orchestration**: Đảm bảo các Tag và Release được gắn chính xác vào các nhánh mã nguồn ổn định nhất.

## 🧠 Reasoning Strategy
AI nên sử dụng kỹ năng này khi:
1. Dự án đã hoàn thành một cột mốc (Milestone) và sẵn sàng để phát hành phiên bản mới.
2. Cần tự động hóa quy trình cập nhật tài liệu thay đổi cho cộng đồng người dùng.
3. Muốn lưu trữ các bản build ổn định để phục vụ việc khôi phục (Rollback) khi cần thiết.

## 💎 Strategic Value
Hoàn thiện "Chu trình Giá trị" (Value Cycle) của Zenith. Khả năng quản lý phát hành chuyên nghiệp giúp nâng cao uy tín của dự án và đảm bảo rằng Master LeeTrung luôn có các phiên bản phần mềm được tổ chức một cách khoa học.

## ⚠️ Edge Cases & Risks
- **Versioning Conflicts**: Nếu quy trình đánh số phiên bản không nhất quán với các hệ thống bên ngoài, có thể gây ra nhầm lẫn cho người dùng.
- **Asset Integrity**: Các tệp tin đính kèm cần được kiểm tra tính toàn vẹn (Checksum) để đảm bảo không bị lỗi trong quá trình tải lên.
