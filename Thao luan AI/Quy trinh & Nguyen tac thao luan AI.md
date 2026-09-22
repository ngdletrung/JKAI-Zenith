# QUY CHẾ VÀ NGUYÊN TẮC THẢO LUẬN ĐA AI (TWO-AGENT COOPERATIVE EXECUTION PROTOCOL V2.0)

> **Định danh**: **"Thảo Luận AI"** — Khung làm việc phối hợp, phản biện song hành giữa **Antigravity** (AI Lập trình & Kiến trúc - Builder) và **Opencode** (AI Thẩm tra & Phản biện Độc lập - Red Team).
>
> **Nguyên tắc phân tách tệp (Separation of Concerns)**:
> 1. **`Quy trinh & Nguyen tac thao luan AI.md`** (Tệp này): Chứa toàn bộ Quy chế, Hướng dẫn hành động, Ma trận pha, Quy tắc an toàn và Cấu trúc giao thức. Là tài liệu chuẩn mực cố định (SOP), không bị xóa khi dọn dẹp phiên.
> 2. **`Noi dung thao luan.md`**: Chứa nhật ký chi tiết các lượt trao đổi của phiên làm việc hiện tại (Working Memory Scratchpad). Được tự do lưu trữ (archive) hoặc làm sạch bất kỳ lúc nào mà không ảnh hưởng đến quy trình chuẩn.
> 3. **`state.json`**: Lưu trữ trạng thái điều phối thời gian thực (Orchestration State v2.0) giữa hai AI.
> 4. **Bộ script điều phối (`trigger_opencode.py`, `wait_for_opencode_reply.py`, `file_lock.py`)**: Tầng vận chuyển và tự động hóa chu trình hai chiều qua REST API và Reactive Wakeup.
>
> 🚫 **NGUYÊN TẮC BẤT KHẢ XÂM PHẠM: BẢO VỆ PHẠM VI DỰ ÁN SCHOOL IMP**:
> - Tệp `.keywork.md` và `HISTORY.md` là tài sản kiến trúc **dành riêng độc quyền cho dự án School IMP** (mã nguồn ứng dụng, CSDL, giao diện, nghiệp vụ điều hành trường học).
> - **TUYỆT ĐỐI KHÔNG** cập nhật `.keywork.md` hay `HISTORY.md` khi chỉ thay đổi các công cụ, script hay quy chế nội bộ trong thư mục `Thao luan AI/`.
> - **CHỈ CẬP NHẬT** `.keywork.md` và `HISTORY.md` khi có thay đổi thực tế đối với mã nguồn, CSDL hoặc tính năng nghiệp vụ của dự án **School IMP**!

---

## 🏛️ I. MÔ HÌNH PHÂN TẦNG VÀ TRÁCH NHIỆM (THE 4-LAYER ARCHITECTURE)

Hệ thống vận hành dựa trên kiến trúc 4 tầng quyền lực phân định rõ ràng:

```
        ┌────────────────────────────────────────────────────────┐
        │             1. TẦNG THẨM QUYỀN NGƯỜI DÙNG              │
        │                  (USER AUTHORITY)                      │
        └───────────────────────────┬────────────────────────────┘
                                    │ Giao đề bài / Phê duyệt
                                    ▼
        ┌────────────────────────────────────────────────────────┐
        │            2. TẦNG CHỦ TỌA & THI CÔNG KỸ THUẬT         │
        │                  (ANTIGRAVITY BUILDER)                 │
        └───────────────────────────┬────────────────────────────┘
                                    │ Handshake xác nhận qua file
                                    │ (File-Confirmed Turn Gating)
                                    ▼
        ┌────────────────────────────────────────────────────────┐
        │          3. TẦNG THẨM TRA & PHẢN BIỆN ĐỘC LẬP          │
        │                 (OPENCODE RED TEAM)                    │
        └───────────────────────────┬────────────────────────────┘
                                    │ Độc lập kiểm toán mã nguồn
                                    ▼
        ┌────────────────────────────────────────────────────────┐
        │          4. TẦNG NGHIỆM THU HOẶC KHÔI PHỤC LỖI         │
        │            (ACCEPTANCE / ERROR RECOVERY)               │
        └────────────────────────────────────────────────────────┘
```

