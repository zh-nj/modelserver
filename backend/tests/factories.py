"""
测试数据工厂
用于生成测试所需的模拟数据
"""
import factory
from datetime import datetime, timedelta
from typing import List, Dict, Any
import random

from app.models.schemas import (
    ModelConfig, GPUInfo, ResourceRequirement, HealthCheckConfig, 
    RetryPolicy, ModelInfo, AlertRule
)
from app.models.enums import (
    FrameworkType, ModelStatus, HealthStatus, GPUVendor, AlertLevel
)


class ResourceRequirementFactory(factory.Factory):
    """资源需求工厂"""
    class Meta:
        model = ResourceRequirement
    
    gpu_memory = factory.Faker('random_int', min=1024, max=24576)  # 1GB-24GB
    gpu_devices = factory.LazyFunction(lambda: [random.randint(0, 3)])


class HealthCheckConfigFactory(factory.Factory):
    """健康检查配置工厂"""
    class Meta:
        model = HealthCheckConfig
    
    enabled = True
    interval = factory.Faker('random_int', min=10, max=300)
    timeout = factory.Faker('random_int', min=5, max=30)
    max_failures = factory.Faker('random_int', min=1, max=5)
    endpoint = factory.Faker('random_element', elements=['/health', '/status', '/ping'])


class RetryPolicyFactory(factory.Factory):
    """重试策略工厂"""
    class Meta:
        model = RetryPolicy
    
    enabled = True
    max_attempts = factory.Faker('random_int', min=1, max=5)
    initial_delay = factory.Faker('random_int', min=1, max=10)
    max_delay = factory.Faker('random_int', min=30, max=300)
    backoff_factor = factory.Faker('pyfloat', min_value=1.0, max_value=3.0)


class ModelConfigFactory(factory.Factory):
    """模型配置工厂"""
    class Meta:
        model = ModelConfig
    
    id = factory.Sequence(lambda n: f"model_{n}")
    name = factory.Faker('sentence', nb_words=2)
    framework = factory.Faker('random_element', elements=list(FrameworkType))
    model_path = factory.Faker('file_path', depth=3, extension='gguf')
    priority = factory.Faker('random_int', min=1, max=10)
    gpu_devices = factory.LazyFunction(lambda: [random.randint(0, 3)])
    
    @factory.lazy_attribute
    def parameters(self) -> Dict[str, Any]:
        """生成框架特定的参数"""
        base_params = {
            'port': random.randint(8000, 9000),
            'host': '127.0.0.1'
        }
        
        if self.framework == FrameworkType.LLAMA_CPP:
            base_params.update({
                'ctx_size': random.choice([2048, 4096, 8192]),
                'n_gpu_layers': random.randint(0, 50),
                'n_threads': random.randint(1, 8)
            })
        elif self.framework == FrameworkType.VLLM:
            base_params.update({
                'tensor_parallel_size': random.choice([1, 2, 4]),
                'gpu_memory_utilization': round(random.uniform(0.7, 0.95), 2),
                'max_num_seqs': random.randint(64, 512)
            })
        
        return base_params
    
    resource_requirements = factory.SubFactory(ResourceRequirementFactory)
    health_check = factory.SubFactory(HealthCheckConfigFactory)
    retry_policy = factory.SubFactory(RetryPolicyFactory)


class GPUInfoFactory(factory.Factory):
    """GPU信息工厂"""
    class Meta:
        model = GPUInfo
    
    device_id = factory.Sequence(lambda n: n)
    name = factory.Faker('random_element', elements=[
        'NVIDIA RTX 4090', 'NVIDIA RTX 4080', 'NVIDIA RTX 3090',
        'AMD RX 7900 XTX', 'AMD RX 6900 XT'
    ])
    
    @factory.lazy_attribute
    def vendor(self) -> GPUVendor:
        """根据GPU名称确定厂商"""
        if 'NVIDIA' in self.name:
            return GPUVendor.NVIDIA
        elif 'AMD' in self.name:
            return GPUVendor.AMD
        else:
            return GPUVendor.UNKNOWN
    
    memory_total = factory.Faker('random_element', elements=[8192, 12288, 16384, 24576])
    
    @factory.lazy_attribute
    def memory_used(self) -> int:
        """生成合理的已使用内存"""
        return random.randint(0, int(self.memory_total * 0.9))
    
    @factory.lazy_attribute
    def memory_free(self) -> int:
        """计算剩余内存"""
        return self.memory_total - self.memory_used
    
    utilization = factory.Faker('pyfloat', min_value=0.0, max_value=100.0)
    temperature = factory.Faker('pyfloat', min_value=30.0, max_value=85.0)
    power_usage = factory.Faker('pyfloat', min_value=50.0, max_value=400.0)


class ModelInfoFactory(factory.Factory):
    """模型信息工厂"""
    class Meta:
        model = ModelInfo
    
    id = factory.Sequence(lambda n: f"model_{n}")
    name = factory.Faker('sentence', nb_words=2)
    framework = factory.Faker('random_element', elements=list(FrameworkType))
    status = factory.Faker('random_element', elements=list(ModelStatus))
    priority = factory.Faker('random_int', min=1, max=10)
    gpu_devices = factory.LazyFunction(lambda: [random.randint(0, 3)])
    
    @factory.lazy_attribute
    def endpoint(self) -> str:
        """生成端点URL"""
        port = random.randint(8000, 9000)
        return f"http://127.0.0.1:{port}"


