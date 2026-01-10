from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from app.db import crud, schemas
from app.db.session import get_db
from typing import List

router = APIRouter()

@router.get("/manifests", response_model=list[schemas.ManifestRead])
def list_manifests(db: Session = Depends(get_db)):
    return crud.get_manifests(db)

@router.post("/manifests", response_model=schemas.ManifestRead, status_code=status.HTTP_201_CREATED)
def create_manifest(manifest_in: schemas.ManifestCreate, db: Session = Depends(get_db)):
    try:
        manifest = crud.create_manifest(db, manifest_in)
        return manifest
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Manifest name must be unique.")

@router.get("/manifests/{manifest_id}", response_model=schemas.ManifestRead)
def get_manifest(manifest_id: UUID, db: Session = Depends(get_db)):
    manifest = crud.get_manifest(db, manifest_id)
    if not manifest:
        raise HTTPException(status_code=404, detail="Manifest not found.")
    return manifest

@router.put("/manifests/{manifest_id}", response_model=schemas.ManifestRead)
def update_manifest(manifest_id: UUID, manifest_in: schemas.ManifestUpdate, db: Session = Depends(get_db)):
    try:
        manifest = crud.update_manifest(db, manifest_id, manifest_in)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Manifest name must be unique.")
    if not manifest:
        raise HTTPException(status_code=404, detail="Manifest not found.")
    return manifest

@router.put("/manifests/{manifest_id}/steps", response_model=List[schemas.ManifestStepRead])
def replace_steps(manifest_id: UUID, steps_in: List[schemas.ManifestStepCreate], db: Session = Depends(get_db)):
    manifest = crud.get_manifest(db, manifest_id)
    if not manifest:
        raise HTTPException(status_code=404, detail="Manifest not found.")
    steps = crud.replace_manifest_steps(db, manifest_id, steps_in)
    return steps
