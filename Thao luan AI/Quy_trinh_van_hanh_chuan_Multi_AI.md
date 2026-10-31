# QUY TRÌNH VẬN HÀNH CHUẨN (SOP) MULTI-AI V10

**Mã tài liệu:** SOP-MULTI-AI-V10  
**Phiên bản SOP:** 10.0  
**Phiên bản giao thức file tham chiếu:** 11.1  
**Quy chế điều hành bắt buộc:** Quy_che_dieu_hanh_va_phoi_hop_Multi_AI.md — V4.0  
**Phạm vi:** Điều phối nhiều AI thông qua file dùng chung, thảo luận độc lập, phân công, thực thi, kiểm tra, tích hợp và phục hồi sau sự cố.  
**AI Chính mặc định:** Cursor (`agent_id=cursor`)  
**AI Builder mặc định:** Antigravity (`agent_id=antigravity`)  
**AI Reviewer mặc định:** OpenCode (`agent_id=opencode`)  

**Triết lý vận hành:** Điều phối bằng file · Bất biến bằng Baseline · Xác minh bằng Snapshot · Cưỡng chế bằng Runtime.
**Luật tối cao:** Quy chế điều hành và phối hợp Multi-AI V4.0. Khi xử lý sự cố, phải kiểm tra văn bản gốc, xác định đúng số Điều và trích nguyên văn ngắn, chính xác trước khi áp dụng. Không tự tạo hoặc suy diễn nội dung Điều luật.
**Đối chiếu Quy chế V4.0:** Xác minh nguyên văn các Điều 16, 18, 20, 24, 27, 32, 33, 34 và 35 tại file `Quy_che_dieu_hanh_va_phoi_hop_Multi_AI.md`
**Điều kiện tiên quyết:** Phải kiểm tra kiến trúc, mã nguồn, công cụ và cơ chế điều phối hiện có trước khi xây dựng controller, state machine, watcher hoặc runtime mới. Ưu tiên tái sử dụng thành phần đã được xác minh; chỉ bổ sung phần còn thiếu.
**LUÔN TUÂN THỦ NGUYÊN TẮC LÀM VIỆC THEO FILE .keywork.md.
---

# PHẦN I. MỤC TIÊU, PHẠM VI VÀ NGUYÊN TẮC

## Điều 1. Mục tiêu

SOP này quy định một quy trình vận hành nhóm AI có khả năng phối hợp qua hệ thống file chung, trong đó AI Chính chịu trách nhiệm điều hành xuyên suốt và các AI thành viên chủ động thảo luận, thực thi nhiệm vụ, phản biện và báo cáo.

Hệ thống hướng tới các mục tiêu:

1. Giảm tối đa việc Master phải chuyển tiếp từng thông điệp giữa các AI.
2. Cho phép AI Chính chủ động phân tích yêu cầu, tổ chức thảo luận, phân vai và điều chỉnh kế hoạch trong phạm vi được phép.
3. Ngăn chặn các AI ghi đè công việc của nhau hoặc tự ý sửa mã nguồn ngoài phạm vi.
4. Bảo đảm mọi kết quả đều truy xuất được nguồn gốc, phiên bản, bằng chứng và lịch sử xử lý.
5. Ngăn việc tuyên bố hoàn thành khi chưa có kết quả kiểm chứng.
6. Có khả năng phát hiện timeout, xung đột, lỗi tích hợp, regression và phục hồi an toàn.
7. Từng bước giảm sự can thiệp thường xuyên của Master mà không loại bỏ quyền kiểm soát của Master.

## Điều 2. Phạm vi áp dụng

SOP áp dụng cho:

- Phân tích yêu cầu và lập kế hoạch.
- Thảo luận nhiều AI.
- Phân vai và giao nhiệm vụ.
- Phát triển, sửa đổi, kiểm tra và rà soát code.
- Tạo và nghiệm thu artifact như tài liệu, báo cáo, cấu hình hoặc sản phẩm đầu ra.
- Theo dõi tiến độ, xử lý timeout và xung đột.
- Tích hợp kết quả vào dự án.
- Rollback, xác minh sau rollback và kết thúc phiên.

Đối với nhiệm vụ chỉ thảo luận hoặc tạo tài liệu, có thể bỏ qua các gate đặc thù của code nếu không liên quan. Tuy nhiên, mọi nhiệm vụ vẫn phải có người chịu trách nhiệm, tiêu chí hoàn thành và bằng chứng tương ứng.

## Điều 3. Ba vai trò cốt lõi

| Vai trò | Chủ thể | Trách nhiệm chính |
|---|---|---|
| Master | Người khởi tạo và giám sát | Xác định mục tiêu, bổ sung yêu cầu, phê duyệt quyết định vượt quyền, STOP/CONTINUE |
| AI Chính | Cursor mặc định | Điều phối, phân công, quản lý trạng thái, kiểm chứng, tích hợp và báo cáo |
| AI thành viên | Antigravity, OpenCode và agent đã đăng ký | Phân tích, thảo luận, thực thi, phản biện và nộp kết quả |

Master không bắt buộc làm trung gian chuyển tin giữa các AI. AI Chính phải tự tổ chức luồng công việc qua file, với điều kiện các agent có quyền truy cập thực tế vào cùng vùng dữ liệu.

## Điều 4. Thứ bậc ưu tiên

Khi có xung đột, áp dụng thứ tự sau:

1. Quy chế điều hành và phối hợp Multi-AI V4.0.
2. Lệnh STOP hợp lệ của Master.
3. Yêu cầu, giới hạn và quyết định được Master phê duyệt.
4. Hợp đồng nhiệm vụ đã được chốt và xác thực.
5. SOP Multi-AI V10.
6. Chỉ thị điều phối của AI Chính.
7. Đề xuất và yêu cầu của AI thành viên.

Một chỉ thị cấp thấp không được phép ghi đè chỉ thị cấp cao hơn. Mọi thay đổi hợp lệ đối với hợp đồng nhiệm vụ phải được ghi nhận bằng quy trình CHANGE_REQUEST.

## Điều 5. Các nguyên tắc bất biến

### 5.1. File là kênh liên lạc chính thức

Mọi thông tin có ý nghĩa điều hành phải được ghi vào file tương ứng trong `AI_TEAM/`.

Chat trực tiếp, thông báo trong giao diện hoặc lời nói của một AI không tự động trở thành trạng thái điều hành chính thức nếu chưa được ghi nhận vào hệ thống file.

### 5.2. Một AI Chính tại một thời điểm

Chỉ một agent được quyền điều hành và ghi các file điều khiển chung trong một phiên.

Mọi thay đổi Orchestrator phải được Master công bố, cập nhật registry và ghi nhận vào lịch sử phiên. Không cho phép hai Orchestrator đồng thời ghi trạng thái điều khiển.

### 5.3. Không tự nhận hoàn thành

Agent chỉ được báo cáo rằng mình đã hoàn tất phần việc khi đã nộp đủ kết quả và bằng chứng theo hợp đồng nhiệm vụ.

Việc chốt nhiệm vụ thuộc thẩm quyền của AI Chính sau khi hoàn thành các bước kiểm chứng tương ứng.

### 5.4. Reviewer PASS không đồng nghĩa với COMPLETED

Reviewer PASS chỉ là kết quả đánh giá độc lập đối với artifact trong phạm vi review.

AI Chính vẫn phải kiểm tra artifact, xác minh nguồn gốc, chạy các bài kiểm tra bắt buộc và thực hiện regression sau tích hợp nếu có sửa đổi code.

### 5.5. Baseline là mốc so sánh bất biến

Mọi diff nghiệm thu phải được so với baseline đã đóng băng cho chính nhiệm vụ đó.

Không dùng source hiện tại đang thay đổi làm mốc tham chiếu thay thế cho baseline.

### 5.6. Theo dõi phải có bằng chứng thực tế

Không tuyên bố một agent đang theo dõi liên tục nếu không có cơ chế polling, watcher hoặc dispatch thực sự hoạt động.

Nếu không còn khả năng theo dõi, phải báo `OFFLINE`, `WATCH_FAILED` hoặc trạng thái tương ứng. File chỉ là dữ liệu; file không tự đánh thức một AI đang ngủ hoặc một tiến trình đã dừng.

### 5.7. BOUNDED_AUTONOMY

AI Chính được tự chủ trong phạm vi hợp đồng, quyền hạn, ngân sách và các gate đã được phê duyệt.

