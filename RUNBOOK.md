# Runbook

This document describes operational procedures for Reckoning Machine.

---

## Prerequisites

- PostgreSQL 14 or newer
- Python 3.10 or newer
- Network access between app host and database

---

## Environment variables

Required:
- DATABASE_URL

Optional:
- LLM_PROVIDER
- LLM_MODEL
- LLM_API_KEY
- LLM_BASE_URL

All configuration is via environment variables. No secrets are hardcoded.

---

## Startup procedure

1. Activate virtual environment
2. Verify DATABASE_URL is set
3. Run Alembic migrations
4. Start FastAPI server

Example:

- python -m alembic upgrade head
- uvicorn app.main:app --host 0.0.0.0 --port 8000

---

## Health checks

- GET /health
- GET /db/ping

Both must return success before accepting traffic.

## Paused runs and operator intervention

A run may enter a `waiting` state if execution reaches an external compute step.

This is expected behavior.

In this state:
- execution is paused deterministically
- no downstream steps will execute
- the service remains healthy

Execution resumes only after an operator submits an attestation
recording the outcome and artifacts of the external computation.

---

## Common failure modes

Database connection failure  
Check security groups, subnet routing, and credentials.

Migration failure  
Confirm DATABASE_URL and driver availability.

LLM failure  
The affected step fails and execution halts. Downstream steps do not execute.

External compute pause  
A run may pause in `waiting` state pending operator attestation.
This is not a failure condition.


---

## Data integrity guarantees

- Runs are immutable
- Step runs are append-only
- Artifacts are never deleted automatically

Backups should be taken at the database level.

---

## Safe restart

The service is stateless.
Restarting the process does not affect in-progress data.
Paused runs remain in `waiting` state until resumed.

---

## Logging and inspection

Primary inspection is via database queries.
Logs are supplemental.

This is intentional.

---

## Shutdown

Stop the FastAPI process.
No drain or cleanup is required.

---

## Operational philosophy

Prefer correctness over availability.
Prefer explicit failure over partial success.
