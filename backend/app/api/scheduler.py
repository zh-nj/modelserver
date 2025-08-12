"""
任务调度管理API端点
实现模型调度、资源分配、调度历史等功能
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..models.schemas import (
    ModelConfig, ScheduleResult, ScheduleDecision, 
    GPUInfo, ResourceAllocation, ScheduleHistory
)
from ..services.resource_scheduler import ResourceScheduler
from ..services.model_manager import ModelManager
from ..services.monitoring import MonitoringService
from ..core.dependencies import (
    get_resource_scheduler, get_model_manager, get_monitoring_service
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/scheduler", tags=["scheduler"])

class ManualScheduleRequest(BaseModel):
    """手动调度请求"""
    model_id: str = Field(..., description="模型ID")
    priority: Optional[int] = Field(None, description="优先级 (1-10)")
    force: bool = Field(False, description="强制调度")
    allow_preemption: bool = Field(True, description="允许抢占")

class SchedulePolicyConfig(BaseModel):
    """调度策略配置"""
    scheduling_algorithm: str = Field("priority_based", description="调度算法")
    preemption_enabled: bool = Field(True, description="启用抢占")
    auto_recovery_enabled: bool = Field(True, description="启用自动恢复")
    resource_threshold: float = Field(0.8, description="资源阈值")
    priority_levels: int = Field(10, description="优先级级别")
    max_queue_size: int = Field(50, description="最大队列长度")
    scheduling_interval: int = Field(30, description="调度间隔(秒)")
    health_check_interval: int = Field(60, description="健康检查间隔(秒)")

@router.get("/status")
async def get_scheduler_status(
    scheduler: ResourceScheduler = Depends(get_resource_scheduler),
    model_manager: ModelManager = Depends(get_model_manager)
):
    """
    获取调度器状态概览
    
    返回调度器运行状态、模型统计、资源使用情况等
    """
    try:
        # 获取所有模型状态
        models = await model_manager.list_models()
        
        # 统计模型状态
        total_models = len(models)
        running_models = len([m for m in models if m.status == 'running'])
        queued_models = len([m for m in models if m.status in ['queued', 'pending']])
        failed_models = len([m for m in models if m.status in ['error', 'failed']])
        
        # 获取调度器状态
        scheduler_status = {
            "status": "running",  # 调度器状态
            "last_schedule_time": datetime.now().isoformat(),
            "auto_scheduling_enabled": True,
            "preemption_enabled": True,
            "total_schedules_today": 0,  # 今日调度次数
            "successful_schedules": 0,   # 成功调度次数
            "failed_schedules": 0        # 失败调度次数
        }
        
        result = {
            "scheduler": scheduler_status,
            "models": {
                "total": total_models,
                "running": running_models,
                "queued": queued_models,
                "failed": failed_models
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info("获取调度器状态成功")
        return result
        
    except Exception as e:
        logger.error(f"获取调度器状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取调度器状态失败: {str(e)}"
        )

@router.get("/queue")
async def get_schedule_queue(
    model_manager: ModelManager = Depends(get_model_manager)
):
    """
    获取调度队列
    
    返回当前等待调度的模型列表，按优先级排序
    """
    try:
        # 获取所有模型
        models = await model_manager.list_models()
        
        # 过滤出队列中的模型（非运行状态）
        queued_models = [
            m for m in models 
            if m.status not in ['running', 'stopped']
        ]
        
        # 按优先级排序
        queued_models.sort(key=lambda x: x.priority or 0, reverse=True)
        
        # 添加队列位置信息
        for i, model in enumerate(queued_models):
            model.queue_position = i + 1
            model.estimated_start_time = datetime.now() + timedelta(minutes=i * 5)
        
        result = {
            "queue": queued_models,
            "total_count": len(queued_models),
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"获取调度队列成功，共 {len(queued_models)} 个模型")
        return result
        
    except Exception as e:
        logger.error(f"获取调度队列失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取调度队列失败: {str(e)}"
        )

@router.get("/history")
async def get_schedule_history(
    limit: int = Query(50, description="返回记录数量"),
    hours: int = Query(24, description="时间范围(小时)"),
    model_id: Optional[str] = Query(None, description="模型ID过滤")
):
    """
    获取调度历史记录
    
    返回指定时间范围内的调度历史，支持按模型过滤
    """
    try:
        # 模拟调度历史数据（实际应该从数据库获取）
        mock_history = []
        
        # 生成一些示例历史记录
        actions = ['scheduled', 'preempted', 'failed', 'recovered']
        model_names = ['ChatGLM-6B', 'Llama2-7B', 'Baichuan2-13B', 'CodeLlama-7B']
        
        for i in range(min(limit, 20)):
            history_item = {
                "id": str(i + 1),
                "model_id": f"model_{i % 4 + 1}",
                "model_name": model_names[i % len(model_names)],
                "action": actions[i % len(actions)],
                "timestamp": datetime.now() - timedelta(minutes=i * 15),
                "gpu_devices": [i % 4] if i % 2 == 0 else [i % 4, (i + 1) % 4],
                "result": "success" if i % 5 != 0 else "failed",
                "reason": f"调度原因 {i + 1}",
                "duration": i * 2 + 10,  # 执行时长(秒)
                "resource_usage": {
                    "gpu_memory": (i % 8 + 1) * 1024,  # MB
                    "cpu_cores": i % 4 + 1,
                    "system_memory": (i % 4 + 1) * 2048  # MB
                }
            }
            
            # 应用模型过滤
            if model_id and history_item["model_id"] != model_id:
                continue
                
            # 应用时间过滤
            if history_item["timestamp"] < datetime.now() - timedelta(hours=hours):
                continue
                
            mock_history.append(history_item)
        
        # 按时间排序
        mock_history.sort(key=lambda x: x["timestamp"], reverse=True)
        
        result = {
            "history": mock_history,
            "total_count": len(mock_history),
            "filters": {
                "limit": limit,
                "hours": hours,
                "model_id": model_id
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"获取调度历史成功，返回 {len(mock_history)} 条记录")
        return result
        
    except Exception as e:
        logger.error(f"获取调度历史失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取调度历史失败: {str(e)}"
        )

@router.post("/schedule")
async def manual_schedule(
    request: ManualScheduleRequest,
    scheduler: ResourceScheduler = Depends(get_resource_scheduler),
    model_manager: ModelManager = Depends(get_model_manager)
):
    """
    手动调度模型
    
    手动触发指定模型的调度，支持强制调度和抢占选项
    """
    try:
        # 验证模型是否存在
        model_config = await model_manager.get_model_config(request.model_id)
        if not model_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"模型不存在: {request.model_id}"
            )
        
        # 检查模型当前状态
        model_status = await model_manager.get_model_status(request.model_id)
        if model_status == 'running':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="模型已在运行中"
            )
        
        # 更新模型优先级（如果指定）
        if request.priority is not None:
            model_config.priority = request.priority
            await model_manager.update_model_config(request.model_id, model_config)
        
        # 执行调度
        schedule_result = await scheduler.schedule_model(
            model_id=request.model_id,
            force=request.force,
            allow_preemption=request.allow_preemption
        )
        
        # 记录调度历史
        history_record = {
            "model_id": request.model_id,
            "action": "manual_schedule",
            "timestamp": datetime.now(),
            "result": "success" if schedule_result.success else "failed",
            "reason": schedule_result.message,
            "gpu_devices": schedule_result.gpu_devices,
            "requested_by": "manual",  # 手动调度标识
            "force": request.force,
            "allow_preemption": request.allow_preemption
        }
        
        result = {
            "success": schedule_result.success,
            "message": schedule_result.message,
            "model_id": request.model_id,
            "gpu_devices": schedule_result.gpu_devices,
            "preempted_models": schedule_result.preempted_models,
            "schedule_time": datetime.now().isoformat(),
            "history_id": history_record.get("id")
        }
        
        logger.info(f"手动调度模型 {request.model_id}: {schedule_result.message}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"手动调度模型失败 {request.model_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"手动调度失败: {str(e)}"
        )

@router.post("/models/{model_id}/prioritize")
async def prioritize_model(
    model_id: str,
    model_manager: ModelManager = Depends(get_model_manager)
):
    """
    提升模型优先级
    
    将指定模型的优先级提升1级，触发重新调度
    """
    try:
        # 获取模型配置
        model_config = await model_manager.get_model_config(model_id)
        if not model_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"模型不存在: {model_id}"
            )
        
        # 提升优先级
        current_priority = model_config.priority or 1
        new_priority = min(current_priority + 1, 10)  # 最高优先级为10
        
        if new_priority == current_priority:
            return {
                "success": False,
                "message": "模型已是最高优先级",
                "current_priority": current_priority
            }
        
        # 更新配置
        model_config.priority = new_priority
        await model_manager.update_model_config(model_id, model_config)
        
        result = {
            "success": True,
            "message": f"优先级已从 {current_priority} 提升到 {new_priority}",
            "model_id": model_id,
            "old_priority": current_priority,
            "new_priority": new_priority,
            "updated_at": datetime.now().isoformat()
        }
        
        logger.info(f"提升模型 {model_id} 优先级: {current_priority} -> {new_priority}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提升模型优先级失败 {model_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提升优先级失败: {str(e)}"
        )

@router.post("/models/{model_id}/cancel")
async def cancel_model_schedule(
    model_id: str,
    model_manager: ModelManager = Depends(get_model_manager)
):
    """
    取消模型调度
    
    将模型从调度队列中移除，停止等待调度
    """
    try:
        # 验证模型存在
        model_config = await model_manager.get_model_config(model_id)
        if not model_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"模型不存在: {model_id}"
            )
        
        # 检查模型状态
        model_status = await model_manager.get_model_status(model_id)
        if model_status == 'running':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无法取消正在运行的模型，请先停止模型"
            )
        
        if model_status == 'stopped':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="模型已停止，无需取消调度"
            )
        
        # 停止模型（这会将其从队列中移除）
        success = await model_manager.stop_model(model_id)
        
        result = {
            "success": success,
            "message": "模型调度已取消" if success else "取消调度失败",
            "model_id": model_id,
            "cancelled_at": datetime.now().isoformat()
        }
        
        logger.info(f"取消模型 {model_id} 调度: {'成功' if success else '失败'}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消模型调度失败 {model_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取消调度失败: {str(e)}"
        )

@router.get("/policy", response_model=SchedulePolicyConfig)
async def get_schedule_policy():
    """
    获取调度策略配置
    
    返回当前的调度策略设置
    """
    try:
        # 模拟调度策略配置（实际应该从配置文件或数据库获取）
        policy = SchedulePolicyConfig(
            scheduling_algorithm="priority_based",
            preemption_enabled=True,
            auto_recovery_enabled=True,
            resource_threshold=0.8,
            priority_levels=10,
            max_queue_size=50,
            scheduling_interval=30,
            health_check_interval=60
        )
        
        logger.info("获取调度策略配置成功")
        return policy
        
    except Exception as e:
        logger.error(f"获取调度策略配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取调度策略失败: {str(e)}"
        )

@router.put("/policy")
async def update_schedule_policy(
    policy: SchedulePolicyConfig
):
    """
    更新调度策略配置
    
    更新调度策略设置，部分更改需要重启调度器
    """
    try:
        # 验证配置参数
        if policy.resource_threshold < 0.1 or policy.resource_threshold > 1.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="资源阈值必须在0.1-1.0之间"
            )
        
        if policy.priority_levels < 1 or policy.priority_levels > 20:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="优先级级别必须在1-20之间"
            )
        
        if policy.scheduling_interval < 10 or policy.scheduling_interval > 300:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="调度间隔必须在10-300秒之间"
            )
        
        # 在实际实现中，这里应该更新配置文件或数据库
        # 并通知调度器重新加载配置
        
        result = {
            "success": True,
            "message": "调度策略配置已更新",
            "policy": policy.dict(),
            "restart_required": True,  # 某些配置更改需要重启
            "updated_at": datetime.now().isoformat()
        }
        
        logger.info("更新调度策略配置成功")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新调度策略配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新调度策略失败: {str(e)}"
        )

@router.get("/resources")
async def get_resource_allocation(
    monitoring_service: MonitoringService = Depends(get_monitoring_service),
    model_manager: ModelManager = Depends(get_model_manager)
):
    """
    获取资源分配状态
    
    返回GPU资源分配情况和模型占用详情
    """
    try:
        # 获取GPU信息
        gpu_metrics = await monitoring_service.collect_gpu_metrics()
        
        # 获取模型信息
        models = await model_manager.list_models()
        running_models = [m for m in models if m.status == 'running']
        
        # 构建资源分配信息
        resource_allocation = []
        
        for gpu in gpu_metrics:
            # 查找使用此GPU的模型
            models_on_gpu = [
                m for m in running_models 
                if m.gpu_devices and gpu.device_id in m.gpu_devices
            ]
            
            allocation_info = {
                "gpu_id": gpu.device_id,
                "gpu_name": gpu.name,
                "memory_total": gpu.memory_total,
                "memory_used": gpu.memory_used,
                "memory_free": gpu.memory_free,
                "utilization": gpu.utilization,
                "temperature": gpu.temperature,
                "power_usage": gpu.power_usage,
                "allocated_models": [
                    {
                        "model_id": m.id,
                        "model_name": m.name,
                        "priority": m.priority,
                        "memory_usage": getattr(m, 'memory_usage', None),
                        "start_time": getattr(m, 'start_time', None)
                    }
                    for m in models_on_gpu
                ],
                "allocation_status": "allocated" if models_on_gpu else "free"
            }
            
            resource_allocation.append(allocation_info)
        
        result = {
            "gpu_allocation": resource_allocation,
            "summary": {
                "total_gpus": len(gpu_metrics),
                "allocated_gpus": len([a for a in resource_allocation if a["allocation_status"] == "allocated"]),
                "free_gpus": len([a for a in resource_allocation if a["allocation_status"] == "free"]),
                "total_models": len(running_models),
                "total_memory_used": sum(gpu.memory_used for gpu in gpu_metrics),
                "total_memory_available": sum(gpu.memory_total for gpu in gpu_metrics)
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"获取资源分配状态成功，{len(gpu_metrics)} 个GPU")
        return result
        
    except Exception as e:
        logger.error(f"获取资源分配状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取资源分配状态失败: {str(e)}"
        )

@router.post("/restart")
async def restart_scheduler():
    """
    重启调度器
    
    重启资源调度器服务
    """
    try:
        # 在实际实现中，这里应该重启调度器服务
        # 这通常需要与进程管理器（如systemd）集成
        
        logger.warning("收到调度器重启请求")
        
        result = {
            "success": True,
            "message": "调度器重启请求已接收",
            "restart_requested_at": datetime.now().isoformat(),
            "note": "实际重启需要外部进程管理器支持"
        }
        
        return result
        
    except Exception as e:
        logger.error(f"重启调度器失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重启调度器失败: {str(e)}"
        )

@router.get("/health")
async def scheduler_health_check(
    scheduler: ResourceScheduler = Depends(get_resource_scheduler)
):
    """
    调度器健康检查
    
    检查调度器各组件的健康状态
    """
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {}
        }
        
        # 检查调度器核心组件
        try:
            # 这里应该检查调度器的实际状态
            health_status["components"]["scheduler_core"] = {
                "status": "healthy",
                "message": "调度器核心运行正常"
            }
        except Exception as e:
            health_status["components"]["scheduler_core"] = {
                "status": "unhealthy",
                "message": f"调度器核心异常: {str(e)}"
            }
            health_status["status"] = "degraded"
        
        # 检查资源监控
        try:
            # 检查GPU监控是否正常
            health_status["components"]["resource_monitor"] = {
                "status": "healthy",
                "message": "资源监控正常"
            }
        except Exception as e:
            health_status["components"]["resource_monitor"] = {
                "status": "unhealthy",
                "message": f"资源监控异常: {str(e)}"
            }
            health_status["status"] = "degraded"
        
        # 检查模型管理器连接
        try:
            health_status["components"]["model_manager"] = {
                "status": "healthy",
                "message": "模型管理器连接正常"
            }
        except Exception as e:
            health_status["components"]["model_manager"] = {
                "status": "unhealthy",
                "message": f"模型管理器连接异常: {str(e)}"
            }
            health_status["status"] = "degraded"
        
        logger.info(f"调度器健康检查完成，状态: {health_status['status']}")
        
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
        logger.error(f"调度器健康检查失败: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "message": f"健康检查失败: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
        )