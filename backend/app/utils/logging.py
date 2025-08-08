"""
结构化日志系统
提供统一的日志记录接口，支持JSON格式、日志轮转和清理机制
"""
import json
import logging
import logging.handlers
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Union
from enum import Enum
import os
import glob

class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class EventType(Enum):
    """事件类型枚举"""
    MODEL_LIFECYCLE = "model_lifecycle"
    RESOURCE_ALLOCATION = "resource_allocation"
    SYSTEM_ERROR = "system_error"
    API_REQUEST = "api_request"
    HEALTH_CHECK = "health_check"
    CONFIGURATION = "configuration"

class StructuredFormatter(logging.Formatter):
    """结构化JSON日志格式器"""
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为JSON格式"""
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # 添加额外的上下文信息
        if hasattr(record, 'event_type'):
            log_entry["event_type"] = record.event_type
        if hasattr(record, 'model_id'):
            log_entry["model_id"] = record.model_id
        if hasattr(record, 'gpu_id'):
            log_entry["gpu_id"] = record.gpu_id
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = record.request_id
        if hasattr(record, 'extra_data'):
            log_entry["extra_data"] = record.extra_data
            
        # 添加异常信息
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
            
        return json.dumps(log_entry, ensure_ascii=False, indent=None)

class LogRotationHandler(logging.handlers.RotatingFileHandler):
    """增强的日志轮转处理器"""
    
    def __init__(self, filename: str, maxBytes: int = 50*1024*1024, 
                 backupCount: int = 10, encoding: str = 'utf-8',
                 cleanup_days: int = 30):
        super().__init__(filename, maxBytes=maxBytes, backupCount=backupCount, encoding=encoding)
        self.cleanup_days = cleanup_days
        
    def doRollover(self):
        """执行日志轮转并清理旧文件"""
        super().doRollover()
        self._cleanup_old_logs()
        
    def _cleanup_old_logs(self):
        """清理超过保留期的日志文件"""
        try:
            log_dir = Path(self.baseFilename).parent
            log_pattern = Path(self.baseFilename).stem + "*"
            cutoff_date = datetime.now() - timedelta(days=self.cleanup_days)
            
            for log_file in glob.glob(str(log_dir / log_pattern)):
                file_path = Path(log_file)
                if file_path.stat().st_mtime < cutoff_date.timestamp():
                    file_path.unlink()
                    
        except Exception as e:
            # 避免日志清理失败影响主程序
            print(f"日志清理失败: {e}")

class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        
    def _log_with_context(self, level: LogLevel, message: str, 
                         event_type: Optional[EventType] = None,
                         model_id: Optional[str] = None,
                         gpu_id: Optional[int] = None,
                         user_id: Optional[str] = None,
                         request_id: Optional[str] = None,
                         extra_data: Optional[Dict[str, Any]] = None,
                         exc_info: bool = False):
        """带上下文信息的日志记录"""
        extra = {}
        if event_type:
            extra['event_type'] = event_type.value
        if model_id:
            extra['model_id'] = model_id
        if gpu_id is not None:
            extra['gpu_id'] = gpu_id
        if user_id:
            extra['user_id'] = user_id
        if request_id:
            extra['request_id'] = request_id
        if extra_data:
            extra['extra_data'] = extra_data
            
        self.logger.log(
            getattr(logging, level.value),
            message,
            extra=extra,
            exc_info=exc_info
        )
    
    def debug(self, message: str, **kwargs):
        """记录调试信息"""
        self._log_with_context(LogLevel.DEBUG, message, **kwargs)
        
    def info(self, message: str, **kwargs):
        """记录一般信息"""
        self._log_with_context(LogLevel.INFO, message, **kwargs)
        
    def warning(self, message: str, **kwargs):
        """记录警告信息"""
        self._log_with_context(LogLevel.WARNING, message, **kwargs)
        
    def error(self, message: str, **kwargs):
        """记录错误信息"""
        self._log_with_context(LogLevel.ERROR, message, exc_info=True, **kwargs)
        
    def critical(self, message: str, **kwargs):
        """记录严重错误信息"""
        self._log_with_context(LogLevel.CRITICAL, message, exc_info=True, **kwargs)
    
    def log_model_event(self, event: str, model_id: str, status: str, 
                       extra_data: Optional[Dict[str, Any]] = None):
        """记录模型生命周期事件"""
        self.info(
            f"模型事件: {event}",
            event_type=EventType.MODEL_LIFECYCLE,
            model_id=model_id,
            extra_data={
                "event": event,
                "status": status,
                **(extra_data or {})
            }
        )
    
    def log_resource_event(self, event: str, gpu_id: int, 
                          extra_data: Optional[Dict[str, Any]] = None):
        """记录资源分配事件"""
        self.info(
            f"资源事件: {event}",
            event_type=EventType.RESOURCE_ALLOCATION,
            gpu_id=gpu_id,
            extra_data={
                "event": event,
                **(extra_data or {})
            }
        )
    
    def log_api_request(self, method: str, path: str, status_code: int,
                       duration: float, request_id: Optional[str] = None,
                       user_id: Optional[str] = None):
        """记录API请求"""
        self.info(
            f"API请求: {method} {path} - {status_code}",
            event_type=EventType.API_REQUEST,
            request_id=request_id,
            user_id=user_id,
            extra_data={
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": duration * 1000
            }
        )

def setup_structured_logging(
    log_dir: str = "logs",
    log_level: str = "INFO",
    max_file_size: int = 50 * 1024 * 1024,  # 50MB
    backup_count: int = 10,
    cleanup_days: int = 30,
    enable_console: bool = True,
    enable_json_format: bool = True
) -> None:
    """配置结构化日志系统"""
    
    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # 创建根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # 清除现有处理器
    root_logger.handlers.clear()
    
    # 选择格式器
    if enable_json_format:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # 控制台处理器
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        if enable_json_format:
            # 控制台使用简化格式
            console_formatter = logging.Formatter(
                fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
        else:
            console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # 主日志文件处理器
    main_log_file = log_path / "application.log"
    main_handler = LogRotationHandler(
        filename=str(main_log_file),
        maxBytes=max_file_size,
        backupCount=backup_count,
        cleanup_days=cleanup_days
    )
    main_handler.setFormatter(formatter)
    root_logger.addHandler(main_handler)
    
    # 错误日志文件处理器
    error_log_file = log_path / "error.log"
    error_handler = LogRotationHandler(
        filename=str(error_log_file),
        maxBytes=max_file_size,
        backupCount=backup_count,
        cleanup_days=cleanup_days
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)
    
    # 模型事件日志文件处理器
    model_log_file = log_path / "model_events.log"
    model_handler = LogRotationHandler(
        filename=str(model_log_file),
        maxBytes=max_file_size,
        backupCount=backup_count,
        cleanup_days=cleanup_days
    )
    model_handler.addFilter(lambda record: hasattr(record, 'event_type') and 
                           record.event_type == EventType.MODEL_LIFECYCLE.value)
    model_handler.setFormatter(formatter)
    root_logger.addHandler(model_handler)
    
    # 设置第三方库的日志级别
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

def get_structured_logger(name: str) -> StructuredLogger:
    """获取结构化日志记录器"""
    return StructuredLogger(name)

def get_logger(name: str) -> logging.Logger:
    """获取标准日志记录器（向后兼容）"""
    return logging.getLogger(name)