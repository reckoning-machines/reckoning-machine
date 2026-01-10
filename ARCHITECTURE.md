# Architecture

This document describes the execution model and system boundaries of Reckoning Machine.

---

## Design goals

- Deterministic execution
- Explicit contracts between steps
- Audit-grade traceability
- Clear separation of control and explanation
- Zero hidden state

---

## High-level system view

Reckoning Machine is composed of three planes:

Control Plane  
Defines what should run.

Execution Plane  
Defines what did run.

Data Plane  
Stores all artifacts produced during execution.

Each plane is isolated and independently inspectable.

---

## Control Plane

The control plane defines intent.

Primary entities:
- Task
- Manifest
- ManifestStep

Tasks define units of work.
Manifests define explicit DAGs of tasks.
Dependencies are declared, never inferred.

---

## Execution Plane

The execution plane is authoritative.

Primary entities:
- DagRun
- DagStepRun

Execution rules:
- Steps execute sequentially
- Dependencies must be satisfied
- Failed steps block downstream execution
- Skipped steps are explicitly recorded

There is no best-effort continuation.

---

## Data Plane

The data plane stores all execution artifacts.

Artifacts include:
- Rendered prompts
- Model request and response payloads
- Parsed outputs
- Decision rationales
- Execution policy reports

Nothing is ephemeral.
Nothing is overwritten.

---

## Decision Rationale vs Execution Policy

Decision Rationale  
Produced by the model. Explanatory only.

Execution Policy  
Produced by the system. Deterministic and authoritative.

The system never trusts model explanations for control decisions.

---

## Canonical Output Chaining

Only validated Canonical Output is allowed to flow between steps.

Raw text is never chained.
Unvalidated JSON is never chained.

This prevents silent error propagation.

---

## Failure model

Failures are explicit and terminal.

A step may:
- Succeed
- Fail
- Be skipped due to upstream failure

Failures are recorded, not retried automatically.

---

## Non-goals

- Autonomous agents
- Dynamic planning
- Implicit tool invocation
- Emergent behavior

Reckoning Machine is intentionally conservative.
