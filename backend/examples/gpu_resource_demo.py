#!/usr/bin/env python3
"""
GPU资源检测和计算演示脚本
"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.utils.gpu import gpu_detector, gpu_monitor
from app.utils.resource_calculator import resource_calculator
from app.models.schemas import ModelConfig, ResourceRequirement
from app.models.enums import FrameworkType


async def demo_gpu_detection():
    """演示GPU检测功能"""
    print("=== GPU检测演示 ===")
    
    # 检测所有GPU
    gpus = await gpu_detector.detect_gpus()
    
    if not gpus:
        print("未检测到GPU设备")
        return []
    
    print(f"检测到 {len(gpus)} 个GPU设备:")
    for gpu in gpus:
        print(f"  GPU {gpu.device_id}: {gpu.name}")
        print(f"    厂商: {gpu.vendor.value}")
        print(f"    总内存: {gpu.memory_total}MB")
        print(f"    已用内存: {gpu.memory_used}MB")
        print(f"    可用内存: {gpu.memory_free}MB")
        print(f"    利用率: {gpu.utilization:.1f}%")
        print(f"    温度: {gpu.temperature:.1f}°C")
        print(f"    功耗: {gpu.power_usage:.1f}W")
        if gpu.driver_version:
            print(f"    驱动版本: {gpu.driver_version}")
        print()
    
    return gpus


def demo_resource_calculation():
    """演示资源需求计算功能"""
    print("=== 资源需求计算演示 ===")
    
    # 创建示例模型配置
    model_configs = [
        ModelConfig(
            id="llama-7b",
            name="Llama-2-7B-Chat",
            framework=FrameworkType.LLAMA_CPP,
            model_path="/models/llama-2-7b-chat.gguf",
            priority=8,
            gpu_devices=[],
            parameters={
                "model_size_gb": 7.0,
                "precision": "fp16",
                "context_length": 4096,
                "batch_size": 1
            },
            resource_requirements=ResourceRequirement(gpu_memory=1000)
        ),
        ModelConfig(
            id="llama-13b",
            name="Llama-2-13B-Chat",
            framework=FrameworkType.VLLM,
            model_path="/models/llama-2-13b-chat",
            priority=6,
            gpu_devices=[],
            parameters={
                "model_size_gb": 13.0,
                "precision": "fp16",
                "context_length": 4096,
                "batch_size": 2
            },
            resource_requirements=ResourceRequirement(gpu_memory=1000)
        ),
        ModelConfig(
            id="qwen-7b",
            name="Qwen-7B-Chat-Int8",
            framework=FrameworkType.LLAMA_CPP,
            model_path="/models/qwen-7b-chat-q8.gguf",
            priority=5,
            gpu_devices=[],
            parameters={
                "model_size_gb": 7.0,
                "precision": "int8",
                "context_length": 2048,
                "batch_size": 1
            },
            resource_requirements=ResourceRequirement(gpu_memory=1000)
        )
    ]
    
    print("计算模型资源需求:")
    requirements = []
    for config in model_configs:
        req = resource_calculator.calculate_model_memory_requirement(config)
        requirements.append(req)
        
        print(f"  {config.name}:")
        print(f"    框架: {config.framework.value}")
        print(f"    GPU内存需求: {req.gpu_memory}MB")
        print(f"    CPU核心需求: {req.cpu_cores}")
        print(f"    系统内存需求: {req.system_memory}MB")
        print()
    
    return model_configs, requirements


async def demo_resource_allocation(gpus, model_configs, requirements):
    """演示资源分配验证"""
    print("=== 资源分配验证演示 ===")
    
    if not gpus:
        print("没有可用GPU，跳过资源分配演示")
        return
    
    print("验证各模型的资源分配:")
    for i, (config, req) in enumerate(zip(model_configs, requirements)):
        is_valid, errors, allocation = resource_calculator.validate_resource_allocation(
            req, gpus
        )
        
        print(f"  {config.name}:")
        if is_valid and allocation:
            print(f"    ✓ 分配成功")
            print(f"    分配GPU: {allocation.gpu_devices}")
            print(f"    分配内存: {allocation.memory_allocated}MB")
        else:
            print(f"    ✗ 分配失败")
            for error in errors:
                print(f"      错误: {error}")
        print()
    
    # 演示最优分配建议
    print("最优分配建议:")
    allocations = resource_calculator.suggest_optimal_allocation(requirements, gpus)
    
    for req_index, allocation in allocations:
        config = model_configs[req_index]
        print(f"  {config.name}:")
        if allocation:
            print(f"    建议GPU: {allocation.gpu_devices}")
            print(f"    分配内存: {allocation.memory_allocated}MB")
        else:
            print(f"    无法分配")
        print()


def demo_memory_fragmentation(gpus):
    """演示内存碎片化分析"""
    print("=== 内存碎片化分析演示 ===")
    
    if not gpus:
        print("没有可用GPU，跳过碎片化分析")
        return
    
    fragmentation = resource_calculator.calculate_memory_fragmentation(gpus)
    
    print("GPU内存碎片化分析:")
    print(f"  GPU总数: {fragmentation['gpu_count']}")
    print(f"  总内存: {fragmentation['total_memory']}MB")
    print(f"  已用内存: {fragmentation['used_memory']}MB")
    print(f"  可用内存: {fragmentation['free_memory']}MB")
    print(f"  最大可用块: {fragmentation['largest_free_block']}MB")
    print(f"  碎片化比率: {fragmentation['fragmentation_ratio']:.2%}")
    print(f"  平均利用率: {fragmentation['average_utilization']:.1f}%")
    print()


async def demo_gpu_monitoring():
    """演示GPU监控功能"""
    print("=== GPU监控演示 ===")
    
    # 定义监控回调函数
    def on_gpu_metrics_update(metrics):
        print(f"[{len(metrics)}个GPU] 监控更新:")
        for metric in metrics:
            print(f"  GPU {metric.device_id}: "
                  f"利用率={metric.utilization:.1f}%, "
                  f"内存={metric.memory_used}/{metric.memory_total}MB, "
                  f"温度={metric.temperature:.1f}°C")
    
    # 添加监控回调
    gpu_monitor.add_callback(on_gpu_metrics_update)
    
    print("启动GPU监控 (5秒)...")
    await gpu_monitor.start_monitoring()
    
    # 运行5秒
    await asyncio.sleep(5)
    
    await gpu_monitor.stop_monitoring()
    print("GPU监控已停止")
    print()


async def main():
    """主演示函数"""
    print("大语言模型推理服务 - GPU资源检测和管理演示")
    print("=" * 60)
    print()
    
    try:
        # 1. GPU检测演示
        gpus = await demo_gpu_detection()
        
        # 2. 资源需求计算演示
        model_configs, requirements = demo_resource_calculation()
        
        # 3. 资源分配验证演示
        await demo_resource_allocation(gpus, model_configs, requirements)
        
        # 4. 内存碎片化分析演示
        demo_memory_fragmentation(gpus)
        
        # 5. GPU监控演示
        if gpus:  # 只有在有GPU时才演示监控
            await demo_gpu_monitoring()
        
        print("演示完成!")
        
    except KeyboardInterrupt:
        print("\n演示被用户中断")
    except Exception as e:
        print(f"演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())