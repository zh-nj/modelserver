"""
测试附加参数功能
"""
import pytest
from unittest.mock import Mock, patch
from app.adapters.llama_cpp import LlamaCppAdapter
from app.adapters.vllm import VllmAdapter
from app.models.schemas import ModelConfig, ResourceRequirement, HealthCheckConfig, RetryPolicy
from app.models.enums import FrameworkType

class TestAdditionalParameters:
    """测试附加参数功能"""
    
    def setup_method(self):
        """测试前设置"""
        self.llama_adapter = LlamaCppAdapter(FrameworkType.LLAMA_CPP)
        self.vllm_adapter = VllmAdapter(FrameworkType.VLLM)
        
        # 基础模型配置
        self.base_config = ModelConfig(
            id="test-model",
            name="测试模型",
            framework=FrameworkType.LLAMA_CPP,
            model_path="/path/to/model.gguf",
            priority=5,
            gpu_devices=[0],
            parameters={
                "port": 8080,
                "host": "0.0.0.0",
                "ctx_size": 2048
            },
            resource_requirements=ResourceRequirement(
                gpu_memory=4096,
                gpu_devices=[0]
            ),
            health_check=HealthCheckConfig(),
            retry_policy=RetryPolicy()
        )
    
    def test_parse_additional_parameters_empty(self):
        """测试空附加参数"""
        # 测试None
        result = self.llama_adapter._parse_additional_parameters(None)
        assert result == []
        
        # 测试空字符串
        result = self.llama_adapter._parse_additional_parameters("")
        assert result == []
        
        # 测试只有空格
        result = self.llama_adapter._parse_additional_parameters("   ")
        assert result == []
    
    def test_parse_additional_parameters_simple(self):
        """测试简单附加参数"""
        # 测试单个参数
        result = self.llama_adapter._parse_additional_parameters("--verbose")
        assert result == ["--verbose"]
        
        # 测试参数和值
        result = self.llama_adapter._parse_additional_parameters("--temperature 0.7")
        assert result == ["--temperature", "0.7"]
        
        # 测试多个参数
        result = self.llama_adapter._parse_additional_parameters("--temperature 0.7 --top-p 0.9")
        assert result == ["--temperature", "0.7", "--top-p", "0.9"]
    
    def test_parse_additional_parameters_quoted(self):
        """测试带引号的附加参数"""
        # 测试单引号
        result = self.llama_adapter._parse_additional_parameters("--prompt 'Hello world'")
        assert result == ["--prompt", "Hello world"]
        
        # 测试双引号
        result = self.llama_adapter._parse_additional_parameters('--prompt "Hello world"')
        assert result == ["--prompt", "Hello world"]
        
        # 测试包含空格的值
        result = self.llama_adapter._parse_additional_parameters('--system-prompt "You are a helpful assistant"')
        assert result == ["--system-prompt", "You are a helpful assistant"]
    
    def test_parse_additional_parameters_invalid(self):
        """测试无效的附加参数"""
        # 测试不匹配的引号（应该回退到简单分割）
        result = self.llama_adapter._parse_additional_parameters('--prompt "Hello world')
        # 应该回退到简单分割
        assert len(result) > 0
    
    def test_llama_cpp_build_command_with_additional_params(self):
        """测试llama.cpp命令构建包含附加参数"""
        config = self.base_config.copy()
        config.additional_parameters = "--verbose --temperature 0.7"
        
        cmd = self.llama_adapter._build_command_line(config)
        
        # 检查基本参数存在
        assert "llama-server" in cmd
        assert "-m" in cmd
        assert config.model_path in cmd
        
        # 检查附加参数存在
        assert "--verbose" in cmd
        assert "--temperature" in cmd
        assert "0.7" in cmd
    
    def test_vllm_build_command_with_additional_params(self):
        """测试vLLM命令构建包含附加参数"""
        config = self.base_config.copy()
        config.framework = FrameworkType.VLLM
        config.additional_parameters = "--trust-remote-code --max-model-len 4096"
        
        docker_config = self.vllm_adapter._build_docker_config(config)
        cmd = docker_config['command']
        
        # 检查基本参数存在
        assert "python" in cmd
        assert "-m" in cmd
        assert "vllm.entrypoints.openai.api_server" in cmd
        
        # 检查附加参数存在
        assert "--trust-remote-code" in cmd
        assert "--max-model-len" in cmd
        assert "4096" in cmd
    
    def test_additional_parameters_override_defaults(self):
        """测试附加参数覆盖默认参数"""
        config = self.base_config.copy()
        # 设置一个与默认端口不同的附加参数
        config.additional_parameters = "--port 9090"
        
        cmd = self.llama_adapter._build_command_line(config)
        
        # 应该包含两个端口设置（默认的和附加的）
        # 通常命令行中后面的参数会覆盖前面的
        port_indices = [i for i, arg in enumerate(cmd) if arg == "--port"]
        assert len(port_indices) >= 1
        
        # 检查附加的端口参数存在
        assert "9090" in cmd
    
    def test_model_config_schema_with_additional_parameters(self):
        """测试模型配置模式包含附加参数"""
        config_data = {
            "id": "test-model",
            "name": "测试模型",
            "framework": "llama_cpp",
            "model_path": "/path/to/model.gguf",
            "priority": 5,
            "gpu_devices": [0],
            "additional_parameters": "--verbose --temperature 0.7",
            "parameters": {
                "port": 8080,
                "host": "0.0.0.0"
            },
            "resource_requirements": {
                "gpu_memory": 4096,
                "gpu_devices": [0]
            }
        }
        
        # 测试Pydantic模式验证
        config = ModelConfig(**config_data)
        assert config.additional_parameters == "--verbose --temperature 0.7"
        
        # 测试序列化
        config_dict = config.dict()
        assert "additional_parameters" in config_dict
        assert config_dict["additional_parameters"] == "--verbose --temperature 0.7"
    
    def test_model_config_without_additional_parameters(self):
        """测试没有附加参数的模型配置"""
        config_data = {
            "id": "test-model",
            "name": "测试模型",
            "framework": "llama_cpp",
            "model_path": "/path/to/model.gguf",
            "priority": 5,
            "gpu_devices": [0],
            "parameters": {
                "port": 8080,
                "host": "0.0.0.0"
            },
            "resource_requirements": {
                "gpu_memory": 4096,
                "gpu_devices": [0]
            }
        }
        
        # 测试Pydantic模式验证
        config = ModelConfig(**config_data)
        assert config.additional_parameters is None
        
        # 测试命令构建不会失败
        cmd = self.llama_adapter._build_command_line(config)
        assert len(cmd) > 0
    
    @pytest.mark.parametrize("additional_params,expected_count", [
        ("--verbose", 1),
        ("--verbose --temperature 0.7", 3),
        ("--ctx-size 4096 --batch-size 1024", 4),
        ("--system-prompt 'You are helpful'", 2),
    ])
    def test_parameter_parsing_count(self, additional_params, expected_count):
        """测试参数解析数量"""
        result = self.llama_adapter._parse_additional_parameters(additional_params)
        assert len(result) == expected_count
    
    def test_vllm_parse_additional_parameters(self):
        """测试vLLM适配器的参数解析"""
        # 测试基本功能
        result = self.vllm_adapter._parse_additional_parameters("--trust-remote-code")
        assert result == ["--trust-remote-code"]
        
        # 测试多个参数
        result = self.vllm_adapter._parse_additional_parameters("--max-model-len 4096 --dtype float16")
        assert result == ["--max-model-len", "4096", "--dtype", "float16"]
        
        # 测试空参数
        result = self.vllm_adapter._parse_additional_parameters("")
        assert result == []