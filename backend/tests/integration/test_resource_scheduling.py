"""
资源调度场景集成测试
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from app.services.resource_scheduler import PriorityResourceScheduler
from app.services.model_manager import ModelManager
from app.services.config_manager import FileConfigManager
from app.models.schemas import ModelConfig, GPUInfo, ResourceRequirement, ResourceAllocation
from app.models.enums import FrameworkType, ModelStatus, ScheduleResult, GPUVendor
from tests.factories import TestDataGenerator, GPUInfoFactory


@pytest.mark.integration
class TestResourceSchedulingScenarios:
    """资源调度场景测试"""
    
    @pytest.fixture
    async def scheduler(self):
        """创建资源调度器"""
        scheduler = PriorityResourceScheduler()
        yield scheduler
        await scheduler.shutdown()
    
    @pytest.fixture
    def gpu_cluster(self):
        """创建GPU集群"""
        return TestDataGenerator.create_gpu_cluster(4)
    
    @pytest.fixture
    def mixed_priority_models(self):
        """创建混合优先级模型"""
        high_priority = TestDataGenerator.create_high_priority_models(2)
        medium_priority = TestDataGenerator.create_model_configs(3)
        low_priority = TestDataGenerator.create_low_priority_models(3)
        
        # 设置中等优先级
        for model in medium_priority:
            model.priority = 5
        
        return high_priority + medium_priority + low_priority
    
    @pytest.mark.asyncio
    async def test_basic_resource_allocation(self, scheduler, gpu_cluster, mixed_priority_models):
        """测试基本资源分配"""
        # 注册所有模型
        for model in mixed_priority_models:
            scheduler.register_model(model)
        
        with patch('app.utils.gpu.get_gpu_info', return_value=gpu_cluster), \
             patch('app.services.resource_scheduler.resource_calculator') as mock_calc:
            
            # Mock资源需求计算
            mock_calc.calculate_model_memory_requirement.return_value = ResourceRequirement(
                gpu_memory=4096,  # 4GB
                gpu_devices=[0]
            )
            
            # Mock资源分配验证
            mock_allocation = ResourceAllocation(
                gpu_devices=[0],
                memory_allocated=4096,
                allocation_time=datetime.now()
            )
            mock_calc.validate_resource_allocation.return_value = (True, [], mock_allocation)
            
            # 调度第一个模型
            model = mixed_priority_models[0]
            result = await scheduler.schedule_model(model.id)
            
            assert result == ScheduleResult.SUCCESS
            
            # 验证模型状态
            model_state = scheduler._model_states[model.id]
            assert model_state.status == ModelStatus.STARTING
            assert model_state.allocated_resources is not None
    
    @pytest.mark.asyncio
    async def test_priority_based_preemption(self, scheduler, gpu_cluster, mixed_priority_models):
        """测试基于优先级的抢占"""
        # 注册所有模型
        for model in mixed_priority_models:
            scheduler.register_model(model)
        
        # 模拟GPU内存有限的情况
        limited_gpu = gpu_cluster[0]
        limited_gpu.memory_free = 8192  # 只有8GB可用
        
        with patch('app.utils.gpu.get_gpu_info', return_value=[limited_gpu]), \
             patch('app.services.resource_scheduler.resource_calculator') as mock_calc:
            
            # Mock资源需求（每个模型需要6GB）
            mock_calc.calculate_model_memory_requirement.return_value = ResourceRequirement(
                gpu_memory=6144,
                gpu_devices=[0]
            )
            
            # 先调度一个低优先级模型
            low_priority_model = [m for m in mixed_priority_models if m.priority <= 3][0]
            
            # Mock第一次分配成功
            mock_allocation_1 = ResourceAllocation(
                gpu_devices=[0],
                memory_allocated=6144,
                allocation_time=datetime.now()
            )
            mock_calc.validate_resource_allocation.return_value = (True, [], mock_allocation_1)
            
            result1 = await scheduler.schedule_model(low_priority_model.id)
            assert result1 == ScheduleResult.SUCCESS
            
            # 更新模型状态为运行中
            scheduler.update_model_status(low_priority_model.id, ModelStatus.RUNNING)
            scheduler._model_states[low_priority_model.id].allocated_resources = mock_allocation_1
            
            # 现在尝试调度高优先级模型
            high_priority_model = [m for m in mixed_priority_models if m.priority >= 8][0]
            
            # Mock第二次分配失败（内存不足），然后抢占后成功
            mock_allocation_2 = ResourceAllocation(
                gpu_devices=[0],
                memory_allocated=6144,
                allocation_time=datetime.now()
            )
            
            mock_calc.validate_resource_allocation.side_effect = [
                (False, ["内存不足"], None),  # 第一次失败
                (True, [], mock_allocation_2)   # 抢占后成功
            ]
            
            result2 = await scheduler.schedule_model(high_priority_model.id)
            assert result2 == ScheduleResult.SUCCESS
            
            # 验证低优先级模型被抢占
            low_priority_state = scheduler._model_states[low_priority_model.id]
            assert low_priority_state.status == ModelStatus.PREEMPTED
            assert low_priority_state.allocated_resources is None
            
            # 验证高优先级模型获得资源
            high_priority_state = scheduler._model_states[high_priority_model.id]
            assert high_priority_state.status == ModelStatus.STARTING
            assert high_priority_state.allocated_resources is not None
    
    @pytest.mark.asyncio
    async def test_multi_gpu_allocation(self, scheduler, gpu_cluster, mixed_priority_models):
        """测试多GPU分配"""
        # 注册模型
        for model in mixed_priority_models:
            scheduler.register_model(model)
        
        with patch('app.utils.gpu.get_gpu_info', return_value=gpu_cluster), \
             patch('app.services.resource_scheduler.resource_calculator') as mock_calc:
            
            # Mock不同模型需要不同的GPU资源
            def mock_calc_requirement(config):
                if config.priority >= 8:
                    # 高优先级模型需要更多资源
                    return ResourceRequirement(
                        gpu_memory=12288,  # 12GB
                        gpu_devices=[0, 1]  # 需要两个GPU
                    )
                else:
                    return ResourceRequirement(
                        gpu_memory=6144,   # 6GB
                        gpu_devices=[0]    # 单GPU
                    )
            
            mock_calc.calculate_model_memory_requirement.side_effect = mock_calc_requirement
            
            # Mock资源分配验证
            def mock_validate_allocation(requirement, gpu_info):
                # 简单的资源检查逻辑
                required_memory = requirement.gpu_memory
                required_gpus = requirement.gpu_devices
                
                if len(required_gpus) == 1:
                    # 单GPU需求
                    gpu = gpu_info[required_gpus[0]]
                    if gpu.memory_free >= required_memory:
                        return (True, [], ResourceAllocation(
                            gpu_devices=required_gpus,
                            memory_allocated=required_memory,
                            allocation_time=datetime.now()
                        ))
                elif len(required_gpus) == 2:
                    # 多GPU需求
                    gpu0, gpu1 = gpu_info[required_gpus[0]], gpu_info[required_gpus[1]]
                    if gpu0.memory_free >= required_memory//2 and gpu1.memory_free >= required_memory//2:
                        return (True, [], ResourceAllocation(
                            gpu_devices=required_gpus,
                            memory_allocated=required_memory,
                            allocation_time=datetime.now()
                        ))
                
                return (False, ["资源不足"], None)
            
            mock_calc.validate_resource_allocation.side_effect = mock_validate_allocation
            
            # 调度不同类型的模型
            scheduled_models = []
            for model in mixed_priority_models:
                result = await scheduler.schedule_model(model.id)
                if result == ScheduleResult.SUCCESS:
                    scheduled_models.append(model)
                    # 更新GPU可用内存（简化模拟）
                    requirement = mock_calc_requirement(model)
                    for gpu_id in requirement.gpu_devices:
                        gpu_cluster[gpu_id].memory_free -= requirement.gpu_memory // len(requirement.gpu_devices)
            
            # 验证调度结果
            assert len(scheduled_models) > 0
            
            # 验证高优先级模型优先获得资源
            high_priority_scheduled = [m for m in scheduled_models if m.priority >= 8]
            assert len(high_priority_scheduled) > 0
    
    @pytest.mark.asyncio
    async def test_resource_recovery_after_preemption(self, scheduler, gpu_cluster, mixed_priority_models):
        """测试抢占后的资源恢复"""
        # 注册模型
        for model in mixed_priority_models:
            scheduler.register_model(model)
        
        # 获取不同优先级的模型
        high_priority_model = [m for m in mixed_priority_models if m.priority >= 8][0]
        low_priority_model = [m for m in mixed_priority_models if m.priority <= 3][0]
        
        # 模拟有限GPU资源
        limited_gpu = gpu_cluster[0]
        limited_gpu.memory_free = 8192  # 8GB可用
        
        with patch('app.utils.gpu.get_gpu_info', return_value=[limited_gpu]), \
             patch('app.services.resource_scheduler.resource_calculator') as mock_calc:
            
            # Mock资源需求
            mock_calc.calculate_model_memory_requirement.return_value = ResourceRequirement(
                gpu_memory=6144,
                gpu_devices=[0]
            )
            
            # 1. 先调度低优先级模型
            mock_allocation = ResourceAllocation(
                gpu_devices=[0],
                memory_allocated=6144,
                allocation_time=datetime.now()
            )
            mock_calc.validate_resource_allocation.return_value = (True, [], mock_allocation)
            
            result1 = await scheduler.schedule_model(low_priority_model.id)
            assert result1 == ScheduleResult.SUCCESS
            
            # 设置为运行状态
            scheduler.update_model_status(low_priority_model.id, ModelStatus.RUNNING)
            scheduler._model_states[low_priority_model.id].allocated_resources = mock_allocation
            
            # 2. 调度高优先级模型（触发抢占）
            mock_calc.validate_resource_allocation.side_effect = [
                (False, ["内存不足"], None),  # 第一次失败
                (True, [], mock_allocation)   # 抢占后成功
            ]
            
            result2 = await scheduler.schedule_model(high_priority_model.id)
            assert result2 == ScheduleResult.SUCCESS
            
            # 验证抢占发生
            assert scheduler._model_states[low_priority_model.id].status == ModelStatus.PREEMPTED
            assert scheduler._model_states[high_priority_model.id].status == ModelStatus.STARTING
            
            # 3. 模拟高优先级模型完成并释放资源
            scheduler.update_model_status(high_priority_model.id, ModelStatus.STOPPED)
            scheduler._model_states[high_priority_model.id].allocated_resources = None
            
            # 更新GPU可用内存
            limited_gpu.memory_free = 8192
            
            # 4. 尝试恢复被抢占的模型
            mock_calc.validate_resource_allocation.return_value = (True, [], mock_allocation)
            
            recovery_result = await scheduler.manual_recover_model(low_priority_model.id)
            assert recovery_result is True
            
            # 验证模型恢复
            assert scheduler._model_states[low_priority_model.id].status == ModelStatus.STARTING
    
    @pytest.mark.asyncio
    async def test_cascading_preemption(self, scheduler, gpu_cluster, mixed_priority_models):
        """测试级联抢占"""
        # 注册模型
        for model in mixed_priority_models:
            scheduler.register_model(model)
        
        # 获取不同优先级的模型
        high_priority = [m for m in mixed_priority_models if m.priority >= 8][0]
        medium_priority = [m for m in mixed_priority_models if m.priority == 5][0]
        low_priority = [m for m in mixed_priority_models if m.priority <= 3][0]
        
        # 模拟非常有限的GPU资源
        very_limited_gpu = gpu_cluster[0]
        very_limited_gpu.memory_free = 10240  # 10GB可用
        
        with patch('app.utils.gpu.get_gpu_info', return_value=[very_limited_gpu]), \
             patch('app.services.resource_scheduler.resource_calculator') as mock_calc:
            
            # Mock资源需求（每个模型需要4GB）
            mock_calc.calculate_model_memory_requirement.return_value = ResourceRequirement(
                gpu_memory=4096,
                gpu_devices=[0]
            )
            
            # 1. 先调度低优先级和中优先级模型
            for model in [low_priority, medium_priority]:
                mock_allocation = ResourceAllocation(
                    gpu_devices=[0],
                    memory_allocated=4096,
                    allocation_time=datetime.now()
                )
                mock_calc.validate_resource_allocation.return_value = (True, [], mock_allocation)
                
                result = await scheduler.schedule_model(model.id)
                assert result == ScheduleResult.SUCCESS
                
                # 设置为运行状态
                scheduler.update_model_status(model.id, ModelStatus.RUNNING)
                scheduler._model_states[model.id].allocated_resources = mock_allocation
                
                # 更新可用内存
                very_limited_gpu.memory_free -= 4096
            
            # 2. 现在调度一个需要大量资源的高优先级模型
            mock_calc.calculate_model_memory_requirement.return_value = ResourceRequirement(
                gpu_memory=8192,  # 需要8GB
                gpu_devices=[0]
            )
            
            # Mock分配失败，然后抢占后成功
            high_priority_allocation = ResourceAllocation(
                gpu_devices=[0],
                memory_allocated=8192,
                allocation_time=datetime.now()
            )
            
            mock_calc.validate_resource_allocation.side_effect = [
                (False, ["内存不足"], None),  # 第一次失败
                (True, [], high_priority_allocation)   # 抢占后成功
            ]
            
            result = await scheduler.schedule_model(high_priority.id)
            assert result == ScheduleResult.SUCCESS
            
            # 验证级联抢占：两个低优先级模型都被抢占
            assert scheduler._model_states[low_priority.id].status == ModelStatus.PREEMPTED
            assert scheduler._model_states[medium_priority.id].status == ModelStatus.PREEMPTED
            assert scheduler._model_states[high_priority.id].status == ModelStatus.STARTING
    
    @pytest.mark.asyncio
    async def test_preemption_rate_limiting(self, scheduler, gpu_cluster, mixed_priority_models):
        """测试抢占频率限制"""
        # 注册模型
        for model in mixed_priority_models:
            scheduler.register_model(model)
        
        # 设置较低的抢占频率限制用于测试
        scheduler._preemption_config['max_preemptions_per_hour'] = 3
        
        with patch('app.utils.gpu.get_gpu_info', return_value=gpu_cluster), \
             patch('app.services.resource_scheduler.resource_calculator') as mock_calc:
            
            # Mock资源需求
            mock_calc.calculate_model_memory_requirement.return_value = ResourceRequirement(
                gpu_memory=4096,
                gpu_devices=[0]
            )
            
            # 模拟多次抢占尝试
            preemption_attempts = 0
            for i, model in enumerate(mixed_priority_models[:5]):
                if i == 0:
                    # 第一个模型正常分配
                    mock_calc.validate_resource_allocation.return_value = (True, [], Mock())
                else:
                    # 后续模型需要抢占
                    mock_calc.validate_resource_allocation.side_effect = [
                        (False, ["内存不足"], None),  # 第一次失败
                        (True, [], Mock())   # 抢占后成功
                    ]
                    preemption_attempts += 1
                
                result = await scheduler.schedule_model(model.id)
                
                if preemption_attempts <= 3:
                    # 在限制内，应该成功
                    assert result == ScheduleResult.SUCCESS
                else:
                    # 超过限制，应该失败
                    assert result == ScheduleResult.PREEMPTION_RATE_LIMITED
    
    @pytest.mark.asyncio
    async def test_resource_fragmentation_handling(self, scheduler, gpu_cluster):
        """测试资源碎片化处理"""
        # 创建需要不同资源的模型
        models = []
        
        # 大模型（需要整个GPU）
        large_model = TestDataGenerator.create_model_configs(1)[0]
        large_model.resource_requirements = ResourceRequirement(
            gpu_memory=20480,  # 20GB
            gpu_devices=[0]
        )
        models.append(large_model)
        
        # 小模型（需要少量资源）
        for i in range(4):
            small_model = TestDataGenerator.create_model_configs(1)[0]
            small_model.id = f"small_model_{i}"
            small_model.resource_requirements = ResourceRequirement(
                gpu_memory=2048,  # 2GB
                gpu_devices=[0]
            )
            models.append(small_model)
        
        # 注册所有模型
        for model in models:
            scheduler.register_model(model)
        
        # 设置GPU有24GB总内存
        test_gpu = gpu_cluster[0]
        test_gpu.memory_total = 24576
        test_gpu.memory_free = 24576
        
        with patch('app.utils.gpu.get_gpu_info', return_value=[test_gpu]), \
             patch('app.services.resource_scheduler.resource_calculator') as mock_calc:
            
            # Mock资源需求计算
            def mock_calc_requirement(config):
                return config.resource_requirements
            
            mock_calc.calculate_model_memory_requirement.side_effect = mock_calc_requirement
            
            # Mock资源分配验证
            def mock_validate_allocation(requirement, gpu_info):
                gpu = gpu_info[0]
                if gpu.memory_free >= requirement.gpu_memory:
                    return (True, [], ResourceAllocation(
                        gpu_devices=[0],
                        memory_allocated=requirement.gpu_memory,
                        allocation_time=datetime.now()
                    ))
                return (False, ["内存不足"], None)
            
            mock_calc.validate_resource_allocation.side_effect = mock_validate_allocation
            
            # 1. 先调度所有小模型
            for small_model in models[1:]:  # 跳过大模型
                result = await scheduler.schedule_model(small_model.id)
                assert result == ScheduleResult.SUCCESS
                
                # 更新可用内存
                test_gpu.memory_free -= 2048
                
                # 设置为运行状态
                scheduler.update_model_status(small_model.id, ModelStatus.RUNNING)
            
            # 现在GPU有16GB被占用，8GB可用
            assert test_gpu.memory_free == 16384
            
            # 2. 尝试调度大模型（需要20GB，但只有8GB可用）
            result = await scheduler.schedule_model(large_model.id)
            
            # 应该触发抢占以整理碎片化的资源
            assert result == ScheduleResult.SUCCESS
            
            # 验证一些小模型被抢占
            preempted_count = sum(1 for model in models[1:] 
                                if scheduler._model_states[model.id].status == ModelStatus.PREEMPTED)
            assert preempted_count >= 3  # 至少需要抢占3个小模型来释放6GB+


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])