Tự chủ không bao gồm quyền tự thay đổi mục tiêu tối cao, mở rộng phạm vi trái phép, vượt quyền truy cập, bỏ qua xác minh hoặc tự phê duyệt các quyết định bắt buộc có sự đồng ý của Master.

---

# PHẦN II. KIẾN TRÚC THƯ MỤC VÀ QUYỀN GHI

## Điều 6. Cấu trúc thư mục chuẩn

Tại thư mục gốc của dự án:

```text
<PROJECT_ROOT>/
├── <SOURCE_CODE>/
└── AI_TEAM/
    ├── system/
    │   ├── JOIN_PROTOCOL.md
    │   ├── Quy_trinh_van_hanh_chuan_Multi_AI.md
    │   ├── Quy_che_dieu_hanh_va_phoi_hop_Multi_AI.md
    │   ├── agents_registry.json
    │   ├── LAW_POINTER.md
    │   └── schemas/
    │       ├── task_contract.schema.json
    │       ├── evidence.schema.json
    │       └── task_state.schema.json
    │
    ├── control/
    │   ├── MASTER_REQUEST.md
    │   ├── THONG_BAO.md
    │   ├── TRANG_THAI.json
    │   ├── DECISIONS.md
    │   └── CHANGE_REQUESTS.md
    │
    ├── discussion/
    │   ├── cursor.md
    │   ├── antigravity.md
    │   └── opencode.md
    │
    ├── inbox/
    │   ├── cursor/
    │   ├── antigravity/
    │   └── opencode/
    │
    ├── results/
    │   ├── cursor/
    │   ├── antigravity/
    │   └── opencode/
    │
    ├── tasks/
    │   └── TASK-001/
    │       ├── contract/
    │       │   ├── master_spec.json
    │       │   └── contract_hash.txt
    │       ├── baseline/
    │       │   └── manifest.json
    │       ├── workspaces/
    │       │   ├── antigravity/
    │       │   └── opencode/
    │       ├── evidence/
    │       │   ├── evidence.json
    │       │   └── logs/
    │       ├── reviews/
    │       │   ├── bundle/
    │       │   │   ├── manifest.json
    │       │   │   └── artifact/
    │       │   └── verdict_opencode.md
    │       ├── snapshots/
    │       └── task_state.json
    │
    ├── runtime/
    │   ├── locks/
    │   ├── heartbeats/
    │   └── health/
    │
    └── logs/
        ├── activity.log
        └── audit/
```

Các thư mục `runtime/locks/`, `runtime/heartbeats/` và `runtime/health/` là vị trí quy ước. Chỉ coi chúng có hiệu lực khi đã có chương trình thực tế thực hiện việc tạo, kiểm tra, cập nhật và xử lý các trạng thái tương ứng.

## Điều 7. Quyền ghi file

### 7.1. Agent thành viên

Mỗi agent chỉ được ghi vào:

- `discussion/<agent_id>.md`
- `inbox/<agent_id>/` khi được cấp quyền phản hồi hoặc cập nhật trạng thái nhận việc.
- `results/<agent_id>/`
- Workspace riêng của chính agent.
- Vùng evidence được giao cho chính agent.

Agent không được tự sửa:

- `control/TRANG_THAI.json`
- `control/THONG_BAO.md`
- Registry của agent.
- Workspace của agent khác.
- Baseline đã đóng băng.
- Review bundle đã đóng gói.
- Source chính của dự án nếu chưa được cấp quyền rõ ràng.

### 7.2. AI Chính

AI Chính được phép:

- Tạo và cập nhật thông báo điều hành.
- Quản lý trạng thái phiên và task.
- Tạo contract, baseline, workspace và review bundle.
- Kiểm tra evidence.
- Tích hợp artifact vào source.
- Tạo snapshot và rollback khi cần.
- Ghi quyết định, nhật ký và báo cáo tổng hợp.

### 7.3. Master

Master có quyền yêu cầu, phê duyệt, từ chối, dừng hoặc tiếp tục phiên theo Quy chế V4.0.

Không mặc định yêu cầu mọi AI có quyền ghi tùy ý vào toàn bộ cây thư mục. Quyền thực tế phải được giới hạn bằng hệ thống file, ACL, process hoặc runtime phù hợp khi môi trường hỗ trợ.

## Điều 8. Quy tắc ghi an toàn

1. Không dùng chung một file đầu ra có nhiều agent cùng ghi đồng thời.
2. Không ghi đè kết quả đã nộp mà không lưu lịch sử hoặc phiên bản mới.
3. Dùng ghi file nguyên tử khi cập nhật trạng thái: ghi file tạm, xác minh nội dung, sau đó thay thế file đích theo cơ chế an toàn của hệ điều hành.
4. Kiểm tra JSON bằng parser trước khi chấp nhận trạng thái.
5. Ghi timestamp ISO-8601 kèm múi giờ.
6. Mọi sự kiện quan trọng phải có ID, agent thực hiện, thời gian và kết quả.
7. Không lưu mật khẩu, API key, token hoặc thông tin bí mật trong log, discussion, evidence hay review bundle.
8. Không giả định việc đổi tên file hoặc ghi file nguyên tử tự động giải quyết được mọi tranh chấp giữa nhiều tiến trình. Cần cơ chế khóa và xử lý xung đột phù hợp.

---

# PHẦN III. REGISTRY VÀ ONBOARDING

## Điều 9. Registry agent

File `system/agents_registry.json` phải phản ánh năng lực đã kiểm tra, quyền hạn, phương thức giao tiếp và trạng thái thực tế của từng agent.

Mẫu khởi tạo:

```json
{
  "protocol_version": "11.1",
  "session_id": "SESSION-001",
  "orchestrator_agent_id": "cursor",
  "agents": [
    {
      "agent_id": "cursor",
      "display_name": "Cursor",
      "allowed_roles": [
        "ORCHESTRATOR",
        "VERIFIER",
        "BUILDER",
        "REVIEWER"
      ],
      "watch_mode": "session_poll",
      "wake_method": "human_or_session",
      "can_write_project_src": true,
      "status": "UNKNOWN",
      "last_probe_at": null
    },
    {
      "agent_id": "antigravity",
      "display_name": "Antigravity",
      "allowed_roles": [
        "BUILDER",
        "ANALYST"
      ],
      "watch_mode": "manual_sync",
      "wake_method": "manual_or_file",
      "can_write_project_src": false,
      "status": "UNKNOWN",
      "last_probe_at": null
    },
    {
      "agent_id": "opencode",
      "display_name": "OpenCode",
      "allowed_roles": [
        "REVIEWER",
        "AUDITOR",
        "BUILDER"
      ],
      "watch_mode": "session_poll",
      "wake_method": "human_or_session",
      "can_write_project_src": false,
      "status": "UNKNOWN",
      "last_probe_at": null
    }
  ]
}
```

Đây là cấu hình mẫu, không phải bằng chứng rằng các agent đã được kết nối. `can_write_project_src` thể hiện quyền được cấp trong cấu hình dự kiến; quyền này chỉ có hiệu lực nếu hệ thống thực tế thực thi nó.

## Điều 10. Trạng thái agent

| Trạng thái | Ý nghĩa |
|---|---|
| `UNKNOWN` | Chưa xác minh khả năng hoạt động |
| `PROBING` | Đang kiểm tra kết nối, quyền và giao tiếp |
| `READY` | Đã vượt qua các kiểm tra cần thiết |
| `BUSY` | Đang thực hiện nhiệm vụ |
| `IDLE` | Đã tham gia nhưng hiện không có nhiệm vụ |
| `OFFLINE` | Không thể liên lạc hoặc không còn phiên hoạt động |
| `WATCH_FAILED` | Cơ chế theo dõi đã lỗi |
| `DISABLED` | Bị vô hiệu hóa |
| `QUARANTINED` | Bị cách ly do vi phạm hoặc nghi ngờ mất an toàn |

Chỉ chuyển sang `READY` khi có bằng chứng probe thành công.

Probe tối thiểu gồm:

1. Đọc được file hướng dẫn và trạng thái phiên.
2. Xác định đúng `agent_id`.
3. Xác nhận đúng workspace và quyền ghi.
4. Ghi được file phản hồi vào đúng vùng được phép.
5. Có cơ chế giao tiếp phù hợp với loại nhiệm vụ.
6. Báo cáo trung thực phương thức theo dõi đang sử dụng.
7. Được AI Chính xác nhận tham gia.

