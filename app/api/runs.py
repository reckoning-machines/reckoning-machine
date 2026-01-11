from datetime import datetime, timezone
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.runner import execute_manifest, resume_run
from app.db import models, schemas
from app.db.session import get_db
import json

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
    return [
        {
            "id": str(r.id),
            "status": r.status,
            "manifest_id": str(r.manifest_id),
            "created_at": r.created_at,
        }
        for r in runs
    ]


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
    return [
        {
            "id": str(s.id),
            "manifest_step_id": str(s.manifest_step_id),
            "status": s.status,
            "started_at": s.started_at,
            "ended_at": s.ended_at,
            "decision_rationale": s.decision_rationale,
            "execution_policy_report": s.execution_policy_report,
            "canonical_output": s.canonical_output,
            "error": s.error,
        }
        for s in step_runs
    ]


@router.post("/runs/{run_id}/steps/{step_run_id}/attest")
def attest_compute_step(
    run_id: UUID,
    step_run_id: UUID,
    body: schemas.ComputeAttestIn,
    db: Session = Depends(get_db),
):
    dag_run = db.get(models.DagRun, run_id)
    if not dag_run:
        raise HTTPException(404, "dag_run not found")

    step_run = db.get(models.DagStepRun, step_run_id)
    if not step_run:
        raise HTTPException(404, "dag_step_run not found")

    if step_run.dag_run_id != run_id:
        raise HTTPException(409, "dag_step_run does not belong to dag_run")

    if step_run.status != "WAITING_FOR_ATTESTATION":
        raise HTTPException(409, "dag_step_run is not WAITING_FOR_ATTESTATION")

    existing = db.execute(
        text("select 1 from compute_attestations where step_run_id = :step_run_id"),
        {"step_run_id": step_run_id},
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(409, "compute attestation already exists for this step_run_id")

    contract_snapshot = db.execute(
        text("select compute_contract from manifest_steps where id = :manifest_step_id"),
        {"manifest_step_id": step_run.manifest_step_id},
    ).scalar_one_or_none()

    if isinstance(contract_snapshot, dict) or isinstance(contract_snapshot, list):
        contract_snapshot = json.dumps(contract_snapshot)
    elif contract_snapshot is not None and not isinstance(contract_snapshot, str):
        contract_snapshot = json.dumps(contract_snapshot)

    attestation_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    try:
        db.execute(
            text(
                """
                insert into compute_attestations
                (id, step_run_id, attested_by, attested_at, outcome, notes, contract_snapshot)
                values
                (:id, :step_run_id, :attested_by, :attested_at, :outcome, :notes, (:contract_snapshot)::jsonb)
                """
            ),
            {
                "id": attestation_id,
                "step_run_id": step_run_id,
                "attested_by": body.attested_by,
                "attested_at": now,
                "outcome": body.outcome,
                "notes": body.notes,
                "contract_snapshot": contract_snapshot,
            },
        )

        for a in body.artifacts:
            db.execute(
                text(
                    """
                    insert into compute_artifacts
                    (id, attestation_id, name, uri, sha256, bytes, created_at)
                    values
                    (:id, :attestation_id, :name, :uri, :sha256, :bytes, :created_at)
                    """
                ),
                {
                    "id": uuid.uuid4(),
                    "attestation_id": attestation_id,
                    "name": a.name,
                    "uri": a.uri,
                    "sha256": a.sha256,
                    "bytes": a.bytes,
                    "created_at": now,
                },
            )

        step_run.status = body.outcome
        step_run.ended_at = now

        if body.outcome == "FAIL":
            dag_run.status = "error"
            dag_run.ended_at = now

        db.commit()

    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "compute attestation already exists for this step_run_id")
    except Exception:
        db.rollback()
        raise

    return {"ok": True, "step_run_id": str(step_run_id), "new_status": body.outcome}


@router.post("/runs/{run_id}/resume")
def resume_existing_run(
    run_id: UUID,
    body: schemas.ResumeRunIn,
    db: Session = Depends(get_db),
):
    dag_run = db.get(models.DagRun, run_id)
    if not dag_run:
        raise HTTPException(404, "dag_run not found")

    if dag_run.status != "waiting":
        raise HTTPException(409, "dag_run is not in waiting status")

    try:
        resume_run(run_id, db, body.initiated_by)
    except ValueError as e:
        raise HTTPException(409, str(e))

    dag_run = db.get(models.DagRun, run_id)
    step_runs = db.scalars(select(models.DagStepRun).filter_by(dag_run_id=run_id)).all()

    return {
        "id": str(dag_run.id),
        "status": dag_run.status,
        "ended_at": dag_run.ended_at,
        "steps": [{"manifest_step_id": str(s.manifest_step_id), "status": s.status} for s in step_runs],
    }
