"""添加网页采集任务表

创建网页采集任务配置表和执行日志表，用于支持浏览器自动化采集功能。

Revision ID: 010_web_scraper
Revises: 009_openclaw_tools
Create Date: 2026-03-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '010_web_scraper'
down_revision: Union[str, None] = '009_openclaw_tools'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级数据库"""

    # 创建web_scraper_tasks表
    op.create_table(
        'web_scraper_tasks',
        sa.Column('id', sa.Integer(), nullable=False, comment='任务ID'),
        sa.Column('name', sa.String(200), nullable=False, comment='任务名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='任务描述'),
        sa.Column('url', sa.String(500), nullable=False, comment='目标URL'),
        sa.Column('url_pattern', sa.String(500), nullable=True, comment='URL匹配模式（支持通配符）'),
        sa.Column('knowledge_base_id', sa.Integer(), nullable=False, comment='目标知识库ID'),
        sa.Column('schedule_type', sa.Enum('once', 'cron', name='schedule_type_enum'),
                  nullable=False, server_default='once', comment='调度类型：once-一次性，cron-定时'),
        sa.Column('cron_expression', sa.String(100), nullable=True, comment='Cron表达式'),
        sa.Column('selector_config', sa.JSON(), nullable=True, comment='选择器配置（JSON格式）'),
        sa.Column('scraper_config', sa.JSON(), nullable=True, comment='采集器配置（JSON格式）'),
        sa.Column('status', sa.Enum('active', 'paused', 'stopped', name='task_status_enum'),
                  nullable=False, server_default='active', comment='任务状态'),
        sa.Column('last_run_at', sa.DateTime(), nullable=True, comment='最后执行时间'),
        sa.Column('next_run_at', sa.DateTime(), nullable=True, comment='下次执行时间'),
        sa.Column('created_by', sa.Integer(), nullable=False, comment='创建者用户ID'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'),
                  comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
                  comment='更新时间'),
        sa.ForeignKeyConstraint(['knowledge_base_id'], ['knowledge_bases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        comment='网页采集任务表'
    )

    # 创建索引
    op.create_index('ix_web_scraper_tasks_id', 'web_scraper_tasks', ['id'], unique=False)
    op.create_index('ix_web_scraper_tasks_status', 'web_scraper_tasks', ['status'], unique=False)
    op.create_index('ix_web_scraper_tasks_next_run', 'web_scraper_tasks', ['next_run_at'], unique=False)
    op.create_index('ix_web_scraper_tasks_knowledge_base', 'web_scraper_tasks', ['knowledge_base_id'], unique=False)
    op.create_index('ix_web_scraper_tasks_created_by', 'web_scraper_tasks', ['created_by'], unique=False)
    op.create_index('ix_web_scraper_tasks_created_at', 'web_scraper_tasks', ['created_at'], unique=False)

    # 创建web_scraper_logs表
    op.create_table(
        'web_scraper_logs',
        sa.Column('id', sa.Integer(), nullable=False, comment='日志ID'),
        sa.Column('task_id', sa.Integer(), nullable=False, comment='任务ID'),
        sa.Column('status', sa.Enum('running', 'success', 'failed', name='log_status_enum'),
                  nullable=False, server_default='running', comment='执行状态'),
        sa.Column('start_time', sa.DateTime(), nullable=False, comment='开始时间'),
        sa.Column('end_time', sa.DateTime(), nullable=True, comment='结束时间'),
        sa.Column('pages_scraped', sa.Integer(), nullable=False, server_default='0', comment='抓取页面数'),
        sa.Column('documents_created', sa.Integer(), nullable=False, server_default='0', comment='创建文档数'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='错误信息'),
        sa.Column('execution_details', sa.JSON(), nullable=True, comment='执行详情（JSON格式）'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'),
                  comment='创建时间'),
        sa.ForeignKeyConstraint(['task_id'], ['web_scraper_tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        comment='网页采集执行日志表'
    )

    # 创建索引
    op.create_index('ix_web_scraper_logs_id', 'web_scraper_logs', ['id'], unique=False)
    op.create_index('ix_web_scraper_logs_task_id', 'web_scraper_logs', ['task_id'], unique=False)
    op.create_index('ix_web_scraper_logs_status', 'web_scraper_logs', ['status'], unique=False)
    op.create_index('ix_web_scraper_logs_start_time', 'web_scraper_logs', ['start_time'], unique=False)
    op.create_index('ix_web_scraper_logs_created_at', 'web_scraper_logs', ['created_at'], unique=False)


def downgrade() -> None:
    """降级数据库"""

    # 直接删除表，MySQL会自动删除所有索引和约束
    # 注意：必须先删除有外键依赖的表（web_scraper_logs），再删除被依赖的表（web_scraper_tasks）
    op.drop_table('web_scraper_logs')
    op.drop_table('web_scraper_tasks')
