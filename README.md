# Reckoning Machine

Reckoning Machine is a policy-governed, ledger-backed execution engine for LLM workflows.

It is built for determinism, auditability, and correction — not autonomous behavior or emergent agent systems.

Reckoning Machine executes explicit task graphs where every step is validated, gated, and recorded. If something is wrong, execution stops. Nothing silently degrades.

---

## What this is

Reckoning Machine executes directed acyclic graphs (DAGs) of LLM tasks with:

- explicit task contracts
- deterministic step gating
- validated intermediate artifacts
- immutable, queryable run ledgers

The system cleanly separates:

- Decision Rationale — model-reported explanation (JSON)
- Execution Policy — deterministic validation and enforcement
- Canonical Output — the only data allowed to flow downstream

This separation is foundational. Explanations are never trusted for control.

---

## What this is not

- Not an agent framework
- Not autonomous
- Not probabilistic orchestration
- Not LangChain-based
- Not a prompt playground

Reckoning Machine prioritizes correctness over cleverness.

---

## Core concepts

Task  
A unit of LLM work with a declared contract.

Manifest  
An explicit DAG of tasks with declared dependencies.

Run  
One execution of a manifest. Runs are immutable and may pause awaiting external attestation.

Decision Rationale  
Structured JSON explanation returned by the model. Stored for interpretability only.

Execution Policy  
Deterministic rules enforced by the system. Authoritative.

Canonical Output  
Validated JSON produced by a task. The only payload allowed to chain forward.

## External Compute and Attestation

In addition to LLM-based tasks, a manifest step may represent **external deterministic compute**.

Examples include:
- spreadsheet models
- batch scripts
- offline or manual procedures

These steps are declared explicitly and treated as execution boundaries.

When execution reaches an external compute step:
- the run transitions to a waiting state
- execution halts deterministically
- no downstream steps execute

Execution resumes only after an operator submits an attestation recording:
- the outcome (success or failure)
- the artifacts produced

This ensures that all external work is explicit, auditable, and replayable.

---

## Architecture

- FastAPI backend
- PostgreSQL system of record
- SQLAlchemy and Alembic for schema control
- Synchronous execution model
- Vanilla HTML and JavaScript UI

Execution planes:
- Control plane: task and manifest definitions
- Execution plane: runs and step runs
- Data plane: prompts, model calls, parsed outputs

---

## Status

This project is under active development.
Execution semantics are stable; APIs may evolve.

For detailed execution semantics, invariants, and failure modes, see `ARCHITECTURE.md`.

---

## License

MIT
