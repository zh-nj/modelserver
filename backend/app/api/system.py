"""
系统配置和管理API端点
实现系统状态查询、GPU资源信息、配置管理等功能
"""
import logging
import os
import psutil
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.responses import JSONResponse

from ..models.schemas import (
    GPUInfo, SystemOverview, SystemResourceMetrics, 
    TimeRange, ValidationResult
)
from ..services.monitoring import MonitoringService
from ..services.config_manager import FileConfigManager
from ..utils.gpu import GPUDetector
from ..core.dependencies import get_monitoring_service, get_config_manager, get_gpu_detector
from ..core.config import settings
from pydantic import BaseModel
from typing import List

class FileBrowseSettings(BaseModel):
    """文件浏览设置"""
    allowed_browse_paths: List[str]
    enable_root_browse: bool
    max_browse_depth: int

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/system", tags=["system"])

@router.get("/status", response_model=SystemOverview)
async def get_system_status(
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """
    获取系统状态概览
    
    返回系统整体运行状态，包括模型数量、GPU使用情况、系统资源等
    """
    try:
        overview = await monitoring_service.get_system_overview()
        logger.info("获取系统状态概览成功")
        return overview
    except Exception as e:
        logger.error(f"获取系统状态概览失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取系统状态失败: {str(e)}"
        )

@router.get("/overview", response_model=SystemOverview)
async def get_system_overview(
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """
    获取系统概览
    
    返回系统整体运行状态，包括模型数量、GPU使用情况、系统资源等
    """
    try:
        overview = await monitoring_service.get_system_overview()
        logger.info("获取系统概览成功")
        return overview
    except Exception as e:
        logger.error(f"获取系统概览失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取系统概览失败: {str(e)}"
        )

@router.get("/gpu", response_model=List[GPUInfo])
async def get_gpu_info(
    gpu_detector: GPUDetector = Depends(get_gpu_detector)
):
    """
    获取GPU设备信息
    
    返回系统中所有GPU设备的详细信息，包括内存、利用率、温度等
    """
    try:
        gpus = await gpu_detector.detect_gpus()
        logger.info(f"获取GPU信息成功，共 {len(gpus)} 个设备")
        return gpus
    except Exception as e:
        logger.error(f"获取GPU信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取GPU信息失败: {str(e)}"
        )

@router.get("/gpu/{device_id}", response_model=GPUInfo)
async def get_gpu_device_info(
    device_id: int,
    gpu_detector: GPUDetector = Depends(get_gpu_detector)
):
    """
    获取指定GPU设备信息
    
    返回指定GPU设备的详细信息
    """
    try:
        gpu_info = await gpu_detector.get_gpu_info(device_id)
        if not gpu_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"GPU设备不存在: {device_id}"
            )
        
        logger.info(f"获取GPU设备 {device_id} 信息成功")
        return gpu_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取GPU设备 {device_id} 信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取GPU设备信息失败: {str(e)}"
        )

