"""add idempotency records and active-claim uniqueness

Revision ID: 9a7f2c1d4e60
Revises: 66e373c68ca8
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "9a7f2c1d4e60"
down_revision: Union[str, Sequence[str], None] = "66e373c68ca8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("uq_categories_name_ci", "categories", [sa.text("lower(name)")], unique=True)
    op.create_check_constraint(
        "ck_item_reports_found_verification_required",
        "item_reports",
        "report_type <> 'FOUND' OR (verification_question IS NOT NULL AND verification_answer_hash IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_item_reports_lost_private_fields_empty",
        "item_reports",
        "report_type <> 'LOST' OR (verification_question IS NULL AND verification_answer_hash IS NULL AND storage_instructions IS NULL)",
    )
    op.create_table(
        "idempotency_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation", sa.String(length=100), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=False),
        sa.Column("response_body", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name="fk_idempotency_records_actor_id_users", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_idempotency_records"),
        sa.UniqueConstraint("actor_id", "operation", "key", name="idempotency_actor_operation_key"),
    )
    op.create_index("ix_idempotency_records_actor_id", "idempotency_records", ["actor_id"])
    op.create_index(
        "uq_claim_active_pair_claimant",
        "claims",
        ["lost_report_id", "found_report_id", "claimant_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING','UNDER_REVIEW','APPROVED')"),
    )


def downgrade() -> None:
    op.drop_index("uq_claim_active_pair_claimant", table_name="claims")
    op.drop_index("ix_idempotency_records_actor_id", table_name="idempotency_records")
    op.drop_table("idempotency_records")
    op.drop_constraint("ck_item_reports_lost_private_fields_empty", "item_reports", type_="check")
    op.drop_constraint("ck_item_reports_found_verification_required", "item_reports", type_="check")
    op.drop_index("uq_categories_name_ci", table_name="categories")
