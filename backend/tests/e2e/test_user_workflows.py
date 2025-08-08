"""
用户工作流端到端测试
"""
import pytest
import asyncio
import httpx
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
import tempfile
import shutil
import time

from app.main import app
from tests.factories import TestDataGenerator


@pytest.mark.e2e
class TestUserWorkflows:
    """用户工作流端到端测试"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)
    
    @pytest.fixture
    def sample_models_data(self):
        """示例模型数据"""
        return [
            {
                "id": "llama-7b",
                "name": "Llama 7B 模型",
                "framework": "llama_cpp",
                "model_path": "/models/llama-7b.gguf",
                "priority": 5,
                "gpu_devices": [0],
                "parameters": {
                    "port": 8001,
                    "host": "127.0.0.1",
                    "ctx_size": 4096,
                    "n_gpu_layers": 32
                },
                "resource_requirements": {
                    "gpu_memory": 8192,
                    "gpu_devices": [0]
                }
            },
            {
                "id": "llama-13b",
                "name": "Llama 13B 模型",
                "framework": "vllm",
                "model_path": "/models/llama-13b",
                "priority": 8,
                "gpu_devices": [0, 1],
                "parameters": {
                    "port": 8002,
                    "host": "0.0.0.0",
                    "tensor_parallel_size": 2
                },
                "resource_requirements": {
                    "gpu_memory": 16384,
                    "gpu_devices": [0, 1]
                }
            },
            {
                "id": "code-llama",
                "name": "Code Llama 模型",
                "framework": "llama_cpp",
                "model_path": "/models/code-llama.gguf",
                "priority": 3,
                "gpu_devices": [1],
                "parameters": {
                    "port": 8003,
                    "host": "127.0.0.1",
                    "ctx_size": 2048
                },
                "resource_requirements": {
                    "gpu_memory": 6144,
                    "gpu_devices": [1]
                }
            }
        ]
    
    def test_complete_model_lifecycle_workflow(self, client, sample_models_data):
        """测试完整的模型生命周期工作流"""
        model_data = sample_models_data[0]
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True), \
             patch('app.adapters.base.BaseFrameworkAdapter._do_start_model', return_value=True), \
             patch('app.adapters.base.BaseFrameworkAdapter._do_stop_model', return_value=True):
            
            # 1. 创建模型
            create_response = client.post("/api/v1/models", json=model_data)
            assert create_response.status_code == 201
            created_model = create_response.json()
            assert created_model["id"] == model_data["id"]
            assert created_model["status"] == "stopped"
            
            # 2. 验证模型出现在列表中
            list_response = client.get("/api/v1/models")
            assert list_response.status_code == 200
            models = list_response.json()
            model_ids = [m["id"] for m in models]
            assert model_data["id"] in model_ids
            
            # 3. 获取模型详情
            get_response = client.get(f"/api/v1/models/{model_data['id']}")
            assert get_response.status_code == 200
            model_details = get_response.json()
            assert model_details["name"] == model_data["name"]
            assert model_details["framework"] == model_data["framework"]
            
            # 4. 启动模型
            start_response = client.post(f"/api/v1/models/{model_data['id']}/start")
            assert start_response.status_code == 200
            start_result = start_response.json()
            assert start_result["success"] is True
            
            # 5. 验证模型状态变为运行中
            time.sleep(0.1)  # 短暂等待状态更新
            status_response = client.get(f"/api/v1/models/{model_data['id']}/status")
            assert status_response.status_code == 200
            status_data = status_response.json()
            assert status_data["status"] in ["starting", "running"]
            
            # 6. 更新模型配置
            updated_data = model_data.copy()
            updated_data["name"] = "更新后的Llama 7B模型"
            updated_data["priority"] = 7
            
            update_response = client.put(f"/api/v1/models/{model_data['id']}", json=updated_data)
            assert update_response.status_code == 200
            updated_model = update_response.json()
            assert updated_model["name"] == "更新后的Llama 7B模型"
            assert updated_model["priority"] == 7
            
            # 7. 重启模型
            restart_response = client.post(f"/api/v1/models/{model_data['id']}/restart")
            assert restart_response.status_code == 200
            restart_result = restart_response.json()
            assert restart_result["success"] is True
            
            # 8. 停止模型
            stop_response = client.post(f"/api/v1/models/{model_data['id']}/stop")
            assert stop_response.status_code == 200
            stop_result = stop_response.json()
            assert stop_result["success"] is True
            
            # 9. 验证模型状态变为停止
            time.sleep(0.1)  # 短暂等待状态更新
            final_status_response = client.get(f"/api/v1/models/{model_data['id']}/status")
            assert final_status_response.status_code == 200
            final_status = final_status_response.json()
            assert final_status["status"] in ["stopping", "stopped"]
            
            # 10. 删除模型
            delete_response = client.delete(f"/api/v1/models/{model_data['id']}")
            assert delete_response.status_code == 200
            delete_result = delete_response.json()
            assert delete_result["success"] is True
            
            # 11. 验证模型已被删除
            final_get_response = client.get(f"/api/v1/models/{model_data['id']}")
            assert final_get_response.status_code == 404
    
    def test_multi_model_deployment_workflow(self, client, sample_models_data):
        """测试多模型部署工作流"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True), \
             patch('app.adapters.base.BaseFrameworkAdapter._do_start_model', return_value=True), \
             patch('app.utils.gpu.get_gpu_info') as mock_gpu:
            
            # Mock GPU信息
            mock_gpu.return_value = TestDataGenerator.create_gpu_cluster(2)
            
            # 1. 批量创建模型
            created_models = []
            for model_data in sample_models_data:
                response = client.post("/api/v1/models", json=model_data)
                assert response.status_code == 201
                created_models.append(response.json())
            
            # 2. 验证所有模型都被创建
            list_response = client.get("/api/v1/models")
            assert list_response.status_code == 200
            all_models = list_response.json()
            assert len(all_models) >= len(sample_models_data)
            
            # 3. 按优先级顺序启动模型
            models_by_priority = sorted(sample_models_data, key=lambda m: m["priority"], reverse=True)
            
            started_models = []
            for model_data in models_by_priority:
                start_response = client.post(f"/api/v1/models/{model_data['id']}/start")
                if start_response.status_code == 200:
                    start_result = start_response.json()
                    if start_result["success"]:
                        started_models.append(model_data["id"])
            
            # 4. 验证高优先级模型优先启动
            assert len(started_models) > 0
            if len(started_models) > 1:
                # 验证第一个启动的是最高优先级模型
                first_started = started_models[0]
                first_model = next(m for m in sample_models_data if m["id"] == first_started)
                assert first_model["priority"] >= 8  # 高优先级
            
            # 5. 检查系统概览
            overview_response = client.get("/api/v1/system/overview")
            assert overview_response.status_code == 200
            overview = overview_response.json()
            assert overview["total_models"] >= len(sample_models_data)
            assert overview["running_models"] >= len(started_models)
            
            # 6. 监控系统指标
            metrics_response = client.get("/api/v1/monitoring/metrics")
            assert metrics_response.status_code == 200
            metrics = metrics_response.json()
            assert "gpu_metrics" in metrics
            assert "system_metrics" in metrics
    
    def test_resource_management_workflow(self, client, sample_models_data):
        """测试资源管理工作流"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True), \
             patch('app.adapters.base.BaseFrameworkAdapter._do_start_model', return_value=True), \
             patch('app.utils.gpu.get_gpu_info') as mock_gpu:
            
            # Mock有限的GPU资源
            limited_gpus = TestDataGenerator.create_gpu_cluster(2)
            for gpu in limited_gpus:
                gpu.memory_free = 8192  # 每个GPU只有8GB可用
            mock_gpu.return_value = limited_gpus
            
            # 1. 创建所有模型
            for model_data in sample_models_data:
                response = client.post("/api/v1/models", json=model_data)
                assert response.status_code == 201
            
            # 2. 尝试启动需要大量资源的模型
            high_resource_model = sample_models_data[1]  # Llama 13B，需要16GB
            
            start_response = client.post(f"/api/v1/models/{high_resource_model['id']}/start")
            # 可能成功或失败，取决于资源调度逻辑
            
            # 3. 启动较小的模型
            small_model = sample_models_data[2]  # Code Llama，需要6GB
            
            small_start_response = client.post(f"/api/v1/models/{small_model['id']}/start")
            # 小模型更可能成功启动
            
            # 4. 检查资源使用情况
            metrics_response = client.get("/api/v1/monitoring/metrics")
            assert metrics_response.status_code == 200
            metrics = metrics_response.json()
            
            # 验证GPU指标
            gpu_metrics = metrics["gpu_metrics"]
            assert len(gpu_metrics) == 2
            for gpu_metric in gpu_metrics:
                assert "memory_used" in gpu_metric
                assert "memory_free" in gpu_metric
                assert "utilization" in gpu_metric
            
            # 5. 尝试资源优化
            # 如果高优先级模型启动失败，尝试停止低优先级模型
            if start_response.status_code != 200 or not start_response.json().get("success"):
                # 停止低优先级模型
                stop_response = client.post(f"/api/v1/models/{small_model['id']}/stop")
                if stop_response.status_code == 200:
                    time.sleep(0.1)  # 等待资源释放
                    
                    # 重新尝试启动高优先级模型
                    retry_response = client.post(f"/api/v1/models/{high_resource_model['id']}/start")
                    # 现在应该更可能成功
    
    def test_monitoring_and_alerting_workflow(self, client, sample_models_data):
        """测试监控和告警工作流"""
        model_data = sample_models_data[0]
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True), \
             patch('app.adapters.base.BaseFrameworkAdapter._do_start_model', return_value=True), \
             patch('app.utils.gpu.get_gpu_info') as mock_gpu, \
             patch('app.services.monitoring.MonitoringService.collect_gpu_metrics') as mock_gpu_metrics, \
             patch('app.services.monitoring.MonitoringService.collect_system_metrics') as mock_system_metrics:
            
            # Mock监控数据
            mock_gpu.return_value = TestDataGenerator.create_gpu_cluster(1)
            mock_gpu_metrics.return_value = [
                {
                    "device_id": 0,
                    "utilization": 85.0,  # 高使用率
                    "memory_used": 20480,
                    "memory_total": 24576,
                    "temperature": 78.0,  # 高温度
                    "power_usage": 350.0
                }
            ]
            mock_system_metrics.return_value = {
                "cpu_percent": 75.5,
                "memory_percent": 82.3,
                "disk_percent": 45.2
            }
            
            # 1. 创建并启动模型
            create_response = client.post("/api/v1/models", json=model_data)
            assert create_response.status_code == 201
            
            start_response = client.post(f"/api/v1/models/{model_data['id']}/start")
            assert start_response.status_code == 200
            
            # 2. 监控模型状态
            status_response = client.get(f"/api/v1/models/{model_data['id']}/status")
            assert status_response.status_code == 200
            status = status_response.json()
            assert "status" in status
            assert "health" in status
            
            # 3. 获取系统指标
            metrics_response = client.get("/api/v1/monitoring/metrics")
            assert metrics_response.status_code == 200
            metrics = metrics_response.json()
            
            # 验证指标数据
            assert "gpu_metrics" in metrics
            assert "system_metrics" in metrics
            
            gpu_metric = metrics["gpu_metrics"][0]
            assert gpu_metric["utilization"] == 85.0
            assert gpu_metric["temperature"] == 78.0
            
            system_metric = metrics["system_metrics"]
            assert system_metric["cpu_percent"] == 75.5
            assert system_metric["memory_percent"] == 82.3
            
            # 4. 检查系统概览
            overview_response = client.get("/api/v1/system/overview")
            assert overview_response.status_code == 200
            overview = overview_response.json()
            
            # 验证概览数据
            assert "total_models" in overview
            assert "running_models" in overview
            assert "gpu_info" in overview
            assert "system_health" in overview
            
            # 5. 模拟告警场景
            # 如果系统支持告警，可以测试告警触发
            # 这里可以检查是否有告警相关的端点
            
            # 6. 性能监控
            # 如果有性能历史数据端点，可以测试
            # performance_response = client.get(f"/api/v1/models/{model_data['id']}/performance")
    
    def test_configuration_management_workflow(self, client, sample_models_data):
        """测试配置管理工作流"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True):
            
            # 1. 创建多个模型配置
            for model_data in sample_models_data:
                response = client.post("/api/v1/models", json=model_data)
                assert response.status_code == 201
            
            # 2. 导出配置（如果支持）
            # export_response = client.get("/api/v1/config/export")
            # if export_response.status_code == 200:
            #     config_data = export_response.json()
            #     assert "models" in config_data
            #     assert len(config_data["models"]) >= len(sample_models_data)
            
            # 3. 批量更新配置
            for i, model_data in enumerate(sample_models_data):
                updated_data = model_data.copy()
                updated_data["name"] = f"批量更新-{model_data['name']}"
                updated_data["priority"] = min(10, model_data["priority"] + 1)
                
                update_response = client.put(f"/api/v1/models/{model_data['id']}", json=updated_data)
                assert update_response.status_code == 200
                
                updated_model = update_response.json()
                assert "批量更新-" in updated_model["name"]
            
            # 4. 验证配置持久化
            list_response = client.get("/api/v1/models")
            assert list_response.status_code == 200
            models = list_response.json()
            
            for model in models:
                if model["id"] in [m["id"] for m in sample_models_data]:
                    assert "批量更新-" in model["name"]
            
            # 5. 配置验证
            # 尝试创建无效配置
            invalid_model = {
                "id": "invalid-model",
                "name": "无效模型",
                "framework": "invalid_framework",  # 无效框架
                "model_path": "/nonexistent/path",
                "priority": 15,  # 超出范围
                "gpu_devices": [99],  # 无效GPU
                "parameters": {},
                "resource_requirements": {
                    "gpu_memory": -1,  # 无效内存
                    "gpu_devices": []
                }
            }
            
            invalid_response = client.post("/api/v1/models", json=invalid_model)
            assert invalid_response.status_code == 422  # 验证错误
    
    def test_disaster_recovery_workflow(self, client, sample_models_data):
        """测试灾难恢复工作流"""
        model_data = sample_models_data[0]
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True), \
             patch('app.adapters.base.BaseFrameworkAdapter._do_start_model', return_value=True), \
             patch('app.adapters.base.BaseFrameworkAdapter._do_stop_model', return_value=True):
            
            # 1. 正常创建和启动模型
            create_response = client.post("/api/v1/models", json=model_data)
            assert create_response.status_code == 201
            
            start_response = client.post(f"/api/v1/models/{model_data['id']}/start")
            assert start_response.status_code == 200
            
            # 2. 模拟模型故障
            with patch('app.adapters.base.BaseFrameworkAdapter._check_model_process', return_value=False):
                # 检查模型状态，应该检测到故障
                status_response = client.get(f"/api/v1/models/{model_data['id']}/status")
                assert status_response.status_code == 200
                # 状态可能变为error或unhealthy
            
            # 3. 尝试自动恢复
            restart_response = client.post(f"/api/v1/models/{model_data['id']}/restart")
            assert restart_response.status_code == 200
            restart_result = restart_response.json()
            assert restart_result["success"] is True
            
            # 4. 验证恢复成功
            time.sleep(0.1)  # 等待恢复
            recovery_status_response = client.get(f"/api/v1/models/{model_data['id']}/status")
            assert recovery_status_response.status_code == 200
            recovery_status = recovery_status_response.json()
            # 状态应该恢复为running或starting
            assert recovery_status["status"] in ["starting", "running"]
            
            # 5. 测试配置备份和恢复
            # 如果支持配置备份
            # backup_response = client.post("/api/v1/config/backup")
            # if backup_response.status_code == 200:
            #     backup_result = backup_response.json()
            #     assert "backup_id" in backup_result
            
            # 6. 系统健康检查
            health_response = client.get("/health")
            assert health_response.status_code == 200
            health_data = health_response.json()
            assert health_data["status"] == "healthy"
    
    def test_performance_optimization_workflow(self, client, sample_models_data):
        """测试性能优化工作流"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True), \
             patch('app.adapters.base.BaseFrameworkAdapter._do_start_model', return_value=True):
            
            # 1. 创建多个模型
            for model_data in sample_models_data:
                response = client.post("/api/v1/models", json=model_data)
                assert response.status_code == 201
            
            # 2. 获取基准性能指标
            initial_metrics_response = client.get("/api/v1/monitoring/metrics")
            assert initial_metrics_response.status_code == 200
            initial_metrics = initial_metrics_response.json()
            
            # 3. 启动模型并监控性能
            for model_data in sample_models_data:
                start_response = client.post(f"/api/v1/models/{model_data['id']}/start")
                if start_response.status_code == 200:
                    # 监控启动后的性能
                    time.sleep(0.1)
                    
                    status_response = client.get(f"/api/v1/models/{model_data['id']}/status")
                    assert status_response.status_code == 200
            
            # 4. 获取运行时性能指标
            runtime_metrics_response = client.get("/api/v1/monitoring/metrics")
            assert runtime_metrics_response.status_code == 200
            runtime_metrics = runtime_metrics_response.json()
            
            # 5. 性能对比分析
            # 比较启动前后的系统资源使用
            if "system_metrics" in initial_metrics and "system_metrics" in runtime_metrics:
                initial_cpu = initial_metrics["system_metrics"].get("cpu_percent", 0)
                runtime_cpu = runtime_metrics["system_metrics"].get("cpu_percent", 0)
                
                # CPU使用率应该有所增加（模型运行中）
                # assert runtime_cpu >= initial_cpu  # 可能的性能影响
            
            # 6. 资源优化建议
            # 如果系统提供优化建议端点
            # optimization_response = client.get("/api/v1/system/optimization-suggestions")
            # if optimization_response.status_code == 200:
            #     suggestions = optimization_response.json()
            #     assert "suggestions" in suggestions
            
            # 7. 系统概览验证
            overview_response = client.get("/api/v1/system/overview")
            assert overview_response.status_code == 200
            overview = overview_response.json()
            
            # 验证系统仍然健康
            assert overview.get("system_health") in ["healthy", "warning"]  # 允许警告状态


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "e2e"])