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

        # Deterministic dependency gating: must have all deps SUCCESS
        if any(step_status.get(dep) != "SUCCESS" for dep in depends_on):
            step_status[step.step_key] = "SKIPPED"
            _record_skipped_step(db=db, dag_run_id=dag_run.id, step=step)
            continue

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

        # Create step run first so artifacts can be linked deterministically
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

        # Always write LLM call artifact linked to this step run
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

        # Deterministic policy enforcement (authoritative)
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

        # Persist prompt artifact + parsed output artifact
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

        # Finalize step run record
        step_run.status = final_status
        step_run.ended_at = _now_utc()
        step_run.decision_rationale = decision_rationale
        step_run.execution_policy_report = report_json
        step_run.canonical_output = canonical_output

        db.commit()

        # Only PASS outputs are allowed to chain forward
        if final_status == "SUCCESS" and canonical_output is not None:
            canonical_by_step_key[step.step_key] = canonical_output

    dag_run.status = "error" if error_found else "success"
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
