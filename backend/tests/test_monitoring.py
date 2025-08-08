"""
监控服务测试
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import json

from app.services.monitoring import MonitoringService, MetricsCollector, AlertManager
from app.models.schemas import (
    GPUInfo, ModelInfo, SystemOverview, AlertRule, AlertCondition, 
    TimeRange
)
from app.services.metrics_storage import MetricsQuery, PerformanceMetrics
from app.models.enums import (
    ModelStatus, HealthStatus, GPUVendor, AlertSeverity, 
    AlertType, MetricType, ComparisonOperator
)


class TestMonitoringService:
    """监控服务测试"""
    
    @pytest.fixture
    def monitoring_service(self):
        """创建监控服务实例"""
        return MonitoringService()
    
    @pytest.fixture
    def sample_gpu_info(self):
        """示例GPU信息"""
        return [
            GPUInfo(
                device_id=0,
                name="NVIDIA RTX 4090",
                vendor=GPUVendor.NVIDIA,
                memory_total=24576,
                memory_used=12288,
                memory_free=12288,
                utilization=50.0,
                temperature=65.0,
                power_usage=250.0
            ),
            GPUInfo(
                device_id=1,
                name="NVIDIA RTX 4090", 
                vendor=GPUVendor.NVIDIA,
                memory_total=24576,
                memory_used=8192,
                memory_free=16384,
                utilization=30.0,
                temperature=60.0,
                power_usage=200.0
            )
        ]
    
    @pytest.fixture
    def sample_model_infos(self):
        """示例模型信息"""
        return [
            ModelInfo(
                id="model_1",
                name="模型1",
                framework="llama.cpp",
                status=ModelStatus.RUNNING,
                endpoint="http://127.0.0.1:8001",
                health=HealthStatus.HEALTHY,
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            ModelInfo(
                id="model_2",
                name="模型2", 
                framework="vllm",
                status=ModelStatus.RUNNING,
                endpoint="http://127.0.0.1:8002",
                health=HealthStatus.HEALTHY,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]
    
    @pytest.mark.asyncio
    async def test_collect_gpu_metrics(self, monitoring_service, sample_gpu_info):
        """测试GPU指标收集"""
        with patch('app.utils.gpu.get_gpu_info', return_value=sample_gpu_info):
            metrics = await monitoring_service.collect_gpu_metrics()
            
            assert len(metrics) == 2
            assert metrics[0].device_id == 0
            assert metrics[0].memory_used == 12288
            assert metrics[0].utilization == 50.0
            assert metrics[1].device_id == 1
            assert metrics[1].memory_used == 8192
            assert metrics[1].utilization == 30.0
    
    @pytest.mark.asyncio
    async def test_collect_model_metrics(self, monitoring_service, sample_model_infos):
        """测试模型指标收集"""
        # Mock模型管理器
        mock_model_manager = Mock()
        mock_model_manager.list_models.return_value = sample_model_infos
        mock_model_manager.get_model_health.side_effect = [
            HealthStatus.HEALTHY, HealthStatus.HEALTHY
        ]
        
        monitoring_service._model_manager = mock_model_manager
        
        metrics = await monitoring_service.collect_model_metrics()
        
        assert len(metrics) == 2
        assert metrics[0]['model_id'] == "model_1"
        assert metrics[0]['status'] == ModelStatus.RUNNING
        assert metrics[0]['health'] == HealthStatus.HEALTHY
        assert metrics[1]['model_id'] == "model_2"
        assert metrics[1]['status'] == ModelStatus.RUNNING
        assert metrics[1]['health'] == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_collect_system_metrics(self, monitoring_service):
        """测试系统指标收集"""
        with patch('psutil.cpu_percent', return_value=45.5), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:
            
            # Mock内存信息
            mock_memory.return_value = Mock(
                total=32 * 1024**3,  # 32GB
                used=16 * 1024**3,   # 16GB
                percent=50.0
            )
            
            # Mock磁盘信息
            mock_disk.return_value = Mock(
                total=1024 * 1024**3,  # 1TB
                used=512 * 1024**3,    # 512GB
                percent=50.0
            )
            
            metrics = await monitoring_service.collect_system_metrics()
            
            assert 'cpu_percent' in metrics
            assert 'memory_total' in metrics
            assert 'memory_used' in metrics
            assert 'memory_percent' in metrics
            assert 'disk_total' in metrics
            assert 'disk_used' in metrics
            assert 'disk_percent' in metrics
            
            assert metrics['cpu_percent'] == 45.5
            assert metrics['memory_percent'] == 50.0
            assert metrics['disk_percent'] == 50.0
    
    @pytest.mark.asyncio
    async def test_get_system_overview(self, monitoring_service, sample_gpu_info, sample_model_infos):
        """测试获取系统概览"""
        # Mock各种数据收集方法
        with patch.object(monitoring_service, 'collect_gpu_metrics', return_value=sample_gpu_info), \
             patch.object(monitoring_service, 'collect_model_metrics', return_value=[
                 {'model_id': info.id, 'status': info.status, 'health': info.health}
                 for info in sample_model_infos
             ]), \
             patch.object(monitoring_service, 'collect_system_metrics', return_value={
                 'cpu_percent': 45.5,
                 'memory_percent': 50.0,
                 'disk_percent': 30.0
             }):
            
            overview = await monitoring_service.get_system_overview()
            
            assert isinstance(overview, SystemOverview)
            assert len(overview.gpu_info) == 2
            assert overview.total_models == 2
            assert overview.running_models == 2
            assert overview.system_health == HealthStatus.HEALTHY
            assert overview.cpu_usage == 45.5
            assert overview.memory_usage == 50.0
    
    @pytest.mark.asyncio
    async def test_check_model_health(self, monitoring_service):
        """测试模型健康检查"""
        model_id = "test_model"
        endpoint = "http://127.0.0.1:8001"
        
        # Mock成功的健康检查
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}
        
        with patch('httpx.AsyncClient.get', return_value=mock_response):
            health = await monitoring_service.check_model_health(model_id, endpoint)
            assert health == HealthStatus.HEALTHY
        
        # Mock失败的健康检查
        with patch('httpx.AsyncClient.get', side_effect=Exception("Connection failed")):
            health = await monitoring_service.check_model_health(model_id, endpoint)
            assert health == HealthStatus.UNHEALTHY
    
    @pytest.mark.asyncio
    async def test_store_metrics(self, monitoring_service):
        """测试指标存储"""
        metrics_data = {
            'timestamp': datetime.now(),
            'gpu_metrics': [
                {'device_id': 0, 'utilization': 50.0, 'memory_used': 12288}
            ],
            'model_metrics': [
                {'model_id': 'test_model', 'status': 'running', 'response_time': 0.5}
            ],
            'system_metrics': {
                'cpu_percent': 45.5,
                'memory_percent': 50.0
            }
        }
        
        # Mock指标存储服务
        mock_storage = Mock()
        mock_storage.store_metrics = AsyncMock()
        monitoring_service._metrics_storage = mock_storage
        
        await monitoring_service.store_metrics(metrics_data)
        
        mock_storage.store_metrics.assert_called_once_with(metrics_data)
    
    @pytest.mark.asyncio
    async def test_query_metrics(self, monitoring_service):
        """测试指标查询"""
        query = MetricsQuery(
            metric_type=MetricType.GPU_UTILIZATION,
            time_range=TimeRange(
                start_time=datetime.now() - timedelta(hours=1),
                end_time=datetime.now()
            ),
            filters={'device_id': 0}
        )
        
        # Mock查询结果
        mock_results = [
            {'timestamp': datetime.now() - timedelta(minutes=30), 'value': 45.0},
            {'timestamp': datetime.now() - timedelta(minutes=15), 'value': 55.0},
            {'timestamp': datetime.now(), 'value': 50.0}
        ]
        
        mock_storage = Mock()
        mock_storage.query_metrics = AsyncMock(return_value=mock_results)
        monitoring_service._metrics_storage = mock_storage
        
        results = await monitoring_service.query_metrics(query)
        
        assert len(results) == 3
        assert results[0]['value'] == 45.0
        assert results[2]['value'] == 50.0
        mock_storage.query_metrics.assert_called_once_with(query)
    
    @pytest.mark.asyncio
    async def test_get_performance_metrics(self, monitoring_service):
        """测试获取性能指标"""
        model_id = "test_model"
        time_range = TimeRange(
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now()
        )
        
        # Mock性能数据
        mock_metrics = PerformanceMetrics(
            model_id=model_id,
            time_range=time_range,
            avg_response_time=0.5,
            max_response_time=1.2,
            min_response_time=0.2,
            total_requests=100,
            successful_requests=95,
            failed_requests=5,
            requests_per_second=27.8,
            error_rate=0.05
        )
        
        mock_storage = Mock()
        mock_storage.get_performance_metrics = AsyncMock(return_value=mock_metrics)
        monitoring_service._metrics_storage = mock_storage
        
        metrics = await monitoring_service.get_performance_metrics(model_id, time_range)
        
        assert metrics.model_id == model_id
        assert metrics.avg_response_time == 0.5
        assert metrics.total_requests == 100
        assert metrics.error_rate == 0.05
        mock_storage.get_performance_metrics.assert_called_once_with(model_id, time_range)
    
    @pytest.mark.asyncio
    async def test_setup_alerts(self, monitoring_service):
        """测试设置告警规则"""
        alert_rules = [
            AlertRule(
                id="gpu_high_utilization",
                name="GPU使用率过高",
                description="GPU使用率超过90%时触发告警",
                metric_type=MetricType.GPU_UTILIZATION,
                condition=AlertCondition(
                    operator=ComparisonOperator.GREATER_THAN,
                    threshold=90.0,
                    duration_minutes=5
                ),
                severity=AlertSeverity.WARNING,
                enabled=True
            ),
            AlertRule(
                id="model_health_check_failed",
                name="模型健康检查失败",
                description="模型健康检查连续失败时触发告警",
                metric_type=MetricType.MODEL_HEALTH,
                condition=AlertCondition(
                    operator=ComparisonOperator.EQUALS,
                    threshold="unhealthy",
                    duration_minutes=2
                ),
                severity=AlertSeverity.CRITICAL,
                enabled=True
            )
        ]
        
        # Mock告警管理器
        mock_alert_manager = Mock()
        mock_alert_manager.setup_rules = AsyncMock(return_value=True)
        monitoring_service._alert_manager = mock_alert_manager
        
        result = await monitoring_service.setup_alerts(alert_rules)
        
        assert result is True
        mock_alert_manager.setup_rules.assert_called_once_with(alert_rules)
    
    @pytest.mark.asyncio
    async def test_check_alert_conditions(self, monitoring_service):
        """测试检查告警条件"""
        # 设置告警规则
        alert_rule = AlertRule(
            id="high_gpu_temp",
            name="GPU温度过高",
            metric_type=MetricType.GPU_TEMPERATURE,
            condition=AlertCondition(
                operator=ComparisonOperator.GREATER_THAN,
                threshold=80.0,
                duration_minutes=1
            ),
            severity=AlertSeverity.WARNING,
            enabled=True
        )
        
        # Mock当前指标数据
        current_metrics = {
            'gpu_metrics': [
                {'device_id': 0, 'temperature': 85.0},  # 超过阈值
                {'device_id': 1, 'temperature': 70.0}   # 正常
            ]
        }
        
        mock_alert_manager = Mock()
        mock_alert_manager.check_conditions = AsyncMock(return_value=[
            {
                'rule_id': 'high_gpu_temp',
                'triggered': True,
                'message': 'GPU 0温度达到85°C，超过阈值80°C'
            }
        ])
        monitoring_service._alert_manager = mock_alert_manager
        
        triggered_alerts = await monitoring_service.check_alert_conditions(current_metrics)
        
        assert len(triggered_alerts) == 1
        assert triggered_alerts[0]['rule_id'] == 'high_gpu_temp'
        assert triggered_alerts[0]['triggered'] is True
        mock_alert_manager.check_conditions.assert_called_once_with(current_metrics)
    
    @pytest.mark.asyncio
    async def test_get_alert_history(self, monitoring_service):
        """测试获取告警历史"""
        time_range = TimeRange(
            start_time=datetime.now() - timedelta(days=1),
            end_time=datetime.now()
        )
        
        # Mock告警历史数据
        mock_history = [
            {
                'id': 'alert_1',
                'rule_id': 'high_gpu_temp',
                'severity': AlertSeverity.WARNING,
                'message': 'GPU温度过高',
                'triggered_at': datetime.now() - timedelta(hours=2),
                'resolved_at': datetime.now() - timedelta(hours=1),
                'status': 'resolved'
            },
            {
                'id': 'alert_2',
                'rule_id': 'model_unhealthy',
                'severity': AlertSeverity.CRITICAL,
                'message': '模型健康检查失败',
                'triggered_at': datetime.now() - timedelta(minutes=30),
                'resolved_at': None,
                'status': 'active'
            }
        ]
        
        mock_alert_manager = Mock()
        mock_alert_manager.get_alert_history = AsyncMock(return_value=mock_history)
        monitoring_service._alert_manager = mock_alert_manager
        
        history = await monitoring_service.get_alert_history(time_range)
        
        assert len(history) == 2
        assert history[0]['status'] == 'resolved'
        assert history[1]['status'] == 'active'
        mock_alert_manager.get_alert_history.assert_called_once_with(time_range)
    
    @pytest.mark.asyncio
    async def test_start_monitoring(self, monitoring_service):
        """测试启动监控"""
        # Mock各种组件
        monitoring_service._metrics_collector = Mock()
        monitoring_service._metrics_collector.start = AsyncMock()
        monitoring_service._alert_manager = Mock()
        monitoring_service._alert_manager.start = AsyncMock()
        
        await monitoring_service.start_monitoring()
        
        assert monitoring_service._is_running is True
        monitoring_service._metrics_collector.start.assert_called_once()
        monitoring_service._alert_manager.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_monitoring(self, monitoring_service):
        """测试停止监控"""
        # 先启动监控
        monitoring_service._is_running = True
        monitoring_service._metrics_collector = Mock()
        monitoring_service._metrics_collector.stop = AsyncMock()
        monitoring_service._alert_manager = Mock()
        monitoring_service._alert_manager.stop = AsyncMock()
        
        await monitoring_service.stop_monitoring()
        
        assert monitoring_service._is_running is False
        monitoring_service._metrics_collector.stop.assert_called_once()
        monitoring_service._alert_manager.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_monitoring_loop(self, monitoring_service, sample_gpu_info):
        """测试监控循环"""
        # Mock数据收集方法
        monitoring_service.collect_gpu_metrics = AsyncMock(return_value=sample_gpu_info)
        monitoring_service.collect_model_metrics = AsyncMock(return_value=[])
        monitoring_service.collect_system_metrics = AsyncMock(return_value={'cpu_percent': 50.0})
        monitoring_service.store_metrics = AsyncMock()
        monitoring_service.check_alert_conditions = AsyncMock(return_value=[])
        
        # 设置监控间隔为很短的时间用于测试
        monitoring_service._monitoring_interval = 0.1
        monitoring_service._is_running = True
        
        # 启动监控循环，运行一小段时间后停止
        monitoring_task = asyncio.create_task(monitoring_service._monitoring_loop())
        await asyncio.sleep(0.3)  # 让循环运行几次
        monitoring_service._is_running = False
        
        try:
            await asyncio.wait_for(monitoring_task, timeout=1.0)
        except asyncio.TimeoutError:
            monitoring_task.cancel()
        
        # 验证数据收集方法被调用
        assert monitoring_service.collect_gpu_metrics.call_count >= 1
        assert monitoring_service.collect_model_metrics.call_count >= 1
        assert monitoring_service.collect_system_metrics.call_count >= 1
        assert monitoring_service.store_metrics.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_get_monitoring_status(self, monitoring_service):
        """测试获取监控状态"""
        # 设置监控状态
        monitoring_service._is_running = True
        monitoring_service._last_collection_time = datetime.now()
        monitoring_service._collection_count = 100
        monitoring_service._error_count = 2
        
        status = await monitoring_service.get_monitoring_status()
        
        assert status['is_running'] is True
        assert status['collection_count'] == 100
        assert status['error_count'] == 2
        assert 'last_collection_time' in status
        assert 'uptime_seconds' in status
    
    @pytest.mark.asyncio
    async def test_export_metrics(self, monitoring_service):
        """测试导出指标"""
        time_range = TimeRange(
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now()
        )
        
        # Mock导出数据
        mock_export_data = {
            'time_range': time_range,
            'gpu_metrics': [
                {'timestamp': datetime.now(), 'device_id': 0, 'utilization': 50.0}
            ],
            'model_metrics': [
                {'timestamp': datetime.now(), 'model_id': 'test', 'response_time': 0.5}
            ],
            'system_metrics': [
                {'timestamp': datetime.now(), 'cpu_percent': 45.0}
            ]
        }
        
        mock_storage = Mock()
        mock_storage.export_metrics = AsyncMock(return_value=mock_export_data)
        monitoring_service._metrics_storage = mock_storage
        
        export_data = await monitoring_service.export_metrics(time_range, format='json')
        
        assert 'time_range' in export_data
        assert 'gpu_metrics' in export_data
        assert 'model_metrics' in export_data
        assert 'system_metrics' in export_data
        mock_storage.export_metrics.assert_called_once_with(time_range, 'json')


class TestMetricsCollector:
    """指标收集器测试"""
    
    @pytest.fixture
    def metrics_collector(self):
        """创建指标收集器实例"""
        return MetricsCollector()
    
    @pytest.mark.asyncio
    async def test_collect_all_metrics(self, metrics_collector):
        """测试收集所有指标"""
        # Mock各种指标收集方法
        metrics_collector.collect_gpu_metrics = AsyncMock(return_value=[
            {'device_id': 0, 'utilization': 50.0}
        ])
        metrics_collector.collect_model_metrics = AsyncMock(return_value=[
            {'model_id': 'test', 'status': 'running'}
        ])
        metrics_collector.collect_system_metrics = AsyncMock(return_value={
            'cpu_percent': 45.0
        })
        
        all_metrics = await metrics_collector.collect_all_metrics()
        
        assert 'timestamp' in all_metrics
        assert 'gpu_metrics' in all_metrics
        assert 'model_metrics' in all_metrics
        assert 'system_metrics' in all_metrics
        assert len(all_metrics['gpu_metrics']) == 1
        assert len(all_metrics['model_metrics']) == 1


class TestAlertManager:
    """告警管理器测试"""
    
    @pytest.fixture
    def alert_manager(self):
        """创建告警管理器实例"""
        return AlertManager()
    
    @pytest.mark.asyncio
    async def test_add_alert_rule(self, alert_manager):
        """测试添加告警规则"""
        rule = AlertRule(
            id="test_rule",
            name="测试规则",
            metric_type=MetricType.GPU_UTILIZATION,
            condition=AlertCondition(
                operator=ComparisonOperator.GREATER_THAN,
                threshold=90.0
            ),
            severity=AlertSeverity.WARNING,
            enabled=True
        )
        
        await alert_manager.add_alert_rule(rule)
        
        assert rule.id in alert_manager._alert_rules
        assert alert_manager._alert_rules[rule.id] == rule
    
    @pytest.mark.asyncio
    async def test_remove_alert_rule(self, alert_manager):
        """测试移除告警规则"""
        rule = AlertRule(
            id="test_rule",
            name="测试规则",
            metric_type=MetricType.GPU_UTILIZATION,
            condition=AlertCondition(
                operator=ComparisonOperator.GREATER_THAN,
                threshold=90.0
            ),
            severity=AlertSeverity.WARNING,
            enabled=True
        )
        
        await alert_manager.add_alert_rule(rule)
        assert rule.id in alert_manager._alert_rules
        
        await alert_manager.remove_alert_rule(rule.id)
        assert rule.id not in alert_manager._alert_rules
    
    @pytest.mark.asyncio
    async def test_evaluate_alert_condition(self, alert_manager):
        """测试评估告警条件"""
        rule = AlertRule(
            id="high_gpu_util",
            name="GPU使用率过高",
            metric_type=MetricType.GPU_UTILIZATION,
            condition=AlertCondition(
                operator=ComparisonOperator.GREATER_THAN,
                threshold=80.0
            ),
            severity=AlertSeverity.WARNING,
            enabled=True
        )
        
        # 测试触发条件
        metrics_data = {
            'gpu_metrics': [
                {'device_id': 0, 'utilization': 85.0}  # 超过阈值
            ]
        }
        
        result = await alert_manager._evaluate_alert_condition(rule, metrics_data)
        
        assert result['triggered'] is True
        assert 'GPU使用率' in result['message']
        
        # 测试未触发条件
        metrics_data = {
            'gpu_metrics': [
                {'device_id': 0, 'utilization': 75.0}  # 未超过阈值
            ]
        }
        
        result = await alert_manager._evaluate_alert_condition(rule, metrics_data)
        
        assert result['triggered'] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])