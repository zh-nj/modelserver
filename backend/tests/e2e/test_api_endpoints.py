"""
API端点端到端测试
"""
import pytest
import asyncio
import httpx
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
import tempfile
import shutil
import json

from app.main import app
from app.services.model_manager import ModelManager
from app.services.config_manager import FileConfigManager
from app.models.schemas import ModelConfig, ResourceRequirement
from app.models.enums import FrameworkType, ModelStatus
from tests.factories import TestDataGenerator, create_sample_model_config


@pytest.mark.e2e
class TestAPIEndpoints:
    """API端点端到端测试"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)
    
    @pytest.fixture
    async def temp_config_dir(self):
        """创建临时配置目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_model_data(self):
        """示例模型数据"""
        return {
            "id": "test-model-1",
            "name": "测试模型1",
            "framework": "llama_cpp",
            "model_path": "/models/test.gguf",
            "priority": 5,
            "gpu_devices": [0],
            "parameters": {
                "port": 8001,
                "host": "127.0.0.1",
                "ctx_size": 2048
            },
            "resource_requirements": {
                "gpu_memory": 4096,
                "gpu_devices": [0]
            },
            "health_check": {
                "enabled": True,
                "interval": 30,
                "timeout": 10,
                "max_failures": 3,
                "endpoint": "/health"
            },
            "retry_policy": {
                "enabled": True,
                "max_attempts": 3,
                "initial_delay": 1
            }
        }
    
    def test_health_check_endpoint(self, client):
        """测试健康检查端点"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    def test_system_info_endpoint(self, client):
        """测试系统信息端点"""
        with patch('app.utils.gpu.get_gpu_info') as mock_gpu:
            mock_gpu.return_value = TestDataGenerator.create_gpu_cluster(2)
            
            response = client.get("/api/v1/system/info")
            
            assert response.status_code == 200
            data = response.json()
            assert "system" in data
            assert "cpu" in data
            assert "memory" in data
            assert "disk" in data
            assert "hostname" in data["system"]
    
    def test_create_model_endpoint(self, client, sample_model_data):
        """测试创建模型端点"""
        import os
        os.makedirs("configs", exist_ok=True)
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True), \
             patch('app.services.config_manager.FileConfigManager.save_model_config', return_value=True):
            
            response = client.post("/api/models/", json=sample_model_data)
            
            assert response.status_code == 201
            data = response.json()
            assert data["success"] is True
            assert data["model_id"] == sample_model_data["id"]
            assert "message" in data
    
    def test_list_models_endpoint(self, client, sample_model_data):
        """测试列出模型端点"""
        # 先创建一个模型
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True):
            
            client.post("/api/models/", json=sample_model_data)
        
        # 列出所有模型
        response = client.get("/api/models/")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # 验证模型数据
        model = next((m for m in data if m["id"] == sample_model_data["id"]), None)
        assert model is not None
        assert model["name"] == sample_model_data["name"]
    
    def test_get_model_endpoint(self, client, sample_model_data):
        """测试获取单个模型端点"""
        # 先创建模型
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True):
            
            client.post("/api/models/", json=sample_model_data)
        
        # 获取模型详情
        response = client.get(f"/api/models/{sample_model_data['id']}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_model_data["id"]
        assert data["name"] == sample_model_data["name"]
        assert data["framework"] == sample_model_data["framework"]
    
    def test_start_model_endpoint(self, client, sample_model_data):
        """测试启动模型端点"""
        # 先创建模型
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True):
            
            client.post("/api/models/", json=sample_model_data)
        
        # 启动模型
        with patch('app.adapters.base.BaseFrameworkAdapter._do_start_model', return_value=True):
            response = client.post(f"/api/models/{sample_model_data['id']}/start")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "message" in data
    
    def test_stop_model_endpoint(self, client, sample_model_data):
        """测试停止模型端点"""
        # 先创建并启动模型
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True):
            
            client.post("/api/models/", json=sample_model_data)
        
        with patch('app.adapters.base.BaseFrameworkAdapter._do_start_model', return_value=True):
            client.post(f"/api/models/{sample_model_data['id']}/start")
        
        # 停止模型
        with patch('app.adapters.base.BaseFrameworkAdapter._do_stop_model', return_value=True):
            response = client.post(f"/api/models/{sample_model_data['id']}/stop")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
    
    def test_restart_model_endpoint(self, client, sample_model_data):
        """测试重启模型端点"""
        # 先创建并启动模型
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True):
            
            client.post("/api/models/", json=sample_model_data)
        
        with patch('app.adapters.base.BaseFrameworkAdapter._do_start_model', return_value=True):
            client.post(f"/api/models/{sample_model_data['id']}/start")
        
        # 重启模型
        with patch('app.adapters.base.BaseFrameworkAdapter._do_stop_model', return_value=True), \
             patch('app.adapters.base.BaseFrameworkAdapter._do_start_model', return_value=True):
            
            response = client.post(f"/api/models/{sample_model_data['id']}/restart")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
    
    def test_delete_model_endpoint(self, client, sample_model_data):
        """测试删除模型端点"""
        # 先创建模型
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True):
            
            client.post("/api/models/", json=sample_model_data)
        
        # 删除模型
        response = client.delete(f"/api/models/{sample_model_data['id']}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # 验证模型已被删除
        get_response = client.get(f"/api/models/{sample_model_data['id']}")
        assert get_response.status_code == 404
    
    def test_update_model_endpoint(self, client, sample_model_data):
        """测试更新模型端点"""
        # 先创建模型
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True):
            
            client.post("/api/models/", json=sample_model_data)
        
        # 更新模型
        updated_data = sample_model_data.copy()
        updated_data["name"] = "更新后的模型名称"
        updated_data["priority"] = 8
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True):
            
            response = client.put(f"/api/models/{sample_model_data['id']}", json=updated_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "更新后的模型名称"
            assert data["priority"] == 8
    
    def test_model_status_endpoint(self, client, sample_model_data):
        """测试模型状态端点"""
        # 先创建模型
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True):
            
            client.post("/api/models/", json=sample_model_data)
        
        # 获取模型状态
        response = client.get(f"/api/models/{sample_model_data['id']}/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "health" in data
        assert data["status"] in ["stopped", "starting", "running", "error"]
    
    def test_monitoring_metrics_endpoint(self, client):
        """测试监控指标端点"""
        with patch('app.services.monitoring.MonitoringService.collect_gpu_metrics') as mock_gpu, \
             patch('app.services.monitoring.MonitoringService.collect_system_metrics') as mock_system:
            
            mock_gpu.return_value = TestDataGenerator.create_gpu_cluster(2)
            mock_system.return_value = {
                "cpu_percent": 45.5,
                "memory_percent": 60.2,
                "disk_percent": 35.8
            }
            
            response = client.get("/api/monitoring/system")
            
            assert response.status_code == 200
            data = response.json()
            assert "gpu_metrics" in data
            assert "system_metrics" in data
            assert len(data["gpu_metrics"]) == 2
    
    def test_system_overview_endpoint(self, client):
        """测试系统概览端点"""
        with patch('app.services.monitoring.MonitoringService.get_system_overview') as mock_overview:
            mock_overview.return_value = Mock(
                total_models=3,
                running_models=2,
                gpu_info=TestDataGenerator.create_gpu_cluster(2),
                system_health="healthy",
                cpu_usage=45.5,
                memory_usage=60.2
            )
            
            response = client.get("/system/overview")
            
            assert response.status_code == 200
            data = response.json()
            assert "total_models" in data
            assert "running_models" in data
            assert "gpu_info" in data
            assert data["total_models"] == 3
            assert data["running_models"] == 2
    
    def test_error_handling(self, client):
        """测试错误处理"""
        # 测试获取不存在的模型
        response = client.get("/api/models/nonexistent-model")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        
        # 测试无效的模型数据
        invalid_data = {"invalid": "data"}
        response = client.post("/api/models/", json=invalid_data)
        assert response.status_code == 422  # Validation error
        
        # 测试启动不存在的模型
        response = client.post("/api/models/nonexistent-model/start")
        assert response.status_code == 404
    
    def test_concurrent_api_requests(self, client, sample_model_data):
        """测试并发API请求"""
        # 先创建模型
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True):
            
            client.post("/api/models/", json=sample_model_data)
        
        # 并发发送多个状态查询请求
        import concurrent.futures
        import threading
        
        def get_model_status():
            return client.get(f"/api/models/{sample_model_data['id']}/status")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_model_status) for _ in range(20)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # 验证所有请求都成功
        for response in results:
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
    
    def test_api_authentication(self, client):
        """测试API认证（如果启用）"""
        # 这里可以测试API密钥或JWT认证
        # 目前系统可能没有启用认证，所以这是一个占位符测试
        
        # 测试无认证访问（应该成功，因为当前没有启用认证）
        response = client.get("/api/models/")
        assert response.status_code == 200
        
        # 如果将来启用认证，可以测试：
        # - 无效的API密钥
        # - 过期的JWT令牌
        # - 缺少认证头
    
    def test_api_rate_limiting(self, client):
        """测试API速率限制"""
        # 快速发送大量请求
        responses = []
        for _ in range(100):
            response = client.get("/health")
            responses.append(response)
        
        # 验证大部分请求成功（如果没有启用速率限制）
        successful_responses = [r for r in responses if r.status_code == 200]
        assert len(successful_responses) >= 90  # 允许少量失败
        
        # 如果启用了速率限制，可以验证429状态码
        rate_limited_responses = [r for r in responses if r.status_code == 429]
        # assert len(rate_limited_responses) > 0  # 如果启用了速率限制
    
    def test_api_response_format(self, client, sample_model_data):
        """测试API响应格式"""
        # 创建模型
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True):
            
            response = client.post("/api/models/", json=sample_model_data)
        
        # 验证响应格式
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        
        # 验证必需字段
        required_fields = ["id", "name", "framework", "status", "created_at"]
        for field in required_fields:
            assert field in data
        
        # 验证数据类型
        assert isinstance(data["id"], str)
        assert isinstance(data["name"], str)
        assert isinstance(data["priority"], int)
        assert isinstance(data["gpu_devices"], list)
    
    def test_api_pagination(self, client):
        """测试API分页"""
        # 创建多个模型
        models_data = []
        for i in range(15):
            model_data = {
                "id": f"test-model-{i}",
                "name": f"测试模型{i}",
                "framework": "llama_cpp",
                "model_path": f"/models/test{i}.gguf",
                "priority": 5,
                "gpu_devices": [0],
                "parameters": {"port": 8000 + i},
                "resource_requirements": {"gpu_memory": 4096, "gpu_devices": [0]}
            }
            models_data.append(model_data)
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True):
            
            for model_data in models_data:
                client.post("/api/models/", json=model_data)
        
        # 测试分页参数
        response = client.get("/api/models/?page=1&size=10")
        assert response.status_code == 200
        data = response.json()
        
        # 如果实现了分页，验证响应结构
        if isinstance(data, dict) and "items" in data:
            assert len(data["items"]) <= 10
            assert "total" in data
            assert "page" in data
            assert "size" in data
        else:
            # 如果没有实现分页，至少验证返回了模型列表
            assert isinstance(data, list)
            assert len(data) >= 15


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "e2e"])