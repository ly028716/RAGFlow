"""Remove obsolete OpenClaw tables while preserving Web Scraper data.

Revision ID: 012_remove_openclaw_tables
Revises: 011_add_web_scraper_indexes
Create Date: 2026-07-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "012_remove_openclaw_tables"
down_revision: Union[str, None] = "011_add_web_scraper_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove the two obsolete OpenClaw tables and their indexes."""
    inspector = sa.inspect(op.get_bind())
    for table_name in ("openclaw_tool_calls", "openclaw_tools"):
        if inspector.has_table(table_name):
            # MySQL drops a table's indexes automatically.  Avoid requiring
            # index names that may differ across historical installations.
            op.drop_table(table_name)


def downgrade() -> None:
    """Restore the OpenClaw schema defined in migration 009."""
    op.create_table(
        "openclaw_tools",
        sa.Column("id", sa.Integer(), nullable=False, comment="Tool ID"),
        sa.Column("name", sa.String(100), nullable=False, comment="Unique tool name"),
        sa.Column("display_name", sa.String(200), nullable=False, comment="Tool display name"),
        sa.Column("description", sa.Text(), nullable=False, comment="Tool description"),
        sa.Column("endpoint_url", sa.String(500), nullable=False, comment="Tool endpoint URL"),
        sa.Column("method", sa.String(10), nullable=False, comment="HTTP method"),
        sa.Column("auth_type", sa.String(50), nullable=False, comment="Authentication type"),
        sa.Column("auth_config", sa.JSON(), nullable=True, comment="Authentication configuration"),
        sa.Column("parameters_schema", sa.JSON(), nullable=True, comment="Parameter schema"),
        sa.Column("response_schema", sa.JSON(), nullable=True, comment="Response schema"),
        sa.Column("status", sa.String(20), nullable=False, comment="Tool status"),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, comment="Whether the tool is built in"),
        sa.Column("created_by", sa.Integer(), nullable=True, comment="Creator user ID"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="Creation time"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="Update time"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_openclaw_tool_name"),
        comment="OpenClaw tool configuration",
    )
    op.create_index("ix_openclaw_tools_id", "openclaw_tools", ["id"], unique=False)
    op.create_index("ix_openclaw_tools_name", "openclaw_tools", ["name"], unique=True)
    op.create_index("ix_openclaw_tools_status", "openclaw_tools", ["status"], unique=False)

    op.create_table(
        "openclaw_tool_calls",
        sa.Column("id", sa.Integer(), nullable=False, comment="Tool call ID"),
        sa.Column("tool_id", sa.Integer(), nullable=False, comment="Tool ID"),
        sa.Column("agent_id", sa.String(100), nullable=True, comment="Agent ID"),
        sa.Column("user_id", sa.Integer(), nullable=True, comment="User ID"),
        sa.Column("request_params", sa.JSON(), nullable=True, comment="Request parameters"),
        sa.Column("response_data", sa.JSON(), nullable=True, comment="Response data"),
        sa.Column("status", sa.String(20), nullable=False, comment="Call status"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="Error message"),
        sa.Column("execution_time", sa.Float(), nullable=True, comment="Execution time"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="Call time"),
        sa.ForeignKeyConstraint(["tool_id"], ["openclaw_tools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        comment="OpenClaw tool call log",
    )
    op.create_index("ix_openclaw_tool_calls_id", "openclaw_tool_calls", ["id"], unique=False)
    op.create_index(
        "ix_openclaw_tool_calls_tool_id", "openclaw_tool_calls", ["tool_id"], unique=False
    )
    op.create_index(
        "ix_openclaw_tool_calls_agent_id", "openclaw_tool_calls", ["agent_id"], unique=False
    )
    op.create_index(
        "ix_openclaw_tool_calls_user_id", "openclaw_tool_calls", ["user_id"], unique=False
    )
    op.create_index(
        "ix_openclaw_tool_calls_status", "openclaw_tool_calls", ["status"], unique=False
    )
    op.create_index(
        "ix_openclaw_tool_calls_created_at",
        "openclaw_tool_calls",
        ["created_at"],
        unique=False,
    )
