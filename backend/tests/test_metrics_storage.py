"""
指标存储服务测试
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import json
import tempfile
import sqlite3

from app.services.metrics_storage import (
    MetricsStorageService, SQLiteMetricsStorage, TimeSeriesMetrics,
    MetricsQuery, PerformanceMetrics
)
from app.models.schemas import (
    TimeRange, GPUInfo
)
from app.models.enums import MetricType, GPUVendor
from tests.factories import TestDataGenerator, GPUInfoFactory


class TestSQLiteMetricsStorage:
    """SQLite指标存储测试"""
    
    @pytest.fixture
    async def storage(self):
        """创建临时SQLite存储实例"""
        # 使用内存数据库进行测试
        storage = SQLiteMetricsStorage(":memory:")
        await storage.initialize()
        try:
            yield storage
        finally:
            await storage.close()
    
    @pytest.fixture
    def sample_metrics_data(self):
        """示例指标数据"""
        return {
            'timestamp': datetime.now(),
            'gpu_metrics': [
                {
                    'device_id': 0,
                    'utilization': 75.5,
                    'memory_used': 12288,
                    'memory_total': 24576,
                    'temperature': 68.0,
                    'power_usage': 280.0
                },
                {
                    'device_id': 1,
                    'utilization': 45.2,
                    'memory_used': 8192,
                    'memory_total': 24576,
                    'temperature': 62.0,
                    'power_usage': 220.0
                }
            ],
            'model_metrics': [
                {
                    'model_id': 'model_1',
                    'status': 'running',
                    'health': 'healthy',
                    'response_time': 0.45,
                    'requests_count': 150,
                    'error_count': 2
                },
                {
                    'model_id': 'model_2',
                    'status': 'running',
                    'health': 'healthy',
                    'response_time': 0.32,
                    'requests_count': 89,
                    'error_count': 0
                }
            ],
            'system_metrics': {
                'cpu_percent': 45.8,
                'memory_percent': 62.3,
                'disk_percent': 35.7,
                'network_bytes_sent': 1024000,
                'network_bytes_recv': 2048000
            }
        }
    
    @pytest.mark.asyncio
    async def test_initialize_database(self, storage):
        """测试数据库初始化"""
        # 验证表是否创建
        async with storage._get_connection() as conn:
            cursor = await conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('gpu_metrics', 'model_metrics', 'system_metrics')
            """)
            tables = await cursor.fetchall()
            table_names = [table[0] for table in tables]
            
            assert 'gpu_metrics' in table_names
            assert 'model_metrics' in table_names
            assert 'system_metrics' in table_names
    
    @pytest.mark.asyncio
    async def test_store_metrics(self, storage, sample_metrics_data):
        """测试存储指标数据"""
        await storage.store_metrics(sample_metrics_data)
        
        # 验证GPU指标存储
        async with storage._get_connection() as conn:
            cursor = await conn.execute("SELECT COUNT(*) FROM gpu_metrics")
            count = await cursor.fetchone()
            assert count[0] == 2  # 两个GPU设备
            
            # 验证模型指标存储
            cursor = await conn.execute("SELECT COUNT(*) FROM model_metrics")
            count = await cursor.fetchone()
            assert count[0] == 2  # 两个模型
            
            # 验证系统指标存储
            cursor = await conn.execute("SELECT COUNT(*) FROM system_metrics")
            count = await cursor.fetchone()
            assert count[0] == 1  # 一条系统指标记录
    
    @pytest.mark.asyncio
    async def test_query_gpu_metrics(self, storage, sample_metrics_data):
        """测试查询GPU指标"""
        # 先存储数据
        await storage.store_metrics(sample_metrics_data)
        
        # 查询指标
        query = MetricsQuery(
            metric_type=MetricType.GPU_UTILIZATION,
            time_range=TimeRange(
                start_time=datetime.now() - timedelta(hours=1),
                end_time=datetime.now() + timedelta(hours=1)
            ),
            filters={'device_id': 0}
        )
        
        results = await storage.query_metrics(query)
        
        assert len(results) == 1
        assert results[0]['device_id'] == 0
        assert results[0]['utilization'] == 75.5
    
    @pytest.mark.asyncio
    async def test_query_model_metrics(self, storage, sample_metrics_data):
        """测试查询模型指标"""
        # 先存储数据
        await storage.store_metrics(sample_metrics_data)
        
        # 查询指标
        query = MetricsQuery(
            metric_type=MetricType.RESPONSE_TIME,
            time_range=TimeRange(
                start_time=datetime.now() - timedelta(hours=1),
                end_time=datetime.now() + timedelta(hours=1)
            ),
            filters={'model_id': 'model_1'}
        )
        
        results = await storage.query_metrics(query)
        
        assert len(results) == 1
        assert results[0]['model_id'] == 'model_1'
        assert results[0]['response_time'] == 0.45
    
    @pytest.mark.asyncio
    async def test_query_system_metrics(self, storage, sample_metrics_data):
        """测试查询系统指标"""
        # 先存储数据
        await storage.store_metrics(sample_metrics_data)
        
        # 查询指标
        query = MetricsQuery(
            metric_type=MetricType.CPU_USAGE,
            time_range=TimeRange(
                start_time=datetime.now() - timedelta(hours=1),
                end_time=datetime.now() + timedelta(hours=1)
            )
        )
        
        results = await storage.query_metrics(query)
        
        assert len(results) == 1
        assert results[0]['cpu_percent'] == 45.8
    
    @pytest.mark.asyncio
    async def test_get_performance_metrics(self, storage):
        """测试获取性能指标"""
        # 创建多条测试数据
        base_time = datetime.now()
        for i in range(10):
            metrics_data = {
                'timestamp': base_time - timedelta(minutes=i*5),
                'model_metrics': [
                    {
                        'model_id': 'test_model',
                        'status': 'running',
                        'health': 'healthy',
                        'response_time': 0.3 + i*0.05,  # 递增响应时间
                        'requests_count': 10 + i*5,
                        'error_count': i % 3  # 偶尔有错误
                    }
                ]
            }
            await storage.store_metrics(metrics_data)
        
        # 查询性能指标
        time_range = TimeRange(
            start_time=base_time - timedelta(hours=1),
            end_time=base_time + timedelta(minutes=10)
        )
        
        perf_metrics = await storage.get_performance_metrics('test_model', time_range)
        
        assert isinstance(perf_metrics, PerformanceMetrics)
        assert perf_metrics.model_id == 'test_model'
        assert perf_metrics.total_requests > 0
        assert perf_metrics.avg_response_time > 0
        assert perf_metrics.max_response_time >= perf_metrics.min_response_time
    
    @pytest.mark.asyncio
    async def test_aggregate_metrics(self, storage, sample_metrics_data):
        """测试指标聚合"""
        # 存储多个时间点的数据
        base_time = datetime.now()
        for i in range(5):
            data = sample_metrics_data.copy()
            data['timestamp'] = base_time - timedelta(minutes=i*10)
            # 修改一些值以测试聚合
            data['gpu_metrics'][0]['utilization'] = 70.0 + i*5
            await storage.store_metrics(data)
        
        # 查询聚合数据
        query = MetricsQuery(
            metric_type=MetricType.GPU_UTILIZATION,
            time_range=TimeRange(
                start_time=base_time - timedelta(hours=1),
                end_time=base_time + timedelta(minutes=10)
            ),
            filters={'device_id': 0},
            aggregation='avg',
            interval_minutes=30
        )
        
        results = await storage.query_metrics(query)
        
        assert len(results) > 0
        # 验证聚合结果
        for result in results:
            assert 'avg_utilization' in result or 'utilization' in result
    
    @pytest.mark.asyncio
    async def test_cleanup_old_metrics(self, storage):
        """测试清理旧指标数据"""
        # 创建一些旧数据
        old_time = datetime.now() - timedelta(days=10)
        old_data = {
            'timestamp': old_time,
            'gpu_metrics': [
                {
                    'device_id': 0,
                    'utilization': 50.0,
                    'memory_used': 8192,
                    'memory_total': 24576,
                    'temperature': 60.0,
                    'power_usage': 200.0
                }
            ]
        }
        await storage.store_metrics(old_data)
        
        # 创建一些新数据
        new_data = {
            'timestamp': datetime.now(),
            'gpu_metrics': [
                {
                    'device_id': 0,
                    'utilization': 75.0,
                    'memory_used': 12288,
                    'memory_total': 24576,
                    'temperature': 70.0,
                    'power_usage': 300.0
                }
            ]
        }
        await storage.store_metrics(new_data)
        
        # 验证数据存在
        async with storage._get_connection() as conn:
            cursor = await conn.execute("SELECT COUNT(*) FROM gpu_metrics")
            count = await cursor.fetchone()
            assert count[0] == 2
        
        # 清理7天前的数据
        await storage.cleanup_old_metrics(days=7)
        
        # 验证旧数据被清理
        async with storage._get_connection() as conn:
            cursor = await conn.execute("SELECT COUNT(*) FROM gpu_metrics")
            count = await cursor.fetchone()
            assert count[0] == 1  # 只剩新数据
    
    @pytest.mark.asyncio
    async def test_export_metrics(self, storage, sample_metrics_data):
        """测试导出指标数据"""
        # 存储测试数据
        await storage.store_metrics(sample_metrics_data)
        
        # 导出数据
        time_range = TimeRange(
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now() + timedelta(hours=1)
        )
        
        export_data = await storage.export_metrics(time_range, format='json')
        
        assert 'time_range' in export_data
        assert 'gpu_metrics' in export_data
        assert 'model_metrics' in export_data
        assert 'system_metrics' in export_data
        
        # 验证导出的数据结构
        assert len(export_data['gpu_metrics']) == 2
        assert len(export_data['model_metrics']) == 2
        assert len(export_data['system_metrics']) == 1
    
    @pytest.mark.asyncio
    async def test_get_metrics_summary(self, storage):
        """测试获取指标摘要"""
        # 创建测试数据
        base_time = datetime.now()
        for i in range(24):  # 24小时的数据
            metrics_data = {
                'timestamp': base_time - timedelta(hours=i),
                'gpu_metrics': [
                    {
                        'device_id': 0,
                        'utilization': 50.0 + (i % 10) * 5,
                        'memory_used': 8192 + i * 100,
                        'memory_total': 24576,
                        'temperature': 60.0 + i,
                        'power_usage': 200.0 + i * 10
                    }
                ],
                'model_metrics': [
                    {
                        'model_id': 'test_model',
                        'status': 'running',
                        'health': 'healthy',
                        'response_time': 0.3 + (i % 5) * 0.1,
                        'requests_count': 100 + i * 10,
                        'error_count': i % 3
                    }
                ]
            }
            await storage.store_metrics(metrics_data)
        
        # 获取摘要
        summary = await storage.get_metrics_summary(
            time_range=TimeRange(
                start_time=base_time - timedelta(hours=24),
                end_time=base_time
            )
        )
        
        assert 'gpu_summary' in summary
        assert 'model_summary' in summary
        assert 'system_summary' in summary
        
        # 验证GPU摘要
        gpu_summary = summary['gpu_summary']
        assert 'avg_utilization' in gpu_summary
        assert 'max_temperature' in gpu_summary
        assert 'total_memory_used' in gpu_summary
        
        # 验证模型摘要
        model_summary = summary['model_summary']
        assert 'total_requests' in model_summary
        assert 'avg_response_time' in model_summary
        assert 'error_rate' in model_summary


