# Agent Sort (Legacy Shim)

**Mục đích:** Chỉ sử dụng khi lệnh `/agent-sort` vẫn được gọi. Quy trình làm việc được duy trì tại `skills/agent-sort/SKILL.md`.

## Giao diện Chuẩn (Canonical Surface)

- Nên ưu tiên sử dụng trực tiếp kỹ năng `agent-sort`.
- Giữ tệp này chỉ với mục đích điểm truy cập tương thích (compatibility entry point).

## Tham số (Arguments)

`$ARGUMENTS`

## Ủy quyền (Delegation)

Áp dụng kỹ năng `agent-sort`.
- Phân loại các bề mặt ECC với bằng chứng kho lưu trữ cụ thể.
- Giữ kết quả ở dạng DAILY so với LIBRARY.
- Nếu cần thay đổi cài đặt sau đó, chuyển giao cho `configure-ecc` thay vì tái triển khai logic cài đặt tại đây.
