"""
配置热重载服务测试
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from app.services.config_hot_reload import ConfigHotReloadService, ConfigChangeType, ConfigChangeEvent
from app.services.database_config_manager import DatabaseConfigManager
from app.models.schemas import ModelConfig, ResourceRequirement, HealthCheckConfig, RetryPolicy
from app.models.enums import FrameworkType, ModelStatus

@pytest.fixture
def sample_model_config():
    """示例模型配置"""
    return ModelConfig(
        id="test-model-1",
        name="测试模型",
        framework=FrameworkType.LLAMA_CPP,
        model_path="/path/to/model.gguf",
        priority=5,
        gpu_devices=[0],
        parameters={"port": 8080, "ctx_size": 2048},
        resource_requirements=ResourceRequirement(
            gpu_memory=4096,
            gpu_devices=[0],
            cpu_cores=4,
            system_memory=8192
        ),
        health_check=HealthCheckConfig(
            enabled=True,
            interval=30,
            timeout=10,
            max_failures=3,
            endpoint="/health"
        ),
        retry_policy=RetryPolicy(
            enabled=True,
            max_attempts=3,
            initial_delay=5,
            max_delay=300,
            backoff_factor=2.0
        ),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

@pytest.fixture
def mock_config_manager():
    """模拟配置管理器"""
    manager = AsyncMock(spec=DatabaseConfigManager)
    return manager

@pytest.fixture
def mock_model_manager():
    """模拟模型管理器"""
    manager = AsyncMock()
    manager.get_model_status = AsyncMock()
    manager.start_model = AsyncMock()
    manager.stop_model = AsyncMock()
    return manager

@pytest.fixture
def hot_reload_service(mock_config_manager, mock_model_manager):
    """热重载服务实例"""
    service = ConfigHotReloadService(mock_config_manager, mock_model_manager)
    service.check_interval = 0.1  # 快速测试
    return service

class TestConfigChangeEvent:
    """配置变更事件测试"""
    
    def test_create_event_with_defaults(self):
        """测试创建事件（使用默认值）"""
        event = ConfigChangeEvent(
            change_type=ConfigChangeType.CREATED,
            model_id="test-model"
        )
        
        assert event.change_type == ConfigChangeType.CREATED
        assert event.model_id == "test-model"
        assert event.old_config is None
        assert event.new_config is None
        assert event.timestamp is not None
        assert event.change_fields is None
    
    def test_detect_changed_fields(self, sample_model_config):
        """测试检测变更字段"""
        old_config = sample_model_config
        new_config = sample_model_config.copy()
        new_config.name = "新名称"
        new_config.priority = 8
        
        event = ConfigChangeEvent(
            change_type=ConfigChangeType.UPDATED,
            model_id="test-model",
            old_config=old_config,
            new_config=new_config
        )
        
        assert "name" in event.change_fields
        assert "priority" in event.change_fields

class TestConfigHotReloadService:
    """配置热重载服务测试"""
    
    @pytest.mark.asyncio
    async def test_initialize_cache(self, hot_reload_service, mock_config_manager, sample_model_config):
        """测试初始化缓存"""
        # 模拟配置管理器返回配置
        mock_config_manager.load_model_configs.return_value = [sample_model_config]
        
        await hot_reload_service._initialize_cache()
        
        assert len(hot_reload_service._config_cache) == 1
        assert "test-model-1" in hot_reload_service._config_cache
        assert hot_reload_service._config_cache["test-model-1"] == sample_model_config
    
    @pytest.mark.asyncio
    async def test_start_and_stop_service(self, hot_reload_service, mock_config_manager):
        """测试启动和停止服务"""
        # 模拟配置管理器返回空配置
        mock_config_manager.load_model_configs.return_value = []
        
        # 启动服务
        await hot_reload_service.start()
        assert hot_reload_service._running is True
        assert hot_reload_service._reload_task is not None
        
        # 停止服务
        await hot_reload_service.stop()
        assert hot_reload_service._running is False
    
    @pytest.mark.asyncio
    async def test_add_remove_listeners(self, hot_reload_service):
        """测试添加和移除监听器"""
        def test_listener(event):
            pass
        
        # 添加监听器
        hot_reload_service.add_change_listener(test_listener)
        assert test_listener in hot_reload_service._change_listeners
        
        # 移除监听器
        hot_reload_service.remove_change_listener(test_listener)
        assert test_listener not in hot_reload_service._change_listeners
    
    @pytest.mark.asyncio
    async def test_reload_model_config_new(self, hot_reload_service, mock_config_manager, sample_model_config):
        """测试重新加载模型配置（新增）"""
        # 模拟配置管理器返回新配置
        mock_config_manager.load_model_configs.return_value = [sample_model_config]
        
        # 缓存为空，模拟新增配置
        hot_reload_service._config_cache = {}
        
        event = await hot_reload_service.reload_model_config("test-model-1")
        
        assert event is not None
        assert event.change_type == ConfigChangeType.CREATED
        assert event.model_id == "test-model-1"
        assert event.new_config == sample_model_config
        assert "test-model-1" in hot_reload_service._config_cache
    
    @pytest.mark.asyncio
    async def test_reload_model_config_updated(self, hot_reload_service, mock_config_manager, sample_model_config):
        """测试重新加载模型配置（更新）"""
        # 设置旧配置
        old_config = sample_model_config.copy()
        hot_reload_service._config_cache = {"test-model-1": old_config}
        
        # 创建新配置
        new_config = sample_model_config.copy()
        new_config.name = "更新后的模型"
        new_config.priority = 8
        
        # 模拟配置管理器返回更新后的配置
        mock_config_manager.load_model_configs.return_value = [new_config]
        
        event = await hot_reload_service.reload_model_config("test-model-1")
        
        assert event is not None
        assert event.change_type == ConfigChangeType.UPDATED
        assert event.model_id == "test-model-1"
        assert event.old_config == old_config
        assert event.new_config == new_config
        assert "name" in event.change_fields
        assert "priority" in event.change_fields
    
    @pytest.mark.asyncio
    async def test_reload_model_config_deleted(self, hot_reload_service, mock_config_manager, sample_model_config):
        """测试重新加载模型配置（删除）"""
        # 设置旧配置
        hot_reload_service._config_cache = {"test-model-1": sample_model_config}
        
        # 模拟配置管理器返回空配置（配置被删除）
        mock_config_manager.load_model_configs.return_value = []
        
        event = await hot_reload_service.reload_model_config("test-model-1")
        
        assert event is not None
        assert event.change_type == ConfigChangeType.DELETED
        assert event.model_id == "test-model-1"
        assert event.old_config == sample_model_config
        assert "test-model-1" not in hot_reload_service._config_cache
    
    @pytest.mark.asyncio
    async def test_configs_differ(self, hot_reload_service, sample_model_config):
        """测试配置差异检测"""
        config1 = sample_model_config
        config2 = sample_model_config.copy()
        
        # 相同配置
        assert not hot_reload_service._configs_differ(config1, config2)
        
        # 不同名称
        config2.name = "不同名称"
        assert hot_reload_service._configs_differ(config1, config2)
        
        # 重置名称，修改优先级
        config2.name = config1.name
        config2.priority = 8
        assert hot_reload_service._configs_differ(config1, config2)
        
        # 重置优先级，修改参数
        config2.priority = config1.priority
        config2.parameters = {"port": 9090}
        assert hot_reload_service._configs_differ(config1, config2)
    
    @pytest.mark.asyncio
    async def test_requires_model_restart(self, hot_reload_service):
        """测试是否需要重启模型判断"""
        # 不需要重启的变更
        event = ConfigChangeEvent(
            change_type=ConfigChangeType.UPDATED,
            model_id="test-model",
            change_fields=["name", "priority"]
        )
        assert not hot_reload_service._requires_model_restart(event)
        
        # 需要重启的变更
        event.change_fields = ["framework", "model_path"]
        assert hot_reload_service._requires_model_restart(event)
        
        event.change_fields = ["gpu_devices"]
        assert hot_reload_service._requires_model_restart(event)
        
        event.change_fields = ["parameters"]
        assert hot_reload_service._requires_model_restart(event)
        
        event.change_fields = ["resource_requirements"]
        assert hot_reload_service._requires_model_restart(event)
    
    @pytest.mark.asyncio
    async def test_handle_config_update_with_restart(self, hot_reload_service, mock_model_manager):
        """测试处理配置更新（需要重启）"""
        # 模拟模型正在运行
        mock_status = MagicMock()
        mock_status.status = ModelStatus.RUNNING
        mock_model_manager.get_model_status.return_value = mock_status
        
        # 创建需要重启的变更事件
        event = ConfigChangeEvent(
            change_type=ConfigChangeType.UPDATED,
            model_id="test-model",
            change_fields=["framework"]
        )
        
        await hot_reload_service._handle_config_update(event)
        
        # 验证模型被停止和启动
        mock_model_manager.stop_model.assert_called_once_with("test-model")
        mock_model_manager.start_model.assert_called_once_with("test-model")
    
    @pytest.mark.asyncio
    async def test_handle_config_update_without_restart(self, hot_reload_service, mock_model_manager):
        """测试处理配置更新（不需要重启）"""
        # 模拟模型正在运行
        mock_status = MagicMock()
        mock_status.status = ModelStatus.RUNNING
        mock_model_manager.get_model_status.return_value = mock_status
        
        # 创建不需要重启的变更事件
        event = ConfigChangeEvent(
            change_type=ConfigChangeType.UPDATED,
            model_id="test-model",
            change_fields=["name"]
        )
        
        await hot_reload_service._handle_config_update(event)
        
        # 验证模型没有被停止和启动
        mock_model_manager.stop_model.assert_not_called()
        mock_model_manager.start_model.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_config_deletion(self, hot_reload_service, mock_model_manager):
        """测试处理配置删除"""
        # 模拟模型正在运行
        mock_status = MagicMock()
        mock_status.status = ModelStatus.RUNNING
        mock_model_manager.get_model_status.return_value = mock_status
        
        # 创建删除事件
        event = ConfigChangeEvent(
            change_type=ConfigChangeType.DELETED,
            model_id="test-model"
        )
        
        await hot_reload_service._handle_config_deletion(event)
        
        # 验证模型被停止
        mock_model_manager.stop_model.assert_called_once_with("test-model")
    
    @pytest.mark.asyncio
    async def test_notify_listeners(self, hot_reload_service):
        """测试通知监听器"""
        # 添加同步监听器
        sync_listener_called = False
        def sync_listener(event):
            nonlocal sync_listener_called
            sync_listener_called = True
        
        # 添加异步监听器
        async_listener_called = False
        async def async_listener(event):
            nonlocal async_listener_called
            async_listener_called = True
        
        hot_reload_service.add_change_listener(sync_listener)
        hot_reload_service.add_change_listener(async_listener)
        
        # 创建事件
        event = ConfigChangeEvent(
            change_type=ConfigChangeType.CREATED,
            model_id="test-model"
        )
        
        # 通知监听器
        await hot_reload_service._notify_listeners(event)
        
        # 验证监听器被调用
        assert sync_listener_called
        assert async_listener_called
    
    def test_get_status(self, hot_reload_service):
        """测试获取服务状态"""
        status = hot_reload_service.get_status()
        
        assert "running" in status
        assert "enabled" in status
        assert "auto_apply_changes" in status
        assert "check_interval" in status
        assert "cached_configs_count" in status
        assert "listeners_count" in status
        assert "last_check_time" in status
    
    def test_settings_management(self, hot_reload_service):
        """测试设置管理"""
        # 测试启用/禁用
        hot_reload_service.disable()
        assert not hot_reload_service.enabled
        
        hot_reload_service.enable()
        assert hot_reload_service.enabled
        
        # 测试设置检查间隔
        hot_reload_service.set_check_interval(10)
        assert hot_reload_service.check_interval == 10
        
        # 测试无效间隔
        hot_reload_service.set_check_interval(-1)
        assert hot_reload_service.check_interval == 10  # 保持原值
        
        # 测试自动应用设置
        hot_reload_service.set_auto_apply(False)
        assert not hot_reload_service.auto_apply_changes
        
        hot_reload_service.set_auto_apply(True)
        assert hot_reload_service.auto_apply_changes
    
    def test_cache_operations(self, hot_reload_service, sample_model_config):
        """测试缓存操作"""
        # 设置缓存
        hot_reload_service._config_cache["test-model"] = sample_model_config
        
        # 获取单个配置
        cached_config = hot_reload_service.get_cached_config("test-model")
        assert cached_config == sample_model_config
        
        # 获取不存在的配置
        non_existent = hot_reload_service.get_cached_config("non-existent")
        assert non_existent is None
        
        # 获取所有配置
        all_configs = hot_reload_service.get_all_cached_configs()
        assert "test-model" in all_configs
        assert all_configs["test-model"] == sample_model_config

if __name__ == "__main__":
    pytest.main([__file__])