## Điều 11. Giao thức onboarding

### 11.1. Điều kiện trước khi mời

AI Chính phải:

- Tạo cấu trúc thư mục cần thiết.
- Tạo file SOP và Quy chế đúng tên.
- Tạo registry ban đầu.
- Tạo `TRANG_THAI.json`, `THONG_BAO.md` và `MASTER_REQUEST.md`.
- Kiểm tra đường dẫn thật trên máy hoặc môi trường làm việc.
- Xác định rõ agent nào đã có khả năng truy cập và agent nào cần Master mở phiên thủ công.

Không phát lời mời với đường dẫn placeholder hoặc đường dẫn không tồn tại.
** gởi cho master "### 11.2. Nội dung Master gửi cho mỗi AI" để master copy gởi cho các AI duy nhất lần đầu để kết nối giao thưc liên lạc file giữa các AI
### 11.2. Nội dung Master gửi cho mỗi AI

```text
Bạn được mời tham gia nhóm Multi-AI.

Bạn phải làm việc theo file điều phối chung trong AI_TEAM/.
AI Chính mặc định là Cursor, trừ khi Master công bố thay đổi.

Hãy thực hiện lần lượt:

1. Đọc JOIN_PROTOCOL.md.
2. Đọc Quy_trinh_van_hanh_chuan_Multi_AI.md.
3. Đọc Quy_che_dieu_hanh_va_phoi_hop_Multi_AI.md.
4. Đọc agents_registry.json.
5. Đọc control/TRANG_THAI.json.
6. Đọc control/THONG_BAO.md.
7. Xác định agent_id và vai trò được cấp.
8. Kiểm tra khả năng đọc/ghi đúng các thư mục được phép.
9. Báo cáo cơ chế giao tiếp và theo dõi thực tế.
10. Ghi xác nhận gia nhập vào discussion/<agent_id>.md.

Không bắt đầu nhiệm vụ nếu chưa có chỉ thị hợp lệ.
Không tự sửa file điều khiển chung.
Không ghi đè workspace của agent khác.
Không tự nhận READY khi chưa kiểm tra.
Không tuyên bố đang theo dõi liên tục nếu không có process thực tế.

Khi nhận STOP:
- Không nhận nhiệm vụ mới.
- Không bắt đầu thay đổi mới.
- Dừng công việc hiện tại theo cách an toàn.
- Ghi trạng thái và công việc còn dang dở.
- Không tự tiếp tục nếu chưa có lệnh CONTINUE hợp lệ.

Nếu không đọc được file, không có quyền truy cập hoặc không thể
duy trì cơ chế theo dõi, hãy báo đúng trạng thái và nguyên nhân.
```

### 11.3. Điều kiện gia nhập thành công

Không coi agent đã gia nhập chỉ vì Master gửi lời mời.

Agent chỉ được xác nhận tham gia khi:

- Có phản hồi được ghi vào đúng file.
- `agent_id` hợp lệ.
- Đã kiểm tra quyền và đường dẫn.
- Có báo cáo probe.
- AI Chính cập nhật registry và thông báo kết quả.

---

# PHẦN IV. BẢNG ĐIỀU KHIỂN VÀ GIAO THỨC THÔNG BÁO

## Điều 12. File trạng thái phiên

File `control/TRANG_THAI.json` là nguồn dữ liệu điều khiển chính thức của phiên.

Mẫu:

```json
{
  "schema_version": "1.0",
  "session_id": "SESSION-001",
  "version": 1,
  "status": "INIT",
  "command": "NONE",
  "reason": "",
  "orchestrator_agent_id": "cursor",
  "updated_at": "2026-10-18T20:00:00+07:00",
  "updated_by": "cursor",
  "last_event_id": "EVT-0001"
}
```

Các trường bắt buộc:

- `session_id`: ID duy nhất của phiên.
- `version`: số phiên bản điều khiển, tăng đơn điệu.
- `status`: trạng thái phiên.
- `command`: lệnh điều khiển gần nhất.
- `reason`: lý do hoặc ngữ cảnh.
- `orchestrator_agent_id`: AI Chính đang được chỉ định.
- `updated_at`: thời gian cập nhật.
- `updated_by`: tác nhân ghi trạng thái.
- `last_event_id`: sự kiện tương ứng trong nhật ký.

Các giá trị `status`:

`INIT` | `RUNNING` | `STOP` | `COMPLETED`

Các giá trị `command`:

`NONE` | `START` | `STOP_ALL` | `CONTINUE` | `COMPLETE_SESSION`

Không coi `command` là cơ chế thực thi độc lập. Agent và runtime phải kiểm tra cả phiên bản, trạng thái, quyền hạn và tính hợp lệ của chuyển trạng thái.

## Điều 13. Quy tắc ưu tiên STOP

Khi phát hiện một lệnh STOP hợp lệ:

1. Ngừng nhận nhiệm vụ mới.
2. Không bắt đầu sửa đổi mới.
3. Dừng hoặc đưa công việc hiện tại về trạng thái an toàn.
4. Không thực hiện tích hợp đang chờ.
5. Ghi lại trạng thái dang dở và vị trí công việc.
6. Báo cáo tiến trình, thay đổi chưa tích hợp và rủi ro còn lại.

STOP ở cấp SOP không bảo đảm mọi process hệ điều hành đã bị kết thúc. Nếu cần dừng tiến trình thực sự, phải sử dụng cơ chế điều khiển process phù hợp và xác minh kết quả.

Nếu STOP đến trong lúc đang thực hiện một thao tác không thể ngắt an toàn, agent phải hoàn thành bước bảo toàn tối thiểu, sau đó dừng. Không được viện lý do an toàn để tiếp tục toàn bộ nhiệm vụ.

## Điều 14. File thông báo điều hành

File `control/THONG_BAO.md` phải chứa thông báo hiện hành và có thể tham chiếu đến lịch sử thông báo.

Mẫu bắt buộc:

```markdown
# THÔNG BÁO ĐIỀU HÀNH

- message_id: MSG-0001
- session_id: SESSION-001
- version: 1
- created_at: 2026-10-18T20:00:00+07:00
- sender: cursor
- status: RUNNING
- phase: DISCUSSION
- recipients:
  - ALL_AGENTS
- task_id: null
- contract_hash: null

## Mục tiêu

[Mô tả mục tiêu cụ thể]

## Yêu cầu Master

[Yêu cầu gốc và giới hạn đã xác nhận]

## Quyết định hiện tại

[Quyết định hoặc nội dung còn chờ]

## Hành động cần thực hiện

1. [Hành động]
2. [Hành động]

## Phân công

- cursor: [Trách nhiệm]
- antigravity: [Trách nhiệm]
- opencode: [Trách nhiệm]

## Đường dẫn

- discussion: AI_TEAM/discussion/
- inbox: AI_TEAM/inbox/
- results: AI_TEAM/results/
- task: [Đường dẫn task nếu có]

## Tiêu chí hoàn thành

- [Tiêu chí đo được]

## Hạn hoặc điều kiện chờ

[Thời hạn hoặc điều kiện]

## Chuyển giai đoạn

[Điều kiện để chuyển sang giai đoạn tiếp theo]
```

Các giai đoạn chuẩn:

`DISCUSSION` → `ASSIGN` → `BUILD` → `REVIEW` → `VERIFY` → `INTEGRATE` → `DONE`

Có thể sử dụng thêm `INCIDENT`, `ROLLBACK`, `PAUSED` hoặc `CANCELLED` khi cần, nhưng phải định nghĩa ý nghĩa và quyền chuyển trạng thái.

## Điều 15. Quy tắc nhận thông báo

Agent phải kiểm tra thông báo trước khi bắt đầu hoặc tiếp tục một bước công việc có tác động.

Agent chỉ được xử lý thông báo khi:

- Đúng `session_id`.
- Phiên không ở trạng thái STOP.
- Agent thuộc danh sách nhận hoặc được phép nhận thông báo chung.
- Nhiệm vụ chưa bị thay thế hoặc hủy.
- Contract và quyền thực thi còn hợp lệ.

Nếu `version` đã tăng, agent phải đọc lại thông báo hiện hành và đánh giá xem nhiệm vụ của mình có thay đổi hay không.

Nếu thông báo bị lỗi định dạng, mâu thuẫn hoặc không thể xác thực, agent phải dừng phần việc có rủi ro và yêu cầu AI Chính làm rõ.

---

# PHẦN V. LUỒNG VẬN HÀNH CHUẨN

