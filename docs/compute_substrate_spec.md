# Compute Substrate (Stub) — MVP Specification (Repo-Aligned)

## 1. Purpose

The compute substrate represents external deterministic compute (e.g., Excel refresh farms, scripts, batch jobs)
as a first-class manifest step type.

In the MVP:
- the engine does not execute external compute
- the engine does enforce compute contracts
- the engine halts deterministically when a compute step is reached
- the engine unhalts only after an operator attests completion
- all attestations and artifacts are persisted in Postgres for audit and replay

This keeps the reference engine deterministic and audit-grade while allowing client-specific compute integrations later.

## 2. Terms

- Task step: an LLM step that runs through llm_complete() and policy evaluation.
- Compute step: an external step that blocks execution until attested.

## 3. Status model (must match repo casing)

### 3.1 Run status (dag_runs.status) — lowercase

Allowed values:
- running
- waiting
- success
- error

### 3.2 Step run status (dag_step_runs.status) — uppercase

Allowed values:
- RUNNING
- WAITING_FOR_ATTESTATION
- SUCCESS
- FAIL
- SKIPPED

Semantics:
- WAITING_FOR_ATTESTATION indicates the step is blocked pending operator attestation.
- SUCCESS and FAIL are terminal.
- SKIPPED is used for deterministic dependency gating when upstream is not SUCCESS.

## 4. Manifest model changes

### 4.1 manifest_steps additions

Add fields to manifest_steps:
- step_type (TEXT, nullable): task or compute. If NULL, treat as task for backward compatibility.
- compute_contract (JSONB, nullable): required when step_type == compute.

### 4.2 Compute contract schema

compute_contract MUST be a JSON object.

Required keys:
- executor (string): free-text identifier (e.g., excel_farm, script, manual)
- inputs (array of string): named inputs required
- outputs (array of string): named outputs expected
- verification (string enum): MVP supports only operator_attest

Optional keys:
- notes (string)
- timeout_minutes (int)

Example compute_contract object:

{
  "executor": "excel_farm",
  "inputs": ["model_inputs.parquet", "calendar_snapshot"],
  "outputs": ["model_outputs.xlsx"],
  "verification": "operator_attest",
  "notes": "Refresh model outputs; attach workbook from S3."
}

Validation rules:
- If step_type == compute, compute_contract is required and must include all required keys.
- verification must equal operator_attest in MVP.

## 5. Persistence model changes

### 5.1 New table: compute_attestations

One operator attestation per step run.

Columns:
- id UUID PK
- step_run_id UUID FK -> dag_step_runs.id (ON DELETE CASCADE), UNIQUE
- attested_by TEXT NOT NULL
- attested_at TIMESTAMPTZ NOT NULL (server time)
- outcome TEXT NOT NULL (SUCCESS or FAIL)
- notes TEXT NULL
- contract_snapshot JSONB NULL (snapshot of the step's compute_contract at attestation time)

### 5.2 New table: compute_artifacts

Artifacts linked to a compute attestation.

Columns:
- id UUID PK
- attestation_id UUID FK -> compute_attestations.id (ON DELETE CASCADE)
- name TEXT NOT NULL
- uri TEXT NOT NULL
- sha256 TEXT NULL
- bytes BIGINT NULL
- created_at TIMESTAMPTZ NOT NULL (server time)

## 6. Runner semantics

### 6.1 Execute manifest (new run)

execute_manifest(manifest_id, db, initiated_by) creates a new dag_runs row and executes steps sequentially.

When a compute step is reached:
- create a dag_step_runs row with:
  - status = WAITING_FOR_ATTESTATION
  - started_at = now
  - ended_at = NULL
- set dag_runs.status = waiting and return the run id
- do not call llm_complete()
- do not write prompt, parsed-output, or llm-call artifacts for compute steps

### 6.2 Deterministic resume (existing run)

Add a runner function:
resume_run(run_id, db, initiated_by)

It must:
- load the existing DagRun by id; it must exist and be in status waiting
- load the run’s manifest and ordered steps
- load existing DagStepRun rows for this run
- rebuild deterministic state used by task steps:
  - step_status[step_key] from existing step run terminal states (SUCCESS, FAIL, SKIPPED, WAITING)
  - canonical_by_step_key[step_key] from existing SUCCESS step runs with non-null canonical_output, keyed by the underlying ManifestStep.step_key
- continue sequential execution:
  - skip any step already in terminal status SUCCESS, FAIL, or SKIPPED
  - if a compute step is still WAITING_FOR_ATTESTATION, stop and keep run waiting
  - for task steps not yet executed, execute using the existing logic
- when all steps are processed, set run status to:
  - error if any step FAIL occurred
  - otherwise success
  - and set ended_at

Idempotency:
- calling resume repeatedly must not duplicate step runs and must not re-run SUCCESS steps.

## 7. API changes

### 7.1 Attest compute step

Endpoint:
POST /api/runs/{run_id}/steps/{step_run_id}/attest

Request JSON body:

{
  "attested_by": "jed",
  "outcome": "SUCCESS",
  "notes": "Workbook refreshed and uploaded.",
  "artifacts": [
    { "name": "model_outputs.xlsx", "uri": "s3://bucket/path.xlsx", "sha256": "..." }
  ]
}

Rules:
- step_run must belong to run_id
- step_run.status must be WAITING_FOR_ATTESTATION
- create row in compute_attestations (unique on step_run_id)
- create rows in compute_artifacts for provided artifacts
- update dag_step_runs.status to SUCCESS or FAIL
- if outcome is FAIL:
  - set dag_runs.status = error
  - set dag_runs.ended_at
- attestation does not auto-resume in MVP

Response JSON:

{ "ok": true, "step_run_id": "...", "new_status": "SUCCESS" }

### 7.2 Resume run

Endpoint:
POST /api/runs/{run_id}/resume

Request JSON body:

{ "initiated_by": "jed" }

Rules:
- run.status must be waiting, else return 409
- call resume_run(run_id, db, initiated_by)
- return updated run status and basic summary

## 8. UI (optional MVP)

If a UI exists:
- display step status WAITING_FOR_ATTESTATION clearly
- provide minimal attestation form (operator, outcome, artifacts)
- provide Resume button when run.status == waiting

## 9. Acceptance tests (manual)

Create a manifest with steps:
- A (task)
- B (compute with contract), depends_on A
- C (task), depends_on B

Run manifest:
- A executes and succeeds
- B becomes WAITING_FOR_ATTESTATION
- run.status == waiting
- C does not execute

Attest B SUCCESS with artifact references:
- B becomes SUCCESS
- run remains waiting

Resume:
- C executes
- run becomes success or error

Determinism:
- resuming twice does not duplicate step runs or rerun successful steps.
