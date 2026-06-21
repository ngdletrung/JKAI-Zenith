# Chuẩn viết skill JKAI (progressive disclosure)

Mục tiêu: skill **ngắn khi load**, chi tiết **trong references/** — giống Harness, phù hợp deck + Mission Control.

## Cấu trúc thư mục

```text
intelligence/skills/<DECK>/<SKILL_ID>/
  SKILL.md          # Bắt buộc — metadata + hướng dẫn cốt lõi (< ~120 dòng)
  references/       # Tùy chọn — chi tiết, checklist, ví dụ
    README.md       # Mục lục references
    *.md
```

Mẫu copy: `intelligence/skills/_STANDARD/`

## SKILL.md

1. **Front matter / header:** `id`, `title`, `domain`, `version`, `triggers` (từ khóa deck).
2. **When to use** — 3–5 bullet, tiếng Việt hoặc song ngữ ngắn.
3. **Inputs / outputs** — rõ artifact (file, báo cáo, không side-effect).
4. **Core procedure** — tối đa 7 bước; không nhét toàn bộ spec.
5. **References** — liệt kê file con: `references/foo.md` — orchestrator/planner load khi goal khớp.
6. **Anti-patterns** — 2–3 dòng (hallucinate tool, ghi registry tự động, v.v.).

## references/

- Mỗi file một chủ đề (checklist, schema, ví dụ prompt).
- `README.md` là index; tên file `SCREAMING_SNAKE` hoặc `kebab-case` nhất quán trong skill.
- Không trùng nội dung SKILL.md — chỉ mở rộng.

## Deck & registry

- Đăng ký trong deck map / `agent_index.json` theo quy trình hiện có — **không** tự thêm khi agent phân tích repo ngoài.
- Trigger deck: hashtag `#SKILL_ID` hoặc từ khóa trong `SKILL.md`.

## Planner / DEEP

- Skill phân tích nặng → gắn pattern `producer_reviewer` (tự suy từ goal).
- Bước plan dùng `tool` = registry id chính xác.

## Review checklist (trước merge skill)

- [ ] SKILL.md đọc được trong < 2 phút
- [ ] Có ít nhất một reference nếu spec > 80 dòng
- [ ] Không hardcode đường dẫn Windows
- [ ] Triggers khớp deck display id
