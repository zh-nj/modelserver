#!/usr/bin/env python3
"""
自动重启和恢复机制演示脚本

展示模型自动重启、故障恢复和状态持久化的工作原理
"""
import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import List

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from backend.app.services.resource_scheduler import PriorityResourceScheduler, RecoveryReason, PreemptionReason
from backend.app.models.schemas import (
    ModelConfig, GPUInfo, ResourceRequirement, ResourceAllocation
)
from backend.app.models.enums import (
    FrameworkType, ModelStatus, GPUVendor, ScheduleResult
)


class AutoRecoveryDemo:
    """自动恢复演示类"""
    
    def __init__(self):
        # 使用临时状态文件
        self.scheduler = PriorityResourceScheduler("demo_scheduler_state.json")
        self.logger = logging.getLogger(__name__)
    
    def create_demo_models(self) -> List[ModelConfig]:
        """创建演示模型配置"""
        return [
            ModelConfig(
                id="critical_service",
                name="关键服务模型",
                framework=FrameworkType.VLLM,
                model_path="/models/critical_service.safetensors",
                priority=9,
                gpu_devices=[0],
                parameters={
                    "model_size_gb": 13.0,
                    "precision": "fp16",
                    "max_seq_len": 2048
                },
                resource_requirements=ResourceRequirement(
                    gpu_memory=16384,  # 16GB
                    gpu_devices=[0]
                )
            ),
            ModelConfig(
                id="backup_service",
                name="备用服务模型",
                framework=FrameworkType.LLAMA_CPP,
                model_path="/models/backup_service.gguf",
                priority=7,
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
                id="experimental_service",
                name="实验服务模型",
                framework=FrameworkType.LLAMA_CPP,
                model_path="/models/experimental.gguf",
                priority=3,
                gpu_devices=[0],
                parameters={
                    "model_size_gb": 3.0,
                    "precision": "int8",
                    "n_ctx": 1024
                },
                resource_requirements=ResourceRequirement(
                    gpu_memory=4096,  # 4GB
                    gpu_devices=[0]
                )
            )
        ]
    
    def create_demo_gpu_info(self) -> List[GPUInfo]:
        """创建演示GPU信息"""
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
                power_usage=50.0
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
                power_usage=45.0
            )
        ]
    
    def print_recovery_stats(self):
        """打印恢复统计信息"""
        stats = self.scheduler.get_recovery_stats()
        
        print("\n=== 恢复统计信息 ===")
        print(f"恢复队列大小: {stats['recovery_queue_size']}")
        print(f"过去1小时恢复尝试: {stats['recovery_attempts_last_hour']}")
        print(f"过去24小时恢复尝试: {stats['recovery_attempts_last_day']}")
        print(f"1小时成功率: {stats['recovery_success_rate_hour']:.2%}")
        print(f"24小时成功率: {stats['recovery_success_rate_day']:.2%}")
        print(f"自动恢复启用: {stats['auto_recovery_enabled']}")
        print(f"故障恢复启用: {stats['failure_recovery_enabled']}")
        
        if stats['pending_recovery_models']:
            print(f"待恢复模型: {stats['pending_recovery_models']}")
        
        if stats['model_recovery_counts']:
            print("\n模型恢复统计:")
            for model_id, counts in stats['model_recovery_counts'].items():
                if counts['total'] > 0:
                    success_rate = counts['success'] / counts['total']
                    print(f"  {model_id}: {counts['success']}/{counts['total']} ({success_rate:.2%})")
    
    def print_model_status(self, title: str = "模型状态"):
        """打印模型状态"""
        print(f"\n=== {title} ===")
        model_states = self.scheduler.get_model_states()
        
        for model_id, state in model_states.items():
            status_icon = {
                ModelStatus.STOPPED: "⏹️",
                ModelStatus.STARTING: "🔄",
                ModelStatus.RUNNING: "✅",
                ModelStatus.ERROR: "❌",
                ModelStatus.STOPPING: "⏸️",
                ModelStatus.PREEMPTED: "⚠️"
            }.get(state.status, "❓")
            
            print(f"{status_icon} {state.config.name}")
            print(f"   状态: {state.status.value}")
            print(f"   优先级: {state.config.priority}")
            if state.allocated_resources:
                print(f"   GPU: {state.allocated_resources.gpu_devices}")
                print(f"   内存: {state.allocated_resources.memory_allocated}MB")
            if state.preemption_count > 0:
                print(f"   被抢占次数: {state.preemption_count}")
    
    async def simulate_model_startup(self, model_id: str, gpu_info: List[GPUInfo]):
        """模拟模型启动"""
        model_state = self.scheduler._model_states.get(model_id)
        if not model_state:
            return
        
        # 模拟启动过程
        self.scheduler.update_model_status(model_id, ModelStatus.STARTING)
        await asyncio.sleep(0.5)  # 模拟启动时间
        
        # 分配资源
        model_state.allocated_resources = ResourceAllocation(
            gpu_devices=model_state.config.resource_requirements.gpu_devices,
            memory_allocated=model_state.config.resource_requirements.gpu_memory,
            allocation_time=datetime.now()
        )
        
        # 更新GPU状态
        for gpu_id in model_state.allocated_resources.gpu_devices:
            gpu = next((g for g in gpu_info if g.device_id == gpu_id), None)
            if gpu:
                gpu.memory_used += model_state.allocated_resources.memory_allocated
                gpu.memory_free = gpu.memory_total - gpu.memory_used
                gpu.utilization = min(100.0, (gpu.memory_used / gpu.memory_total) * 100)
        
        self.scheduler.update_model_status(model_id, ModelStatus.RUNNING)
        model_state.last_scheduled = datetime.now()
    
    async def simulate_model_failure(self, model_id: str, gpu_info: List[GPUInfo]):
        """模拟模型故障"""
        model_state = self.scheduler._model_states.get(model_id)
        if not model_state:
            return
        
        print(f"💥 模拟模型 {model_id} 发生故障")
        
        # 释放资源
        if model_state.allocated_resources:
            for gpu_id in model_state.allocated_resources.gpu_devices:
                gpu = next((g for g in gpu_info if g.device_id == gpu_id), None)
                if gpu:
                    gpu.memory_used -= model_state.allocated_resources.memory_allocated
                    gpu.memory_free = gpu.memory_total - gpu.memory_used
                    gpu.utilization = max(0.0, (gpu.memory_used / gpu.memory_total) * 100)
            
            model_state.allocated_resources = None
        
        # 设置为错误状态
        self.scheduler.update_model_status(model_id, ModelStatus.ERROR)
        
        # 添加到恢复队列
        self.scheduler.add_to_recovery_queue(model_id)
    
    async def mock_gpu_monitor(self, gpu_info: List[GPUInfo]):
        """模拟GPU监控器"""
        return gpu_info
    
    async def mock_resource_calculator(self, config: ModelConfig):
        """模拟资源计算器"""
        return config.resource_requirements
    
    async def mock_resource_validation(self, requirement: ResourceRequirement, gpu_info: List[GPUInfo]):
        """模拟资源验证"""
        # 简单检查是否有足够内存
        for gpu_id in requirement.gpu_devices:
            gpu = next((g for g in gpu_info if g.device_id == gpu_id), None)
            if gpu and gpu.memory_free >= requirement.gpu_memory:
                allocation = ResourceAllocation(
                    gpu_devices=[gpu_id],
                    memory_allocated=requirement.gpu_memory,
                    allocation_time=datetime.now()
                )
                return True, [], allocation
        
        return False, ["内存不足"], None
    
    async def run_demo(self):
        """运行演示"""
        print("🚀 自动重启和恢复机制演示开始")
        print("=" * 60)
        
        # 创建演示数据
        models = self.create_demo_models()
        gpu_info = self.create_demo_gpu_info()
        
        # 注册模型
        print("\n📝 注册模型到调度器...")
        for model in models:
            self.scheduler.register_model(model)
        
        # 设置模拟函数
        import backend.app.services.resource_scheduler as scheduler_module
        scheduler_module.gpu_monitor.get_gpu_info = lambda: asyncio.create_task(self.mock_gpu_monitor(gpu_info))
        scheduler_module.resource_calculator.calculate_model_memory_requirement = lambda config: self.mock_resource_calculator(config)
        scheduler_module.resource_calculator.validate_resource_allocation = lambda req, gpus: self.mock_resource_validation(req, gpu_info)
        
        self.print_model_status("初始模型状态")
        
        # 场景1: 启动模型服务
        print("\n" + "=" * 60)
        print("📋 场景1: 启动模型服务")
        print("=" * 60)
        
        for model_id in ["critical_service", "backup_service", "experimental_service"]:
            print(f"\n🔄 启动模型: {model_id}")
            await self.simulate_model_startup(model_id, gpu_info)
        
        self.print_model_status("启动后模型状态")
        
        # 场景2: 模拟故障和自动恢复
        print("\n" + "=" * 60)
        print("📋 场景2: 模拟故障和自动恢复")
        print("=" * 60)
        
        # 模拟实验服务故障
        await self.simulate_model_failure("experimental_service", gpu_info)
        
        self.print_model_status("故障后模型状态")
        self.print_recovery_stats()
        
        # 尝试自动恢复
        print("\n🔄 尝试自动恢复故障模型...")
        result = await self.scheduler._attempt_model_recovery(
            "experimental_service", 
            RecoveryReason.FAILURE_RECOVERY
        )
        
        if result:
            print("✅ 自动恢复成功")
            await self.simulate_model_startup("experimental_service", gpu_info)
        else:
            print("❌ 自动恢复失败")
        
        self.print_model_status("恢复后模型状态")
        
        # 场景3: 手动重启模型
        print("\n" + "=" * 60)
        print("📋 场景3: 手动重启模型")
        print("=" * 60)
        
        print("🔄 手动重启关键服务模型...")
        
        # 先停止模型
        await self.simulate_model_failure("critical_service", gpu_info)
        
        # 手动重启
        restart_result = await self.scheduler.restart_model("critical_service")
        
        if restart_result:
            print("✅ 手动重启成功")
            await self.simulate_model_startup("critical_service", gpu_info)
        else:
            print("❌ 手动重启失败")
        
        self.print_model_status("重启后模型状态")
        
        # 场景4: 抢占和恢复
        print("\n" + "=" * 60)
        print("📋 场景4: 抢占和恢复机制")
        print("=" * 60)
        
        # 模拟高优先级模型需要资源
        print("🔥 高优先级模型请求资源，触发抢占...")
        
        # 手动抢占低优先级模型
        await self.scheduler._preempt_model("experimental_service", PreemptionReason.HIGHER_PRIORITY)
        
        # 释放资源
        model_state = self.scheduler._model_states["experimental_service"]
        if model_state.allocated_resources:
            for gpu_id in model_state.allocated_resources.gpu_devices:
                gpu = next((g for g in gpu_info if g.device_id == gpu_id), None)
                if gpu:
                    gpu.memory_used -= model_state.allocated_resources.memory_allocated
                    gpu.memory_free = gpu.memory_total - gpu.memory_used
                    gpu.utilization = max(0.0, (gpu.memory_used / gpu.memory_total) * 100)
        
        self.print_model_status("抢占后模型状态")
        
        # 尝试恢复被抢占的模型
        print("\n🔄 尝试恢复被抢占的模型...")
        recovery_result = await self.scheduler.manual_recover_model("experimental_service")
        
        if recovery_result:
            print("✅ 恢复成功")
            await self.simulate_model_startup("experimental_service", gpu_info)
        else:
            print("❌ 恢复失败，资源不足")
        
        self.print_model_status("最终模型状态")
        
        # 场景5: 状态持久化演示
        print("\n" + "=" * 60)
        print("📋 场景5: 状态持久化")
        print("=" * 60)
        
        print("💾 保存调度器状态...")
        self.scheduler._save_state()
        
        print("📊 当前恢复队列:")
        recovery_queue = self.scheduler.get_recovery_queue()
        if recovery_queue:
            for model_id in recovery_queue:
                model_name = self.scheduler._model_states[model_id].config.name
                print(f"  - {model_name} ({model_id})")
        else:
            print("  恢复队列为空")
        
        # 最终统计
        print("\n" + "=" * 60)
        print("📈 最终统计")
        print("=" * 60)
        
        self.print_recovery_stats()
        
        # 显示调度历史
        print("\n=== 调度历史 ===")
        history = self.scheduler.get_schedule_history(5)
        for i, decision in enumerate(reversed(history), 1):
            print(f"{i}. 模型: {decision.model_id}")
            print(f"   时间: {decision.decision_time.strftime('%H:%M:%S')}")
            print(f"   结果: {decision.result.value}")
            print(f"   原因: {decision.reason}")
        
        print("\n" + "=" * 60)
        print("✅ 演示完成！")
        print("=" * 60)
        
        # 清理
        await self.scheduler.shutdown()
        
        # 删除演示状态文件
        try:
            os.remove("demo_scheduler_state.json")
        except:
            pass


async def main():
    """主函数"""
    demo = AutoRecoveryDemo()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())