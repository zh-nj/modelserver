"""
API代理管理端点
实现模型API请求转发、负载均衡配置和代理统计查询
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query, Request, Response, status
from fastapi.responses import StreamingResponse
import json

from ..services.api_proxy import APIProxyService, RequestMetrics
from ..core.dependencies import get_proxy_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/proxy", tags=["proxy"])

@router.get("/targets")
async def get_proxy_targets(
    model_id: Optional[str] = Query(None, description="模型ID过滤"),
    proxy_service: APIProxyService = Depends(get_proxy_service)
):
    """
    获取代理目标列表
    
    返回当前配置的所有代理目标信息，包括健康状态和统计数据
    """
    try:
        targets = proxy_service.get_proxy_targets(model_id)
        
        # 转换为可序列化的格式
        result = {}
        for mid, target_list in targets.items():
            result[mid] = []
            for target in target_list:
                target_info = {
                    "model_id": target.model_id,
                    "endpoint": target.endpoint,
                    "framework": target.framework,
                    "priority": target.priority,
                    "weight": target.weight,
                    "active": target.active,
                    "last_health_check": target.last_health_check.isoformat() if target.last_health_check else None,
                    "consecutive_failures": target.consecutive_failures,
                    "total_requests": target.total_requests,
                    "total_response_time": target.total_response_time,
                    "error_count": target.error_count,
                    "average_response_time": (
                        target.total_response_time / target.total_requests 
                        if target.total_requests > 0 else 0.0
                    )
                }
                result[mid].append(target_info)
        
        logger.info(f"获取代理目标成功，共 {len(result)} 个模型")
        return {
            "targets": result,
            "total_models": len(result),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取代理目标失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取代理目标失败: {str(e)}"
        )

@router.get("/stats")
async def get_proxy_stats(
    proxy_service: APIProxyService = Depends(get_proxy_service)
):
    """
    获取代理统计信息
    
    返回所有模型的代理统计数据，包括请求数、响应时间、错误率等
    """
    try:
        stats = proxy_service.get_target_stats()
        
        # 计算总体统计
        total_stats = {
            "total_models": len(stats),
            "total_targets": sum(model_stats["total_targets"] for model_stats in stats.values()),
            "active_targets": sum(model_stats["active_targets"] for model_stats in stats.values()),
            "total_requests": 0,
            "total_errors": 0,
            "average_response_time": 0.0
        }
        
        total_response_time = 0.0
        total_request_count = 0
        
        for model_stats in stats.values():
            for target_stats in model_stats["targets"]:
                total_stats["total_requests"] += target_stats["total_requests"]
                total_stats["total_errors"] += target_stats["error_count"]
                total_response_time += target_stats["average_response_time"] * target_stats["total_requests"]
                total_request_count += target_stats["total_requests"]
        
        if total_request_count > 0:
            total_stats["average_response_time"] = total_response_time / total_request_count
            total_stats["error_rate"] = (total_stats["total_errors"] / total_stats["total_requests"]) * 100
        else:
            total_stats["error_rate"] = 0.0
        
        logger.info("获取代理统计信息成功")
        return {
            "summary": total_stats,
            "models": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取代理统计信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取代理统计信息失败: {str(e)}"
        )

@router.get("/models/{model_id}/stats")
async def get_model_proxy_stats(
    model_id: str,
    hours: int = Query(24, description="统计时间范围(小时)"),
    proxy_service: APIProxyService = Depends(get_proxy_service)
):
    """
    获取指定模型的代理统计
    
    返回指定模型在指定时间范围内的详细统计信息
    """
    try:
        stats = proxy_service.get_request_stats(model_id, hours)
        
        logger.info(f"获取模型 {model_id} 代理统计成功")
        return {
            "model_id": model_id,
            "time_range_hours": hours,
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取模型 {model_id} 代理统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模型代理统计失败: {str(e)}"
        )

@router.get("/requests/history")
async def get_request_history(
    model_id: Optional[str] = Query(None, description="模型ID过滤"),
    limit: int = Query(100, description="返回记录数限制"),
    proxy_service: APIProxyService = Depends(get_proxy_service)
):
    """
    获取请求历史记录
    
    返回API代理的请求历史，支持按模型过滤
    """
    try:
        history = proxy_service.get_request_history(model_id, limit)
        
        # 转换为可序列化的格式
        result = []
        for metrics in history:
            record = {
                "model_id": metrics.model_id,
                "timestamp": metrics.timestamp.isoformat(),
                "method": metrics.method,
                "path": metrics.path,
                "status_code": metrics.status_code,
                "response_time": metrics.response_time,
                "request_size": metrics.request_size,
                "response_size": metrics.response_size,
                "client_ip": metrics.client_ip,
                "user_agent": metrics.user_agent
            }
            
            if metrics.error_message:
                record["error_message"] = metrics.error_message
            
            result.append(record)
        
        logger.info(f"获取请求历史成功，返回 {len(result)} 条记录")
        return {
            "requests": result,
            "total_count": len(result),
            "model_id_filter": model_id,
            "limit": limit,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取请求历史失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取请求历史失败: {str(e)}"
        )

@router.put("/load-balance")
async def update_load_balance_strategy(
    strategy: str = Query(..., description="负载均衡策略: round_robin, weighted, least_connections, response_time"),
    proxy_service: APIProxyService = Depends(get_proxy_service)
):
    """
    更新负载均衡策略
    
    支持的策略：
    - round_robin: 轮询
    - weighted: 加权轮询
    - least_connections: 最少连接
    - response_time: 响应时间优先
    """
    try:
        valid_strategies = ["round_robin", "weighted", "least_connections", "response_time"]
        
        if strategy not in valid_strategies:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的负载均衡策略。支持的策略: {', '.join(valid_strategies)}"
            )
        
        proxy_service.update_load_balance_strategy(strategy)
        
        logger.info(f"负载均衡策略更新成功: {strategy}")
        return {
            "success": True,
            "message": "负载均衡策略更新成功",
            "strategy": strategy,
            "updated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新负载均衡策略失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新负载均衡策略失败: {str(e)}"
        )

# 模型API代理端点
@router.api_route("/models/{model_id}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_model_request(
    model_id: str,
    path: str,
    request: Request,
    proxy_service: APIProxyService = Depends(get_proxy_service)
):
    """
    代理模型API请求
    
    将请求转发到指定模型的实际API端点，支持负载均衡和故障转移
    """
    try:
        # 获取请求信息
        method = request.method
        headers = dict(request.headers)
        body = await request.body()
        client_ip = request.client.host if request.client else ""
        user_agent = headers.get("user-agent", "")
        
        # 执行代理请求
        status_code, response_headers, response_body = await proxy_service.proxy_request(
            model_id=model_id,
            method=method,
            path=f"/{path}",
            headers=headers,
            body=body,
            client_ip=client_ip,
            user_agent=user_agent
        )
        
        # 构建响应
        return Response(
            content=response_body,
            status_code=status_code,
            headers=response_headers
        )
        
    except Exception as e:
        logger.error(f"代理模型 {model_id} 请求失败: {e}")
        error_response = {
            "error": f"代理请求失败: {str(e)}",
            "model_id": model_id,
            "path": path,
            "timestamp": datetime.now().isoformat()
        }
        
        return Response(
            content=json.dumps(error_response).encode(),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )

@router.get("/health")
async def proxy_health_check(
    proxy_service: APIProxyService = Depends(get_proxy_service)
):
    """
    代理服务健康检查
    
    检查代理服务本身的健康状态
    """
    try:
        targets = proxy_service.get_proxy_targets()
        total_targets = sum(len(target_list) for target_list in targets.values())
        active_targets = sum(
            sum(1 for target in target_list if target.active) 
            for target_list in targets.values()
        )
        
        health_status = {
            "status": "healthy" if active_targets > 0 else "degraded",
            "total_models": len(targets),
            "total_targets": total_targets,
            "active_targets": active_targets,
            "inactive_targets": total_targets - active_targets,
            "timestamp": datetime.now().isoformat()
        }
        
        if active_targets == 0 and total_targets > 0:
            health_status["status"] = "unhealthy"
            health_status["message"] = "没有活跃的代理目标"
        elif active_targets < total_targets:
            health_status["status"] = "degraded"
            health_status["message"] = f"{total_targets - active_targets} 个目标不可用"
        else:
            health_status["message"] = "所有代理目标正常"
        
        logger.info(f"代理服务健康检查: {health_status['status']}")
        
        # 根据健康状态返回适当的HTTP状态码
        if health_status["status"] == "unhealthy":
            return Response(
                content=json.dumps(health_status).encode(),
                status_code=503,
                headers={"Content-Type": "application/json"}
            )
        else:
            return health_status
        
    except Exception as e:
        logger.error(f"代理服务健康检查失败: {e}")
        error_response = {
            "status": "unhealthy",
            "message": f"健康检查失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
        
        return Response(
            content=json.dumps(error_response).encode(),
            status_code=503,
            headers={"Content-Type": "application/json"}
        )