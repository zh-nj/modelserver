"""
枚举类型定义
"""
from enum import Enum

class FrameworkType(str, Enum):
    """推理框架类型"""
    LLAMA_CPP = "llama_cpp"
    VLLM = "vllm"
    DOCKER = "docker"

class ModelStatus(str, Enum):
    """模型状态"""
    STOPPED = "stopped"          # 已停止
    STARTING = "starting"        # 启动中
    RUNNING = "running"          # 运行中
    ERROR = "error"              # 错误状态
    STOPPING = "stopping"       # 停止中
    PREEMPTED = "preempted"      # 被抢占

class GPUVendor(str, Enum):
    """GPU厂商"""
    NVIDIA = "nvidia"
    AMD = "amd"
    INTEL = "intel"
    UNKNOWN = "unknown"

class HealthStatus(str, Enum):
    """健康状态"""
    HEALTHY = "healthy"          # 健康
    UNHEALTHY = "unhealthy"      # 不健康
    UNKNOWN = "unknown"          # 未知

class AlertLevel(str, Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ScheduleResult(str, Enum):
    """调度结果"""
    SUCCESS = "success"          # 调度成功
    INSUFFICIENT_RESOURCES = "insufficient_resources"  # 资源不足
    PREEMPTION_REQUIRED = "preemption_required"       # 需要抢占
    FAILED = "failed"            # 调度失败

class MetricType(str, Enum):
    """指标类型"""
    GPU_UTILIZATION = "gpu_utilization"    # GPU利用率
    GPU_MEMORY = "gpu_memory"              # GPU内存
    GPU_TEMPERATURE = "gpu_temperature"    # GPU温度
    CPU_USAGE = "cpu_usage"                # CPU使用率
    MEMORY_USAGE = "memory_usage"          # 内存使用率
    RESPONSE_TIME = "response_time"        # 响应时间
    REQUEST_COUNT = "request_count"        # 请求数量
    ERROR_RATE = "error_rate"              # 错误率
    THROUGHPUT = "throughput"              # 吞吐量
    MODEL_HEALTH = "model_health"          # 模型健康状态

class ComparisonOperator(str, Enum):
    """比较操作符"""
    EQUALS = "equals"                      # 等于
    NOT_EQUALS = "not_equals"              # 不等于
    GREATER_THAN = "greater_than"          # 大于
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"  # 大于等于
    LESS_THAN = "less_than"                # 小于
    LESS_THAN_OR_EQUAL = "less_than_or_equal"        # 小于等于
    CONTAINS = "contains"                  # 包含
    NOT_CONTAINS = "not_contains"          # 不包含

class AlertSeverity(str, Enum):
    """告警严重程度"""
    LOW = "low"                           # 低
    MEDIUM = "medium"                     # 中
    HIGH = "high"                         # 高
    CRITICAL = "critical"                 # 严重

class AlertType(str, Enum):
    """告警类型"""
    THRESHOLD = "threshold"               # 阈值告警
    ANOMALY = "anomaly"                   # 异常告警
    TREND = "trend"                       # 趋势告警
    HEALTH = "health"                     # 健康检查告警

class PreemptionReason(str, Enum):
    """抢占原因"""
    HIGHER_PRIORITY = "higher_priority"   # 高优先级模型需要资源
    RESOURCE_SHORTAGE = "resource_shortage"  # 资源短缺
    MANUAL_PREEMPTION = "manual_preemption"  # 手动抢占

class RecoveryReason(str, Enum):
    """恢复原因"""
    RESOURCE_AVAILABLE = "resource_available"  # 资源可用
    PREEMPTION_ENDED = "preemption_ended"      # 抢占结束
    MANUAL_RECOVERY = "manual_recovery"        # 手动恢复

class ScheduleDecisionType(str, Enum):
    """调度决策类型"""
    SCHEDULE = "schedule"                 # 调度
    PREEMPT = "preempt"                   # 抢占
    QUEUE = "queue"                       # 排队
    REJECT = "reject"                     # 拒绝