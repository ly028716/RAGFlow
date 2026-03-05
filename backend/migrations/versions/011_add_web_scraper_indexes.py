"""add web scraper indexes for performance

Revision ID: 011_add_web_scraper_indexes
Revises: 010_add_web_scraper_tables
Create Date: 2026-03-04 21:43:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '011_add_web_scraper_indexes'
down_revision = '010_add_web_scraper_tables'
branch_labels = None
depends_on = None


def upgrade():
    """添加Web Scraper性能优化索引"""

    # web_scraper_tasks表索引
    op.create_index(
        'idx_web_scraper_tasks_status',
        'web_scraper_tasks',
        ['status'],
        unique=False
    )

    op.create_index(
        'idx_web_scraper_tasks_created_by',
        'web_scraper_tasks',
        ['created_by'],
        unique=False
    )

    op.create_index(
        'idx_web_scraper_tasks_knowledge_base_id',
        'web_scraper_tasks',
        ['knowledge_base_id'],
        unique=False
    )

    op.create_index(
        'idx_web_scraper_tasks_schedule_type',
        'web_scraper_tasks',
        ['schedule_type'],
        unique=False
    )

    op.create_index(
        'idx_web_scraper_tasks_next_run_at',
        'web_scraper_tasks',
        ['next_run_at'],
        unique=False
    )

    # 复合索引：用于查询活跃的定时任务
    op.create_index(
        'idx_web_scraper_tasks_status_schedule',
        'web_scraper_tasks',
        ['status', 'schedule_type'],
        unique=False
    )

    # 复合索引：用于查询用户的特定状态任务
    op.create_index(
        'idx_web_scraper_tasks_user_status',
        'web_scraper_tasks',
        ['created_by', 'status'],
        unique=False
    )

    # web_scraper_logs表索引
    op.create_index(
        'idx_web_scraper_logs_task_id',
        'web_scraper_logs',
        ['task_id'],
        unique=False
    )

    op.create_index(
        'idx_web_scraper_logs_status',
        'web_scraper_logs',
        ['status'],
        unique=False
    )

    op.create_index(
        'idx_web_scraper_logs_start_time',
        'web_scraper_logs',
        ['start_time'],
        unique=False
    )

    # 复合索引：用于统计任务的日志
    op.create_index(
        'idx_web_scraper_logs_task_status',
        'web_scraper_logs',
        ['task_id', 'status'],
        unique=False
    )

    # 复合索引：用于按时间倒序查询任务日志
    op.create_index(
        'idx_web_scraper_logs_task_created',
        'web_scraper_logs',
        ['task_id', sa.text('created_at DESC')],
        unique=False
    )


def downgrade():
    """删除Web Scraper性能优化索引"""

    # 删除web_scraper_logs表索引
    op.drop_index('idx_web_scraper_logs_task_created', table_name='web_scraper_logs')
    op.drop_index('idx_web_scraper_logs_task_status', table_name='web_scraper_logs')
    op.drop_index('idx_web_scraper_logs_start_time', table_name='web_scraper_logs')
    op.drop_index('idx_web_scraper_logs_status', table_name='web_scraper_logs')
    op.drop_index('idx_web_scraper_logs_task_id', table_name='web_scraper_logs')

    # 删除web_scraper_tasks表索引
    op.drop_index('idx_web_scraper_tasks_user_status', table_name='web_scraper_tasks')
    op.drop_index('idx_web_scraper_tasks_status_schedule', table_name='web_scraper_tasks')
    op.drop_index('idx_web_scraper_tasks_next_run_at', table_name='web_scraper_tasks')
    op.drop_index('idx_web_scraper_tasks_schedule_type', table_name='web_scraper_tasks')
    op.drop_index('idx_web_scraper_tasks_knowledge_base_id', table_name='web_scraper_tasks')
    op.drop_index('idx_web_scraper_tasks_created_by', table_name='web_scraper_tasks')
    op.drop_index('idx_web_scraper_tasks_status', table_name='web_scraper_tasks')
