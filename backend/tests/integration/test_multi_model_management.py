"""
多模型并发管理集成测试
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import tempfile
import shutil

from app.services.model_manager import ModelManager
from app.services.resource_scheduler import PriorityResourceScheduler
from app.services.config_manager import FileConfigManager
from app.models.schemas import ModelConfig, ResourceRequirement
from app.models.enums import FrameworkType, ModelStatus, ScheduleResult
from tests.factories import TestDataGenerator, create_sample_model_config


@pytest.mark.integration
class TestMultiModelManagement:
    """多模型管理集成测试"""
    
    @pytest.fixture
    async def temp_config_dir(self):
        """创建临时配置目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    async def config_manager(self, temp_config_dir):
        """创建配置管理器"""
        return FileConfigManager(temp_config_dir)
    
    @pytest.fixture
    async def model_manager(self, config_manager):
        """创建模型管理器"""
        manager = ModelManager(config_manager)
        await manager.initialize()
        yield manager
        await manager.shutdown()
    
    @pytest.fixture
    async def scheduler(self):
        """创建资源调度器"""
        scheduler = PriorityResourceScheduler()
        yield scheduler
        await scheduler.shutdown()
    
    @pytest.fixture
    def sample_models(self):
        """创建示例模型配置"""
        return TestDataGenerator.create_model_configs(5)
    
    @pytest.mark.asyncio
    async def test_concurrent_model_creation(self, model_manager, sample_models):
        """测试并发模型创建"""
        # 并发创建多个模型
        create_tasks = []
        for model_config in sample_models:
            task = model_manager.create_model(model_config)
            create_tasks.append(task)
        
        # 等待所有创建任务完成
        results = await asyncio.gather(*create_tasks, return_exceptions=True)
        
        # 验证结果
        successful_creates = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_creates) == len(sample_models)
        
        # 验证所有模型都被创建
        all_models = await model_manager.list_models()
        assert len(all_models) == len(sample_models)
        
        # 验证模型状态
        for model in all_models:
            assert model.status == ModelStatus.STOPPED
    
    @pytest.mark.asyncio
    async def test_concurrent_model_startup(self, model_manager, sample_models):
        """测试并发模型启动"""
        # 先创建所有模型
        for model_config in sample_models:
            await model_manager.create_model(model_config)
        
        # Mock适配器启动成功
        with patch('app.adapters.base.BaseFrameworkAdapter._do_start_model', return_value=True):
            # 并发启动所有模型
            start_tasks = []
            for model_config in sample_models:
                task = model_manager.start_model(model_config.id)
                start_tasks.append(task)
            
            # 等待所有启动任务完成
            results = await asyncio.gather(*start_tasks, return_exceptions=True)
            
            # 验证启动结果
            successful_starts = [r for r in results if r is True]
            assert len(successful_starts) == len(sample_models)
            
            # 验证模型状态
            for model_config in sample_models:
                status = await model_manager.get_model_status(model_config.id)
                assert status == ModelStatus.RUNNING
    
    @pytest.mark.asyncio
    async def test_model_lifecycle_with_scheduler(self, model_manager, scheduler, sample_models):
        """测试模型生命周期与调度器集成"""
        # 注册模型到调度器
        for model_config in sample_models:
            await model_manager.create_model(model_config)
            scheduler.register_model(model_config)
        
        # Mock GPU资源信息
        mock_gpu_info = TestDataGenerator.create_gpu_cluster(2)
        
        with patch('app.utils.gpu.get_gpu_info', return_value=mock_gpu_info), \
             patch('app.services.resource_scheduler.resource_calculator') as mock_calc:
            
            # Mock资源计算
            mock_calc.calculate_model_memory_requirement.return_value = ResourceRequirement(
                gpu_memory=4096,
                gpu_devices=[0]
            )
            mock_calc.validate_resource_allocation.return_value = (True, [], Mock())
            
            # 尝试调度所有模型
            schedule_results = []
            for model_config in sample_models:
                result = await scheduler.schedule_model(model_config.id)
                schedule_results.append(result)
            
            # 验证调度结果
            successful_schedules = [r for r in schedule_results if r == ScheduleResult.SUCCESS]
            assert len(successful_schedules) > 0  # 至少有一些模型成功调度
    
    @pytest.mark.asyncio
    async def test_model_priority_based_scheduling(self, model_manager, scheduler):
        """测试基于优先级的模型调度"""
        # 创建不同优先级的模型
        high_priority_models = TestDataGenerator.create_high_priority_models(2)
        low_priority_models = TestDataGenerator.create_low_priority_models(3)
        
        all_models = high_priority_models + low_priority_models
        
        # 创建并注册所有模型
        for model_config in all_models:
            await model_manager.create_model(model_config)
            scheduler.register_model(model_config)
        
        # Mock有限的GPU资源
        limited_gpu_info = [TestDataGenerator.create_gpu_cluster(1)[0]]  # 只有一个GPU
        limited_gpu_info[0].memory_free = 8192  # 8GB可用内存
        
        with patch('app.utils.gpu.get_gpu_info', return_value=limited_gpu_info), \
             patch('app.services.resource_scheduler.resource_calculator') as mock_calc:
            
            # Mock资源需求（每个模型需要4GB）
            mock_calc.calculate_model_memory_requirement.return_value = ResourceRequirement(
                gpu_memory=4096,
                gpu_devices=[0]
            )
            
            # Mock资源分配验证
            def mock_validate_allocation(requirement, gpu_info):
                # 简单的内存检查
                available_memory = gpu_info[0].memory_free
                if requirement.gpu_memory <= available_memory:
                    return (True, [], Mock(gpu_devices=[0], memory_allocated=requirement.gpu_memory))
                else:
                    return (False, ["内存不足"], None)
            
            mock_calc.validate_resource_allocation.side_effect = mock_validate_allocation
            
            # 按优先级顺序调度模型
            models_by_priority = sorted(all_models, key=lambda m: m.priority, reverse=True)
            
            scheduled_models = []
            for model_config in models_by_priority:
                result = await scheduler.schedule_model(model_config.id)
                if result == ScheduleResult.SUCCESS:
                    scheduled_models.append(model_config)
                    # 更新可用内存
                    limited_gpu_info[0].memory_free -= 4096
            
            # 验证高优先级模型被优先调度
            assert len(scheduled_models) >= len(high_priority_models)
            for model in scheduled_models[:len(high_priority_models)]:
                assert model.priority >= 8  # 高优先级
    
    @pytest.mark.asyncio
    async def test_model_failure_and_recovery(self, model_manager, scheduler, sample_models):
        """测试模型故障和恢复"""
        # 创建并启动模型
        model_config = sample_models[0]
        await model_manager.create_model(model_config)
        scheduler.register_model(model_config)
        
        # Mock成功启动
        with patch('app.adapters.base.BaseFrameworkAdapter._do_start_model', return_value=True):
            await model_manager.start_model(model_config.id)
            assert await model_manager.get_model_status(model_config.id) == ModelStatus.RUNNING
        
        # 模拟模型故障
        with patch('app.adapters.base.BaseFrameworkAdapter._check_model_process', return_value=False):
            # 触发健康检查
            await model_manager._check_model_health(model_config.id)
            
            # 验证模型状态变为错误
            status = await model_manager.get_model_status(model_config.id)
            assert status == ModelStatus.ERROR
        
        # 模拟恢复
        with patch('app.adapters.base.BaseFrameworkAdapter._do_start_model', return_value=True), \
             patch('app.adapters.base.BaseFrameworkAdapter._check_model_process', return_value=True):
            
            # 尝试重启模型
            success = await model_manager.restart_model(model_config.id)
            assert success is True
            
            # 验证模型恢复运行
            status = await model_manager.get_model_status(model_config.id)
            assert status == ModelStatus.RUNNING
    
    @pytest.mark.asyncio
    async def test_resource_constrained_scenario(self, model_manager, scheduler):
        """测试资源受限场景"""
        # 创建资源受限场景
        scenario_data = TestDataGenerator.create_resource_constrained_scenario()
        gpus = scenario_data['gpus']
        models = scenario_data['models']
        
        # 创建并注册模型
        for model_config in models:
            await model_manager.create_model(model_config)
            scheduler.register_model(model_config)
        
        with patch('app.utils.gpu.get_gpu_info', return_value=gpus), \
             patch('app.services.resource_scheduler.resource_calculator') as mock_calc:
            
            # Mock资源计算
            def mock_calc_requirement(config):
                return config.resource_requirements
            
            mock_calc.calculate_model_memory_requirement.side_effect = mock_calc_requirement
            
            # Mock资源分配验证
            def mock_validate_allocation(requirement, gpu_info):
                # 查找有足够内存的GPU
                for gpu in gpu_info:
                    if gpu.memory_free >= requirement.gpu_memory:
                        return (True, [], Mock(
                            gpu_devices=[gpu.device_id],
                            memory_allocated=requirement.gpu_memory
                        ))
                return (False, ["内存不足"], None)
            
            mock_calc.validate_resource_allocation.side_effect = mock_validate_allocation
            
            # 尝试调度所有模型
            schedule_results = []
            for model_config in models:
                result = await scheduler.schedule_model(model_config.id)
                schedule_results.append((model_config.id, result))
            
            # 验证调度结果
            successful_schedules = [r for _, r in schedule_results if r == ScheduleResult.SUCCESS]
            failed_schedules = [r for _, r in schedule_results if r == ScheduleResult.INSUFFICIENT_RESOURCES]
            
            # 在资源受限的情况下，应该有一些成功和一些失败的调度
            assert len(successful_schedules) > 0
            assert len(failed_schedules) > 0
    
    @pytest.mark.asyncio
    async def test_model_configuration_persistence(self, model_manager, config_manager, sample_models):
        """测试模型配置持久化"""
        # 创建模型
        for model_config in sample_models:
            await model_manager.create_model(model_config)
        
        # 验证配置被保存
        saved_configs = await config_manager.load_model_configs()
        assert len(saved_configs) == len(sample_models)
        
        # 验证配置内容
        saved_ids = {config.id for config in saved_configs}
        original_ids = {config.id for config in sample_models}
        assert saved_ids == original_ids
        
        # 创建新的模型管理器实例（模拟重启）
        new_manager = ModelManager(config_manager)
        await new_manager.initialize()
        
        try:
            # 验证配置被正确加载
            loaded_models = await new_manager.list_models()
            assert len(loaded_models) == len(sample_models)
            
            loaded_ids = {model.id for model in loaded_models}
            assert loaded_ids == original_ids
        finally:
            await new_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_concurrent_model_operations(self, model_manager, sample_models):
        """测试并发模型操作"""
        # 创建模型
        for model_config in sample_models:
            await model_manager.create_model(model_config)
        
        # Mock适配器操作
        with patch('app.adapters.base.BaseFrameworkAdapter._do_start_model', return_value=True), \
             patch('app.adapters.base.BaseFrameworkAdapter._do_stop_model', return_value=True):
            
            # 并发执行不同操作
            tasks = []
            
            # 启动一些模型
            for i in range(0, len(sample_models), 2):
                task = model_manager.start_model(sample_models[i].id)
                tasks.append(task)
            
            # 同时获取模型状态
            for model_config in sample_models:
                task = model_manager.get_model_status(model_config.id)
                tasks.append(task)
            
            # 同时列出所有模型
            tasks.append(model_manager.list_models())
            
            # 等待所有操作完成
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 验证没有异常
            exceptions = [r for r in results if isinstance(r, Exception)]
            assert len(exceptions) == 0
    
    @pytest.mark.asyncio
    async def test_model_update_during_operation(self, model_manager, sample_models):
        """测试运行时模型配置更新"""
        model_config = sample_models[0]
        await model_manager.create_model(model_config)
        
        # 启动模型
        with patch('app.adapters.base.BaseFrameworkAdapter._do_start_model', return_value=True):
            await model_manager.start_model(model_config.id)
            assert await model_manager.get_model_status(model_config.id) == ModelStatus.RUNNING
        
        # 更新模型配置
        updated_config = model_config.model_copy()
        updated_config.name = "更新后的模型名称"
        updated_config.priority = 8
        
        # 在模型运行时更新配置
        success = await model_manager.update_model_config(model_config.id, updated_config)
        assert success is True
        
        # 验证配置更新
        current_config = await model_manager.get_model_config(model_config.id)
        assert current_config.name == "更新后的模型名称"
        assert current_config.priority == 8
        
        # 验证模型仍在运行
        status = await model_manager.get_model_status(model_config.id)
        assert status == ModelStatus.RUNNING


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])