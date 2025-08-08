"""
配置管理API端点
提供模型配置的CRUD操作、备份恢复等功能
"""
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse

from ..core.dependencies import get_database_config_manager
from ..services.database_config_manager import DatabaseConfigManager
from ..services.config_hot_reload import get_hot_reload_service, ConfigChangeEvent
from ..models.schemas import ModelConfig, ValidationResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["配置管理"])

@router.post("/models", response_model=dict)
async def create_model_config(
    config: ModelConfig,
    config_manager: DatabaseConfigManager = Depends(get_database_config_manager)
):
    """创建或更新模型配置"""
    try:
        # 验证配置
        validation_result = await config_manager.validate_config(config)
        if not validation_result.is_valid:
            return {
                "success": False,
                "message": "配置验证失败",
                "errors": validation_result.errors,
                "warnings": validation_result.warnings
            }
        
        # 保存配置
        success = await config_manager.save_model_config(config)
        if success:
            return {
                "success": True,
                "message": f"模型配置 {config.id} 保存成功",
                "warnings": validation_result.warnings
            }
        else:
            raise HTTPException(status_code=500, detail="保存配置失败")
            
    except Exception as e:
        logger.error(f"创建模型配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建配置失败: {str(e)}")

@router.get("/models", response_model=List[ModelConfig])
async def list_model_configs(
    config_manager: DatabaseConfigManager = Depends(get_database_config_manager)
):
    """获取所有模型配置"""
    try:
        configs = await config_manager.load_model_configs()
        return configs
    except Exception as e:
        logger.error(f"获取模型配置列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置列表失败: {str(e)}")

@router.get("/models/{model_id}", response_model=ModelConfig)
async def get_model_config(
    model_id: str,
    config_manager: DatabaseConfigManager = Depends(get_database_config_manager)
):
    """获取指定模型配置"""
    try:
        configs = await config_manager.load_model_configs()
        for config in configs:
            if config.id == model_id:
                return config
        
        raise HTTPException(status_code=404, detail=f"模型配置 {model_id} 不存在")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模型配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")

@router.put("/models/{model_id}", response_model=dict)
async def update_model_config(
    model_id: str,
    config: ModelConfig,
    config_manager: DatabaseConfigManager = Depends(get_database_config_manager)
):
    """更新模型配置"""
    try:
        # 确保ID匹配
        if config.id != model_id:
            raise HTTPException(status_code=400, detail="配置ID与路径参数不匹配")
        
        # 验证配置
        validation_result = await config_manager.validate_config(config)
        if not validation_result.is_valid:
            return {
                "success": False,
                "message": "配置验证失败",
                "errors": validation_result.errors,
                "warnings": validation_result.warnings
            }
        
        # 更新配置
        success = await config_manager.save_model_config(config)
        if success:
            return {
                "success": True,
                "message": f"模型配置 {model_id} 更新成功",
                "warnings": validation_result.warnings
            }
        else:
            raise HTTPException(status_code=500, detail="更新配置失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新模型配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")

@router.delete("/models/{model_id}", response_model=dict)
async def delete_model_config(
    model_id: str,
    config_manager: DatabaseConfigManager = Depends(get_database_config_manager)
):
    """删除模型配置"""
    try:
        success = await config_manager.delete_model_config(model_id)
        if success:
            return {
                "success": True,
                "message": f"模型配置 {model_id} 删除成功"
            }
        else:
            raise HTTPException(status_code=500, detail="删除配置失败")
            
    except Exception as e:
        logger.error(f"删除模型配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除配置失败: {str(e)}")

@router.post("/models/{model_id}/validate", response_model=ValidationResult)
async def validate_model_config(
    model_id: str,
    config: ModelConfig,
    config_manager: DatabaseConfigManager = Depends(get_database_config_manager)
):
    """验证模型配置"""
    try:
        # 确保ID匹配
        if config.id != model_id:
            raise HTTPException(status_code=400, detail="配置ID与路径参数不匹配")
        
        validation_result = await config_manager.validate_config(config)
        return validation_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"验证模型配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"验证配置失败: {str(e)}")

@router.post("/backup", response_model=dict)
async def create_backup(
    config_manager: DatabaseConfigManager = Depends(get_database_config_manager)
):
    """创建配置备份"""
    try:
        backup_name = await config_manager.backup_configs()
        if backup_name:
            return {
                "success": True,
                "message": "配置备份创建成功",
                "backup_name": backup_name
            }
        else:
            raise HTTPException(status_code=500, detail="创建备份失败")
            
    except Exception as e:
        logger.error(f"创建配置备份失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建备份失败: {str(e)}")

