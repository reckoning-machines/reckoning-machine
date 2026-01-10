from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from app.db.session import get_db
from app.core.runner import execute_manifest
from app.db import models
from sqlalchemy import select

router = APIRouter()

@router.post("/runs")
def run_manifest(body: dict, db: Session = Depends(get_db)):
    manifest_id = UUID(body["manifest_id"])
    initiated_by = body.get("initiated_by")
    run_id = execute_manifest(manifest_id, db, initiated_by)
    return {"run_id": str(run_id)}

@router.get("/runs")
def list_runs(db: Session = Depends(get_db)):
    runs = db.scalars(select(models.DagRun)).all()
    return [{"id": str(r.id), "status": r.status, "manifest_id": str(r.manifest_id), "created_at": r.created_at} for r in runs]

@router.get("/runs/{run_id}")
def get_run(run_id: UUID, db: Session = Depends(get_db)):
    run = db.get(models.DagRun, run_id)
    if not run:
        raise HTTPException(404, "dag_run not found")
    return {
        "id": str(run.id),
        "status": run.status,
        "manifest_id": str(run.manifest_id),
        "created_at": run.created_at,
        "ended_at": run.ended_at,
        "initiated_by": run.initiated_by,
    }

@router.get("/runs/{run_id}/steps")
def get_run_steps(run_id: UUID, db: Session = Depends(get_db)):
    step_runs = db.scalars(select(models.DagStepRun).filter_by(dag_run_id=run_id)).all()
    return [{
        "id": str(s.id),
        "manifest_step_id": str(s.manifest_step_id),
        "status": s.status,
        "started_at": s.started_at,
        "ended_at": s.ended_at,
        "decision_rationale": s.decision_rationale,
        "execution_policy_report": s.execution_policy_report,
        "canonical_output": s.canonical_output,
        "error": s.error,
    } for s in step_runs]
