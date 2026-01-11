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

### Compute Steps

In addition to task-based steps, a ManifestStep may declare a **compute step**.

Compute steps represent external deterministic computation (e.g. Excel models, batch scripts, manual procedures).
They are first-class citizens in the Control Plane and must be declared explicitly.

A compute step:
- declares a compute contract (inputs, outputs, verification mode)
- does not execute within the Reckoning Machine process
- introduces an explicit execution boundary

The system does not infer or automate external compute.
All external work must be acknowledged explicitly.

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

### Compute Step Execution Model

When the execution engine encounters a compute step:

- A DagStepRun is created with status `WAITING_FOR_ATTESTATION`
- The DagRun transitions to status `waiting`
- Execution halts immediately
- No downstream steps execute

The system does not poll, retry, or invoke external compute.

Execution resumes only when an operator submits an attestation that:
- identifies the completed step
- records the outcome (SUCCESS or FAIL)
- attaches produced artifacts

This ensures that all external computation is:
- explicit
- auditable
- replayable
- deterministic from the system’s perspective

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

### Compute Attestations and Artifacts

External compute resolution is recorded via:

- Compute attestations (operator, timestamp, outcome)
- Linked compute artifacts (URIs, hashes, metadata)

These records are immutable and fully queryable.

The system never assumes that external computation occurred.
It is only recognized once attested and persisted.

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

### Manifest Immutability During Execution

Once a DagRun is created, the associated Manifest and its steps are treated as immutable.

Editing or replacing manifest steps while a run is active is not supported.
If detected, execution is aborted to preserve determinism.

This invariant ensures:
- step identity remains stable
- execution history remains interpretable
- resume semantics remain correct


## Non-goals

- Autonomous agents
- Dynamic planning
- Implicit tool invocation
- Emergent behavior

Reckoning Machine is intentionally conservative.