## Điều 16. Giai đoạn 1 — Tiếp nhận yêu cầu

Master cung cấp mục tiêu, yêu cầu và các giới hạn đã biết.

AI Chính phải:

1. Ghi yêu cầu vào `control/MASTER_REQUEST.md`.
2. Tạo ID cho yêu cầu hoặc phiên.
3. Phân loại nhiệm vụ: thảo luận, phân tích, tài liệu, code, vận hành hoặc hỗn hợp.
4. Xác định phạm vi, đầu ra mong muốn và tiêu chí nghiệm thu.
5. Xác định rủi ro, quyền truy cập và các quyết định cần Master phê duyệt.
6. Kiểm tra trạng thái các agent.
7. Phát thông báo giai đoạn `DISCUSSION`.

Nếu yêu cầu chưa đủ rõ, AI Chính có thể đưa ra giả định được ghi rõ hoặc hỏi Master về điểm có ảnh hưởng trọng yếu. Không tự biến giả định thành yêu cầu đã được phê duyệt.

## Điều 17. Giai đoạn 2 — Thảo luận độc lập

Các agent nhận chỉ thị sẽ đọc yêu cầu gốc và viết ý kiến vào file discussion riêng.

Mỗi ý kiến nên bao gồm:

- Hiểu biết về mục tiêu.
- Phương án đề xuất.
- Lý do và bằng chứng.
- Rủi ro và giới hạn.
- Phần việc có thể đảm nhận.
- Các giả định cần xác minh.
- Những điểm không đồng ý với phương án khác.

Các agent được phép phản biện lẫn nhau thông qua file, nhưng không được sửa file discussion của agent khác.

AI Chính phải phân biệt dữ kiện đã xác minh, giả định, ý kiến và kết luận. Không quyết định chỉ dựa vào số lượng agent đồng ý.

## Điều 18. Giai đoạn 3 — Tổng hợp và quyết định

AI Chính tổng hợp các phương án, xác định điểm thống nhất, mâu thuẫn và khoảng trống bằng chứng.

Trước khi giao việc, AI Chính phải:

1. Chốt phạm vi và tiêu chí nghiệm thu.
2. Chốt contract.
3. Xác định agent chịu trách nhiệm chính.
4. Xác định reviewer độc lập nếu cần.
5. Chạy Conflict Gate.
6. Tạo baseline và workspace nếu nhiệm vụ thay đổi code.
7. Phát thông báo giai đoạn `ASSIGN`.

Mọi quyết định quan trọng phải được ghi trong `control/DECISIONS.md`, kèm lý do, người quyết định và bằng chứng liên quan.

## Điều 19. Giai đoạn 4 — Giao nhiệm vụ

Mỗi nhiệm vụ phải có file riêng, ví dụ:

`AI_TEAM/inbox/antigravity/TASK-001.md`

Nội dung tối thiểu:

```markdown
# TASK-001

- session_id: SESSION-001
- task_id: TASK-001
- assigned_to: antigravity
- role: BUILDER
- status: ASSIGNED
- contract_path: AI_TEAM/tasks/TASK-001/contract/master_spec.json
- contract_hash: [SHA-256]
- baseline_id: BASELINE-TASK-001
- workspace_path: [Đường dẫn thật]
- created_at: [ISO-8601]
- deadline: [ISO-8601 hoặc điều kiện]
- reviewer: opencode

## Mục tiêu

[Mục tiêu cụ thể]

## Phạm vi được phép

[Phạm vi file hoặc artifact]

## Phạm vi không được phép

[Giới hạn]

## Acceptance tests

[Danh sách bài kiểm tra]

## Evidence bắt buộc

[Danh sách bằng chứng]

## Điều kiện báo cáo

[Điều kiện PASS nội bộ, BLOCKED, NEEDS_CLARIFICATION]

## Quy tắc kết thúc

Không tự tích hợp vào source chính.
Nộp kết quả, evidence và báo cáo theo đúng quy trình.
```

Agent được giao phải xác nhận đã nhận nhiệm vụ và nêu rõ nếu không đủ quyền, không đủ năng lực hoặc không thể đáp ứng thời hạn.

## Điều 20. Giai đoạn 5 — Thực thi

Builder chỉ thực hiện nhiệm vụ trong workspace được giao.

Trong quá trình làm việc, Builder phải:

- Tuân thủ contract và baseline.
- Không sửa ngoài phạm vi.
- Không thay đổi tiêu chí nghiệm thu.
- Không tự thêm thư viện, dependency hoặc quyền hệ thống ngoài phạm vi được duyệt.
- Ghi lại lệnh kiểm tra và kết quả.
- Báo sớm khi phát hiện lỗi nền tảng hoặc yêu cầu mâu thuẫn.
- Tạo evidence có thể kiểm tra độc lập.

Nếu cần thay đổi yêu cầu, Builder phải gửi CHANGE_REQUEST và chờ phê duyệt khi thay đổi vượt quyền được cấp.

## Điều 21. Giai đoạn 6 — Đóng gói kết quả

Khi hoàn tất, Builder phải:

1. Kiểm tra lại danh sách file thay đổi.
2. Tính hash cho các file liên quan.
3. Chạy các bài kiểm tra đã quy định.
4. Ghi exit code và đường dẫn log.
5. Tạo `evidence.json`.
6. Viết báo cáo vào `results/<agent_id>/`.
7. Chuyển task sang trạng thái chờ review.

Không được tự chuyển nhiệm vụ sang `COMPLETED`.

## Điều 22. Giai đoạn 7 — Review độc lập

AI Chính tạo review bundle từ artifact đã nộp, kèm manifest và hash.

Reviewer phải đọc bundle được chỉ định, không review một workspace khác hoặc source đã thay đổi sau khi đóng gói.

Verdict hợp lệ:

- `PASS`: đạt tiêu chí review.
- `FAIL`: có lỗi hoặc vi phạm điều kiện bắt buộc.
- `NEEDS_REVISION`: cần sửa hoặc bổ sung bằng chứng.
- `BLOCKED`: không đủ dữ liệu hoặc môi trường để kết luận.

Reviewer phải nêu căn cứ cho từng lỗi quan trọng. Nếu không chạy được test, phải ghi rõ chưa chạy; không được diễn đạt như đã xác minh.

## Điều 23. Giai đoạn 8 — Verify và tích hợp

Sau review, AI Chính phải:

1. Xác thực manifest và hash.
2. Kiểm tra evidence.
3. Tự chạy acceptance tests trên artifact dự kiến tích hợp.
4. Xác nhận trạng thái `VERIFIED`.
5. Tạo snapshot source trước khi thay đổi.
6. Tích hợp artifact.
7. Chạy regression trên source sau tích hợp.
8. Xác nhận trạng thái `COMPLETED` nếu mọi gate đều đạt.

Nếu bất kỳ gate bắt buộc nào thất bại, không được chuyển sang `COMPLETED`.

## Điều 24. Giai đoạn 9 — Tổng kết

AI Chính ghi báo cáo kết thúc gồm:

- Mục tiêu ban đầu.
- Kết quả đạt được.
- Những nhiệm vụ hoàn thành, chưa hoàn thành và bị chặn.
- Các file hoặc artifact đã thay đổi.
- Bằng chứng xác minh.
- Kết quả regression.
- Các quyết định của Master.
- Rủi ro còn lại.
- Snapshot và thông tin rollback.
- Đề xuất bước tiếp theo.

Sau khi kết thúc, AI Chính cập nhật thông báo và trạng thái phiên.

---

# PHẦN VI. QUẢN LÝ TASK VÀ TRẠNG THÁI

## Điều 25. Trạng thái nhiệm vụ

Mỗi task phải có trạng thái riêng trong `task_state.json`.

Các trạng thái chuẩn:

`CREATED` → `ASSIGNED` → `ACKNOWLEDGED` → `BUILD` → `SUBMITTED` → `REVIEW` → `VERIFIED` → `INTEGRATED` → `COMPLETED`

Các trạng thái phụ:

`BLOCKED`, `NEEDS_REVISION`, `TIMEOUT`, `CANCELLED`, `ROLLBACK_REQUIRED`, `ROLLED_BACK`, `FAILED`.

Chỉ cho phép các chuyển trạng thái phù hợp với trạng thái hiện tại. Không cho phép nhảy trực tiếp từ `BUILD` sang `COMPLETED` hoặc từ `PASS` sang `COMPLETED`.

