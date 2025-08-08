"""
资源调度器简化测试
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from app.models.schemas import (
    ModelConfig, GPUInfo, ResourceRequirement, ResourceAllocation
)
from app.models.enums import (
    FrameworkType, ModelStatus, GPUVendor
)
from tests.factories import TestDataGenerator, GPUInfoFactory


@pytest.mark.unit
class TestResourceSchedulerBasic:
    """资源调度器基础测试"""
    
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
        return TestDataGenerator.create_model_configs(3)
    
    def test_gpu_info_creation(self, sample_gpu_info):
        """测试GPU信息创建"""
        assert len(sample_gpu_info) == 2
        assert sample_gpu_info[0].device_id == 0
        assert sample_gpu_info[0].memory_total == 24576
        assert sample_gpu_info[0].memory_free == 16384
    
    def test_model_config_creation(self, sample_model_configs):
        """测试模型配置创建"""
        assert len(sample_model_configs) == 3
        for config in sample_model_configs:
            assert config.id is not None
            assert config.name is not None
            assert config.framework in list(FrameworkType)
            assert 1 <= config.priority <= 10
    
    def test_resource_requirement_validation(self):
        """测试资源需求验证"""
        requirement = ResourceRequirement(
            gpu_memory=8192,
            gpu_devices=[0, 1]
        )
        
        assert requirement.gpu_memory == 8192
        assert requirement.gpu_devices == [0, 1]
    
    def test_resource_allocation_creation(self):
        """测试资源分配创建"""
        allocation = ResourceAllocation(
            gpu_devices=[0],
            memory_allocated=8192,
            allocation_time=datetime.now()
        )
        
        assert allocation.gpu_devices == [0]
        assert allocation.memory_allocated == 8192
        assert allocation.allocation_time is not None
    
    def test_gpu_factory_generation(self):
        """测试GPU工厂生成"""
        gpus = TestDataGenerator.create_gpu_cluster(4)
        
        assert len(gpus) == 4
        for i, gpu in enumerate(gpus):
            assert gpu.device_id == i
            assert gpu.memory_total > 0
            assert gpu.memory_free >= 0
            assert gpu.memory_used >= 0
            assert gpu.memory_total == gpu.memory_used + gpu.memory_free
    
    def test_model_priority_sorting(self, sample_model_configs):
        """测试模型优先级排序"""
        # 按优先级降序排序
        sorted_models = sorted(sample_model_configs, key=lambda m: m.priority, reverse=True)
        
        assert len(sorted_models) == len(sample_model_configs)
        
        # 验证排序正确
        for i in range(len(sorted_models) - 1):
            assert sorted_models[i].priority >= sorted_models[i + 1].priority
    
    def test_resource_constrained_scenario(self):
        """测试资源受限场景"""
        scenario = TestDataGenerator.create_resource_constrained_scenario()
        
        assert 'gpus' in scenario
        assert 'models' in scenario
        assert 'scenario' in scenario
        assert scenario['scenario'] == 'resource_constrained'
        
        # 验证GPU资源受限
        gpus = scenario['gpus']
        for gpu in gpus:
            # 可用内存应该相对较少
            utilization_rate = gpu.memory_used / gpu.memory_total
            assert utilization_rate > 0.5  # 使用率超过50%
    
    def test_performance_test_data_generation(self):
        """测试性能测试数据生成"""
        perf_data = TestDataGenerator.create_performance_test_data(20)
        
        assert 'models' in perf_data
        assert 'gpus' in perf_data
        assert 'scenario' in perf_data
        assert perf_data['scenario'] == 'performance_test'
        
        models = perf_data['models']
        assert len(models) == 20
        
        # 验证优先级分布
        high_priority = [m for m in models if m.priority >= 8]
        low_priority = [m for m in models if m.priority <= 3]
        
        assert len(high_priority) > 0
        assert len(low_priority) > 0
    
    @pytest.mark.asyncio
    async def test_async_resource_calculation(self):
        """测试异步资源计算"""
        # 模拟异步资源计算
        async def calculate_memory_requirement(config):
            # 模拟计算延迟
            await asyncio.sleep(0.01)
            return config.priority * 1024  # 简单的计算逻辑
        
        model_config = TestDataGenerator.create_model_configs(1)[0]
        result = await calculate_memory_requirement(model_config)
        
        assert result == model_config.priority * 1024
    
    def test_gpu_memory_calculation(self, sample_gpu_info):
        """测试GPU内存计算"""
        total_memory = sum(gpu.memory_total for gpu in sample_gpu_info)
        used_memory = sum(gpu.memory_used for gpu in sample_gpu_info)
        free_memory = sum(gpu.memory_free for gpu in sample_gpu_info)
        
        assert total_memory == used_memory + free_memory
        assert total_memory == 24576 * 2  # 两个GPU，每个24GB
    
    def test_model_resource_matching(self, sample_model_configs, sample_gpu_info):
        """测试模型资源匹配"""
        # 简单的资源匹配逻辑测试
        for model in sample_model_configs:
            required_memory = model.resource_requirements.gpu_memory
            
            # 查找有足够内存的GPU
            suitable_gpus = [
                gpu for gpu in sample_gpu_info 
                if gpu.memory_free >= required_memory
            ]
            
            # 验证至少有一个GPU可以满足需求（基于我们的测试数据）
            if required_memory <= 16384:  # 如果需求不超过16GB
                assert len(suitable_gpus) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])