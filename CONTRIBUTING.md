# Contributing

Contributions are welcome, but this project has strong design constraints.

Please read this document carefully before opening a pull request.

---

## Guiding principles

- Determinism over autonomy
- Explicit contracts over inference
- Validation over trust
- Ledgers over logs
- Correctness over convenience

PRs that violate these principles will be rejected.

---

## What we accept

- Bug fixes with clear reproduction steps
- Improvements to determinism or auditability
- Documentation improvements
- Performance improvements that preserve semantics

---

## What we do not accept

- Agent frameworks or abstractions
- Implicit chaining or hidden state
- Best-effort execution semantics
- Retry loops without explicit policy
- LangChain or similar orchestration libraries
- Changes that obscure execution flow

---

## PR requirements

Every PR must include:
- A clear problem statement
- Explanation of why the change is safe
- Confirmation that execution semantics are unchanged
- Tests or reproducible verification steps

Large refactors without justification will be closed.

---

## Code style

- Explicit is better than clever
- Fewer abstractions are preferred
- Readability matters more than DRY
- Comments should explain why, not what

---

## Philosophy

Reckoning Machine is not a playground.
It is an execution system.

If your contribution adds magic, it probably does not belong here.