## Điều 26. Mẫu task_state.json

```json
{
  "schema_version": "1.0",
  "session_id": "SESSION-001",
  "task_id": "TASK-001",
  "status": "CREATED",
  "assigned_to": "antigravity",
  "reviewer": "opencode",
  "contract_hash": "",
  "baseline_id": "BASELINE-TASK-001",
  "workspace_path": "",
  "review_bundle_hash": "",
  "snapshot_id": null,
  "created_at": "2026-10-18T20:00:00+07:00",
  "updated_at": "2026-10-18T20:00:00+07:00",
  "updated_by": "cursor",
  "last_event_id": "EVT-0001",
  "failure_reason": null
}
```

Giá trị hash và đường dẫn phải được điền bằng dữ liệu thực tế. Không để trường bắt buộc trống khi task đã chuyển sang giai đoạn cần trường đó.

---

# PHẦN VII. GATE KỸ THUẬT BẮT BUỘC KHI SỬA CODE

## Điều 27. Gate A — Contract và Baseline (P0)

Gate A phải đạt trước khi giao nhiệm vụ sửa code.

### 27.1. Contract bất biến

Tạo:

`tasks/TASK-X/contract/master_spec.json`

và:

`tasks/TASK-X/contract/contract_hash.txt`

Contract tối thiểu phải xác định:

- `session_id`
- `task_id`
- Mục tiêu.
- Phạm vi được phép.
- Phạm vi bị cấm.
- `owned_files`.
- Acceptance tests.
- Dependency và giới hạn môi trường.
- Ngân sách hoặc thời hạn nếu áp dụng.
- Evidence bắt buộc.
- Quy tắc nghiệm thu.
- Điều kiện phải xin Master phê duyệt.

Tính SHA-256 trên đúng byte của file contract đã chốt, sau đó ghi kết quả vào `contract_hash.txt`.

Không chỉnh sửa contract sau khi đã đóng băng. Nếu thay đổi, tạo phiên bản contract mới, hash mới và ghi nhận quyết định phê duyệt.

### 27.2. Baseline

Baseline phải phản ánh source tại thời điểm giao nhiệm vụ.

Có thể sử dụng:

- Snapshot toàn bộ source; hoặc
- Snapshot phạm vi chọn lọc kèm manifest đầy đủ và hash.

Nếu dùng baseline chọn lọc, phải bao gồm tất cả file có thể ảnh hưởng đến việc kiểm tra task, bao gồm dependency, cấu hình và các file liên quan trực tiếp khi cần.

### 27.3. Workspace

Tạo workspace riêng cho Builder từ baseline đã xác minh.

Không dùng workspace đang chứa thay đổi của agent khác làm nguồn khởi tạo mặc định.

### 27.4. Kiểm tra hợp đồng

Task package chỉ hợp lệ khi bind đầy đủ:

`task_id`, `agent_id`, `role`, `contract_hash`, `baseline_id`, `owned_files`, `acceptance_tests`, `deadline` hoặc điều kiện hoàn tất tương đương, `workspace_path` và nơi nộp evidence.

Nếu thiếu trường bắt buộc, task chưa được phép chuyển sang `BUILD`.

## Điều 28. Gate B — Conflict Gate (P0)

Trước khi giao task mới, AI Chính phải kiểm tra toàn bộ task đang ở trạng thái `ASSIGNED`, `BUILD`, `SUBMITTED` chưa xử lý hoặc trạng thái khác còn quyền ghi.

Quy tắc:

1. So sánh `owned_files` của task mới với task đang hoạt động.
2. Nếu có đường dẫn trùng, không giao song song theo mặc định.
3. Nếu đường dẫn là thư mục cha hoặc thư mục con của nhau, coi là xung đột tiềm năng.
4. Chuẩn hóa đường dẫn trước khi so sánh, kể cả dấu phân cách và quy tắc chữ hoa/chữ thường phù hợp với hệ điều hành.
5. Chỉ cho phép song song khi đã chứng minh được tính độc lập hoặc có cơ chế điều phối xung đột được phê duyệt.
6. Ghi kết quả kiểm tra vào nhật ký.

Không coi việc hai agent sửa hai file khác tên là đủ chứng minh không xung đột nếu chúng cùng sửa dependency, schema, cấu hình, generated files hoặc các thành phần dùng chung.

## Điều 29. Gate C — Evidence và Provenance (P0)

Mỗi nhiệm vụ sửa code phải có `evidence.json`.

Mẫu:

```json
{
  "schema_version": "1.0",
  "session_id": "SESSION-001",
  "task_id": "TASK-001",
  "from": "antigravity",
  "contract_hash": "<SHA-256 thực tế>",
  "baseline_id": "BASELINE-TASK-001",
  "workspace_path": "<đường dẫn thật>",
  "changed_files": [
    {
      "path": "src/example.py",
      "sha256": "<SHA-256 thực tế>"
    }
  ],
  "test_commands": [
    {
      "command": "<lệnh thực tế>",
      "exit_code": 0,
      "log_path": "evidence/logs/test-001.log"
    }
  ],
  "diff_summary": {
    "baseline_id": "BASELINE-TASK-001",
    "changed_files_count": 1,
    "added_files": 0,
    "modified_files": 1,
    "deleted_files": 0
  },
  "created_at": "2026-10-18T20:00:00+07:00"
}
```

Đây là cấu trúc minh họa; các placeholder phải được thay bằng dữ liệu thực tế trước khi nghiệm thu.

Evidence tối thiểu phải thể hiện:

- Task và agent nguồn.
- Hash contract.
- Baseline.
- Workspace.
- Danh sách file thay đổi và hash.
- Lệnh kiểm tra thực tế.
- Exit code.
- Đường dẫn log.
- Diff so với baseline.

Thiếu trường bắt buộc, hash không khớp hoặc không xác định được nguồn gốc artifact thì từ chối nghiệm thu.

Báo cáo Markdown chỉ hỗ trợ người đọc. Nó không thay thế evidence máy có thể kiểm tra.

## Điều 30. Gate D — Immutable Review Bundle (P0)

AI Chính tạo review bundle từ artifact đã nộp.

Bundle phải chứa:

- Bản sao nguyên vẹn của artifact cần review.
- `manifest.json`.
- Hash SHA-256 cho từng file thuộc phạm vi review.
- Contract hash.
- Baseline ID.
- Task ID.
- Danh sách file thay đổi.
- Thông tin redaction nếu có.

Không được xóa comment, định dạng lại code, đổi tên biến hoặc sửa nội dung trong lúc đóng gói review.

Nếu cần che secret, phải áp dụng quy tắc redaction đã định nghĩa, ghi rõ file và vùng bị che. Artifact đã redaction không được tuyên bố là bản sao byte-for-byte của file gốc.

Sau khi bundle được chốt:

1. Không chỉnh sửa nội dung bundle.
2. Không cho Reviewer sửa bundle.
3. Nếu cần thay đổi artifact, tạo bundle phiên bản mới.
4. Trước khi tích hợp, tính lại hash.
5. Hash không khớp manifest thì hủy lần tích hợp đang xét và điều tra nguồn thay đổi.

Manifest giúp phát hiện sai lệch, nhưng không tự chứng minh tác giả hoặc thời điểm tạo nếu không có cơ chế ký hay kiểm soát provenance bổ sung.

## Điều 31. Gate E — Timeout và workspace mới (P0)

Khi task quá thời hạn hoặc agent mất liên lạc:

1. Chuyển task sang `TIMEOUT` hoặc trạng thái phù hợp.
2. Ngừng cấp quyền ghi mới nếu runtime hỗ trợ.
3. Thu thập log và diff hiện có.
4. Ghi nhận trạng thái cuối cùng có thể xác minh.
5. Đánh dấu workspace cũ là không còn đủ điều kiện làm nguồn sạch.
6. Không tái sử dụng workspace cũ để tiếp tục như chưa từng có sự cố.
7. Khi giao lại, tạo workspace mới từ baseline đã xác minh.

Nếu hệ điều hành không bảo đảm được việc khóa workspace, phải ghi rõ giới hạn. Không tuyên bố workspace đã bị khóa hoặc process đã chết khi chưa kiểm tra thực tế.

## Điều 32. Gate F — Verify → Snapshot → Integrate → Regression (P0)

Đây là trình tự bắt buộc đối với nhiệm vụ sửa code có tích hợp vào source chính.

### Bước 1. Review

Reviewer độc lập hoàn thành đánh giá và ghi verdict.

