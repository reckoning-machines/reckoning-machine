from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from app.db import crud, schemas
from app.db.session import get_db

router = APIRouter()

@router.get("/tasks", response_model=list[schemas.TaskRead])
def list_tasks(db: Session = Depends(get_db)):
    return crud.get_tasks(db)

@router.post("/tasks", response_model=schemas.TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(task_in: schemas.TaskCreate, db: Session = Depends(get_db)):
    try:
        task = crud.create_task(db, task_in)
        return task
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Task name must be unique.")

@router.get("/tasks/{task_id}", response_model=schemas.TaskRead)
def get_task(task_id: UUID, db: Session = Depends(get_db)):
    task = crud.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task

@router.put("/tasks/{task_id}", response_model=schemas.TaskRead)
def update_task(task_id: UUID, task_in: schemas.TaskUpdate, db: Session = Depends(get_db)):
    try:
        task = crud.update_task(db, task_id, task_in)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Task name must be unique.")
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task
