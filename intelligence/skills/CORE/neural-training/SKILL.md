---
id: neural-training
name_vn: neural-training
version: 1.0.0
author: Zenith Legacy
domain: UNKNOWN
intent_pairs: []
aliases_vn: []
schema: {}
priority: NORMAL
related_skills: []

---

# neural-training (neural-training)

## 🌟 TỔNG QUAN
---
name: neural-training
description: >
  Neural pattern training with SONA (Self-Optimizing Neural Architecture), MoE (Mixture of Experts), and EWC++ for knowledge consolidation.
  Use when: pattern learning, model optimization, knowledge transfer, adaptive routing.
  Skip when: simple tasks, no learning required, one-off operations.
---

# Neural Training Skill

## Purpose
Train and optimize neural patterns using SONA, MoE, and EWC++ systems.

## When to Trigger
- Training new patterns
- Optimizing agent routing
- Knowledge consolidation
- Pattern recognition tasks

## Intelligence Pipeline

1. **RETRIEVE** — Fetch relevant patterns via HNSW (150x-12,500x faster)
2. **JUDGE** — Evaluate with verdicts (success$failure)
3. **DISTILL** — Extract key learnings via LoRA
4. **CONSOLIDATE** — Prevent catastrophic forgetting via EWC++

## Components

| Component | Purpose | Performance |
|-----------|---------|-------------|
| SONA | Self-optimizing adaptation | <0.05ms |
| MoE | Expert routing | 8 experts |
| HNSW | Pattern search | 150x-12,500x |
| EWC++ | Prevent forgetting | Continuous |
| Flash Attention | Speed | 2.49x-7.47x |

## Commands

### Train Patterns
```bash
npx claude-flow neural train --model-type moe --epochs 10
```

### Check Status
```bash
npx claude-flow neural status
```

### View Patterns
```bash
npx claude-flow neural patterns --type all
```

### Predict
```bash
npx claude-flow neural predict --input "task description"
```

### Optimize
```bash
npx claude-flow neural optimize --target latency
```

## Best Practices
1. Use pretrain hook for batch learning
2. Store successful patterns after completion
3. Consolidate regularly to prevent forgetting
4. Route based on task complexity


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
