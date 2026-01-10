import uuid
from sqlalchemy import (
    Column, String, Text, Integer, ForeignKey, DateTime, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .session import Base

class Task(Base):
    __tablename__ = "tasks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, unique=True, nullable=False)
    description = Column(Text)
    prompt_template = Column(Text)
    extract_schema = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class Manifest(Base):
    __tablename__ = "manifests"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class ManifestStep(Base):
    __tablename__ = "manifest_steps"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    manifest_id = Column(UUID(as_uuid=True), ForeignKey("manifests.id", ondelete="CASCADE"), nullable=False)
    step_key = Column(Text, nullable=False)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    depends_on = Column(JSONB)
    chaining = Column(JSONB)
    config = Column(JSONB)
    order_index = Column(Integer)
    __table_args__ = (
        UniqueConstraint('manifest_id', 'step_key', name='_manifest_step_uc'),
        Index('ix_manifest_steps_manifest_id', 'manifest_id')
    )
    manifest = relationship("Manifest", backref="steps")
    task = relationship("Task")

class DagRun(Base):
    __tablename__ = "dag_runs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    manifest_id = Column(UUID(as_uuid=True), ForeignKey("manifests.id"), nullable=False)
    status = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))
    initiated_by = Column(Text)
    run_params = Column(JSONB)
    __table_args__ = (Index('ix_dag_runs_manifest_id', 'manifest_id'),)
    manifest = relationship("Manifest")

class DagStepRun(Base):
    __tablename__ = "dag_step_runs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dag_run_id = Column(UUID(as_uuid=True), ForeignKey("dag_runs.id", ondelete="CASCADE"), nullable=False)
    manifest_step_id = Column(UUID(as_uuid=True), ForeignKey("manifest_steps.id"), nullable=False)
    status = Column(Text)
    started_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))
    input_hash = Column(Text)
    error = Column(Text)
    decision_rationale = Column(JSONB)
    execution_policy_report = Column(JSONB)
    canonical_output = Column(JSONB)
    __table_args__ = (Index('ix_dag_step_runs_dag_run_id', 'dag_run_id'),)
    dag_run = relationship("DagRun")
    manifest_step = relationship("ManifestStep")

class PromptArtifact(Base):
    __tablename__ = "prompt_artifacts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    step_run_id = Column(UUID(as_uuid=True), ForeignKey("dag_step_runs.id", ondelete="CASCADE"), nullable=False)
    rendered_prompt = Column(Text)
    context = Column(JSONB)
    token_estimate = Column(Integer)
    step_run = relationship("DagStepRun")

class LLMCallArtifact(Base):
    __tablename__ = "llm_call_artifacts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    step_run_id = Column(UUID(as_uuid=True), ForeignKey("dag_step_runs.id", ondelete="CASCADE"), nullable=False)
    provider = Column(Text)
    model = Column(Text)
    request_json = Column(JSONB)
    response_json = Column(JSONB)
    latency_ms = Column(Integer)
    step_run = relationship("DagStepRun")

class ParsedOutputArtifact(Base):
    __tablename__ = "parsed_output_artifacts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    step_run_id = Column(UUID(as_uuid=True), ForeignKey("dag_step_runs.id", ondelete="CASCADE"), nullable=False)
    output_text = Column(Text)
    output_json = Column(JSONB)
    extraction_report = Column(JSONB)
    step_run = relationship("DagStepRun")
