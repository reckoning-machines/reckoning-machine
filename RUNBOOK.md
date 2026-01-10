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

---

## Common failure modes

Database connection failure  
Check security groups, subnet routing, and credentials.

Migration failure  
Confirm DATABASE_URL and driver availability.

LLM failure  
System falls back to stub execution if configured.

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