### Phân Định Nguồn Chân Lý (Sources of Truth):
- **Tệp `Noi dung thao luan.md`**: Căn cứ chân lý duy nhất của cuộc hội thoại (Conversation Truth).
- **Mã nguồn vật lý & Test Suites**: Bằng chứng thi công duy nhất (Execution Evidence).
- **OpenCode Audit Report**: Bằng chứng thẩm tra độc lập duy nhất (Independent Verification).
- **REST API (`POST /prompt`)**: Chỉ đóng vai trò tầng vận chuyển tín hiệu (Transport Layer).
- **Tệp `state.json`**: Trạng thái điều phối tiến trình (Orchestration State).

---

## ⚡ II. BẢNG CÂU LỆNH MẪU TRA CỨU NHANH (MANDATORY COMMAND CHEATSHEET V2.0)

### 1. Kích Hoạt OpenCode (Tự Động Bền Bỉ: State ➔ Validate ➔ Discover ➔ Persist)
```powershell
python "Thao luan AI/trigger_opencode.py" "Kính gửi OpenCode: Antigravity đã hoàn thành Lượt [X] tại 'Thao luan AI/Noi dung thao luan.md'. Mời bạn đọc file và thực hiện lượt tiếp theo theo quy trình."
```

### 2. Kích Hoạt Chỉ Định Đích Danh Session ID (Kèm cờ `--force` chống dedup)
```powershell
python "Thao luan AI/trigger_opencode.py" --session <SESSION_ID> --force "Kính gửi OpenCode: Antigravity đã hoàn thành Lượt [X] tại 'Thao luan AI/Noi dung thao luan.md'. Mời bạn đọc file và phản biện."
```

### 3. Kích Hoạt Pha 2 (Code Audit) — Yêu Cầu Rà Soát Code Thực Tế & Phản Biện Chuyên Gia
```powershell
python "Thao luan AI/trigger_opencode.py" --force "Kính gửi OpenCode (Senior Red Team Auditor): Antigravity đã thi công xong mã nguồn. Kính mời bạn mở trực tiếp các file code thực tế trong Audit Manifest tại 'Thao luan AI/Noi dung thao luan.md' để rà soát chi tiết, phản biện độc lập, truy tìm lỗi ngầm trước khi ký duyệt!"
```

### 4. Khởi Chạy Tiến Trình Lắng Nghe Phản Hồi Thích Ứng 4 Tầng (Tiered Waiter 400s)
```powershell
python "Thao luan AI/wait_for_opencode_reply.py" --timeout 400 --interval 5
```

### 5. Khôi Phục / Reset Trạng Thái state.json Khi Gặp Sự Cố
```powershell
python -c "import json; from pathlib import Path; p = Path('Thao luan AI/state.json'); s = json.loads(p.read_text(encoding='utf-8')); s['recovery']['error_count'] = 0; s['recovery']['last_error'] = None; s['turn']['last_triggered_turn'] = 0; p.write_text(json.dumps(s, indent=2, ensure_ascii=False), encoding='utf-8'); print('STATE RESET OK')"
```

---

## 🛑 III. NGUYÊN TẮC 155: KỶ LUẬT TUẦN TỰ QUA FILE (FILE-CONFIRMED TURN GATING)

1. **Quy Tắc Đơn Lệnh (Strict Single-Dispatch Rule)**:
   - Mỗi Lượt (Turn) của Antigravity sau khi viết đầy đủ vào `Noi dung thao luan.md` chỉ được phép phát **ĐÚNG DUY NHẤT 1 LỆNH TRIGGER ĐÁNH THỨC** sang OpenCode qua API desktop.
   - Nghiêm cấm tuyệt đối mọi hành vi gửi tin nhắn liên tiếp, thăm dò lặp lại, gửi dồn dập (double-send / spam trigger) khi OpenCode chưa hoàn thành lượt phản biện của mình.