Nếu Reviewer không sẵn sàng, phải chỉ định người review thay thế đủ điều kiện hoặc chuyển task sang `BLOCKED`. Không tự tạo verdict PASS thay cho reviewer.

### Bước 2. Verify artifact

AI Chính tự kiểm tra:

- Contract hash.
- Baseline ID.
- Evidence.
- Manifest.
- Hash artifact.
- Phạm vi file.
- Acceptance tests.
- Các điều kiện an toàn liên quan.

Chỉ chuyển sang `VERIFIED` khi các điều kiện bắt buộc đã đạt.

### Bước 3. Snapshot source trước tích hợp

Tạo snapshot toàn vùng source đang được quản lý trước khi thay đổi.

Snapshot phải có:

- Snapshot ID.
- Thời gian.
- Task ID.
- Phạm vi được chụp.
- Manifest và hash.
- Vị trí lưu trữ.
- Kết quả kiểm tra khả năng khôi phục.

Nếu snapshot không được tạo hoặc không thể xác minh, không được tiếp tục tích hợp theo quy trình chuẩn.

### Bước 4. Integrate

Chỉ AI Chính được thực hiện tích hợp vào source chính theo mô hình mặc định của SOP.

Trước khi ghi, kiểm tra lại hash của artifact so với review bundle.

Chỉ chuyển sang `INTEGRATED` sau khi xác nhận các thay đổi dự kiến đã được áp dụng đúng phạm vi.

### Bước 5. Regression

Chạy các bài kiểm tra bắt buộc trên source sau tích hợp, không chỉ trên workspace riêng.

Ghi lại lệnh, exit code, log và kết quả.

### Bước 6. Kết luận

- Regression đạt: có thể chuyển sang `COMPLETED`.
- Regression thất bại: chuyển sang `ROLLBACK_REQUIRED` hoặc trạng thái xử lý lỗi tương ứng.
- Có lỗi chưa xác định: giữ task ở trạng thái chưa hoàn thành và báo Master nếu ảnh hưởng đáng kể.

### Bước 7. Rollback

Nếu cần rollback:

1. Dừng các hoạt động tích hợp liên quan.
2. Xác định snapshot chính xác.
3. Khôi phục theo quy trình an toàn.
4. Xác minh source sau khôi phục.
5. Chạy bài kiểm tra hậu rollback.
6. Ghi kết quả và báo Master.

Rollback chỉ được coi là thành công khi source đã khôi phục được xác minh. Không coi việc copy snapshot trở lại là bằng chứng đủ nếu chưa kiểm tra kết quả.

**Chuỗi trạng thái bắt buộc:**

`REVIEW_PASS` → `VERIFIED` → `INTEGRATED` → `REGRESSION_PASS` → `COMPLETED`

---

# PHẦN VIII. THẢO LUẬN, PHẢN BIỆN VÀ RA QUYẾT ĐỊNH

## Điều 33. Nguyên tắc thảo luận

Các agent phải đưa ra nhận định độc lập trước khi AI Chính chốt phương án, trừ trường hợp khẩn cấp hoặc nhiệm vụ quá đơn giản để cần nhiều vòng thảo luận.

Thảo luận phải tập trung vào:

- Bằng chứng.
- Tính đúng đắn.
- Phương án thay thế.
- Tác động và rủi ro.
- Khả năng triển khai.
- Điều kiện kiểm chứng.

Không dùng số lượng ý kiến đồng thuận làm tiêu chí duy nhất.

## Điều 34. Giải quyết bất đồng

Khi các agent bất đồng:

1. AI Chính xác định chính xác điểm tranh chấp.
2. Yêu cầu từng bên cung cấp bằng chứng.
3. Phân biệt tranh chấp về yêu cầu, thiết kế, dữ kiện hay kết quả kiểm thử.
4. Nếu cần, giao một agent độc lập tái hiện vấn đề.
5. Ưu tiên kết quả kiểm thử có thể lặp lại và bằng chứng trực tiếp.
6. Ghi quyết định cuối cùng cùng lý do.

Nếu chưa đủ dữ liệu, trạng thái phải là `BLOCKED` hoặc `NEEDS_CLARIFICATION`, không được ép kết luận.

## Điều 35. Yêu cầu thay đổi (CHANGE_REQUEST)

Mọi đề xuất vượt contract phải được ghi thành yêu cầu thay đổi.

Nội dung tối thiểu:

- ID.
- Task liên quan.
- Người đề xuất.
- Nội dung thay đổi.
- Lý do.
- Phạm vi ảnh hưởng.
- Tác động đến baseline, dependency, test và thời hạn.
- Rủi ro.
- Người có thẩm quyền phê duyệt.
- Quyết định cuối cùng.

Không cho phép agent tự mở rộng `owned_files`, thêm dependency, đổi tiêu chí nghiệm thu hoặc thay đổi quyền thực thi chỉ vì cho rằng cần thiết.

Nếu được phê duyệt, AI Chính cập nhật contract theo phiên bản mới và tạo hash tương ứng trước khi tiếp tục.

---

# PHẦN IX. DẪN CHIẾU QUY CHẾ V4.0 VÀ XỬ LÝ SỰ CỐ

## Điều 36. Nguyên tắc trích dẫn luật

File `system/LAW_POINTER.md` phải chỉ tới đúng bản Quy chế V4.0 được phê duyệt.

Khi xử lý sự cố:

1. Mở văn bản gốc.
2. Xác định chính xác Điều áp dụng.
3. Đối chiếu toàn bộ ngữ cảnh liên quan.
4. Trích đúng số Điều và một đoạn nguyên văn ngắn.
5. Nêu hành động theo Quy chế và SOP.
6. Ghi nguồn, thời điểm và quyết định vào nhật ký.

Không được coi số Điều trong bảng dưới đây là bằng chứng độc lập rằng nội dung Điều đó đã được xác minh. Các dẫn chiếu phải được đối chiếu với đúng văn bản V4.0 trước khi áp dụng.

## Điều 37. Bảng xử lý sự cố

| Tình huống | Điều cần đối chiếu theo chỉ mục | Hành động ban đầu |
|---|---|---|
| Sửa ngoài phạm vi hoặc ngoài `owned_files` | Điều 33, 16 | Tạm dừng nghiệm thu; xác định file và tác động; yêu cầu làm lại trong workspace mới nếu cần |
| Timeout | Điều 24 | Thu thập evidence, đánh dấu workspace cũ, tạo workspace mới từ baseline |
| Tranh chấp PASS/FAIL | Điều 27, 18 | Chạy lại test trong môi trường được xác định rõ; ghi kết quả và điều kiện tái hiện |
| Đòi đổi contract, thêm thư viện hoặc vượt quyền | Điều 34, 35 | Tạo CHANGE_REQUEST; không thực hiện phần vượt quyền trước khi được duyệt |
| Regression sau tích hợp | Điều 20, 32 | Dừng thay đổi tiếp theo; rollback theo snapshot và xác minh hậu rollback |
| Agent không phản hồi | Tra cứu Điều liên quan trong V4.0 | Kiểm tra watcher, phiên, quyền truy cập và heartbeat; không tự kết luận agent đang hoạt động |
| Hash review bundle không khớp | Tra cứu Điều liên quan trong V4.0 | Hủy lần tích hợp đang xét; kiểm tra provenance và tạo bundle mới nếu được phép |
| Không thể xác minh artifact | Tra cứu Điều liên quan trong V4.0 | Chuyển sang BLOCKED; không tuyên bố hoàn thành |

### Mẫu ghi nhận sự cố

```markdown
# INCIDENT-001

- session_id: SESSION-001
- incident_id: INCIDENT-001
- detected_at: [ISO-8601]
- detected_by: [agent_id]
- severity: [LOW / MEDIUM / HIGH / CRITICAL]
- affected_tasks: [TASK-ID]

## Mô tả

[Mô tả sự cố]

## Bằng chứng

[File, log, hash, lệnh hoặc kết quả kiểm tra]

## Quy chế áp dụng

- File nguồn: [đường dẫn Quy chế V4.0]
- Điều: [số Điều đã xác minh]
- Trích nguyên văn: "[đoạn trích chính xác]"

## Hành động đã thực hiện

[Hành động]

## Trạng thái hiện tại

[Trạng thái]

## Quyết định cần Master

[Nếu có]

## Điều kiện đóng sự cố

[Tiêu chí kiểm chứng]
```

