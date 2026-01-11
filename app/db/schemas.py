from typing import Optional, List, Union
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, root_validator

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
        from_attributes = True

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

    class Config:
        from_attributes = True

# --- Manifest Step Schemas ---
class ManifestStepBase(BaseModel):
    step_key: str
    task_id: Optional[UUID] = None
    depends_on: Optional[JsonType] = None
    chaining: Optional[JsonType] = None
    config: Optional[JsonType] = None
    order_index: Optional[int] = None

    step_type: Optional[str] = None
    compute_contract: Optional[dict] = None

    @root_validator
    def validate_compute_contract(cls, values):
        raw_step_type = values.get("step_type")
        step_type = (raw_step_type or "").strip().lower() or "task"
        values["step_type"] = step_type

        contract = values.get("compute_contract")

        if step_type == "compute":
            if contract is None:
                raise ValueError("compute_contract is required when step_type == 'compute'")
            if not isinstance(contract, dict):
                raise ValueError("compute_contract must be an object")

            required_keys = {"executor", "inputs", "outputs", "verification"}
            missing = [k for k in required_keys if k not in contract]
            if missing:
                raise ValueError(f"compute_contract missing required keys: {', '.join(sorted(missing))}")

            if not isinstance(contract.get("executor"), str) or not contract.get("executor").strip():
                raise ValueError("compute_contract.executor must be a non-empty string")

            inputs = contract.get("inputs")
            if not isinstance(inputs, list) or any((not isinstance(x, str) or not x.strip()) for x in inputs):
                raise ValueError("compute_contract.inputs must be a list of non-empty strings")

            outputs = contract.get("outputs")
            if not isinstance(outputs, list) or any((not isinstance(x, str) or not x.strip()) for x in outputs):
                raise ValueError("compute_contract.outputs must be a list of non-empty strings")

            if contract.get("verification") != "operator_attest":
                raise ValueError("compute_contract.verification must equal 'operator_attest'")

        return values

class ManifestStepCreate(ManifestStepBase):
    pass

class ManifestStepRead(ManifestStepBase):
    id: UUID
    manifest_id: UUID

    class Config:
        from_attributes = True


class ComputeArtifactIn(BaseModel):
    name: str
    uri: str
    sha256: Optional[str] = None
    bytes: Optional[int] = None


class ComputeAttestIn(BaseModel):
    attested_by: str
    outcome: str
    notes: Optional[str] = None
    artifacts: List[ComputeArtifactIn] = Field(default_factory=list)

    @root_validator(skip_on_failure=True)
    def _validate_outcome(cls, values):
        outcome = (values.get("outcome") or "").strip().upper()
        values["outcome"] = outcome

        if outcome not in ("SUCCESS", "FAIL"):
            raise ValueError("outcome must be SUCCESS or FAIL")

        artifacts = values.get("artifacts")
        if artifacts is None:
            raise ValueError("artifacts field is required")

        return values


class ResumeRunIn(BaseModel):
    initiated_by: Optional[str] = None
