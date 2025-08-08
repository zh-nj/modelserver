"""
数据库配置管理器测试
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from app.services.database_config_manager import DatabaseConfigManager
from app.models.schemas import ModelConfig, ResourceRequirement, HealthCheckConfig, RetryPolicy
from app.models.enums import FrameworkType

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
def mock_session():
    """模拟数据库会话"""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session

@pytest.fixture
def config_manager(mock_session):
    """配置管理器实例"""
    manager = DatabaseConfigManager()
    # 模拟会话工厂
    manager.session_factory = AsyncMock(return_value=mock_session)
    return manager

class TestDatabaseConfigManager:
    """数据库配置管理器测试类"""
    
    @pytest.mark.asyncio
    async def test_initialize(self, config_manager):
        """测试初始化"""
        # 模拟数据库连接测试
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        config_manager.session_factory.return_value.execute.return_value = mock_result
        
        await config_manager.initialize()
        
        # 验证数据库连接测试被调用
        config_manager.session_factory.return_value.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_save_model_config_new(self, config_manager, sample_model_config, mock_session):
        """测试保存新模型配置"""
        # 模拟配置不存在
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        result = await config_manager.save_model_config(sample_model_config)
        
        assert result is True
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_save_model_config_update(self, config_manager, sample_model_config, mock_session):
        """测试更新现有模型配置"""
        # 模拟配置已存在
        existing_config = MagicMock()
        existing_config.id = sample_model_config.id
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_config
        mock_session.execute.return_value = mock_result
        
        result = await config_manager.save_model_config(sample_model_config)
        
        assert result is True
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_load_model_configs(self, config_manager, mock_session):
        """测试加载模型配置"""
        # 模拟数据库返回
        mock_db_config = MagicMock()
        mock_db_config.id = "test-model-1"
        mock_db_config.name = "测试模型"
        mock_db_config.framework = "llama_cpp"
        mock_db_config.model_path = "/path/to/model.gguf"
        mock_db_config.priority = 5
        mock_db_config.gpu_devices = [0]
        mock_db_config.parameters = {"port": 8080}
        mock_db_config.gpu_memory = 4096
        mock_db_config.cpu_cores = 4
        mock_db_config.system_memory = 8192
        mock_db_config.health_check_enabled = True
        mock_db_config.health_check_interval = 30
        mock_db_config.health_check_timeout = 10
        mock_db_config.health_check_max_failures = 3
        mock_db_config.health_check_endpoint = "/health"
        mock_db_config.retry_enabled = True
        mock_db_config.retry_max_attempts = 3
        mock_db_config.retry_initial_delay = 5
        mock_db_config.retry_max_delay = 300
        mock_db_config.retry_backoff_factor = 2.0
        mock_db_config.created_at = datetime.now()
        mock_db_config.updated_at = datetime.now()
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_db_config]
        mock_session.execute.return_value = mock_result
        
        configs = await config_manager.load_model_configs()
        
        assert len(configs) == 1
        assert configs[0].id == "test-model-1"
        assert configs[0].name == "测试模型"
        assert configs[0].framework == FrameworkType.LLAMA_CPP
    
    @pytest.mark.asyncio
    async def test_delete_model_config(self, config_manager, mock_session):
        """测试删除模型配置"""
        # 模拟配置存在
        existing_config = MagicMock()
        existing_config.id = "test-model-1"
        existing_config.is_active = True
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_config
        mock_session.execute.return_value = mock_result
        
        result = await config_manager.delete_model_config("test-model-1")
        
        assert result is True
        assert existing_config.is_active is False
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_config_valid(self, config_manager, sample_model_config):
        """测试有效配置验证"""
        # 模拟数据库查询（配置不存在）
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        config_manager.session_factory = AsyncMock(return_value=mock_session)
        
        validation_result = await config_manager.validate_config(sample_model_config)
        
        assert validation_result.is_valid is True
        assert len(validation_result.errors) == 0
    
    @pytest.mark.asyncio
    async def test_validate_config_invalid(self, config_manager):
        """测试无效配置验证"""
        # 创建无效配置
        invalid_config = ModelConfig(
            id="",  # 空ID
            name="",  # 空名称
            framework=FrameworkType.LLAMA_CPP,
            model_path="",  # 空路径
            priority=15,  # 无效优先级
            gpu_devices=[-1],  # 无效GPU设备
            parameters={},
            resource_requirements=ResourceRequirement(
                gpu_memory=0,  # 无效内存需求
                gpu_devices=[],
                cpu_cores=None,
                system_memory=None
            ),
            health_check=HealthCheckConfig(),
            retry_policy=RetryPolicy()
        )
        
        validation_result = await config_manager.validate_config(invalid_config)
        
        assert validation_result.is_valid is False
        assert len(validation_result.errors) > 0
        assert "模型ID不能为空" in validation_result.errors
        assert "模型名称不能为空" in validation_result.errors
        assert "模型路径不能为空" in validation_result.errors
        assert "优先级必须在1-10之间" in validation_result.errors
        assert "无效的GPU设备ID: -1" in validation_result.errors
        assert "GPU内存需求必须大于0" in validation_result.errors
    
    @pytest.mark.asyncio
    async def test_backup_configs(self, config_manager, mock_session):
        """测试配置备份"""
        # 模拟数据库返回配置
        mock_db_config = MagicMock()
        mock_db_config.id = "test-model-1"
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_db_config]
        mock_session.execute.return_value = mock_result
        
        # 模拟_db_to_dict方法
        config_manager._db_to_dict = MagicMock(return_value={"id": "test-model-1"})
        
        backup_name = await config_manager.backup_configs()
        
        assert backup_name.startswith("models_backup_")
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_restore_configs(self, config_manager, mock_session):
        """测试配置恢复"""
        # 模拟备份记录存在
        mock_backup = MagicMock()
        mock_backup.backup_data = '{"timestamp": "20240101_000000", "version": "1.0", "configs": [{"id": "test-model-1", "name": "测试模型"}]}'
        mock_backup.checksum = "test_checksum"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_backup
        mock_session.execute.return_value = mock_result
        
        # 模拟校验和计算
        import hashlib
        expected_checksum = hashlib.sha256(mock_backup.backup_data.encode('utf-8')).hexdigest()
        mock_backup.checksum = expected_checksum
        
        # 模拟backup_configs方法
        config_manager.backup_configs = AsyncMock(return_value="current_backup")
        
        # 模拟save_model_config方法
        config_manager.save_model_config = AsyncMock(return_value=True)
        
        result = await config_manager.restore_configs("test_backup")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_list_backups(self, config_manager, mock_session):
        """测试列出备份"""
        # 模拟备份记录
        mock_backup = MagicMock()
        mock_backup.backup_name = "test_backup"
        mock_backup.backup_type = "model_configs"
        mock_backup.backup_size = 1024
        mock_backup.description = "测试备份"
        mock_backup.created_at = datetime.now()
        mock_backup.checksum = "test_checksum"
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_backup]
        mock_session.execute.return_value = mock_result
        
        backups = await config_manager.list_backups()
        
        assert len(backups) == 1
        assert backups[0]["backup_name"] == "test_backup"
        assert backups[0]["backup_type"] == "model_configs"
    
    @pytest.mark.asyncio
    async def test_cleanup_old_backups(self, config_manager, mock_session):
        """测试清理旧备份"""
        # 模拟多个备份记录
        mock_backups = []
        for i in range(15):
            mock_backup = MagicMock()
            mock_backup.backup_name = f"backup_{i}"
            mock_backup.created_at = datetime.now()
            mock_backups.append(mock_backup)
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_backups
        mock_session.execute.return_value = mock_result
        
        deleted_count = await config_manager.cleanup_old_backups(keep_count=10)
        
        assert deleted_count == 5  # 删除了5个旧备份
        assert mock_session.delete.call_count == 5
        mock_session.commit.assert_called_once()

if __name__ == "__main__":
    pytest.main([__file__])