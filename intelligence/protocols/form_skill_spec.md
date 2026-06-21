---
id: [SKILL_ID_IN_UPPERCASE]
name_vn: [Ten tieng Viet chuyen nghiep]
version: [Phien ban dang x.y.z]
author: [Ten tac gia hoac phan he]
domain: [Phan loai mien: CORE | CODING | DEVOPS | RESEARCH | SECURITY]
intent_pairs:
  - "TASK+DOMAIN"
aliases_vn:
  - "tu khoa tim kiem tieng Viet khong dau"
schema:
  properties:
    [ten_tham_so]:
      type: [kieu_du_lieu]
      description: [mo ta tham so]
  required:
    - [cac_tham_so_bat_buoc]
priority: [CRITICAL | HIGH | NORMAL | LOW]
related_skills: []
---

# [SKILL_ID]

## 1. TONG QUAN
- **Mo ta**: Dinh nghia chi tiet nhiem vu va chuc nang vat ly cua cong cu.
- **Pham vi bien**: Chi dinh ro cac gioi han dau vao, dau ra, va cac truong hop loi.

## 2. PHAC DO VAN HANH (OPERATIONAL PROTOCOL)
- **Phase 1: Input Validation**: Quy dinh kiem tra tham so dau vao so voi Schema.
- **Phase 2: Execution Logic**: Trieu goi logic thuc thi trong `logic.py`.
- **Phase 3: Error Bounds**: Xu ly ngoai le, luon tra ve ket qua cau truc chuan (khong tra ve None).

## 3. SAI LAM THUONG GAP (COMMON PITFALLS)
- Liet ke cac loi cau hinh hoac tham so can tranh.