# AlertCondition 类不存在，暂时移除


class AlertRuleFactory(factory.Factory):
    """告警规则工厂"""
    class Meta:
        model = AlertRule
    
    id = factory.Sequence(lambda n: f"alert_rule_{n}")
    name = factory.Faker('sentence', nb_words=3)
    condition = factory.Faker('sentence', nb_words=5)  # 简化为字符串
    threshold = factory.Faker('pyfloat', min_value=0.0, max_value=100.0)
    level = factory.Faker('random_element', elements=list(AlertLevel))
    enabled = factory.Faker('boolean', chance_of_getting_true=80)


class TestDataGenerator:
    """测试数据生成器"""
    
    @staticmethod
    def create_model_configs(count: int = 5) -> List[ModelConfig]:
        """创建多个模型配置"""
        return ModelConfigFactory.create_batch(count)
    
    @staticmethod
    def create_gpu_cluster(gpu_count: int = 4) -> List[GPUInfo]:
        """创建GPU集群信息"""
        gpus = []
        for i in range(gpu_count):
            gpu = GPUInfoFactory.create(device_id=i)
            gpus.append(gpu)
        return gpus
    
    @staticmethod
    def create_mixed_model_statuses(count: int = 10) -> List[ModelInfo]:
        """创建混合状态的模型信息"""
        models = []
        statuses = list(ModelStatus)
        healths = list(HealthStatus)
        
        for i in range(count):
            model = ModelInfoFactory.create(
                status=random.choice(statuses),
                health=random.choice(healths)
            )
            models.append(model)
        
        return models
    
    @staticmethod
    def create_high_priority_models(count: int = 3) -> List[ModelConfig]:
        """创建高优先级模型配置"""
        return ModelConfigFactory.create_batch(
            count, 
            priority=factory.Faker('random_int', min=8, max=10)
        )
    
    @staticmethod
    def create_low_priority_models(count: int = 3) -> List[ModelConfig]:
        """创建低优先级模型配置"""
        return ModelConfigFactory.create_batch(
            count,
            priority=factory.Faker('random_int', min=1, max=3)
        )
    
    @staticmethod
    def create_resource_constrained_scenario() -> Dict[str, Any]:
        """创建资源受限场景"""
        # 创建有限的GPU资源
        gpus = [
            GPUInfoFactory.create(
                device_id=0,
                memory_total=8192,
                memory_used=6144,  # 大部分已使用
                memory_free=2048
            ),
            GPUInfoFactory.create(
                device_id=1,
                memory_total=8192,
                memory_used=7168,  # 几乎满载
                memory_free=1024
            )
        ]
        
        # 创建需要大量资源的模型
        high_resource_models = ModelConfigFactory.create_batch(
            3,
            resource_requirements=factory.SubFactory(
                ResourceRequirementFactory,
                gpu_memory=factory.Faker('random_int', min=6144, max=8192)
            )
        )
        
        return {
            'gpus': gpus,
            'models': high_resource_models,
            'scenario': 'resource_constrained'
        }
    
    @staticmethod
    def create_alert_rules_set() -> List[AlertRule]:
        """创建一套完整的告警规则"""
        rules = [
            AlertRuleFactory.create(
                id="gpu_high_utilization",
                name="GPU使用率过高",
                condition="GPU utilization > 90%",
                threshold=90.0,
                level=AlertLevel.WARNING
            ),
            AlertRuleFactory.create(
                id="gpu_high_temperature",
                name="GPU温度过高",
                condition="GPU temperature > 80°C",
                threshold=80.0,
                level=AlertLevel.CRITICAL
            ),
            AlertRuleFactory.create(
                id="model_health_failed",
                name="模型健康检查失败",
                condition="Model health status == unhealthy",
                threshold=1.0,
                level=AlertLevel.CRITICAL
            ),
            AlertRuleFactory.create(
                id="high_response_time",
                name="响应时间过长",
                condition="Response time > 2000ms",
                threshold=2000.0,
                level=AlertLevel.WARNING
            )
        ]
        return rules
    
    @staticmethod
    def create_performance_test_data(model_count: int = 50) -> Dict[str, Any]:
        """创建性能测试数据"""
        models = ModelConfigFactory.create_batch(model_count)
        gpus = TestDataGenerator.create_gpu_cluster(8)  # 8个GPU
        
        # 创建不同优先级分布
        for i, model in enumerate(models):
            if i < 10:
                model.priority = random.randint(8, 10)  # 高优先级
            elif i < 30:
                model.priority = random.randint(4, 7)   # 中优先级
            else:
                model.priority = random.randint(1, 3)   # 低优先级
        
        return {
            'models': models,
            'gpus': gpus,
            'scenario': 'performance_test'
        }


# 便捷函数
def create_sample_model_config(**kwargs) -> ModelConfig:
    """创建示例模型配置"""
    return ModelConfigFactory.create(**kwargs)


def create_sample_gpu_info(**kwargs) -> GPUInfo:
    """创建示例GPU信息"""
    return GPUInfoFactory.create(**kwargs)


def create_sample_model_info(**kwargs) -> ModelInfo:
    """创建示例模型信息"""
    return ModelInfoFactory.create(**kwargs)


def create_sample_alert_rule(**kwargs) -> AlertRule:
    """创建示例告警规则"""
    return AlertRuleFactory.create(**kwargs)