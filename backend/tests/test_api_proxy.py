"""
API代理服务测试
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import json

from app.services.api_proxy import APIProxyService, ProxyRule, LoadBalancingStrategy
from app.models.schemas import ModelConfig, ModelInfo
from app.models.enums import FrameworkType, ModelStatus, HealthStatus


class TestAPIProxyService:
    """API代理服务测试"""
    
    @pytest.fixture
    def proxy_service(self):
        """创建代理服务实例"""
        return APIProxyService()
    
    @pytest.fixture
    def sample_model_configs(self):
        """示例模型配置"""
        return [
            ModelConfig(
                id="model_1",
                name="模型1",
                framework=FrameworkType.LLAMA_CPP,
                model_path="/models/model1.gguf",
                priority=5,
                gpu_devices=[0],
                parameters={"port": 8001, "host": "127.0.0.1"}
            ),
            ModelConfig(
                id="model_2", 
                name="模型2",
                framework=FrameworkType.VLLM,
                model_path="/models/model2",
                priority=7,
                gpu_devices=[1],
                parameters={"port": 8002, "host": "127.0.0.1"}
            )
        ]
    
    @pytest.fixture
    def sample_model_infos(self, sample_model_configs):
        """示例模型信息"""
        return [
            ModelInfo(
                id=config.id,
                name=config.name,
                framework=config.framework,
                status=ModelStatus.RUNNING,
                endpoint=f"http://{config.parameters['host']}:{config.parameters['port']}",
                health=HealthStatus.HEALTHY,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            for config in sample_model_configs
        ]
    
    @pytest.mark.asyncio
    async def test_register_model_endpoint(self, proxy_service, sample_model_infos):
        """测试注册模型端点"""
        model_info = sample_model_infos[0]
        
        await proxy_service.register_model_endpoint(model_info)
        
        assert model_info.id in proxy_service._model_endpoints
        endpoint_info = proxy_service._model_endpoints[model_info.id]
        assert endpoint_info['endpoint'] == model_info.endpoint
        assert endpoint_info['status'] == ModelStatus.RUNNING
        assert endpoint_info['health'] == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_unregister_model_endpoint(self, proxy_service, sample_model_infos):
        """测试注销模型端点"""
        model_info = sample_model_infos[0]
        
        # 先注册
        await proxy_service.register_model_endpoint(model_info)
        assert model_info.id in proxy_service._model_endpoints
        
        # 再注销
        await proxy_service.unregister_model_endpoint(model_info.id)
        assert model_info.id not in proxy_service._model_endpoints
    
    @pytest.mark.asyncio
    async def test_update_model_status(self, proxy_service, sample_model_infos):
        """测试更新模型状态"""
        model_info = sample_model_infos[0]
        
        # 注册模型
        await proxy_service.register_model_endpoint(model_info)
        
        # 更新状态
        await proxy_service.update_model_status(model_info.id, ModelStatus.STOPPED)
        
        endpoint_info = proxy_service._model_endpoints[model_info.id]
        assert endpoint_info['status'] == ModelStatus.STOPPED
        assert endpoint_info['last_updated'] is not None
    
    @pytest.mark.asyncio
    async def test_update_model_health(self, proxy_service, sample_model_infos):
        """测试更新模型健康状态"""
        model_info = sample_model_infos[0]
        
        # 注册模型
        await proxy_service.register_model_endpoint(model_info)
        
        # 更新健康状态
        await proxy_service.update_model_health(model_info.id, HealthStatus.UNHEALTHY)
        
        endpoint_info = proxy_service._model_endpoints[model_info.id]
        assert endpoint_info['health'] == HealthStatus.UNHEALTHY
        assert endpoint_info['last_health_check'] is not None
    
    @pytest.mark.asyncio
    async def test_get_available_endpoints(self, proxy_service, sample_model_infos):
        """测试获取可用端点"""
        # 注册多个模型
        for model_info in sample_model_infos:
            await proxy_service.register_model_endpoint(model_info)
        
        # 设置一个模型为不健康
        await proxy_service.update_model_health(sample_model_infos[1].id, HealthStatus.UNHEALTHY)
        
        # 获取可用端点
        available = await proxy_service.get_available_endpoints()
        
        assert len(available) == 1
        assert sample_model_infos[0].id in available
        assert sample_model_infos[1].id not in available
    
    @pytest.mark.asyncio
    async def test_select_endpoint_round_robin(self, proxy_service, sample_model_infos):
        """测试轮询负载均衡端点选择"""
        # 注册多个模型
        for model_info in sample_model_infos:
            await proxy_service.register_model_endpoint(model_info)
        
        # 设置负载均衡策略为轮询
        proxy_service._load_balancing_strategy = LoadBalancingStrategy.ROUND_ROBIN
        
        # 多次选择端点，应该轮询
        selected_endpoints = []
        for _ in range(4):
            endpoint = await proxy_service.select_endpoint()
            if endpoint:
                selected_endpoints.append(endpoint['model_id'])
        
        # 验证轮询行为
        assert len(set(selected_endpoints)) == 2  # 两个不同的模型
        assert selected_endpoints[0] != selected_endpoints[1]  # 第一次和第二次不同
        assert selected_endpoints[0] == selected_endpoints[2]  # 第一次和第三次相同（轮询）
    
    @pytest.mark.asyncio
    async def test_select_endpoint_least_connections(self, proxy_service, sample_model_infos):
        """测试最少连接负载均衡端点选择"""
        # 注册多个模型
        for model_info in sample_model_infos:
            await proxy_service.register_model_endpoint(model_info)
        
        # 设置负载均衡策略为最少连接
        proxy_service._load_balancing_strategy = LoadBalancingStrategy.LEAST_CONNECTIONS
        
        # 模拟连接数
        proxy_service._connection_counts[sample_model_infos[0].id] = 5
        proxy_service._connection_counts[sample_model_infos[1].id] = 2
        
        # 选择端点，应该选择连接数最少的
        endpoint = await proxy_service.select_endpoint()
        
        assert endpoint is not None
        assert endpoint['model_id'] == sample_model_infos[1].id  # 连接数较少的模型
    
    @pytest.mark.asyncio
    async def test_proxy_request_success(self, proxy_service, sample_model_infos):
        """测试代理请求成功"""
        model_info = sample_model_infos[0]
        await proxy_service.register_model_endpoint(model_info)
        
        # Mock HTTP客户端
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "test response"}
        mock_response.headers = {"Content-Type": "application/json"}
        
        with patch('httpx.AsyncClient.post', return_value=mock_response) as mock_post:
            response = await proxy_service.proxy_request(
                model_id=model_info.id,
                path="/v1/chat/completions",
                method="POST",
                data={"messages": [{"role": "user", "content": "Hello"}]},
                headers={"Authorization": "Bearer test"}
            )
            
            assert response['status_code'] == 200
            assert response['data'] == {"response": "test response"}
            assert response['headers']['Content-Type'] == "application/json"
            
            # 验证请求被正确代理
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert model_info.endpoint in str(call_args)
    
    @pytest.mark.asyncio
    async def test_proxy_request_model_not_found(self, proxy_service):
        """测试代理请求模型不存在"""
        response = await proxy_service.proxy_request(
            model_id="nonexistent_model",
            path="/v1/chat/completions",
            method="POST",
            data={"messages": [{"role": "user", "content": "Hello"}]}
        )
        
        assert response['status_code'] == 404
        assert "模型不存在或不可用" in response['error']
    
    @pytest.mark.asyncio
    async def test_proxy_request_model_unhealthy(self, proxy_service, sample_model_infos):
        """测试代理请求模型不健康"""
        model_info = sample_model_infos[0]
        await proxy_service.register_model_endpoint(model_info)
        await proxy_service.update_model_health(model_info.id, HealthStatus.UNHEALTHY)
        
        response = await proxy_service.proxy_request(
            model_id=model_info.id,
            path="/v1/chat/completions",
            method="POST",
            data={"messages": [{"role": "user", "content": "Hello"}]}
        )
        
        assert response['status_code'] == 503
        assert "模型当前不可用" in response['error']
    
    @pytest.mark.asyncio
    async def test_proxy_request_with_failover(self, proxy_service, sample_model_infos):
        """测试带故障转移的代理请求"""
        # 注册多个模型
        for model_info in sample_model_infos:
            await proxy_service.register_model_endpoint(model_info)
        
        # 启用故障转移
        proxy_service._enable_failover = True
        
        # Mock第一个模型请求失败，第二个成功
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"response": "success"}
        mock_response_success.headers = {"Content-Type": "application/json"}
        
        with patch('httpx.AsyncClient.post') as mock_post:
            # 第一次调用失败，第二次成功
            mock_post.side_effect = [
                Exception("Connection failed"),
                mock_response_success
            ]
            
            response = await proxy_service.proxy_request_with_failover(
                path="/v1/chat/completions",
                method="POST",
                data={"messages": [{"role": "user", "content": "Hello"}]}
            )
            
            assert response['status_code'] == 200
            assert response['data'] == {"response": "success"}
            assert mock_post.call_count == 2  # 尝试了两次
    
    @pytest.mark.asyncio
    async def test_add_proxy_rule(self, proxy_service):
        """测试添加代理规则"""
        rule = ProxyRule(
            path_pattern="/api/v1/models/{model_id}/chat",
            target_path="/v1/chat/completions",
            methods=["POST"],
            auth_required=True,
            rate_limit=100
        )
        
        proxy_service.add_proxy_rule(rule)
        
        assert len(proxy_service._proxy_rules) == 1
        assert proxy_service._proxy_rules[0] == rule
    
    @pytest.mark.asyncio
    async def test_remove_proxy_rule(self, proxy_service):
        """测试移除代理规则"""
        rule = ProxyRule(
            path_pattern="/api/v1/models/{model_id}/chat",
            target_path="/v1/chat/completions",
            methods=["POST"]
        )
        
        proxy_service.add_proxy_rule(rule)
        assert len(proxy_service._proxy_rules) == 1
        
        proxy_service.remove_proxy_rule(rule.path_pattern)
        assert len(proxy_service._proxy_rules) == 0
    
    @pytest.mark.asyncio
    async def test_match_proxy_rule(self, proxy_service):
        """测试匹配代理规则"""
        rule = ProxyRule(
            path_pattern="/api/v1/models/{model_id}/chat",
            target_path="/v1/chat/completions",
            methods=["POST"]
        )
        
        proxy_service.add_proxy_rule(rule)
        
        # 测试匹配
        matched_rule, params = proxy_service._match_proxy_rule("/api/v1/models/test-model/chat", "POST")
        
        assert matched_rule == rule
        assert params == {"model_id": "test-model"}
        
        # 测试不匹配
        matched_rule, params = proxy_service._match_proxy_rule("/api/v1/other", "POST")
        assert matched_rule is None
        assert params == {}
    
    @pytest.mark.asyncio
    async def test_get_proxy_stats(self, proxy_service, sample_model_infos):
        """测试获取代理统计信息"""
        # 注册模型
        for model_info in sample_model_infos:
            await proxy_service.register_model_endpoint(model_info)
        
        # 模拟一些请求统计
        proxy_service._request_counts[sample_model_infos[0].id] = 100
        proxy_service._request_counts[sample_model_infos[1].id] = 50
        proxy_service._connection_counts[sample_model_infos[0].id] = 5
        proxy_service._connection_counts[sample_model_infos[1].id] = 3
        
        stats = await proxy_service.get_proxy_stats()
        
        assert 'total_endpoints' in stats
        assert 'available_endpoints' in stats
        assert 'total_requests' in stats
        assert 'total_connections' in stats
        assert 'model_stats' in stats
        
        assert stats['total_endpoints'] == 2
        assert stats['available_endpoints'] == 2
        assert stats['total_requests'] == 150
        assert stats['total_connections'] == 8
        assert len(stats['model_stats']) == 2
    
    @pytest.mark.asyncio
    async def test_health_check_endpoints(self, proxy_service, sample_model_infos):
        """测试端点健康检查"""
        # 注册模型
        for model_info in sample_model_infos:
            await proxy_service.register_model_endpoint(model_info)
        
        # Mock健康检查响应
        mock_response_healthy = Mock()
        mock_response_healthy.status_code = 200
        mock_response_healthy.json.return_value = {"status": "healthy"}
        
        mock_response_unhealthy = Mock()
        mock_response_unhealthy.status_code = 500
        
        with patch('httpx.AsyncClient.get') as mock_get:
            # 第一个模型健康，第二个不健康
            mock_get.side_effect = [mock_response_healthy, mock_response_unhealthy]
            
            await proxy_service.health_check_endpoints()
            
            # 验证健康状态更新
            endpoint1 = proxy_service._model_endpoints[sample_model_infos[0].id]
            endpoint2 = proxy_service._model_endpoints[sample_model_infos[1].id]
            
            assert endpoint1['health'] == HealthStatus.HEALTHY
            assert endpoint2['health'] == HealthStatus.UNHEALTHY
    
    @pytest.mark.asyncio
    async def test_connection_tracking(self, proxy_service, sample_model_infos):
        """测试连接跟踪"""
        model_info = sample_model_infos[0]
        await proxy_service.register_model_endpoint(model_info)
        
        # 增加连接
        proxy_service.increment_connection_count(model_info.id)
        assert proxy_service._connection_counts[model_info.id] == 1
        
        proxy_service.increment_connection_count(model_info.id)
        assert proxy_service._connection_counts[model_info.id] == 2
        
        # 减少连接
        proxy_service.decrement_connection_count(model_info.id)
        assert proxy_service._connection_counts[model_info.id] == 1
        
        proxy_service.decrement_connection_count(model_info.id)
        assert proxy_service._connection_counts[model_info.id] == 0
    
    @pytest.mark.asyncio
    async def test_request_rate_limiting(self, proxy_service, sample_model_infos):
        """测试请求频率限制"""
        model_info = sample_model_infos[0]
        await proxy_service.register_model_endpoint(model_info)
        
        # 设置频率限制
        proxy_service._rate_limits[model_info.id] = {
            'requests_per_minute': 10,
            'current_count': 0,
            'window_start': datetime.now()
        }
        
        # 测试在限制内的请求
        for _ in range(5):
            allowed = proxy_service._check_rate_limit(model_info.id)
            assert allowed is True
        
        # 测试超出限制的请求
        proxy_service._rate_limits[model_info.id]['current_count'] = 15
        allowed = proxy_service._check_rate_limit(model_info.id)
        assert allowed is False
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, proxy_service, sample_model_infos):
        """测试并发请求处理"""
        # 注册模型
        for model_info in sample_model_infos:
            await proxy_service.register_model_endpoint(model_info)
        
        # Mock成功响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "success"}
        mock_response.headers = {"Content-Type": "application/json"}
        
        with patch('httpx.AsyncClient.post', return_value=mock_response):
            # 并发发送多个请求
            tasks = []
            for i in range(10):
                task = proxy_service.proxy_request(
                    model_id=sample_model_infos[i % 2].id,
                    path="/v1/chat/completions",
                    method="POST",
                    data={"messages": [{"role": "user", "content": f"Hello {i}"}]}
                )
                tasks.append(task)
            
            # 等待所有请求完成
            responses = await asyncio.gather(*tasks)
            
            # 验证所有请求都成功
            assert len(responses) == 10
            for response in responses:
                assert response['status_code'] == 200
                assert response['data'] == {"response": "success"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])