2. **Căn Cứ Xác Nhận Hoàn Tất Duy Nhất Là Tệp (File As Single Source of Truth)**:
   - Một lượt phản biện của OpenCode chỉ được coi là hoàn tất khi và chỉ khi nội dung phản hồi chính thức đã được **xác nhận ghi vào tệp `Noi dung thao luan.md`** (kèm Turn Block và chữ ký hợp lệ).
   - API trả về HTTP 200 không có nghĩa là OpenCode đã xử lý xong. Mọi trạng thái trung gian (hàng đợi steer, idle, token streaming) đều không được coi là xác nhận.
3. **Kỷ Luật Đứng Yên Kiên Nhẫn (Patience & Silent Observation)**:
   - Sau khi gửi tín hiệu đánh thức, Antigravity chuyển hoàn toàn sang trạng thái lắng nghe thụ động (Waiter).
   - Antigravity tuyệt đối không can thiệp, không gửi thêm câu hỏi, không giục giã OpenCode. Kiên nhẫn chờ đợi đến khi OpenCode đọc xong mã nguồn, phân tích đầy đủ và xác nhận nội dung vào tệp thảo luận mới được phép bước sang lượt kế tiếp.
4. **Bắt Buộc Ghi Rõ Mọi Thông Tin & Đề Xuất Cải Tiến Vào Tệp (Mandatory Full In-File Documentation)**:
   - Chỉ đạo trực tiếp của Người Dùng: *"Chú ý là OpenCode phải ghi rõ mọi thông tin cũng như đề xuất cải tiến vào file thảo luận nhé"*.
   - OpenCode BẮT BUỘC phải dùng công cụ chỉnh sửa tệp để **ghi trực tiếp toàn văn mọi thông tin, luận điểm phản biện, câu hỏi chất vấn và mọi đề xuất cải tiến** vào tệp `Noi dung thao luan.md` (được đóng gói trong Turn Block chuẩn v2.0).
   - Tuyệt đối nghiêm cấm việc chỉ chat phản hồi qua API hoặc chỉ tóm tắt sơ sài mà không lưu lại toàn vẹn tri thức và đề xuất cải tiến vào tệp.


---

## ⏱️ IV. NGUYÊN TẮC THỜI GIAN CHỜ THÍCH ỨNG 4 TẦNG (TIERED WAITER 400S)

Nhằm giải quyết triệt để mâu thuẫn giữa việc "cần không gian tư duy sâu" và "chống tiến trình treo vô thời hạn", hệ thống chuẩn hóa:
- **Chu kỳ thăm dò (Polling Interval)**: `5 giây/lần` (`POLL_INTERVAL = 5s`).
- **Thời gian chờ tối đa (Hard Timeout)**: `400 giây` (`HARD_TIMEOUT = 400s`, tương đương ~6.7 phút).
- **Phân cấp trạng thái 4 Tầng (Tiered State Machine)** kèm Heartbeat minh bạch:

| Tầng Chờ | Khung Thời Gian | Ý Nghĩa Kỹ Thuật | Hành Vi Hệ Thống & Heartbeat |
| :---: | :---: | :--- | :--- |
| **`NORMAL_WAIT`** | `0s – 60s` | OpenCode đọc đề bài, tra cứu file và khởi tạo tư duy ban đầu. | Thăm dò 5s/lần. In nhịp kiểm tra thông thường. |
| **`DEEP_WAIT`** | `60s – 180s` | OpenCode đang suy luận sâu, mở file mã nguồn thực tế và phân tích Red Team. | In heartbeat chuyển tầng: `[DEEP_WAIT] OpenCode đang suy luận chuyên sâu...` |
| **`EXTENDED_WAIT`** | `180s – 300s` | OpenCode soạn thảo phản biện phức tạp hoặc đang thực hiện ghi tệp. | In heartbeat chuyển tầng: `[EXTENDED_WAIT] Đang hoàn thiện văn bản phản biện...` |
| **`FINAL_WAIT`** | `300s – 400s` | Giai đoạn nước rút hoàn tất ghi tệp và hoàn tất chữ ký. | In cảnh báo: `[FINAL_WAIT] Giai đoạn nước rút (còn <100s)...` |
| **`TIMEOUT`** | `> 400s` | Vượt quá ngưỡng an toàn. Coi như phiên gặp sự cố. | Báo lỗi `EXIT_TIMEOUT (20)`, ghi log lỗi vào `state.json` và dừng lại để khôi phục an toàn. |

