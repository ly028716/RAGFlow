"""添加OpenClaw工具表

创建OpenClaw工具配置表和工具调用记录表，用于支持OpenClaw工具注册和调用追踪。

Revision ID: 009_openclaw_tools
Revises: 008_fix_tooltype_enum_lowercase
Create Date: 2026-03-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '009_openclaw_tools'
down_revision: Union[str, None] = '008_fix_tooltype_enum_lowercase'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级数据库"""

    # 创建openclaw_tools表
    op.create_table(
        'openclaw_tools',
        sa.Column('id', sa.Integer(), nullable=False, comment='工具ID'),
        sa.Column('name', sa.String(100), nullable=False, comment='工具名称（唯一）'),
        sa.Column('display_name', sa.String(200), nullable=False, comment='工具显示名称'),
        sa.Column('description', sa.Text(), nullable=False, comment='工具描述'),
        sa.Column('endpoint_url', sa.String(500), nullable=False, comment='工具端点URL'),
        sa.Column('method', sa.String(10), nullable=False, comment='HTTP方法（GET/POST）'),
        sa.Column('auth_type', sa.String(50), nullable=False, comment='认证类型'),
        sa.Column('auth_config', sa.JSON(), nullable=True, comment='认证配置（JSON）'),
        sa.Column('parameters_schema', sa.JSON(), nullable=True, comment='参数Schema（JSON Schema）'),
        sa.Column('response_schema', sa.JSON(), nullable=True, comment='响应Schema（JSON Schema）'),
        sa.Column('status', sa.String(20), nullable=False, comment='工具状态'),
        sa.Column('is_builtin', sa.Boolean(), nullable=False, comment='是否为内置工具'),
        sa.Column('created_by', sa.Integer(), nullable=True, comment='创建者用户ID'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_openclaw_tool_name'),
        comment='OpenClaw工具配置表'
    )
    op.create_index('ix_openclaw_tools_id', 'openclaw_tools', ['id'], unique=False)
    op.create_index('ix_openclaw_tools_name', 'openclaw_tools', ['name'], unique=True)
    op.create_index('ix_openclaw_tools_status', 'openclaw_tools', ['status'], unique=False)

    # 创建openclaw_tool_calls表
    op.create_table(
        'openclaw_tool_calls',
        sa.Column('id', sa.Integer(), nullable=False, comment='调用记录ID'),
        sa.Column('tool_id', sa.Integer(), nullable=False, comment='工具ID'),
        sa.Column('agent_id', sa.String(100), nullable=True, comment='Agent ID'),
        sa.Column('user_id', sa.Integer(), nullable=True, comment='用户ID'),
        sa.Column('request_params', sa.JSON(), nullable=True, comment='请求参数（JSON）'),
        sa.Column('response_data', sa.JSON(), nullable=True, comment='响应数据（JSON）'),
        sa.Column('status', sa.String(20), nullable=False, comment='调用状态'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='错误信息'),
        sa.Column('execution_time', sa.Float(), nullable=True, comment='执行时间（秒）'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='调用时间'),
        sa.ForeignKeyConstraint(['tool_id'], ['openclaw_tools.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        comment='OpenClaw工具调用记录表'
    )
    op.create_index('ix_openclaw_tool_calls_id', 'openclaw_tool_calls', ['id'], unique=False)
    op.create_index('ix_openclaw_tool_calls_tool_id', 'openclaw_tool_calls', ['tool_id'], unique=False)
    op.create_index('ix_openclaw_tool_calls_agent_id', 'openclaw_tool_calls', ['agent_id'], unique=False)
    op.create_index('ix_openclaw_tool_calls_user_id', 'openclaw_tool_calls', ['user_id'], unique=False)
    op.create_index('ix_openclaw_tool_calls_status', 'openclaw_tool_calls', ['status'], unique=False)
    op.create_index('ix_openclaw_tool_calls_created_at', 'openclaw_tool_calls', ['created_at'], unique=False)


def downgrade() -> None:
    """降级数据库"""

    # 删除openclaw_tool_calls表
    op.drop_index('ix_openclaw_tool_calls_created_at', table_name='openclaw_tool_calls')
    op.drop_index('ix_openclaw_tool_calls_status', table_name='openclaw_tool_calls')
    op.drop_index('ix_openclaw_tool_calls_user_id', table_name='openclaw_tool_calls')
    op.drop_index('ix_openclaw_tool_calls_agent_id', table_name='openclaw_tool_calls')
    op.drop_index('ix_openclaw_tool_calls_tool_id', table_name='openclaw_tool_calls')
    op.drop_index('ix_openclaw_tool_calls_id', table_name='openclaw_tool_calls')
    op.drop_table('openclaw_tool_calls')

    # 删除openclaw_tools表
    op.drop_index('ix_openclaw_tools_status', table_name='openclaw_tools')
    op.drop_index('ix_openclaw_tools_name', table_name='openclaw_tools')
    op.drop_index('ix_openclaw_tools_id', table_name='openclaw_tools')
    op.drop_table('openclaw_tools')
