"""添加告警系统表

Revision ID: 002
Revises: 001
Create Date: 2024-08-06 10:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    """升级数据库"""
    # 创建告警规则表
    op.create_table('alert_rules_v2',
        sa.Column('id', sa.String(255), nullable=False, comment='规则ID'),
        sa.Column('name', sa.String(255), nullable=False, comment='规则名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='规则描述'),
        sa.Column('condition', sa.JSON(), nullable=False, comment='告警条件(JSON格式)'),
        sa.Column('severity', sa.String(50), nullable=False, comment='严重程度'),
        sa.Column('enabled', sa.Boolean(), nullable=True, default=True, comment='是否启用'),
        sa.Column('notification_channels', sa.JSON(), nullable=True, comment='通知渠道列表'),
        sa.Column('notification_config', sa.JSON(), nullable=True, comment='通知配置'),
        sa.Column('labels', sa.JSON(), nullable=True, comment='标签'),
        sa.Column('annotations', sa.JSON(), nullable=True, comment='注释'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建索引
    op.create_index('idx_alert_rule_v2_enabled', 'alert_rules_v2', ['enabled'])
    op.create_index('idx_alert_rule_v2_severity', 'alert_rules_v2', ['severity'])
    op.create_index('idx_alert_rule_v2_name', 'alert_rules_v2', ['name'])
    
    # 创建告警历史表
    op.create_table('alert_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('alert_id', sa.String(255), nullable=False, comment='告警实例ID'),
        sa.Column('rule_id', sa.String(255), nullable=False, comment='规则ID'),
        sa.Column('rule_name', sa.String(255), nullable=False, comment='规则名称'),
        sa.Column('severity', sa.String(50), nullable=False, comment='严重程度'),
        sa.Column('message', sa.Text(), nullable=False, comment='告警消息'),
        sa.Column('labels', sa.JSON(), nullable=True, comment='标签'),
        sa.Column('annotations', sa.JSON(), nullable=True, comment='注释'),
        sa.Column('starts_at', sa.DateTime(), nullable=False, comment='开始时间'),
        sa.Column('ends_at', sa.DateTime(), nullable=True, comment='结束时间'),
        sa.Column('status', sa.String(50), nullable=False, comment='状态'),
        sa.Column('notification_sent', sa.Boolean(), nullable=True, default=False, comment='是否已发送通知'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
        sa.ForeignKeyConstraint(['rule_id'], ['alert_rules_v2.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建索引
    op.create_index('idx_alert_history_rule_id', 'alert_history', ['rule_id'])
    op.create_index('idx_alert_history_severity', 'alert_history', ['severity'])
    op.create_index('idx_alert_history_status', 'alert_history', ['status'])
    op.create_index('idx_alert_history_starts_at', 'alert_history', ['starts_at'])
    op.create_index('idx_alert_history_alert_id', 'alert_history', ['alert_id'])


def downgrade():
    """降级数据库"""
    # 删除索引
    op.drop_index('idx_alert_history_alert_id', table_name='alert_history')
    op.drop_index('idx_alert_history_starts_at', table_name='alert_history')
    op.drop_index('idx_alert_history_status', table_name='alert_history')
    op.drop_index('idx_alert_history_severity', table_name='alert_history')
    op.drop_index('idx_alert_history_rule_id', table_name='alert_history')
    
    op.drop_index('idx_alert_rule_v2_name', table_name='alert_rules_v2')
    op.drop_index('idx_alert_rule_v2_severity', table_name='alert_rules_v2')
    op.drop_index('idx_alert_rule_v2_enabled', table_name='alert_rules_v2')
    
    # 删除表
    op.drop_table('alert_history')
    op.drop_table('alert_rules_v2')