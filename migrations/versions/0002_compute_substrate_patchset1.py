"""compute substrate patch set 1

Revision ID: 0002_compute_substrate_patchset1
Revises: 0001_init_schema
Create Date: 2024-06-12
"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as psql
import uuid

# revision identifiers, used by Alembic.
revision = '0002_compute_substrate_patchset1'
down_revision = '0001_init_schema'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Add columns to manifest_steps
    op.add_column('manifest_steps', sa.Column('step_type', sa.Text(), nullable=True))
    op.add_column('manifest_steps', sa.Column('compute_contract', psql.JSONB(), nullable=True))

    # 2. Create compute_attestations table
    op.create_table(
        'compute_attestations',
        sa.Column('id', psql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('step_run_id', psql.UUID(as_uuid=True), sa.ForeignKey('dag_step_runs.id', ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column('attested_by', sa.Text(), nullable=False),
        sa.Column('attested_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('outcome', sa.Text(), nullable=False), # "SUCCESS" or "FAIL"
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('contract_snapshot', psql.JSONB(), nullable=True),
    )

    # 3. Create compute_artifacts table
    op.create_table(
        'compute_artifacts',
        sa.Column('id', psql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('attestation_id', psql.UUID(as_uuid=True), sa.ForeignKey('compute_attestations.id', ondelete="CASCADE"), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('uri', sa.Text(), nullable=False),
        sa.Column('sha256', sa.Text(), nullable=True),
        sa.Column('bytes', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

def downgrade():
    op.drop_table('compute_artifacts')
    op.drop_table('compute_attestations')
    op.drop_column('manifest_steps', 'compute_contract')
    op.drop_column('manifest_steps', 'step_type')
