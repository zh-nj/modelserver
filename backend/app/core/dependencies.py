"""
依赖注入配置
提供FastAPI依赖注入的服务实例
"""
import logging
from typing import Optional
from functools import lru_cache
from fastapi import HTTPException

from ..services.monitoring import MonitoringService
from ..services.model_manager import ModelManager
from ..services.config_manager import FileConfigManager
from ..services.database_config_manager import DatabaseConfigManager
from ..services.config_hot_reload import ConfigHotReloadService, set_hot_reload_service
from ..utils.gpu import GPUDetector
from .database import init_database, close_database

logger = logging.getLogger(__name__)

# 全局服务实例
_monitoring_service: Optional[MonitoringService] = None
_model_manager: Optional[ModelManager] = None
_config_manager: Optional[FileConfigManager] = None
_database_config_manager: Optional[DatabaseConfigManager] = None
_gpu_detector: Optional[GPUDetector] = None
_proxy_service: Optional['APIProxyService'] = None

@lru_cache()
def get_gpu_detector() -> GPUDetector:
    """获取GPU检测器实例"""
    global _gpu_detector
    if _gpu_detector is None:
        _gpu_detector = GPUDetector()
    return _gpu_detector

@lru_cache()
def get_config_manager() -> FileConfigManager:
    """获取文件配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = FileConfigManager()
    return _config_manager

@lru_cache()
def get_database_config_manager() -> DatabaseConfigManager:
    """获取数据库配置管理器实例"""
    global _database_config_manager
    if _database_config_manager is None:
        _database_config_manager = DatabaseConfigManager()
    return _database_config_manager

@lru_cache()
def get_model_manager() -> ModelManager:
    """获取模型管理器实例"""
    global _model_manager
    if _model_manager is None:
        config_manager = get_config_manager()
        _model_manager = ModelManager(config_manager)
    return _model_manager

@lru_cache()
def get_monitoring_service() -> MonitoringService:
    """获取监控服务实例"""
    global _monitoring_service
    if _monitoring_service is None:
        model_manager = get_model_manager()
        gpu_detector = get_gpu_detector()
        _monitoring_service = MonitoringService(model_manager, gpu_detector)
    return _monitoring_service

def get_proxy_service():
    """获取API代理服务实例"""
    global _proxy_service
    if _proxy_service is None:
        raise HTTPException(
            status_code=503,
            detail="API代理服务尚未初始化"
        )
    return _proxy_service

async def initialize_services():
    """初始化所有服务"""
    try:
        logger.info("初始化应用服务...")
        
        # 初始化数据库
        await init_database()
        
        # 初始化数据库配置管理器
        database_config_manager = get_database_config_manager()
        await database_config_manager.initialize()
        
        # 初始化文件配置管理器（作为备用）
        config_manager = get_config_manager()
        await config_manager.initialize()
        
        # 初始化模型管理器（使用数据库配置管理器）
        model_manager = get_model_manager()
        # 更新模型管理器使用数据库配置管理器
        model_manager.config_manager = database_config_manager
        await model_manager.initialize()
        
        # 初始化监控服务
        monitoring_service = get_monitoring_service()
        await monitoring_service.initialize()
        
        # 初始化配置热重载服务
        hot_reload_service = ConfigHotReloadService(database_config_manager, model_manager)
        set_hot_reload_service(hot_reload_service)
        await hot_reload_service.start()
        
        # 初始化API代理服务
        from ..services.api_proxy import APIProxyService
        global _proxy_service
        if _proxy_service is None:
            _proxy_service = APIProxyService()
            # API代理服务不需要start方法，它是无状态的
        
        logger.info("所有服务初始化完成")
        
    except Exception as e:
        logger.error(f"服务初始化失败: {e}")
        raise

async def shutdown_services():
    """关闭所有服务"""
    try:
        logger.info("关闭应用服务...")
        
        # 关闭API代理服务
        if _proxy_service:
            await _proxy_service.stop()
        
        # 关闭配置热重载服务
        from ..services.config_hot_reload import get_hot_reload_service
        hot_reload_service = get_hot_reload_service()
        if hot_reload_service:
            await hot_reload_service.stop()
        
        # 关闭监控服务
        if _monitoring_service:
            await _monitoring_service.shutdown()
        
        # 关闭模型管理器
        if _model_manager:
            await _model_manager.shutdown()
        
        # 关闭数据库连接
        await close_database()
        
        logger.info("所有服务关闭完成")
        
    except Exception as e:
        logger.error(f"服务关闭失败: {e}")