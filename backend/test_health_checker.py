"""
健康检查系统测试
"""
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.services.model_manager import ModelManager
from app.services.config_manager import FileConfigManager
from app.services.health_checker import ModelHealthChecker, AutoRecoveryManager
from app.models.schemas import ModelConfig, ResourceRequirement, HealthCheckConfig, RetryPolicy
from app.models.enums import FrameworkType, ModelStatus, HealthStatus
from app.adapters.base import FrameworkAdapterFactory, BaseFrameworkAdapter

class TestHealthAdapter(BaseFrameworkAdapter):
    """测试健康检查适配器"""
    
    def __init__(self, framework_type: FrameworkType):
        super().__init__(framework_type)
        self.should_fail = False
        
    async def _do_start_model(self, config: ModelConfig) -> bool:
        self._set_model_info(config.id, {'status': ModelStatus.RUNNING})
        return True
    
    async def _do_stop_model(self, model_id: str) -> bool:
        self._remove_model_info(model_id)
        return True
    
    async def _check_model_process(self, model_id: str) -> bool:
        return model_id in self._running_models
    
    async def check_health(self, model_id: str):
        if self.should_fail:
            return HealthStatus.UNHEALTHY
        return HealthStatus.HEALTHY
    
    async def get_api_endpoint(self, model_id: str) -> str:
        return f"http://localhost:8001/v1/models/{model_id}"
    
    def validate_config(self, config: ModelConfig):
        from app.models.schemas import ValidationResult
        return ValidationResult(is_valid=True, errors=[], warnings=[])

async def test_health_checker():
    """测试健康检查系统"""
    print("开始测试健康检查系统...")
    
    # 注册测试适配器
    FrameworkAdapterFactory.register_adapter(FrameworkType.LLAMA_CPP, TestHealthAdapter)
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    try:
        # 创建配置管理器和模型管理器
        config_manager = FileConfigManager(temp_dir)
        model_manager = ModelManager(config_manager)
        await model_manager.initialize()
        
        # 创建临时模型文件
        model_file = Path(temp_dir) / "test_model.gguf"
        model_file.write_text("fake model content")
        
        # 创建模型配置，启用健康检查
        config = ModelConfig(
            id="test_model",
            name="测试模型",
            framework=FrameworkType.LLAMA_CPP,
            model_path=str(model_file),
            priority=5,
            gpu_devices=[0],
            parameters={"port": 8001, "host": "localhost"},
            resource_requirements=ResourceRequirement(gpu_memory=4096, gpu_devices=[0]),
            health_check=HealthCheckConfig(
                enabled=True,
                interval=2,  # 2秒检查一次
                timeout=5,
                max_failures=2
            ),
            retry_policy=RetryPolicy(
                enabled=True,
                max_attempts=2,
                initial_delay=1
            )
        )
        
        # 测试创建和启动模型
        print("测试创建和启动模型...")
        model_id = await model_manager.create_model(config)
        assert model_id == "test_model"
        
        success = await model_manager.start_model("test_model")
        assert success is True
        print("✓ 模型启动成功")
        
        # 等待健康检查启动
        await asyncio.sleep(1)
        
        # 测试健康状态
        print("测试健康状态检查...")
        health_status = await model_manager.get_model_health("test_model")
        print(f"健康状态: {health_status}")
        
        # 测试手动健康检查
        print("测试手动健康检查...")
        with patch('aiohttp.ClientSession.get') as mock_get:
            # 模拟HTTP响应
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value="OK")
            mock_get.return_value.__aenter__.return_value = mock_response
            
            health_result = await model_manager.manual_health_check("test_model")
            if health_result:
                print(f"✓ 手动健康检查成功: {health_result.status}")
            else:
                print("! 手动健康检查返回None")
        
        # 测试健康指标
        print("测试健康指标...")
        health_metrics = await model_manager.get_model_health_metrics("test_model")
        if health_metrics:
            print(f"✓ 健康指标: 总检查次数={health_metrics.total_checks}, 成功次数={health_metrics.successful_checks}")
        
        # 测试模拟故障
        print("测试模拟故障和自动恢复...")
        
        # 获取适配器并设置故障
        adapter = model_manager._adapters.get("test_model")
        if adapter:
            adapter.should_fail = True
            print("✓ 设置适配器故障模式")
            
            # 等待健康检查检测到故障
            await asyncio.sleep(6)  # 等待几次健康检查
            
            # 检查恢复状态
            recovery_status = model_manager.get_recovery_status("test_model")
            print(f"恢复状态: {recovery_status}")
            
            # 恢复正常
            adapter.should_fail = False
            print("✓ 恢复适配器正常模式")
            
            # 等待恢复
            await asyncio.sleep(3)
        
        # 测试停止模型
        print("测试停止模型...")
        success = await model_manager.stop_model("test_model")
        assert success is True
        print("✓ 模型停止成功")
        
        # 关闭模型管理器
        await model_manager.shutdown()
        print("✓ 模型管理器关闭成功")
        
        print("健康检查系统测试完成！")
        
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)
        FrameworkAdapterFactory._adapters.clear()

async def test_health_checker_standalone():
    """测试独立的健康检查器"""
    print("\n开始测试独立健康检查器...")
    
    health_checker = ModelHealthChecker()
    await health_checker.initialize()
    
    try:
        # 创建临时模型文件
        temp_dir = tempfile.mkdtemp()
        model_file = Path(temp_dir) / "test_model.gguf"
        model_file.write_text("fake model content")
        
        config = ModelConfig(
            id="standalone_test",
            name="独立测试模型",
            framework=FrameworkType.LLAMA_CPP,
            model_path=str(model_file),
            priority=5,
            gpu_devices=[0],
            parameters={"port": 8002, "host": "localhost"},
            resource_requirements=ResourceRequirement(gpu_memory=4096, gpu_devices=[0]),
            health_check=HealthCheckConfig(
                enabled=True,
                interval=1,
                timeout=3,
                max_failures=2
            ),
            retry_policy=RetryPolicy()
        )
        
        def get_endpoint(model_id):
            return "http://localhost:8002"
        
        # 启动健康检查
        await health_checker.start_health_check("standalone_test", config, get_endpoint)
        print("✓ 启动独立健康检查")
        
        # 等待几次检查
        await asyncio.sleep(3)
        
        # 获取健康状态
        status = health_checker.get_health_status("standalone_test")
        print(f"✓ 健康状态: {status}")
        
        # 获取健康指标
        metrics = health_checker.get_health_metrics("standalone_test")
        if metrics:
            print(f"✓ 健康指标: 检查次数={metrics.total_checks}, 失败次数={metrics.failed_checks}")
        
        # 停止健康检查
        await health_checker.stop_health_check("standalone_test")
        print("✓ 停止独立健康检查")
        
        # 清理
        shutil.rmtree(temp_dir)
        
    finally:
        await health_checker.shutdown()
        print("✓ 独立健康检查器关闭成功")

if __name__ == "__main__":
    asyncio.run(test_health_checker())
    asyncio.run(test_health_checker_standalone())