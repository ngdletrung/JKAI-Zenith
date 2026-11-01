# Bộ đếm hệ thống (System Counters)

Tất cả bộ đếm dùng chung trong JKAI đi qua **một** chủ: [`core/telemetry/system_counters.py`](../../core/telemetry/system_counters.py).

## Vì sao phải gom về một chỗ

`ai-brain` chạy nhiều worker (`uvicorn --workers 2`). Mỗi worker giữ bộ đếm riêng trong RAM, nên con số của worker được load-balancer chọn không đại diện cho cả hệ thống. Ngoài ra `ai-control-plane` cũng phải đếm (judicial gate). Vì vậy bộ đếm được:

- cộng vào RAM của tiến trình hiện tại (nhanh, luôn đúng cục bộ);
- cộng dồn vào Redis hash `jkai:counters:<tên>` bằng `HINCRBY` (đúng toàn hệ thống, không phụ thuộc worker).

Module nằm trong `core/` vì `core` được mount vào cả `ai-brain` (`/shared/core`) và `ai-control-plane` (`/shared/core`).

## Fail-fast khi Redis chết

`bump()` đặt `_down_until = now + 30s` sau lần lỗi đầu tiên; trong cửa sổ đó mọi lần bump bỏ qua Redis và chỉ cộng RAM. Nhờ vậy Redis chết không cộng connect-timeout vào từng request trên đường ingress.

## Các bộ đếm đang dùng

| Bộ đếm | Trường | Ai ghi | Ý nghĩa |
|---|---|---|---|
| `firewall` | `total_scanned`, `blocked_count` | `ai-brain/security/semantic_firewall.py` | Mọi input qua tường lửa ngữ nghĩa; số lần chặn |
| `critic` | `approve`, `enforce`, `retry`, `deterministic_override`, `double_reject` | `ai-brain/main.py` (`_record_critic_decision`) | Phán quyết của Critic ở mỗi vòng thẩm định |
| `judicial` | `stop`, `partial` | `ai-control-plane/task_manager.py` | Mission bị dừng vì không có bằng chứng (`stop`) hoặc chỉ cảnh báo (`partial`) |

## Đọc số liệu

| Endpoint | Nội dung |
|---|---|
| `GET http://localhost:8001/firewall/stats` | Bộ đếm firewall toàn hệ thống + bộ đếm cục bộ của worker trả lời |
| `GET http://localhost:8001/critic/stats` | Phán quyết Critic toàn hệ thống + cục bộ |
| `GET http://localhost:8001/judicial/stats` | Kết quả judicial gate toàn hệ thống |

Mọi endpoint trả trường `source`:

- `redis` — số liệu đọc từ Redis, là số của **toàn hệ thống**;
- `local` — Redis không có dữ liệu (chưa ai ghi hoặc vừa reset), số liệu chỉ của worker đang trả lời.

`local` **không** có nghĩa là "0 sự kiện"; đó là lý do trường `source` tồn tại.

## Metric Prometheus

`GET http://localhost:8001/metrics` xuất:

```
jkai_hallucination_total
jkai_semantic_firewall_hits_total
jkai_critic_decision_total{outcome="..."}
```

Đây là bộ đếm **theo tiến trình** (chuẩn Prometheus: mỗi target xuất số của chính nó). Muốn số toàn hệ thống, dùng các endpoint bảng trên.

## Reset

```bash
# Xoá bộ đếm của một nhóm (ví dụ firewall)
MSYS_NO_PATHCONV=1 docker exec ai-brain python -c "
from redis_client import get_redis
print(get_redis().delete('jkai:counters:firewall'))"
```

Reset chỉ xoá số tổng hợp trong Redis; bộ đếm RAM trong worker vẫn tiếp tục cộng từ mốc hiện tại cho tới khi worker khởi động lại. Nếu cần mốc sạch hoàn toàn, reset Redis rồi restart `ai-brain`/`ai-control-plane` khi `active_tasks == 0`.

## Giám sát

- `block_rate` trong `/firewall/stats` tăng đột ngột → có thể đang bị tấn công hoặc có client gửi nhầm nội dung hệ thống qua ingress.
- `double_reject` trong `/critic/stats` tăng → Critic đang chặn nhiều; xem log `[CRITIC-DOUBLE-REJECT]`.
- `stop` trong `/judicial/stats` khác 0 → mission đã bị dừng vì không có bằng chứng thực thi; xem log `[JUDICIAL-STOP]` của `ai-control-plane`.
- `partial` khác 0 nhưng `stop` bằng 0 → mission vẫn chạy với bằng chứng một phần; xem log `[JUDICIAL-PARTIAL]`.