@router.get("/backups", response_model=List[Dict[str, Any]])
async def list_backups(
    config_manager: DatabaseConfigManager = Depends(get_database_config_manager)
):
    """获取备份列表"""
    try:
        backups = await config_manager.list_backups()
        return backups
    except Exception as e:
        logger.error(f"获取备份列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取备份列表失败: {str(e)}")

@router.post("/restore/{backup_name}", response_model=dict)
async def restore_backup(
    backup_name: str,
    config_manager: DatabaseConfigManager = Depends(get_database_config_manager)
):
    """从备份恢复配置"""
    try:
        success = await config_manager.restore_configs(backup_name)
        if success:
            return {
                "success": True,
                "message": f"配置从备份 {backup_name} 恢复成功"
            }
        else:
            raise HTTPException(status_code=500, detail="恢复配置失败")
            
    except Exception as e:
        logger.error(f"恢复配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"恢复配置失败: {str(e)}")

@router.delete("/backups/cleanup", response_model=dict)
async def cleanup_old_backups(
    keep_count: int = Query(10, description="保留的备份数量"),
    config_manager: DatabaseConfigManager = Depends(get_database_config_manager)
):
    """清理旧备份"""
    try:
        deleted_count = await config_manager.cleanup_old_backups(keep_count)
        return {
            "success": True,
            "message": f"清理完成，删除了 {deleted_count} 个旧备份",
            "deleted_count": deleted_count
        }
    except Exception as e:
        logger.error(f"清理备份失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理备份失败: {str(e)}")

@router.get("/export", response_model=dict)
async def export_configs(
    config_manager: DatabaseConfigManager = Depends(get_database_config_manager)
):
    """导出所有配置"""
    try:
        configs = await config_manager.load_model_configs()
        
        # 转换为可序列化的格式
        export_data = {
            "version": "1.0",
            "export_time": "2024-01-01T00:00:00Z",  # 实际应该使用当前时间
            "configs": []
        }
        
        for config in configs:
            config_dict = {
                "id": config.id,
                "name": config.name,
                "framework": config.framework.value,
                "model_path": config.model_path,
                "priority": config.priority,
                "gpu_devices": config.gpu_devices,
                "parameters": config.parameters,
                "resource_requirements": {
                    "gpu_memory": config.resource_requirements.gpu_memory,
                    "gpu_devices": config.resource_requirements.gpu_devices,
                    "cpu_cores": config.resource_requirements.cpu_cores,
                    "system_memory": config.resource_requirements.system_memory
                },
                "health_check": {
                    "enabled": config.health_check.enabled,
                    "interval": config.health_check.interval,
                    "timeout": config.health_check.timeout,
                    "max_failures": config.health_check.max_failures,
                    "endpoint": config.health_check.endpoint
                },
                "retry_policy": {
                    "enabled": config.retry_policy.enabled,
                    "max_attempts": config.retry_policy.max_attempts,
                    "initial_delay": config.retry_policy.initial_delay,
                    "max_delay": config.retry_policy.max_delay,
                    "backoff_factor": config.retry_policy.backoff_factor
                }
            }
            export_data["configs"].append(config_dict)
        
        return {
            "success": True,
            "data": export_data,
            "count": len(configs)
        }
        
    except Exception as e:
        logger.error(f"导出配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"导出配置失败: {str(e)}")

@router.post("/import", response_model=dict)
async def import_configs(
    import_data: Dict[str, Any],
    config_manager: DatabaseConfigManager = Depends(get_database_config_manager)
):
    """导入配置"""
    try:
        if "configs" not in import_data:
            raise HTTPException(status_code=400, detail="导入数据格式错误，缺少configs字段")
        
        configs_data = import_data["configs"]
        imported_count = 0
        errors = []
        
        for config_data in configs_data:
            try:
                # 构建ModelConfig对象
                from ..models.schemas import ResourceRequirement, HealthCheckConfig, RetryPolicy
                from ..models.enums import FrameworkType
                from datetime import datetime
                
                resource_req_data = config_data.get("resource_requirements", {})
                resource_requirements = ResourceRequirement(
                    gpu_memory=resource_req_data.get("gpu_memory", 0),
                    gpu_devices=resource_req_data.get("gpu_devices", []),
                    cpu_cores=resource_req_data.get("cpu_cores"),
                    system_memory=resource_req_data.get("system_memory")
                )
                
                health_check_data = config_data.get("health_check", {})
                health_check = HealthCheckConfig(
                    enabled=health_check_data.get("enabled", True),
                    interval=health_check_data.get("interval", 30),
                    timeout=health_check_data.get("timeout", 10),
                    max_failures=health_check_data.get("max_failures", 3),
                    endpoint=health_check_data.get("endpoint")
                )
                
                retry_policy_data = config_data.get("retry_policy", {})
                retry_policy = RetryPolicy(
                    enabled=retry_policy_data.get("enabled", True),
                    max_attempts=retry_policy_data.get("max_attempts", 3),
                    initial_delay=retry_policy_data.get("initial_delay", 5),
                    max_delay=retry_policy_data.get("max_delay", 300),
                    backoff_factor=retry_policy_data.get("backoff_factor", 2.0)
                )
                
                config = ModelConfig(
                    id=config_data["id"],
                    name=config_data["name"],
                    framework=FrameworkType(config_data["framework"]),
                    model_path=config_data["model_path"],
                    priority=config_data["priority"],
                    gpu_devices=config_data.get("gpu_devices", []),
                    parameters=config_data.get("parameters", {}),
                    resource_requirements=resource_requirements,
                    health_check=health_check,
                    retry_policy=retry_policy,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                # 验证并保存配置
                validation_result = await config_manager.validate_config(config)
                if validation_result.is_valid:
                    success = await config_manager.save_model_config(config)
                    if success:
                        imported_count += 1
                    else:
                        errors.append(f"保存配置 {config.id} 失败")
                else:
                    errors.append(f"配置 {config.id} 验证失败: {', '.join(validation_result.errors)}")
                    
            except Exception as e:
                errors.append(f"处理配置 {config_data.get('id', 'unknown')} 失败: {str(e)}")
                continue
        
        return {
            "success": True,
            "message": f"导入完成，成功导入 {imported_count}/{len(configs_data)} 个配置",
            "imported_count": imported_count,
            "total_count": len(configs_data),
            "errors": errors
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导入配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"导入配置失败: {str(e)}")

@router.get("/health", response_model=dict)
async def config_health_check(
    config_manager: DatabaseConfigManager = Depends(get_database_config_manager)
):
    """配置管理健康检查"""
    try:
        # 检查数据库连接
        from ..core.database import db_manager
        db_healthy = await db_manager.health_check()
        
        # 获取配置统计
        configs = await config_manager.load_model_configs()
        config_count = len(configs)
        
        # 获取备份统计
        backups = await config_manager.list_backups()
        backup_count = len(backups)
        
        return {
            "healthy": db_healthy,
            "database_connected": db_healthy,
            "config_count": config_count,
            "backup_count": backup_count,
            "message": "配置管理服务正常" if db_healthy else "数据库连接异常"
        }
        
    except Exception as e:
        logger.error(f"配置管理健康检查失败: {e}")
        return {
            "healthy": False,
            "database_connected": False,
            "config_count": 0,
            "backup_count": 0,
            "message": f"健康检查失败: {str(e)}"
        }

# 配置热重载相关端点

@router.get("/hot-reload/status", response_model=dict)
async def get_hot_reload_status():
    """获取配置热重载服务状态"""
    try:
        hot_reload_service = get_hot_reload_service()
        if not hot_reload_service:
            return {
                "available": False,
                "message": "配置热重载服务未启用"
            }
        
        status = hot_reload_service.get_status()
        return {
            "available": True,
            "status": status
        }
        
    except Exception as e:
        logger.error(f"获取热重载状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取热重载状态失败: {str(e)}")

@router.post("/hot-reload/force-reload", response_model=dict)
async def force_reload_configs():
    """强制重新加载所有配置"""
    try:
        hot_reload_service = get_hot_reload_service()
        if not hot_reload_service:
            raise HTTPException(status_code=503, detail="配置热重载服务未启用")
        
        changes = await hot_reload_service.force_reload()
        
        return {
            "success": True,
            "message": f"强制重载完成，检测到 {len(changes)} 个配置变更",
            "changes_count": len(changes),
            "changes": [
                {
                    "model_id": change.model_id,
                    "change_type": change.change_type.value,
                    "timestamp": change.timestamp.isoformat(),
                    "changed_fields": change.change_fields or []
                }
                for change in changes
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"强制重载配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"强制重载配置失败: {str(e)}")

@router.post("/hot-reload/reload-model/{model_id}", response_model=dict)
async def reload_model_config(model_id: str):
    """重新加载指定模型配置"""
    try:
        hot_reload_service = get_hot_reload_service()
        if not hot_reload_service:
            raise HTTPException(status_code=503, detail="配置热重载服务未启用")
        
        change = await hot_reload_service.reload_model_config(model_id)
        
        if change:
            return {
                "success": True,
                "message": f"模型配置 {model_id} 重载成功",
                "change": {
                    "model_id": change.model_id,
                    "change_type": change.change_type.value,
                    "timestamp": change.timestamp.isoformat(),
                    "changed_fields": change.change_fields or []
                }
            }
        else:
            return {
                "success": True,
                "message": f"模型配置 {model_id} 无变更",
                "change": None
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重载模型配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"重载模型配置失败: {str(e)}")

@router.put("/hot-reload/settings", response_model=dict)
async def update_hot_reload_settings(
    enabled: bool = Query(None, description="是否启用热重载"),
    check_interval: int = Query(None, description="检查间隔（秒）"),
    auto_apply: bool = Query(None, description="是否自动应用配置变更")
):
    """更新热重载设置"""
    try:
        hot_reload_service = get_hot_reload_service()
        if not hot_reload_service:
            raise HTTPException(status_code=503, detail="配置热重载服务未启用")
        
        updated_settings = []
        
        if enabled is not None:
            if enabled:
                hot_reload_service.enable()
            else:
                hot_reload_service.disable()
            updated_settings.append(f"启用状态: {'启用' if enabled else '禁用'}")
        
        if check_interval is not None:
            hot_reload_service.set_check_interval(check_interval)
            updated_settings.append(f"检查间隔: {check_interval}秒")
        
        if auto_apply is not None:
            hot_reload_service.set_auto_apply(auto_apply)
            updated_settings.append(f"自动应用: {'启用' if auto_apply else '禁用'}")
        
        return {
            "success": True,
            "message": f"热重载设置更新成功: {', '.join(updated_settings)}",
            "current_status": hot_reload_service.get_status()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新热重载设置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新热重载设置失败: {str(e)}")

@router.get("/hot-reload/cached-configs", response_model=dict)
async def get_cached_configs():
    """获取缓存的配置"""
    try:
        hot_reload_service = get_hot_reload_service()
        if not hot_reload_service:
            raise HTTPException(status_code=503, detail="配置热重载服务未启用")
        
        cached_configs = hot_reload_service.get_all_cached_configs()
        
        # 转换为可序列化的格式
        configs_data = []
        for model_id, config in cached_configs.items():
            configs_data.append({
                "id": config.id,
                "name": config.name,
                "framework": config.framework.value,
                "priority": config.priority,
                "created_at": config.created_at.isoformat() if config.created_at else None,
                "updated_at": config.updated_at.isoformat() if config.updated_at else None
            })
        
        return {
            "success": True,
            "cached_configs": configs_data,
            "count": len(configs_data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取缓存配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取缓存配置失败: {str(e)}")

@router.get("/hot-reload/cached-configs/{model_id}", response_model=dict)
async def get_cached_model_config(model_id: str):
    """获取指定模型的缓存配置"""
    try:
        hot_reload_service = get_hot_reload_service()
        if not hot_reload_service:
            raise HTTPException(status_code=503, detail="配置热重载服务未启用")
        
        cached_config = hot_reload_service.get_cached_config(model_id)
        
        if not cached_config:
            raise HTTPException(status_code=404, detail=f"缓存中未找到模型配置 {model_id}")
        
        return {
            "success": True,
            "config": {
                "id": cached_config.id,
                "name": cached_config.name,
                "framework": cached_config.framework.value,
                "model_path": cached_config.model_path,
                "priority": cached_config.priority,
                "gpu_devices": cached_config.gpu_devices,
                "parameters": cached_config.parameters,
                "resource_requirements": {
                    "gpu_memory": cached_config.resource_requirements.gpu_memory,
                    "gpu_devices": cached_config.resource_requirements.gpu_devices,
                    "cpu_cores": cached_config.resource_requirements.cpu_cores,
                    "system_memory": cached_config.resource_requirements.system_memory
                },
                "health_check": {
                    "enabled": cached_config.health_check.enabled,
                    "interval": cached_config.health_check.interval,
                    "timeout": cached_config.health_check.timeout,
                    "max_failures": cached_config.health_check.max_failures,
                    "endpoint": cached_config.health_check.endpoint
                },
                "retry_policy": {
                    "enabled": cached_config.retry_policy.enabled,
                    "max_attempts": cached_config.retry_policy.max_attempts,
                    "initial_delay": cached_config.retry_policy.initial_delay,
                    "max_delay": cached_config.retry_policy.max_delay,
                    "backoff_factor": cached_config.retry_policy.backoff_factor
                },
                "created_at": cached_config.created_at.isoformat() if cached_config.created_at else None,
                "updated_at": cached_config.updated_at.isoformat() if cached_config.updated_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取缓存模型配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取缓存模型配置失败: {str(e)}")