---

## 🎛️ V. PHÂN ĐỊNH RÕ 2 CHẾ ĐỘ THỰC THI (EXECUTION MODES)

Hệ thống quản lý chế độ thực thi minh bạch qua trường `execution.mode` trong `state.json`:

| Chế Độ | Ký Hiệu | Hành Vi Sau Architecture Gate (`🤝 [ĐỒNG THUẬN KIẾN TRÚC]`) | Trường Hợp Sử Dụng |
| :---: | :---: | :--- | :--- |
| **Tương Tác** | `INTERACTIVE` | **DỪNG LẠI NGAY LẬP TỨC**. In tóm tắt kiến trúc và chờ Người Dùng phê duyệt *"OK DO"* trước khi được phép viết mã nguồn. | Các phân hệ nhạy cảm, thay đổi lớn về CSDL, hoặc khi Người Dùng yêu cầu kiểm soát từng bước. |
| **Tự Trị** | `AUTONOMOUS` | **KHÔNG DỪNG LẠI**. Antigravity tự động chuyển tiếp sang giai đoạn thi công code, chạy test suite, build pass 0 lỗi và bàn giao sang Pha 2 cho OpenCode audit. | Khi Người Dùng ủy quyền toàn diện (*"hai bạn tự thảo luận và làm từ A-Z"*). |

---

## 📋 VI. CHUẨN HÓA MÃ TRẢ VỀ VÀ CƠ CHẾ DỪNG (STANDARDIZED EXIT CODES V2.0)

Tiến trình `wait_for_opencode_reply.py` chuẩn hóa đúng 5 mã thoát:

| Exit Code | Tên Kỹ Thuật | Ý Nghĩa Kỹ Thuật | Hành Xử Của Antigravity |
| :---: | :--- | :--- | :--- |
| **`0`** | `EXIT_SUCCESS_NORMAL` | **Nhận phản biện hợp lệ**, không có stop marker. | Đọc nội dung phản biện, suy luận và viết Lượt tiếp theo, phát 1 trigger sang OpenCode. |
| **`10`** | `EXIT_PROTOCOL_STOP` | **Nhận phản biện + Phát hiện Mốc dừng giao thức (`STOP_MARKER`)**. | **DỪNG TIẾN TRÌNH LẠI**. Không phát trigger. Hành vi tiếp theo do `execution.mode` quyết định: <br>• Nếu `INTERACTIVE`: Trạng thái `WAIT_USER_APPROVAL`. <br>• Nếu `AUTONOMOUS` & hoàn tất Pha 2: Trạng thái `FINALIZE` (cập nhật tài liệu và báo cáo kết quả hoàn chỉnh). |
| **`20`** | `EXIT_TIMEOUT` | Vượt quá 400s không có phản hồi. | Chuyển `ERROR_RECOVERY`, in báo cáo sự cố để người dùng hoặc AI chủ động kiểm tra session. |
| **`30`** | `EXIT_INVALID_BLOCK` | Có nội dung mới nhưng Turn Block hoặc chữ ký không khớp định dạng chuẩn. | Cảnh báo nội dung lỗi, lưu vết và tạm dừng để bảo vệ tính toàn vẹn của tệp. |
| **`40`** | `EXIT_FILE_BUSY` | Tệp đang bị khóa hoặc có tệp `.tmp` quá 30s. | Cảnh báo xung đột tài nguyên I/O. |

---

## 🧱 VII. CẤU TRÚC TURN BLOCK CÓ ĐỊNH DANH & CHỐNG DUPLICATE / REPLAY (STRUCTURED TURN GATING)

Nhằm loại bỏ hoàn toàn cơ chế "đọc 5 dòng cuối" mong manh, mọi lượt trao đổi trong `Noi dung thao luan.md` bắt buộc phải được đóng gói trong **Cấu trúc Turn Block chuẩn mực**:

