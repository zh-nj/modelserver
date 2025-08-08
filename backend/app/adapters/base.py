"""
抽象适配器基类和工厂模式实现
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import asyncio
import logging
from ..models.schemas import ModelConfig, ModelStatus, HealthStatus, ValidationResult
from ..models.enums import FrameworkType

logger = logging.getLogger(__name__)

class FrameworkAdapterInterface(ABC):
    """框架适配器接口"""
    
    @abstractmethod
    async def start_model(self, config: ModelConfig) -> bool:
        """启动模型实例"""
        pass
    
    @abstractmethod
    async def stop_model(self, model_id: str) -> bool:
        """停止模型实例"""
        pass
    
    @abstractmethod
    async def get_model_status(self, model_id: str) -> ModelStatus:
        """获取模型状态"""
        pass
    
    @abstractmethod
    async def check_health(self, model_id: str) -> HealthStatus:
        """检查模型健康状态"""
        pass
    
    @abstractmethod
    async def get_api_endpoint(self, model_id: str) -> Optional[str]:
        """获取模型API端点"""
        pass
    
    @abstractmethod
    def validate_config(self, config: ModelConfig) -> ValidationResult:
        """验证配置参数"""
        pass

class BaseFrameworkAdapter(FrameworkAdapterInterface, ABC):
    """框架适配器基类"""
    
    def __init__(self, framework_type: FrameworkType):
        self.framework_type = framework_type
        self._running_models: Dict[str, Dict[str, Any]] = {}
        self._health_check_tasks: Dict[str, asyncio.Task] = {}
    
    def _get_model_info(self, model_id: str) -> Dict[str, Any]:
        """获取模型运行信息"""
        return self._running_models.get(model_id, {})
    
    def _set_model_info(self, model_id: str, info: Dict[str, Any]):
        """设置模型运行信息"""
        self._running_models[model_id] = info
    
    def _remove_model_info(self, model_id: str):
        """移除模型运行信息"""
        self._running_models.pop(model_id, None)
        # 取消健康检查任务
        if model_id in self._health_check_tasks:
            self._health_check_tasks[model_id].cancel()
            del self._health_check_tasks[model_id]
    
    def _validate_common_config(self, config: ModelConfig) -> ValidationResult:
        """验证通用配置参数"""
        errors = []
        warnings = []
        
        # 检查基本参数
        if not config.id:
            errors.append("模型ID不能为空")
        
        if not config.name:
            errors.append("模型名称不能为空")
        
        if not config.model_path:
            errors.append("模型路径不能为空")
        
        if config.priority < 1 or config.priority > 10:
            errors.append("优先级必须在1-10之间")
        
        # 检查资源需求
        if config.resource_requirements.gpu_memory <= 0:
            errors.append("GPU内存需求必须大于0")
        
        # 检查GPU设备ID
        for gpu_id in config.gpu_devices:
            if gpu_id < 0:
                errors.append(f"无效的GPU设备ID: {gpu_id}")
        
        # 检查健康检查配置
        if config.health_check.enabled:
            if config.health_check.interval <= 0:
                errors.append("健康检查间隔必须大于0")
            if config.health_check.timeout <= 0:
                errors.append("健康检查超时时间必须大于0")
            if config.health_check.max_failures <= 0:
                errors.append("最大失败次数必须大于0")
        
        # 检查重试策略
        if config.retry_policy.enabled:
            if config.retry_policy.max_attempts <= 0:
                errors.append("最大重试次数必须大于0")
            if config.retry_policy.initial_delay < 0:
                errors.append("初始延迟不能为负数")
            if config.retry_policy.backoff_factor <= 0:
                errors.append("退避因子必须大于0")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    async def _start_health_check(self, model_id: str, config: ModelConfig):
        """启动健康检查任务"""
        if not config.health_check.enabled:
            return
        
        async def health_check_loop():
            failure_count = 0
            while True:
                try:
                    await asyncio.sleep(config.health_check.interval)
                    health_status = await self.check_health(model_id)
                    
                    if health_status == HealthStatus.UNHEALTHY:
                        failure_count += 1
                        logger.warning(f"模型 {model_id} 健康检查失败，失败次数: {failure_count}")
                        
                        if failure_count >= config.health_check.max_failures:
                            logger.error(f"模型 {model_id} 健康检查连续失败 {failure_count} 次，尝试重启")
                            if config.retry_policy.enabled:
                                await self._restart_model_with_retry(model_id, config)
                            failure_count = 0
                    else:
                        failure_count = 0
                        
                except asyncio.CancelledError:
                    logger.info(f"模型 {model_id} 健康检查任务已取消")
                    break
                except Exception as e:
                    logger.error(f"模型 {model_id} 健康检查异常: {e}")
        
        task = asyncio.create_task(health_check_loop())
        self._health_check_tasks[model_id] = task
    
    async def _restart_model_with_retry(self, model_id: str, config: ModelConfig):
        """带重试的模型重启"""
        for attempt in range(config.retry_policy.max_attempts):
            try:
                logger.info(f"尝试重启模型 {model_id}，第 {attempt + 1} 次")
                
                # 停止模型
                await self.stop_model(model_id)
                
                # 等待延迟
                delay = min(
                    config.retry_policy.initial_delay * (config.retry_policy.backoff_factor ** attempt),
                    config.retry_policy.max_delay
                )
                await asyncio.sleep(delay)
                
                # 重新启动模型
                success = await self.start_model(config)
                if success:
                    logger.info(f"模型 {model_id} 重启成功")
                    return True
                    
            except Exception as e:
                logger.error(f"模型 {model_id} 重启失败: {e}")
        
        logger.error(f"模型 {model_id} 重启失败，已达到最大重试次数")
        return False
    
    @abstractmethod
    async def _do_start_model(self, config: ModelConfig) -> bool:
        """具体的模型启动实现，由子类实现"""
        pass
    
    @abstractmethod
    async def _do_stop_model(self, model_id: str) -> bool:
        """具体的模型停止实现，由子类实现"""
        pass
    
    @abstractmethod
    async def _check_model_process(self, model_id: str) -> bool:
        """检查模型进程是否运行，由子类实现"""
        pass
    
    async def start_model(self, config: ModelConfig) -> bool:
        """启动模型实例"""
        try:
            logger.info(f"启动模型 {config.id}，框架: {self.framework_type}")
            
            # 执行具体的启动逻辑
            success = await self._do_start_model(config)
            
            if success:
                # 启动健康检查
                await self._start_health_check(config.id, config)
                logger.info(f"模型 {config.id} 启动成功")
            else:
                logger.error(f"模型 {config.id} 启动失败")
            
            return success
            
        except Exception as e:
            logger.error(f"启动模型 {config.id} 时发生异常: {e}")
            return False
    
    async def stop_model(self, model_id: str) -> bool:
        """停止模型实例"""
        try:
            logger.info(f"停止模型 {model_id}")
            
            # 取消健康检查任务
            if model_id in self._health_check_tasks:
                self._health_check_tasks[model_id].cancel()
                del self._health_check_tasks[model_id]
            
            # 执行具体的停止逻辑
            success = await self._do_stop_model(model_id)
            
            if success:
                self._remove_model_info(model_id)
                logger.info(f"模型 {model_id} 停止成功")
            else:
                logger.error(f"模型 {model_id} 停止失败")
            
            return success
            
        except Exception as e:
            logger.error(f"停止模型 {model_id} 时发生异常: {e}")
            return False
    
    async def get_model_status(self, model_id: str) -> ModelStatus:
        """获取模型状态"""
        try:
            model_info = self._get_model_info(model_id)
            if not model_info:
                return ModelStatus.STOPPED
            
            # 检查进程是否还在运行
            is_running = await self._check_model_process(model_id)
            if not is_running:
                self._remove_model_info(model_id)
                return ModelStatus.STOPPED
            
            return model_info.get('status', ModelStatus.RUNNING)
            
        except Exception as e:
            logger.error(f"获取模型 {model_id} 状态时发生异常: {e}")
            return ModelStatus.ERROR

class FrameworkAdapterFactory:
    """框架适配器工厂类"""
    
    _adapters: Dict[FrameworkType, type] = {}
    
    @classmethod
    def register_adapter(cls, framework_type: FrameworkType, adapter_class: type):
        """注册适配器类"""
        cls._adapters[framework_type] = adapter_class
        logger.info(f"注册框架适配器: {framework_type} -> {adapter_class.__name__}")
    
    @classmethod
    def create_adapter(cls, framework_type: FrameworkType) -> BaseFrameworkAdapter:
        """创建适配器实例"""
        if framework_type not in cls._adapters:
            raise ValueError(f"不支持的框架类型: {framework_type}")
        
        adapter_class = cls._adapters[framework_type]
        return adapter_class(framework_type)
    
    @classmethod
    def get_supported_frameworks(cls) -> list[FrameworkType]:
        """获取支持的框架类型列表"""
        return list(cls._adapters.keys())
    
    @classmethod
    def is_framework_supported(cls, framework_type: FrameworkType) -> bool:
        """检查是否支持指定框架"""
        return framework_type in cls._adapters

def register_adapter(framework_type: FrameworkType):
    """适配器注册装饰器"""
    def decorator(adapter_class):
        FrameworkAdapterFactory.register_adapter(framework_type, adapter_class)
        return adapter_class
    return decorator