Không điền trích dẫn luật bằng suy đoán. Nếu chưa đọc được văn bản gốc, ghi rõ `LAW_REFERENCE_UNVERIFIED` và áp dụng biện pháp an toàn tạm thời trong phạm vi quyền hạn.

---

# PHẦN X. STOP, CONTINUE VÀ KẾT THÚC PHIÊN

## Điều 38. STOP

Khi Master yêu cầu dừng, AI Chính phải:

1. Xác nhận yêu cầu.
2. Tăng `version`.
3. Cập nhật `status=STOP`.
4. Đặt `command=STOP_ALL`.
5. Ghi lý do và người yêu cầu.
6. Phát thông báo mới cho các agent.
7. Kiểm tra trạng thái task và các tiến trình có liên quan trong phạm vi khả năng thực tế.
8. Theo dõi việc xác nhận dừng của từng agent.

Agent khi nhận STOP phải dừng nhận việc mới, dừng sửa đổi mới và bảo toàn trạng thái công việc hiện tại.

Nếu agent không phản hồi, AI Chính ghi nhận agent đó là `OFFLINE` hoặc `WATCH_FAILED` khi có đủ căn cứ. Không giả định rằng lệnh đã được nhận.

## Điều 39. CONTINUE

Chỉ tiếp tục sau khi có lệnh CONTINUE hợp lệ.

AI Chính phải:

1. Đọc trạng thái phiên và các task còn dang dở.
2. Xác định workspace nào còn an toàn.
3. Xác định task nào cần tạo lại workspace.
4. Kiểm tra registry và watcher.
5. Kiểm tra các yêu cầu mới.
6. Cập nhật phiên bản trạng thái.
7. Đặt `status=RUNNING`, `command=CONTINUE`.
8. Phát thông báo mới.
9. Chỉ giao tiếp tục những task đủ điều kiện.

CONTINUE không tự động làm sống lại process đã chết. Việc khởi động lại phải do session, script, dispatcher hoặc người vận hành thực hiện và xác minh.

## Điều 40. Hoàn thành phiên

Chỉ đặt `status=COMPLETED` khi:

- Các mục tiêu bắt buộc đã được xử lý.
- Không còn task bắt buộc chưa giải quyết.
- Các artifact cần tích hợp đã qua gate.
- Regression bắt buộc đã đạt.
- Các lỗi và rủi ro còn lại đã được ghi nhận.
- Báo cáo tổng kết đã được tạo.
- Không có lệnh STOP hoặc yêu cầu đang chờ xử lý.

Nếu còn việc chưa hoàn tất, phải ghi rõ trạng thái và không tuyên bố toàn phiên đã hoàn thành.

---

# PHẦN XI. THEO DÕI LIÊN TỤC VÀ RUNTIME

## Điều 41. Phân biệt đọc file và theo dõi thực sự

Việc một agent có thể đọc file khi được yêu cầu không đồng nghĩa với việc agent đang theo dõi liên tục.

Các phương thức hợp lệ:

- `external_script`: tiến trình bên ngoài kiểm tra file và điều phối.
- `native_watcher`: watcher hệ điều hành theo dõi thay đổi file.
- `session_poll`: agent hoặc runtime chủ động kiểm tra theo chu kỳ khi phiên còn hoạt động.
- `manual_sync`: chỉ kiểm tra khi có người mở hoặc đồng bộ phiên.
- `http_dispatch_or_session_poll`: có dispatcher thực sự hoặc polling khi phiên hoạt động.

Không sử dụng `manual_sync` để tuyên bố tự động theo dõi 24/24.

## Điều 42. Heartbeat và health check

Nếu triển khai heartbeat, mỗi bản ghi phải thể hiện tối thiểu:

- `session_id`
- `agent_id`
- `timestamp`
- `status`
- `watch_mode`
- `last_seen_message_version`
- `last_task_id`
- `error` nếu có.

Heartbeat chỉ chứng minh một thành phần đã phát bản ghi tại thời điểm đó. Nó không tự chứng minh AI còn nhận thức, hiểu thông báo mới hoặc đang thực thi nhiệm vụ đúng.

Cần phân biệt:

- Agent còn phiên hoạt động.
- Watcher còn hoạt động.
- Agent đã đọc thông báo.
- Agent đã xác nhận nhận nhiệm vụ.
- Task đã thực sự được thực thi.

Các trạng thái này không được gộp thành một cờ `READY` duy nhất nếu cần giám sát đáng tin cậy.

## Điều 43. Runtime enforcement

Các quy tắc quan trọng nên được cưỡng chế bằng cơ chế thực thi, thay vì chỉ ghi trong tài liệu.

Ưu tiên triển khai:

1. Xác thực schema của file điều khiển.
2. Kiểm tra quyền ghi theo agent.
3. Khóa task và kiểm soát cập nhật đồng thời.
4. Conflict Gate tự động.
5. Xác thực contract hash.
6. Tạo manifest và xác minh artifact.
7. Kiểm tra acceptance tests.
8. Snapshot trước tích hợp.
9. Regression sau tích hợp.
10. Ghi nhật ký các chuyển trạng thái.

Trước khi tạo runtime mới, AI Chính phải audit các thành phần đang tồn tại và xác định phần nào có thể tái sử dụng. Không xây dựng controller hoặc state machine trùng lặp khi một cơ chế hiện có đã đáp ứng yêu cầu và vượt qua kiểm thử.

---

# PHẦN XII. CHECKLIST NGHIỆM THU KHẢ NĂNG TỰ VẬN HÀNH

## Điều 44. Checklist bắt buộc

### A. Hạ tầng và onboarding

- [ ] Các agent truy cập được cùng cây `AI_TEAM/`.
- [ ] Đường dẫn thực tế đã được kiểm tra.
- [ ] Agent có `agent_id` duy nhất.
- [ ] Probe đọc/ghi đã thành công.
- [ ] Registry phản ánh đúng trạng thái thực tế.
- [ ] Quyền ghi được giới hạn theo vai trò.
- [ ] Không có hai Orchestrator cùng điều khiển một phiên.

### B. Điều phối

- [ ] AI Chính tạo và cập nhật thông báo đúng phiên bản.
- [ ] Agent nhận biết thông báo mới và kiểm tra đối tượng nhận.
- [ ] STOP được ưu tiên hơn task đang chờ.
- [ ] CONTINUE không tự khởi động agent đã chết.
- [ ] Có nhật ký quyết định và lịch sử sự kiện.
- [ ] Có cơ chế xử lý file lỗi hoặc cập nhật đồng thời.

### C. An toàn code

- [ ] Contract có hash xác minh được.
- [ ] Baseline được đóng băng.
- [ ] Workspace riêng được tạo từ baseline.
- [ ] Conflict Gate phát hiện trùng hoặc giao nhau giữa các đường dẫn.
- [ ] Evidence có provenance và log.
- [ ] Review bundle có manifest và hash.
- [ ] Reviewer kiểm tra đúng artifact đã đóng gói.
- [ ] AI Chính tự verify trước khi tích hợp.
- [ ] Snapshot trước tích hợp đã được kiểm tra.
- [ ] Regression chạy trên source sau tích hợp.
- [ ] Rollback đã được thử nghiệm và có kiểm tra hậu rollback.

### D. Theo dõi và phục hồi

- [ ] Phương thức watch được kiểm chứng thực tế.
- [ ] Có thể phát hiện watcher chết.
- [ ] Có thể phát hiện agent mất phản hồi.
- [ ] Có quy trình restart hoặc khởi tạo lại.
- [ ] Có cách thu thập log và xác định trạng thái task sau sự cố.
- [ ] Có thử nghiệm STOP khi agent đang thực thi.
- [ ] Có thử nghiệm lỗi trong lúc tích hợp.
- [ ] Có thử nghiệm khôi phục snapshot.
- [ ] Có quy trình xử lý trạng thái không xác định.

### E. Nghiệm thu tổng thể

- [ ] Các tình huống quan trọng đã được chạy thử.
- [ ] Không có trường hợp tuyên bố hoàn thành khi gate bắt buộc chưa đạt.
- [ ] Kết quả kiểm thử có log và bằng chứng.
- [ ] Các giới hạn còn lại được công bố rõ ràng.

## Điều 45. Mức độ trưởng thành

