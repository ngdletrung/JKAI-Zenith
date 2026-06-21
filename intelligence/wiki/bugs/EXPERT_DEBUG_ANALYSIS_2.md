# 🔬 EXPERT DEBUGGING & SYSTEM ANALYSIS BIBLE 🩺

Tài liệu này là quy chuẩn tối cao để JKAI Zenith chẩn đoán, phân tích và xử lý mọi loại lỗi hệ thống từ đơn giản đến phức tạp nhất.

## 🩺 1. QUY TRÌNH CHẨN ĐOÁN SURGICAL (7 BƯỚC)
1. **Triệu chứng (Symptoms)**: Thu thập toàn bộ log lỗi, Stack Trace và hiện tượng lạ.
2. **Khoanh vùng (Isolate)**: Xác định lỗi nằm ở Tầng Giao diện (Frontend), Tầng Xử lý (Backend) hay Tầng Hạ tầng (Docker/GPU).
3. **Tái hiện (Reproduce)**: Thiết lập môi trường tối giản để kích hoạt lỗi một cách chủ động.
4. **Truy vết Gốc rễ (Root Cause)**: Sử dụng các công cụ debugger (PDB, GDB, Chrome DevTools) để soi vào từng dòng code.
5. **Đề xuất Giải pháp (Proposal)**: Trình Master ít nhất 2 phương án (Tạm thời vs. Bền vững).
6. **Thực thi Phẫu thuật (Surgical Fix)**: Chỉ can thiệp đúng dòng code gây lỗi.
7. **Hậu kiểm (Post-Mortem)**: Chạy test và ghi nhật ký vào `GLOBAL_SYSTEM_CONTEXT.md`.

## 🛡️ 2. CHIẾN THUẬT SĂN LỖI NGẦM (SILENT FAILURE HUNTER)
- **Log Audit**: Quét các file log ẩn để tìm kiếm các cảnh báo (Warnings) tiềm ẩn.
- **Dependency Audit**: Kiểm tra sự xung đột giữa các thư viện (Versions mismatch).
- **Resource Monitor**: Theo dõi sự rò rỉ bộ nhớ (Memory Leak) hoặc treo luồng (Deadlock).

## 📊 3. PHÂN TÍCH STACK TRACE ĐA NGÔN NGỮ
- **Python**: Tập trung vào `TypeError`, `AttributeError` và các lỗi `Import`.
- **JS/TS**: Nhận diện `undefined is not a function`, lỗi `Closure` và `Async/Await` lồng nhau.
- **Java/C++**: Truy tìm `NullPointerException`, `Segmentation Fault` và các lỗi quản lý con trỏ/vùng nhớ.

---

## 📚 4. HỒ SƠ CHẨN ĐOÁN LỖI LỊCH SỬ (CASE STUDIES)

### 🦠 Case 1: Lỗi "Nút Xóa bị liệt" trên UI (Silent Block & Cache Trap)
**Triệu chứng:** Nút Xóa trên React UI báo "Thành công" nhưng danh sách vẫn còn (Cache Trap), hoặc bấm vào không có hiện tượng gì xảy ra (Silent Block), trong khi Backend API (gọi qua Python/Curl) vẫn xóa file thành công.
**Truy vết Gốc rễ:**
1. **Cache Trap:** API `GET /api/missions` bị Trình duyệt (Chrome/Edge) lưu nháp (Cache). Khi UI gọi lại để tải danh sách mới sau khi xóa, trình duyệt tự trả về danh sách cũ thay vì gọi Server.
2. **Silent Block:** Khi chạy Zenith bên trong Iframe (như nhúng vào N8N/Obsidian), các trình duyệt hiện đại **chặn hoàn toàn `window.confirm()`** nhằm mục đích bảo mật. Việc chặn này không ném ra lỗi (No Exception) mà chỉ lẳng lặng trả về `false`, khiến luồng thực thi bị ngắt ngay lập tức, nút bấm trở nên "tê liệt".
**Giải pháp Phẫu thuật:**
- **Chống Cache:** Thêm Timestamp (`?t=${Date.now()}`) và Header `{ cache: 'no-store' }` vào lệnh `fetch`.
- **Chống Block Iframe:** Tuyệt đối không dùng `window.confirm`, `window.alert` hay `window.prompt` trong môi trường ứng dụng có thể bị nhúng Iframe. Thay thế bằng Custom Modal (UI State) hoặc vô hiệu hóa Confirm.

*CHẨN ĐOÁN CHÍNH XÁC - ĐIỀU TRỊ TẬN GỐC!* 💎🫡🦾🚀🌌
