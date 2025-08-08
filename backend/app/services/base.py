"""
基础接口和抽象类定义
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from ..models.schemas import (
    ModelConfig, ModelInfo, ModelStatus, GPUInfo, ResourceRequirement,
    ResourceAllocation, SystemOverview, HealthStatus, ValidationResult,
    GPUMetrics, TimeRange, Metrics, ScheduleResult
)

class ModelManagerInterface(ABC):
    """模型管理器接口"""
    
    @abstractmethod
    async def create_model(self, config: ModelConfig) -> str:
        """创建模型配置"""
        pass
    
    @abstractmethod
    async def start_model(self, model_id: str) -> bool:
        """启动模型"""
        pass
    
    @abstractmethod
    async def stop_model(self, model_id: str) -> bool:
        """停止模型"""
        pass
    
    @abstractmethod
    async def restart_model(self, model_id: str) -> bool:
        """重启模型"""
        pass
    
    @abstractmethod
    async def get_model_status(self, model_id: str) -> ModelStatus:
        """获取模型状态"""
        pass
    
    @abstractmethod
    async def list_models(self) -> List[ModelInfo]:
        """列出所有模型"""
        pass
    
    @abstractmethod
    async def delete_model(self, model_id: str) -> bool:
        """删除模型"""
        pass

class ResourceSchedulerInterface(ABC):
    """资源调度器接口"""
    
    @abstractmethod
    async def schedule_model(self, model_id: str) -> ScheduleResult:
        """调度模型资源"""
        pass
    
    @abstractmethod
    async def get_gpu_info(self) -> List[GPUInfo]:
        """获取GPU信息"""
        pass
    
    @abstractmethod
    async def calculate_resource_requirements(self, config: ModelConfig) -> ResourceRequirement:
        """计算资源需求"""
        pass
    
    @abstractmethod
    async def find_available_resources(self, requirement: ResourceRequirement) -> Optional[ResourceAllocation]:
        """查找可用资源"""
        pass
    
    @abstractmethod
    async def preempt_lower_priority_models(self, required_memory: int, target_gpu: int) -> List[str]:
        """抢占低优先级模型"""
        pass

class MonitoringServiceInterface(ABC):
    """监控服务接口"""
    
    @abstractmethod
    async def collect_gpu_metrics(self) -> List[GPUMetrics]:
        """收集GPU指标"""
        pass
    
    @abstractmethod
    async def check_model_health(self, model_id: str) -> HealthStatus:
        """检查模型健康状态"""
        pass
    
    @abstractmethod
    async def get_system_overview(self) -> SystemOverview:
        """获取系统概览"""
        pass
    
    @abstractmethod
    async def get_performance_metrics(self, model_id: str, timerange: TimeRange) -> Metrics:
        """获取性能指标"""
        pass

class ConfigManagerInterface(ABC):
    """配置管理器接口"""
    
    @abstractmethod
    async def save_model_config(self, config: ModelConfig) -> bool:
        """保存模型配置"""
        pass
    
    @abstractmethod
    async def load_model_configs(self) -> List[ModelConfig]:
        """加载模型配置"""
        pass
    
    @abstractmethod
    async def validate_config(self, config: ModelConfig) -> ValidationResult:
        """验证配置"""
        pass
    
    @abstractmethod
    async def backup_configs(self) -> str:
        """备份配置"""
        pass
    
    @abstractmethod
    async def restore_configs(self, backup_path: str) -> bool:
        """恢复配置"""
        pass

