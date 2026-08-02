<!--
[ZENITH FILE DIRECTIVE]
- File: intelligence/skills/SECURITY/code-review-and-quality/dossier.md
- Role: Sovereign Knowledge Protocol - Assimilated from agent-skills v1.0 (MIT - Addy Osmani)
- Deck ID: #6015 | Domain: SECURITY
- Ownership: Mr LeeTrung
- Status: Active | Version: SDS v1.0
-->

# DOSSIER: #6015 NGHIEM THU CODE

# Code Review and Quality

## 🎯 Capability Overview
Multi-dimensional code review with quality gates. Every change gets reviewed before merge. Review covers five axes: correctness, readability, architecture, security, and performance.

The approval standard: Approve a change when it definitely improves overall code health, even if it isn't perfect. Perfect code doesn't exist.

## 🧠 Reasoning & Strategy
- Use before merging any PR or change.
- Use after completing a feature implementation.
- Use when another agent or model produced code you need to evaluate.
- Use when refactoring existing code.
- Use after any bug fix (review both the fix and the regression test).

## 🛠️ Detailed Features
Every review evaluates code across these dimensions:

### 1. Correctness
Does the code do what it claims to do?
- Does it match the spec or task requirements?
- Are edge cases handled (null, empty, boundary values)?
- Are error paths handled (not just the happy path)?
- Does it pass all tests?
- Are there off-by-one errors, race conditions, or state inconsistencies?

### 2. Readability & Simplicity
Can another engineer (or agent) understand this code without the author explaining it?
- Are names descriptive and consistent with project conventions?
- Is the control flow straightforward?
- Is the code organized logically?
- Are there any clever tricks that should be simplified?
- Could this be done in fewer lines?
- Are abstractions earning their complexity?
- Would comments help clarify non-obvious intent?
- Are there dead code artifacts: no-op variables, backwards-compat shims, or removed comments?

### 3. Architecture
Does the change fit the system's design?
- Does it follow existing patterns or introduce a new one?
- Does it maintain clean module boundaries?
- Is there code duplication that should be shared?
- Are dependencies flowing in the right direction?
- Is the abstraction level appropriate?

### 4. Security
Does the change introduce vulnerabilities?
- Is user input validated and sanitized?
- Are secrets kept out of code, logs, and version control?
- Is authentication/authorization checked where needed?
- Are SQL queries parameterized?
- Are outputs encoded to prevent XSS?
- Are dependencies from trusted sources?
- Is data from external sources treated as untrusted?
- Are external data flows validated at system boundaries before use?

### 5. Performance
Does the change introduce performance problems?
- Any N+1 query patterns?
- Any unbounded loops or unconstrained data fetching?
- Any synchronous operations that should be async?
- Any unnecessary re-renders in UI components?
- Any missing pagination on list endpoints?
- Any large objects created in hot paths?

### Change Sizing
Small, focused changes are easier to review, faster to merge, and safer to deploy. Target these sizes:
- ~100 lines changed: Good.
- ~300 lines changed: Acceptable if it's a single logical change.
- ~1000 lines changed: Too large. Split it.

## 🌌 Strategic Value
Maintaining high quality code review ensures continuous codebase evolution and prevents systemic decay.

### Red Flags
- PRs merged without any review
- Review that only checks if tests pass (ignoring other axes)
- LGTM without evidence of actual review
- Security-sensitive changes without security-focused review
- Large PRs that are too big to review properly
- No regression tests with bug fix PRs
- Review comments without severity labels
- Accepting "I'll fix it later" — it never happens

### Sovereign Laws
- Skill nay duoc dong hoa tu agent-skills (MIT License - Addy Osmani).
- Moi hanh vi cua JKAI khi kich hoat skill #6015 phai tuan thu giao thuc tren.
- Khong dua ra ket qua cuoi cung neu chua hoan thanh checklist cuoi muc Verification.

*Deck #6015 | Property of Master LeeTrung | JKAI Zenith*
