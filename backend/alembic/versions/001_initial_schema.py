"""初始数据库架构

修订ID: 001
修订时间: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# 修订标识符，由Alembic使用
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """升级数据库结构"""
    
    # 创建模型配置表
    op.create_table('model_configs',
        sa.Column('id', sa.String(255), nullable=False, comment='模型唯一标识'),
        sa.Column('name', sa.String(255), nullable=False, comment='模型名称'),
        sa.Column('framework', sa.String(50), nullable=False, comment='推理框架类型'),
        sa.Column('model_path', sa.Text(), nullable=False, comment='模型文件路径'),
        sa.Column('priority', sa.Integer(), nullable=False, default=5, comment='优先级(1-10)'),
        sa.Column('gpu_devices', sa.JSON(), nullable=True, comment='指定GPU设备列表'),
        sa.Column('parameters', sa.JSON(), nullable=True, comment='框架特定参数'),
        sa.Column('gpu_memory', sa.Integer(), nullable=False, default=0, comment='所需GPU内存(MB)'),
        sa.Column('cpu_cores', sa.Integer(), nullable=True, comment='所需CPU核心数'),
        sa.Column('system_memory', sa.Integer(), nullable=True, comment='所需系统内存(MB)'),
        sa.Column('health_check_enabled', sa.Boolean(), default=True, comment='是否启用健康检查'),
        sa.Column('health_check_interval', sa.Integer(), default=30, comment='健康检查间隔(秒)'),
        sa.Column('health_check_timeout', sa.Integer(), default=10, comment='健康检查超时(秒)'),
        sa.Column('health_check_max_failures', sa.Integer(), default=3, comment='最大失败次数'),
        sa.Column('health_check_endpoint', sa.String(255), nullable=True, comment='健康检查端点'),
        sa.Column('retry_enabled', sa.Boolean(), default=True, comment='是否启用重试'),
        sa.Column('retry_max_attempts', sa.Integer(), default=3, comment='最大重试次数'),
        sa.Column('retry_initial_delay', sa.Integer(), default=5, comment='初始延迟(秒)'),
        sa.Column('retry_max_delay', sa.Integer(), default=300, comment='最大延迟(秒)'),
        sa.Column('retry_backoff_factor', sa.Float(), default=2.0, comment='退避因子'),
        sa.Column('is_active', sa.Boolean(), default=True, comment='是否激活'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    
    # 创建索引
    op.create_index('idx_model_priority', 'model_configs', ['priority'])
    op.create_index('idx_model_framework', 'model_configs', ['framework'])
    op.create_index('idx_model_active', 'model_configs', ['is_active'])
    op.create_index('idx_model_created', 'model_configs', ['created_at'])
    
    # 创建系统配置表
    op.create_table('system_configs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('config_key', sa.String(255), nullable=False, comment='配置键'),
        sa.Column('config_value', sa.JSON(), nullable=True, comment='配置值'),
        sa.Column('config_type', sa.String(50), nullable=False, comment='配置类型'),
        sa.Column('description', sa.Text(), nullable=True, comment='配置描述'),
        sa.Column('is_encrypted', sa.Boolean(), default=False, comment='是否加密存储'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('config_key'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    
    # 创建索引
    op.create_index('idx_config_key', 'system_configs', ['config_key'])
    op.create_index('idx_config_type', 'system_configs', ['config_type'])
    
    # 创建配置备份表
    op.create_table('config_backups',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('backup_name', sa.String(255), nullable=False, comment='备份名称'),
        sa.Column('backup_type', sa.String(50), nullable=False, comment='备份类型'),
        sa.Column('backup_data', sa.Text(), nullable=False, comment='备份数据(JSON)'),
        sa.Column('backup_size', sa.Integer(), nullable=False, default=0, comment='备份大小(字节)'),
        sa.Column('checksum', sa.String(64), nullable=True, comment='数据校验和'),
        sa.Column('description', sa.Text(), nullable=True, comment='备份描述'),
        sa.Column('created_by', sa.String(255), nullable=True, comment='创建者'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    
    # 创建索引
    op.create_index('idx_backup_name', 'config_backups', ['backup_name'])
    op.create_index('idx_backup_type', 'config_backups', ['backup_type'])
    op.create_index('idx_backup_created', 'config_backups', ['created_at'])
    
    # 创建配置变更日志表
    op.create_table('config_change_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('model_id', sa.String(255), nullable=True, comment='模型ID'),
        sa.Column('change_type', sa.String(50), nullable=False, comment='变更类型'),
        sa.Column('old_value', sa.JSON(), nullable=True, comment='旧值'),
        sa.Column('new_value', sa.JSON(), nullable=True, comment='新值'),
        sa.Column('changed_fields', sa.JSON(), nullable=True, comment='变更字段列表'),
        sa.Column('change_reason', sa.Text(), nullable=True, comment='变更原因'),
        sa.Column('changed_by', sa.String(255), nullable=True, comment='变更者'),
        sa.Column('ip_address', sa.String(45), nullable=True, comment='IP地址'),
        sa.Column('user_agent', sa.Text(), nullable=True, comment='用户代理'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='变更时间'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    
    # 创建索引
    op.create_index('idx_change_model_id', 'config_change_logs', ['model_id'])
    op.create_index('idx_change_type', 'config_change_logs', ['change_type'])
    op.create_index('idx_change_created', 'config_change_logs', ['created_at'])
    
    # 创建模型状态表
    op.create_table('model_status',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('model_id', sa.String(255), nullable=False, comment='模型ID'),
        sa.Column('status', sa.String(50), nullable=False, comment='模型状态'),
        sa.Column('pid', sa.Integer(), nullable=True, comment='进程ID'),
        sa.Column('api_endpoint', sa.String(255), nullable=True, comment='API端点'),
        sa.Column('gpu_devices', sa.JSON(), nullable=True, comment='使用的GPU设备'),
        sa.Column('memory_usage', sa.Integer(), nullable=True, comment='内存使用量(MB)'),
        sa.Column('start_time', sa.DateTime(), nullable=True, comment='启动时间'),
        sa.Column('last_health_check', sa.DateTime(), nullable=True, comment='最后健康检查时间'),
        sa.Column('health_status', sa.String(50), nullable=True, comment='健康状态'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='错误信息'),
        sa.Column('restart_count', sa.Integer(), default=0, comment='重启次数'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['model_id'], ['model_configs.id']),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    
    # 创建索引
    op.create_index('idx_status_model_id', 'model_status', ['model_id'])
    op.create_index('idx_status_status', 'model_status', ['status'])
    op.create_index('idx_status_updated', 'model_status', ['updated_at'])
    
    # 创建GPU指标表
    op.create_table('gpu_metrics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('device_id', sa.Integer(), nullable=False, comment='GPU设备ID'),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='时间戳'),
        sa.Column('utilization', sa.Float(), nullable=False, comment='利用率(%)'),
        sa.Column('memory_used', sa.Integer(), nullable=False, comment='内存使用(MB)'),
        sa.Column('memory_total', sa.Integer(), nullable=False, comment='总内存(MB)'),
        sa.Column('temperature', sa.Float(), nullable=True, comment='温度(摄氏度)'),
        sa.Column('power_usage', sa.Float(), nullable=True, comment='功耗(瓦特)'),
        sa.Column('fan_speed', sa.Float(), nullable=True, comment='风扇转速(%)'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    
    # 创建索引
    op.create_index('idx_gpu_device_time', 'gpu_metrics', ['device_id', 'timestamp'])
    op.create_index('idx_gpu_timestamp', 'gpu_metrics', ['timestamp'])
    
    # 创建系统指标表
    op.create_table('system_metrics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='时间戳'),
        sa.Column('cpu_usage', sa.Float(), nullable=False, comment='CPU使用率(%)'),
        sa.Column('memory_usage', sa.Float(), nullable=False, comment='内存使用率(%)'),
        sa.Column('memory_total', sa.Integer(), nullable=False, comment='总内存(MB)'),
        sa.Column('memory_used', sa.Integer(), nullable=False, comment='已用内存(MB)'),
        sa.Column('disk_usage', sa.Float(), nullable=False, comment='磁盘使用率(%)'),
        sa.Column('disk_total', sa.Integer(), nullable=False, comment='总磁盘空间(GB)'),
        sa.Column('disk_used', sa.Integer(), nullable=False, comment='已用磁盘空间(GB)'),
        sa.Column('network_sent', sa.Integer(), default=0, comment='网络发送字节数'),
        sa.Column('network_recv', sa.Integer(), default=0, comment='网络接收字节数'),
        sa.Column('load_average_1m', sa.Float(), nullable=True, comment='1分钟负载'),
        sa.Column('load_average_5m', sa.Float(), nullable=True, comment='5分钟负载'),
        sa.Column('load_average_15m', sa.Float(), nullable=True, comment='15分钟负载'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    
    # 创建索引
    op.create_index('idx_system_timestamp', 'system_metrics', ['timestamp'])
    
    # 创建告警规则表
    op.create_table('alert_rules',
        sa.Column('id', sa.String(255), nullable=False, comment='规则ID'),
        sa.Column('name', sa.String(255), nullable=False, comment='规则名称'),
        sa.Column('condition', sa.Text(), nullable=False, comment='告警条件'),
        sa.Column('threshold', sa.Float(), nullable=False, comment='阈值'),
        sa.Column('level', sa.String(50), nullable=False, comment='告警级别'),
        sa.Column('enabled', sa.Boolean(), default=True, comment='是否启用'),
        sa.Column('notification_channels', sa.JSON(), nullable=True, comment='通知渠道'),
        sa.Column('description', sa.Text(), nullable=True, comment='规则描述'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    
    # 创建索引
    op.create_index('idx_alert_enabled', 'alert_rules', ['enabled'])
    op.create_index('idx_alert_level', 'alert_rules', ['level'])
    
    # 创建告警事件表
    op.create_table('alert_events',
        sa.Column('id', sa.String(255), nullable=False, comment='告警ID'),
        sa.Column('rule_id', sa.String(255), nullable=False, comment='规则ID'),
        sa.Column('level', sa.String(50), nullable=False, comment='告警级别'),
        sa.Column('message', sa.Text(), nullable=False, comment='告警消息'),
        sa.Column('details', sa.JSON(), nullable=True, comment='告警详情'),
        sa.Column('resolved', sa.Boolean(), default=False, comment='是否已解决'),
        sa.Column('resolved_at', sa.DateTime(), nullable=True, comment='解决时间'),
        sa.Column('resolved_by', sa.String(255), nullable=True, comment='解决者'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='告警时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['rule_id'], ['alert_rules.id']),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    
    # 创建索引
    op.create_index('idx_event_rule_id', 'alert_events', ['rule_id'])
    op.create_index('idx_event_level', 'alert_events', ['level'])
    op.create_index('idx_event_resolved', 'alert_events', ['resolved'])
    op.create_index('idx_event_created', 'alert_events', ['created_at'])


def downgrade() -> None:
    """降级数据库结构"""
    
    # 删除表（按依赖关系逆序）
    op.drop_table('alert_events')
    op.drop_table('alert_rules')
    op.drop_table('system_metrics')
    op.drop_table('gpu_metrics')
    op.drop_table('model_status')
    op.drop_table('config_change_logs')
    op.drop_table('config_backups')
    op.drop_table('system_configs')
    op.drop_table('model_configs')