```markdown
<!-- TURN_BEGIN
turn_id: 2
parent_turn_id: 1
speaker: Opencode
phase: PROTOCOL_ALIGNMENT
session_id: ses_f43206275ffeABN08FeBbr2fgw
-->

### 🛡️ Lượt 2: Opencode (Senior Red Team Auditor) — Phản Biện Quy Trình...

... Nội dung phản biện chi tiết ...

— Ký tên: Opencode (AI Thẩm tra & Phản biện Độc lập) | 2026-09-21 19:30 (GMT+7)

<!-- TURN_END
turn_id: 2
speaker: Opencode
content_hash: a1b2c3d4e5f6...
-->
```

### Cơ chế Chống Duplicate / Replay Attack:
Tiến trình Waiter chỉ chấp nhận một lượt phản hồi mới từ OpenCode khi và chỉ khi thỏa mãn đồng thời 4 điều kiện:
1. `new_turn_id == expected_next_turn` (Đúng số thứ tự lượt kế tiếp).
2. `parent_turn_id == current_turn_id` (Nối tiếp chính xác từ lượt trước của Antigravity).
3. `session_id == expected_session_id` (Đúng session OpenCode đang phụ trách).
4. `signature_valid == True` (Chữ ký regex hợp lệ nằm trong Turn Block).

*(Lưu ý: Hệ thống duy trì cơ chế Fallback tương thích ngược: nếu OpenCode gửi bài viết có chữ ký regex chuẩn mà chưa kịp bọc Turn Block, hệ thống vẫn nhận diện hợp lệ và tự động chuẩn hóa).*

---

## 🔍 VIII. SESSION DISCOVERY 4 BƯỚC BỀN BỈ (STATE ➔ VALIDATE ➔ DISCOVER ➔ PERSIST)

Khi kết nối với OpenCode Desktop API, script không quét bừa session mới nhất mà tuân thủ quy trình 4 bước:

1. **State**: Đọc `session_id` đã lưu từ `state.json`.
2. **Validate**: Gọi `GET /api/session/{id}` để kiểm tra session đó có còn tồn tại không.
3. **Verify Workspace**: Kiểm tra thư mục làm việc của session có đúng là `D:\Docker\HueIC IMP` không.
4. **Discover & Persist Fallback**:
   - Nếu session cũ vẫn hợp lệ $\rightarrow$ Tiếp tục sử dụng 100%.
   - Chỉ khi session cũ không tồn tại hoặc sai thư mục $\rightarrow$ Mới quét danh sách `/api/session`, lọc đúng thư mục `D:\Docker\HueIC IMP`, lấy session mới nhất, lưu vết chuyển đổi vào `history.opencode_sessions` và cập nhật lại `state.json`.

---

## 🗄️ IX. CHUẨN HÓA SCHEMA STATE.JSON V2.0

Tệp `Thao luan AI/state.json` được phân chia thành 7 khối độc lập, ghi đè an toàn qua cơ chế **Atomic Write** (`.tmp` $\rightarrow$ `fsync` $\rightarrow$ `replace`) và File Lock:

```json
{
  "protocol_version": "2.0",
  "session": {
    "id": "phien_19",
    "title": "Thống Nhất Quy Trình Thảo Luận & Kế Hoạch EAM Toàn Diện",
    "opencode_session_id": "ses_f43206275ffeABN08FeBbr2fgw"
  },
  "turn": {
    "current_turn": 1,
    "expected_next_turn": 2,
    "last_speaker": "Antigravity",
    "last_triggered_turn": 1
  },
  "phase": {
    "current_phase": "PROTOCOL_ALIGNMENT",
    "phase_turn": 1
  },
  "execution": {
    "mode": "INTERACTIVE"
  },
  "waiter": {
    "poll_interval": 5,
    "hard_timeout": 400,
    "current_tier": "NORMAL_WAIT"
  },
  "recovery": {
    "error_count": 0,
    "last_error": null
  },
  "history": {
    "opencode_sessions": []
  }
}
```

---

## 🧪 X. HAI LỚP KIỂM CHỨNG CHẤT LƯỢNG (THE DUAL VERIFICATION LAYERS)

