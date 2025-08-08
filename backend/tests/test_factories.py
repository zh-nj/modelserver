"""
测试数据工厂验证测试
"""
import pytest
from tests.factories import (
    ModelConfigFactory, GPUInfoFactory, ModelInfoFactory, 
    TestDataGenerator, create_sample_model_config
)
from app.models.enums import FrameworkType, ModelStatus, HealthStatus, GPUVendor


class TestFactories:
    """测试数据工厂测试"""
    
    def test_model_config_factory(self):
        """测试模型配置工厂"""
        config = ModelConfigFactory.create()
        
        assert config.id is not None
        assert config.name is not None
        assert config.framework in list(FrameworkType)
        assert config.model_path is not None
        assert 1 <= config.priority <= 10
        assert len(config.gpu_devices) > 0
        assert isinstance(config.parameters, dict)
        assert config.resource_requirements is not None
    
    def test_gpu_info_factory(self):
        """测试GPU信息工厂"""
        gpu = GPUInfoFactory.create()
        
        assert gpu.device_id >= 0
        assert gpu.name is not None
        assert gpu.vendor in list(GPUVendor)
        assert gpu.memory_total > 0
        assert gpu.memory_used >= 0
        assert gpu.memory_free >= 0
        assert gpu.memory_total == gpu.memory_used + gpu.memory_free
        assert 0 <= gpu.utilization <= 100
        assert gpu.temperature > 0
        assert gpu.power_usage > 0
    
    def test_model_info_factory(self):
        """测试模型信息工厂"""
        model = ModelInfoFactory.create()
        
        assert model.id is not None
        assert model.name is not None
        assert model.framework in list(FrameworkType)
        assert model.status in list(ModelStatus)
        assert model.priority >= 1 and model.priority <= 10
        assert len(model.gpu_devices) > 0
        assert model.api_endpoint is None or isinstance(model.api_endpoint, str)
    
    def test_test_data_generator(self):
        """测试数据生成器测试"""
        # 测试创建模型配置
        configs = TestDataGenerator.create_model_configs(5)
        assert len(configs) == 5
        for config in configs:
            assert config.id is not None
            assert config.name is not None
        
        # 测试创建GPU集群
        gpus = TestDataGenerator.create_gpu_cluster(4)
        assert len(gpus) == 4
        for i, gpu in enumerate(gpus):
            assert gpu.device_id == i
        
        # 测试创建高优先级模型
        high_priority = TestDataGenerator.create_high_priority_models(3)
        assert len(high_priority) == 3
        for model in high_priority:
            assert model.priority >= 8
        
        # 测试创建低优先级模型
        low_priority = TestDataGenerator.create_low_priority_models(3)
        assert len(low_priority) == 3
        for model in low_priority:
            assert model.priority <= 3
    
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
            assert gpu.memory_free < gpu.memory_total * 0.5  # 可用内存少于50%
        
        # 验证模型需要大量资源
        models = scenario['models']
        for model in models:
            assert model.resource_requirements.gpu_memory >= 6144  # 至少需要6GB
    
    def test_performance_test_data(self):
        """测试性能测试数据"""
        perf_data = TestDataGenerator.create_performance_test_data(50)
        
        assert 'models' in perf_data
        assert 'gpus' in perf_data
        assert 'scenario' in perf_data
        assert perf_data['scenario'] == 'performance_test'
        
        models = perf_data['models']
        assert len(models) == 50
        
        # 验证优先级分布
        high_priority = [m for m in models if m.priority >= 8]
        medium_priority = [m for m in models if 4 <= m.priority <= 7]
        low_priority = [m for m in models if m.priority <= 3]
        
        assert len(high_priority) > 0
        assert len(medium_priority) > 0
        assert len(low_priority) > 0
        
        gpus = perf_data['gpus']
        assert len(gpus) == 8
    
    def test_create_sample_functions(self):
        """测试便捷创建函数"""
        model_config = create_sample_model_config()
        assert model_config.id is not None
        assert model_config.name is not None
        
        # 测试带参数的创建
        custom_config = create_sample_model_config(
            priority=9,
            framework=FrameworkType.VLLM
        )
        assert custom_config.priority == 9
        assert custom_config.framework == FrameworkType.VLLM
    
    def test_alert_rules_set(self):
        """测试告警规则集合"""
        rules = TestDataGenerator.create_alert_rules_set()
        
        assert len(rules) == 4
        
        # 验证规则类型
        rule_ids = [rule.id for rule in rules]
        expected_ids = [
            "gpu_high_utilization",
            "gpu_high_temperature", 
            "model_health_failed",
            "high_response_time"
        ]
        
        for expected_id in expected_ids:
            assert expected_id in rule_ids
        
        # 验证规则配置
        for rule in rules:
            assert rule.id is not None
            assert rule.name is not None
            assert rule.condition is not None
            assert rule.level is not None
    
    def test_batch_creation(self):
        """测试批量创建"""
        # 批量创建模型配置
        configs = ModelConfigFactory.create_batch(10)
        assert len(configs) == 10
        
        # 验证每个配置都是唯一的
        ids = [config.id for config in configs]
        assert len(set(ids)) == 10  # 所有ID都应该是唯一的
        
        # 批量创建GPU信息
        gpus = GPUInfoFactory.create_batch(5)
        assert len(gpus) == 5
        
        # 验证设备ID都是有效的（不需要连续，因为factory.Sequence是全局的）
        device_ids = [gpu.device_id for gpu in gpus]
        assert len(device_ids) == 5
        assert all(isinstance(device_id, int) and device_id >= 0 for device_id in device_ids)
    
    def test_factory_consistency(self):
        """测试工厂一致性"""
        # 多次创建应该产生不同的对象
        config1 = ModelConfigFactory.create()
        config2 = ModelConfigFactory.create()
        
        assert config1.id != config2.id
        assert config1.name != config2.name
        
        # 但应该符合相同的约束
        assert type(config1.priority) == type(config2.priority)
        assert type(config1.framework) == type(config2.framework)
    
    def test_factory_parameters(self):
        """测试工厂参数化"""
        # 测试llama.cpp参数
        llama_config = ModelConfigFactory.create(framework=FrameworkType.LLAMA_CPP)
        assert llama_config.framework == FrameworkType.LLAMA_CPP
        assert 'ctx_size' in llama_config.parameters
        assert 'n_gpu_layers' in llama_config.parameters
        
        # 测试vLLM参数
        vllm_config = ModelConfigFactory.create(framework=FrameworkType.VLLM)
        assert vllm_config.framework == FrameworkType.VLLM
        assert 'tensor_parallel_size' in vllm_config.parameters
        assert 'gpu_memory_utilization' in vllm_config.parameters


if __name__ == "__main__":
    pytest.main([__file__, "-v"])