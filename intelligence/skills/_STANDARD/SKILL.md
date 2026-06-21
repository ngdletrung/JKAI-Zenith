# SKILL_ID — Title (template)

**Deck:** CORE | ZENITH | …  
**Domain:** GENERAL  
**Version:** 1.0.0  
**Triggers:** keyword1, keyword2, #SKILL_ID

## When to use

- Mô tả ngắn khi nào gọi skill này.
- Không dùng cho … (1 dòng).

## Inputs

- `goal` — yêu cầu Master
- (tùy chọn) `context` — workspace, trace_id

## Outputs

- Artifact: báo cáo markdown / file path / walkthrough section

## Core procedure

1. Xác nhận phạm vi (read-only vs mutate).
2. Thu thập (tool registry — không bịa id).
3. Xử lý theo `references/CHECKLIST.md` nếu phức tạp.
4. Tổng hợp deliverable + tiêu chí review.
5. (DEEP) Để T5 CRITIC duyệt nếu phân tích/so sánh.

## References

- `references/README.md` — mục lục
- Thêm file khi cần: `references/EXAMPLES.md`

## Anti-patterns

- Không ghi `agent_index.json` / registry khi chỉ phân tích.
- Không nhét toàn bộ spec vào SKILL.md — dùng `references/`.