| Mức | Tiêu chí | Kết luận |
|---|---|---|
| L0 — Documented | Chỉ có SOP và hướng dẫn | Chưa có hệ thống điều phối thực tế |
| L1 — File-based | Agent có thể đọc/ghi file khi được kích hoạt | Phối hợp bằng file, chưa tự vận hành liên tục |
| L2 — Coordinated | Có phân công, trạng thái, conflict check và review | Điều phối có kiểm soát |
| L3 — Runtime-enforced | Gate quan trọng được runtime kiểm tra và thực thi | Có cưỡng chế kỹ thuật |
| L4 — Recovery-tested | Đã kiểm thử STOP, timeout, lỗi tích hợp và rollback | Có khả năng phục hồi đã được chứng minh |

Chỉ công nhận mức cao nhất mà toàn bộ tiêu chí bắt buộc của mức đó đã được kiểm thử và có bằng chứng. Không suy ra L3 hoặc L4 chỉ từ việc đã viết đủ file cấu hình.

---

# PHẦN XIII. QUY TẮC MỞ RỘNG VÀ THAY ĐỔI HỆ THỐNG

## Điều 46. Onboarding agent mới

Agent mới phải được đăng ký qua quy trình onboarding, không tự động được trao quyền vì xuất hiện trong thư mục hoặc tự khai báo vai trò.

Quy trình gồm:

1. Khai báo agent ID.
2. Xác định vai trò.
3. Xác định phạm vi truy cập.
4. Xác minh khả năng đọc/ghi.
5. Kiểm tra phương thức giao tiếp.
6. Kiểm tra watcher hoặc cơ chế kích hoạt.
7. Chạy bài test mẫu.
8. Cập nhật registry.
9. Công bố cho nhóm.

Mặc định agent mới không được quyền ghi vào source chính.

## Điều 47. Thay đổi Orchestrator

Chỉ Master được chỉ định thay đổi Orchestrator theo quy trình điều hành.

Khi chuyển từ Cursor sang agent khác:

1. Dừng việc cấp task mới.
2. Ghi lại trạng thái phiên và task.
3. Xác định các file điều khiển đang được cập nhật.
4. Xác nhận không còn thao tác ghi đồng thời.
5. Master công bố Orchestrator mới.
6. Cập nhật registry và thông báo.
7. Kiểm tra quyền và năng lực agent mới.
8. Chỉ tiếp tục sau khi quyền điều khiển đã được bàn giao rõ ràng.

Không cho phép hai Orchestrator cùng ghi `THONG_BAO.md` hoặc `TRANG_THAI.json`.

## Điều 48. Quản lý phiên bản SOP

Mọi thay đổi SOP phải ghi nhận:

- Phiên bản trước và sau.
- Nội dung thay đổi.
- Lý do.
- Phạm vi ảnh hưởng.
- Tương thích với giao thức và runtime.
- Người phê duyệt.
- Ngày áp dụng.

SOP V10 là phiên bản tài liệu vận hành. Giao thức file 11.1 là lớp tham chiếu tương thích được khai báo riêng; không được tự động đổi tên SOP thành V11.1 chỉ vì sử dụng protocol 11.1.

Nếu SOP và runtime không còn tương thích, phải xác định rõ thành phần cần nâng cấp trước khi vận hành các chức năng phụ thuộc.

---

# PHẦN XIV. PHÂN CÔNG TRÁCH NHIỆM CUỐI CÙNG

## Điều 49. Trách nhiệm của Master

Master:

- Xác định mục tiêu và giới hạn.
- Cung cấp thông tin cần thiết.
- Phê duyệt những quyết định vượt quyền.
- Có quyền yêu cầu dừng hoặc tiếp tục.
- Xem xét báo cáo tổng hợp.
- Quyết định các thay đổi có rủi ro hoặc ảnh hưởng lớn theo Quy chế.

Master không bắt buộc phải chuyển từng thông điệp giữa các agent.

## Điều 50. Trách nhiệm của AI Chính

AI Chính:

- Duy trì trạng thái điều hành chính thức.
- Tổ chức thảo luận và phản biện.
- Phân vai, tạo task và kiểm tra xung đột.
- Bảo đảm contract và baseline hợp lệ.
- Kiểm tra evidence và review bundle.
- Xác minh artifact trước khi tích hợp.
- Thực hiện hoặc điều phối rollback trong phạm vi quyền hạn.
- Ghi nhận mọi quyết định và báo cáo trung thực.
- Không vượt quyền Master.
- Không tuyên bố hoàn thành khi chưa có bằng chứng.

## Điều 51. Trách nhiệm của Builder

Builder:

- Đọc đầy đủ chỉ thị.
- Làm trong workspace được giao.
- Tuân thủ contract.
- Không tự mở rộng phạm vi.
- Nộp artifact, evidence và log.
- Báo sớm trở ngại.
- Không tự tích hợp vào source chính.
- Không tự chốt nhiệm vụ.

## Điều 52. Trách nhiệm của Reviewer

Reviewer:

- Đánh giá độc lập.
- Kiểm tra đúng artifact được chỉ định.
- Đối chiếu tiêu chí nghiệm thu.
- Nêu lỗi và bằng chứng.
- Phân biệt test đã chạy và chưa chạy.
- Không sửa artifact đang review.
- Không coi PASS là quyền tích hợp hoặc quyền chốt nhiệm vụ.

## Điều 53. Trách nhiệm của runtime

Runtime hoặc cơ chế vận hành hỗ trợ có trách nhiệm:

- Kiểm tra schema và trạng thái.
- Cưỡng chế quyền khi có thể.
- Hạn chế ghi đồng thời.
- Hỗ trợ kiểm tra contract và manifest.
- Ghi log.
- Hỗ trợ phát hiện lỗi và khôi phục.

Nếu một chức năng chưa được triển khai hoặc chưa được kiểm thử, phải công bố là chưa có hoặc chưa xác minh.

---

# PHẦN XV. KẾT LUẬN VẬN HÀNH

SOP Multi-AI V10 xác định một mô hình làm việc trong đó **AI Chính là người điều phối duy nhất, file là kênh liên lạc chính thức, baseline bảo vệ tính toàn vẹn của nhiệm vụ, evidence xác định nguồn gốc kết quả, review bundle bảo vệ tính toàn vẹn của artifact, còn runtime thực thi các quy tắc có thể cưỡng chế bằng kỹ thuật.**

Mô hình mặc định:

- **Master:** Khởi tạo, giám sát, phê duyệt và dừng.
- **Cursor:** Orchestrator, quản lý trạng thái và là cổng tích hợp duy nhất theo mô hình mặc định.
- **Antigravity:** Builder và Analyst.
- **OpenCode:** Reviewer, Auditor hoặc Builder khi được giao.
- **Agent bổ sung:** Chỉ tham gia sau khi onboarding và xác minh năng lực.
- **Runtime:** Thực thi các gate kỹ thuật đã triển khai và kiểm thử.

Trình tự nghiệm thu code bắt buộc:

**Contract → Baseline → Workspace → Build → Evidence → Immutable Review Bundle → Review → Verify → Snapshot → Integrate → Regression → Completed hoặc Rollback.**

Trình tự điều hành bắt buộc:

**Master Request → Discussion → Decision → Assignment → Execution → Review → Verification → Integration → Report.**

Nguyên tắc kết thúc:

1. Không có bằng chứng thì không xác nhận hoàn thành.
2. Không có baseline thì không nghiệm thu diff theo quy trình chuẩn.
3. Không có manifest hợp lệ thì không tích hợp artifact đã đóng gói.
4. Không vượt qua verify thì không tích hợp.
5. Không vượt qua regression thì không kết thúc task ở trạng thái `COMPLETED`.
6. Không có watcher thực sự thì không tuyên bố đang theo dõi liên tục.
7. Không có kiểm thử phục hồi thì không tuyên bố khả năng rollback đã được chứng minh.
8. Không tự xây dựng controller mới trước khi audit và xác định khả năng tái sử dụng các thành phần hiện có.
9. Không sử dụng quyền tự chủ để vượt qua các giới hạn hoặc quyết định thuộc thẩm quyền Master.

**Tiêu chuẩn cuối cùng:** Một đội Multi-AI chỉ được coi là tự vận hành có kiểm soát khi không chỉ biết đọc SOP, mà còn thực hiện đúng giao thức, phát hiện sai lệch, cưỡng chế được các giới hạn cần thiết, tạo ra bằng chứng có thể kiểm tra và phục hồi được sau sự cố theo các bài thử nghiệm đã xác minh.

**KẾT THÚC — SOP MULTI-AI V10.0**