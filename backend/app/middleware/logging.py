"""
日志中间件
自动记录API请求和响应信息
"""
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from ..utils.logging import get_structured_logger

logger = get_structured_logger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """API请求日志中间件"""
    
    def __init__(self, app, skip_paths: list = None):
        super().__init__(app)
        self.skip_paths = skip_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并记录日志"""
        # 生成请求ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # 跳过不需要记录的路径
        if any(request.url.path.startswith(path) for path in self.skip_paths):
            return await call_next(request)
        
        # 记录请求开始时间
        start_time = time.time()
        
        # 记录请求信息
        logger.info(
            f"API请求开始: {request.method} {request.url.path}",
            request_id=request_id,
            extra_data={
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent")
            }
        )
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 计算处理时间
            duration = time.time() - start_time
            
            # 记录响应信息
            logger.log_api_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration=duration,
                request_id=request_id
            )
            
            # 添加请求ID到响应头
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # 记录异常
            duration = time.time() - start_time
            logger.error(
                f"API请求异常: {request.method} {request.url.path}",
                request_id=request_id,
                extra_data={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration * 1000,
                    "error": str(e)
                }
            )
            raise