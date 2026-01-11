from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from . import models
from . import schemas

# --- Task CRUD ---
def create_task(db: Session, task_in: schemas.TaskCreate) -> models.Task:
    task = models.Task(**task_in.dict())
    db.add(task)
    try:
        db.commit()
        db.refresh(task)
    except IntegrityError:
        db.rollback()
        raise
    return task

def get_tasks(db: Session) -> List[models.Task]:
    return db.scalars(select(models.Task)).all()

def get_task(db: Session, task_id: UUID) -> Optional[models.Task]:
    return db.get(models.Task, task_id)

def update_task(db: Session, task_id: UUID, task_in: schemas.TaskUpdate) -> Optional[models.Task]:
    task = db.get(models.Task, task_id)
    if not task:
        return None
    for key, value in task_in.dict(exclude_unset=True).items():
        setattr(task, key, value)
    try:
        db.commit()
        db.refresh(task)
    except IntegrityError:
        db.rollback()
        raise
    return task

# --- Manifest CRUD ---
def create_manifest(db: Session, manifest_in: schemas.ManifestCreate) -> models.Manifest:
    manifest = models.Manifest(**manifest_in.dict())
    db.add(manifest)
    try:
        db.commit()
        db.refresh(manifest)
    except IntegrityError:
        db.rollback()
        raise
    return manifest

def get_manifests(db: Session) -> List[models.Manifest]:
    return db.scalars(select(models.Manifest)).all()

def get_manifest(db: Session, manifest_id: UUID) -> Optional[models.Manifest]:
    return db.get(models.Manifest, manifest_id)

def update_manifest(db: Session, manifest_id: UUID, manifest_in: schemas.ManifestUpdate) -> Optional[models.Manifest]:
    manifest = db.get(models.Manifest, manifest_id)
    if not manifest:
        return None
    for key, value in manifest_in.dict(exclude_unset=True).items():
        setattr(manifest, key, value)
    try:
        db.commit()
        db.refresh(manifest)
    except IntegrityError:
        db.rollback()
        raise
    return manifest

# --- Manifest Steps (replace all steps for manifest) ---
def replace_manifest_steps(
    db: Session,
    manifest_id: UUID,
    steps_in: List[schemas.ManifestStepCreate],
) -> List[models.ManifestStep]:
    manifest = db.get(models.Manifest, manifest_id)
    if not manifest:
        return []

    try:
        db.query(models.ManifestStep).filter(models.ManifestStep.manifest_id == manifest_id).delete()

        steps: List[models.ManifestStep] = []
        for order, step_in in enumerate(steps_in):
            data = step_in.dict()
            data["manifest_id"] = manifest_id
            data["order_index"] = data.get("order_index") if data.get("order_index") is not None else order
            step = models.ManifestStep(**data)
            db.add(step)
            steps.append(step)

        db.commit()

        for s in steps:
            db.refresh(s)

        return steps

    except Exception:
        db.rollback()
        raise
