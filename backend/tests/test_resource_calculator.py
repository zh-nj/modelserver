"""
资源需求计算器测试
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from app.utils.resource_calculator import ResourceCalculator, resource_calculator
from app.models.schemas import ModelConfig, ResourceRequirement, GPUInfo, ResourceAllocation
from app.models.enums import FrameworkType, GPUVendor


class TestResourceCalculator:
    """资源计算器测试"""
    
    @pytest.fixture
    def calculator(self):
        """创建资源计算器实例"""
        return ResourceCalculator()
    
    @pytest.fixture
    def sample_model_config(self):
        """创建示例模型配置"""
        return ModelConfig(
            id="test-model",
            name="llama-7b-chat",
            framework=FrameworkType.LLAMA_CPP,
            model_path="/models/llama-7b.gguf",
            priority=5,
            gpu_devices=[0],
            parameters={
                "model_size_gb": 7.0,
                "precision": "fp16",
                "context_length": 2048,
                "batch_size": 1
            },
            resource_requirements=ResourceRequirement(
                gpu_memory=8192,
                gpu_devices=[0]
            )
        )
    
    @pytest.fixture
    def sample_gpus(self):
        """创建示例GPU列表"""
        return [
            GPUInfo(
                device_id=0,
                name="NVIDIA RTX 4090",
                vendor=GPUVendor.NVIDIA,
                memory_total=24576,
                memory_used=2048,
                memory_free=22528,
                utilization=10.0,
                temperature=45.0,
                power_usage=150.0,
                driver_version="525.60.11"
            ),
            GPUInfo(
                device_id=1,
                name="NVIDIA RTX 4080",
                vendor=GPUVendor.NVIDIA,
                memory_total=16384,
                memory_used=1024,
                memory_free=15360,
                utilization=5.0,
                temperature=40.0,
                power_usage=120.0,
                driver_version="525.60.11"
            )
        ]
    
    def test_calculate_model_memory_requirement_basic(self, calculator, sample_model_config):
        """测试基本模型内存需求计算"""
        requirement = calculator.calculate_model_memory_requirement(sample_model_config)
        
        assert isinstance(requirement, ResourceRequirement)
        assert requirement.gpu_memory > 0
        assert requirement.gpu_devices == [0]
        assert requirement.cpu_cores > 0
        assert requirement.system_memory > 0
    
    def test_calculate_model_memory_requirement_different_frameworks(self, calculator):
        """测试不同框架的内存需求计算"""
        base_config = ModelConfig(
            id="test",
            name="test-model",
            framework=FrameworkType.LLAMA_CPP,
            model_path="/test",
            priority=5,
            gpu_devices=[],
            parameters={"model_size_gb": 7.0, "precision": "fp16"},
            resource_requirements=ResourceRequirement(gpu_memory=1000)
        )
        
        frameworks = [FrameworkType.LLAMA_CPP, FrameworkType.VLLM, FrameworkType.DOCKER]
        requirements = []
        
        for framework in frameworks:
            config = base_config.model_copy()
            config.framework = framework
            req = calculator.calculate_model_memory_requirement(config)
            requirements.append(req)
        
        # vLLM应该需要更多内存
        assert requirements[1].gpu_memory > requirements[0].gpu_memory  # vLLM > llama.cpp
        assert requirements[2].gpu_memory > requirements[0].gpu_memory  # Docker > llama.cpp
    
    def test_extract_model_size_from_parameters(self, calculator, sample_model_config):
        """测试从参数中提取模型大小"""
        size = calculator._extract_model_size(sample_model_config)
        assert size == 7.0
    
    def test_extract_model_size_from_name(self, calculator):
        """测试从模型名称推断大小"""
        config = ModelConfig(
            id="test",
            name="llama-13b-instruct",
            framework=FrameworkType.LLAMA_CPP,
            model_path="/test",
            priority=5,
            gpu_devices=[],
            parameters={},
            resource_requirements=ResourceRequirement(gpu_memory=1000)
        )
        
        size = calculator._extract_model_size(config)
        assert size == 13.0
    
    def test_extract_model_size_from_file(self, calculator):
        """测试从文件大小推断模型大小"""
        config = ModelConfig(
            id="test",
            name="unknown-model",
            framework=FrameworkType.LLAMA_CPP,
            model_path="/nonexistent/path",
            priority=5,
            gpu_devices=[],
            parameters={},
            resource_requirements=ResourceRequirement(gpu_memory=1000)
        )
        
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=7 * 1024**3):  # 7GB文件
            
            size = calculator._extract_model_size(config)
            assert size == 10.5  # 7GB * 1.5
    
    def test_extract_precision_from_parameters(self, calculator, sample_model_config):
        """测试从参数中提取精度"""
        precision = calculator._extract_precision(sample_model_config)
        assert precision == "fp16"
    
    def test_extract_precision_from_quantization(self, calculator):
        """测试从量化参数推断精度"""
        config = ModelConfig(
            id="test",
            name="test-model",
            framework=FrameworkType.LLAMA_CPP,
            model_path="/test",
            priority=5,
            gpu_devices=[],
            parameters={"quantization": "int8"},
            resource_requirements=ResourceRequirement(gpu_memory=1000)
        )
        
        precision = calculator._extract_precision(config)
        assert precision == "int8"
    
    def test_extract_precision_from_name(self, calculator):
        """测试从模型名称推断精度"""
        config = ModelConfig(
            id="test",
            name="llama-7b-q4",
            framework=FrameworkType.LLAMA_CPP,
            model_path="/test",
            priority=5,
            gpu_devices=[],
            parameters={},
            resource_requirements=ResourceRequirement(gpu_memory=1000)
        )
        
        precision = calculator._extract_precision(config)
        assert precision == "int4"
    
    def test_extract_context_length(self, calculator, sample_model_config):
        """测试提取上下文长度"""
        context_length = calculator._extract_context_length(sample_model_config)
        assert context_length == 2048
    
    def test_extract_batch_size(self, calculator, sample_model_config):
        """测试提取批处理大小"""
        batch_size = calculator._extract_batch_size(sample_model_config)
        assert batch_size == 1
    
    def test_calculate_base_model_memory(self, calculator):
        """测试基础模型内存计算"""
        # 测试不同精度
        memory_fp32 = calculator._calculate_base_model_memory(7.0, "fp32", FrameworkType.LLAMA_CPP)
        memory_fp16 = calculator._calculate_base_model_memory(7.0, "fp16", FrameworkType.LLAMA_CPP)
        memory_int8 = calculator._calculate_base_model_memory(7.0, "int8", FrameworkType.LLAMA_CPP)
        
        assert memory_fp32 > memory_fp16 > memory_int8
        
        # 测试不同框架
        memory_llama = calculator._calculate_base_model_memory(7.0, "fp16", FrameworkType.LLAMA_CPP)
        memory_vllm = calculator._calculate_base_model_memory(7.0, "fp16", FrameworkType.VLLM)
        
        assert memory_vllm > memory_llama
    
    def test_calculate_context_memory(self, calculator):
        """测试上下文内存计算"""
        # 测试不同上下文长度
        memory_2k = calculator._calculate_context_memory(7.0, 2048, 1, "fp16")
        memory_4k = calculator._calculate_context_memory(7.0, 4096, 1, "fp16")
        
        assert memory_4k > memory_2k
        
        # 测试不同批处理大小
        memory_batch1 = calculator._calculate_context_memory(7.0, 2048, 1, "fp16")
        memory_batch4 = calculator._calculate_context_memory(7.0, 2048, 4, "fp16")
        
        assert memory_batch4 > memory_batch1
    
    def test_estimate_cpu_cores(self, calculator, sample_model_config):
        """测试CPU核心估算"""
        cpu_cores = calculator._estimate_cpu_cores(sample_model_config)
        assert cpu_cores > 0
        
        # 测试不同框架
        sample_model_config.framework = FrameworkType.VLLM
        vllm_cores = calculator._estimate_cpu_cores(sample_model_config)
        
        sample_model_config.framework = FrameworkType.LLAMA_CPP
        llama_cores = calculator._estimate_cpu_cores(sample_model_config)
        
        assert vllm_cores >= llama_cores
    
    def test_estimate_system_memory(self, calculator):
        """测试系统内存估算"""
        system_memory = calculator._estimate_system_memory(8192)
        assert system_memory >= 2048  # 最小值
        assert system_memory <= 8192  # 不超过GPU内存
    
    def test_validate_specific_gpu_allocation_success(self, calculator, sample_gpus):
        """测试指定GPU分配验证 - 成功情况"""
        requirement = ResourceRequirement(
            gpu_memory=8192,
            gpu_devices=[0]
        )
        
        is_valid, errors, allocation = calculator.validate_resource_allocation(
            requirement, sample_gpus
        )
        
        assert is_valid
        assert len(errors) == 0
        assert allocation is not None
        assert allocation.gpu_devices == [0]
        assert allocation.memory_allocated == 8192
    
    def test_validate_specific_gpu_allocation_insufficient_memory(self, calculator, sample_gpus):
        """测试指定GPU分配验证 - 内存不足"""
        requirement = ResourceRequirement(
            gpu_memory=30000,  # 超过单个GPU内存
            gpu_devices=[0]
        )
        
        is_valid, errors, allocation = calculator.validate_resource_allocation(
            requirement, sample_gpus
        )
        
        assert not is_valid
        assert len(errors) > 0
        assert allocation is None
    
    def test_validate_specific_gpu_allocation_missing_gpu(self, calculator, sample_gpus):
        """测试指定GPU分配验证 - GPU不存在"""
        requirement = ResourceRequirement(
            gpu_memory=8192,
            gpu_devices=[999]  # 不存在的GPU
        )
        
        is_valid, errors, allocation = calculator.validate_resource_allocation(
            requirement, sample_gpus
        )
        
        assert not is_valid
        assert len(errors) > 0
        assert "不存在" in errors[0]
        assert allocation is None
    
    def test_validate_specific_gpu_allocation_multi_gpu(self, calculator, sample_gpus):
        """测试多GPU分配验证"""
        requirement = ResourceRequirement(
            gpu_memory=30000,  # 需要多个GPU
            gpu_devices=[0, 1]
        )
        
        is_valid, errors, allocation = calculator.validate_resource_allocation(
            requirement, sample_gpus
        )
        
        assert is_valid  # 总内存足够
        assert len(errors) == 0
        assert allocation is not None
        assert set(allocation.gpu_devices) == {0, 1}
    
    def test_validate_automatic_gpu_allocation_single_gpu(self, calculator, sample_gpus):
        """测试自动GPU分配 - 单GPU"""
        requirement = ResourceRequirement(
            gpu_memory=8192,
            gpu_devices=[]  # 自动分配
        )
        
        is_valid, errors, allocation = calculator.validate_resource_allocation(
            requirement, sample_gpus
        )
        
        assert is_valid
        assert len(errors) == 0
        assert allocation is not None
        assert len(allocation.gpu_devices) == 1
        assert allocation.gpu_devices[0] == 0  # 应该选择内存最大的GPU
    
    def test_validate_automatic_gpu_allocation_multi_gpu(self, calculator, sample_gpus):
        """测试自动GPU分配 - 多GPU"""
        requirement = ResourceRequirement(
            gpu_memory=35000,  # 需要多个GPU
            gpu_devices=[]
        )
        
        is_valid, errors, allocation = calculator.validate_resource_allocation(
            requirement, sample_gpus
        )
        
        assert is_valid
        assert len(errors) == 0
        assert allocation is not None
        assert len(allocation.gpu_devices) == 2
    
    def test_validate_automatic_gpu_allocation_insufficient_memory(self, calculator, sample_gpus):
        """测试自动GPU分配 - 总内存不足"""
        requirement = ResourceRequirement(
            gpu_memory=50000,  # 超过所有GPU总内存
            gpu_devices=[]
        )
        
        is_valid, errors, allocation = calculator.validate_resource_allocation(
            requirement, sample_gpus
        )
        
        assert not is_valid
        assert len(errors) > 0
        assert "内存不足" in errors[0]
        assert allocation is None
    
    def test_validate_resource_allocation_no_gpus(self, calculator):
        """测试无GPU情况下的资源分配验证"""
        requirement = ResourceRequirement(
            gpu_memory=8192,
            gpu_devices=[]
        )
        
        is_valid, errors, allocation = calculator.validate_resource_allocation(
            requirement, []
        )
        
        assert not is_valid
        assert len(errors) > 0
        assert "没有可用的GPU" in errors[0]
        assert allocation is None
    
    def test_calculate_memory_fragmentation(self, calculator, sample_gpus):
        """测试内存碎片化计算"""
        fragmentation = calculator.calculate_memory_fragmentation(sample_gpus)
        
        assert 'total_memory' in fragmentation
        assert 'used_memory' in fragmentation
        assert 'free_memory' in fragmentation
        assert 'fragmentation_ratio' in fragmentation
        assert 'largest_free_block' in fragmentation
        assert 'gpu_count' in fragmentation
        assert 'average_utilization' in fragmentation
        
        assert fragmentation['total_memory'] == 24576 + 16384
        assert fragmentation['used_memory'] == 2048 + 1024
        assert fragmentation['free_memory'] == 22528 + 15360
        assert fragmentation['gpu_count'] == 2
        assert 0 <= fragmentation['fragmentation_ratio'] <= 1
    
    def test_calculate_memory_fragmentation_empty(self, calculator):
        """测试空GPU列表的碎片化计算"""
        fragmentation = calculator.calculate_memory_fragmentation([])
        
        assert fragmentation['total_memory'] == 0
        assert fragmentation['gpu_count'] == 0
        assert fragmentation['fragmentation_ratio'] == 0.0
    
    def test_suggest_optimal_allocation(self, calculator, sample_gpus):
        """测试最优分配建议"""
        requirements = [
            ResourceRequirement(gpu_memory=8192, gpu_devices=[]),
            ResourceRequirement(gpu_memory=16384, gpu_devices=[]),
            ResourceRequirement(gpu_memory=4096, gpu_devices=[])
        ]
        
        allocations = calculator.suggest_optimal_allocation(requirements, sample_gpus)
        
        assert len(allocations) == 3
        
        # 检查分配结果
        for req_index, allocation in allocations:
            assert 0 <= req_index < 3
            # 前两个需求应该能够分配，第三个可能无法分配（取决于剩余资源）
    
    def test_suggest_optimal_allocation_priority_order(self, calculator, sample_gpus):
        """测试最优分配的优先级顺序"""
        requirements = [
            ResourceRequirement(gpu_memory=4096, gpu_devices=[]),   # 小需求
            ResourceRequirement(gpu_memory=20000, gpu_devices=[]),  # 大需求
            ResourceRequirement(gpu_memory=8192, gpu_devices=[])    # 中等需求
        ]
        
        allocations = calculator.suggest_optimal_allocation(requirements, sample_gpus)
        
        # 应该按内存需求降序处理：大需求(索引1) -> 中等需求(索引2) -> 小需求(索引0)
        processed_order = [alloc[0] for alloc in allocations]
        assert processed_order[0] == 1  # 大需求先处理
    
    def test_error_handling_in_calculate_model_memory_requirement(self, calculator):
        """测试内存需求计算的错误处理"""
        # 创建一个会导致错误的配置
        invalid_config = ModelConfig(
            id="test",
            name="test-model",
            framework=FrameworkType.LLAMA_CPP,
            model_path="/nonexistent",
            priority=5,
            gpu_devices=[],
            parameters={"invalid_param": "invalid_value"},
            resource_requirements=ResourceRequirement(gpu_memory=1000)
        )
        
        # 模拟内部方法抛出异常
        with patch.object(calculator, '_extract_model_size', side_effect=Exception("Test error")):
            requirement = calculator.calculate_model_memory_requirement(invalid_config)
            
            # 应该返回默认值而不是抛出异常
            assert isinstance(requirement, ResourceRequirement)
            assert requirement.gpu_memory == 8192  # 默认值
    
    def test_global_resource_calculator_instance(self):
        """测试全局资源计算器实例"""
        assert resource_calculator is not None
        assert isinstance(resource_calculator, ResourceCalculator)


if __name__ == "__main__":
    pytest.main([__file__])