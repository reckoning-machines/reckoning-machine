import datetime
from typing import Any, Dict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.llm_router import llm_complete
from app.core.policy import evaluate_policy
from app.db import models


def _now_utc() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def execute_manifest(manifest_id: UUID, db: Session, initiated_by: str | None = None) -> UUID:
    """
    Execute a manifest sequentially with deterministic gating + audit logging.

    Principles:
    - Only canonical_output chains forward.
    - execution_policy_report is authoritative.
    - decision_rationale is stored as an explanatory artifact and may be validated by policy.
    """
    run_started = _now_utc()

    dag_run = models.DagRun(
        manifest_id=manifest_id,
        status="running",
        started_at=run_started,
        initiated_by=initiated_by,
    )
    db.add(dag_run)
    db.commit()
    db.refresh(dag_run)

    manifest = db.get(models.Manifest, manifest_id)
    if not manifest:
        raise ValueError("Manifest not found")

    steps = (
        db.scalars(
            select(models.ManifestStep)
            .filter_by(manifest_id=manifest_id)
            .order_by(models.ManifestStep.order_index)
        )
        .all()
    )

    canonical_by_step_key: dict[str, dict] = {}
    step_status: dict[str, str] = {}
    error_found = False

    for step in steps:
        depends_on = step.depends_on or []

        if any(step_status.get(dep) != "SUCCESS" for dep in depends_on):
            step_status[step.step_key] = "SKIPPED"
            _record_skipped_step(db=db, dag_run_id=dag_run.id, step=step)
            continue

        step_type = (getattr(step, "step_type", None) or "task").strip().lower()
        if step_type == "compute":
            step_run = models.DagStepRun(
                dag_run_id=dag_run.id,
                manifest_step_id=step.id,
                status="WAITING_FOR_ATTESTATION",
                started_at=_now_utc(),
                ended_at=None,
            )
            db.add(step_run)
            dag_run.status = "waiting"
            db.commit()
            return dag_run.id

        upstream = {k: canonical_by_step_key.get(k) for k in depends_on}

        prompt_payload: Dict[str, Any] = {
            "step_key": step.step_key,
            "task_id": str(step.task_id) if step.task_id else None,
            "config": step.config or {},
            "upstream_canonical": upstream,
        }

        rendered_prompt = (
            "Execute step.\n\n"
            f"INPUT_JSON:\n{prompt_payload}\n\n"
            "Return STRICT JSON only with keys: decision_rationale, output_json."
        )

        step_run = models.DagStepRun(
            dag_run_id=dag_run.id,
            manifest_step_id=step.id,
            status="RUNNING",
            started_at=_now_utc(),
        )
        db.add(step_run)
        db.commit()
        db.refresh(step_run)

        llm_result = llm_complete(rendered_prompt)

        db.add(
            models.LLMCallArtifact(
                step_run_id=step_run.id,
                provider=llm_result.get("provider"),
                model=llm_result.get("model"),
                request_json=llm_result.get("request_json"),
                response_json=llm_result.get("response_json") or {"raw_text": llm_result.get("raw_text")},
                latency_ms=llm_result.get("latency_ms"),
            )
        )
        db.commit()

        parsed = llm_result.get("parsed_json") or {}
        decision_rationale = parsed.get("decision_rationale")
        output_json = parsed.get("output_json")

        policy_status, report_json = evaluate_policy(
            step=step,
            output_json=output_json,
            decision_rationale=decision_rationale,
        )

        canonical_output = output_json if policy_status == "PASS" else None
        final_status = "SUCCESS" if policy_status == "PASS" else "FAIL"

        if final_status == "FAIL":
            error_found = True

        step_status[step.step_key] = final_status

        db.add(
            models.PromptArtifact(
                step_run_id=step_run.id,
                rendered_prompt=rendered_prompt,
                context={"prompt_payload": prompt_payload},
                token_estimate=None,
            )
        )
        db.add(
            models.ParsedOutputArtifact(
                step_run_id=step_run.id,
                output_text=llm_result.get("raw_text"),
                output_json=output_json,
                extraction_report=llm_result.get("json_errors"),
            )
        )

        step_run.status = final_status
        step_run.ended_at = _now_utc()
        step_run.decision_rationale = decision_rationale
        step_run.execution_policy_report = report_json
        step_run.canonical_output = canonical_output

        db.commit()

        if final_status == "SUCCESS" and canonical_output is not None:
            canonical_by_step_key[step.step_key] = canonical_output

    dag_run.status = "error" if error_found else "success"
    dag_run.ended_at = _now_utc()
    db.commit()

    return dag_run.id