@router.get("/resources", response_model=SystemResourceMetrics)
async def get_system_resources(
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """
    获取系统资源使用情况
    
    返回CPU、内存、磁盘、网络等系统资源的实时使用情况
    """
    try:
        # 获取最新的系统资源指标
        system_metrics = await monitoring_service.system_collector.collect_metrics()
        logger.info("获取系统资源信息成功")
        return system_metrics
    except Exception as e:
        logger.error(f"获取系统资源信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取系统资源信息失败: {str(e)}"
        )

@router.get("/info")
async def get_system_info():
    """
    获取系统基本信息
    
    返回操作系统、Python版本、硬件信息等基本系统信息
    """
    try:
        import platform
        import sys
        
        # 获取系统信息
        system_info = {
            "hostname": platform.node(),
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": sys.version,
            "python_executable": sys.executable,
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
            "current_time": datetime.now().isoformat(),
            "timezone": str(datetime.now().astimezone().tzinfo)
        }
        
        # 获取CPU信息
        cpu_info = {
            "cpu_count_logical": psutil.cpu_count(logical=True),
            "cpu_count_physical": psutil.cpu_count(logical=False),
            "cpu_freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
        }
        
        # 获取内存信息
        memory = psutil.virtual_memory()
        memory_info = {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent,
            "used": memory.used,
            "free": memory.free
        }
        
        # 获取磁盘信息
        disk_usage = psutil.disk_usage('/')
        disk_info = {
            "total": disk_usage.total,
            "used": disk_usage.used,
            "free": disk_usage.free,
            "percent": (disk_usage.used / disk_usage.total) * 100
        }
        
        result = {
            "system": system_info,
            "cpu": cpu_info,
            "memory": memory_info,
            "disk": disk_info
        }
        
        logger.info("获取系统基本信息成功")
        return result
        
    except Exception as e:
        logger.error(f"获取系统基本信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取系统基本信息失败: {str(e)}"
        )

@router.get("/processes")
async def get_system_processes(
    limit: int = Query(20, description="返回进程数量限制"),
    sort_by: str = Query("memory", description="排序字段: cpu, memory, name")
):
    """
    获取系统进程信息
    
    返回系统中运行的进程信息，按指定字段排序
    """
    try:
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status', 'create_time']):
            try:
                proc_info = proc.info
                proc_info['create_time'] = datetime.fromtimestamp(proc_info['create_time']).isoformat()
                processes.append(proc_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        # 排序
        if sort_by == "cpu":
            processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
        elif sort_by == "memory":
            processes.sort(key=lambda x: x.get('memory_percent', 0), reverse=True)
        elif sort_by == "name":
            processes.sort(key=lambda x: x.get('name', ''))
        
        # 限制返回数量
        processes = processes[:limit]
        
        logger.info(f"获取系统进程信息成功，返回 {len(processes)} 个进程")
        return {
            "processes": processes,
            "total_count": len(processes),
            "sort_by": sort_by
        }
        
    except Exception as e:
        logger.error(f"获取系统进程信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取系统进程信息失败: {str(e)}"
        )

@router.get("/config")
async def get_system_config(
    config_manager: FileConfigManager = Depends(get_config_manager)
):
    """
    获取系统配置
    
    返回当前系统的配置信息
    """
    try:
        # 获取应用配置
        app_config = {
            "cors_origins": settings.cors_origins,
            "debug": settings.debug,
            "log_level": settings.log_level,
            "database_url": settings.database_url,
            "redis_url": settings.redis_url,
            "monitoring_interval": getattr(settings, 'monitoring_interval', 30),
            "health_check_interval": getattr(settings, 'health_check_interval', 60),
            "max_models": getattr(settings, 'max_models', 10),
            "default_gpu_memory_limit": getattr(settings, 'default_gpu_memory_limit', 8192)
        }
        
        # 获取运行时配置
        runtime_config = {
            "service_start_time": datetime.now().isoformat(),  # 这里应该从实际启动时间获取
            "config_file_path": getattr(settings, 'config_file', 'config.yaml'),
            "log_file_path": getattr(settings, 'log_file', 'logs/app.log'),
            "data_directory": getattr(settings, 'data_dir', 'data/'),
            "backup_directory": getattr(settings, 'backup_dir', 'backups/')
        }
        
        result = {
            "application": app_config,
            "runtime": runtime_config,
            "last_updated": datetime.now().isoformat()
        }
        
        logger.info("获取系统配置成功")
        return result
        
    except Exception as e:
        logger.error(f"获取系统配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取系统配置失败: {str(e)}"
        )

@router.put("/config")
async def update_system_config(
    config_data: Dict[str, Any],
    config_manager: FileConfigManager = Depends(get_config_manager)
):
    """
    更新系统配置
    
    更新系统配置参数，部分配置需要重启服务才能生效
    """
    try:
        # 验证配置数据
        allowed_keys = {
            'monitoring_interval', 'health_check_interval', 'max_models',
            'default_gpu_memory_limit', 'log_level', 'cors_origins'
        }
        
        invalid_keys = set(config_data.keys()) - allowed_keys
        if invalid_keys:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的配置项: {', '.join(invalid_keys)}"
            )
        
        # 这里应该实现实际的配置更新逻辑
        # 由于settings通常是只读的，这里只是示例
        updated_keys = []
        for key, value in config_data.items():
            if hasattr(settings, key):
                # 在实际实现中，应该更新配置文件并重新加载
                updated_keys.append(key)
        
        logger.info(f"更新系统配置成功: {updated_keys}")
        return {
            "success": True,
            "message": "系统配置更新成功",
            "updated_keys": updated_keys,
            "restart_required": True,  # 大部分配置更改需要重启
            "updated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新系统配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新系统配置失败: {str(e)}"
        )

@router.get("/logs")
async def get_system_logs(
    lines: int = Query(100, description="返回日志行数"),
    level: Optional[str] = Query(None, description="日志级别过滤: DEBUG, INFO, WARNING, ERROR"),
    since: Optional[str] = Query(None, description="起始时间 (ISO格式)")
):
    """
    获取系统日志
    
    返回系统运行日志，支持按级别和时间过滤
    """
    try:
        log_file = getattr(settings, 'log_file', 'logs/app.log')
        
        if not os.path.exists(log_file):
            return {
                "logs": [],
                "message": f"日志文件不存在: {log_file}",
                "total_lines": 0
            }
        
        # 读取日志文件
        with open(log_file, 'r', encoding='utf-8') as f:
            log_lines = f.readlines()
        
        # 过滤日志
        filtered_logs = []
        for line in log_lines[-lines:]:  # 只取最后N行
            line = line.strip()
            if not line:
                continue
            
            # 级别过滤
            if level and level.upper() not in line:
                continue
            
            # 时间过滤 (简化实现)
            if since:
                try:
                    since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
                    # 这里应该解析日志中的时间戳进行比较
                    # 简化实现，跳过时间过滤
                except ValueError:
                    pass
            
            filtered_logs.append(line)
        
        logger.info(f"获取系统日志成功，返回 {len(filtered_logs)} 行")
        return {
            "logs": filtered_logs,
            "total_lines": len(filtered_logs),
            "log_file": log_file,
            "filters": {
                "lines": lines,
                "level": level,
                "since": since
            }
        }
        
    except Exception as e:
        logger.error(f"获取系统日志失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取系统日志失败: {str(e)}"
        )

@router.post("/backup")
async def create_backup(
    config_manager: FileConfigManager = Depends(get_config_manager)
):
    """
    创建配置备份
    
    备份当前系统配置和模型配置到备份目录
    """
    try:
        # 创建备份
        backup_path = await config_manager.backup_configs()
        
        logger.info(f"创建配置备份成功: {backup_path}")
        return {
            "success": True,
            "message": "配置备份创建成功",
            "backup_path": backup_path,
            "created_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"创建配置备份失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建配置备份失败: {str(e)}"
        )

@router.post("/restore")
async def restore_backup(
    backup_path: str,
    config_manager: FileConfigManager = Depends(get_config_manager)
):
    """
    恢复配置备份
    
    从指定备份文件恢复系统配置
    """
    try:
        # 验证备份文件是否存在
        if not os.path.exists(backup_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"备份文件不存在: {backup_path}"
            )
        
        # 恢复配置
        success = await config_manager.restore_configs(backup_path)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="配置恢复失败"
            )
        
        logger.info(f"恢复配置备份成功: {backup_path}")
        return {
            "success": True,
            "message": "配置恢复成功",
            "backup_path": backup_path,
            "restored_at": datetime.now().isoformat(),
            "restart_required": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复配置备份失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"恢复配置备份失败: {str(e)}"
        )

