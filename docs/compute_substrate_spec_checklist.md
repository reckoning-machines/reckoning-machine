# Compute Substrate Stub — Implementation Checklist (MVP)

This checklist is the acceptance gate for implementing the compute substrate stub.
Do not add worker systems, queues, Excel automation, or background executors.

## A. Schema / DB

- [ ] `manifest_steps` has `step_type` (TEXT, nullable).
- [ ] `manifest_steps` has `compute_contract` (JSONB, nullable).
- [ ] New table `compute_attestations` exists:
  - [ ] `step_run_id` FK to `dag_step_runs.id` with ON DELETE CASCADE
  - [ ] UNIQUE(`step_run_id`) (one attestation per step run)
  - [ ] columns: `attested_by`, `attested_at`, `outcome`, `notes`, `contract_snapshot`
- [ ] New table `compute_artifacts` exists:
  - [ ] FK to `compute_attestations.id` with ON DELETE CASCADE
  - [ ] columns: `name`, `uri`, `sha256`, `bytes`, `created_at`
- [ ] Alembic migration applies cleanly: `python -m alembic upgrade head`

## B. Manifest validation

- [ ] Manifest step schema supports `step_type` and `compute_contract`.
- [ ] Backward compatible: missing/null `step_type` behaves as `"task"`.
- [ ] Validation enforced:
  - [ ] If `step_type == "compute"`, `compute_contract` is required.
  - [ ] Required keys exist: `executor`, `inputs[]`, `outputs[]`, `verification`.
  - [ ] `verification` must equal `"operator_attest"` in MVP.
- [ ] Invalid compute steps are rejected with a clear error (422 preferred).

## C. Runner gating behavior

- [ ] When a compute step is reached during `execute_manifest()`:
  - [ ] A `DagStepRun` is created with `status="WAITING_FOR_ATTESTATION"`, `started_at` set, `ended_at` null.
  - [ ] The `DagRun.status` is set to `"waiting"` and the runner returns immediately.
  - [ ] No LLM call occurs for compute steps (`llm_complete()` not called).
  - [ ] No PromptArtifact/LLMCallArtifact/ParsedOutputArtifact is written for compute steps.
- [ ] Downstream steps do not execute while a compute step is waiting.

## D. Attestation + artifacts

- [ ] Endpoint exists: `POST /api/runs/{run_id}/steps/{step_run_id}/attest`
- [ ] Validations:
  - [ ] step_run belongs to run_id
  - [ ] step_run.status must be `WAITING_FOR_ATTESTATION`
  - [ ] only one attestation per step_run_id
- [ ] Attestation persists:
  - [ ] row in `compute_attestations`
  - [ ] rows in `compute_artifacts`
  - [ ] `DagStepRun.status` flips to SUCCESS or FAIL
- [ ] If outcome is FAIL:
  - [ ] `DagRun.status="error"` and `ended_at` set.

## E. Resume semantics (deterministic, idempotent)

- [ ] Endpoint exists: `POST /api/runs/{run_id}/resume`
- [ ] Resume preconditions:
  - [ ] run.status must be `"waiting"` else 409
- [ ] Resume uses existing state:
  - [ ] does not create a new DagRun
  - [ ] does not duplicate step runs
  - [ ] does not rerun SUCCESS steps
- [ ] Resume reconstructs chaining state from DB:
  - [ ] canonical outputs for SUCCESS steps are used as upstream inputs
- [ ] After resume, if all steps complete:
  - [ ] run.status is `"success"` or `"error"` and `ended_at` set.

## F. Manual end-to-end test

- [ ] Manifest steps: A (task) → B (compute) → C (task)
- [ ] Run:
  - [ ] A SUCCESS
  - [ ] B WAITING_FOR_ATTESTATION
  - [ ] run.status waiting
  - [ ] C not executed
- [ ] Attest B SUCCESS with artifact refs
- [ ] Resume run:
  - [ ] C executes
  - [ ] run completes success/error
- [ ] Calling resume twice is safe (no duplicates)
