"""Add webhook_events table (table 14).

Revision ID: a7b2c9d3e4f1
Revises: 304cd6261f7a
Create Date: 2026-04-02 18:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "a7b2c9d3e4f1"
down_revision = "304cd6261f7a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "event_type",
            sa.String(100),
            nullable=False,
            server_default="ORGANIZATION_SOCIAL_ACTION_NOTIFICATIONS",
        ),
        sa.Column("action", sa.String(50), nullable=False, server_default=""),
        sa.Column("notification_id", sa.Integer(), nullable=False),
        sa.Column("organization_urn", sa.String(200), nullable=False, server_default=""),
        sa.Column("source_post_urn", sa.String(200), nullable=True),
        sa.Column("generated_activity_urn", sa.String(200), nullable=False, server_default=""),
        sa.Column("actor_urn", sa.String(200), nullable=True),
        sa.Column("comment_text", sa.Text(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column("processed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("queue_item_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("notification_id"),
    )
    op.create_index("ix_webhook_events_received_at", "webhook_events", ["received_at"])
    op.create_index("ix_webhook_events_action", "webhook_events", ["action"])
    op.create_index("ix_webhook_events_notification_id", "webhook_events", ["notification_id"])
    op.create_index("ix_webhook_events_processed", "webhook_events", ["processed"])


def downgrade() -> None:
    op.drop_index("ix_webhook_events_processed", table_name="webhook_events")
    op.drop_index("ix_webhook_events_notification_id", table_name="webhook_events")
    op.drop_index("ix_webhook_events_action", table_name="webhook_events")
    op.drop_index("ix_webhook_events_received_at", table_name="webhook_events")
    op.drop_table("webhook_events")
