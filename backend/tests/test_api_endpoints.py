"""
测试API端点的可访问性和响应格式
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from app.main import app
from app.models.schemas import SystemOverview, GPUInfo, ModelConfig, ResourceRequirement
from app.models.enums import FrameworkType, ModelStatus, GPUVendor

client = TestClient(app)

class TestSystemEndpoints:
    """测试系统相关API端点"""
    
    @patch('app.core.dependencies.get_monitoring_service')
    def test_get_system_overview(self, mock_get_monitoring_service):
        """测试获取系统概览端点"""
        # 模拟监控服务
        mock_service = Mock()
        mock_overview = SystemOverview(
            total_models=5,
            running_models=3,
            total_gpus=2,
            available_gpus=1,
            total_gpu_memory=16384,
            used_gpu_memory=8192,
            system_uptime=3600,
            last_updated="2025-01-11T12:00:00"
        )
        mock_service.get_system_overview.return_value = mock_overview
        mock_get_monitoring_service.return_value = mock_service
        
        # 发送请求
        response = client.get("/api/v1/system/overview")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["total_models"] == 5
        assert data["running_models"] == 3
        assert data["total_gpus"] == 2
    
    @patch('app.core.dependencies.get_gpu_detector')
    def test_get_gpu_info(self, mock_get_gpu_detector):
        """测试获取GPU信息端点"""
        # 模拟GPU检测器
        mock_detector = Mock()
        mock_gpus = [
            GPUInfo(
                device_id=0,
                name="NVIDIA RTX 4090",
                vendor=GPUVendor.NVIDIA,
                memory_total=24576,
                memory_used=8192,
                memory_free=16384,
                utilization=75.0,
                temperature=65.0,
                power_usage=350.0,
                driver_version="535.86.10"
            )
        ]
        mock_detector.detect_gpus.return_value = mock_gpus
        mock_get_gpu_detector.return_value = mock_detector
        
        # 发送请求
        response = client.get("/api/v1/system/gpu")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["device_id"] == 0
        assert data[0]["name"] == "NVIDIA RTX 4090"
        assert data[0]["memory_total"] == 24576
    
    @patch('app.core.dependencies.get_monitoring_service')
    def test_get_system_health(self, mock_get_monitoring_service):
        """测试系统健康检查端点"""
        # 发送请求
        response = client.get("/api/v1/system/health")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "components" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

class TestMonitoringEndpoints:
    """测试监控相关API端点"""
    
    @patch('app.core.dependencies.get_monitoring_service')
    def test_get_system_metrics(self, mock_get_monitoring_service):
        """测试获取系统指标端点"""
        # 模拟监控服务
        mock_service = Mock()
        mock_metrics = Mock()
        mock_metrics.timestamp = "2025-01-11T12:00:00"
        mock_metrics.cpu_usage = 45.5
        mock_metrics.memory_usage = 60.2
        mock_metrics.disk_usage = 30.1
        mock_metrics.memory_total = 32768
        mock_metrics.memory_used = 19661
        mock_metrics.disk_total = 1000
        mock_metrics.disk_used = 301
        mock_metrics.network_sent = 1024000
        mock_metrics.network_recv = 2048000
        mock_metrics.load_average = [1.5, 1.2, 1.0]
        
        mock_service.system_collector.collect_metrics.return_value = mock_metrics
        mock_get_monitoring_service.return_value = mock_service
        
        # 发送请求
        response = client.get("/api/monitoring/metrics/system")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "cpu_usage" in data
        assert "memory_usage" in data
        assert data["cpu_usage"] == 45.5
        assert data["memory_usage"] == 60.2
    
    @patch('app.core.dependencies.get_monitoring_service')
    def test_get_gpu_metrics(self, mock_get_monitoring_service):
        """测试获取GPU指标端点"""
        # 模拟监控服务
        mock_service = Mock()
        mock_gpu_metrics = [
            Mock(
                device_id=0,
                timestamp="2025-01-11T12:00:00",
                utilization=75.0,
                memory_used=8192,
                memory_total=24576,
                temperature=65.0,
                power_usage=350.0
            )
        ]
        mock_service.collect_gpu_metrics.return_value = mock_gpu_metrics
        mock_get_monitoring_service.return_value = mock_service
        
        # 发送请求
        response = client.get("/api/monitoring/gpu")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["device_id"] == 0
        assert data[0]["utilization"] == 75.0

class TestModelEndpoints:
    """测试模型相关API端点"""
    
    @patch('app.core.dependencies.get_model_manager')
    def test_list_models(self, mock_get_model_manager):
        """测试获取模型列表端点"""
        # 模拟模型管理器
        mock_manager = Mock()
        mock_models = [
            Mock(
                id="test-model-1",
                name="测试模型1",
                framework=FrameworkType.LLAMA_CPP,
                status=ModelStatus.RUNNING,
                priority=5,
                gpu_devices=[0],
                memory_usage=4096,
                api_endpoint="http://localhost:8080",
                uptime=3600,
                last_health_check="2025-01-11T12:00:00"
            )
        ]
        mock_manager.list_models.return_value = mock_models
        mock_get_model_manager.return_value = mock_manager
        
        # 发送请求
        response = client.get("/api/models/")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "test-model-1"
        assert data[0]["name"] == "测试模型1"
        assert data[0]["status"] == "running"
    
    @patch('app.core.dependencies.get_model_manager')
    def test_create_model(self, mock_get_model_manager):
        """测试创建模型端点"""
        # 模拟模型管理器
        mock_manager = Mock()
        mock_manager.create_model.return_value = "test-model-1"
        mock_get_model_manager.return_value = mock_manager
        
        # 准备测试数据
        model_config = {
            "id": "test-model-1",
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
        
        # 发送请求
        response = client.post("/api/models/", json=model_config)
        
        # 验证响应
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["model_id"] == "test-model-1"
    
    @patch('app.core.dependencies.get_model_manager')
    def test_validate_model_config(self, mock_get_model_manager):
        """测试验证模型配置端点"""
        # 模拟模型管理器
        mock_manager = Mock()
        mock_validation_result = Mock()
        mock_validation_result.is_valid = True
        mock_validation_result.errors = []
        mock_validation_result.warnings = []
        mock_manager.validate_model_config.return_value = mock_validation_result
        mock_get_model_manager.return_value = mock_manager
        
        # 准备测试数据
        model_config = {
            "id": "test-model-1",
            "name": "测试模型",
            "framework": "llama_cpp",
            "model_path": "/path/to/model.gguf",
            "priority": 5,
            "gpu_devices": [0],
            "additional_parameters": "--verbose",
            "parameters": {
                "port": 8080,
                "host": "0.0.0.0"
            },
            "resource_requirements": {
                "gpu_memory": 4096,
                "gpu_devices": [0]
            }
        }
        
        # 发送请求
        response = client.post("/api/models/validate", json=model_config)
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is True
        assert data["errors"] == []

class TestErrorHandling:
    """测试错误处理"""
    
    def test_404_endpoint(self):
        """测试不存在的端点返回404"""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404
    
    @patch('app.core.dependencies.get_monitoring_service')
    def test_500_error_handling(self, mock_get_monitoring_service):
        """测试服务器错误处理"""
        # 模拟服务抛出异常
        mock_service = Mock()
        mock_service.get_system_overview.side_effect = Exception("测试异常")
        mock_get_monitoring_service.return_value = mock_service
        
        # 发送请求
        response = client.get("/api/v1/system/overview")
        
        # 验证响应
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "获取系统状态概览失败" in data["detail"]

class TestAPIConsistency:
    """测试API一致性"""
    
    def test_api_prefix_consistency(self):
        """测试API前缀一致性"""
        # 测试系统API使用v1前缀
        response = client.get("/api/v1/system/health")
        assert response.status_code == 200
        
        # 测试监控API使用monitoring前缀
        with patch('app.core.dependencies.get_monitoring_service') as mock_service:
            mock_service.return_value.system_collector.collect_metrics.return_value = Mock(
                timestamp="2025-01-11T12:00:00",
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                memory_total=0,
                memory_used=0,
                disk_total=0,
                disk_used=0,
                network_sent=0,
                network_recv=0,
                load_average=[]
            )
            response = client.get("/api/monitoring/metrics/system")
            assert response.status_code == 200
    
    def test_response_format_consistency(self):
        """测试响应格式一致性"""
        # 测试成功响应格式
        with patch('app.core.dependencies.get_model_manager') as mock_manager:
            mock_manager.return_value.list_models.return_value = []
            response = client.get("/api/models/")
            assert response.status_code == 200
            assert isinstance(response.json(), list)
        
        # 测试错误响应格式
        response = client.get("/api/models/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

@pytest.mark.parametrize("endpoint,expected_status", [
    ("/api/v1/system/health", 200),
    ("/api/v1/system/info", 200),
    ("/api/models/", 200),
    ("/api/nonexistent", 404),
])
def test_endpoint_accessibility(endpoint, expected_status):
    """参数化测试端点可访问性"""
    with patch('app.core.dependencies.get_model_manager') as mock_manager:
        mock_manager.return_value.list_models.return_value = []
        response = client.get(endpoint)
        assert response.status_code == expected_status