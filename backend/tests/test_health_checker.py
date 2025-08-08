"""
健康检查器测试
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from app.services.health_checker import HealthChecker, HealthCheckResult
from app.models.schemas import ModelConfig, ModelInfo, HealthCheckConfig, ResourceRequirement
from app.models.enums import FrameworkType, ModelStatus, HealthStatus


class TestHealthChecker:
    """健康检查器测试"""
    
    @pytest.fixture
    def health_checker(self):
        """创建健康检查器实例"""
        return HealthChecker()
    
    @pytest.fixture
    def sample_model_config(self):
        """示例模型配置"""
        return ModelConfig(
            id="test_model",
            name="测试模型",
            framework=FrameworkType.LLAMA_CPP,
            model_path="/models/test.gguf",
            priority=5,
            gpu_devices=[0],
            parameters={"port": 8001, "host": "127.0.0.1"},
            resource_requirements=ResourceRequirement(
                gpu_memory=4096,
                gpu_devices=[0]
            ),
            health_check=HealthCheckConfig(
                enabled=True,
                interval=30,
                timeout=10,
                max_failures=3,
                endpoint="/health"
            )
        )
    
    @pytest.fixture
    def sample_model_info(self, sample_model_config):
        """示例模型信息"""
        return ModelInfo(
            id=sample_model_config.id,
            name=sample_model_config.name,
            framework=sample_model_config.framework,
            status=ModelStatus.RUNNING,
            priority=sample_model_config.priority,
            gpu_devices=sample_model_config.gpu_devices,
            api_endpoint="http://127.0.0.1:8001"
        )
    
    @pytest.mark.asyncio
    async def test_register_model(self, health_checker, sample_model_info):
        """测试注册模型健康检查"""
        await health_checker.register_model(sample_model_info)
        
        assert sample_model_info.id in health_checker._registered_models
        model_data = health_checker._registered_models[sample_model_info.id]
        assert model_data['model_info'] == sample_model_info
        assert model_data['last_check'] is None
        assert model_data['failure_count'] == 0
        assert model_data['status'] == HealthStatus.UNKNOWN
    
    @pytest.mark.asyncio
    async def test_unregister_model(self, health_checker, sample_model_info):
        """测试注销模型健康检查"""
        # 先注册
        await health_checker.register_model(sample_model_info)
        assert sample_model_info.id in health_checker._registered_models
        
        # 再注销
        await health_checker.unregister_model(sample_model_info.id)
        assert sample_model_info.id not in health_checker._registered_models
    
    @pytest.mark.asyncio
    async def test_check_model_health_success(self, health_checker, sample_model_info):
        """测试模型健康检查成功"""
        # Mock成功的HTTP响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy", "uptime": 3600}
        mock_response.elapsed.total_seconds.return_value = 0.1
        
        with patch('httpx.AsyncClient.get', return_value=mock_response):
            result = await health_checker.check_model_health(sample_model_info)
            
            assert isinstance(result, HealthCheckResult)
            assert result.model_id == sample_model_info.id
            assert result.status == HealthStatus.HEALTHY
            assert result.response_time == 0.1
            assert result.error_message is None
            assert "uptime" in result.details
    
    @pytest.mark.asyncio
    async def test_check_model_health_failure(self, health_checker, sample_model_info):
        """测试模型健康检查失败"""
        # Mock失败的HTTP响应
        with patch('httpx.AsyncClient.get', side_effect=Exception("Connection refused")):
            result = await health_checker.check_model_health(sample_model_info)
            
            assert isinstance(result, HealthCheckResult)
            assert result.model_id == sample_model_info.id
            assert result.status == HealthStatus.UNHEALTHY
            assert result.response_time is None
            assert "Connection refused" in result.error_message
    
    @pytest.mark.asyncio
    async def test_check_model_health_timeout(self, health_checker, sample_model_info):
        """测试模型健康检查超时"""
        # Mock超时异常
        with patch('httpx.AsyncClient.get', side_effect=asyncio.TimeoutError()):
            result = await health_checker.check_model_health(sample_model_info)
            
            assert result.status == HealthStatus.UNHEALTHY
            assert "超时" in result.error_message or "timeout" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_check_model_health_invalid_response(self, health_checker, sample_model_info):
        """测试模型健康检查无效响应"""
        # Mock无效状态码的响应
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.elapsed.total_seconds.return_value = 0.2
        
        with patch('httpx.AsyncClient.get', return_value=mock_response):
            result = await health_checker.check_model_health(sample_model_info)
            
            assert result.status == HealthStatus.UNHEALTHY
            assert result.response_time == 0.2
            assert "500" in result.error_message
    
    @pytest.mark.asyncio
    async def test_update_model_status(self, health_checker, sample_model_info):
        """测试更新模型状态"""
        # 先注册模型
        await health_checker.register_model(sample_model_info)
        
        # 创建健康检查结果
        result = HealthCheckResult(
            model_id=sample_model_info.id,
            status=HealthStatus.HEALTHY,
            check_time=datetime.now(),
            response_time=0.1,
            details={"status": "ok"}
        )
        
        await health_checker._update_model_status(result)
        
        model_data = health_checker._registered_models[sample_model_info.id]
        assert model_data['status'] == HealthStatus.HEALTHY
        assert model_data['last_check'] is not None
        assert model_data['failure_count'] == 0
        assert len(model_data['check_history']) == 1
    
    @pytest.mark.asyncio
    async def test_failure_count_tracking(self, health_checker, sample_model_info):
        """测试失败次数跟踪"""
        # 注册模型
        await health_checker.register_model(sample_model_info)
        
        # 模拟连续失败
        for i in range(3):
            result = HealthCheckResult(
                model_id=sample_model_info.id,
                status=HealthStatus.UNHEALTHY,
                check_time=datetime.now(),
                error_message=f"Error {i+1}"
            )
            await health_checker._update_model_status(result)
        
        model_data = health_checker._registered_models[sample_model_info.id]
        assert model_data['failure_count'] == 3
        assert model_data['status'] == HealthStatus.UNHEALTHY
        
        # 模拟恢复成功
        success_result = HealthCheckResult(
            model_id=sample_model_info.id,
            status=HealthStatus.HEALTHY,
            check_time=datetime.now(),
            response_time=0.1
        )
        await health_checker._update_model_status(success_result)
        
        model_data = health_checker._registered_models[sample_model_info.id]
        assert model_data['failure_count'] == 0  # 重置失败计数
        assert model_data['status'] == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_get_model_health_status(self, health_checker, sample_model_info):
        """测试获取模型健康状态"""
        # 注册模型
        await health_checker.register_model(sample_model_info)
        
        # 初始状态应该是UNKNOWN
        status = await health_checker.get_model_health_status(sample_model_info.id)
        assert status == HealthStatus.UNKNOWN
        
        # 执行健康检查后更新状态
        result = HealthCheckResult(
            model_id=sample_model_info.id,
            status=HealthStatus.HEALTHY,
            check_time=datetime.now(),
            response_time=0.1
        )
        await health_checker._update_model_status(result)
        
        status = await health_checker.get_model_health_status(sample_model_info.id)
        assert status == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_get_model_health_details(self, health_checker, sample_model_info):
        """测试获取模型健康详情"""
        # 注册模型
        await health_checker.register_model(sample_model_info)
        
        # 添加一些检查历史
        for i in range(3):
            result = HealthCheckResult(
                model_id=sample_model_info.id,
                status=HealthStatus.HEALTHY if i % 2 == 0 else HealthStatus.UNHEALTHY,
                check_time=datetime.now() - timedelta(minutes=i*5),
                response_time=0.1 + i*0.05,
                details={"check_number": i}
            )
            await health_checker._update_model_status(result)
        
        details = await health_checker.get_model_health_details(sample_model_info.id)
        
        assert details is not None
        assert details['model_id'] == sample_model_info.id
        assert details['current_status'] == HealthStatus.HEALTHY
        assert details['failure_count'] == 0
        assert 'last_check' in details
        assert 'check_history' in details
        assert len(details['check_history']) == 3
    
    @pytest.mark.asyncio
    async def test_get_all_health_status(self, health_checker, sample_model_info):
        """测试获取所有模型健康状态"""
        # 注册多个模型
        models = []
        for i in range(3):
            model_info = ModelInfo(
                id=f"model_{i}",
                name=f"模型{i}",
                framework=FrameworkType.LLAMA_CPP,
                status=ModelStatus.RUNNING,
                priority=5,
                gpu_devices=[0],
                api_endpoint=f"http://127.0.0.1:800{i}"
            )
            models.append(model_info)
            await health_checker.register_model(model_info)
        
        # 设置不同的健康状态
        for i, model in enumerate(models):
            status = [HealthStatus.HEALTHY, HealthStatus.UNHEALTHY, HealthStatus.UNKNOWN][i]
            result = HealthCheckResult(
                model_id=model.id,
                status=status,
                check_time=datetime.now(),
                response_time=0.1
            )
            await health_checker._update_model_status(result)
        
        all_status = await health_checker.get_all_health_status()
        
        assert len(all_status) == 3
        assert all_status[models[0].id] == HealthStatus.HEALTHY
        assert all_status[models[1].id] == HealthStatus.UNHEALTHY
        assert all_status[models[2].id] == HealthStatus.UNKNOWN
    
    @pytest.mark.asyncio
    async def test_start_periodic_checks(self, health_checker, sample_model_info):
        """测试启动定期检查"""
        # 注册模型
        await health_checker.register_model(sample_model_info)
        
        # Mock健康检查方法
        health_checker.check_model_health = AsyncMock(return_value=HealthCheckResult(
            model_id=sample_model_info.id,
            status=HealthStatus.HEALTHY,
            check_time=datetime.now(),
            response_time=0.1
        ))
        
        # 设置很短的检查间隔用于测试
        health_checker._check_interval = 0.1
        
        # 启动定期检查
        await health_checker.start_periodic_checks()
        
        # 等待一段时间让检查执行
        await asyncio.sleep(0.3)
        
        # 停止检查
        await health_checker.stop_periodic_checks()
        
        # 验证检查方法被调用
        assert health_checker.check_model_health.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_stop_periodic_checks(self, health_checker):
        """测试停止定期检查"""
        # 启动检查
        health_checker._is_running = True
        health_checker._check_task = asyncio.create_task(asyncio.sleep(10))
        
        # 停止检查
        await health_checker.stop_periodic_checks()
        
        assert health_checker._is_running is False
        assert health_checker._check_task.cancelled()
    
    @pytest.mark.asyncio
    async def test_health_check_callback(self, health_checker, sample_model_info):
        """测试健康检查回调"""
        callback_calls = []
        
        async def health_callback(model_id, old_status, new_status, result):
            callback_calls.append((model_id, old_status, new_status, result))
        
        # 添加回调
        health_checker.add_health_callback(health_callback)
        
        # 注册模型
        await health_checker.register_model(sample_model_info)
        
        # 执行健康检查
        result = HealthCheckResult(
            model_id=sample_model_info.id,
            status=HealthStatus.HEALTHY,
            check_time=datetime.now(),
            response_time=0.1
        )
        await health_checker._update_model_status(result)
        
        # 验证回调被调用
        assert len(callback_calls) == 1
        assert callback_calls[0][0] == sample_model_info.id
        assert callback_calls[0][1] == HealthStatus.UNKNOWN  # 初始状态
        assert callback_calls[0][2] == HealthStatus.HEALTHY  # 新状态
    
    @pytest.mark.asyncio
    async def test_health_check_with_custom_endpoint(self, health_checker):
        """测试自定义端点健康检查"""
        # 创建带自定义健康检查端点的模型
        model_info = ModelInfo(
            id="custom_model",
            name="自定义模型",
            framework=FrameworkType.VLLM,
            status=ModelStatus.RUNNING,
            priority=5,
            gpu_devices=[0],
            api_endpoint="http://127.0.0.1:8002"
        )
        
        # Mock成功响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ready", "model_loaded": True}
        mock_response.elapsed.total_seconds.return_value = 0.15
        
        with patch('httpx.AsyncClient.get', return_value=mock_response) as mock_get:
            result = await health_checker.check_model_health(
                model_info, 
                health_endpoint="/v1/models"
            )
            
            assert result.status == HealthStatus.HEALTHY
            assert result.response_time == 0.15
            
            # 验证请求了正确的端点
            mock_get.assert_called_once()
            call_args = mock_get.call_args[0]
            assert "http://127.0.0.1:8002/v1/models" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_health_check_statistics(self, health_checker, sample_model_info):
        """测试健康检查统计信息"""
        # 注册模型
        await health_checker.register_model(sample_model_info)
        
        # 模拟多次检查
        for i in range(10):
            status = HealthStatus.HEALTHY if i < 8 else HealthStatus.UNHEALTHY
            result = HealthCheckResult(
                model_id=sample_model_info.id,
                status=status,
                check_time=datetime.now() - timedelta(minutes=i),
                response_time=0.1 + i*0.01
            )
            await health_checker._update_model_status(result)
        
        stats = await health_checker.get_health_statistics(sample_model_info.id)
        
        assert stats is not None
        assert stats['model_id'] == sample_model_info.id
        assert stats['total_checks'] == 10
        assert stats['successful_checks'] == 8
        assert stats['failed_checks'] == 2
        assert stats['success_rate'] == 0.8
        assert 'avg_response_time' in stats
        assert 'last_check_time' in stats
    
    @pytest.mark.asyncio
    async def test_health_check_history_cleanup(self, health_checker, sample_model_info):
        """测试健康检查历史清理"""
        # 注册模型
        await health_checker.register_model(sample_model_info)
        
        # 设置较小的历史记录限制
        health_checker._max_history_size = 5
        
        # 添加超过限制的检查记录
        for i in range(10):
            result = HealthCheckResult(
                model_id=sample_model_info.id,
                status=HealthStatus.HEALTHY,
                check_time=datetime.now() - timedelta(minutes=i),
                response_time=0.1
            )
            await health_checker._update_model_status(result)
        
        model_data = health_checker._registered_models[sample_model_info.id]
        
        # 验证历史记录被限制在最大大小内
        assert len(model_data['check_history']) == 5
        
        # 验证保留的是最新的记录
        history = model_data['check_history']
        for i in range(len(history) - 1):
            assert history[i].check_time >= history[i + 1].check_time


if __name__ == "__main__":
    pytest.main([__file__, "-v"])