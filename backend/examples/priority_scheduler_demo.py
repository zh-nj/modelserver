#!/usr/bin/env python3
"""
优先级调度算法演示脚本

展示基于优先级的资源分配和抢占机制的工作原理
"""
import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import List

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from backend.app.services.resource_scheduler import PriorityResourceScheduler
from backend.app.models.schemas import (
    ModelConfig, GPUInfo, ResourceRequirement
)
from backend.app.models.enums import (
    FrameworkType, ModelStatus, GPUVendor, ScheduleResult
)


class SchedulerDemo:
    """调度器演示类"""
    
    def __init__(self):
        self.scheduler = PriorityResourceScheduler()
        self.logger = logging.getLogger(__name__)
    
    def create_sample_models(self) -> List[ModelConfig]:
        """创建示例模型配置"""
        models = [
            ModelConfig(
                id="critical_model",
                name="关键业务模型",
                framework=FrameworkType.VLLM,
                model_path="/models/critical_llama_70b.safetensors",
                priority=10,  # 最高优先级
                gpu_devices=[0, 1],
                parameters={
                    "model_size_gb": 70.0,
                    "precision": "fp16",
                    "max_seq_len": 4096,
                    "tensor_parallel_size": 2
                },
                resource_requirements=ResourceRequirement(
                    gpu_memory=40960,  # 40GB
                    gpu_devices=[0, 1]
                )
            ),
            ModelConfig(
                id="production_model",
                name="生产环境模型",
                framework=FrameworkType.LLAMA_CPP,
                model_path="/models/production_llama_13b.gguf",
                priority=8,  # 高优先级
                gpu_devices=[0],
                parameters={
                    "model_size_gb": 13.0,
                    "precision": "fp16",
                    "n_ctx": 2048
                },
                resource_requirements=ResourceRequirement(
                    gpu_memory=16384,  # 16GB
                    gpu_devices=[0]
                )
            ),
            ModelConfig(
                id="dev_model",
                name="开发测试模型",
                framework=FrameworkType.LLAMA_CPP,
                model_path="/models/dev_llama_7b.gguf",
                priority=5,  # 中等优先级
                gpu_devices=[1],
                parameters={
                    "model_size_gb": 7.0,
                    "precision": "fp16",
                    "n_ctx": 2048
                },
                resource_requirements=ResourceRequirement(
                    gpu_memory=10240,  # 10GB
                    gpu_devices=[1]
                )
            ),
            ModelConfig(
                id="experimental_model",
                name="实验性模型",
                framework=FrameworkType.VLLM,
                model_path="/models/experimental_model",
                priority=3,  # 较低优先级
                gpu_devices=[0],
                parameters={
                    "model_size_gb": 30.0,
                    "precision": "int8",
                    "max_seq_len": 1024
                },
                resource_requirements=ResourceRequirement(
                    gpu_memory=12288,  # 12GB
                    gpu_devices=[0]
                )
            ),
            ModelConfig(
                id="background_model",
                name="后台处理模型",
                framework=FrameworkType.LLAMA_CPP,
                model_path="/models/background_model.gguf",
                priority=1,  # 最低优先级
                gpu_devices=[1],
                parameters={
                    "model_size_gb": 3.0,
                    "precision": "int4",
                    "n_ctx": 512
                },
                resource_requirements=ResourceRequirement(
                    gpu_memory=4096,  # 4GB
                    gpu_devices=[1]
                )
            )
        ]
        return models
    
    def create_sample_gpu_info(self) -> List[GPUInfo]:
        """创建示例GPU信息"""
        return [
            GPUInfo(
                device_id=0,
                name="NVIDIA RTX 4090",
                vendor=GPUVendor.NVIDIA,
                memory_total=24576,  # 24GB
                memory_used=0,
                memory_free=24576,
                utilization=0.0,
                temperature=45.0,
                power_usage=50.0,
                driver_version="535.86.10"
            ),
            GPUInfo(
                device_id=1,
                name="NVIDIA RTX 4090",
                vendor=GPUVendor.NVIDIA,
                memory_total=24576,  # 24GB
                memory_used=0,
                memory_free=24576,
                utilization=0.0,
                temperature=42.0,
                power_usage=45.0,
                driver_version="535.86.10"
            )
        ]
    
    def print_gpu_status(self, gpu_info: List[GPUInfo], title: str = "GPU状态"):
        """打印GPU状态"""
        print(f"\n=== {title} ===")
        for gpu in gpu_info:
            usage_percent = (gpu.memory_used / gpu.memory_total) * 100
            print(f"GPU {gpu.device_id}: {gpu.name}")
            print(f"  内存: {gpu.memory_used}MB / {gpu.memory_total}MB ({usage_percent:.1f}%)")
            print(f"  可用: {gpu.memory_free}MB")
            print(f"  利用率: {gpu.utilization:.1f}%")
            print(f"  温度: {gpu.temperature:.1f}°C")
    
    def print_model_status(self, title: str = "模型状态"):
        """打印模型状态"""
        print(f"\n=== {title} ===")
        model_states = self.scheduler.get_model_states()
        
        # 按优先级排序
        sorted_models = sorted(
            model_states.items(),
            key=lambda x: x[1].config.priority,
            reverse=True
        )
        
        for model_id, state in sorted_models:
            status_icon = {
                ModelStatus.STOPPED: "⏹️",
                ModelStatus.STARTING: "🔄",
                ModelStatus.RUNNING: "✅",
                ModelStatus.ERROR: "❌",
                ModelStatus.STOPPING: "⏸️",
                ModelStatus.PREEMPTED: "⚠️"
            }.get(state.status, "❓")
            
            print(f"{status_icon} {state.config.name} (优先级: {state.config.priority})")
            print(f"   状态: {state.status.value}")
            if state.allocated_resources:
                print(f"   GPU: {state.allocated_resources.gpu_devices}")
                print(f"   内存: {state.allocated_resources.memory_allocated}MB")
            if state.preemption_count > 0:
                print(f"   被抢占次数: {state.preemption_count}")
    
    def print_schedule_history(self, limit: int = 5):
        """打印调度历史"""
        print(f"\n=== 最近{limit}次调度决策 ===")
        history = self.scheduler.get_schedule_history(limit)
        
        for i, decision in enumerate(reversed(history), 1):
            result_icon = {
                ScheduleResult.SUCCESS: "✅",
                ScheduleResult.INSUFFICIENT_RESOURCES: "❌",
                ScheduleResult.PREEMPTION_REQUIRED: "⚠️",
                ScheduleResult.FAILED: "💥"
            }.get(decision.result, "❓")
            
            print(f"{i}. {result_icon} 模型: {decision.model_id}")
            print(f"   时间: {decision.decision_time.strftime('%H:%M:%S')}")
            print(f"   结果: {decision.result.value}")
            print(f"   原因: {decision.reason}")
            if decision.preempted_models:
                print(f"   抢占模型: {decision.preempted_models}")
    
    async def simulate_gpu_usage(self, gpu_info: List[GPUInfo], model_states: dict):
        """模拟GPU使用情况"""
        for gpu in gpu_info:
            gpu.memory_used = 0
            gpu.memory_free = gpu.memory_total
            gpu.utilization = 0.0
        
        # 根据模型分配情况更新GPU状态
        for model_id, state in model_states.items():
            if state.status == ModelStatus.RUNNING and state.allocated_resources:
                for gpu_id in state.allocated_resources.gpu_devices:
                    gpu = next((g for g in gpu_info if g.device_id == gpu_id), None)
                    if gpu:
                        # 简化计算：假设内存平均分配到所有GPU
                        memory_per_gpu = state.allocated_resources.memory_allocated // len(state.allocated_resources.gpu_devices)
                        gpu.memory_used += memory_per_gpu
                        gpu.memory_free = gpu.memory_total - gpu.memory_used
                        gpu.utilization = min(100.0, (gpu.memory_used / gpu.memory_total) * 100)
                        gpu.temperature += gpu.utilization * 0.3  # 模拟温度上升
    
    async def run_demo(self):
        """运行演示"""
        print("🚀 优先级调度算法演示开始")
        print("=" * 60)
        
        # 创建示例数据
        models = self.create_sample_models()
        gpu_info = self.create_sample_gpu_info()
        
        # 注册所有模型
        print("\n📝 注册模型到调度器...")
        for model in models:
            self.scheduler.register_model(model)
        
        self.print_model_status("初始模型状态")
        self.print_gpu_status(gpu_info, "初始GPU状态")
        
        # 模拟GPU监控器
        async def mock_get_gpu_info():
            await self.simulate_gpu_usage(gpu_info, self.scheduler.get_model_states())
            return gpu_info
        
        # 替换GPU监控器
        import backend.app.services.resource_scheduler as scheduler_module
        scheduler_module.gpu_monitor.get_gpu_info = mock_get_gpu_info
        
        # 场景1: 按优先级顺序启动模型
        print("\n" + "=" * 60)
        print("📋 场景1: 按优先级顺序启动模型")
        print("=" * 60)
        
        # 先启动低优先级模型
        low_priority_models = ["background_model", "experimental_model", "dev_model"]
        
        for model_id in low_priority_models:
            print(f"\n🔄 启动模型: {model_id}")
            self.scheduler.update_model_status(model_id, ModelStatus.RUNNING)
            
            # 模拟资源分配
            model_state = self.scheduler._model_states[model_id]
            from backend.app.models.schemas import ResourceAllocation
            model_state.allocated_resources = ResourceAllocation(
                gpu_devices=model_state.config.resource_requirements.gpu_devices,
                memory_allocated=model_state.config.resource_requirements.gpu_memory,
                allocation_time=datetime.now()
            )
            
            await asyncio.sleep(0.1)  # 模拟启动时间
            
            self.print_model_status()
            self.print_gpu_status(gpu_info)
        
        # 场景2: 高优先级模型请求资源，触发抢占
        print("\n" + "=" * 60)
        print("📋 场景2: 高优先级模型触发抢占")
        print("=" * 60)
        
        print(f"\n🔥 关键业务模型请求资源 (优先级: 10)")
        result = await self.scheduler.schedule_model("critical_model")
        
        print(f"调度结果: {result.value}")
        
        self.print_model_status("抢占后模型状态")
        self.print_gpu_status(gpu_info, "抢占后GPU状态")
        self.print_schedule_history()
        
        # 场景3: 显示抢占统计
        print("\n" + "=" * 60)
        print("📊 抢占统计信息")
        print("=" * 60)
        
        stats = self.scheduler.get_preemption_stats()
        print(f"过去1小时抢占次数: {stats['total_preemptions_last_hour']}")
        print(f"过去24小时抢占次数: {stats['total_preemptions_last_day']}")
        print(f"抢占频率限制: {stats['preemption_rate_limit']}/小时")
        
        print("\n模型被抢占次数统计:")
        for model_id, count in stats['model_preemption_counts'].items():
            if count > 0:
                model_name = self.scheduler._model_states[model_id].config.name
                print(f"  {model_name}: {count}次")
        
        # 场景4: 资源释放后的自动恢复
        print("\n" + "=" * 60)
        print("📋 场景4: 资源释放后的模型恢复")
        print("=" * 60)
        
        print("🔄 关键业务模型完成任务，释放资源...")
        self.scheduler.update_model_status("critical_model", ModelStatus.STOPPED)
        await self.scheduler._release_resources("critical_model")
        
        # 尝试恢复被抢占的模型
        print("\n🔄 尝试恢复被抢占的模型...")
        for model_id, state in self.scheduler.get_model_states().items():
            if state.status == ModelStatus.PREEMPTED:
                print(f"恢复模型: {state.config.name}")
                result = await self.scheduler.schedule_model(model_id)
                print(f"恢复结果: {result.value}")
        
        self.print_model_status("恢复后模型状态")
        self.print_gpu_status(gpu_info, "恢复后GPU状态")
        
        print("\n" + "=" * 60)
        print("✅ 演示完成！")
        print("=" * 60)
        
        # 最终统计
        final_stats = self.scheduler.get_preemption_stats()
        print(f"\n📈 最终统计:")
        print(f"  总调度决策: {len(self.scheduler.get_schedule_history())}")
        print(f"  总抢占次数: {sum(final_stats['model_preemption_counts'].values())}")
        print(f"  活跃模型数: {sum(1 for s in self.scheduler.get_model_states().values() if s.status == ModelStatus.RUNNING)}")


async def main():
    """主函数"""
    demo = SchedulerDemo()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())