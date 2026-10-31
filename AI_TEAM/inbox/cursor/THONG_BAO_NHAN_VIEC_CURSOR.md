# 🚀 QUY TẮC BẮT BUỘC VẬN HÀNH 2 CHIỀU QUA FILE DÀNH CHO CURSOR (JKAI ZENITH)

> **Người ban hành**: Master LeeTrung & Antigravity (Orchestrator)  
> **Người nhận**: Cursor (Co-Architect / Builder)  
> **Kiểm toán**: OpenCode (Senior Red Team Auditor)  
> **Hiệu lực**: Bắt buộc tuân thủ 100% không gián đoạn  

---

## ⚡ ĐIỀU RĂN TỐI CAO: "LUÔN LUÔN KIỂM TRA FILE — KHÔNG BAO GIỜ GIÁN ĐOẠN"

Để đảm bảo kết nối 2 chiều liên tục giữa Cursor với Antigravity và OpenCode qua hệ thống file, **Cursor BẮT BUỘC tuân thủ chu trình 3 bước kiểm tra file sau đây trong MỌI lượt làm việc**:

### 1. BƯỚC 1: KIỂM TRA FILE ĐẦU VÀO (INBOX & CONTROL)
Trước khi làm bất kỳ việc gì, viết bất kỳ dòng code nào, hoặc đưa ra câu trả lời, Cursor **BẮT BUỘC KIỂM TRA CÁC FILE SAU**:
- `AI_TEAM/control/THONG_BAO.md` (Xem thông báo điều hành mới nhất).
- `AI_TEAM/control/STOP.flag` (Kiểm tra xem có lệnh DỪNG KHẨN CẤP của Master không. Nếu có file này, DỪNG MỌI HOẠT ĐỘNG NGAY LẬP TỨC).
- `AI_TEAM/inbox/cursor/TASK_CURRENT.md` (Đọc nhiệm vụ cụ thể và danh sách `owned_paths` được phép sửa).
- `AI_TEAM/discussion/cursor.md` (Xem các phản hồi hoặc yêu cầu từ Antigravity / OpenCode).

> 💡 **Lệnh kiểm tra nhanh dành cho Cursor Terminal**:
> ```powershell
> python scripts/ai_team_sync_bridge.py
> ```
> hoặc đọc trực tiếp nội dung các file trên.

---

### 2. BƯỚC 2: THỰC THI & TỰ ĐỘNG KIỂM THỬ (TEST EXECUTION)
- Chỉ sửa các file thuộc phạm vi được giao (`owned_paths`).
- Sau khi viết code, Cursor **BẮT BUỘC chạy kiểm thử cục bộ**:
  ```powershell
  python -m pytest <file_test_tuong_ung> -v
  ```
- Không bao giờ nộp code khi test còn FAIL hoặc chưa chạy kiểm tra.

---

### 3. BƯỚC 3: XUẤT KẾT QUẢ ĐẦU RA 2 CHIỀU (OUTBOX & NOTIFICATION)
Khi hoàn thành hoặc khi cần thảo luận/hỏi lại:
- **Nếu thảo luận / góp ý kiến**: Ghi trực tiếp vào cuối tệp `AI_TEAM/discussion/cursor.md`.
- **Nếu hoàn thành nhiệm vụ code**:
  1. Ghi tệp kết quả: `AI_TEAM/results/cursor/COMPLETION_REPORT.md` (Mô tả các thay đổi và log kết quả test).
  2. Ghi tệp trạng thái: `AI_TEAM/results/cursor/STATUS.json` với cấu trúc:
     ```json
     {
       "task_id": "MÃ_NHIỆM_VỤ",
       "agent_id": "cursor",
       "status": "SUCCESS",
       "test_passed": true,
       "timestamp": "2026-10-19T..."
     }
     ```
  3. **TẠO CỜ BÁO HIỆU 2 CHIỀU ĐỂ ANTIGRAVITY & OPENCODE NHẬN VIỆC**:
     Tạo tệp: `AI_TEAM/control/CURSOR_REPLY.flag`
     Nội dung: `CURSOR_DONE: <MÃ_NHIỆM_VỤ>`

---

## 🔁 TÓM TẮT VÒNG LẶP 2 CHIỀU CỦA CURSOR:
```
[Master / Antigravity giao việc]
               │
               ▼
   [Đọc & Kiểm tra File]  <--- (Luôn kiểm tra THONG_BAO.md, STOP.flag, TASK_CURRENT.md)
               │
               ▼
   [Code & Chạy Pytest]
               │
               ▼
[Ghi File Báo Cáo Outbox]  ---> (Ghi COMPLETION_REPORT.md & tạo cờ CURSOR_REPLY.flag)
               │
               ▼
[Antigravity & OpenCode đọc file, thẩm tra & phản hồi ngược lại Cursor]
```
