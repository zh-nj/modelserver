"""
资源调度器测试
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from app.services.resource_scheduler import (
    PriorityResourceScheduler
)
from app.models.schemas import (
    ModelConfig, GPUInfo, ResourceRequirement, ResourceAllocation,
    ScheduleDecision, RecoveryAttempt
)
from app.models.enums import (
    FrameworkType, ModelStatus, GPUVendor, ScheduleResult, 
    PreemptionReason, RecoveryReason
)


class TestPriorityResourceScheduler:
    """优先级资源调度器测试"""
    
    @pytest.fixture
    def scheduler(self):
        """创建调度器实例"""
        return PriorityResourceScheduler()
    
    @pytest.fixture
    def sample_gpu_info(self):
        """示例GPU信息"""
        return [
            GPUInfo(
                device_id=0,
                name="NVIDIA RTX 4090",
                vendor=GPUVendor.NVIDIA,
                memory_total=24576,
                memory_used=8192,
                memory_free=16384,
                utilization=30.0,
                temperature=65.0,
                power_usage=250.0
            ),
            GPUInfo(
                device_id=1,
                name="NVIDIA RTX 4090",
                vendor=GPUVendor.NVIDIA,
                memory_total=24576,
                memory_used=12288,
                memory_free=12288,
                utilization=50.0,
                temperature=70.0,
                power_usage=300.0
            )
        ]
    
    @pytest.fixture
    def sample_model_configs(self):
        """示例模型配置"""
        return [
            ModelConfig(
                id="model_high_priority",
                name="高优先级模型",
                framework=FrameworkType.LLAMA_CPP,
                model_path="/models/high_priority.gguf",
                priority=9,
                gpu_devices=[0],
                parameters={"model_size_gb": 7.0, "precision": "fp16"},
                resource_requirements=ResourceRequirement(
                    gpu_memory=14336,  # 14GB
                    gpu_devices=[0]
                )
            ),
            ModelConfig(
                id="model_medium_priority",
                name="中优先级模型",
                framework=FrameworkType.VLLM,
                model_path="/models/medium_priority",
                priority=5,
                gpu_devices=[1],
                parameters={"model_size_gb": 13.0, "precision": "fp16"},
                resource_requirements=ResourceRequirement(
                    gpu_memory=10240,  # 10GB
                    gpu_devices=[1]
                )
            ),
            ModelConfig(
                id="model_low_priority",
                name="低优先级模型",
                framework=FrameworkType.LLAMA_CPP,
                model_path="/models/low_priority.gguf",
                priority=2,
                gpu_devices=[0],
                parameters={"model_size_gb": 3.0, "precision": "int8"},
                resource_requirements=ResourceRequirement(
                    gpu_memory=4096,  # 4GB
                    gpu_devices=[0]
                )
            )
        ]
    
    def test_scheduler_initialization(self, scheduler):
        """测试调度器初始化"""
        assert scheduler is not None
        assert len(scheduler._model_states) == 0
        assert len(scheduler._schedule_history) == 0
        assert scheduler._preemption_config['enable_preemption'] is True
    
    def test_register_model(self, scheduler, sample_model_configs):
        """测试模型注册"""
        config = sample_model_configs[0]
        scheduler.register_model(config)
        
        assert config.id in scheduler._model_states
        model_state = scheduler._model_states[config.id]
        assert model_state.model_id == config.id
        assert model_state.config == config
        assert model_state.status == ModelStatus.STOPPED
    
    def test_unregister_model(self, scheduler, sample_model_configs):
        """测试模型注销"""
        config = sample_model_configs[0]
        scheduler.register_model(config)
        
        assert config.id in scheduler._model_states
        
        scheduler.unregister_model(config.id)
        assert config.id not in scheduler._model_states
    
    def test_update_model_status(self, scheduler, sample_model_configs):
        """测试更新模型状态"""
        config = sample_model_configs[0]
        scheduler.register_model(config)
        
        scheduler.update_model_status(config.id, ModelStatus.RUNNING)
        assert scheduler._model_states[config.id].status == ModelStatus.RUNNING
    
    @pytest.mark.asyncio
    async def test_calculate_resource_requirements(self, scheduler, sample_model_configs):
        """测试资源需求计算"""
        config = sample_model_configs[0]
        
        with patch('app.services.resource_scheduler.resource_calculator') as mock_calc:
            mock_calc.calculate_model_memory_requirement.return_value = ResourceRequirement(
                gpu_memory=14336,
                gpu_devices=[0]
            )
            
            result = await scheduler.calculate_resource_requirements(config)
            
            assert result.gpu_memory == 14336
            assert result.gpu_devices == [0]
            mock_calc.calculate_model_memory_requirement.assert_called_once_with(config)
    
    @pytest.mark.asyncio
    async def test_find_available_resources_success(self, scheduler, sample_gpu_info):
        """测试查找可用资源 - 成功情况"""
        requirement = ResourceRequirement(
            gpu_memory=8192,  # 8GB
            gpu_devices=[0]
        )
        
        with patch('app.services.resource_scheduler.gpu_monitor') as mock_gpu:
            mock_gpu.get_gpu_info.return_value = sample_gpu_info
            
            with patch('app.services.resource_scheduler.resource_calculator') as mock_calc:
                mock_allocation = ResourceAllocation(
                    gpu_devices=[0],
                    memory_allocated=8192,
                    allocation_time=datetime.now()
                )
                mock_calc.validate_resource_allocation.return_value = (True, [], mock_allocation)
                
                result = await scheduler.find_available_resources(requirement)
                
                assert result is not None
                assert result.gpu_devices == [0]
                assert result.memory_allocated == 8192
    
    @pytest.mark.asyncio
    async def test_find_available_resources_failure(self, scheduler, sample_gpu_info):
        """测试查找可用资源 - 失败情况"""
        requirement = ResourceRequirement(
            gpu_memory=32768,  # 32GB - 超过可用内存
            gpu_devices=[0]
        )
        
        with patch('app.services.resource_scheduler.gpu_monitor') as mock_gpu:
            mock_gpu.get_gpu_info.return_value = sample_gpu_info
            
            with patch('app.services.resource_scheduler.resource_calculator') as mock_calc:
                mock_calc.validate_resource_allocation.return_value = (False, ["内存不足"], None)
                
                result = await scheduler.find_available_resources(requirement)
                
                assert result is None
    
    @pytest.mark.asyncio
    async def test_preempt_model(self, scheduler, sample_model_configs):
        """测试模型抢占"""
        config = sample_model_configs[2]  # 低优先级模型
        scheduler.register_model(config)
        
        # 设置模型为运行状态
        scheduler.update_model_status(config.id, ModelStatus.RUNNING)
        scheduler._model_states[config.id].allocated_resources = ResourceAllocation(
            gpu_devices=[0],
            memory_allocated=4096,
            allocation_time=datetime.now()
        )
        
        # 执行抢占
        result = await scheduler._preempt_model(config.id, PreemptionReason.HIGHER_PRIORITY)
        
        assert result is True
        assert scheduler._model_states[config.id].status == ModelStatus.PREEMPTED
        assert scheduler._model_states[config.id].preemption_count == 1
        assert scheduler._model_states[config.id].allocated_resources is None
    
    @pytest.mark.asyncio
    async def test_find_preemptable_models(self, scheduler, sample_model_configs):
        """测试查找可抢占模型"""
        # 注册多个模型
        for config in sample_model_configs:
            scheduler.register_model(config)
            scheduler.update_model_status(config.id, ModelStatus.RUNNING)
            scheduler._model_states[config.id].allocated_resources = ResourceAllocation(
                gpu_devices=config.gpu_devices,
                memory_allocated=config.resource_requirements.gpu_memory,
                allocation_time=datetime.now()
            )
        
        # 查找可抢占的模型（从高优先级模型的角度）
        requesting_priority = 9
        resource_req = ResourceRequirement(gpu_memory=8192, gpu_devices=[])
        
        preemptable = await scheduler._find_preemptable_models(requesting_priority, resource_req)
        
        # 应该找到中优先级和低优先级模型
        assert len(preemptable) == 2
        
        # 验证按优先级排序（低优先级在前）
        model_ids = [item[0] for item in preemptable]
        assert "model_low_priority" in model_ids
        assert "model_medium_priority" in model_ids
        
        # 低优先级模型应该排在前面
        assert preemptable[0][0] == "model_low_priority"
    
    @pytest.mark.asyncio
    async def test_attempt_preemption_success(self, scheduler, sample_model_configs):
        """测试抢占尝试 - 成功情况"""
        # 注册模型
        for config in sample_model_configs:
            scheduler.register_model(config)
            if config.priority < 9:  # 非高优先级模型设为运行状态
                scheduler.update_model_status(config.id, ModelStatus.RUNNING)
                scheduler._model_states[config.id].allocated_resources = ResourceAllocation(
                    gpu_devices=config.gpu_devices,
                    memory_allocated=config.resource_requirements.gpu_memory,
                    allocation_time=datetime.now()
                )
        
        # 高优先级模型请求资源
        requesting_model_id = "model_high_priority"
        resource_req = ResourceRequirement(gpu_memory=8192, gpu_devices=[])
        
        result = await scheduler._attempt_preemption(requesting_model_id, resource_req)
        
        assert result['success'] is True
        assert len(result['preempted_models']) > 0
        assert result['freed_memory'] >= 8192
    
    @pytest.mark.asyncio
    async def test_schedule_model_direct_allocation(self, scheduler, sample_model_configs, sample_gpu_info):
        """测试模型调度 - 直接分配成功"""
        config = sample_model_configs[0]
        scheduler.register_model(config)
        
        with patch('app.services.resource_scheduler.gpu_monitor') as mock_gpu:
            mock_gpu.get_gpu_info.return_value = sample_gpu_info
            
            with patch('app.services.resource_scheduler.resource_calculator') as mock_calc:
                # 模拟资源需求计算
                mock_calc.calculate_model_memory_requirement.return_value = ResourceRequirement(
                    gpu_memory=8192,
                    gpu_devices=[0]
                )
                
                # 模拟资源分配成功
                mock_allocation = ResourceAllocation(
                    gpu_devices=[0],
                    memory_allocated=8192,
                    allocation_time=datetime.now()
                )
                mock_calc.validate_resource_allocation.return_value = (True, [], mock_allocation)
                
                result = await scheduler.schedule_model(config.id)
                
                assert result == ScheduleResult.SUCCESS
                assert scheduler._model_states[config.id].status == ModelStatus.STARTING
                assert scheduler._model_states[config.id].allocated_resources is not None
                assert len(scheduler._schedule_history) == 1
    
    @pytest.mark.asyncio
    async def test_schedule_model_with_preemption(self, scheduler, sample_model_configs, sample_gpu_info):
        """测试模型调度 - 需要抢占"""
        # 注册所有模型
        for config in sample_model_configs:
            scheduler.register_model(config)
            if config.id != "model_high_priority":
                scheduler.update_model_status(config.id, ModelStatus.RUNNING)
                scheduler._model_states[config.id].allocated_resources = ResourceAllocation(
                    gpu_devices=config.gpu_devices,
                    memory_allocated=config.resource_requirements.gpu_memory,
                    allocation_time=datetime.now()
                )
        
        # 模拟GPU内存不足的情况
        insufficient_gpu_info = [
            GPUInfo(
                device_id=0,
                name="NVIDIA RTX 4090",
                vendor=GPUVendor.NVIDIA,
                memory_total=24576,
                memory_used=20480,  # 大部分内存已使用
                memory_free=4096,   # 只有4GB可用
                utilization=80.0,
                temperature=75.0,
                power_usage=350.0
            )
        ]
        
        with patch('app.services.resource_scheduler.gpu_monitor') as mock_gpu:
            mock_gpu.get_gpu_info.return_value = insufficient_gpu_info
            
            with patch('app.services.resource_scheduler.resource_calculator') as mock_calc:
                # 高优先级模型需要14GB内存
                mock_calc.calculate_model_memory_requirement.return_value = ResourceRequirement(
                    gpu_memory=14336,
                    gpu_devices=[0]
                )
                
                # 第一次分配失败（内存不足）
                # 第二次分配成功（抢占后）
                mock_allocation = ResourceAllocation(
                    gpu_devices=[0],
                    memory_allocated=14336,
                    allocation_time=datetime.now()
                )
                
                mock_calc.validate_resource_allocation.side_effect = [
                    (False, ["内存不足"], None),  # 第一次失败
                    (True, [], mock_allocation)   # 抢占后成功
                ]
                
                result = await scheduler.schedule_model("model_high_priority")
                
                assert result == ScheduleResult.SUCCESS
                assert len(scheduler._schedule_history) == 1
                
                # 检查是否有模型被抢占
                decision = scheduler._schedule_history[0]
                assert len(decision.preempted_models) > 0
    
    def test_get_preemption_stats(self, scheduler, sample_model_configs):
        """测试获取抢占统计信息"""
        # 注册模型并设置抢占计数
        for config in sample_model_configs:
            scheduler.register_model(config)
            scheduler._model_states[config.id].preemption_count = config.priority  # 模拟抢占次数
        
        # 添加一些调度历史
        now = datetime.now()
        scheduler._schedule_history.extend([
            ScheduleDecision(
                model_id="test1",
                decision_time=now - timedelta(minutes=30),
                result=ScheduleResult.SUCCESS,
                preempted_models=["model_low_priority"]
            ),
            ScheduleDecision(
                model_id="test2",
                decision_time=now - timedelta(minutes=10),
                result=ScheduleResult.SUCCESS,
                preempted_models=["model_medium_priority", "model_low_priority"]
            )
        ])
        
        stats = scheduler.get_preemption_stats()
        
        assert 'total_preemptions_last_hour' in stats
        assert 'total_preemptions_last_day' in stats
        assert 'model_preemption_counts' in stats
        assert 'most_preempted_models' in stats
        
        assert stats['total_preemptions_last_hour'] == 3  # 1 + 2 个被抢占的模型
        assert len(stats['model_preemption_counts']) == 3
    
    def test_check_preemption_rate_limit(self, scheduler):
        """测试抢占频率限制检查"""
        # 默认情况下应该允许抢占
        assert scheduler._check_preemption_rate_limit() is True
        
        # 添加大量抢占历史
        now = datetime.now()
        for i in range(15):  # 超过限制的抢占次数
            scheduler._schedule_history.append(
                ScheduleDecision(
                    model_id=f"test_{i}",
                    decision_time=now - timedelta(minutes=i),
                    result=ScheduleResult.SUCCESS,
                    preempted_models=[f"victim_{i}"]
                )
            )
        
        # 现在应该被限制
        assert scheduler._check_preemption_rate_limit() is False
    
    @pytest.mark.asyncio
    async def test_preempt_lower_priority_models(self, scheduler, sample_model_configs):
        """测试抢占指定GPU上的低优先级模型"""
        # 注册模型并设置为运行状态
        for config in sample_model_configs:
            scheduler.register_model(config)
            scheduler.update_model_status(config.id, ModelStatus.RUNNING)
            scheduler._model_states[config.id].allocated_resources = ResourceAllocation(
                gpu_devices=config.gpu_devices,
                memory_allocated=config.resource_requirements.gpu_memory,
                allocation_time=datetime.now()
            )
        
        # 抢占GPU 0上的模型
        preempted = await scheduler.preempt_lower_priority_models(8192, 0)
        
        # 应该抢占在GPU 0上的低优先级模型
        assert len(preempted) > 0
        
        # 验证被抢占的模型确实在GPU 0上
        for model_id in preempted:
            original_config = next(c for c in sample_model_configs if c.id == model_id)
            assert 0 in original_config.gpu_devices


    @pytest.mark.asyncio
    async def test_auto_recovery_mechanism(self, scheduler, sample_model_configs):
        """测试自动恢复机制"""
        # 注册模型
        config = sample_model_configs[2]  # 低优先级模型
        scheduler.register_model(config)
        
        # 设置模型为被抢占状态
        scheduler.update_model_status(config.id, ModelStatus.PREEMPTED)
        
        # 模拟资源可用的情况
        with patch('app.services.resource_scheduler.gpu_monitor') as mock_gpu:
            mock_gpu.get_gpu_info.return_value = [
                GPUInfo(
                    device_id=0,
                    name="NVIDIA RTX 4090",
                    vendor=GPUVendor.NVIDIA,
                    memory_total=24576,
                    memory_used=0,
                    memory_free=24576,
                    utilization=0.0,
                    temperature=45.0,
                    power_usage=50.0
                )
            ]
            
            with patch('app.services.resource_scheduler.resource_calculator') as mock_calc:
                mock_calc.calculate_model_memory_requirement.return_value = ResourceRequirement(
                    gpu_memory=4096,
                    gpu_devices=[0]
                )
                
                mock_allocation = ResourceAllocation(
                    gpu_devices=[0],
                    memory_allocated=4096,
                    allocation_time=datetime.now()
                )
                mock_calc.validate_resource_allocation.return_value = (True, [], mock_allocation)
                
                # 尝试恢复模型
                result = await scheduler._attempt_model_recovery(
                    config.id, 
                    RecoveryReason.RESOURCE_AVAILABLE
                )
                
                assert result is True
                assert scheduler._model_states[config.id].status == ModelStatus.STARTING
                assert len(scheduler._recovery_attempts) == 1
                assert scheduler._recovery_attempts[0].success is True
    
    @pytest.mark.asyncio
    async def test_manual_recover_model(self, scheduler, sample_model_configs):
        """测试手动恢复模型"""
        config = sample_model_configs[0]
        scheduler.register_model(config)
        scheduler.update_model_status(config.id, ModelStatus.PREEMPTED)
        
        with patch.object(scheduler, 'schedule_model') as mock_schedule:
            mock_schedule.return_value = ScheduleResult.SUCCESS
            
            result = await scheduler.manual_recover_model(config.id)
            
            assert result is True
            mock_schedule.assert_called_once_with(config.id)
    
    @pytest.mark.asyncio
    async def test_restart_model(self, scheduler, sample_model_configs):
        """测试重启模型"""
        config = sample_model_configs[0]
        scheduler.register_model(config)
        scheduler.update_model_status(config.id, ModelStatus.RUNNING)
        scheduler._model_states[config.id].allocated_resources = ResourceAllocation(
            gpu_devices=[0],
            memory_allocated=8192,
            allocation_time=datetime.now()
        )
        
        with patch.object(scheduler, 'schedule_model') as mock_schedule:
            mock_schedule.return_value = ScheduleResult.SUCCESS
            
            result = await scheduler.restart_model(config.id)
            
            assert result is True
            assert scheduler._model_states[config.id].allocated_resources is None
            mock_schedule.assert_called_once_with(config.id)
    
    def test_recovery_queue_management(self, scheduler, sample_model_configs):
        """测试恢复队列管理"""
        config = sample_model_configs[0]
        scheduler.register_model(config)
        
        # 添加到恢复队列
        scheduler.add_to_recovery_queue(config.id)
        assert config.id in scheduler.get_recovery_queue()
        
        # 从恢复队列移除
        scheduler.remove_from_recovery_queue(config.id)
        assert config.id not in scheduler.get_recovery_queue()
    
    def test_should_attempt_recovery(self, scheduler, sample_model_configs):
        """测试恢复条件判断"""
        config = sample_model_configs[0]
        scheduler.register_model(config)
        
        # 初始情况下应该允许恢复
        result = asyncio.run(scheduler._should_attempt_recovery(config.id))
        assert result is True
        
        # 添加过多的恢复尝试
        now = datetime.now()
        for i in range(5):  # 超过最大尝试次数
            scheduler._recovery_attempts.append(
                RecoveryAttempt(
                    model_id=config.id,
                    attempt_time=now - timedelta(minutes=i),
                    reason=RecoveryReason.RESOURCE_AVAILABLE,
                    success=False
                )
            )
        
        # 现在应该被限制
        result = asyncio.run(scheduler._should_attempt_recovery(config.id))
        assert result is False
    
    def test_get_recovery_stats(self, scheduler, sample_model_configs):
        """测试获取恢复统计信息"""
        # 添加一些恢复尝试记录
        now = datetime.now()
        for i, config in enumerate(sample_model_configs[:2]):
            scheduler.register_model(config)
            scheduler._recovery_attempts.extend([
                RecoveryAttempt(
                    model_id=config.id,
                    attempt_time=now - timedelta(minutes=i * 10),
                    reason=RecoveryReason.RESOURCE_AVAILABLE,
                    success=i % 2 == 0  # 交替成功/失败
                ),
                RecoveryAttempt(
                    model_id=config.id,
                    attempt_time=now - timedelta(minutes=i * 10 + 5),
                    reason=RecoveryReason.MANUAL_RECOVERY,
                    success=True
                )
            ])
        
        # 添加到恢复队列
        scheduler.add_to_recovery_queue(sample_model_configs[0].id)
        
        stats = scheduler.get_recovery_stats()
        
        assert 'recovery_queue_size' in stats
        assert 'recovery_attempts_last_hour' in stats
        assert 'recovery_success_rate_hour' in stats
        assert 'model_recovery_counts' in stats
        assert 'pending_recovery_models' in stats
        
        assert stats['recovery_queue_size'] == 1
        assert stats['recovery_attempts_last_hour'] == 4
        assert len(stats['model_recovery_counts']) == 2
    
    def test_state_persistence(self, scheduler, sample_model_configs, tmp_path):
        """测试状态持久化"""
        # 使用临时文件
        state_file = tmp_path / "test_scheduler_state.json"
        scheduler._state_file = str(state_file)
        
        # 注册模型并添加到恢复队列
        config = sample_model_configs[0]
        scheduler.register_model(config)
        scheduler.add_to_recovery_queue(config.id)
        
        # 保存状态
        scheduler._save_state()
        
        # 验证文件存在
        assert state_file.exists()
        
        # 创建新的调度器实例并加载状态
        new_scheduler = scheduler.__class__(str(state_file))
        
        # 验证恢复队列被正确加载
        assert config.id in new_scheduler.get_recovery_queue()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])