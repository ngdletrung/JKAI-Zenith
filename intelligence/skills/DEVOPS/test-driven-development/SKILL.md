---
id: TEST_DRIVEN_DEVELOPMENT
name_vn: "Phát triển Hướng Kiểm thử"
version: 1.0.0
domain: DEVOPS
intent_pairs:
  - ["CREATE", "TEST"]
  - ["ANALYZE", "CODE"]
aliases_vn: ["phát triển hướng kiểm thử", "TDD", "red green refactor"]
schema:
  parameters:
    type: object
    properties:
      target: { type: string, description: "Đối tượng hoặc tính năng cần triển khai kiểm thử" }
    required: ["target"]
assigned_agent: agent_executor_alpha.md
priority: HIGH
---

# Test-Driven Development

Write a failing test before writing the code that makes it pass. For bug fixes, reproduce the bug with a test before attempting a fix. Tests are proof — "seems right" is not done. A codebase with good tests is an AI agent's superpower; a codebase without tests is a liability.

## When to Use

- Implementing any new logic or behavior
- Fixing any bug (the Prove-It Pattern)
- Modifying existing functionality
- Adding edge case handling
- Any change that could break existing behavior

**When NOT to use:** Pure configuration changes, documentation updates, or static content changes that have no behavioral impact.

## The TDD Cycle

```
    RED                GREEN              REFACTOR
 Write a test    Write minimal code    Clean up the
  that fails  ──→  to make it pass  ──→  implementation  ──→  (repeat)
      │                  │                    │
      ▼                  ▼                    ▼
   Test FAILS        Test PASSES         Tests still PASS
```

### Step 1: RED — Write a Failing Test

Write the test first. It must fail. A test that passes immediately proves nothing.

### Step 2: GREEN — Make It Pass

Write the minimum code to make the test pass. Don't over-engineer.

### Step 3: REFACTOR — Clean Up

With tests green, improve the code without changing behavior. Run tests after every refactor step to confirm nothing broke.

## The Prove-It Pattern (Bug Fixes)

When a bug is reported, **do not start by trying to fix it.** Start by writing a test that reproduces it.

```
Bug report arrives ──→ Write a test demonstrating bug ──→ Test FAILS ──→ Implement fix ──→ Test PASSES ──→ Run full suite
```

## Anti-Rationalization (Chống Ngụy Biện)

| Rationalization | Reality |
|---|---|
| "I'll write tests after the code works" | You won't. And tests written after the fact test implementation, not behavior. |
| "This is too simple to test" | Simple code gets complicated. The test documents the expected behavior. |
| "Tests slow me down" | Tests slow you down now. They speed you up every time you change the code later. |
| "I tested it manually" | Manual testing doesn't persist. Tomorrow's change might break it with no way to know. |
| "The code is self-explanatory" | Tests ARE the specification. They document what the code should do, not what it does. |
| "It's just a prototype" | Prototypes become production code. Tests from day one prevent the "test debt" crisis. |
| "Let me run the tests again just to be extra sure" | Repeating the same command adds nothing unless the code has changed since. Run again after subsequent edits, not as reassurance. |

## Red Flags

- Writing code without any corresponding tests
- Tests that pass on the first run (they may not be testing what you think)
- "All tests pass" but no tests were actually run
- Bug fixes without reproduction tests
- Test names that don't describe the expected behavior
- Running the same test command twice in a row without any intervening code change

## Exit Criteria & Verification

After completing any implementation:

- [ ] Every new behavior has a corresponding test
- [ ] All tests pass: `npm test` or the matching test runner command
- [ ] Bug fixes include a reproduction test that failed before the fix
- [ ] Test names describe the behavior being verified
- [ ] No tests were skipped or disabled

---
## Sovereign Laws
- Skill nay duoc dong hoa tu agent-skills (MIT License - Addy Osmani).
- Moi hanh vi cua JKAI khi kich hoat skill #3503 phai tuan thu giao thuc tren.
- Khong dua ra ket qua cuoi cung neu chua hoan thanh checklist cuoi muc Verification.

*Deck #3503 | Property of Master LeeTrung | JKAI Zenith*
