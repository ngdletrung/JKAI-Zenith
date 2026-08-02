---
id: claims
name_vn: claims
version: 1.0.0
author: Zenith Legacy
domain: UNKNOWN
intent_pairs: []
aliases_vn: []
schema: {}
priority: NORMAL
related_skills: []

---

# claims (claims)

## 🌟 TỔNG QUAN
---
name: claims
description: >
  Claims-based authorization for agents and operations. Grant, revoke, and verify permissions for secure multi-agent coordination.
  Use when: permission management, access control, secure operations, authorization checks.
  Skip when: open access, no security requirements, single-agent local work.
---

# Claims Authorization Skill

## Purpose
Claims-based authorization for secure agent operations and access control.

## Claim Types

| Claim | Description |
|-------|-------------|
| `read` | Read file access |
| `write` | Write file access |
| `execute` | Command execution |
| `spawn` | Agent spawning |
| `memory` | Memory access |
| `network` | Network access |
| `admin` | Administrative operations |

## Commands

### Check Claim
```bash
npx claude-flow claims check --agent agent-123 --claim write
```

### Grant Claim
```bash
npx claude-flow claims grant --agent agent-123 --claim write --scope "/src/**"
```

### Revoke Claim
```bash
npx claude-flow claims revoke --agent agent-123 --claim write
```

### List Claims
```bash
npx claude-flow claims list --agent agent-123
```

## Scope Patterns

| Pattern | Description |
|---------|-------------|
| `*` | All resources |
| `/src/**` | All files in src |
| `/config/*.toml` | TOML files in config |
| `memory:patterns` | Patterns namespace |

## Security Levels

| Level | Claims |
|-------|--------|
| `minimal` | read only |
| `standard` | read, write, execute |
| `elevated` | + spawn, memory |
| `admin` | all claims |

## Best Practices
1. Follow principle of least privilege
2. Scope claims to specific resources
3. Audit claim usage regularly
4. Revoke claims when no longer needed


## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)
### 🔍 Phase 1: Investigation (Thẩm định)
- Xác minh tham số đầu vào dựa trên Schema.
- Kiểm tra bối cảnh hệ thống liên quan.

### 🚀 Phase 2: Action (Thực thi)
- Triệu hồi logic thực thi trong `logic.py`.
- Trả về kết quả và chắt lọc kinh nghiệm.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Chưa ghi nhận.

---
*TRUNG THÀNH - CHÍNH XÁC - TỐI THƯỢNG* 💎🦾
