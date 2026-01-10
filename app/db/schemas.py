from typing import Optional, List, Union
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

JsonType = Union[dict, list, None]

# --- Task Schemas ---
class TaskBase(BaseModel):
    name: str
    description: Optional[str] = None
    prompt_template: Optional[str] = None
    extract_schema: Optional[JsonType] = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    description: Optional[str] = None
    prompt_template: Optional[str] = None
    extract_schema: Optional[JsonType] = None

class TaskRead(TaskBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# --- Manifest Schemas ---
class ManifestBase(BaseModel):
    name: str
    description: Optional[str] = None

class ManifestCreate(ManifestBase):
    pass

class ManifestUpdate(BaseModel):
    description: Optional[str] = None

class ManifestRead(ManifestBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# --- Manifest Step Schemas ---
class ManifestStepBase(BaseModel):
    step_key: str
    task_id: Optional[UUID] = None
    depends_on: Optional[JsonType] = None
    chaining: Optional[JsonType] = None
    config: Optional[JsonType] = None
    order_index: Optional[int] = None

class ManifestStepCreate(ManifestStepBase):
    pass

class ManifestStepRead(ManifestStepBase):
    id: UUID
    manifest_id: UUID

    class Config:
        orm_mode = True
