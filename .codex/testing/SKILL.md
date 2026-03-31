---
name: testing
description: How to write tests for this project — what to test, what to skip, and the equivalence-class discipline that prevents redundant or missing cases. Read before writing any test.
user-invocable: false
---

## Decision framework: what earns a test

Before writing anything, answer these questions:

**1. What are the branches?**
List every `if`/`elif`/`else` and every early return. Each branch is one required test.

**2. Where are the boundaries?**
Every `>=`, `<=`, `>`, `<` comparison earns *two* tests: one at exactly the limit, one on each side.

**3. What are the failure modes?**
Error paths are at least as important as happy paths.

**4. Does complexity scale with test count?**
Simple functions with no branching may need zero tests. Complex logic needs many.

**5. Would deleting this test let a regression slip through?**
If another test already covers the same branch and boundary, delete one.

---

## What NOT to test

**LLM outputs** — test what happens *given* certain outputs, not that the LLM was called.

**Prompt content** — asserting a prompt string contains specific text is brittle.

**That a mock was called** — assert on *outcomes*: return values, side effects, errors.

---

## Equivalence classes, not examples

One test per branch + two tests per boundary. Delete any parametrize case that exercises the same branch as another.

---

## Test naming

Name tests after the **behaviour under test**, not the function:

```python
# BAD
def test_execute_python():

# GOOD
def test_syntax_error_populates_error_field():
def test_timeout_populates_error_field():
```

---

## Running tests

Use the test command that exists in the current scaffold.

- If the repo does not yet have a test harness, add the smallest useful one with the code you introduce.
- If you add a new command or test location, update `agents.md` so future work can discover it quickly.
