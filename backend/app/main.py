"""
LLM推理服务 - FastAPI应用程序入口
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import models, monitoring, system, proxy, config, websocket, alerts
from .core.config import settings
from .core.dependencies import initialize_services, shutdown_services
from .middleware.logging import LoggingMiddleware
from .utils.logging import setup_structured_logging, get_structured_logger, EventType

# 初始化结构化日志系统
setup_structured_logging(
    log_dir=getattr(settings, 'log_dir', 'logs'),
    log_level=getattr(settings, 'log_level', 'INFO'),
    enable_json_format=getattr(settings, 'enable_json_logs', True)
)

logger = get_structured_logger(__name__)

app = FastAPI(
    title="LLM推理服务",
    description="大语言模型推理管理和监控服务",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加日志中间件
app.add_middleware(LoggingMiddleware)

# 注册API路由
app.include_router(models.router)
app.include_router(monitoring.router)
app.include_router(system.router)
app.include_router(proxy.router)
app.include_router(config.router)
app.include_router(websocket.router)
app.include_router(alerts.router)

# 添加兼容性路由（无版本前缀）
from fastapi import APIRouter, Depends
from .core.dependencies import get_monitoring_service

compat_router = APIRouter(prefix="/system", tags=["system-compat"])

@compat_router.get("/overview")
async def get_system_overview_compat(
    monitoring_service = Depends(get_monitoring_service)
):
    """获取系统概览（兼容性端点）"""
    try:
        overview = await monitoring_service.get_system_overview()
        return overview
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"获取系统概览失败: {str(e)}")

app.include_router(compat_router)

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    try:
        logger.info("正在启动LLM推理服务...", 
                   event_type=EventType.CONFIGURATION,
                   extra_data={"action": "startup"})
        await initialize_services()
        logger.info("LLM推理服务启动完成",
                   event_type=EventType.CONFIGURATION,
                   extra_data={"action": "startup_complete"})
    except Exception as e:
        logger.error(f"启动LLM推理服务失败: {e}",
                    event_type=EventType.SYSTEM_ERROR,
                    extra_data={"action": "startup_failed", "error": str(e)})
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    try:
        logger.info("正在关闭LLM推理服务...",
                   event_type=EventType.CONFIGURATION,
                   extra_data={"action": "shutdown"})
        await shutdown_services()
        logger.info("LLM推理服务关闭完成",
                   event_type=EventType.CONFIGURATION,
                   extra_data={"action": "shutdown_complete"})
    except Exception as e:
        logger.error(f"关闭LLM推理服务失败: {e}",
                    event_type=EventType.SYSTEM_ERROR,
                    extra_data={"action": "shutdown_failed", "error": str(e)})

@app.get("/")
async def root():
    """根端点"""
    return {"message": "LLM推理服务正在运行"}

@app.get("/health")
async def health_check():
    """健康检查端点"""
    from datetime import datetime
    return {
        "status": "healthy", 
        "service": "llm-inference-service",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }