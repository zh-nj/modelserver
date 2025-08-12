"""
模型生命周期管理服务
实现模型的创建、启动、停止、删除功能，以及状态跟踪和配置验证
"""
import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from .base import ModelManagerInterface, ConfigManagerInterface
from .health_checker import ModelHealthChecker, AutoRecoveryManager
from ..models.schemas import (
    ModelConfig, ModelInfo, ModelStatus, ValidationResult, 
    HealthStatus, ResourceRequirement
)
from ..models.enums import FrameworkType
from ..adapters.base import FrameworkAdapterFactory, BaseFrameworkAdapter
from ..core.config import settings

logger = logging.getLogger(__name__)

class ModelManager(ModelManagerInterface):
    """模型管理器实现"""
    
    def __init__(self, config_manager: ConfigManagerInterface):
        self.config_manager = config_manager
        self._models: Dict[str, ModelConfig] = {}  # 内存中的模型配置
        self._model_status: Dict[str, ModelStatus] = {}  # 模型状态缓存
        self._adapters: Dict[str, BaseFrameworkAdapter] = {}  # 模型对应的适配器实例
        self._status_update_callbacks: List[callable] = []  # 状态更新回调
        self._lock = asyncio.Lock()  # 并发控制锁
        
        # 健康检查相关
        self.health_checker: Optional[ModelHealthChecker] = None
        self.auto_recovery_manager: Optional[AutoRecoveryManager] = None
        
    async def initialize(self):
        """初始化模型管理器，加载已保存的配置"""
        try:
            logger.info("初始化模型管理器...")
            
            # 初始化健康检查器
            self.health_checker = ModelHealthChecker()
            await self.health_checker.start()
            
            # 初始化自动恢复管理器
            self.auto_recovery_manager = AutoRecoveryManager(self, self.health_checker)
            
            # 加载已保存的模型配置
            configs = await self.config_manager.load_model_configs()
            for config in configs:
                self._models[config.id] = config
                self._model_status[config.id] = ModelStatus.STOPPED
                logger.info(f"加载模型配置: {config.id} ({config.name})")
            
            logger.info(f"模型管理器初始化完成，加载了 {len(configs)} 个模型配置")
            
        except Exception as e:
            logger.error(f"初始化模型管理器失败: {e}")
            raise
    
    def add_status_update_callback(self, callback: callable):
        """添加状态更新回调函数"""
        self._status_update_callbacks.append(callback)
    
    async def _notify_status_change(self, model_id: str, old_status: ModelStatus, new_status: ModelStatus):
        """通知状态变更"""
        try:
            for callback in self._status_update_callbacks:
                await callback(model_id, old_status, new_status)
        except Exception as e:
            logger.error(f"通知状态变更失败: {e}")
    
    async def _update_model_status(self, model_id: str, status: ModelStatus):
        """更新模型状态并通知"""
        old_status = self._model_status.get(model_id, ModelStatus.STOPPED)
        if old_status != status:
            self._model_status[model_id] = status
            await self._notify_status_change(model_id, old_status, status)
            logger.info(f"模型 {model_id} 状态变更: {old_status} -> {status}")
    
    def _get_adapter(self, model_id: str) -> Optional[BaseFrameworkAdapter]:
        """获取模型对应的适配器"""
        return self._adapters.get(model_id)
    
    def _create_adapter(self, config: ModelConfig) -> BaseFrameworkAdapter:
        """为模型创建适配器"""
        try:
            adapter = FrameworkAdapterFactory.create_adapter(config.framework)
            self._adapters[config.id] = adapter
            return adapter
        except Exception as e:
            logger.error(f"创建适配器失败，框架: {config.framework}, 错误: {e}")
            raise
    
    def _get_model_endpoint(self, model_id: str) -> Optional[str]:
        """获取模型API端点"""
        try:
            adapter = self._adapters.get(model_id)
            if adapter:
                # 构建基础端点URL
                config = self._models.get(model_id)
                if config and config.parameters:
                    port = config.parameters.get('port', 8000)
                    host = config.parameters.get('host', 'localhost')
                    return f"http://{host}:{port}"
            return None
        except Exception as e:
            logger.error(f"获取模型 {model_id} 端点失败: {e}")
            return None
    
    async def create_model(self, config: ModelConfig) -> str:
        """创建模型配置"""
        async with self._lock:
            try:
                logger.info(f"创建模型配置: {config.id} ({config.name})")
                
                # 检查模型ID是否已存在
                if config.id in self._models:
                    raise ValueError(f"模型ID已存在: {config.id}")
                
                # 验证配置
                validation_result = await self._validate_model_config(config)
                if not validation_result.is_valid:
                    error_msg = f"配置验证失败: {', '.join(validation_result.errors)}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                # 设置创建时间
                config.created_at = datetime.now()
                config.updated_at = config.created_at
                
                # 保存配置到持久化存储
                success = await self.config_manager.save_model_config(config)
                if not success:
                    raise RuntimeError("保存模型配置失败")
                
                # 添加到内存缓存
                self._models[config.id] = config
                self._model_status[config.id] = ModelStatus.STOPPED
                
                logger.info(f"模型配置创建成功: {config.id}")
                return config.id
                
            except Exception as e:
                logger.error(f"创建模型配置失败: {e}")
                raise
    
    async def _validate_model_config(self, config: ModelConfig) -> ValidationResult:
        """验证模型配置"""
        try:
            # 首先进行基础验证
            if not FrameworkAdapterFactory.is_framework_supported(config.framework):
                return ValidationResult(
                    is_valid=False,
                    errors=[f"不支持的框架类型: {config.framework}"]
                )
            
            # 检查模型文件是否存在
            model_path = Path(config.model_path)
            if not model_path.exists():
                return ValidationResult(
                    is_valid=False,
                    errors=[f"模型文件不存在: {config.model_path}"]
                )
            
            # 使用适配器进行框架特定的验证
            try:
                adapter = FrameworkAdapterFactory.create_adapter(config.framework)
                adapter_validation = adapter.validate_config(config)
                return adapter_validation
            except Exception as e:
                return ValidationResult(
                    is_valid=False,
                    errors=[f"适配器验证失败: {str(e)}"]
                )
                
        except Exception as e:
            logger.error(f"验证模型配置时发生异常: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"配置验证异常: {str(e)}"]
            )
    
    async def start_model(self, model_id: str) -> bool:
        """启动模型"""
        async with self._lock:
            try:
                logger.info(f"启动模型: {model_id}")
                
                # 检查模型是否存在
                if model_id not in self._models:
                    logger.error(f"模型不存在: {model_id}")
                    return False
                
                config = self._models[model_id]
                current_status = self._model_status.get(model_id, ModelStatus.STOPPED)
                
                # 检查当前状态
                if current_status == ModelStatus.RUNNING:
                    logger.warning(f"模型 {model_id} 已在运行中")
                    return True
                
                if current_status in [ModelStatus.STARTING, ModelStatus.STOPPING]:
                    logger.warning(f"模型 {model_id} 正在状态转换中: {current_status}")
                    return False
                
                # 更新状态为启动中
                await self._update_model_status(model_id, ModelStatus.STARTING)
                
                try:
                    # 创建或获取适配器
                    adapter = self._adapters.get(model_id)
                    if not adapter:
                        adapter = self._create_adapter(config)
                    
                    # 启动模型
                    success = await adapter.start_model(config)
                    
                    if success:
                        await self._update_model_status(model_id, ModelStatus.RUNNING)
                        
                        # 启动健康检查
                        if self.health_checker and config.health_check.enabled:
                            await self.health_checker.start_health_check(
                                model_id, config, self._get_model_endpoint
                            )
                        
                        logger.info(f"模型 {model_id} 启动成功")
                    else:
                        await self._update_model_status(model_id, ModelStatus.ERROR)
                        logger.error(f"模型 {model_id} 启动失败")
                    
                    return success
                    
                except Exception as e:
                    await self._update_model_status(model_id, ModelStatus.ERROR)
                    logger.error(f"启动模型 {model_id} 时发生异常: {e}")
                    return False
                
            except Exception as e:
                logger.error(f"启动模型操作失败: {e}")
                return False
    
    async def stop_model(self, model_id: str) -> bool:
        """停止模型"""
        async with self._lock:
            try:
                logger.info(f"停止模型: {model_id}")
                
                # 检查模型是否存在
                if model_id not in self._models:
                    logger.error(f"模型不存在: {model_id}")
                    return False
                
                current_status = self._model_status.get(model_id, ModelStatus.STOPPED)
                
                # 检查当前状态
                if current_status == ModelStatus.STOPPED:
                    logger.warning(f"模型 {model_id} 已停止")
                    return True
                
                if current_status in [ModelStatus.STARTING, ModelStatus.STOPPING]:
                    logger.warning(f"模型 {model_id} 正在状态转换中: {current_status}")
                    return False
                
                # 更新状态为停止中
                await self._update_model_status(model_id, ModelStatus.STOPPING)
                
                try:
                    # 获取适配器
                    adapter = self._adapters.get(model_id)
                    if not adapter:
                        logger.warning(f"模型 {model_id} 没有对应的适配器，直接标记为已停止")
                        await self._update_model_status(model_id, ModelStatus.STOPPED)
                        return True
                    
                    # 停止模型
                    success = await adapter.stop_model(model_id)
                    
                    if success:
                        await self._update_model_status(model_id, ModelStatus.STOPPED)
                        
                        # 停止健康检查
                        if self.health_checker:
                            await self.health_checker.stop_health_check(model_id)
                            self.health_checker.cleanup_model_data(model_id)
                        
                        # 清理适配器
                        self._adapters.pop(model_id, None)
                        logger.info(f"模型 {model_id} 停止成功")
                    else:
                        await self._update_model_status(model_id, ModelStatus.ERROR)
                        logger.error(f"模型 {model_id} 停止失败")
                    
                    return success
                    
                except Exception as e:
                    await self._update_model_status(model_id, ModelStatus.ERROR)
                    logger.error(f"停止模型 {model_id} 时发生异常: {e}")
                    return False
                
            except Exception as e:
                logger.error(f"停止模型操作失败: {e}")
                return False
    
    async def restart_model(self, model_id: str) -> bool:
        """重启模型"""
        try:
            logger.info(f"重启模型: {model_id}")
            
            # 先停止模型
            stop_success = await self.stop_model(model_id)
            if not stop_success:
                logger.error(f"重启模型失败：停止模型 {model_id} 失败")
                return False
            
            # 等待一小段时间确保完全停止
            await asyncio.sleep(2)
            
            # 再启动模型
            start_success = await self.start_model(model_id)
            if start_success:
                logger.info(f"模型 {model_id} 重启成功")
            else:
                logger.error(f"重启模型失败：启动模型 {model_id} 失败")
            
            return start_success
            
        except Exception as e:
            logger.error(f"重启模型 {model_id} 时发生异常: {e}")
            return False
    
    async def get_model_status(self, model_id: str) -> ModelStatus:
        """获取模型状态"""
        try:
            if model_id not in self._models:
                logger.warning(f"模型不存在: {model_id}")
                return ModelStatus.STOPPED
            
            # 从适配器获取实时状态
            adapter = self._adapters.get(model_id)
            if adapter:
                try:
                    real_status = await adapter.get_model_status(model_id)
                    # 更新缓存状态
                    if real_status != self._model_status.get(model_id):
                        await self._update_model_status(model_id, real_status)
                    return real_status
                except Exception as e:
                    logger.error(f"从适配器获取模型 {model_id} 状态失败: {e}")
            
            # 返回缓存状态
            return self._model_status.get(model_id, ModelStatus.STOPPED)
            
        except Exception as e:
            logger.error(f"获取模型状态失败: {e}")
            return ModelStatus.ERROR
    
    async def list_models(self) -> List[ModelInfo]:
        """列出所有模型"""
        try:
            models = []
            
            for model_id, config in self._models.items():
                # 获取当前状态
                status = await self.get_model_status(model_id)
                
                # 获取API端点
                api_endpoint = None
                adapter = self._adapters.get(model_id)
                if adapter and status == ModelStatus.RUNNING:
                    try:
                        api_endpoint = await adapter.get_api_endpoint(model_id)
                    except Exception as e:
                        logger.warning(f"获取模型 {model_id} API端点失败: {e}")
                
                # 计算运行时间
                uptime = None
                if status == ModelStatus.RUNNING:
                    # 这里可以从适配器获取更精确的运行时间
                    # 暂时使用简单的估算
                    uptime = 0  # 需要在适配器中实现运行时间跟踪
                
                model_info = ModelInfo(
                    id=config.id,
                    name=config.name,
                    framework=config.framework,
                    model_path=config.model_path,  # 添加缺失的model_path字段
                    status=status,
                    priority=config.priority,
                    gpu_devices=config.gpu_devices,
                    memory_usage=config.resource_requirements.gpu_memory if status == ModelStatus.RUNNING else None,
                    api_endpoint=api_endpoint,
                    uptime=uptime,
                    last_health_check=None  # 需要从适配器获取
                )
                
                models.append(model_info)
            
            return models
            
        except Exception as e:
            logger.error(f"列出模型失败: {e}")
            return []
    
    async def delete_model(self, model_id: str) -> bool:
        """删除模型"""
        async with self._lock:
            try:
                logger.info(f"删除模型: {model_id}")
                
                # 检查模型是否存在
                if model_id not in self._models:
                    logger.error(f"模型不存在: {model_id}")
                    return False
                
                # 如果模型正在运行，先停止它
                current_status = self._model_status.get(model_id, ModelStatus.STOPPED)
                if current_status not in [ModelStatus.STOPPED, ModelStatus.ERROR]:
                    logger.info(f"模型 {model_id} 正在运行，先停止模型")
                    stop_success = await self.stop_model(model_id)
                    if not stop_success:
                        logger.error(f"删除模型失败：无法停止模型 {model_id}")
                        return False
                
                # 从持久化存储中删除配置
                config = self._models[model_id]
                # 这里需要配置管理器提供删除方法
                # await self.config_manager.delete_model_config(model_id)
                
                # 从内存中删除
                del self._models[model_id]
                self._model_status.pop(model_id, None)
                self._adapters.pop(model_id, None)
                
                logger.info(f"模型 {model_id} 删除成功")
                return True
                
            except Exception as e:
                logger.error(f"删除模型 {model_id} 失败: {e}")
                return False
    
    async def update_model_config(self, model_id: str, config: ModelConfig) -> bool:
        """更新模型配置"""
        async with self._lock:
            try:
                logger.info(f"更新模型配置: {model_id}")
                
                # 检查模型是否存在
                if model_id not in self._models:
                    logger.error(f"模型不存在: {model_id}")
                    return False
                
                # 验证新配置
                validation_result = await self._validate_model_config(config)
                if not validation_result.is_valid:
                    error_msg = f"配置验证失败: {', '.join(validation_result.errors)}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                # 检查模型是否正在运行
                current_status = self._model_status.get(model_id, ModelStatus.STOPPED)
                was_running = current_status == ModelStatus.RUNNING
                
                # 如果模型正在运行，需要重启以应用新配置
                if was_running:
                    logger.info(f"模型 {model_id} 正在运行，将重启以应用新配置")
                    await self.stop_model(model_id)
                
                # 更新配置
                config.updated_at = datetime.now()
                config.created_at = self._models[model_id].created_at  # 保持原创建时间
                
                # 保存到持久化存储
                success = await self.config_manager.save_model_config(config)
                if not success:
                    raise RuntimeError("保存模型配置失败")
                
                # 更新内存缓存
                self._models[model_id] = config
                
                # 如果之前在运行，重新启动
                if was_running:
                    await self.start_model(model_id)
                
                logger.info(f"模型配置 {model_id} 更新成功")
                return True
                
            except Exception as e:
                logger.error(f"更新模型配置 {model_id} 失败: {e}")
                return False
    
    async def get_model_config(self, model_id: str) -> Optional[ModelConfig]:
        """获取模型配置"""
        return self._models.get(model_id)
    
    async def get_model_health(self, model_id: str) -> HealthStatus:
        """获取模型健康状态"""
        try:
            # 优先从健康检查器获取状态
            if self.health_checker:
                health_status = self.health_checker.get_health_status(model_id)
                if health_status != HealthStatus.UNKNOWN:
                    return health_status
            
            # 如果健康检查器没有数据，从适配器获取
            adapter = self._adapters.get(model_id)
            if adapter:
                return await adapter.check_health(model_id)
            
            return HealthStatus.UNKNOWN
            
        except Exception as e:
            logger.error(f"获取模型 {model_id} 健康状态失败: {e}")
            return HealthStatus.UNKNOWN
    
    async def get_model_health_metrics(self, model_id: str):
        """获取模型健康指标"""
        if self.health_checker:
            return self.health_checker.get_health_metrics(model_id)
        return None
    
    async def get_model_health_result(self, model_id: str):
        """获取最新健康检查结果"""
        if self.health_checker:
            return self.health_checker.get_health_result(model_id)
        return None
    
    async def manual_health_check(self, model_id: str):
        """手动执行健康检查"""
        try:
            if not self.health_checker:
                return None
            
            config = self._models.get(model_id)
            if not config:
                return None
            
            return await self.health_checker.manual_health_check(
                model_id, config, self._get_model_endpoint
            )
        except Exception as e:
            logger.error(f"手动健康检查失败: {e}")
            return None
    
    def get_recovery_status(self, model_id: str):
        """获取模型恢复状态"""
        if self.auto_recovery_manager:
            return self.auto_recovery_manager.get_recovery_status(model_id)
        return {"is_recovering": False, "recovery_attempts": 0}
    
    async def stop_auto_recovery(self, model_id: str):
        """停止自动恢复"""
        if self.auto_recovery_manager:
            await self.auto_recovery_manager.stop_recovery(model_id)
    
    async def get_running_models(self) -> List[str]:
        """获取正在运行的模型ID列表"""
        running_models = []
        for model_id in self._models.keys():
            status = await self.get_model_status(model_id)
            if status == ModelStatus.RUNNING:
                running_models.append(model_id)
        return running_models
    
    async def get_models_by_priority(self, ascending: bool = False) -> List[ModelConfig]:
        """按优先级排序获取模型配置"""
        models = list(self._models.values())
        models.sort(key=lambda x: x.priority, reverse=not ascending)
        return models
    
    async def validate_model_config(self, config: ModelConfig) -> ValidationResult:
        """公共的模型配置验证方法"""
        return await self._validate_model_config(config)
    
    async def shutdown(self):
        """关闭模型管理器，停止所有运行中的模型"""
        try:
            logger.info("关闭模型管理器...")
            
            # 获取所有运行中的模型
            running_models = await self.get_running_models()
            
            # 并发停止所有模型
            if running_models:
                logger.info(f"停止 {len(running_models)} 个运行中的模型")
                tasks = [self.stop_model(model_id) for model_id in running_models]
                await asyncio.gather(*tasks, return_exceptions=True)
            
            # 关闭自动恢复管理器
            if self.auto_recovery_manager:
                await self.auto_recovery_manager.shutdown()
            
            # 关闭健康检查器
            if self.health_checker:
                await self.health_checker.shutdown()
            
            # 清理资源
            self._adapters.clear()
            self._status_update_callbacks.clear()
            
            logger.info("模型管理器关闭完成")
            
        except Exception as e:
            logger.error(f"关闭模型管理器失败: {e}")