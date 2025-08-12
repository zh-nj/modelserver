"""
SQLAlchemy数据库模型定义
用于配置持久化和系统状态管理
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, Float, DateTime, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Dict, Any

Base = declarative_base()

class ModelConfigDB(Base):
    """模型配置数据库模型"""
    __tablename__ = "model_configs"
    
    # 主键和基本信息
    id = Column(String(255), primary_key=True, comment="模型唯一标识")
    name = Column(String(255), nullable=False, comment="模型名称")
    framework = Column(String(50), nullable=False, comment="推理框架类型")
    model_path = Column(Text, nullable=False, comment="模型文件路径")
    priority = Column(Integer, nullable=False, default=5, comment="优先级(1-10)")
    
    # GPU和资源配置
    gpu_devices = Column(JSON, nullable=True, comment="指定GPU设备列表")
    additional_parameters = Column(Text, nullable=True, comment="附加启动参数")
    parameters = Column(JSON, nullable=True, comment="框架特定参数")
    
    # 资源需求
    gpu_memory = Column(Integer, nullable=False, default=0, comment="所需GPU内存(MB)")
    cpu_cores = Column(Integer, nullable=True, comment="所需CPU核心数")
    system_memory = Column(Integer, nullable=True, comment="所需系统内存(MB)")
    
    # 健康检查配置
    health_check_enabled = Column(Boolean, default=True, comment="是否启用健康检查")
    health_check_interval = Column(Integer, default=30, comment="健康检查间隔(秒)")
    health_check_timeout = Column(Integer, default=10, comment="健康检查超时(秒)")
    health_check_max_failures = Column(Integer, default=3, comment="最大失败次数")
    health_check_endpoint = Column(String(255), nullable=True, comment="健康检查端点")
    
    # 重试策略
    retry_enabled = Column(Boolean, default=True, comment="是否启用重试")
    retry_max_attempts = Column(Integer, default=3, comment="最大重试次数")
    retry_initial_delay = Column(Integer, default=5, comment="初始延迟(秒)")
    retry_max_delay = Column(Integer, default=300, comment="最大延迟(秒)")
    retry_backoff_factor = Column(Float, default=2.0, comment="退避因子")
    
    # 状态和时间戳
    is_active = Column(Boolean, default=True, comment="是否激活")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 索引 - 暂时移除以避免TiDB临时空间问题
    # __table_args__ = (
    #     Index('idx_model_priority', 'priority'),
    #     Index('idx_model_framework', 'framework'),
    #     Index('idx_model_active', 'is_active'),
    #     Index('idx_model_created', 'created_at'),
    # )

class SystemConfigDB(Base):
    """系统配置数据库模型"""
    __tablename__ = "system_configs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String(255), unique=True, nullable=False, comment="配置键")
    config_value = Column(JSON, nullable=True, comment="配置值")
    config_type = Column(String(50), nullable=False, comment="配置类型")
    description = Column(Text, nullable=True, comment="配置描述")
    is_encrypted = Column(Boolean, default=False, comment="是否加密存储")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 索引 - 暂时移除以避免TiDB临时空间问题
    # __table_args__ = (
    #     Index('idx_config_key', 'config_key'),
    #     Index('idx_config_type', 'config_type'),
    # )

class ConfigBackupDB(Base):
    """配置备份数据库模型"""
    __tablename__ = "config_backups"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    backup_name = Column(String(255), nullable=False, comment="备份名称")
    backup_type = Column(String(50), nullable=False, comment="备份类型")
    backup_data = Column(Text, nullable=False, comment="备份数据(JSON)")
    backup_size = Column(Integer, nullable=False, default=0, comment="备份大小(字节)")
    checksum = Column(String(64), nullable=True, comment="数据校验和")
    description = Column(Text, nullable=True, comment="备份描述")
    created_by = Column(String(255), nullable=True, comment="创建者")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    
    # 索引 - 暂时移除以避免TiDB临时空间问题
    # __table_args__ = (
    #     Index('idx_backup_name', 'backup_name'),
    #     Index('idx_backup_type', 'backup_type'),
    #     Index('idx_backup_created', 'created_at'),
    # )

class ConfigChangeLogDB(Base):
    """配置变更日志数据库模型"""
    __tablename__ = "config_change_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(String(255), nullable=True, comment="模型ID")
    change_type = Column(String(50), nullable=False, comment="变更类型")
    old_value = Column(JSON, nullable=True, comment="旧值")
    new_value = Column(JSON, nullable=True, comment="新值")
    changed_fields = Column(JSON, nullable=True, comment="变更字段列表")
    change_reason = Column(Text, nullable=True, comment="变更原因")
    changed_by = Column(String(255), nullable=True, comment="变更者")
    ip_address = Column(String(45), nullable=True, comment="IP地址")
    user_agent = Column(Text, nullable=True, comment="用户代理")
    created_at = Column(DateTime, default=func.now(), comment="变更时间")
    
    # 索引 - 暂时移除以避免TiDB临时空间问题
    # __table_args__ = (
    #     Index('idx_change_model_id', 'model_id'),
    #     Index('idx_change_type', 'change_type'),
    #     Index('idx_change_created', 'created_at'),
    # )

class ModelStatusDB(Base):
    """模型状态数据库模型"""
    __tablename__ = "model_status"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(String(255), nullable=False, comment="模型ID")
    status = Column(String(50), nullable=False, comment="模型状态")
    pid = Column(Integer, nullable=True, comment="进程ID")
    api_endpoint = Column(String(255), nullable=True, comment="API端点")
    gpu_devices = Column(JSON, nullable=True, comment="使用的GPU设备")
    memory_usage = Column(Integer, nullable=True, comment="内存使用量(MB)")
    start_time = Column(DateTime, nullable=True, comment="启动时间")
    last_health_check = Column(DateTime, nullable=True, comment="最后健康检查时间")
    health_status = Column(String(50), nullable=True, comment="健康状态")
    error_message = Column(Text, nullable=True, comment="错误信息")
    restart_count = Column(Integer, default=0, comment="重启次数")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 索引 - 暂时移除以避免TiDB临时空间问题
    # __table_args__ = (
    #     Index('idx_status_model_id', 'model_id'),
    #     Index('idx_status_status', 'status'),
    #     Index('idx_status_updated', 'updated_at'),
    # )

class GPUMetricsDB(Base):
    """GPU指标数据库模型"""
    __tablename__ = "gpu_metrics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, nullable=False, comment="GPU设备ID")
    timestamp = Column(DateTime, default=func.now(), comment="时间戳")
    utilization = Column(Float, nullable=False, comment="利用率(%)")
    memory_used = Column(Integer, nullable=False, comment="内存使用(MB)")
    memory_total = Column(Integer, nullable=False, comment="总内存(MB)")
    temperature = Column(Float, nullable=True, comment="温度(摄氏度)")
    power_usage = Column(Float, nullable=True, comment="功耗(瓦特)")
    fan_speed = Column(Float, nullable=True, comment="风扇转速(%)")
    
    # 索引 - 暂时移除以避免TiDB临时空间问题
    # __table_args__ = (
    #     Index('idx_gpu_device_time', 'device_id', 'timestamp'),
    #     Index('idx_gpu_timestamp', 'timestamp'),
    # )

class SystemMetricsDB(Base):
    """系统指标数据库模型"""
    __tablename__ = "system_metrics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=func.now(), comment="时间戳")
    cpu_usage = Column(Float, nullable=False, comment="CPU使用率(%)")
    memory_usage = Column(Float, nullable=False, comment="内存使用率(%)")
    memory_total = Column(Integer, nullable=False, comment="总内存(MB)")
    memory_used = Column(Integer, nullable=False, comment="已用内存(MB)")
    disk_usage = Column(Float, nullable=False, comment="磁盘使用率(%)")
    disk_total = Column(Integer, nullable=False, comment="总磁盘空间(GB)")
    disk_used = Column(Integer, nullable=False, comment="已用磁盘空间(GB)")
    network_sent = Column(Integer, default=0, comment="网络发送字节数")
    network_recv = Column(Integer, default=0, comment="网络接收字节数")
    load_average_1m = Column(Float, nullable=True, comment="1分钟负载")
    load_average_5m = Column(Float, nullable=True, comment="5分钟负载")
    load_average_15m = Column(Float, nullable=True, comment="15分钟负载")
    
    # 索引 - 暂时移除以避免TiDB临时空间问题
    # __table_args__ = (
    #     Index('idx_system_timestamp', 'timestamp'),
    # )

class AlertRuleDB(Base):
    """告警规则数据库模型"""
    __tablename__ = "alert_rules"
    
    id = Column(String(255), primary_key=True, comment="规则ID")
    name = Column(String(255), nullable=False, comment="规则名称")
    condition = Column(Text, nullable=False, comment="告警条件")
    threshold = Column(Float, nullable=False, comment="阈值")
    level = Column(String(50), nullable=False, comment="告警级别")
    enabled = Column(Boolean, default=True, comment="是否启用")
    notification_channels = Column(JSON, nullable=True, comment="通知渠道")
    description = Column(Text, nullable=True, comment="规则描述")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 索引 - 暂时移除以避免TiDB临时空间问题
    # __table_args__ = (
    #     Index('idx_alert_enabled', 'enabled'),
    #     Index('idx_alert_level', 'level'),
    # )

class AlertEventDB(Base):
    """告警事件数据库模型"""
    __tablename__ = "alert_events"
    
    id = Column(String(255), primary_key=True, comment="告警ID")
    rule_id = Column(String(255), nullable=False, comment="规则ID")
    level = Column(String(50), nullable=False, comment="告警级别")
    message = Column(Text, nullable=False, comment="告警消息")
    details = Column(JSON, nullable=True, comment="告警详情")
    resolved = Column(Boolean, default=False, comment="是否已解决")
    resolved_at = Column(DateTime, nullable=True, comment="解决时间")
    resolved_by = Column(String(255), nullable=True, comment="解决者")
    created_at = Column(DateTime, default=func.now(), comment="告警时间")
    
    # 索引 - 暂时移除以避免TiDB临时空间问题
    # __table_args__ = (
    #     Index('idx_event_rule_id', 'rule_id'),
    #     Index('idx_event_level', 'level'),
    #     Index('idx_event_resolved', 'resolved'),
    #     Index('idx_event_created', 'created_at'),
    # )

class AlertRule(Base):
    """新版告警规则数据库模型"""
    __tablename__ = "alert_rules_v2"
    
    id = Column(String(255), primary_key=True, comment="规则ID")
    name = Column(String(255), nullable=False, comment="规则名称")
    description = Column(Text, nullable=True, comment="规则描述")
    condition = Column(JSON, nullable=False, comment="告警条件(JSON格式)")
    severity = Column(String(50), nullable=False, comment="严重程度")
    enabled = Column(Boolean, default=True, comment="是否启用")
    notification_channels = Column(JSON, nullable=True, comment="通知渠道列表")
    notification_config = Column(JSON, nullable=True, comment="通知配置")
    labels = Column(JSON, nullable=True, comment="标签")
    annotations = Column(JSON, nullable=True, comment="注释")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 索引 - 暂时移除以避免TiDB临时空间问题
    # __table_args__ = (
    #     Index('idx_alert_rule_v2_enabled', 'enabled'),
    #     Index('idx_alert_rule_v2_severity', 'severity'),
    #     Index('idx_alert_rule_v2_name', 'name'),
    # )

class AlertHistory(Base):
    """告警历史数据库模型"""
    __tablename__ = "alert_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String(255), nullable=False, comment="告警实例ID")
    rule_id = Column(String(255), nullable=False, comment="规则ID")
    rule_name = Column(String(255), nullable=False, comment="规则名称")
    severity = Column(String(50), nullable=False, comment="严重程度")
    message = Column(Text, nullable=False, comment="告警消息")
    labels = Column(JSON, nullable=True, comment="标签")
    annotations = Column(JSON, nullable=True, comment="注释")
    starts_at = Column(DateTime, nullable=False, comment="开始时间")
    ends_at = Column(DateTime, nullable=True, comment="结束时间")
    status = Column(String(50), nullable=False, comment="状态")
    notification_sent = Column(Boolean, default=False, comment="是否已发送通知")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 索引 - 暂时移除以避免TiDB临时空间问题
    # __table_args__ = (
    #     Index('idx_alert_history_rule_id', 'rule_id'),
    #     Index('idx_alert_history_severity', 'severity'),
    #     Index('idx_alert_history_status', 'status'),
    #     Index('idx_alert_history_starts_at', 'starts_at'),
    #     Index('idx_alert_history_alert_id', 'alert_id'),
    # )