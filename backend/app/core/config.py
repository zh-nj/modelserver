"""
应用程序配置管理
"""
from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    """应用程序设置"""
    
    # 应用程序基本配置
    app_name: str = "LLM推理服务"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # 数据库配置
    database_url: str = "mysql+pymysql://root:@127.0.0.1:4000/llm_inference?charset=utf8mb4"
    
    # Redis配置
    redis_url: str = "redis://localhost:6379"
    
    # API配置
    api_prefix: str = "/api"
    cors_origins: str = "*"
    
    # GPU监控配置
    gpu_check_interval: int = 5  # 秒
    health_check_interval: int = 30  # 秒
    
    # 日志配置
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    # 模型配置
    default_model_timeout: int = 300  # 秒
    max_concurrent_models: int = 10
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略额外的环境变量

# 全局设置实例
settings = Settings()