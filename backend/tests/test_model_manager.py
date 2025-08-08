"""
模型管理器测试
"""
import pytest
import asyncio
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from app.services.model_manager import ModelManager
from app.services.config_manager import FileConfigManager
from app.models.schemas import (
    ModelConfig, ResourceRequirement, HealthCheckConfig, 
    RetryPolicy, ModelInfo, ValidationResult
)
from app.models.enums import FrameworkType, ModelStatus, HealthStatus
from app.adapters.base import FrameworkAdapterFactory, BaseFrameworkAdapter

class MockAdapter(BaseFrameworkAdapter):
    """模拟适配器用于测试"""
    
    def __init__(self, framework_type: FrameworkType):
        super().__init__(framework_type)
        self.start_success = True
        self.stop_success = True
        self.health_status = HealthStatus.HEALTHY
        
    async def _do_start_model(self, config: ModelConfig) -> bool:
        if self.start_success:
            self._set_model_info(config.id, {
                'status': ModelStatus.RUNNING,
                'config': config,
                'started_at': datetime.now()
            })
        return self.start_success
    
    async def _do_stop_model(self, model_id: str) -> bool:
        if self.stop_success:
            self._remove_model_info(model_id)
        return self.stop_success
    
    async def _check_model_process(self, model_id: str) -> bool:
        return model_id in self._running_models
    
    async def check_health(self, model_id: str) -> HealthStatus:
        return self.health_status
    
    async def get_api_endpoint(self, model_id: str) -> str:
        return f"http://localhost:8000/v1/models/{model_id}"
    
    def validate_config(self, config: ModelConfig) -> ValidationResult:
        return ValidationResult(is_valid=True, errors=[], warnings=[])