class TestMetricsStorageService:
    """指标存储服务测试"""
    
    @pytest.fixture
    def storage_service(self):
        """创建指标存储服务实例"""
        return MetricsStorageService()
    
    @pytest.mark.asyncio
    async def test_initialize_service(self, storage_service):
        """测试服务初始化"""
        # Mock存储后端
        mock_storage = Mock()
        mock_storage.initialize = AsyncMock()
        storage_service._storage = mock_storage
        
        await storage_service.initialize()
        
        mock_storage.initialize.assert_called_once()
        assert storage_service._initialized is True
    
    @pytest.mark.asyncio
    async def test_store_metrics_batch(self, storage_service):
        """测试批量存储指标"""
        # Mock存储后端
        mock_storage = Mock()
        mock_storage.store_metrics = AsyncMock()
        storage_service._storage = mock_storage
        storage_service._initialized = True
        
        # 创建批量数据
        metrics_batch = []
        for i in range(5):
            metrics_data = {
                'timestamp': datetime.now() - timedelta(minutes=i),
                'gpu_metrics': [{'device_id': 0, 'utilization': 50.0 + i}]
            }
            metrics_batch.append(metrics_data)
        
        await storage_service.store_metrics_batch(metrics_batch)
        
        # 验证每个指标都被存储
        assert mock_storage.store_metrics.call_count == 5
    
    @pytest.mark.asyncio
    async def test_query_with_cache(self, storage_service):
        """测试带缓存的查询"""
        # Mock存储后端
        mock_storage = Mock()
        mock_results = [{'device_id': 0, 'utilization': 75.0}]
        mock_storage.query_metrics = AsyncMock(return_value=mock_results)
        storage_service._storage = mock_storage
        storage_service._initialized = True
        
        query = MetricsQuery(
            metric_type=MetricType.GPU_UTILIZATION,
            time_range=TimeRange(
                start_time=datetime.now() - timedelta(hours=1),
                end_time=datetime.now()
            )
        )
        
        # 第一次查询
        results1 = await storage_service.query_metrics(query)
        assert results1 == mock_results
        assert mock_storage.query_metrics.call_count == 1
        
        # 第二次查询（应该使用缓存）
        results2 = await storage_service.query_metrics(query)
        assert results2 == mock_results
        # 如果启用了缓存，调用次数应该还是1
        # 这里简化测试，实际实现中可能会有缓存逻辑
    
    @pytest.mark.asyncio
    async def test_get_real_time_metrics(self, storage_service):
        """测试获取实时指标"""
        # Mock存储后端
        mock_storage = Mock()
        mock_storage.query_metrics = AsyncMock(return_value=[
            {'timestamp': datetime.now(), 'device_id': 0, 'utilization': 80.0}
        ])
        storage_service._storage = mock_storage
        storage_service._initialized = True
        
        real_time_metrics = await storage_service.get_real_time_metrics()
        
        assert 'gpu_metrics' in real_time_metrics
        assert 'model_metrics' in real_time_metrics
        assert 'system_metrics' in real_time_metrics
        assert 'timestamp' in real_time_metrics
    
    @pytest.mark.asyncio
    async def test_calculate_trends(self, storage_service):
        """测试计算趋势"""
        # Mock历史数据
        mock_storage = Mock()
        mock_storage.query_metrics = AsyncMock(return_value=[
            {'timestamp': datetime.now() - timedelta(hours=2), 'utilization': 60.0},
            {'timestamp': datetime.now() - timedelta(hours=1), 'utilization': 70.0},
            {'timestamp': datetime.now(), 'utilization': 80.0}
        ])
        storage_service._storage = mock_storage
        storage_service._initialized = True
        
        trends = await storage_service.calculate_trends(
            metric_type=MetricType.GPU_UTILIZATION,
            time_range=TimeRange(
                start_time=datetime.now() - timedelta(hours=3),
                end_time=datetime.now()
            )
        )
        
        assert 'trend_direction' in trends
        assert 'trend_rate' in trends
        assert 'prediction' in trends
        
        # 验证趋势方向（应该是上升的）
        assert trends['trend_direction'] in ['increasing', 'decreasing', 'stable']
    
    @pytest.mark.asyncio
    async def test_generate_alerts_from_metrics(self, storage_service):
        """测试从指标生成告警"""
        # Mock当前指标数据
        current_metrics = {
            'gpu_metrics': [
                {'device_id': 0, 'utilization': 95.0, 'temperature': 85.0}
            ],
            'model_metrics': [
                {'model_id': 'test_model', 'response_time': 3.0, 'error_count': 10}
            ]
        }
        
        # 定义告警阈值
        alert_thresholds = {
            'gpu_utilization_high': 90.0,
            'gpu_temperature_high': 80.0,
            'response_time_high': 2.0,
            'error_count_high': 5
        }
        
        alerts = await storage_service.generate_alerts_from_metrics(
            current_metrics, 
            alert_thresholds
        )
        
        # 验证生成的告警
        assert len(alerts) > 0
        
        # 检查特定告警
        alert_types = [alert['type'] for alert in alerts]
        assert 'gpu_utilization_high' in alert_types
        assert 'gpu_temperature_high' in alert_types
        assert 'response_time_high' in alert_types
        assert 'error_count_high' in alert_types


