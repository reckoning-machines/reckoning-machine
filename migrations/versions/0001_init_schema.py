"""init_schema\n\nRevision ID: 0001_init_schema\nRevises: \nCreate Date: 2024-06-12\n"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as psql
import uuid

# revision identifiers, used by Alembic.
revision = '0001_init_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'tasks',
        sa.Column('id', psql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.Text(), nullable=False, unique=True),
        sa.Column('description', sa.Text()),
        sa.Column('prompt_template', sa.Text()),
        sa.Column('extract_schema', psql.JSONB()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_table(
        'manifests',
        sa.Column('id', psql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.Text(), nullable=False, unique=True),
        sa.Column('description', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_table(
        'manifest_steps',
        sa.Column('id', psql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('manifest_id', psql.UUID(as_uuid=True), sa.ForeignKey('manifests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('step_key', sa.Text(), nullable=False),
        sa.Column('task_id', psql.UUID(as_uuid=True), sa.ForeignKey('tasks.id')), 
        sa.Column('depends_on', psql.JSONB()),
        sa.Column('chaining', psql.JSONB()),
        sa.Column('config', psql.JSONB()),
        sa.Column('order_index', sa.Integer()),
        sa.UniqueConstraint('manifest_id', 'step_key', name='_manifest_step_uc'),
    )
    op.create_index('ix_manifest_steps_manifest_id', 'manifest_steps', ['manifest_id'])
    op.create_table(
        'dag_runs',
        sa.Column('id', psql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('manifest_id', psql.UUID(as_uuid=True), sa.ForeignKey('manifests.id'), nullable=False),
        sa.Column('status', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('ended_at', sa.DateTime(timezone=True)),
        sa.Column('initiated_by', sa.Text()),
        sa.Column('run_params', psql.JSONB()),
    )
    op.create_index('ix_dag_runs_manifest_id', 'dag_runs', ['manifest_id'])
    op.create_table(
        'dag_step_runs',
        sa.Column('id', psql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('dag_run_id', psql.UUID(as_uuid=True), sa.ForeignKey('dag_runs.id', ondelete="CASCADE"), nullable=False),
        sa.Column('manifest_step_id', psql.UUID(as_uuid=True), sa.ForeignKey('manifest_steps.id'), nullable=False),
        sa.Column('status', sa.Text()),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('ended_at', sa.DateTime(timezone=True)),
        sa.Column('input_hash', sa.Text()),
        sa.Column('error', sa.Text()),
        sa.Column('decision_rationale', psql.JSONB()),
        sa.Column('execution_policy_report', psql.JSONB()),
        sa.Column('canonical_output', psql.JSONB()),
    )
    op.create_index('ix_dag_step_runs_dag_run_id', 'dag_step_runs', ['dag_run_id'])
    op.create_table(
        'prompt_artifacts',
        sa.Column('id', psql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('step_run_id', psql.UUID(as_uuid=True), sa.ForeignKey('dag_step_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rendered_prompt', sa.Text()),
        sa.Column('context', psql.JSONB()),
        sa.Column('token_estimate', sa.Integer()),
    )
    op.create_table(
        'llm_call_artifacts',
        sa.Column('id', psql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('step_run_id', psql.UUID(as_uuid=True), sa.ForeignKey('dag_step_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.Text()),
        sa.Column('model', sa.Text()),
        sa.Column('request_json', psql.JSONB()),
        sa.Column('response_json', psql.JSONB()),
        sa.Column('latency_ms', sa.Integer()),
    )
    op.create_table(
        'parsed_output_artifacts',
        sa.Column('id', psql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('step_run_id', psql.UUID(as_uuid=True), sa.ForeignKey('dag_step_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('output_text', sa.Text()),
        sa.Column('output_json', psql.JSONB()),
        sa.Column('extraction_report', psql.JSONB()),
    )

def downgrade():
    op.drop_table('parsed_output_artifacts')
    op.drop_table('llm_call_artifacts')
    op.drop_table('prompt_artifacts')
    op.drop_index('ix_dag_step_runs_dag_run_id', table_name='dag_step_runs')
    op.drop_table('dag_step_runs')
    op.drop_index('ix_dag_runs_manifest_id', table_name='dag_runs')
    op.drop_table('dag_runs')
    op.drop_index('ix_manifest_steps_manifest_id', table_name='manifest_steps')
    op.drop_table('manifest_steps')
    op.drop_table('manifests')
    op.drop_table('tasks')
