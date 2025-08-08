#!/usr/bin/env python3
"""
框架适配器使用示例
"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.adapters import FrameworkAdapterFactory
from app.models.enums import FrameworkType
from app.models.schemas import ModelConfig, ResourceRequirement, HealthCheckConfig, RetryPolicy

async def demo_llama_cpp_adapter():
    """演示llama.cpp适配器使用"""
    print("=== llama.cpp适配器演示 ===")
    
    # 创建适配器
    adapter = FrameworkAdapterFactory.create_adapter(FrameworkType.LLAMA_CPP)
    print(f"创建适配器: {adapter.__class__.__name__}")
    
    # 创建模型配置
    config = ModelConfig(
        id="llama-demo",
        name="Llama演示模型",
        framework=FrameworkType.LLAMA_CPP,
        model_path="/path/to/model.gguf",  # 实际使用时需要真实路径
        priority=5,
        gpu_devices=[0],
        parameters={
            'port': 8080,
            'host': '127.0.0.1',
            'ctx_size': 2048,
            'n_gpu_layers': 32,
            'temperature': 0.8,
            'gpu_vendor': 'nvidia'  # 或 'amd'
        },
        resource_requirements=ResourceRequirement(
            gpu_memory=4096,
            gpu_devices=[0]
        ),
        health_check=HealthCheckConfig(
            enabled=True,
            interval=30,
            timeout=10
        ),
        retry_policy=RetryPolicy(
            enabled=True,
            max_attempts=3
        )
    )
    
    # 验证配置
    validation_result = adapter.validate_config(config)
    print(f"配置验证结果: {'有效' if validation_result.is_valid else '无效'}")
    if validation_result.errors:
        print(f"错误: {validation_result.errors}")
    if validation_result.warnings:
        print(f"警告: {validation_result.warnings}")
    
    # 获取默认参数
    defaults = adapter.get_default_parameters()
    print(f"默认参数: {defaults}")
    
    # 获取API端点（模拟）
    endpoint = await adapter.get_api_endpoint("llama-demo")
    print(f"API端点: {endpoint}")

async def demo_vllm_adapter():
    """演示vLLM适配器使用"""
    print("\n=== vLLM适配器演示 ===")
    
    # 创建适配器
    adapter = FrameworkAdapterFactory.create_adapter(FrameworkType.VLLM)
    print(f"创建适配器: {adapter.__class__.__name__}")
    
    # 创建模型配置
    config = ModelConfig(
        id="vllm-demo",
        name="vLLM演示模型",
        framework=FrameworkType.VLLM,
        model_path="microsoft/DialoGPT-medium",  # Hugging Face模型名
        priority=7,
        gpu_devices=[0, 1],
        parameters={
            'port': 8000,
            'host': '0.0.0.0',
            'model_name': 'microsoft/DialoGPT-medium',
            'tensor_parallel_size': 2,
            'gpu_memory_utilization': 0.8,
            'max_model_len': 1024,
            'docker_image': 'vllm/vllm-openai:latest',
            'trust_remote_code': True
        },
        resource_requirements=ResourceRequirement(
            gpu_memory=8192,
            gpu_devices=[0, 1]
        ),
        health_check=HealthCheckConfig(
            enabled=True,
            interval=60,
            timeout=15
        ),
        retry_policy=RetryPolicy(
            enabled=True,
            max_attempts=2
        )
    )
    
    # 验证配置
    validation_result = adapter.validate_config(config)
    print(f"配置验证结果: {'有效' if validation_result.is_valid else '无效'}")
    if validation_result.errors:
        print(f"错误: {validation_result.errors}")
    if validation_result.warnings:
        print(f"警告: {validation_result.warnings}")
    
    # 获取默认参数
    defaults = adapter.get_default_parameters()
    print(f"默认参数: {defaults}")
    
    # 获取API端点（模拟）
    endpoint = await adapter.get_api_endpoint("vllm-demo")
    print(f"API端点: {endpoint}")

async def demo_factory_pattern():
    """演示工厂模式使用"""
    print("\n=== 工厂模式演示 ===")
    
    # 获取支持的框架
    supported_frameworks = FrameworkAdapterFactory.get_supported_frameworks()
    print(f"支持的框架: {supported_frameworks}")
    
    # 检查框架支持
    for framework in [FrameworkType.LLAMA_CPP, FrameworkType.VLLM, "unsupported"]:
        is_supported = FrameworkAdapterFactory.is_framework_supported(framework)
        print(f"框架 {framework} 支持状态: {is_supported}")
    
    # 动态创建适配器
    for framework_type in supported_frameworks:
        adapter = FrameworkAdapterFactory.create_adapter(framework_type)
        print(f"创建 {framework_type} 适配器: {adapter.__class__.__name__}")

async def main():
    """主函数"""
    print("框架适配器使用示例")
    print("=" * 50)
    
    try:
        await demo_factory_pattern()
        await demo_llama_cpp_adapter()
        await demo_vllm_adapter()
        
        print("\n演示完成！")
        
    except Exception as e:
        print(f"演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())