"""
框架适配器测试
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.adapters import FrameworkAdapterFactory, LlamaCppAdapter, VllmAdapter
from app.models.enums import FrameworkType
from app.models.schemas import ModelConfig, ResourceRequirement, HealthCheckConfig, RetryPolicy

@pytest.fixture
def sample_model_config():
    """示例模型配置"""
    return ModelConfig(
        id="test-model",
        name="测试模型",
        framework=FrameworkType.LLAMA_CPP,
        model_path="/path/to/model.gguf",
        priority=5,
        gpu_devices=[0],
        parameters={
            'port': 8080,
            'host': '127.0.0.1',
            'ctx_size': 2048,
            'n_gpu_layers': 32
        },
        resource_requirements=ResourceRequirement(
            gpu_memory=4096,
            gpu_devices=[0]
        ),
        health_check=HealthCheckConfig(),
        retry_policy=RetryPolicy()
    )

class TestFrameworkAdapterFactory:
    """框架适配器工厂测试"""
    
    def test_factory_has_registered_adapters(self):
        """测试工厂已注册适配器"""
        supported_frameworks = FrameworkAdapterFactory.get_supported_frameworks()
        
        assert FrameworkType.LLAMA_CPP in supported_frameworks
        assert FrameworkType.VLLM in supported_frameworks
    
    def test_create_llama_cpp_adapter(self):
        """测试创建llama.cpp适配器"""
        adapter = FrameworkAdapterFactory.create_adapter(FrameworkType.LLAMA_CPP)
        
        assert isinstance(adapter, LlamaCppAdapter)
        assert adapter.framework_type == FrameworkType.LLAMA_CPP
    
    def test_create_vllm_adapter(self):
        """测试创建vLLM适配器"""
        adapter = FrameworkAdapterFactory.create_adapter(FrameworkType.VLLM)
        
        assert isinstance(adapter, VllmAdapter)
        assert adapter.framework_type == FrameworkType.VLLM
    
    def test_create_unsupported_adapter(self):
        """测试创建不支持的适配器"""
        with pytest.raises(ValueError, match="不支持的框架类型"):
            FrameworkAdapterFactory.create_adapter("unsupported_framework")
    
    def test_is_framework_supported(self):
        """测试框架支持检查"""
        assert FrameworkAdapterFactory.is_framework_supported(FrameworkType.LLAMA_CPP)
        assert FrameworkAdapterFactory.is_framework_supported(FrameworkType.VLLM)
        assert not FrameworkAdapterFactory.is_framework_supported("unsupported")

class TestLlamaCppAdapter:
    """llama.cpp适配器测试"""
    
    def test_validate_config_success(self, sample_model_config):
        """测试配置验证成功"""
        adapter = LlamaCppAdapter(FrameworkType.LLAMA_CPP)
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True):
            result = adapter.validate_config(sample_model_config)
            
            assert result.is_valid
            assert len(result.errors) == 0
    
    def test_validate_config_missing_model_file(self, sample_model_config):
        """测试模型文件不存在的配置验证"""
        adapter = LlamaCppAdapter(FrameworkType.LLAMA_CPP)
        
        with patch('pathlib.Path.exists', return_value=False):
            result = adapter.validate_config(sample_model_config)
            
            assert not result.is_valid
            assert any("模型文件不存在" in error for error in result.errors)
    
    def test_validate_config_invalid_port(self, sample_model_config):
        """测试无效端口的配置验证"""
        sample_model_config.parameters['port'] = 99999
        adapter = LlamaCppAdapter(FrameworkType.LLAMA_CPP)
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True):
            result = adapter.validate_config(sample_model_config)
            
            assert not result.is_valid
            assert any("端口必须是1024-65535之间的整数" in error for error in result.errors)
    
    def test_build_command_line(self, sample_model_config):
        """测试命令行构建"""
        adapter = LlamaCppAdapter(FrameworkType.LLAMA_CPP)
        cmd = adapter._build_command_line(sample_model_config)
        
        assert 'llama-server' in cmd
        assert '-m' in cmd
        assert sample_model_config.model_path in cmd
        assert '--host' in cmd
        assert '127.0.0.1' in cmd
        assert '--port' in cmd
        assert '8080' in cmd
        assert '-ngl' in cmd
        assert '32' in cmd
    
    def test_setup_environment_nvidia(self, sample_model_config):
        """测试NVIDIA GPU环境设置"""
        sample_model_config.gpu_devices = [0, 1]
        adapter = LlamaCppAdapter(FrameworkType.LLAMA_CPP)
        
        with patch.dict('os.environ', {}, clear=True):
            env = adapter._setup_environment(sample_model_config)
            
            assert 'CUDA_VISIBLE_DEVICES' in env
            assert env['CUDA_VISIBLE_DEVICES'] == '0,1'
    
    def test_get_default_parameters(self):
        """测试获取默认参数"""
        adapter = LlamaCppAdapter(FrameworkType.LLAMA_CPP)
        defaults = adapter.get_default_parameters()
        
        assert defaults['host'] == '127.0.0.1'
        assert defaults['port'] == 8080
        assert defaults['ctx_size'] == 2048
        assert defaults['n_gpu_layers'] == 0

class TestVllmAdapter:
    """vLLM适配器测试"""
    
    @patch('docker.from_env')
    def test_validate_config_success(self, mock_docker, sample_model_config):
        """测试vLLM配置验证成功"""
        sample_model_config.framework = FrameworkType.VLLM
        sample_model_config.parameters = {
            'port': 8000,
            'host': '0.0.0.0',
            'tensor_parallel_size': 1
        }
        
        # Mock Docker客户端
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.images.get.return_value = Mock()
        mock_docker.return_value = mock_client
        
        adapter = VllmAdapter(FrameworkType.VLLM)
        result = adapter.validate_config(sample_model_config)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    @patch('docker.from_env')
    def test_validate_config_docker_unavailable(self, mock_docker, sample_model_config):
        """测试Docker不可用的配置验证"""
        sample_model_config.framework = FrameworkType.VLLM
        
        # Mock Docker客户端异常
        mock_client = Mock()
        mock_client.ping.side_effect = Exception("Docker daemon not running")
        mock_docker.return_value = mock_client
        
        adapter = VllmAdapter(FrameworkType.VLLM)
        result = adapter.validate_config(sample_model_config)
        
        assert not result.is_valid
        assert any("Docker服务不可用" in error for error in result.errors)
    
    @patch('docker.from_env')
    def test_build_docker_config(self, mock_docker, sample_model_config):
        """测试Docker配置构建"""
        sample_model_config.framework = FrameworkType.VLLM
        sample_model_config.parameters = {
            'port': 8000,
            'host': '0.0.0.0',
            'model_name': 'test-model',
            'tensor_parallel_size': 2,
            'gpu_memory_utilization': 0.8
        }
        
        mock_client = Mock()
        mock_docker.return_value = mock_client
        
        adapter = VllmAdapter(FrameworkType.VLLM)
        config = adapter._build_docker_config(sample_model_config)
        
        assert config['name'] == 'vllm-test-model'
        assert config['ports']['8000/tcp'] == 8000
        assert 'CUDA_VISIBLE_DEVICES' in config['environment']
        assert '--model' in config['command']
        assert 'test-model' in config['command']
        assert '--tensor-parallel-size' in config['command']
        assert '2' in config['command']
    
    @patch('docker.from_env')
    def test_get_default_parameters(self, mock_docker):
        """测试获取默认参数"""
        mock_client = Mock()
        mock_docker.return_value = mock_client
        
        adapter = VllmAdapter(FrameworkType.VLLM)
        defaults = adapter.get_default_parameters()
        
        assert defaults['host'] == '0.0.0.0'
        assert defaults['port'] == 8000
        assert defaults['tensor_parallel_size'] == 1
        assert defaults['gpu_memory_utilization'] == 0.9
        assert defaults['docker_image'] == 'vllm/vllm-openai:latest'

if __name__ == "__main__":
    pytest.main([__file__])