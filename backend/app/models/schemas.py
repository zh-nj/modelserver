"""
Pydantic数据模式定义
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from .enums import (
    FrameworkType, ModelStatus, GPUVendor, HealthStatus, AlertLevel, 
    ScheduleResult, ComparisonOperator, PreemptionReason, RecoveryReason, 
    ScheduleDecisionType
)

class GPUInfo(BaseModel):
    """GPU设备信息"""
    device_id: int = Field(..., description="GPU设备ID")
    name: str = Field(..., description="GPU设备名称")
    vendor: GPUVendor = Field(..., description="GPU厂商")
    memory_total: int = Field(..., description="总内存大小(MB)")
    memory_used: int = Field(..., description="已使用内存(MB)")
    memory_free: int = Field(..., description="可用内存(MB)")
    utilization: float = Field(..., ge=0, le=100, description="GPU利用率(%)")
    temperature: float = Field(..., description="GPU温度(摄氏度)")
    power_usage: float = Field(..., description="功耗(瓦特)")
    driver_version: Optional[str] = Field(None, description="驱动版本")

class ResourceRequirement(BaseModel):
    """资源需求"""
    gpu_memory: int = Field(..., description="所需GPU内存(MB)")
    gpu_devices: List[int] = Field(default_factory=list, description="指定GPU设备ID列表")
    cpu_cores: Optional[int] = Field(None, description="所需CPU核心数")
    system_memory: Optional[int] = Field(None, description="所需系统内存(MB)")

class HealthCheckConfig(BaseModel):
    """健康检查配置"""
    enabled: bool = Field(True, description="是否启用健康检查")
    interval: int = Field(30, description="检查间隔(秒)")
    timeout: int = Field(10, description="检查超时(秒)")
    max_failures: int = Field(3, description="最大失败次数")
    endpoint: Optional[str] = Field(None, description="健康检查端点")

class RetryPolicy(BaseModel):
    """重试策略"""
    enabled: bool = Field(True, description="是否启用重试")
    max_attempts: int = Field(3, description="最大重试次数")
    initial_delay: int = Field(5, description="初始延迟(秒)")
    max_delay: int = Field(300, description="最大延迟(秒)")
    backoff_factor: float = Field(2.0, description="退避因子")

class ModelConfig(BaseModel):
    """模型配置"""
    id: str = Field(..., description="模型唯一标识")
    name: str = Field(..., description="模型名称")
    framework: FrameworkType = Field(..., description="推理框架类型")
    model_path: str = Field(..., description="模型文件路径")
    priority: int = Field(..., ge=1, le=10, description="优先级(1-10，10最高)")
    gpu_devices: List[int] = Field(default_factory=list, description="指定GPU设备")
    additional_parameters: Optional[str] = Field(None, description="附加启动参数")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="框架特定参数")
    resource_requirements: ResourceRequirement = Field(..., description="资源需求")
    health_check: HealthCheckConfig = Field(default_factory=HealthCheckConfig, description="健康检查配置")
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy, description="重试策略")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

class ModelInfo(BaseModel):
    """模型信息"""
    id: str = Field(..., description="模型ID")
    name: str = Field(..., description="模型名称")
    framework: FrameworkType = Field(..., description="推理框架")
    model_path: str = Field(..., description="模型文件路径")
    status: ModelStatus = Field(..., description="模型状态")
    priority: int = Field(..., description="优先级")
    gpu_devices: List[int] = Field(..., description="使用的GPU设备")
    memory_usage: Optional[int] = Field(None, description="内存使用量(MB)")
    api_endpoint: Optional[str] = Field(None, description="API端点")
    uptime: Optional[int] = Field(None, description="运行时间(秒)")
    last_health_check: Optional[datetime] = Field(None, description="最后健康检查时间")

class ResourceAllocation(BaseModel):
    """资源分配"""
    gpu_devices: List[int] = Field(..., description="分配的GPU设备")
    memory_allocated: int = Field(..., description="分配的内存(MB)")
    allocation_time: datetime = Field(..., description="分配时间")

class SystemOverview(BaseModel):
    """系统概览"""
    total_models: int = Field(..., description="模型总数")
    running_models: int = Field(..., description="运行中模型数")
    total_gpus: int = Field(..., description="GPU总数")
    available_gpus: int = Field(..., description="可用GPU数")
    total_gpu_memory: int = Field(..., description="GPU总内存(MB)")
    used_gpu_memory: int = Field(..., description="已用GPU内存(MB)")
    system_uptime: int = Field(..., description="系统运行时间(秒)")
    last_updated: datetime = Field(..., description="最后更新时间")

class GPUMetrics(BaseModel):
    """GPU指标"""
    device_id: int = Field(..., description="GPU设备ID")
    timestamp: datetime = Field(..., description="时间戳")
    utilization: float = Field(..., description="利用率(%)")
    memory_used: int = Field(..., description="内存使用(MB)")
    memory_total: int = Field(..., description="总内存(MB)")
    temperature: float = Field(..., description="温度(摄氏度)")
    power_usage: float = Field(..., description="功耗(瓦特)")

class AlertRule(BaseModel):
    """告警规则"""
    id: str = Field(..., description="规则ID")
    name: str = Field(..., description="规则名称")
    condition: str = Field(..., description="告警条件")
    threshold: float = Field(..., description="阈值")
    level: AlertLevel = Field(..., description="告警级别")
    enabled: bool = Field(True, description="是否启用")
    notification_channels: List[str] = Field(default_factory=list, description="通知渠道")

class ValidationResult(BaseModel):
    """验证结果"""
    is_valid: bool = Field(..., description="是否有效")
    errors: List[str] = Field(default_factory=list, description="错误信息列表")
    warnings: List[str] = Field(default_factory=list, description="警告信息列表")

class TimeRange(BaseModel):
    """时间范围"""
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime = Field(..., description="结束时间")

class Metrics(BaseModel):
    """性能指标"""
    model_id: str = Field(..., description="模型ID")
    time_range: TimeRange = Field(..., description="时间范围")
    request_count: int = Field(..., description="请求数量")
    average_response_time: float = Field(..., description="平均响应时间(毫秒)")
    error_rate: float = Field(..., description="错误率(%)")
    throughput: float = Field(..., description="吞吐量(请求/秒)")
    gpu_utilization: List[float] = Field(..., description="GPU利用率历史数据")

class ModelPerformanceMetrics(BaseModel):
    """模型性能指标"""
    model_id: str = Field(..., description="模型ID")
    timestamp: datetime = Field(..., description="时间戳")
    request_count: int = Field(0, description="请求数量")
    total_response_time: float = Field(0.0, description="总响应时间(毫秒)")
    error_count: int = Field(0, description="错误数量")
    active_connections: int = Field(0, description="活跃连接数")
    memory_usage: int = Field(0, description="内存使用量(MB)")
    cpu_usage: float = Field(0.0, description="CPU使用率(%)")
    gpu_utilization: float = Field(0.0, description="GPU利用率(%)")

class SystemResourceMetrics(BaseModel):
    """系统资源指标"""
    timestamp: datetime = Field(..., description="时间戳")
    cpu_usage: float = Field(0.0, description="CPU使用率(%)")
    memory_usage: float = Field(0.0, description="内存使用率(%)")
    memory_total: int = Field(0, description="总内存(MB)")
    memory_used: int = Field(0, description="已用内存(MB)")
    disk_usage: float = Field(0.0, description="磁盘使用率(%)")
    disk_total: int = Field(0, description="总磁盘空间(GB)")
    disk_used: int = Field(0, description="已用磁盘空间(GB)")
    network_sent: int = Field(0, description="网络发送字节数")
    network_recv: int = Field(0, description="网络接收字节数")
    load_average: List[float] = Field(default_factory=list, description="系统负载(1,5,15分钟)")

class AlertEvent(BaseModel):
    """告警事件"""
    id: str = Field(..., description="告警ID")
    rule_id: str = Field(..., description="规则ID")
    level: AlertLevel = Field(..., description="告警级别")
    message: str = Field(..., description="告警消息")
    timestamp: datetime = Field(..., description="告警时间")
    resolved: bool = Field(False, description="是否已解决")
    resolved_at: Optional[datetime] = Field(None, description="解决时间")

class AlertCondition(BaseModel):
    """告警条件"""
    operator: ComparisonOperator = Field(..., description="比较操作符")
    threshold: Any = Field(..., description="阈值")
    duration: Optional[int] = Field(None, description="持续时间(秒)")

# 新版告警系统模式
class AlertConditionSchema(BaseModel):
    """告警条件模式"""
    metric: str = Field(..., description="监控指标名称")
    operator: str = Field(..., description="比较操作符")
    threshold: float = Field(..., description="阈值")
    duration: int = Field(..., description="持续时间(秒)")

class NotificationConfig(BaseModel):
    """通知配置模式"""
    email: Optional[Dict[str, Any]] = Field(None, description="邮件通知配置")
    webhook: Optional[Dict[str, Any]] = Field(None, description="Webhook通知配置")
    slack: Optional[Dict[str, Any]] = Field(None, description="Slack通知配置")
    dingtalk: Optional[Dict[str, Any]] = Field(None, description="钉钉通知配置")

class AlertRuleCreate(BaseModel):
    """创建告警规则请求"""
    name: str = Field(..., description="规则名称")
    description: Optional[str] = Field(None, description="规则描述")
    condition: AlertConditionSchema = Field(..., description="告警条件")
    severity: str = Field(..., description="严重程度")
    enabled: bool = Field(True, description="是否启用")
    notification_channels: List[str] = Field(default_factory=list, description="通知渠道")
    notification_config: NotificationConfig = Field(default_factory=NotificationConfig, description="通知配置")
    labels: Optional[Dict[str, str]] = Field(None, description="标签")
    annotations: Optional[Dict[str, str]] = Field(None, description="注释")

class AlertRuleUpdate(BaseModel):
    """更新告警规则请求"""
    name: Optional[str] = Field(None, description="规则名称")
    description: Optional[str] = Field(None, description="规则描述")
    condition: Optional[AlertConditionSchema] = Field(None, description="告警条件")
    severity: Optional[str] = Field(None, description="严重程度")
    enabled: Optional[bool] = Field(None, description="是否启用")
    notification_channels: Optional[List[str]] = Field(None, description="通知渠道")
    notification_config: Optional[NotificationConfig] = Field(None, description="通知配置")
    labels: Optional[Dict[str, str]] = Field(None, description="标签")
    annotations: Optional[Dict[str, str]] = Field(None, description="注释")

class AlertRuleResponse(BaseModel):
    """告警规则响应"""
    id: str = Field(..., description="规则ID")
    name: str = Field(..., description="规则名称")
    description: Optional[str] = Field(None, description="规则描述")
    condition: AlertConditionSchema = Field(..., description="告警条件")
    severity: str = Field(..., description="严重程度")
    enabled: bool = Field(..., description="是否启用")
    notification_channels: List[str] = Field(..., description="通知渠道")
    notification_config: NotificationConfig = Field(..., description="通知配置")
    labels: Dict[str, str] = Field(..., description="标签")
    annotations: Dict[str, str] = Field(..., description="注释")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

class AlertResponse(BaseModel):
    """告警响应"""
    id: str = Field(..., description="告警ID")
    rule_id: str = Field(..., description="规则ID")
    rule_name: str = Field(..., description="规则名称")
    severity: str = Field(..., description="严重程度")
    message: str = Field(..., description="告警消息")
    labels: Dict[str, str] = Field(..., description="标签")
    annotations: Dict[str, str] = Field(..., description="注释")
    starts_at: datetime = Field(..., description="开始时间")
    ends_at: Optional[datetime] = Field(None, description="结束时间")
    status: str = Field(..., description="状态")

class AlertHistoryResponse(BaseModel):
    """告警历史响应"""
    id: int = Field(..., description="历史记录ID")
    alert_id: str = Field(..., description="告警实例ID")
    rule_id: str = Field(..., description="规则ID")
    rule_name: str = Field(..., description="规则名称")
    severity: str = Field(..., description="严重程度")
    message: str = Field(..., description="告警消息")
    labels: Dict[str, str] = Field(..., description="标签")
    annotations: Dict[str, str] = Field(..., description="注释")
    starts_at: datetime = Field(..., description="开始时间")
    ends_at: Optional[datetime] = Field(None, description="结束时间")
    status: str = Field(..., description="状态")
    notification_sent: bool = Field(..., description="是否已发送通知")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

class AlertSummary(BaseModel):
    """告警摘要"""
    total_alerts: int = Field(..., description="总告警数")
    active_alerts: int = Field(..., description="活跃告警数")
    resolved_alerts: int = Field(..., description="已解决告警数")
    suppressed_alerts: int = Field(..., description="已抑制告警数")
    critical_alerts: int = Field(..., description="严重告警数")
    high_alerts: int = Field(..., description="高级告警数")
    medium_alerts: int = Field(..., description="中级告警数")
    low_alerts: int = Field(..., description="低级告警数")
    last_updated: datetime = Field(..., description="最后更新时间")

# 调度相关类
class ScheduleDecision(BaseModel):
    """调度决策"""
    model_id: str = Field(..., description="模型ID")
    decision_time: datetime = Field(..., description="决策时间")
    result: ScheduleResult = Field(..., description="调度结果")
    gpu_devices: List[int] = Field(default_factory=list, description="分配的GPU设备")
    preempted_models: List[str] = Field(default_factory=list, description="被抢占的模型")
    reason: Optional[str] = Field(None, description="决策原因")

class RecoveryAttempt(BaseModel):
    """恢复尝试"""
    model_id: str = Field(..., description="模型ID")
    attempt_time: datetime = Field(..., description="尝试时间")
    reason: RecoveryReason = Field(..., description="恢复原因")
    success: bool = Field(..., description="是否成功")
    attempt_number: Optional[int] = Field(None, description="尝试次数")
    error_message: Optional[str] = Field(None, description="错误信息")

class PreemptionStats(BaseModel):
    """抢占统计"""
    total_preemptions: int = Field(0, description="总抢占次数")
    successful_preemptions: int = Field(0, description="成功抢占次数")
    failed_preemptions: int = Field(0, description="失败抢占次数")
    average_preemption_time: float = Field(0.0, description="平均抢占时间(秒)")
    last_preemption_time: Optional[datetime] = Field(None, description="最后抢占时间")

class RecoveryStats(BaseModel):
    """恢复统计"""
    total_recoveries: int = Field(0, description="总恢复次数")
    successful_recoveries: int = Field(0, description="成功恢复次数")
    failed_recoveries: int = Field(0, description="失败恢复次数")
    average_recovery_time: float = Field(0.0, description="平均恢复时间(秒)")
    last_recovery_time: Optional[datetime] = Field(None, description="最后恢复时间")