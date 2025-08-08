"""
框架适配器模块
"""
from .base import BaseFrameworkAdapter, FrameworkAdapterFactory, register_adapter
from .llama_cpp import LlamaCppAdapter
from .vllm import VllmAdapter

# 导入适配器会自动注册到工厂类中
__all__ = [
    'BaseFrameworkAdapter',
    'FrameworkAdapterFactory', 
    'register_adapter',
    'LlamaCppAdapter',
    'VllmAdapter'
]