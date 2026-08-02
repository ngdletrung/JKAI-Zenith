---
id: memory-management
name_vn: memory-management
version: 1.0.0
author: Zenith Legacy
domain: UNKNOWN
intent_pairs: []
aliases_vn: []
schema: {}
priority: NORMAL
related_skills: []

---

# memory-management (memory-management)

## 🌟 TỔNG QUAN
---
name: memory-management
description: >
  AgentDB memory system with HNSW vector search. Provides 150x-12,500x faster pattern retrieval, persistent storage, and semantic search capabilities for learning and knowledge management.
  Use when: need to store successful patterns, searching for similar solutions, semantic lookup of past work, learning from previous tasks, sharing knowledge between agents, building knowledge base.
  Skip when: no learning needed, ephemeral one-off tasks, external data sources available, read-only exploration.
---

# Memory Management Skill

## Purpose
AgentDB memory system with HNSW vector search. Provides 150x-12,500x faster pattern retrieval, persistent storage, and semantic search capabilities for learning and knowledge management.

## When to Trigger
- need to store successful patterns
- searching for similar solutions
- semantic lookup of past work
- learning from previous tasks
- sharing knowledge between agents
- building knowledge base

## When to Skip
- no learning needed
- ephemeral one-off tasks
- external data sources available
- read-only exploration

## Commands

### Store Pattern
Store a pattern or knowledge item in memory

```bash
npx @claude-flow/cli memory store --key "[key]" --value "[value]" --namespace patterns
```

**Example:**
```bash
npx @claude-flow/cli memory store --key "auth-jwt-pattern" --value "JWT validation with refresh tokens" --namespace patterns
```

### Semantic Search
Search memory using semantic similarity

```bash
npx @claude-flow/cli memory search --query "[search terms]" --limit 10
```

**Example:**
```bash
npx @claude-flow/cli memory search --query "authentication best practices" --limit 5
```

### Retrieve Entry
Retrieve a specific memory entry by key

```bash
npx @claude-flow/cli memory get --key "[key]" --namespace [namespace]
```

**Example:**
```bash
npx @claude-flow/cli memory get --key "auth-jwt-pattern" --namespace patterns
```

### List Entries
List all entries in a namespace

```bash
npx @claude-flow/cli memory list --namespace [namespace]
```

**Example:**
```bash
npx @claude-flow/cli memory list --namespace patterns --limit 20
```

### Delete Entry
Delete a memory entry

```bash
npx @claude-flow/cli memory delete --key "[key]" --namespace [namespace]
```

### Initialize HNSW Index
Initialize HNSW vector search index

```bash
npx @claude-flow/cli memory init --enable-hnsw
```

### Memory Stats
Show memory usage statistics

```bash
npx @claude-flow/cli memory stats
```

### Export Memory
Export memory to JSON

```bash
npx @claude-flow/cli memory export --output memory-backup.json
```


## Scripts

| Script | Path | Description |
|--------|------|-------------|
| `memory-backup` | `.agents/scripts/memory-backup.sh` | Backup memory to external storage |
| `memory-consolidate` | `.agents/scripts/memory-consolidate.sh` | Consolidate and optimize memory |


## References

| Document | Path | Description |
|----------|------|-------------|
| `HNSW Guide` | `docs/hnsw.md` | HNSW vector search configuration |
| `Memory Schema` | `docs/memory-schema.md` | Memory namespace and schema reference |

## Best Practices
1. Check memory for existing patterns before starting
2. Use hierarchical topology for coordination
3. Store successful patterns after completion
4. Document any new learnings


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
