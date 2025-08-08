"""
系统监控API端点
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, timedelta

from ..services.monitoring import MonitoringService
from ..models.schemas import (
    GPUMetrics, SystemOverview, Metrics, TimeRange, AlertRule
)
from ..models.enums import HealthStatus
from ..core.dependencies import get_monitoring_service

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

@router.get("/system")
async def get_system_status(
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """获取系统状态概览"""
    try:
        overview = await monitoring_service.get_system_overview()
        gpu_metrics = await monitoring_service.collect_gpu_metrics()
        
        # 将SystemOverview转换为字典并添加gpu_metrics和system_metrics
        result = overview.model_dump()
        result["gpu_metrics"] = [metric.model_dump() for metric in gpu_metrics]
        
        # 添加系统指标
        try:
            system_metrics = await monitoring_service.system_collector.collect_metrics()
            result["system_metrics"] = {
                "cpu_percent": system_metrics.cpu_usage,
                "memory_percent": system_metrics.memory_usage,
                "disk_percent": system_metrics.disk_usage
            }
        except Exception:
            # 如果系统指标收集失败，提供默认值
            result["system_metrics"] = {
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "disk_percent": 0.0
            }
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统状态失败: {str(e)}")

@router.get("/gpu", response_model=List[GPUMetrics])
async def get_gpu_metrics(
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """获取GPU资源指标"""
    try:
        metrics = await monitoring_service.collect_gpu_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取GPU指标失败: {str(e)}")

@router.get("/metrics/system")
async def get_system_metrics(
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """获取系统资源指标"""
    try:
        # 获取最新的系统指标
        system_metrics = await monitoring_service.system_collector.collect_metrics()
        return {
            "timestamp": system_metrics.timestamp,
            "cpu_usage": system_metrics.cpu_usage,
            "memory_usage": system_metrics.memory_usage,
            "memory_total": system_metrics.memory_total,
            "memory_used": system_metrics.memory_used,
            "disk_usage": system_metrics.disk_usage,
            "disk_total": system_metrics.disk_total,
            "disk_used": system_metrics.disk_used,
            "network_sent": system_metrics.network_sent,
            "network_recv": system_metrics.network_recv,
            "load_average": system_metrics.load_average
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统指标失败: {str(e)}")

@router.get("/models/{model_id}/health")
async def check_model_health(
    model_id: str,
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """检查模型健康状态"""
    try:
        health_status = await monitoring_service.check_model_health(model_id)
        return {
            "model_id": model_id,
            "health_status": health_status,
            "timestamp": datetime.now()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检查模型健康状态失败: {str(e)}")

@router.get("/models/{model_id}/metrics", response_model=Metrics)
async def get_model_performance_metrics(
    model_id: str,
    hours: int = Query(1, description="获取过去几小时的数据"),
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """获取模型性能指标"""
    try:
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        time_range = TimeRange(start_time=start_time, end_time=end_time)
        
        metrics = await monitoring_service.get_performance_metrics(model_id, time_range)
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模型性能指标失败: {str(e)}")

@router.get("/alerts/active")
async def get_active_alerts(
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """获取活跃告警"""
    try:
        alerts = monitoring_service.get_active_alerts()
        return [
            {
                "id": alert.id,
                "rule_id": alert.rule_id,
                "level": alert.level,
                "message": alert.message,
                "timestamp": alert.timestamp,
                "resolved": alert.resolved
            }
            for alert in alerts
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取活跃告警失败: {str(e)}")

@router.get("/alerts/history")
async def get_alert_history(
    limit: int = Query(100, description="返回的告警数量限制"),
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """获取告警历史"""
    try:
        alerts = monitoring_service.get_alert_history(limit)
        return [
            {
                "id": alert.id,
                "rule_id": alert.rule_id,
                "level": alert.level,
                "message": alert.message,
                "timestamp": alert.timestamp,
                "resolved": alert.resolved,
                "resolved_at": alert.resolved_at
            }
            for alert in alerts
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取告警历史失败: {str(e)}")

@router.post("/alerts/rules")
async def setup_alert_rules(
    rules: List[AlertRule],
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """设置告警规则"""
    try:
        success = await monitoring_service.setup_alerts(rules)
        if success:
            return {"message": f"成功设置 {len(rules)} 个告警规则"}
        else:
            raise HTTPException(status_code=500, detail="设置告警规则失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置告警规则失败: {str(e)}")

@router.post("/start")
async def start_monitoring(
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """启动监控服务"""
    try:
        await monitoring_service.start_monitoring()
        return {"message": "监控服务已启动"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动监控服务失败: {str(e)}")

@router.post("/stop")
async def stop_monitoring(
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """停止监控服务"""
    try:
        await monitoring_service.stop_monitoring()
        return {"message": "监控服务已停止"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止监控服务失败: {str(e)}")

@router.post("/models/{model_id}/request")
async def record_model_request(
    model_id: str,
    response_time: float,
    success: bool = True,
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """记录模型请求指标"""
    try:
        monitoring_service.record_model_request(model_id, response_time, success)
        return {"message": "请求指标已记录"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"记录请求指标失败: {str(e)}")

# 历史数据查询接口
@router.get("/gpu/history")
async def get_gpu_metrics_history(
    device_id: Optional[int] = Query(None, description="GPU设备ID"),
    hours: int = Query(24, description="获取过去几小时的数据"),
    limit: int = Query(1000, description="返回记录数限制"),
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """获取GPU指标历史数据"""
    try:
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        time_range = TimeRange(start_time=start_time, end_time=end_time)
        
        metrics = await monitoring_service.get_gpu_metrics_history(device_id, time_range, limit)
        return [
            {
                "device_id": metric.device_id,
                "timestamp": metric.timestamp,
                "utilization": metric.utilization,
                "memory_used": metric.memory_used,
                "memory_total": metric.memory_total,
                "temperature": metric.temperature,
                "power_usage": metric.power_usage
            }
            for metric in metrics
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取GPU历史数据失败: {str(e)}")

@router.get("/models/{model_id}/history")
async def get_model_metrics_history(
    model_id: str,
    hours: int = Query(24, description="获取过去几小时的数据"),
    limit: int = Query(1000, description="返回记录数限制"),
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """获取模型性能指标历史数据"""
    try:
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        time_range = TimeRange(start_time=start_time, end_time=end_time)
        
        metrics = await monitoring_service.get_model_metrics_history(model_id, time_range, limit)
        return [
            {
                "model_id": metric.model_id,
                "timestamp": metric.timestamp,
                "request_count": metric.request_count,
                "total_response_time": metric.total_response_time,
                "error_count": metric.error_count,
                "active_connections": metric.active_connections,
                "memory_usage": metric.memory_usage,
                "cpu_usage": metric.cpu_usage,
                "gpu_utilization": metric.gpu_utilization
            }
            for metric in metrics
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模型历史数据失败: {str(e)}")

@router.get("/system/history")
async def get_system_metrics_history(
    hours: int = Query(24, description="获取过去几小时的数据"),
    limit: int = Query(1000, description="返回记录数限制"),
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """获取系统资源指标历史数据"""
    try:
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        time_range = TimeRange(start_time=start_time, end_time=end_time)
        
        metrics = await monitoring_service.get_system_metrics_history(time_range, limit)
        return [
            {
                "timestamp": metric.timestamp,
                "cpu_usage": metric.cpu_usage,
                "memory_usage": metric.memory_usage,
                "memory_total": metric.memory_total,
                "memory_used": metric.memory_used,
                "disk_usage": metric.disk_usage,
                "disk_total": metric.disk_total,
                "disk_used": metric.disk_used,
                "network_sent": metric.network_sent,
                "network_recv": metric.network_recv,
                "load_average": metric.load_average
            }
            for metric in metrics
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统历史数据失败: {str(e)}")

# 数据聚合和趋势分析接口
@router.get("/gpu/{device_id}/trend")
async def get_gpu_utilization_trend(
    device_id: int,
    hours: int = Query(24, description="获取过去几小时的数据"),
    interval_minutes: int = Query(5, description="聚合时间间隔(分钟)"),
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """获取GPU利用率趋势"""
    try:
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        time_range = TimeRange(start_time=start_time, end_time=end_time)
        
        trend_data = await monitoring_service.get_gpu_utilization_trend(
            device_id, time_range, interval_minutes
        )
        return trend_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取GPU趋势数据失败: {str(e)}")

@router.get("/system/trend")
async def get_system_resource_trend(
    hours: int = Query(24, description="获取过去几小时的数据"),
    interval_minutes: int = Query(5, description="聚合时间间隔(分钟)"),
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """获取系统资源使用趋势"""
    try:
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        time_range = TimeRange(start_time=start_time, end_time=end_time)
        
        trend_data = await monitoring_service.get_system_resource_trend(
            time_range, interval_minutes
        )
        return trend_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统趋势数据失败: {str(e)}")

@router.get("/models/top")
async def get_top_models_by_requests(
    hours: int = Query(24, description="获取过去几小时的数据"),
    limit: int = Query(10, description="返回模型数量限制"),
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """获取请求量最高的模型"""
    try:
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        time_range = TimeRange(start_time=start_time, end_time=end_time)
        
        top_models = await monitoring_service.get_top_models_by_requests(time_range, limit)
        return top_models
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取热门模型数据失败: {str(e)}")

# 数据管理接口
@router.post("/cleanup")
async def cleanup_old_metrics(
    retention_days: int = Query(30, description="保留天数"),
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """清理过期的历史数据"""
    try:
        deleted_counts = await monitoring_service.cleanup_old_metrics(retention_days)
        return {
            "message": f"成功清理 {retention_days} 天前的历史数据",
            "deleted_counts": deleted_counts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理历史数据失败: {str(e)}")

@router.get("/storage/stats")
async def get_storage_stats(
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    """获取存储统计信息"""
    try:
        stats = await monitoring_service.get_storage_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取存储统计信息失败: {str(e)}")