@pytest.fixture
def temp_config_dir():
    """创建临时配置目录"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def config_manager(temp_config_dir):
    """创建配置管理器实例"""
    return FileConfigManager(temp_config_dir)

@pytest.fixture
async def model_manager(config_manager):
    """创建模型管理器实例"""
    manager = ModelManager(config_manager)
    await manager.initialize()
    yield manager
    await manager.shutdown()

@pytest.fixture
def sample_model_config(tmp_path):
    """创建示例模型配置"""
    # 创建一个临时模型文件
    model_file = tmp_path / "test_model.gguf"
    model_file.write_text("fake model content")
    
    return ModelConfig(
        id="test_model_1",
        name="测试模型1",
        framework=FrameworkType.LLAMA_CPP,
        model_path=str(model_file),
        priority=5,
        gpu_devices=[0],
        parameters={"port": 8001, "ctx_size": 2048},
        resource_requirements=ResourceRequirement(
            gpu_memory=4096,
            gpu_devices=[0]
        ),
        health_check=HealthCheckConfig(),
        retry_policy=RetryPolicy()
    )

@pytest.fixture(autouse=True)
def setup_mock_adapter():
    """设置模拟适配器"""
    # 注册模拟适配器
    FrameworkAdapterFactory.register_adapter(FrameworkType.LLAMA_CPP, MockAdapter)
    FrameworkAdapterFactory.register_adapter(FrameworkType.VLLM, MockAdapter)
    yield
    # 清理注册的适配器
    FrameworkAdapterFactory._adapters.clear()

class TestModelManager:
    """模型管理器测试类"""
    
    @pytest.mark.asyncio
    async def test_create_model_success(self, model_manager, sample_model_config):
        """测试成功创建模型"""
        model_id = await model_manager.create_model(sample_model_config)
        
        assert model_id == sample_model_config.id
        assert sample_model_config.id in model_manager._models
        assert model_manager._model_status[sample_model_config.id] == ModelStatus.STOPPED
    
    @pytest.mark.asyncio
    async def test_create_model_duplicate_id(self, model_manager, sample_model_config):
        """测试创建重复ID的模型"""
        # 先创建一个模型
        await model_manager.create_model(sample_model_config)
        
        # 尝试创建相同ID的模型
        with pytest.raises(ValueError, match="模型ID已存在"):
            await model_manager.create_model(sample_model_config)
    
    @pytest.mark.asyncio
    async def test_create_model_invalid_config(self, model_manager, sample_model_config):
        """测试创建无效配置的模型"""
        # 设置无效的模型路径
        sample_model_config.model_path = "/nonexistent/path"
        
        with pytest.raises(ValueError, match="配置验证失败"):
            await model_manager.create_model(sample_model_config)
    
    @pytest.mark.asyncio
    async def test_start_model_success(self, model_manager, sample_model_config):
        """测试成功启动模型"""
        # 先创建模型
        await model_manager.create_model(sample_model_config)
        
        # 启动模型
        success = await model_manager.start_model(sample_model_config.id)
        
        assert success is True
        assert model_manager._model_status[sample_model_config.id] == ModelStatus.RUNNING
        assert sample_model_config.id in model_manager._adapters
    
    @pytest.mark.asyncio
    async def test_start_nonexistent_model(self, model_manager):
        """测试启动不存在的模型"""
        success = await model_manager.start_model("nonexistent_model")
        assert success is False
    
    @pytest.mark.asyncio
    async def test_start_already_running_model(self, model_manager, sample_model_config):
        """测试启动已运行的模型"""
        # 创建并启动模型
        await model_manager.create_model(sample_model_config)
        await model_manager.start_model(sample_model_config.id)
        
        # 再次启动
        success = await model_manager.start_model(sample_model_config.id)
        assert success is True  # 应该返回True，因为模型已在运行
    
    @pytest.mark.asyncio
    async def test_stop_model_success(self, model_manager, sample_model_config):
        """测试成功停止模型"""
        # 创建并启动模型
        await model_manager.create_model(sample_model_config)
        await model_manager.start_model(sample_model_config.id)
        
        # 停止模型
        success = await model_manager.stop_model(sample_model_config.id)
        
        assert success is True
        assert model_manager._model_status[sample_model_config.id] == ModelStatus.STOPPED
        assert sample_model_config.id not in model_manager._adapters
    
    @pytest.mark.asyncio
    async def test_stop_nonexistent_model(self, model_manager):
        """测试停止不存在的模型"""
        success = await model_manager.stop_model("nonexistent_model")
        assert success is False
    
    @pytest.mark.asyncio
    async def test_stop_already_stopped_model(self, model_manager, sample_model_config):
        """测试停止已停止的模型"""
        # 创建模型（但不启动）
        await model_manager.create_model(sample_model_config)
        
        # 停止模型
        success = await model_manager.stop_model(sample_model_config.id)
        assert success is True  # 应该返回True，因为模型已停止
    
    @pytest.mark.asyncio
    async def test_restart_model_success(self, model_manager, sample_model_config):
        """测试成功重启模型"""
        # 创建并启动模型
        await model_manager.create_model(sample_model_config)
        await model_manager.start_model(sample_model_config.id)
        
        # 重启模型
        success = await model_manager.restart_model(sample_model_config.id)
        
        assert success is True
        assert model_manager._model_status[sample_model_config.id] == ModelStatus.RUNNING
    
    @pytest.mark.asyncio
    async def test_get_model_status(self, model_manager, sample_model_config):
        """测试获取模型状态"""
        # 创建模型
        await model_manager.create_model(sample_model_config)
        
        # 获取停止状态
        status = await model_manager.get_model_status(sample_model_config.id)
        assert status == ModelStatus.STOPPED
        
        # 启动模型后获取状态
        await model_manager.start_model(sample_model_config.id)
        status = await model_manager.get_model_status(sample_model_config.id)
        assert status == ModelStatus.RUNNING
    
    @pytest.mark.asyncio
    async def test_list_models(self, model_manager, sample_model_config):
        """测试列出所有模型"""
        # 创建模型
        await model_manager.create_model(sample_model_config)
        
        # 列出模型
        models = await model_manager.list_models()
        
        assert len(models) == 1
        assert isinstance(models[0], ModelInfo)
        assert models[0].id == sample_model_config.id
        assert models[0].name == sample_model_config.name
        assert models[0].framework == sample_model_config.framework
        assert models[0].status == ModelStatus.STOPPED
    
    @pytest.mark.asyncio
    async def test_delete_model_success(self, model_manager, sample_model_config):
        """测试成功删除模型"""
        # 创建模型
        await model_manager.create_model(sample_model_config)
        
        # 删除模型
        success = await model_manager.delete_model(sample_model_config.id)
        
        assert success is True
        assert sample_model_config.id not in model_manager._models
        assert sample_model_config.id not in model_manager._model_status
    
    @pytest.mark.asyncio
    async def test_delete_running_model(self, model_manager, sample_model_config):
        """测试删除运行中的模型"""
        # 创建并启动模型
        await model_manager.create_model(sample_model_config)
        await model_manager.start_model(sample_model_config.id)
        
        # 删除模型
        success = await model_manager.delete_model(sample_model_config.id)
        
        assert success is True
        assert sample_model_config.id not in model_manager._models
        assert sample_model_config.id not in model_manager._adapters
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_model(self, model_manager):
        """测试删除不存在的模型"""
        success = await model_manager.delete_model("nonexistent_model")
        assert success is False
    
    @pytest.mark.asyncio
    async def test_update_model_config(self, model_manager, sample_model_config, tmp_path):
        """测试更新模型配置"""
        # 创建模型
        await model_manager.create_model(sample_model_config)
        
        # 创建新的模型文件
        new_model_file = tmp_path / "updated_model.gguf"
        new_model_file.write_text("updated model content")
        
        # 更新配置
        updated_config = sample_model_config.model_copy()
        updated_config.name = "更新后的模型"
        updated_config.model_path = str(new_model_file)
        updated_config.priority = 8
        
        success = await model_manager.update_model_config(sample_model_config.id, updated_config)
        
        assert success is True
        stored_config = model_manager._models[sample_model_config.id]
        assert stored_config.name == "更新后的模型"
        assert stored_config.priority == 8
        assert stored_config.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_get_model_config(self, model_manager, sample_model_config):
        """测试获取模型配置"""
        # 创建模型
        await model_manager.create_model(sample_model_config)
        
        # 获取配置
        config = await model_manager.get_model_config(sample_model_config.id)
        
        assert config is not None
        assert config.id == sample_model_config.id
        assert config.name == sample_model_config.name
    
    @pytest.mark.asyncio
    async def test_get_model_health(self, model_manager, sample_model_config):
        """测试获取模型健康状态"""
        # 创建并启动模型
        await model_manager.create_model(sample_model_config)
        await model_manager.start_model(sample_model_config.id)
        
        # 获取健康状态
        health = await model_manager.get_model_health(sample_model_config.id)
        
        assert health == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_get_running_models(self, model_manager, sample_model_config, tmp_path):
        """测试获取运行中的模型列表"""
        # 创建两个模型
        await model_manager.create_model(sample_model_config)
        
        # 创建第二个模型
        model_file2 = tmp_path / "test_model2.gguf"
        model_file2.write_text("fake model content 2")
        
        config2 = sample_model_config.model_copy()
        config2.id = "test_model_2"
        config2.name = "测试模型2"
        config2.model_path = str(model_file2)
        config2.parameters = {"port": 8002}
        
        await model_manager.create_model(config2)
        
        # 只启动第一个模型
        await model_manager.start_model(sample_model_config.id)
        
        # 获取运行中的模型
        running_models = await model_manager.get_running_models()
        
        assert len(running_models) == 1
        assert sample_model_config.id in running_models
        assert config2.id not in running_models
    
    @pytest.mark.asyncio
    async def test_get_models_by_priority(self, model_manager, sample_model_config, tmp_path):
        """测试按优先级获取模型"""
        # 创建多个不同优先级的模型
        await model_manager.create_model(sample_model_config)  # 优先级5
        
        # 高优先级模型
        model_file_high = tmp_path / "high_priority_model.gguf"
        model_file_high.write_text("high priority model")
        
        high_priority_config = sample_model_config.model_copy()
        high_priority_config.id = "high_priority_model"
        high_priority_config.name = "高优先级模型"
        high_priority_config.model_path = str(model_file_high)
        high_priority_config.priority = 9
        high_priority_config.parameters = {"port": 8003}
        
        await model_manager.create_model(high_priority_config)
        
        # 低优先级模型
        model_file_low = tmp_path / "low_priority_model.gguf"
        model_file_low.write_text("low priority model")
        
        low_priority_config = sample_model_config.model_copy()
        low_priority_config.id = "low_priority_model"
        low_priority_config.name = "低优先级模型"
        low_priority_config.model_path = str(model_file_low)
        low_priority_config.priority = 2
        low_priority_config.parameters = {"port": 8004}
        
        await model_manager.create_model(low_priority_config)
        
        # 按优先级降序获取
        models_desc = await model_manager.get_models_by_priority(ascending=False)
        assert len(models_desc) == 3
        assert models_desc[0].priority == 9  # 高优先级在前
        assert models_desc[1].priority == 5
        assert models_desc[2].priority == 2
        
        # 按优先级升序获取
        models_asc = await model_manager.get_models_by_priority(ascending=True)
        assert len(models_asc) == 3
        assert models_asc[0].priority == 2  # 低优先级在前
        assert models_asc[1].priority == 5
        assert models_asc[2].priority == 9
    
    @pytest.mark.asyncio
    async def test_status_update_callback(self, model_manager, sample_model_config):
        """测试状态更新回调"""
        callback_calls = []
        
        async def status_callback(model_id, old_status, new_status):
            callback_calls.append((model_id, old_status, new_status))
        
        # 添加回调
        model_manager.add_status_update_callback(status_callback)
        
        # 创建并启动模型
        await model_manager.create_model(sample_model_config)
        await model_manager.start_model(sample_model_config.id)
        
        # 验证回调被调用
        assert len(callback_calls) >= 1
        # 应该有从STOPPED到STARTING，再从STARTING到RUNNING的状态变更
        assert any(call[0] == sample_model_config.id for call in callback_calls)
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, model_manager, sample_model_config, tmp_path):
        """测试并发操作"""
        # 创建多个模型配置
        configs = []
        for i in range(3):
            model_file = tmp_path / f"model_{i}.gguf"
            model_file.write_text(f"model content {i}")
            
            config = sample_model_config.model_copy()
            config.id = f"test_model_{i}"
            config.name = f"测试模型{i}"
            config.model_path = str(model_file)
            config.parameters = {"port": 8001 + i}
            configs.append(config)
        
        # 并发创建模型
        create_tasks = [model_manager.create_model(config) for config in configs]
        results = await asyncio.gather(*create_tasks, return_exceptions=True)
        
        # 验证所有模型都创建成功
        assert len([r for r in results if not isinstance(r, Exception)]) == 3
        
        # 并发启动模型
        start_tasks = [model_manager.start_model(config.id) for config in configs]
        start_results = await asyncio.gather(*start_tasks, return_exceptions=True)
        
        # 验证启动结果
        success_count = len([r for r in start_results if r is True])
        assert success_count == 3
    
    @pytest.mark.asyncio
    async def test_adapter_failure_handling(self, model_manager, sample_model_config):
        """测试适配器失败处理"""
        # 创建模型
        await model_manager.create_model(sample_model_config)
        
        # 模拟适配器启动失败
        with patch.object(MockAdapter, '_do_start_model', return_value=False):
            success = await model_manager.start_model(sample_model_config.id)
            assert success is False
            assert model_manager._model_status[sample_model_config.id] == ModelStatus.ERROR
    
    @pytest.mark.asyncio
    async def test_initialization_with_existing_configs(self, config_manager, sample_model_config):
        """测试使用已存在配置初始化"""
        # 先保存一个配置
        await config_manager.save_model_config(sample_model_config)
        
        # 创建新的模型管理器实例
        new_manager = ModelManager(config_manager)
        await new_manager.initialize()
        
        try:
            # 验证配置被加载
            assert sample_model_config.id in new_manager._models
            assert new_manager._model_status[sample_model_config.id] == ModelStatus.STOPPED
            
            # 验证可以操作加载的模型
            models = await new_manager.list_models()
            assert len(models) == 1
            assert models[0].id == sample_model_config.id
        finally:
            await new_manager.shutdown()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])