"""
简单的模型管理器测试，用于验证基本功能
"""
import asyncio
import tempfile
import shutil
from pathlib import Path

from app.services.model_manager import ModelManager
from app.services.config_manager import FileConfigManager
from app.models.schemas import ModelConfig, ResourceRequirement, HealthCheckConfig, RetryPolicy
from app.models.enums import FrameworkType, ModelStatus
from app.adapters.base import FrameworkAdapterFactory, BaseFrameworkAdapter

class SimpleTestAdapter(BaseFrameworkAdapter):
    """简单测试适配器"""
    
    def __init__(self, framework_type: FrameworkType):
        super().__init__(framework_type)
        
    async def _do_start_model(self, config: ModelConfig) -> bool:
        self._set_model_info(config.id, {'status': ModelStatus.RUNNING})
        return True
    
    async def _do_stop_model(self, model_id: str) -> bool:
        self._remove_model_info(model_id)
        return True
    
    async def _check_model_process(self, model_id: str) -> bool:
        return model_id in self._running_models
    
    async def check_health(self, model_id: str):
        from app.models.enums import HealthStatus
        return HealthStatus.HEALTHY
    
    async def get_api_endpoint(self, model_id: str) -> str:
        return f"http://localhost:8000/v1/models/{model_id}"
    
    def validate_config(self, config: ModelConfig):
        from app.models.schemas import ValidationResult
        return ValidationResult(is_valid=True, errors=[], warnings=[])

async def test_model_manager():
    """测试模型管理器基本功能"""
    print("开始测试模型管理器...")
    
    # 注册测试适配器
    FrameworkAdapterFactory.register_adapter(FrameworkType.LLAMA_CPP, SimpleTestAdapter)
    
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
        
        # 创建模型配置
        config = ModelConfig(
            id="test_model",
            name="测试模型",
            framework=FrameworkType.LLAMA_CPP,
            model_path=str(model_file),
            priority=5,
            gpu_devices=[0],
            parameters={"port": 8001},
            resource_requirements=ResourceRequirement(gpu_memory=4096, gpu_devices=[0]),
            health_check=HealthCheckConfig(),
            retry_policy=RetryPolicy()
        )
        
        # 测试创建模型
        print("测试创建模型...")
        model_id = await model_manager.create_model(config)
        assert model_id == "test_model"
        print("✓ 模型创建成功")
        
        # 测试列出模型
        print("测试列出模型...")
        models = await model_manager.list_models()
        assert len(models) == 1
        assert models[0].id == "test_model"
        assert models[0].status == ModelStatus.STOPPED
        print("✓ 模型列表正确")
        
        # 测试启动模型
        print("测试启动模型...")
        success = await model_manager.start_model("test_model")
        assert success is True
        
        status = await model_manager.get_model_status("test_model")
        assert status == ModelStatus.RUNNING
        print("✓ 模型启动成功")
        
        # 测试停止模型
        print("测试停止模型...")
        success = await model_manager.stop_model("test_model")
        assert success is True
        
        status = await model_manager.get_model_status("test_model")
        assert status == ModelStatus.STOPPED
        print("✓ 模型停止成功")
        
        # 测试删除模型
        print("测试删除模型...")
        success = await model_manager.delete_model("test_model")
        assert success is True
        
        models = await model_manager.list_models()
        assert len(models) == 0
        print("✓ 模型删除成功")
        
        # 关闭模型管理器
        await model_manager.shutdown()
        print("✓ 模型管理器关闭成功")
        
        print("所有测试通过！")
        
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)
        FrameworkAdapterFactory._adapters.clear()

if __name__ == "__main__":
    asyncio.run(test_model_manager())