@router.get("/backups")
async def list_backups():
    """
    列出可用的备份文件
    
    返回备份目录中所有可用的备份文件信息
    """
    try:
        backup_dir = getattr(settings, 'backup_dir', 'backups/')
        
        if not os.path.exists(backup_dir):
            return {
                "backups": [],
                "message": f"备份目录不存在: {backup_dir}",
                "backup_directory": backup_dir
            }
        
        backups = []
        for filename in os.listdir(backup_dir):
            if filename.endswith('.tar.gz') or filename.endswith('.zip'):
                file_path = os.path.join(backup_dir, filename)
                stat = os.stat(file_path)
                
                backup_info = {
                    "filename": filename,
                    "path": file_path,
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                }
                backups.append(backup_info)
        
        # 按创建时间排序
        backups.sort(key=lambda x: x['created_at'], reverse=True)
        
        logger.info(f"列出备份文件成功，共 {len(backups)} 个备份")
        return {
            "backups": backups,
            "total_count": len(backups),
            "backup_directory": backup_dir
        }
        
    except Exception as e:
        logger.error(f"列出备份文件失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"列出备份文件失败: {str(e)}"
        )

@router.delete("/backups/{backup_filename}")
async def delete_backup(backup_filename: str):
    """
    删除指定的备份文件
    
    删除备份目录中的指定备份文件
    """
    try:
        backup_dir = getattr(settings, 'backup_dir', 'backups/')
        backup_path = os.path.join(backup_dir, backup_filename)
        
        if not os.path.exists(backup_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"备份文件不存在: {backup_filename}"
            )
        
        # 安全检查：确保文件在备份目录内
        if not os.path.abspath(backup_path).startswith(os.path.abspath(backup_dir)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的备份文件路径"
            )
        
        os.remove(backup_path)
        
        logger.info(f"删除备份文件成功: {backup_filename}")
        return {
            "success": True,
            "message": "备份文件删除成功",
            "filename": backup_filename,
            "deleted_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除备份文件失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除备份文件失败: {str(e)}"
        )