def resume_run(run_id: UUID, db: Session, initiated_by: str | None = None) -> UUID:
    dag_run = db.get(models.DagRun, run_id)
    if not dag_run:
        raise ValueError("Run not found")

    if dag_run.status != "waiting":
        raise ValueError("Run not in waiting status")

    steps = (
        db.scalars(
            select(models.ManifestStep)
            .filter_by(manifest_id=dag_run.manifest_id)
            .order_by(models.ManifestStep.order_index)
        )
        .all()
    )

    step_by_id: dict[UUID, models.ManifestStep] = {s.id: s for s in steps}

    step_runs = (
        db.scalars(
            select(models.DagStepRun)
            .filter_by(dag_run_id=dag_run.id)
            .order_by(models.DagStepRun.started_at)
        )
        .all()
    )

    for sr in step_runs:
        if sr.manifest_step_id not in step_by_id:
            raise ValueError("Manifest steps changed since run started")

    existing_by_step_key: dict[str, models.DagStepRun] = {}
    for sr in step_runs:
        ms = step_by_id.get(sr.manifest_step_id)
        if not ms:
            continue
        existing_by_step_key[ms.step_key] = sr

    canonical_by_step_key: dict[str, dict] = {}
    step_status: dict[str, str] = {}
    error_found = False

    for step_key, sr in existing_by_step_key.items():
        st = sr.status
        if st in {"SUCCESS", "FAIL", "SKIPPED", "WAITING_FOR_ATTESTATION"}:
            step_status[step_key] = st
        if st == "FAIL":
            error_found = True
        if st == "SUCCESS" and sr.canonical_output is not None:
            canonical_by_step_key[step_key] = sr.canonical_output

    dag_run.status = "running"
    dag_run.initiated_by = initiated_by if initiated_by is not None else dag_run.initiated_by
    db.commit()

    for step in steps:
        existing = existing_by_step_key.get(step.step_key)
        if existing and existing.status in {"SUCCESS", "FAIL", "SKIPPED"}:
            continue
        if existing and existing.status == "RUNNING":
            raise ValueError("Run has an in-flight step; cannot resume deterministically")

        depends_on = step.depends_on or []
        if any(step_status.get(dep) != "SUCCESS" for dep in depends_on):
            if not existing:
                step_status[step.step_key] = "SKIPPED"
                _record_skipped_step(db=db, dag_run_id=dag_run.id, step=step)
            continue

        step_type = (getattr(step, "step_type", None) or "task").strip().lower()
        if step_type == "compute":
            if existing and existing.status == "WAITING_FOR_ATTESTATION":
                dag_run.status = "waiting"
                db.commit()
                return dag_run.id

            if not existing:
                step_run = models.DagStepRun(
                    dag_run_id=dag_run.id,
                    manifest_step_id=step.id,
                    status="WAITING_FOR_ATTESTATION",
                    started_at=_now_utc(),
                    ended_at=None,
                )
                db.add(step_run)
                dag_run.status = "waiting"
                db.commit()
                return dag_run.id

        upstream = {k: canonical_by_step_key.get(k) for k in depends_on}

        prompt_payload: Dict[str, Any] = {
            "step_key": step.step_key,
            "task_id": str(step.task_id) if step.task_id else None,
            "config": step.config or {},
            "upstream_canonical": upstream,
        }

        rendered_prompt = (
            "Execute step.\n\n"
            f"INPUT_JSON:\n{prompt_payload}\n\n"
            "Return STRICT JSON only with keys: decision_rationale, output_json."
        )

        step_run = models.DagStepRun(
            dag_run_id=dag_run.id,
            manifest_step_id=step.id,
            status="RUNNING",
            started_at=_now_utc(),
        )
        db.add(step_run)
        db.commit()
        db.refresh(step_run)

        llm_result = llm_complete(rendered_prompt)

        db.add(
            models.LLMCallArtifact(
                step_run_id=step_run.id,
                provider=llm_result.get("provider"),
                model=llm_result.get("model"),
                request_json=llm_result.get("request_json"),
                response_json=llm_result.get("response_json") or {"raw_text": llm_result.get("raw_text")},
                latency_ms=llm_result.get("latency_ms"),
            )
        )
        db.commit()

        parsed = llm_result.get("parsed_json") or {}
        decision_rationale = parsed.get("decision_rationale")
        output_json = parsed.get("output_json")

        policy_status, report_json = evaluate_policy(
            step=step,
            output_json=output_json,
            decision_rationale=decision_rationale,
        )

        canonical_output = output_json if policy_status == "PASS" else None
        final_status = "SUCCESS" if policy_status == "PASS" else "FAIL"

        if final_status == "FAIL":
            error_found = True

        step_status[step.step_key] = final_status

        db.add(
            models.PromptArtifact(
                step_run_id=step_run.id,
                rendered_prompt=rendered_prompt,
                context={"prompt_payload": prompt_payload},
                token_estimate=None,
            )
        )
        db.add(
            models.ParsedOutputArtifact(
                step_run_id=step_run.id,
                output_text=llm_result.get("raw_text"),
                output_json=output_json,
                extraction_report=llm_result.get("json_errors"),
            )
        )

        step_run.status = final_status
        step_run.ended_at = _now_utc()
        step_run.decision_rationale = decision_rationale
        step_run.execution_policy_report = report_json
        step_run.canonical_output = canonical_output

        db.commit()

        if final_status == "SUCCESS" and canonical_output is not None:
            canonical_by_step_key[step.step_key] = canonical_output

    dag_run.status = "error" if (error_found or any(v == "FAIL" for v in step_status.values())) else "success"
    dag_run.ended_at = _now_utc()
    db.commit()
    return dag_run.id


def _record_skipped_step(db: Session, dag_run_id: UUID, step: models.ManifestStep) -> None:
    now = _now_utc()
    step_run = models.DagStepRun(
        dag_run_id=dag_run_id,
        manifest_step_id=step.id,
        status="SKIPPED",
        started_at=now,
        ended_at=now,
        decision_rationale=None,
        execution_policy_report={"outcome": "SKIPPED", "reason": "dependency_not_success"},
        canonical_output=None,
    )
    db.add(step_run)
    db.commit()
