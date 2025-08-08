"""
配置热重载服务
实现配置变更检测、运行时更新和通知机制
"""
import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass
from enum import Enum

from ..models.schemas import ModelConfig
from ..models.enums import ModelStatus
from .database_config_manager import DatabaseConfigManager

logger = logging.getLogger(__name__)

class ConfigChangeType(Enum):
    """配置变更类型"""
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    RELOADED = "reloaded"

@dataclass
class ConfigChangeEvent:
    """配置变更事件"""
    change_type: ConfigChangeType
    model_id: str
    old_config: Optional[ModelConfig] = None
    new_config: Optional[ModelConfig] = None
    timestamp: datetime = None
    change_fields: List[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        
        if self.change_fields is None and self.old_config and self.new_config:
            self.change_fields = self._detect_changed_fields()
    
    def _detect_changed_fields(self) -> List[str]:
        """检测变更字段"""
        changed_fields = []
        
        if not self.old_config or not self.new_config:
            return changed_fields
        
        # 比较基本字段
        basic_fields = ['name', 'framework', 'model_path', 'priority', 'gpu_devices', 'parameters']
        for field in basic_fields:
            old_value = getattr(self.old_config, field)
            new_value = getattr(self.new_config, field)
            if old_value != new_value:
                changed_fields.append(field)
        
        # 比较资源需求
        if self.old_config.resource_requirements != self.new_config.resource_requirements:
            changed_fields.append('resource_requirements')
        
        # 比较健康检查配置
        if self.old_config.health_check != self.new_config.health_check:
            changed_fields.append('health_check')
        
        # 比较重试策略
        if self.old_config.retry_policy != self.new_config.retry_policy:
            changed_fields.append('retry_policy')
        
        return changed_fields

class ConfigHotReloadService:
    """配置热重载服务"""
    
    def __init__(self, config_manager: DatabaseConfigManager, model_manager=None):
        self.config_manager = config_manager
        self.model_manager = model_manager
        
        # 配置缓存
        self._config_cache: Dict[str, ModelConfig] = {}
        self._last_check_time = datetime.now()
        
        # 事件监听器
        self._change_listeners: List[Callable[[ConfigChangeEvent], None]] = []
        
        # 热重载设置
        self.check_interval = 5  # 检查间隔（秒）
        self.enabled = True
        self.auto_apply_changes = True  # 是否自动应用配置变更
        
        # 任务控制
        self._reload_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info("配置热重载服务初始化完成")
    
    async def start(self):
        """启动热重载服务"""
        if self._running:
            logger.warning("配置热重载服务已在运行")
            return
        
        try:
            logger.info("启动配置热重载服务...")
            self._running = True
            
            # 初始化配置缓存
            await self._initialize_cache()
            
            # 启动监控任务
            self._reload_task = asyncio.create_task(self._reload_loop())
            
            logger.info("配置热重载服务启动成功")
            
        except Exception as e:
            logger.error(f"启动配置热重载服务失败: {e}")
            self._running = False
            raise
    
    async def stop(self):
        """停止热重载服务"""
        if not self._running:
            return
        
        try:
            logger.info("停止配置热重载服务...")
            self._running = False
            
            # 取消监控任务
            if self._reload_task and not self._reload_task.done():
                self._reload_task.cancel()
                try:
                    await self._reload_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("配置热重载服务停止完成")
            
        except Exception as e:
            logger.error(f"停止配置热重载服务失败: {e}")
    
    def add_change_listener(self, listener: Callable[[ConfigChangeEvent], None]):
        """添加配置变更监听器"""
        if listener not in self._change_listeners:
            self._change_listeners.append(listener)
            logger.info(f"添加配置变更监听器: {listener.__name__}")
    
    def remove_change_listener(self, listener: Callable[[ConfigChangeEvent], None]):
        """移除配置变更监听器"""
        if listener in self._change_listeners:
            self._change_listeners.remove(listener)
            logger.info(f"移除配置变更监听器: {listener.__name__}")
    
    async def force_reload(self) -> List[ConfigChangeEvent]:
        """强制重新加载配置"""
        logger.info("强制重新加载配置...")
        return await self._check_and_apply_changes()
    
    async def reload_model_config(self, model_id: str) -> Optional[ConfigChangeEvent]:
        """重新加载指定模型配置"""
        try:
            logger.info(f"重新加载模型配置: {model_id}")
            
            # 从数据库加载最新配置
            configs = await self.config_manager.load_model_configs()
            new_config = None
            for config in configs:
                if config.id == model_id:
                    new_config = config
                    break
            
            old_config = self._config_cache.get(model_id)
            
            # 检测变更
            if new_config and old_config:
                # 配置更新
                if self._configs_differ(old_config, new_config):
                    event = ConfigChangeEvent(
                        change_type=ConfigChangeType.UPDATED,
                        model_id=model_id,
                        old_config=old_config,
                        new_config=new_config
                    )
                    
                    # 更新缓存
                    self._config_cache[model_id] = new_config
                    
                    # 应用变更
                    if self.auto_apply_changes:
                        await self._apply_config_change(event)
                    
                    # 通知监听器
                    await self._notify_listeners(event)
                    
                    return event
            elif new_config and not old_config:
                # 新增配置
                event = ConfigChangeEvent(
                    change_type=ConfigChangeType.CREATED,
                    model_id=model_id,
                    new_config=new_config
                )
                
                # 更新缓存
                self._config_cache[model_id] = new_config
                
                # 应用变更
                if self.auto_apply_changes:
                    await self._apply_config_change(event)
                
                # 通知监听器
                await self._notify_listeners(event)
                
                return event
            elif not new_config and old_config:
                # 删除配置
                event = ConfigChangeEvent(
                    change_type=ConfigChangeType.DELETED,
                    model_id=model_id,
                    old_config=old_config
                )
                
                # 更新缓存
                if model_id in self._config_cache:
                    del self._config_cache[model_id]
                
                # 应用变更
                if self.auto_apply_changes:
                    await self._apply_config_change(event)
                
                # 通知监听器
                await self._notify_listeners(event)
                
                return event
            
            return None
            
        except Exception as e:
            logger.error(f"重新加载模型配置 {model_id} 失败: {e}")
            return None
    
    def get_cached_config(self, model_id: str) -> Optional[ModelConfig]:
        """获取缓存的配置"""
        return self._config_cache.get(model_id)
    
    def get_all_cached_configs(self) -> Dict[str, ModelConfig]:
        """获取所有缓存的配置"""
        return self._config_cache.copy()
    
    async def _initialize_cache(self):
        """初始化配置缓存"""
        try:
            logger.info("初始化配置缓存...")
            configs = await self.config_manager.load_model_configs()
            
            self._config_cache.clear()
            for config in configs:
                self._config_cache[config.id] = config
            
            logger.info(f"配置缓存初始化完成，加载了 {len(configs)} 个配置")
            
        except Exception as e:
            logger.error(f"初始化配置缓存失败: {e}")
            raise
    
    async def _reload_loop(self):
        """配置重载循环"""
        logger.info("配置重载监控循环启动")
        
        while self._running:
            try:
                if self.enabled:
                    await self._check_and_apply_changes()
                
                # 等待下次检查
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                logger.info("配置重载监控循环被取消")
                break
            except Exception as e:
                logger.error(f"配置重载监控循环异常: {e}")
                # 继续运行，避免因单次错误导致服务停止
                await asyncio.sleep(self.check_interval)
        
        logger.info("配置重载监控循环结束")
    
    async def _check_and_apply_changes(self) -> List[ConfigChangeEvent]:
        """检查并应用配置变更"""
        try:
            # 从数据库加载最新配置
            current_configs = await self.config_manager.load_model_configs()
            current_config_dict = {config.id: config for config in current_configs}
            
            changes = []
            
            # 检查新增和更新的配置
            for model_id, new_config in current_config_dict.items():
                old_config = self._config_cache.get(model_id)
                
                if old_config is None:
                    # 新增配置
                    event = ConfigChangeEvent(
                        change_type=ConfigChangeType.CREATED,
                        model_id=model_id,
                        new_config=new_config
                    )
                    changes.append(event)
                    
                elif self._configs_differ(old_config, new_config):
                    # 更新配置
                    event = ConfigChangeEvent(
                        change_type=ConfigChangeType.UPDATED,
                        model_id=model_id,
                        old_config=old_config,
                        new_config=new_config
                    )
                    changes.append(event)
            
            # 检查删除的配置
            for model_id in self._config_cache:
                if model_id not in current_config_dict:
                    event = ConfigChangeEvent(
                        change_type=ConfigChangeType.DELETED,
                        model_id=model_id,
                        old_config=self._config_cache[model_id]
                    )
                    changes.append(event)
            
            # 应用变更
            if changes:
                logger.info(f"检测到 {len(changes)} 个配置变更")
                
                for event in changes:
                    # 更新缓存
                    if event.change_type == ConfigChangeType.DELETED:
                        if event.model_id in self._config_cache:
                            del self._config_cache[event.model_id]
                    else:
                        self._config_cache[event.model_id] = event.new_config
                    
                    # 应用变更
                    if self.auto_apply_changes:
                        await self._apply_config_change(event)
                    
                    # 通知监听器
                    await self._notify_listeners(event)
            
            self._last_check_time = datetime.now()
            return changes
            
        except Exception as e:
            logger.error(f"检查配置变更失败: {e}")
            return []
    
    def _configs_differ(self, config1: ModelConfig, config2: ModelConfig) -> bool:
        """比较两个配置是否不同"""
        try:
            # 比较基本字段
            basic_fields = ['name', 'framework', 'model_path', 'priority', 'gpu_devices']
            for field in basic_fields:
                if getattr(config1, field) != getattr(config2, field):
                    return True
            
            # 比较参数（JSON序列化后比较）
            if json.dumps(config1.parameters, sort_keys=True) != json.dumps(config2.parameters, sort_keys=True):
                return True
            
            # 比较资源需求
            if (config1.resource_requirements.gpu_memory != config2.resource_requirements.gpu_memory or
                config1.resource_requirements.gpu_devices != config2.resource_requirements.gpu_devices or
                config1.resource_requirements.cpu_cores != config2.resource_requirements.cpu_cores or
                config1.resource_requirements.system_memory != config2.resource_requirements.system_memory):
                return True
            
            # 比较健康检查配置
            hc1, hc2 = config1.health_check, config2.health_check
            if (hc1.enabled != hc2.enabled or hc1.interval != hc2.interval or
                hc1.timeout != hc2.timeout or hc1.max_failures != hc2.max_failures or
                hc1.endpoint != hc2.endpoint):
                return True
            
            # 比较重试策略
            rp1, rp2 = config1.retry_policy, config2.retry_policy
            if (rp1.enabled != rp2.enabled or rp1.max_attempts != rp2.max_attempts or
                rp1.initial_delay != rp2.initial_delay or rp1.max_delay != rp2.max_delay or
                rp1.backoff_factor != rp2.backoff_factor):
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"比较配置时发生异常: {e}")
            return True  # 发生异常时认为配置不同，触发更新
    
    async def _apply_config_change(self, event: ConfigChangeEvent):
        """应用配置变更"""
        try:
            if not self.model_manager:
                logger.warning("模型管理器未设置，无法应用配置变更")
                return
            
            logger.info(f"应用配置变更: {event.change_type.value} - {event.model_id}")
            
            if event.change_type == ConfigChangeType.CREATED:
                # 新增模型配置，但不自动启动
                logger.info(f"新增模型配置: {event.model_id}")
                
            elif event.change_type == ConfigChangeType.UPDATED:
                # 更新模型配置
                await self._handle_config_update(event)
                
            elif event.change_type == ConfigChangeType.DELETED:
                # 删除模型配置
                await self._handle_config_deletion(event)
            
        except Exception as e:
            logger.error(f"应用配置变更失败: {e}")
    
    async def _handle_config_update(self, event: ConfigChangeEvent):
        """处理配置更新"""
        try:
            model_id = event.model_id
            
            # 检查模型是否正在运行
            model_status = await self.model_manager.get_model_status(model_id)
            
            if model_status and model_status.status == ModelStatus.RUNNING:
                # 检查是否需要重启模型
                if self._requires_model_restart(event):
                    logger.info(f"配置变更需要重启模型: {model_id}")
                    
                    # 停止模型
                    await self.model_manager.stop_model(model_id)
                    
                    # 等待一段时间确保模型完全停止
                    await asyncio.sleep(2)
                    
                    # 使用新配置启动模型
                    await self.model_manager.start_model(model_id)
                    
                    logger.info(f"模型 {model_id} 重启完成")
                else:
                    logger.info(f"配置变更不需要重启模型: {model_id}")
            else:
                logger.info(f"模型 {model_id} 未运行，配置更新已生效")
            
        except Exception as e:
            logger.error(f"处理配置更新失败: {e}")
    
    async def _handle_config_deletion(self, event: ConfigChangeEvent):
        """处理配置删除"""
        try:
            model_id = event.model_id
            
            # 检查模型是否正在运行
            model_status = await self.model_manager.get_model_status(model_id)
            
            if model_status and model_status.status == ModelStatus.RUNNING:
                logger.info(f"停止已删除配置的模型: {model_id}")
                await self.model_manager.stop_model(model_id)
            
            logger.info(f"模型配置 {model_id} 删除处理完成")
            
        except Exception as e:
            logger.error(f"处理配置删除失败: {e}")
    
    def _requires_model_restart(self, event: ConfigChangeEvent) -> bool:
        """判断配置变更是否需要重启模型"""
        if not event.change_fields:
            return False
        
        # 需要重启的配置字段
        restart_required_fields = {
            'framework', 'model_path', 'gpu_devices', 'parameters', 'resource_requirements'
        }
        
        # 检查是否有需要重启的字段变更
        for field in event.change_fields:
            if field in restart_required_fields:
                return True
        
        return False
    
    async def _notify_listeners(self, event: ConfigChangeEvent):
        """通知配置变更监听器"""
        try:
            for listener in self._change_listeners:
                try:
                    if asyncio.iscoroutinefunction(listener):
                        await listener(event)
                    else:
                        listener(event)
                except Exception as e:
                    logger.error(f"配置变更监听器 {listener.__name__} 执行失败: {e}")
        except Exception as e:
            logger.error(f"通知配置变更监听器失败: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取热重载服务状态"""
        return {
            "running": self._running,
            "enabled": self.enabled,
            "auto_apply_changes": self.auto_apply_changes,
            "check_interval": self.check_interval,
            "cached_configs_count": len(self._config_cache),
            "listeners_count": len(self._change_listeners),
            "last_check_time": self._last_check_time.isoformat() if self._last_check_time else None
        }
    
    def set_check_interval(self, interval: int):
        """设置检查间隔"""
        if interval > 0:
            self.check_interval = interval
            logger.info(f"配置检查间隔设置为 {interval} 秒")
        else:
            logger.warning("检查间隔必须大于0")
    
    def enable(self):
        """启用热重载"""
        self.enabled = True
        logger.info("配置热重载已启用")
    
    def disable(self):
        """禁用热重载"""
        self.enabled = False
        logger.info("配置热重载已禁用")
    
    def set_auto_apply(self, auto_apply: bool):
        """设置是否自动应用配置变更"""
        self.auto_apply_changes = auto_apply
        logger.info(f"自动应用配置变更: {'启用' if auto_apply else '禁用'}")

# 全局热重载服务实例
_hot_reload_service: Optional[ConfigHotReloadService] = None

def get_hot_reload_service() -> Optional[ConfigHotReloadService]:
    """获取热重载服务实例"""
    return _hot_reload_service

def set_hot_reload_service(service: ConfigHotReloadService):
    """设置热重载服务实例"""
    global _hot_reload_service
    _hot_reload_service = service