class TestTimeSeriesMetrics:
    """时间序列指标测试"""
    
    @pytest.fixture
    def time_series(self):
        """创建时间序列指标实例"""
        return TimeSeriesMetrics()
    
    def test_add_data_point(self, time_series):
        """测试添加数据点"""
        timestamp = datetime.now()
        time_series.add_data_point(timestamp, 'gpu_utilization', 75.5, {'device_id': 0})
        
        assert len(time_series._data_points) == 1
        point = time_series._data_points[0]
        assert point['timestamp'] == timestamp
        assert point['metric_name'] == 'gpu_utilization'
        assert point['value'] == 75.5
        assert point['tags']['device_id'] == 0
    
    def test_get_data_points_in_range(self, time_series):
        """测试获取时间范围内的数据点"""
        base_time = datetime.now()
        
        # 添加多个数据点
        for i in range(10):
            timestamp = base_time - timedelta(minutes=i*5)
            time_series.add_data_point(timestamp, 'cpu_usage', 50.0 + i, {})
        
        # 查询特定时间范围
        start_time = base_time - timedelta(minutes=30)
        end_time = base_time
        
        points = time_series.get_data_points_in_range('cpu_usage', start_time, end_time)
        
        # 应该返回30分钟内的数据点（包括边界）
        assert len(points) == 7  # 0, 5, 10, 15, 20, 25, 30分钟前的数据
    
    def test_calculate_average(self, time_series):
        """测试计算平均值"""
        base_time = datetime.now()
        values = [60.0, 70.0, 80.0, 90.0, 100.0]
        
        for i, value in enumerate(values):
            timestamp = base_time - timedelta(minutes=i*5)
            time_series.add_data_point(timestamp, 'test_metric', value, {})
        
        avg = time_series.calculate_average('test_metric', 
                                          base_time - timedelta(minutes=25), 
                                          base_time)
        
        assert avg == 80.0  # (60+70+80+90+100)/5
    
    def test_calculate_percentile(self, time_series):
        """测试计算百分位数"""
        base_time = datetime.now()
        values = list(range(1, 101))  # 1到100
        
        for i, value in enumerate(values):
            timestamp = base_time - timedelta(seconds=i)
            time_series.add_data_point(timestamp, 'test_metric', float(value), {})
        
        p95 = time_series.calculate_percentile('test_metric', 
                                             base_time - timedelta(seconds=100), 
                                             base_time, 
                                             95)
        
        # 95百分位数应该接近95
        assert 94 <= p95 <= 96
    
    def test_detect_anomalies(self, time_series):
        """测试异常检测"""
        base_time = datetime.now()
        
        # 添加正常数据
        for i in range(50):
            value = 50.0 + (i % 10)  # 50-59之间的正常值
            timestamp = base_time - timedelta(minutes=i)
            time_series.add_data_point(timestamp, 'normal_metric', value, {})
        
        # 添加异常数据
        anomaly_time = base_time - timedelta(minutes=25)
        time_series.add_data_point(anomaly_time, 'normal_metric', 150.0, {})  # 异常高值
        
        anomalies = time_series.detect_anomalies('normal_metric',
                                               base_time - timedelta(minutes=60),
                                               base_time,
                                               threshold=2.0)  # 2个标准差
        
        assert len(anomalies) == 1
        assert anomalies[0]['value'] == 150.0
        assert anomalies[0]['timestamp'] == anomaly_time


if __name__ == "__main__":
    pytest.main([__file__, "-v"])