# QUY CHẾ VÀ NGUYÊN TẮC THẢO LUẬN ĐA AI (TWO-AGENT COOPERATIVE EXECUTION PROTOCOL V2.4)

> **Định danh**: **"Thảo Luận AI"** — Khung làm việc phối hợp, phản biện song hành giữa **Antigravity** (AI Lập trình & Kiến trúc - Builder) và **Opencode** (AI Thẩm tra & Phản biện Độc lập - Red Team).
>
> **Nguyên tắc phân tách tệp & Tồn kho thực tế (Separation of Concerns & File Inventory)**:
> 1. **`Quy trinh & Nguyen tac thao luan AI.md`** (Tệp này): Chứa toàn bộ Quy chế, Hợp đồng chuyển trạng thái, Ma trận phục hồi lỗi, Hợp đồng nghiệm thu và Cấu trúc giao thức v2.3. Là tài liệu chuẩn mực cố định (SOP), không bị xóa khi dọn dẹp phiên.
> 2. **`Noi dung thao luan.md`**: Chứa nhật ký chi tiết các lượt trao đổi của phiên làm việc hiện tại (Working Memory Scratchpad). Bắt buộc duy trì đồng thời **dưới 300 dòng VÀ dưới 40 KB**.
> 3. **`state.json` & `state.json.bak`**: Lưu trữ trạng thái điều phối thời gian thực (Orchestration State Schema v2.0 — 9 khóa gốc chuẩn + khóa dừng tùy chọn) giữa hai AI.
> 4. **`archive_manifest.json` & `archive_Phien_*.md`**: Sổ cái băm SHA-256 và các tệp lưu trữ lịch sử thảo luận đã cắt tỉa.
> 5. **`dispatch_history.log`**: Nhật ký kiểm toán toàn văn các lệnh kích hoạt gửi sang OpenCode (mã hóa chuẩn UTF-8).
> 6. **Bộ script điều phối chính thức (`trigger_opencode.py`, `wait_for_opencode_reply.py`, `file_lock.py`)**: Tầng vận chuyển, kiểm định 4 điều kiện Turn Block, khóa tệp nguyên tử và khôi phục trạng thái an toàn.
> 7. **Tệp ngừng sử dụng (`poll_reply.py` — DEPRECATED)**: Script thuộc Nguyên tắc 154 cũ (poll 60s qua REST API), đã bị vô hiệu hóa và thay thế hoàn toàn bởi `wait_for_opencode_reply.py`.
>
> **NGUYÊN TẮC PHẠM VI TRUNG LẬP & CHỐT NGUỒN CHÂN LÝ SSoT DUY NHẤT**:
> - Quy trình thảo luận này là khung làm việc chung cho mọi chủ đề.
> - **Tệp SSoT gốc duy nhất (Canonical SSoT)** về nguyên tắc tác nghiệp của AI trong repo là **[`.keyword.md`](file:///d:/Docker/JKAI/.keyword.md)** (tệp `.keywork.md` được giữ đồng bộ 100% làm bản gương tương thích ngược). Chỉ cập nhật SSoT khi nội dung thống nhất liên quan trực tiếp đến nguyên tắc tác nghiệp toàn cục của AI.
> - Thay đổi chỉ thuộc công cụ, script hay quy chế nội bộ trong thư mục `Thao luan AI/` thì chỉ sửa tệp quy trình này, không lan sang SSoT.

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

## ⚡ II. TỔNG QUAN CƠ CHẾ LIÊN LẠC & QUY TRÌNH 5 BƯỚC CHUẨN MỰC VỚI OPENCODE (END-TO-END COMMUNICATION SOP V2.3)

### A. Tổng Quan Kiến Trúc Liên Lạc Giữa Antigravity Và OpenCode
Hai AI **không** trò chuyện qua bộ nhớ tạm mà phối hợp qua **Cơ chế Bắt tay Kép (Dual-Channel Handshake)**:
1. **Kênh Nội Dung & Chân Lý Duy Nhất (Data & Truth Channel — Trên Đĩa)**:
   - Tệp [`Thao luan AI/Noi dung thao luan.md`](file:///d:/Docker/JKAI/Thao%20luan%20AI/Noi%20dung%20thao%20luan.md) chứa toàn văn nội dung thảo luận được đóng gói trong `<!-- TURN_BEGIN ... -->` và `<!-- TURN_END ... -->`.
   - Tệp [`Thao luan AI/state.json`](file:///d:/Docker/JKAI/Thao%20luan%20AI/state.json) lưu trạng thái điều phối (`current_turn`, `expected_next_turn`, `opencode_session_id`, `status`).
2. **Kênh Tín Hiệu Đánh Thức (Wakeup Transport Channel — Qua Local Desktop REST API)**:
   - OpenCode Desktop mở một HTTP server nội bộ tại `127.0.0.1:<port>` (cổng động, tự động dò qua `find_opencode_port()` trong `trigger_opencode.py` bằng cách quét các cổng `LISTENING` trên `127.0.0.1` phản hồi `/doc` với mã `200`/`401`).
   - Xác thực qua **HTTP Basic Auth** (`opencode:<password>`), trong đó mật khẩu được đọc tự động từ `~/.config/opencode/service.json`.
   - Lệnh đánh thức gửi `POST http://127.0.0.1:<port>/api/session/<opencode_session_id>/prompt` với payload `{"text": "<Thông điệp điều phối>"}`.
3. **Kênh Kiểm Định Hoàn Tất (Verification Channel — Qua Waiter 400s)**:
   - Tiến trình `wait_for_opencode_reply.py` theo dõi tệp `Noi dung thao luan.md` mỗi `5s` (tối đa `400s`), chỉ xác nhận hoàn tất khi OpenCode đã ghi xong khối `TURN_BEGIN ... TURN_END` vào tệp và vượt qua đủ 4 điều kiện kiểm định (`format_valid`, `turn_chain_valid`, `session_match`, `content_hash_valid`).

---

### B. Quy Trình 5 Bước Bắt Buộc Mỗi Khi Liên Lạc Với OpenCode (5-Step Standard Operating Procedure)
Để đảm bảo tin nhắn **luôn gửi trúng cửa sổ OpenCode mà Người Dùng (Master) đang mở trên màn hình** và không bao giờ lệch chuỗi lượt, Antigravity bắt buộc thực hiện đúng 5 bước theo thứ tự sau:

#### **Bước 1 — Kiểm tra cửa sổ Session OpenCode đang hoạt động của Master (`--list-sessions`)**
Trước khi ghi lượt mới, chạy lệnh kiểm tra danh sách root session đang mở trên OpenCode Desktop:
```powershell
python "Thao luan AI/trigger_opencode.py" --list-sessions
```
- Lệnh này tự động dò cổng OpenCode, lọc bỏ các phiên subagent con (có `parentID` như `explore`), đối chiếu thư mục workspace (`D:\Docker\JKAI`) và chỉ ra chính xác **`👉 [ACTIVE TARGET]`** (phiên gốc mới nhất mà Master đang mở trên màn hình).

#### **Bước 2 — Ghi Turn Block của Antigravity vào cuối tệp `Noi dung thao luan.md`**
- Đóng gói nội dung lượt mới trong cặp `<!-- TURN_BEGIN ... -->` và `<!-- TURN_END ... -->` với:
  - `turn_id`: Lượt hiện tại của Antigravity (ví dụ `255`).
  - `parent_turn_id`: Lượt liền trước của OpenCode (`254`).
  - `speaker: Antigravity`.
  - `session_id`: Ghi đúng mã session `👉 [ACTIVE TARGET]` vừa xác định ở Bước 1.
- Kiểm tra tệp `Noi dung thao luan.md` bắt buộc **dưới 300 dòng VÀ dưới 40 KB** (nếu vượt phải archive các lượt cũ vào `archive_Phien_*.md` trước).

#### **Bước 3 — Đồng bộ hóa `state.json` khớp 100% với lượt vừa ghi (`--recover-state`)**
```powershell
python "Thao luan AI/trigger_opencode.py" --recover-state
```
- Lệnh này đọc Turn Block hợp lệ cuối cùng vừa ghi ở Bước 2 để cập nhật nguyên tử `state.json` (`current_turn`, `expected_next_turn = current_turn + 1`, `last_speaker = "Antigravity"`, `session.opencode_session_id = <session_id>`, `status = "READY_TO_TRIGGER"`).

#### **Bước 4 — Phát duy nhất 1 lệnh Trigger đánh thức OpenCode (`trigger_opencode.py`)**
- **Trường hợp 4a — Lần đầu mở chủ đề mới HOẶC vừa chuyển sang cửa sổ Session mới của Master (Bắt buộc nhắc đọc quy chế v2.3)**:
```powershell
python "Thao luan AI/trigger_opencode.py" --session <SESSION_ID> --force "Kính gửi OpenCode: Mở đầu chủ đề/phiên mới, mời bạn ĐỌC TRƯỚC tệp quy chế 'Thao luan AI/Quy trinh & Nguyen tac thao luan AI.md' (Protocol v2.3) để nắm vững quy trình. Sau đó đọc Lượt [X] tại cuối tệp 'Thao luan AI/Noi dung thao luan.md' và ghi phản hồi Lượt [X+1] (turn_id: [X+1], parent_turn_id: [X], speaker: Opencode, session_id: <SESSION_ID>) vào cuối tệp 'Thao luan AI/Noi dung thao luan.md'."
```
- **Trường hợp 4b — Các lượt trao đổi kế tiếp trong cùng một Session**:
```powershell
python "Thao luan AI/trigger_opencode.py" --session <SESSION_ID> --force "Kính gửi OpenCode: Antigravity đã hoàn thành Lượt [X] tại 'Thao luan AI/Noi dung thao luan.md'. Mời bạn đọc cuối tệp và ghi phản biện Lượt [X+1] đúng chuẩn Turn Block v2.3."
```
- **Trường hợp 4c — Kích hoạt Pha 2 (Code Audit) yêu cầu kiểm toán mã nguồn thực tế**:
```powershell
python "Thao luan AI/trigger_opencode.py" --session <SESSION_ID> --force "Kính gửi OpenCode (Senior Red Team Auditor): Antigravity đã thi công xong mã nguồn tại Lượt [X]. Kính mời bạn mở trực tiếp các file code thực tế trong Audit Manifest tại 'Thao luan AI/Noi dung thao luan.md', tự chạy pytest và ghi phán quyết nghiệm thu Lượt [X+1] vào tệp!"
```

#### **Bước 5 — Chạy Tiến Trình Waiter 400s Lắng Nghe Phản Hồi Xác Nhận Qua Tệp (`wait_for_opencode_reply.py`)**
```powershell
python "Thao luan AI/wait_for_opencode_reply.py" --timeout 400 --interval 5
```
- Đứng yên chờ Waiter trả về mã thoát (`0`: Thành công bình thường; `10`: Chạm mốc đồng thuận/dừng giao thức; `20`: Timeout; `30`: Lỗi khối/TOCTOU; `40`: Bận tệp). Tuyệt đối không gửi lệnh trigger thứ 2 khi Waiter đang chạy.

---

## 🛑 III. NGUYÊN TẮC 155: KỶ LUẬT TUẦN TỰ QUA FILE (FILE-CONFIRMED TURN GATING)

1. **Quy Tắc Đơn Lệnh (Strict Single-Dispatch Rule)**:
   - Mỗi Lượt (Turn) của Antigravity sau khi viết đầy đủ vào `Noi dung thao luan.md` chỉ được phép phát **ĐÚNG DUY NHẤT 1 LỆNH TRIGGER ĐÁNH THỨC** sang OpenCode qua API desktop.
   - Nghiêm cấm tuyệt đối mọi hành vi gửi tin nhắn liên tiếp, thăm dò lặp lại, gửi dồn dập (double-send / spam trigger) khi OpenCode chưa hoàn thành lượt phản biện của mình.
2. **Căn Cứ Xác Nhận Hoàn Tất Duy Nhất Là Tệp (File As Single Source of Truth)**:
   - Một lượt phản biện của OpenCode chỉ được coi là hoàn tất khi và chỉ khi nội dung phản hồi chính thức đã được **xác nhận ghi hoàn chỉnh vào tệp `Noi dung thao luan.md`** (đóng đủ `<!-- TURN_BEGIN ... -->` và `<!-- TURN_END ... -->` kèm chữ ký hợp lệ).
   - API trả về HTTP 200 không có nghĩa là OpenCode đã xử lý xong. Mọi trạng thái trung gian hoặc nội dung đang ghi dở ở cuối tệp đều không được coi là xác nhận.
3. **Kỷ Luật Đứng Yên Kiên Nhẫn (Patience & Silent Observation)**:
   - Sau khi gửi tín hiệu đánh thức, Antigravity chuyển hoàn toàn sang trạng thái lắng nghe thụ động (Waiter).
   - Antigravity tuyệt đối không can thiệp, không gửi thêm câu hỏi, không giục giã OpenCode cho đến khi Waiter trả về mã thoát.
4. **Bắt Buộc Ghi Rõ Mọi Thông Tin & Đề Xuất Cải Tiến Vào Tệp (Mandatory Full In-File Documentation)**:
   - OpenCode BẮT BUỘC phải dùng công cụ chỉnh sửa tệp để **ghi trực tiếp toàn văn mọi thông tin, luận điểm phản biện, câu hỏi chất vấn và mọi đề xuất cải tiến** vào tệp `Noi dung thao luan.md` (đóng gói trong Turn Block chuẩn v2.3).
   - Nhật ký điều phối `dispatch_history.log` bắt buộc ghi chuẩn UTF-8 (`newline="\n"`), cấm để xảy ra lỗi mojibake.
5. **Bắt Buộc Đánh Giá & Đề Xuất Cải Tiến Kỹ Thuật Chủ Động (Proactive Technical Proposals with Honest Exemption)**:
   - OpenCode không được chỉ đóng vai trò "người chấm thi thụ động". Trong mỗi lượt phản biện, bên cạnh việc thẩm tra mã nguồn thực tế (Red Team Critique), OpenCode phải chủ động đề xuất giải pháp cải tiến kỹ thuật cụ thể (kiến trúc, thuật toán, tối ưu I/O/VRAM/Latency, test khóa).
   - **Ngoại lệ trung thực (Anti-Performative Clause)**: Nếu sau khi kiểm toán thực chứng mà mã nguồn đã đạt tối ưu và không còn điểm cần cải tiến thực chất, OpenCode được phép ghi rõ tại Khối 2: *"Không có đề xuất bổ sung sau khi đánh giá thực chứng"* kèm lý do và bằng chứng kiểm thử, thay vì bị ép bịa ra các đề xuất hình thức làm phức tạp hóa hệ thống.

---

## ⏱️ IV. NGUYÊN TẮC THỜI GIAN CHỜ THÍCH ỨNG 4 TẦNG & CHẨN ĐOÁN TIMEOUT (TIERED WAITER 400S)

Hệ thống chuẩn hóa:
- **Chu kỳ thăm dò (Polling Interval)**: `5 giây/lần` (`POLL_INTERVAL = 5s`).
- **Thời gian chờ tối đa (Hard Timeout)**: `400 giây` (`HARD_TIMEOUT = 400s`, tương đương ~6.7 phút).
- **Phân cấp trạng thái 4 Tầng (Tiered State Machine)** kèm Heartbeat và Chẩn đoán sau Timeout:

| Tầng Chờ | Khung Thời Gian | Ý Nghĩa Kỹ Thuật | Hành Vi Hệ Thống & Heartbeat |
| :---: | :---: | :--- | :--- |
| **`NORMAL_WAIT`** | `0s – 60s` | OpenCode đọc đề bài, tra cứu file và khởi tạo tư duy ban đầu. | Thăm dò 5s/lần. In nhịp kiểm tra thông thường. |
| **`DEEP_WAIT`** | `60s – 180s` | OpenCode đang suy luận sâu, mở file mã nguồn thực tế và phân tích Red Team. | In heartbeat chuyển tầng: `[DEEP_WAIT] OpenCode đang suy luận chuyên sâu...` |
| **`EXTENDED_WAIT`** | `180s – 300s` | OpenCode soạn thảo phản biện phức tạp hoặc đang thực hiện ghi tệp. | In heartbeat chuyển tầng: `[EXTENDED_WAIT] Đang hoàn thiện văn bản phản biện...` |
| **`FINAL_WAIT`** | `300s – 400s` | Giai đoạn nước rút hoàn tất ghi tệp và hoàn tất chữ ký. | In cảnh báo: `[FINAL_WAIT] Giai đoạn nước rút (còn <100s)...` |
| **`TIMEOUT`** | `> 400s` | Vượt quá ngưỡng chờ 400s. Gọi `diagnose_timeout_reason()` để phân loại căn nguyên. | Báo `EXIT_TIMEOUT (20)`, ghi `timeout_diagnosis` vào `state.json` và giữ nguyên hiện trường để kiểm tra an toàn. |

### Phân Loại Chẩn Đoán Sau Timeout (`diagnose_timeout_reason`):
Timeout chỉ cho biết chưa nhận được Turn Block hoàn chỉnh trong 400s, không đồng nghĩa OpenCode đã chết. Trước khi thoát mã `20`, Waiter tự động phân loại và ghi vào `state.recovery.timeout_diagnosis`:
1. `PARTIAL_WRITE_INCOMPLETE_BLOCK`: Phát hiện có `<!-- TURN_BEGIN` mới nhưng chưa đóng `<!-- TURN_END -->` (tiến trình ghi bị ngắt hoặc đang ghi dở).
2. `UNFORMATTED_NEW_CONTENT_WITHOUT_VALID_BLOCK`: Số dòng tệp tăng nhưng thiếu cấu trúc Turn Block chuẩn.
3. `OPENCODE_NO_FILE_WRITE_WITHIN_400S`: Tệp thảo luận chưa có thay đổi nào sau 400s.

---

## 🎛️ V. PHÂN ĐỊNH RÕ 2 CHẾ ĐỘ THỰC THI & DANH MỤC CẤM TỰ ĐỘNG (EXECUTION MODES & MANDATORY APPROVAL LIST)

Hệ thống quản lý chế độ thực thi minh bạch qua trường `execution.mode` trong `state.json`:

| Chế Độ | Ký Hiệu | Hành Vi Sau Architecture Gate (`🤝 [ĐỒNG THUẬN KIẾN TRÚC]`) | Trường Hợp Sử Dụng |
| :---: | :---: | :--- | :--- |
| **Tương Tác** | `INTERACTIVE` | **DỪNG LẠI NGAY LẬP TỨC**. In tóm tắt kiến trúc và chờ Người Dùng phê duyệt *"OK DO"* trước khi được phép viết mã nguồn. | Các phân hệ nhạy cảm, thay đổi lớn về CSDL, hoặc khi Người Dùng yêu cầu kiểm soát từng bước. |
| **Tự Trị** | `AUTONOMOUS` | **KHÔNG DỪNG LẠI Ở BƯỚC TRUNG GIAN**. Antigravity tự động chuyển tiếp sang giai đoạn thi công code, chạy test suite, build pass 0 lỗi và bàn giao sang Pha 2 cho OpenCode audit. | Khi Người Dùng ủy quyền toàn diện (*"hai bạn tự thảo luận và làm từ A-Z"*). |

### Danh Mục Hành Động Luôn Bắt Buộc Xin Phê Duyệt Người Dùng ( kể cả trong `AUTONOMOUS`):
Ngay cả khi `execution.mode == "AUTONOMOUS"`, hai AI **tuyệt đối không được tự động thực hiện** các thao tác không thể đảo ngược sau nếu chưa có chữ ký/lệnh trực tiếp từ Người Dùng (Master):
1. Xóa dữ liệu trọng yếu, xóa bảng/volume CSDL hoặc xóa tệp nguyên tắc gốc (`.keyword.md`, `.keywork.md`).
2. Chuyển đổi công tắc backend chính thức (`set_active_backend`) hoặc thăng cấp trạng thái hiệu chuẩn (`promote_calibration`) trên Production.
3. Thay đổi cấu hình mạng/tường lửa phần cứng thật ngoài phạm vi Sandbox Lab.

---

## 📋 VI. CHUẨN HÓA MÃ TRẢ VỀ & THỨ TỰ ƯU TIÊN TRẠNG THÁI (STANDARDIZED EXIT CODES V2.3)

Tiến trình `wait_for_opencode_reply.py` chuẩn hóa đúng 5 mã thoát:

| Exit Code | Tên Kỹ Thuật | Ý Nghĩa Kỹ Thuật | Hành Xử Của Antigravity |
| :---: | :--- | :--- | :--- |
| **`0`** | `EXIT_SUCCESS_NORMAL` | **Nhận phản biện hợp lệ (đạt đủ 4 điều kiện v2.3)**, không có stop marker. | Đọc nội dung phản biện, suy luận và viết Lượt tiếp theo, phát 1 trigger sang OpenCode. |
| **`10`** | `EXIT_PROTOCOL_STOP` | **Nhận phản biện hợp lệ + Phát hiện Mốc dừng giao thức (`STOP_MARKER`)**. | **DỪNG TIẾN TRÌNH LẠI**. Không phát trigger. Hành vi tiếp theo do `execution.mode` quyết định (`WAIT_USER_APPROVAL` hoặc `COMPLETED`). |
| **`20`** | `EXIT_TIMEOUT` | Vượt quá 400s không có phản hồi hoàn chỉnh. | Chuyển `ERROR_RECOVERY`, đọc `recovery.timeout_diagnosis` trong `state.json` để xử lý theo Ma trận Mục XVI.B. |
| **`30`** | `EXIT_INVALID_BLOCK` | Có nội dung mới nhưng Turn Block ghi dở quá 30s, sai chuỗi `turn_id`/`parent_turn_id`, lệch `session_id` (TOCTOU), sai `content_hash` hoặc thiếu chữ ký. | Cảnh báo lỗi toàn vẹn khối, lưu vết vào `recovery.last_error` và dừng lại để sửa khối lỗi. |
| **`40`** | `EXIT_FILE_BUSY` | Tệp đang bị khóa `.lock` hoặc có tệp `.tmp` tồn tại quá `30.0s` (`BUSY_MAX_AGE_SECONDS = 30.0`). | Cảnh báo xung đột tài nguyên I/O. |

### Thứ Tự Ưu Tiên Xét Trạng Thái (State Evaluation Precedence):
Nếu nhiều điều kiện xuất hiện đồng thời trong cùng một chu kỳ quét, Waiter bắt buộc xét theo thứ tự ưu tiên nghiêm ngặt từ cao xuống thấp:
$$\texttt{FILE\_BUSY (40)} \;\succ\; \texttt{PARTIAL\_WRITE / INVALID\_BLOCK (30)} \;\succ\; \texttt{PROTOCOL\_STOP (10)} \;\succ\; \texttt{SUCCESS\_NORMAL (0)} \;\succ\; \texttt{TIMEOUT (20)}$$
*(Nghĩa là: Một lượt dù có chứa mốc dừng hoặc chữ ký nhưng nếu tệp đang ghi dở hoặc vi phạm kiểm định Turn Block thì luôn trả về `30` hoặc `40`, tuyệt đối không trả về `0` hay `10`).*

---

## 🧱 VII. CẤU TRÚC TURN BLOCK CÓ ĐỊNH DANH, KIỂM ĐỊNH SHA-256 & CHỐNG REPLAY / TOCTOU (STRUCTURED TURN GATING V2.3)

Mọi lượt trao đổi trong `Noi dung thao luan.md` bắt buộc phải được đóng gói trong **Cấu trúc Turn Block chuẩn mực**:

```markdown
<!-- TURN_BEGIN
turn_id: 250
parent_turn_id: 249
speaker: Opencode
phase: RED_TURN248_CLOSURE_AND_CEILING_FIX_VERDICT
session_id: ses_ed7498d55ffe8w9PokqHBhaxI4
-->

### Luot 250: Opencode (Senior Red Team Auditor) — Nghiem thu Luot 249...

... Nội dung phản biện chi tiết ...

— Ký tên: Opencode (AI Thẩm tra & Phản biện Độc lập — Senior Red Team Auditor) | 2026-10-11 (GMT+7)

<!-- TURN_END
turn_id: 250
speaker: Opencode
content_hash: a1b2c3d4e5f60123
-->
```

### Bốn Điều Kiện Kiểm Định Bắt Buộc Trong Code (`validate_turn_block` tại `wait_for_opencode_reply.py`):
Tiến trình Waiter thực thi kiểm định thực tế cả 4 điều kiện trước khi chấp nhận một lượt mới:
1. **`format_valid == True`**:
   - Khối có đủ cặp `<!-- TURN_BEGIN ... -->` và `<!-- TURN_END ... -->` đã đóng hoàn chỉnh (`is_complete == True`, chống đọc tệp đang ghi dở qua `has_incomplete_turn_block()`).
   - Bên trong thân khối có dòng chữ ký khớp `SIGNATURE_REGEX` của đúng `speaker`.
2. **`turn_chain_valid == True`**:
   - `int(turn_id) == expected_next_turn` và `int(parent_turn_id) == current_turn_id`, đồng thời `turn_id` ở `TURN_BEGIN` khớp với `turn_id` ở `TURN_END`.
   - `turn_id` chưa từng xuất hiện trong tệp (chống trùng/replay số lượt): khối tái sử dụng số lượt đã có bị từ chối `EXIT_INVALID_BLOCK (30)` kể cả khi các điều kiện còn lại đạt.
3. **`session_match == True` (Chống Replay & TOCTOU Session Switch)**:
   - `block.session_id == expected_session_id` (đọc từ `state.json` lúc bắt đầu chờ).
   - Đồng thời kiểm tra **TOCTOU**: `live_state.session.opencode_session_id == expected_session_id`. Nếu session trong `state.json` bị đổi giữa lúc bắt đầu chờ và lúc ghi phản hồi, Waiter lập tức từ chối khối với lý do `TOCTOU_SESSION_CHANGED_MID_FLIGHT` (`EXIT_INVALID_BLOCK = 30`).
4. **`content_hash_valid == True`**:
   - Hàm `compute_turn_content_hash(body)` tính lại mã băm SHA-256 16 ký tự hex từ thân bài thực tế. Nếu `content_hash` khai báo ở dạng hex (16–64 ký tự) hoặc chạy với cờ `--strict-hash`, giá trị khai báo bắt buộc phải khớp với mã băm SHA-256 tính lại từ nội dung thực tế.

*(Chính sách Fallback tương thích có kiểm soát: Chế độ nhận diện chữ ký rời không có Turn Block bị **TẮT MẶC ĐỊNH** (`allow_legacy_fallback = False`) để bảo vệ tính toàn vẹn của cổng kiểm soát lượt; chỉ kích hoạt khi truyền cờ tường minh `--allow-legacy-fallback`).*

---

## 🔍 VIII. SESSION DISCOVERY 4 BƯỚC & TỰ ĐỘNG BÁM ĐUỔI CỬA SỔ ĐANG MỞ CỦA MASTER (STATE ➔ VALIDATE ROOT ➔ AUTO-SWITCH NEWER WINDOW ➔ DISCOVER)

Khi kết nối với OpenCode Desktop API (`GET /api/session`), OpenCode vẫn giữ lại toàn bộ các phiên cũ trong cơ sở dữ liệu và đồng thời sinh ra các phiên con (`parentID != null`, ví dụ subagent `explore`). Để không bao giờ gửi nhầm vào phiên cũ hoặc phiên con khi Master đã mở một cửa sổ phiên mới trên màn hình, hàm `get_active_session_id()` trong `trigger_opencode.py` thực thi thuật toán 4 bước:
1. **State & Root Filter**:
   - Đọc `session.opencode_session_id` ứng viên (`candidate_session`) từ `state.json`.
   - Gọi `GET /api/session` và **lọc chỉ giữ lại các Root Session** (`not s.get("parentID")` — loại bỏ hoàn toàn các phiên subagent con).
2. **Validate & Verify Workspace**:
   - Chỉ xét các Root Session có `location.directory` khớp thư mục gốc repo hiện tại (`SCRIPT_DIR.parent`, tức `d:\docker\jkai`).
3. **Auto-Switch Newer Active Window (`[SESSION AUTO-SWITCH]`)**:
   - Sắp xếp các Root Session thuộc workspace theo thứ tự `(time.created, time.updated)` giảm dần để tìm `newest_root`.
   - **Quy tắc chống kẹt ở phiên cũ**: Ngay cả khi `candidate_session` trong `state.json` vẫn còn tồn tại trong API, nếu phát hiện Master đã tạo một cửa sổ Root Session mới hơn (`newest_root.time.created > candidate_session.time.created`), hệ thống lập tức kích hoạt `[SESSION AUTO-SWITCH]` chuyển sang `newest_root["id"]` và ghi nhận lịch sử chuyển đổi vào `history.opencode_sessions`.
4. **Discover & Fail-Closed**:
   - Nếu `candidate_session` chính là Root Session mới nhất của workspace $\rightarrow$ Tái sử dụng 100%.
   - **Tuyệt đối không hard-code fallback về session chết cũ**: Nếu cả API Discovery và `state.json` đều không có session hợp lệ, script dừng ngay với lỗi `SESSION_DISCOVERY_FAILED` (`exit 1`).

---

## 🗄️ IX. CHUẨN HÓA SCHEMA STATE.JSON V2.0 (9 KHÓA GỐC CHUẨN + KHÓA DỪNG TÙY CHỌN)

Tệp `Thao luan AI/state.json` gồm **9 khóa cấp cao nhất (top-level keys)** trong vận hành bình thường (và thêm 2 khóa `stop_condition_reached`, `stop_reason` khi chạm mốc dừng), được bảo vệ qua **Atomic Write** (`.tmp` $\rightarrow$ `fsync` $\rightarrow$ `os.replace`) và `file_lock` (`LOCK_TIMEOUT = 30.0s`, `BUSY_MAX_AGE_SECONDS = 30.0s`):

```json
{
  "protocol_version": "2.0",
  "session": {
    "id": "phien_23",
    "title": "Tích Hợp Module Trung Tâm Phản Xạ Song Ngữ EN/VI & Đa Tác Vụ Trên JKAI-Zenith",
    "opencode_session_id": "ses_ed7498d55ffe8w9PokqHBhaxI4"
  },
  "turn": {
    "current_turn": 250,
    "expected_next_turn": 251,
    "last_speaker": "Opencode",
    "last_triggered_turn": 249
  },
  "phase": {
    "current_phase": "SIX_STEP_GOVERNANCE_AND_FIVE_LAYER_PIPELINE_AUDIT",
    "phase_turn": 1
  },
  "execution": {
    "mode": "AUTONOMOUS"
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
    "opencode_sessions": [
      {
        "session_id": "ses_f39944a40ffeYczlW5STEm4sp6",
        "switched_at": "2026-09-22T19:29:15.578377",
        "turn": 18
      },
      {
        "session_id": "ses_f36e9de2dffeNjDcmEFYZPrOF0",
        "switched_at": "2026-10-11T10:54:00.000000",
        "turn": 239
      }
    ]
  },
  "status": "WAITING_FOR_ANTIGRAVITY",
  "last_updated_at": "2026-10-11T18:20:30.000000"
}
```

---

## 🧪 X. HAI LỚP KIỂM CHỨNG CHẤT LƯỢNG & RUBRIC NGHIỆM THU 4 TRẠNG THÁI (THE DUAL VERIFICATION LAYERS)

Tuyệt đối không dùng "test pass 100%" hay "build 0 lỗi" làm thước đo duy nhất cho tính đúng đắn nghiệp vụ. Hệ thống thiết lập 2 lớp kiểm chứng độc lập:

1. **Lớp 1 — Automated Verification (Bằng chứng mã nguồn tự động)**:
   - Unit Tests, Integration Tests, Regression Suites, IP/Brand Guardrail (`test_ip_brand_guardrail.py`), và Protocol Conformance Tests (`test_two_agent_protocol_v23.py`).
   - **Red phải là hành vi**: test đỏ đầu tiên của TDD phải assert sai hành vi cụ thể (assertion fail), cấm đếm `ModuleNotFoundError`/`ImportError` làm bằng chứng Red-to-Green.
   - **SUITE_MANIFEST bắt buộc**: mọi suite lũy kế phải có `tests/SUITE_MANIFEST.json` khóa danh sách tệp + số test kỳ vọng mỗi tệp + lệnh chạy chính xác, kèm test tự kiểm manifest (lệch 1 là FAIL).
   - **Chạy lại full sprint sau mọi sửa code**: bất kỳ chỉnh sửa mã nguồn nào (kể cả 1 dòng import) bắt buộc chạy lại toàn bộ sprint suite và ghi lệnh + thời gian + kết quả vào verdict. Báo "xanh" mà không nêu 3 thông tin này thì verdict vô hiệu.
2. **Lớp 2 — Independent Red Team Audit (OpenCode thẩm tra độc lập)**:
   - Mở trực tiếp mã nguồn vật lý trên đĩa, chạy probe độc lập ngoài mẫu (**Zero Self-Grading**: người ra đề khác người viết scorer), đối chiếu trực tiếp với yêu cầu ban đầu của Người Dùng.
   - **Đo lại độc lập trước khi kết luận**: không công nhận số báo cáo nào chưa tự chạy lại; probe riêng khớp mới ghi vào verdict.
3. **Phân Loại Trạng Thái Nghiệm Thu Bắt Buộc (4-State Acceptance Rubric)**:
   Mọi báo cáo nghiệm thu phải phân định rạch ròi từng hạng mục vào 1 trong 4 trạng thái:
   - **`PASS`**: Đã có code thực tế trên đĩa + test tự động/probe độc lập chạy xanh + khớp yêu cầu nghiệp vụ.
   - **`FAIL`**: Code sai logic, test đỏ, hoặc báo cáo sai lệch so với mã nguồn thực tế.
   - **`BLOCKED`**: Đã thi công xong cơ chế nhưng đang chờ cổng điều kiện bắt buộc (ví dụ: chờ đủ 100 nhãn vàng `reviewed_by_master=True` hoặc chờ chữ ký phê duyệt của Master).
   - **`NOT_TESTED`**: Nhánh logic đã viết nhưng chưa kích hoạt được trong môi trường live thực tế (bắt buộc ghi rõ lý do và kế hoạch test giả lập, cấm gộp chung vào `PASS`).
4. **Phân Biệt Số Quan Sát Và Số Bảo Đảm (Observation vs Guarantee)**:
   - Giá trị tuyệt đối (tokens, %, ms, ECE...) hoặc được test ghim bằng assert chính xác, hoặc ghi nhãn **`OBSERVATION`** kèm phiên bản code sinh ra nó. Cấm trích số tuyệt đối không ghim vào bảng nghiệm thu.
   - Ngưỡng (threshold: `<=`, `>=`, `<`) phải có test ghim ngưỡng; giá trị đo từng lần chạy là quan sát, có thể trôi theo máy.
5. **Quyền VETO Chuẩn (Load-Bearing Veto)**: Phát hiện tải trọng (bypass cổng kiểm soát, secret trong source, số liệu phân nhóm sai lệch, endpoint ma, tự ký duyệt) thì verdict là **TỪ CHỐI NGHIỆM THU + chặn slice kế tiếp** cho đến khi sửa xong và audit lại. Cấm dùng `XANH ĐIỀU KIỆN` cho qua lỗi tải trọng.

---

## 📜 XI. NGUYÊN TẮC 156: BẮT BUỘC THÔNG BÁO & THỐNG NHẤT QUY TRÌNH THẢO LUẬN TRƯỚC KHI THẢO LUẬN NỘI DUNG (FIRST-CONTACT BRIEFING & PROTOCOL ALIGNMENT GATE)

> **Chỉ thị trực tiếp từ Master**:
> *"chú ý trong lần đầu gởi thông tin cho opencode thì cần báo opencode biết về quy trình này nhé. ghi vào rõ trong quy trinh de lần sau cứ vậy là phải làm"*

1. **Quy Tắc Bắt Buộc Ở Lần Đầu Gửi Thông Tin Cho OpenCode (Mandatory First-Contact Protocol Briefing)**:
   - Mỗi khi bắt đầu một phiên mới, mở một chủ đề thảo luận mới, hoặc khi quy trình vừa được nâng cấp: **Ngay trong lần đầu tiên gửi thông tin / lệnh kích hoạt (`trigger_opencode.py`) và trong Turn Block mở đầu tại `Noi dung thao luan.md`, Antigravity BẮT BUỘC phải thông báo rõ ràng cho OpenCode biết về tệp quy trình `Thao luan AI/Quy trinh & Nguyen tac thao luan AI.md` (Protocol v2.3)** và yêu cầu OpenCode đọc kỹ tệp quy trình này trước khi viết phản biện.
   - Quy tắc này là bất biến bắt buộc cho mọi lần thảo luận về sau ("cứ vậy là phải làm"), tuyệt đối không được bỏ qua bước thông báo quy trình ở lượt mở đầu.
2. **Nguyên Tắc Bắt Buộc Pha 0 Khởi Động (Protocol Alignment Gate)**:
   - Khi bước vào chủ đề lớn hoặc phân hệ mới, Lượt đầu tiên (Pha 0) phải thống nhất đủ 4 nội dung:
     * **Mục tiêu tối thượng & Sản phẩm bàn giao (North Star & Deliverables)**.
     * **Lộ trình thảo luận theo Vòng (Round-by-Round Agenda)**.
     * **Tiêu chuẩn chất lượng & Rubric nghiệm thu 4 trạng thái (`PASS / FAIL / BLOCKED / NOT_TESTED`)**.
     * **Ranh giới tác nghiệp & Kỷ luật nghiêm ngặt (Chưa đồng thuận kiến trúc và chưa được Master duyệt thì chưa tự ý viết code nghiệp vụ mới)**.
3. **Mốc Ký Kết Thống Nhất Quy Trình (Protocol Sign-off Gate)**:
   - Chỉ khi cả Antigravity và OpenCode cùng ký xác nhận `🤝 [ĐỒNG THUẬN QUY TRÌNH THẢO LUẬN]` vào `Noi dung thao luan.md`, hai bên mới chính thức bước sang Vòng 1 chuyên môn.

---

## 🧹 XII. NGUYÊN TẮC DỌN DẸP, NÉN BỘ NHỚ, SỔ CÁI ARCHIVE SHA-256 & ROLLBACK (SCRATCHPAD ARCHIVING & COMPACTION V2.3)

1. **Ngưỡng Trần Kép Bắt Buộc (Dual Hard Limits — Cả Hai Điều Kiện Phải Thỏa Mãn)**:
   - Tệp `Noi dung thao luan.md` **BẮT BUỘC PHẢI ĐỒNG THỜI DƯỚI 300 DÒNG (`< 300 lines`) VÀ DƯỚI 40 KB (`< 40,960 bytes`)**.
   - Nếu vượt **bất kỳ một trong hai ngưỡng** (dù ngưỡng kia vẫn đạt), tệp bị coi là vi phạm giới hạn và Antigravity bắt buộc phải thực hiện lưu trữ & cắt tỉa ngay khi kết thúc chủ đề hiện tại.
2. **Thẩm Quyền Duy Nhất (Sole Cleaning Authority)**:
   - Chỉ duy nhất **Antigravity** được phép gọi hàm `verify_and_archive_discussion()` để lưu trữ và cắt tỉa tệp thảo luận. OpenCode chỉ thực hiện thao tác nối thêm (append) Turn Block mới.
3. **Quy Trình Lưu-Xác Minh-Cắt Tỉa-Rollback Có Sổ Cái (`verify_and_archive_discussion` trong `file_lock.py`)**:
   - **Bước 1 (Ghi Archive nguyên tử)**: Ghi toàn bộ các lượt cũ sang `Thao luan AI/archive_Phien_{XX}_Part{Y}_{Chu_De}.md` qua `atomic_write`.
   - **Bước 2 (Xác minh SHA-256 & Chống trùng lặp)**: Đọc lại tệp archive từ đĩa, tính mã băm SHA-256 và đối chiếu với `expected_arch_sha` cùng sổ cái `Thao luan AI/archive_manifest.json`. Nếu tệp archive không tồn tại hoặc lệch SHA-256, **hủy bỏ ngay thao tác cắt tỉa**.
   - **Bước 3 (Kiểm tra bản cắt tỉa trước khi ghi)**: Bản cắt tỉa phải giữ lại Header + Bảng đúc kết + tối thiểu 1–2 Turn Block gần nhất (để bảo toàn chuỗi `parent_turn_id`), đạt `< 300` dòng và `< 40 KB`, và không có Turn Block dở dang (`has_incomplete_turn_block == False`).
   - **Bước 4 (Sao lưu `.bak` & Rollback tự động)**: Tạo `Noi dung thao luan.md.bak` trước khi ghi đè bản cắt tỉa. Nếu xảy ra bất kỳ lỗi I/O hoặc lệch hash nào sau khi ghi, hệ thống tự động khôi phục nguyên trạng từ `.bak`.

---

## ⚖️ XIII. NGUYÊN TẮC 157: PHẢN BIỆN TƯƠNG HỖ, GIỚI HẠN VÒNG TRANH LUẬN & TRỌNG TÀI TỐI CAO (MUTUAL DIALECTIC & ARBITRATION RULE)

1. **Nghiêm Cấm Thỏa Hiệp / Gật Đầu Hình Thức (Zero Blind Acceptance)**:
   - Không bên nào được gật đầu hình thức nếu đề xuất làm tăng độ trễ, gây rủi ro bảo mật/dữ liệu hoặc vi phạm kiến trúc.
2. **Quy Trình Phản Biện 3 Bước (3-Step Dialectic Protocol)**:
   - Bước 1: Phân tích mặt hạn chế / trade-off bằng số liệu thực chứng.
   - Bước 2: Đề xuất phương án thay thế tối ưu hơn.
   - Bước 3: Hội tụ về phương án tối ưu toàn cục.
3. **Giới Hạn Vòng Phản Biện & Cơ Chế Phân Xử Khi Bất Đồng (`MAX_DIALECTIC_ROUNDS = 3`)**:
   - Một điểm bất đồng kỹ thuật chỉ được phép tranh luận tối đa **3 vòng qua lại (6 lượt)**.
   - Nếu sau 3 vòng vẫn chưa đạt đồng thuận, hoặc nếu bất đồng liên quan đến **kiến trúc cốt lõi, bảo mật, dữ liệu, bản quyền hay thay đổi không thể đảo ngược**, Antigravity bắt buộc phải lập **Bảng Đối Sánh Trade-off 2 Phương Án (Option A vs Option B)** kèm bằng chứng của mỗi bên, chuyển trạng thái sang `WAITING_FOR_USER_APPROVAL`, và trình **Người Dùng (Master — Trọng tài tối cao)** ra phán quyết cuối cùng.
4. **Chỉ Tiêu Độ Tin Cậy Thực Thực Chất**:
   - Mục tiêu hoàn thành tác vụ (TCR) được đo lường thực tế qua bộ benchmark/soak telemetry có phân nhóm lỗi rõ ràng, không dùng khẩu hiệu tuyệt đối hóa để che giấu lỗi.

---

## 🚀 XIV. NGUYÊN TẮC 158: ĐỒNG KIẾN TẠO & CẤU TRÚC 3 KHỐI LINH HOẠT (CO-CREATION & PEER ACCOUNTABILITY)

Mọi Turn Block của OpenCode trong `Noi dung thao luan.md` gồm 3 khối chuẩn:
- **Khối 1 — Thẩm tra thực chứng (Empirical Audit & Verification)**: Mở trực tiếp mã nguồn và chạy test/probe để xác nhận `PASS / FAIL / BLOCKED / NOT_TESTED`. **Bắt buộc kiểm ngoài manifest**: ngoài các tệp trong Audit Manifest, phải grep caller production và trace ít nhất 1 đường nóng liên quan (đường request thật, caller ngoài `tests/`); thiếu bước này thì verdict tối đa là VÀNG, không được XANH.
- **Khối 2 — Đề xuất cải tiến kỹ thuật chủ động (Proactive Engineering Proposals)**: Đưa ra 1–3 đề xuất kỹ thuật thực chất; hoặc nếu mã nguồn đã hoàn thiện tối ưu, ghi rõ *"Không có đề xuất bổ sung sau khi đánh giá thực chứng"* kèm lý do và bằng chứng kiểm thử.
- **Khối 3 — Điều kiện nghiệm thu & Bước tiếp theo (Clear Acceptance Bar & Next Steps)**: Nêu rõ điều kiện đóng sổ hoặc hướng đi tiếp theo.
- **Kỷ luật probe của auditor**: Đọc signature/tham số API trước khi kết luận hành vi; probe lỗi do gọi sai API phải tự đính chính công khai trong lượt, không lặng lẽ bỏ qua.

---

## 🛡️ XV. QUY TẮC BÀN GIAO SESSION, VỆ SINH SECRET & CỔNG CHẶN BẢN QUYỀN FAIL-CLOSED

1. **Quy tắc bàn giao session (Session Handover Rule)**:
   - Khi chuyển sang desktop session mới, Antigravity phải cập nhật `state.json` (`session.opencode_session_id` + `history.opencode_sessions`) **trước** khi viết Turn Block mới. Nếu session bị đổi giữa lúc Waiter đang chờ (TOCTOU), lượt cũ lập tức bị chặn (`EXIT_INVALID_BLOCK = 30`).
2. **Cổng chặn Bản quyền & Manifest Mặc định Đóng (Fail-Closed License & Manifest Gate)**:
   - Mọi lượt chạm code/model phải qua `tests/test_ip_brand_guardrail.py` + kiểm tra manifest checkpoint (`models/reflex_checkpoint_manifest.json` và `models/reflex_engine/0.4.2/manifest.json`).
   - **Hành vi Fail-Closed bắt buộc**: Nếu thiếu tệp manifest, thiếu `sha256`, chứa URL ngoại vi trái phép (`external_urls_allowed: false`), hoặc `license` ở trạng thái không xác định (`"unknown"` / rỗng), hệ thống **mặc định chặn tích hợp và cấm phân phối** cho đến khi xác minh đầy đủ nguồn gốc, mã băm và giấy phép.
3. **Vệ sinh Secret**: Tuyệt đối không dán mật khẩu, token hay private key vào tệp thảo luận, `state.json` hoặc `dispatch_history.log`.

---

## 📐 XVI. HỢP ĐỒNG VẬN HÀNH & KIỂM THỬ TUÂN THỦ GIAO THỨC V2.3 (OPERATIONAL CONTRACTS & CONFORMANCE SUITE)

### A. Hợp Đồng Chuyển Trạng Thái (`state.status` State Transition Contract)

```
  ┌─────────────────────────┐
  │ WAITING_FOR_ANTIGRAVITY │ ◄── (Khởi tạo phiên / Sau khi OpenCode hoàn tất lượt hợp lệ)
  └────────────┬────────────┘
               │ Antigravity ghi xong Turn Block hoàn chỉnh vào Noi dung thao luan.md
               ▼
  ┌─────────────────────────┐
  │    READY_TO_TRIGGER     │ ◄── (Hoặc sau lệnh --recover-state khi lượt cuối là Antigravity)
  └────────────┬────────────┘
               │ trigger_opencode.py gửi POST /prompt thành công (HTTP 200/202/409)
               ▼
  ┌─────────────────────────┐
  │  WAITING_FOR_OPENCODE   │
  └─────┬──────┴──────┬─────┘
        │             │
        │             ├──► [Lỗi Timeout 20 / Invalid Block 30 / API Unreachable] ──► ERROR_RECOVERY
        │             │                                                                    │
        │             │    (Chạy trigger_opencode.py --recover-state sau khi xử lý lỗi) ◄──┘
        ▼             │
  [Waiter xác nhận 4 điều kiện Turn Block v2.3]
        │
        ├──► Không có STOP_MARKER (Exit 0) ──────────────────────────► WAITING_FOR_ANTIGRAVITY
        ├──► Có STOP_MARKER / Cần duyệt (Exit 10, INTERACTIVE) ──────► WAITING_FOR_USER_APPROVAL
        └──► Có SESSION_COMPLETED (Exit 10, AUTONOMOUS) ─────────────► COMPLETED
```

### B. Ma Trận Lỗi & Phục Hồi (Failure and Recovery Matrix)

| Tình Huống Lỗi | Cách Phát Hiện Trong Code | Dữ Liệu Giữ Lại | Hành Động Phục Hồi Được Phép |
| :--- | :--- | :--- | :--- |
| **1. Ghi dở Turn Block (`PARTIAL_WRITE`)** | `has_incomplete_turn_block()` phát hiện `TURN_BEGIN` chưa đóng `TURN_END`. | Giữ nguyên tệp thảo luận; chờ tối đa 30s rồi thoát `EXIT_INVALID_BLOCK (30)`. | Kiểm tra tiến trình ghi của AI, đóng hoàn chỉnh khối hoặc khôi phục từ `.bak`, sau đó chạy `--recover-state`. |
| **2. Tệp bị khóa quá hạn (`FILE_BUSY`)** | `is_file_busy()` phát hiện `.tmp` hoặc `.lock` trong vòng `30.0s` (dọn khóa mồ côi `>60s`). | Không ghi đè; thoát `EXIT_FILE_BUSY (40)` sau 30s chờ. | Đợi tiến trình giữ khóa kết thúc; khóa mồ côi quá 60s được `file_lock` tự động thu hồi an toàn. |
| **3. Sai chuỗi lượt / Sai Session (Replay / TOCTOU)** | `validate_turn_block()` trả `turn_chain_valid=False` hoặc `session_match=False`. | Ghi lý do vào `recovery.last_error`, thoát `EXIT_INVALID_BLOCK (30)`. | Sửa lại `turn_id` / `parent_turn_id` / `session_id` trong Turn Block khớp với `state.json`, sau đó chạy `--recover-state`. |
| **4. Lệch mã băm nội dung (`SHA256_MISMATCH`)** | `compute_turn_content_hash(body)` khác với `content_hash` hex trong `TURN_END`. | Thoát `EXIT_INVALID_BLOCK (30)`, báo `SHA256_HASH_MISMATCH`. | Tính lại hash từ thân bài thực tế và cập nhật vào `TURN_END`. |
| **5. Quá thời gian chờ 400s (`HARD_TIMEOUT`)** | `elapsed >= 400s`; `diagnose_timeout_reason()` ghi chẩn đoán vào `state.json`. | Giữ nguyên toàn bộ tệp và trạng thái; thoát `EXIT_TIMEOUT (20)`. | Không kích hoạt lại mù quáng; kiểm tra `timeout_diagnosis` và OpenCode session trước khi chạy `--recover-state`. |
| **6. Lỗi cắt tỉa / Archive** | `verify_and_archive_discussion()` kiểm tra SHA-256 hoặc giới hạn `<300 dòng & <40KB` thất bại. | Tự động rollback `Noi dung thao luan.md` từ `.bak`. | Kiểm tra dung lượng bản cắt tỉa (<300 dòng, <40KB) rồi thực hiện lại. |

### C. Hợp Đồng Nghiệm Thu Nhiệm Vụ (Task Acceptance Contract)
1. Mỗi nhiệm vụ khi bắt đầu phải cố định rõ: **Tiêu chí hoàn thành**, **Bằng chứng vật lý bắt buộc** (file, test, benchmark, SHA-256), **Người có thẩm quyền phê duyệt** và **Danh sách mục chưa kiểm thử (`NOT_TESTED`)**.
2. Nghiêm cấm cả hai AI tự ý hạ thấp hoặc thay đổi tiêu chí nghiệm thu sau khi đã bắt đầu thi công.

### D. Bảng Đối Chiếu 3 Cột: Quy Định — Code Thực Tế — Kiểm Thử Tự Động (`tests/test_two_agent_protocol_v23.py`)

| Hạng Mục | Quy Định SOP v2.3 | Mã Nguồn Thực Thi Thực Tế | Bài Kiểm Thử Khóa (`test_two_agent_protocol_v23.py`) |
| :--- | :--- | :--- | :--- |
| **P0-1 & P0-4: Kiểm định 4 điều kiện Turn Block & TOCTOU** | Mục VII (`format_valid`, `turn_chain_valid`, `session_match`, `content_hash_valid`, tắt fallback mặc định) | `wait_for_opencode_reply.py`: `validate_turn_block()`, `compute_turn_content_hash()`, `allow_legacy_fallback=False` | `test_validate_turn_block_four_conditions_and_toctou` |
| **P0-2: Khôi phục `state.json` an toàn** | Mục II.5 & XVI.A (`--recover-state`, đọc Turn Block cuối, chặn reset khi đang chạy) | `trigger_opencode.py`: `recover_state()` | `test_safe_recover_state_reconciles_from_discussion_and_blocks_live_wait` |
| **P0-3: Chống ghi dở & Khóa tệp 30s** | Mục III.2, VI & XVI.B (`has_incomplete_turn_block`, `append_turn_block_atomic`, `is_file_busy=30.0s`) | `file_lock.py`: `has_incomplete_turn_block()`, `append_turn_block_atomic()`, `BUSY_MAX_AGE_SECONDS = 30.0` | `test_partial_write_detection_and_atomic_turn_append` |
| **P1-5: Chẩn đoán sau Timeout** | Mục IV (`diagnose_timeout_reason`) | `wait_for_opencode_reply.py`: `diagnose_timeout_reason()` | `test_diagnose_timeout_reason_categories` |
| **P1-8: Archive có Manifest SHA-256 & Rollback** | Mục XII (`< 300 dòng` VÀ `< 40 KB`, `archive_manifest.json`, rollback `.bak`) | `file_lock.py`: `verify_and_archive_discussion()` | `test_verified_archive_manifest_sha256_and_rollback_on_limit_violation` |
| **Vệ sinh Inventory & SSoT** | Đánh dấu `poll_reply.py` DEPRECATED, xóa fallback session chết, giữ nguyên vẹn `.keyword.md` & `.keywork.md` | `poll_reply.py`, `trigger_opencode.py:get_active_session_id()`, `.keyword.md` / `.keywork.md` | `test_inventory_hygiene_deprecated_poll_and_ssot_intact` |

---

— **Ban Hành**: Ban Điều Phối Kiến Trúc Hệ Thống JKAI-Zenith  
— **Phiên Bản**: Protocol v2.4 (Kiểm ngoài manifest + Red hành vi + Chống trùng turn_id + SUITE_MANIFEST + Phân biệt số quan sát/bảo đảm + Kỷ luật probe + Quyền VETO chuẩn) | 2026-10-14 (GMT+7)
