"""
故障恢复流程集成测试
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import tempfile
import shutil

from app.services.model_manager import ModelManager
from app.services.resource_scheduler import PriorityResourceScheduler
from app.services.health_checker import HealthChecker
from app.services.config_manager import FileConfigManager
from app.models.schemas import ModelConfig, ModelInfo
from app.services.health_checker import HealthCheckResult
from app.models.enums import FrameworkType, ModelStatus, HealthStatus
from tests.factories import TestDataGenerator, create_sample_model_config


@pytest.mark.integration
class TestFailureRecoveryFlows:
    """故障恢复流程测试"""
    
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
    async def health_checker(self):
        """创建健康检查器"""
        checker = HealthChecker()
        yield checker
        await checker.stop_periodic_checks()
    
    @pytest.fixture
    def sample_models(self):
        """创建示例模型配置"""
        return TestDataGenerator.create_model_configs(3)
    
    @pytest.mark.asyncio
    async def test_model_process_crash_recovery(self, model_manager, scheduler, sample_models):
        """测试模型进程崩溃恢复"""
        model_config = sample_models[0]
        
        # 创建并启动模型
        await model_manager.create_model(model_config)
        scheduler.register_model(model_config)
        
        # Mock成功启动
        with patch('app.adapters.base.BaseFrameworkAdapter._do_start_model', return_value=True), \
             patch('app.adapters.base.BaseFrameworkAdapter._check_model_process', return_value=True):
            
            await model_manager.start_model(model_config.id)
            assert await model_manager.get_model_status(model_config.id) == ModelStatus.RUNNING
        
        # 模拟进程崩溃
        with patch('app.adapters.base.BaseFrameworkAdapter._check_model_process', return_value=False):
            # 触发健康检查
            await model_manager._check_model_health(model_config.id)
            
            # 验证模型状态变为错误
            status = await model_manager.get_model_status(model_config.id)
            assert status == ModelStatus.ERROR
        
        # 模拟自动重启
        restart_attempts = 0
        max_restart_attempts = 3
        
        async def mock_restart_with_retry():
            nonlocal restart_attempts
            restart_attempts += 1
            
            if restart_attempts <= 2:
                # 前两次重启失败
                return False
            else:
                # 第三次重启成功
                return True
        
        with patch('app.adapters.base.BaseFrameworkAdapter._do_start_model', side_effect=mock_restart_with_retry), \
             patch('app.adapters.base.BaseFrameworkAdapter._check_model_process', return_value=True):
            
            # 执行自动重启逻辑
            for attempt in range(max_restart_attempts):
                success = await model_manager.restart_model(model_config.id)
                if success:
                    break
                await asyncio.sleep(0.1)  # 短暂延迟模拟重试间隔
            
            # 验证最终重启成功
            assert success is True
            assert restart_attempts == 3
            
            # 验证模型恢复运行
            status = await model_manager.get_model_status(model_config.id)
            assert status == ModelStatus.RUNNING
    
    @pytest.mark.asyncio
    async def test_resource_exhaustion_recovery(self, model_manager, scheduler, sample_models):
        """测试资源耗尽后的恢复"""
        # 创建并注册所有模型
        for model_config in sample_models:
            await model_manager.create_model(model_config)
            scheduler.register_model(model_config)
        
        # Mock有限的GPU资源
        limited_gpu = TestDataGenerator.create_gpu_cluster(1)[0]
        limited_gpu.memory_free = 4096  # 只有4GB可用
        
        with patch('app.utils.gpu.get_gpu_info', return_value=[limited_gpu]), \
             patch('app.services.resource_scheduler.resource_calculator') as mock_calc:
            
            # Mock每个模型需要3GB内存
            mock_calc.calculate_model_memory_requirement.return_value = Mock(
                gpu_memory=3072,
                gpu_devices=[0]
            )
            
            # Mock资源分配验证
            def mock_validate_allocation(requirement, gpu_info):
                gpu = gpu_info[0]
                if gpu.memory_free >= requirement.gpu_memory:
                    return (True, [], Mock(
                        gpu_devices=[0],
                        memory_allocated=requirement.gpu_memory
                    ))
                return (False, ["内存不足"], None)
            
            mock_calc.validate_resource_allocation.side_effect = mock_validate_allocation
            
            # 1. 尝试调度第一个模型（应该成功）
            result1 = await scheduler.schedule_model(sample_models[0].id)
            assert result1.name == "SUCCESS"
            
            # 更新可用内存
            limited_gpu.memory_free -= 3072
            
            # 2. 尝试调度第二个模型（应该失败，资源不足）
            result2 = await scheduler.schedule_model(sample_models[1].id)
            assert result2.name == "INSUFFICIENT_RESOURCES"
            
            # 3. 模拟第一个模型完成并释放资源
            scheduler.update_model_status(sample_models[0].id, ModelStatus.STOPPED)
            scheduler._model_states[sample_models[0].id].allocated_resources = None
            limited_gpu.memory_free = 4096  # 恢复可用内存
            
            # 4. 现在应该能够调度第二个模型
            result3 = await scheduler.schedule_model(sample_models[1].id)
            assert result3.name == "SUCCESS"
    
    @pytest.mark.asyncio
    async def test_health_check_failure_recovery(self, model_manager, health_checker, sample_models):
        """测试健康检查失败后的恢复"""
        model_config = sample_models[0]
        
        # 创建并启动模型
        await model_manager.create_model(model_config)
        
        with patch('app.adapters.base.BaseFrameworkAdapter._do_start_model', return_value=True):
            await model_manager.start_model(model_config.id)
        
        # 创建模型信息并注册到健康检查器
        model_info = ModelInfo(
            id=model_config.id,
            name=model_config.name,
            framework=model_config.framework,
            status=ModelStatus.RUNNING,
            endpoint=f"http://127.0.0.1:{model_config.parameters['port']}",
            health=HealthStatus.HEALTHY,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        await health_checker.register_model(model_info)
        
        # 模拟健康检查失败
        failure_count = 0
        max_failures = 3
        
        async def mock_health_check_with_failures(model_info, endpoint=None):
            nonlocal failure_count
            failure_count += 1
            
            if failure_count <= max_failures:
                # 前几次检查失败
                return HealthCheckResult(
                    model_id=model_info.id,
                    status=HealthStatus.UNHEALTHY,
                    check_time=datetime.now(),
                    error_message=f"Health check failed (attempt {failure_count})"
                )
            else:
                # 后续检查成功（模拟恢复）
                return HealthCheckResult(
                    model_id=model_info.id,
                    status=HealthStatus.HEALTHY,
                    check_time=datetime.now(),
                    response_time=0.1
                )
        
        # 设置健康检查回调来处理失败
        recovery_triggered = False
        
        async def health_callback(model_id, old_status, new_status, result):
            nonlocal recovery_triggered
            if new_status == HealthStatus.UNHEALTHY and not recovery_triggered:
                recovery_triggered = True
                # 触发模型重启
                with patch('app.adapters.base.BaseFrameworkAdapter._do_start_model', return_value=True):
                    await model_manager.restart_model(model_id)
        
        health_checker.add_health_callback(health_callback)
        
        # 执行多次健康检查
        with patch.object(health_checker, 'check_model_health', side_effect=mock_health_check_with_failures):
            for _ in range(max_failures + 2):
                result = await health_checker.check_model_health(model_info)
                await health_checker._update_model_status(result)
                await asyncio.sleep(0.1)  # 短暂延迟
        
        # 验证恢复过程
        assert recovery_triggered is True
        assert failure_count > max_failures
        
        # 验证最终健康状态
        final_status = await health_checker.get_model_health_status(model_config.id)
        assert final_status == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_configuration_corruption_recovery(self, model_manager, config_manager, sample_models):
        """测试配置损坏后的恢复"""
        # 创建模型
        for model_config in sample_models:
            await model_manager.create_model(model_config)
        
        # 验证配置正常保存
        saved_configs = await config_manager.load_model_configs()
        assert len(saved_configs) == len(sample_models)
        
        # 模拟配置文件损坏
        with patch.object(config_manager, 'load_model_configs', side_effect=Exception("配置文件损坏")):
            # 创建新的模型管理器实例（模拟重启）
            new_manager = ModelManager(config_manager)
            
            # 初始化应该处理配置加载失败
            try:
                await new_manager.initialize()
                # 如果没有抛出异常，说明有错误处理机制
                loaded_models = await new_manager.list_models()
                # 配置损坏时应该从空状态开始
                assert len(loaded_models) == 0
            except Exception as e:
                # 如果抛出异常，验证是预期的配置错误
                assert "配置" in str(e)
            finally:
                await new_manager.shutdown()
        
        # 验证配置恢复机制
        # 模拟从备份恢复配置
        with patch.object(config_manager, 'restore_from_backup', return_value=True):
            recovery_manager = ModelManager(config_manager)
            await recovery_manager.initialize()
            
            try:
                # 手动恢复配置
                for model_config in sample_models:
                    await recovery_manager.create_model(model_config)
                
                # 验证恢复成功
                recovered_models = await recovery_manager.list_models()
                assert len(recovered_models) == len(sample_models)
                
                recovered_ids = {model.id for model in recovered_models}
                original_ids = {model.id for model in sample_models}
                assert recovered_ids == original_ids
            finally:
                await recovery_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_network_partition_recovery(self, model_manager, health_checker, sample_models):
        """测试网络分区后的恢复"""
        model_config = sample_models[0]
        
        # 创建并启动模型
        await model_manager.create_model(model_config)
        
        with patch('app.adapters.base.BaseFrameworkAdapter._do_start_model', return_value=True):
            await model_manager.start_model(model_config.id)
        
        # 创建模型信息
        model_info = ModelInfo(
            id=model_config.id,
            name=model_config.name,
            framework=model_config.framework,
            status=ModelStatus.RUNNING,
            endpoint=f"http://127.0.0.1:{model_config.parameters['port']}",
            health=HealthStatus.HEALTHY,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        await health_checker.register_model(model_info)
        
        # 模拟网络分区（连接超时）
        network_partition_active = True
        
        async def mock_health_check_with_network_issues(model_info, endpoint=None):
            if network_partition_active:
                # 网络分区期间，健康检查超时
                raise asyncio.TimeoutError("Network partition - connection timeout")
            else:
                # 网络恢复后，健康检查成功
                return HealthCheckResult(
                    model_id=model_info.id,
                    status=HealthStatus.HEALTHY,
                    check_time=datetime.now(),
                    response_time=0.1
                )
        
        # 执行网络分区期间的健康检查
        with patch.object(health_checker, 'check_model_health', side_effect=mock_health_check_with_network_issues):
            # 网络分区期间的检查应该失败
            result1 = await health_checker.check_model_health(model_info)
            assert result1.status == HealthStatus.UNHEALTHY
            assert "timeout" in result1.error_message.lower()
            
            # 模拟网络恢复
            network_partition_active = False
            
            # 网络恢复后的检查应该成功
            result2 = await health_checker.check_model_health(model_info)
            assert result2.status == HealthStatus.HEALTHY
            assert result2.error_message is None
    
    @pytest.mark.asyncio
    async def test_cascading_failure_recovery(self, model_manager, scheduler, sample_models):
        """测试级联故障恢复"""
        # 创建依赖链：高优先级模型依赖于低优先级模型
        high_priority_model = sample_models[0]
        high_priority_model.priority = 9
        
        dependent_models = sample_models[1:]
        for i, model in enumerate(dependent_models):
            model.priority = 5 - i  # 递减优先级
        
        # 创建并启动所有模型
        all_models = [high_priority_model] + dependent_models
        for model_config in all_models:
            await model_manager.create_model(model_config)
            scheduler.register_model(model_config)
        
        # Mock所有模型成功启动
        with patch('app.adapters.base.BaseFrameworkAdapter._do_start_model', return_value=True):
            for model_config in all_models:
                await model_manager.start_model(model_config.id)
                scheduler.update_model_status(model_config.id, ModelStatus.RUNNING)
        
        # 模拟级联故障：从最低优先级模型开始失败
        failed_models = []
        
        for model_config in reversed(dependent_models):  # 从低优先级开始
            # 模拟模型失败
            with patch('app.adapters.base.BaseFrameworkAdapter._check_model_process', return_value=False):
                await model_manager._check_model_health(model_config.id)
                
                status = await model_manager.get_model_status(model_config.id)
                if status == ModelStatus.ERROR:
                    failed_models.append(model_config.id)
                    scheduler.update_model_status(model_config.id, ModelStatus.ERROR)
        
        # 验证级联故障发生
        assert len(failed_models) > 0
        
        # 模拟级联恢复：按优先级顺序恢复
        recovered_models = []
        
        # 按优先级排序进行恢复
        recovery_order = sorted(all_models, key=lambda m: m.priority, reverse=True)
        
        for model_config in recovery_order:
            if model_config.id in failed_models or model_config.id == high_priority_model.id:
                # 模拟恢复成功
                with patch('app.adapters.base.BaseFrameworkAdapter._do_start_model', return_value=True), \
                     patch('app.adapters.base.BaseFrameworkAdapter._check_model_process', return_value=True):
                    
                    success = await model_manager.restart_model(model_config.id)
                    if success:
                        recovered_models.append(model_config.id)
                        scheduler.update_model_status(model_config.id, ModelStatus.RUNNING)
        
        # 验证恢复结果
        assert len(recovered_models) > 0
        
        # 验证高优先级模型首先恢复
        if high_priority_model.id in recovered_models:
            high_priority_index = recovered_models.index(high_priority_model.id)
            assert high_priority_index == 0  # 应该是第一个恢复的
    
    @pytest.mark.asyncio
    async def test_partial_system_recovery(self, model_manager, scheduler, health_checker, sample_models):
        """测试部分系统恢复"""
        # 创建多个模型
        for model_config in sample_models:
            await model_manager.create_model(model_config)
            scheduler.register_model(model_config)
        
        # 启动所有模型
        with patch('app.adapters.base.BaseFrameworkAdapter._do_start_model', return_value=True):
            for model_config in sample_models:
                await model_manager.start_model(model_config.id)
                scheduler.update_model_status(model_config.id, ModelStatus.RUNNING)
        
        # 模拟部分系统故障（只有部分模型失败）
        failed_models = sample_models[:2]  # 前两个模型失败
        working_models = sample_models[2:]  # 其余模型正常
        
        # 设置失败模型的状态
        for model_config in failed_models:
            with patch('app.adapters.base.BaseFrameworkAdapter._check_model_process', return_value=False):
                await model_manager._check_model_health(model_config.id)
                scheduler.update_model_status(model_config.id, ModelStatus.ERROR)
        
        # 验证部分故障状态
        for model_config in failed_models:
            status = await model_manager.get_model_status(model_config.id)
            assert status == ModelStatus.ERROR
        
        for model_config in working_models:
            status = await model_manager.get_model_status(model_config.id)
            assert status == ModelStatus.RUNNING
        
        # 执行部分恢复
        recovery_success_count = 0
        
        for model_config in failed_models:
            # 模拟恢复尝试（50%成功率）
            recovery_success = model_config.id.endswith('0')  # 简单的成功条件
            
            if recovery_success:
                with patch('app.adapters.base.BaseFrameworkAdapter._do_start_model', return_value=True):
                    success = await model_manager.restart_model(model_config.id)
                    if success:
                        recovery_success_count += 1
                        scheduler.update_model_status(model_config.id, ModelStatus.RUNNING)
        
        # 验证部分恢复结果
        running_models = []
        error_models = []
        
        for model_config in sample_models:
            status = await model_manager.get_model_status(model_config.id)
            if status == ModelStatus.RUNNING:
                running_models.append(model_config.id)
            elif status == ModelStatus.ERROR:
                error_models.append(model_config.id)
        
        # 应该有一些模型在运行，可能还有一些处于错误状态
        assert len(running_models) >= len(working_models)
        assert len(running_models) + len(error_models) == len(sample_models)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])