---
id: SPEC_DRIVEN_DEVELOPMENT
name_vn: "Phát triển Hướng Đặc tả"
version: 1.0.0
domain: RESEARCH
intent_pairs:
  - ["CREATE", "SPEC"]
  - ["ANALYZE", "REQUIREMENT"]
aliases_vn: ["phát triển hướng đặc tả", "spec driven", "viết đặc tả", "tạo PRD"]
schema:
  parameters:
    type: object
    properties:
      feature: { type: string, description: "Mô tả tính năng hoặc yêu cầu đầu vào" }
    required: ["feature"]
assigned_agent: agent_planner.md
priority: HIGH
---

# Spec-Driven Development

Write a structured specification before writing any code. The spec is the shared source of truth between you and the human engineer — it defines what we're building, why, and how we'll know it's done. Code without a spec is guessing.

## When to Use

- Starting a new project or feature
- Requirements are ambiguous or incomplete
- The change touches multiple files or modules
- You're about to make an architectural decision
- The task would take more than 30 minutes to implement

**When NOT to use:** Single-line fixes, typo corrections, or changes where requirements are unambiguous and self-contained.

## The Gated Workflow

Spec-driven development has four phases. Do not advance to the next phase until the current one is validated.

```
SPECIFY ──→ PLAN ──→ TASKS ──→ IMPLEMENT
   │          │        │          │
   ▼          ▼        ▼          ▼
  Human      Human    Human      Human
  reviews    reviews  reviews    reviews
```

### Phase 1: Specify

Start with a high-level vision. Ask the human clarifying questions until requirements are concrete.

**Surface assumptions immediately.** Before writing any spec content, list what you're assuming:

```
ASSUMPTIONS I'M MAKING:
1. This is a web application (not native mobile)
2. Authentication uses session-based cookies (not JWT)
3. The database is PostgreSQL (based on existing Prisma schema)
4. We're targeting modern browsers only (no IE11)
→ Correct me now or I'll proceed with these.
```

Don't silently fill in ambiguous requirements. The spec's entire purpose is to surface misunderstandings *before* code gets written — assumptions are the most dangerous form of misunderstanding.

**Write a spec document covering these six core areas:**

1. **Objective** — What are we building and why? Who is the user? What does success look like?
2. **Commands** — Full executable commands with flags, not just tool names.
3. **Project Structure** — Where source code lives, where tests go, where docs belong.
4. **Code Style** — One real code snippet showing your style.
5. **Testing Strategy** — What framework, where tests live, coverage expectations.
6. **Boundaries** — Always do, Ask first, Never do.

### Phase 2: Plan

With the validated spec, generate a technical implementation plan:
1. Identify the major components and their dependencies
2. Determine the implementation order
3. Note risks and mitigation strategies
4. Identify what can be built in parallel vs. what must be sequential
5. Define verification checkpoints between phases

### Phase 3: Tasks

Break the plan into discrete, implementable tasks:
- Each task should be completable in a single focused session
- Each task has explicit acceptance criteria
- Each task includes a verification step (test, build, manual check)
- Tasks are ordered by dependency
- No task should require changing more than ~5 files

### Phase 4: Implement

Execute tasks one at a time following `skills/incremental-implementation/SKILL.md` and `skills/test-driven-development/SKILL.md`.

## Anti-Rationalization (Chống Ngụy Biện)

| Rationalization | Reality |
|---|---|
| "This is simple, I don't need a spec" | Simple tasks don't need *long* specs, but they still need acceptance criteria. A two-line spec is fine. |
| "I'll write the spec after I code it" | That's documentation, not specification. The spec's value is in forcing clarity *before* code. |
| "The spec will slow us down" | A 15-minute spec prevents hours of rework. Waterfall in 15 minutes beats debugging in 15 hours. |
| "Requirements will change anyway" | That's why the spec is a living document. An outdated spec is still better than no spec. |
| "The user knows what they want" | Even clear requests have implicit assumptions. The spec surfaces those assumptions. |

## Red Flags

- Starting to write code without any written requirements
- Asking "should I just start building?" before clarifying what "done" means
- Implementing features not mentioned in any spec or task list
- Making architectural decisions without documenting them
- Skipping the spec because "it's obvious what to build"

## Exit Criteria & Verification

Before proceeding to implementation, confirm:

- [ ] The spec covers all six core areas
- [ ] The human has reviewed and approved the spec
- [ ] Success criteria are specific and testable
- [ ] Boundaries (Always/Ask First/Never) are defined
- [ ] The spec is saved to a file in the repository

---
## Sovereign Laws
- Skill nay duoc dong hoa tu agent-skills (MIT License - Addy Osmani).
- Moi hanh vi cua JKAI khi kich hoat skill #4010 phai tuan thu giao thuc tren.
- Khong dua ra ket qua cuoi cung neu chua hoan thanh checklist cuoi muc Verification.

*Deck #4010 | Property of Master LeeTrung | JKAI Zenith*
