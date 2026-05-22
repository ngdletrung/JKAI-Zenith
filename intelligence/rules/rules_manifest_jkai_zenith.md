# JKAI Zenith Rules Manifest

Tổng số bản ghi: 17
Hệ thống chỉ cần đọc tập này để nắm bắt toàn bộ năng lực của JKAI Zenith.

- [x] DIR: common
- [x] DIR: cpp
- [x] DIR: csharp
- [x] DIR: dart
- [x] DIR: golang
- [x] DIR: java
- [x] DIR: kotlin
- [x] DIR: perl
- [x] DIR: php
- [x] DIR: python
- [x] DIR: rust
- [x] DIR: swift
- [x] DIR: typescript
- [x] DIR: web
- [x] DIR: zh
- [x] FILE: README.md
- [x] FILE: general.md

---

## Cấu Trúc Quy Tắc JKAI Zenith

Các quy tắc được tổ chức thành một lớp **common** (chung) và các thư mục **language-specific** (cụ thể theo ngôn ngữ):

```markdown
rules/
├── common/          # Nguyên tắc không phụ thuộc ngôn ngữ (luôn được cài đặt)
│   ├── coding-style.md
│   ├── git-workflow.md
│   ├── testing.md
│   ├── performance.md
│   ├── patterns.md
│   ├── hooks.md
│   ├── agents.md
│   └── security.md
├── typescript/      # Quy tắc dành riêng cho TypeScript/JavaScript
├── python/          # Quy tắc dành riêng cho Python
├── golang/          # Quy tắc dành riêng cho Go
├── web/             # Quy tắc dành riêng cho Web/Frontend
├── swift/           # Quy tắc dành riêng cho Swift
└── php/             # Quy tắc dành riêng cho PHP
```

### Nguyên tắc hoạt động

1. **Tính kế thừa:** Các nguyên tắc chung được định nghĩa ở `common/` là nền tảng. Các quy tắc cụ thể trong từng ngôn ngữ sẽ kế thừa và mở rộng các nguyên tắc chung.
2. **Tính ưu tiên:** Quy tắc cụ thể trong từng ngôn ngữ luôn có độ ưu tiên cao hơn quy tắc chung, đảm bảo tính chính xác và phù hợp với đặc thù ngôn ngữ.

### Hướng dẫn triển khai (Tóm tắt)

* **Mục đích:** Thiết lập một bộ tiêu chuẩn phát triển toàn diện, đảm bảo mọi dự án tuân thủ cùng một bộ quy tắc chất lượng cao, bất kể ngôn ngữ được sử dụng. 
* **Cấu trúc:** Sử dụng cấu trúc module hóa để dễ dàng quản lý và mở rộng các quy tắc. 
* **Triển khai:** Bắt đầu bằng việc thiết lập các tiêu chuẩn chung, sau đó áp dụng và tinh chỉnh cho từng ngôn ngữ cụ thể. 

**Tóm lại:** Đây là bộ khung tiêu chuẩn hóa toàn bộ quy trình phát triển phần mềm, giúp đội ngũ phát triển duy trì chất lượng đồng nhất và tối ưu hóa quy trình làm việc. (Tối ưu hóa cho người đọc/AI)
