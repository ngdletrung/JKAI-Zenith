# DOSSIER: WEB_PATHFINDER

## 🌌 Overview
Đây là "Hoa tiêu Kỹ thuật số" (Digital Navigator) của Zenith. Web Pathfinder chuyên trách việc tìm kiếm con đường ngắn nhất và hiệu quả nhất để đạt được một mục tiêu cụ thể trên bất kỳ trang web nào. Khác với việc duyệt web ngẫu nhiên, kỹ năng này sử dụng suy luận nơ-ron để "nhìn" và phân tích cấu trúc trang, từ đó đưa ra các quyết định tương tác (Click, Scroll, Form-filling) một cách có mục đích. Kỹ năng này đảm bảo Zenith luôn đạt được đích đến cuối cùng cho Master LeeTrung mà không bị lạc lối trong "mê cung" thông tin.

## 🛠️ Detailed Features
- **Semantic Pathfinding Protocol**: Sử dụng AI để đánh giá mức độ liên quan của các liên kết và nút bấm so với mục tiêu cuối cùng, ưu tiên những hành động có xác suất thành công cao nhất.
- **Goal-Oriented Interaction**: Tự động thực hiện các chuỗi hành động phức tạp (như điều hướng qua các trang con, xử lý menu đa cấp) cho đến khi đạt được mục tiêu hoặc chạm giới hạn bước đi.
- **Neural Reflection Loop**: Sau mỗi bước đi, AI sẽ tự soi chiếu và đánh giá lại tình hình để điều chỉnh chiến lược dẫn đường ngay lập tức.

## 🧠 Reasoning Strategy
AI nên triệu hồi kỹ năng này khi:
1. Cần thực hiện một quy trình nghiệp vụ trên web yêu cầu nhiều bước trung gian (như tìm kiếm sản phẩm -> thêm vào giỏ hàng -> tìm trang thanh toán).
2. Master yêu cầu lấy dữ liệu nằm sâu bên trong cấu trúc của một trang web phức tạp.
3. Cần tự động hóa các thao tác lặp đi lặp lại trên các giao diện web mà không có API chính thức.
4. Phối hợp với `STEALTH_WEB_NAVIGATOR` để dẫn đường trong môi trường ẩn danh.

## 💎 Strategic Value
Thiết lập "Sự Hiệu quả trong Điều hướng" (Navigation Efficiency). Web Pathfinder giúp Master LeeTrung tiết kiệm thời gian tối đa bằng cách giao phó những thao tác web tẻ nhạt và phức tạp cho AI, đảm bảo mọi nhiệm vụ thực địa đều được hoàn thành một cách chuẩn xác và thần tốc.

## ⚠️ Edge Cases & Risks
- **Dynamic Content Changes**: Các trang web thường xuyên thay đổi cấu trúc hoặc ID phần tử có thể làm "hoa tiêu" bị lạc; hệ thống đã tích hợp cơ chế dò đường linh hoạt dựa trên ngữ nghĩa thay vì selector cứng.
- **Infinite Loops**: Rủi ro khi AI bị xoay vòng giữa các trang tương tự; đã được giới hạn bởi thông số `max_steps` (mặc định là 5 bước) để đảm bảo an toàn tài nguyên.