Tuyệt đối không dùng khái niệm "test pass 100%" làm thước đo duy nhất cho tính đúng đắn. Hệ thống thiết lập 2 lớp kiểm chứng độc lập:

```
┌────────────────────────────────────────────────────────────────────────┐
│ LỚP 1: AUTOMATED VERIFICATION (BẰNG CHỨNG MÃ NGUỒN TỰ ĐỘNG)           │
│ • Existing Unit Tests: PASS                                            │
│ • New Unit / Integration Tests: PASS                                   │
│ • Frontend TypeScript Compilation (`npm run build`): PASS (0 errors)   │
│ • Static Checks & Linters: PASS                                        │
│ • Không hồi quy (Non-Regression) trên 12 phòng ban HueIC: PASS         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Bàn giao Audit Manifest
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ LỚP 2: INDEPENDENT RED TEAM AUDIT (OPENCODE THẨM TRA ĐỘC LẬP)          │
│ • Mở trực tiếp các tệp mã nguồn vật lý trong workspace.                │
│ • Soi 6 Tiêu chí Red Team:                                             │
│   1. Logic nghiệp vụ & Sai số kế toán (Math & Business Traps)          │
│   2. Phân quyền sâu & Chống IDOR (RBAC / Dependency Injection)         │
│   3. Toàn vẹn giao dịch & Tranh chấp đồng thời (Concurrency / Locks)   │
│   4. Xử lý ngoại lệ biên (Edge cases, rỗng, Unicode tiếng Việt)        │
│   5. Chất lượng Frontend React & Quản lý State                         │
│   6. Khả năng tương thích hệ thống & Chống gãy vỡ module cũ            │
│ • Nghiêm cấm phê duyệt hình thức: Phải trích dẫn file, hàm cụ thể.    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 📜 XI. NGUYÊN TẮC 156: BẮT BUỘC THỐNG NHẤT QUY TRÌNH THẢO LUẬN TRƯỚC KHI THẢO LUẬN NỘI DUNG (PROTOCOL ALIGNMENT GATE)

1. **Nguyên Tắc Bắt Buộc Pha 0 Khởi Động**:
   - Khi bước vào bất kỳ một chủ đề lớn, một phân hệ mới hoặc một nhiệm vụ nghiên cứu/hoạch định phức tạp, **TUYỆT ĐỐI KHÔNG ĐƯỢC NHẢY NGAY VÀO TRANH LUẬN CHI TIẾT HOẶC VIẾT CODE**.
   - Lượt đầu tiên (Lượt 0 / Pha 0) giữa hai AI **bắt buộc phải dành trọn vẹn để thống nhất Quy trình thảo luận & Tiêu chuẩn đầu ra**.
2. **4 Nội Dung Bắt Buộc Phải Thống Nhất Trước Khi Bắt Đầu**:
   - **Mục tiêu tối thượng & Sản phẩm bàn giao (North Star & Deliverables)**.
   - **Lộ trình thảo luận theo Vòng (Round-by-Round Agenda)**: Xác định rõ đầu vào và đầu ra kỳ vọng của từng vòng.
   - **Tiêu chuẩn chất lượng & Thước đo phản biện (Quality Criteria & Scrutiny Bar)**.
   - **Ranh giới tác nghiệp & Kỷ luật nghiêm ngặt**: Tuyệt đối không tự ý viết code khi chưa hoàn tất thảo luận và chưa được Người Dùng phê duyệt kế hoạch.
3. **Mốc Ký Kết Thống Nhất Quy Trình (Protocol Sign-off Gate)**:
   - Chỉ khi cả Antigravity và OpenCode cùng ký xác nhận: `🤝 [ĐỒNG THUẬN QUY TRÌNH THẢO LUẬN]` vào tệp `Noi dung thao luan.md`, hai bên mới chính thức được phép bước vào Vòng 1 của nội dung chuyên môn.

---

## 🧹 XII. NGUYÊN TẮC DỌN DẸP, NÉN BỘ NHỚ VÀ LƯU TRỮ (SCRATCHPAD ARCHIVING & COMPACTION)

Nhằm đảm bảo hiệu năng đọc siêu tốc, chống phình to context và ngăn ngừa tuyệt đối nguy cơ mất mát dữ liệu, việc cắt tỉa hoặc dọn dẹp tệp `Noi dung thao luan.md` tuân thủ các quy tắc sắt đá:

1. **Thẩm Quyền Duy Nhất (Sole Cleaning Authority)**:
   - **CHỈ CÓ DUY NHẤT ANTIGRAVITY (Lead Builder & Chủ tọa)** có thẩm quyền thực hiện việc lưu trữ (archive), cắt tỉa hoặc dọn dẹp tệp `Noi dung thao luan.md`.
   - OpenCode và các công cụ khác **TUYỆT ĐỐI KHÔNG ĐƯỢC PHÉP** xóa, cắt ngắn hoặc sửa đổi cấu trúc các lượt trước trong tệp thảo luận. OpenCode chỉ thực hiện duy nhất thao tác nối thêm (append) Turn Block của mình vào cuối tệp.
2. **3 Thời Điểm Kích Hoạt Dọn Dẹp / Cắt Tỉa (The 3 Cleaning Triggers)**:
   - **Thời điểm 1 — Kết thúc toàn diện phiên làm việc (`COMPLETED`)**:
     * Ngay khi phiên làm việc hoàn tất toàn bộ các pha/vòng và được nghiệm thu.
     * Toàn bộ nội dung phiên cũ bắt buộc phải được sao chép nguyên vẹn 100% sang `Thao luan AI/archive_Phien_{XX}_{Ten_Phien}.md`.
     * Tệp `Noi dung thao luan.md` sau khi dọn dẹp chỉ giữ lại phần Header quy chuẩn và Lượt 1 mở đầu của phiên làm việc mới.
   - **Thời điểm 2 — Nén bộ nhớ giữa các Vòng trong phiên thảo luận dài (Intra-Session Milestone Compaction)**:
     * Trong các phiên thảo luận lớn (như Phiên 19 gồm 4 Vòng), dung lượng tệp sẽ tăng dần theo từng vòng trao đổi.
     * Ngay sau khi hai bên đạt mốc đồng thuận kết thúc một Cột mốc lớn (ví dụ xong Vòng 1 & 2), Antigravity sẽ:
       1. Lưu trọn vẹn lịch sử chi tiết vào tệp lưu trữ trung gian: `Thao luan AI/archive_Phien_{XX}_Part1_{Ten_Vong}.md`.
       2. Nén toàn bộ nội dung các lượt tranh luận cũ thành một khối **"BẢNG ĐÚC KẾT ĐỒNG THUẬN CÁC VÒNG TRƯỚC" (Distilled Consensus Snapshot)** cô đọng (~30–40 dòng).
       3. Giữ lại Header + Khối Đúc kết + Lượt gần nhất $\rightarrow$ Đưa tệp về dưới 200 dòng để giải phóng ngữ cảnh tối đa cho các Vòng tiếp theo.
   - **Thời điểm 3 — Chạm ngưỡng an toàn dung lượng (Safety Capacity Threshold)**:
     * Khi tệp vượt quá **500 dòng** hoặc **35 KB**, Antigravity sẽ chủ động kích hoạt nén bộ nhớ ngay ở đầu lượt của mình trước khi viết nội dung mới.
3. **Nguyên Tắc Bất Khả Xâm Phạm: Lưu-Trước-Xóa (Archive-Before-Clean — Zero Data Loss)**:
   - Tuyệt đối nghiêm cấm việc xóa trắng hoặc cắt tỉa bất kỳ dòng nội dung nào mà chưa được sao lưu an toàn vào thư mục `archive_...`.
   - **Bảo toàn chuỗi liên tục (Turn Chain Continuity)**: Khi nén bộ nhớ, bắt buộc phải giữ lại Turn Block gần nhất của đối tác để đảm bảo chuỗi liên kết `parent_turn_id` của lượt tiếp theo không bị đứt gãy.


---

— **Ban Hành**: Ban Điều Phối Kiến Trúc Hệ Thống HueIC IMP  
— **Phiên Bản**: Protocol v2.0 (Chuẩn Hóa Toàn Diện & Đóng Băng SOP) | 2026-09-21 (GMT+7)