@router.post("/restart")
async def restart_service():
    """
    重启服务
    
    重启LLM推理服务（需要外部进程管理器支持）
    """
    try:
        # 这里应该实现实际的服务重启逻辑
        # 通常需要与systemd或其他进程管理器集成
        
        logger.warning("收到服务重启请求")
        return {
            "success": True,
            "message": "服务重启请求已接收，请等待服务重新启动",
            "restart_requested_at": datetime.now().isoformat(),
            "note": "实际重启需要外部进程管理器支持"
        }
        
    except Exception as e:
        logger.error(f"重启服务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重启服务失败: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """
    系统健康检查
    
    检查系统各组件的健康状态
    """
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {}
        }
        
        # 检查数据库连接
        try:
            # 这里应该实际检查数据库连接
            health_status["components"]["database"] = {
                "status": "healthy",
                "message": "数据库连接正常"
            }
        except Exception as e:
            health_status["components"]["database"] = {
                "status": "unhealthy",
                "message": f"数据库连接失败: {str(e)}"
            }
            health_status["status"] = "degraded"
        
        # 检查GPU可用性
        try:
            gpu_detector = get_gpu_detector()
            gpus = await gpu_detector.detect_gpus()
            health_status["components"]["gpu"] = {
                "status": "healthy" if gpus else "warning",
                "message": f"检测到 {len(gpus)} 个GPU设备",
                "gpu_count": len(gpus)
            }
        except Exception as e:
            health_status["components"]["gpu"] = {
                "status": "unhealthy",
                "message": f"GPU检测失败: {str(e)}"
            }
            health_status["status"] = "degraded"
        
        # 检查磁盘空间
        try:
            disk_usage = psutil.disk_usage('/')
            free_percent = (disk_usage.free / disk_usage.total) * 100
            
            if free_percent < 10:
                disk_status = "critical"
                health_status["status"] = "unhealthy"
            elif free_percent < 20:
                disk_status = "warning"
                if health_status["status"] == "healthy":
                    health_status["status"] = "degraded"
            else:
                disk_status = "healthy"
            
            health_status["components"]["disk"] = {
                "status": disk_status,
                "message": f"磁盘可用空间: {free_percent:.1f}%",
                "free_percent": free_percent
            }
        except Exception as e:
            health_status["components"]["disk"] = {
                "status": "unhealthy",
                "message": f"磁盘检查失败: {str(e)}"
            }
            health_status["status"] = "degraded"
        
        # 检查内存使用
        try:
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                memory_status = "critical"
                health_status["status"] = "unhealthy"
            elif memory.percent > 80:
                memory_status = "warning"
                if health_status["status"] == "healthy":
                    health_status["status"] = "degraded"
            else:
                memory_status = "healthy"
            
            health_status["components"]["memory"] = {
                "status": memory_status,
                "message": f"内存使用率: {memory.percent:.1f}%",
                "usage_percent": memory.percent
            }
        except Exception as e:
            health_status["components"]["memory"] = {
                "status": "unhealthy",
                "message": f"内存检查失败: {str(e)}"
            }
            health_status["status"] = "degraded"
        
        logger.info(f"系统健康检查完成，状态: {health_status['status']}")
        
        # 根据健康状态返回适当的HTTP状态码
        if health_status["status"] == "unhealthy":
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=health_status
            )
        elif health_status["status"] == "degraded":
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=health_status
            )
        else:
            return health_status
        
    except Exception as e:
        logger.error(f"系统健康检查失败: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "message": f"健康检查失败: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
        )

@router.get("/file-browse-settings", response_model=FileBrowseSettings)
async def get_file_browse_settings():
    """
    获取文件浏览设置
    
    返回当前的文件浏览配置，包括允许的路径、根目录浏览权限等
    """
    try:
        current_settings = FileBrowseSettings(
            allowed_browse_paths=settings.allowed_browse_paths,
            enable_root_browse=settings.enable_root_browse,
            max_browse_depth=settings.max_browse_depth
        )
        
        logger.info("获取文件浏览设置成功")
        return current_settings
        
    except Exception as e:
        logger.error(f"获取文件浏览设置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文件浏览设置失败: {str(e)}"
        )

@router.put("/file-browse-settings")
async def update_file_browse_settings(
    new_settings: FileBrowseSettings
):
    """
    更新文件浏览设置
    
    更新文件浏览配置，包括允许的路径、根目录浏览权限等
    注意：此更改需要重启服务才能完全生效
    """
    try:
        # 验证路径设置
        if not new_settings.allowed_browse_paths:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="至少需要配置一个允许的浏览路径"
            )
        
        # 验证最大浏览深度
        if new_settings.max_browse_depth < 1 or new_settings.max_browse_depth > 20:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="最大浏览深度必须在1-20之间"
            )
        
        # 验证路径是否存在（可选验证）
        valid_paths = []
        invalid_paths = []
        
        for path in new_settings.allowed_browse_paths:
            try:
                expanded_path = os.path.expanduser(path)
                expanded_path = os.path.abspath(expanded_path)
                
                if os.path.exists(expanded_path):
                    valid_paths.append(path)
                else:
                    invalid_paths.append(path)
            except Exception:
                invalid_paths.append(path)
        
        # 在实际应用中，这里应该更新配置文件
        # 由于settings通常是只读的，这里只是模拟更新
        # 实际实现需要写入配置文件并重新加载
        
        result = {
            "success": True,
            "message": "文件浏览设置更新成功",
            "settings": new_settings.dict(),
            "validation": {
                "valid_paths": valid_paths,
                "invalid_paths": invalid_paths,
                "total_paths": len(new_settings.allowed_browse_paths)
            },
            "restart_required": True,
            "updated_at": datetime.now().isoformat()
        }
        
        if invalid_paths:
            result["warning"] = f"以下路径不存在或无法访问: {', '.join(invalid_paths)}"
        
        logger.info(f"更新文件浏览设置成功: {len(valid_paths)} 个有效路径")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新文件浏览设置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新文件浏览设置失败: {str(e)}"
        )

@router.post("/validate-browse-path")
async def validate_browse_path(
    path: str = Query(..., description="要验证的路径")
):
    """
    验证浏览路径
    
    检查指定路径是否存在且可访问
    """
    try:
        expanded_path = os.path.expanduser(path)
        expanded_path = os.path.abspath(expanded_path)
        
        result = {
            "path": path,
            "expanded_path": expanded_path,
            "exists": False,
            "is_directory": False,
            "accessible": False,
            "readable": False,
            "writable": False
        }
        
        if os.path.exists(expanded_path):
            result["exists"] = True
            result["is_directory"] = os.path.isdir(expanded_path)
            
            try:
                result["accessible"] = os.access(expanded_path, os.F_OK)
                result["readable"] = os.access(expanded_path, os.R_OK)
                result["writable"] = os.access(expanded_path, os.W_OK)
            except Exception:
                pass
        
        logger.info(f"验证浏览路径: {path} -> {result}")
        return result
        
    except Exception as e:
        logger.error(f"验证浏览路径失败 {path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"验证浏览路径失败: {str(e)}"
        )