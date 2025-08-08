"""
性能基准测试套件
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
import statistics
from concurrent.futures import ThreadPoolExecutor
import tempfile
import shutil

from app.services.model_manager import ModelManager
from app.services.resource_scheduler import PriorityResourceScheduler
from app.services.config_manager import FileConfigManager
from app.services.monitoring import MonitoringService
from tests.factories import TestDataGenerator


@pytest.mark.benchmark
class TestPerformanceBenchmarks:
    """性能基准测试"""
    
    @pytest.fixture
    async def temp_config_dir(self):
        """创建临时配置目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    async def config_manager(self, temp_config_dir):
        """创建配置管理器"""
        return FileConfigManager(temp_config_dir)
    
    @pytest.fixture
    async def model_manager(self, config_manager):
        """创建模型管理器"""
        manager = ModelManager(config_manager)
        await manager.initialize()
        yield manager
        await manager.shutdown()
    
    @pytest.fixture
    async def scheduler(self):
        """创建资源调度器"""
        scheduler = PriorityResourceScheduler()
        yield scheduler
        await scheduler.shutdown()
    
    @pytest.fixture
    async def monitoring_service(self):
        """创建监控服务"""
        service = MonitoringService()
        yield service
        await service.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_model_creation_performance(self, benchmark, model_manager):
        """测试模型创建性能"""
        model_configs = TestDataGenerator.create_model_configs(100)
        
        async def create_models():
            tasks = []
            for config in model_configs:
                task = model_manager.create_model(config)
                tasks.append(task)
            
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            successful_creates = [r for r in results if not isinstance(r, Exception)]
            return {
                'total_time': end_time - start_time,
                'successful_creates': len(successful_creates),
                'total_models': len(model_configs),
                'avg_time_per_model': (end_time - start_time) / len(model_configs)
            }
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True):
            
            result = benchmark(lambda: asyncio.run(create_models()))
            
            # 性能断言
            assert result['successful_creates'] == result['total_models']
            assert result['avg_time_per_model'] < 0.1  # 每个模型创建应少于100ms
            assert result['total_time'] < 10.0  # 总时间应少于10秒
    
    @pytest.mark.asyncio
    async def test_concurrent_model_operations_performance(self, benchmark, model_manager):
        """测试并发模型操作性能"""
        model_configs = TestDataGenerator.create_model_configs(50)
        
        # 先创建所有模型
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True):
            
            for config in model_configs:
                await model_manager.create_model(config)
        
        async def concurrent_operations():
            start_time = time.time()
            
            # 并发执行不同操作
            tasks = []
            
            # 启动操作
            with patch('app.adapters.base.BaseFrameworkAdapter._do_start_model', return_value=True):
                for i in range(0, len(model_configs), 3):
                    task = model_manager.start_model(model_configs[i].id)
                    tasks.append(task)
            
            # 状态查询操作
            for config in model_configs:
                task = model_manager.get_model_status(config.id)
                tasks.append(task)
            
            # 列表操作
            for _ in range(10):
                task = model_manager.list_models()
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            exceptions = [r for r in results if isinstance(r, Exception)]
            return {
                'total_time': end_time - start_time,
                'total_operations': len(tasks),
                'exceptions': len(exceptions),
                'ops_per_second': len(tasks) / (end_time - start_time)
            }
        
        result = benchmark(lambda: asyncio.run(concurrent_operations()))
        
        # 性能断言
        assert result['exceptions'] == 0
        assert result['ops_per_second'] > 100  # 每秒应处理超过100个操作
        assert result['total_time'] < 5.0  # 总时间应少于5秒
    
    @pytest.mark.asyncio
    async def test_resource_scheduling_performance(self, benchmark, scheduler):
        """测试资源调度性能"""
        # 创建大量模型用于调度测试
        performance_data = TestDataGenerator.create_performance_test_data(100)
        models = performance_data['models']
        gpus = performance_data['gpus']
        
        # 注册所有模型
        for model in models:
            scheduler.register_model(model)
        
        async def scheduling_benchmark():
            start_time = time.time()
            
            with patch('app.utils.gpu.get_gpu_info', return_value=gpus), \
                 patch('app.services.resource_scheduler.resource_calculator') as mock_calc:
                
                # Mock资源计算
                mock_calc.calculate_model_memory_requirement.return_value = Mock(
                    gpu_memory=4096,
                    gpu_devices=[0]
                )
                mock_calc.validate_resource_allocation.return_value = (True, [], Mock())
                
                # 并发调度所有模型
                tasks = []
                for model in models:
                    task = scheduler.schedule_model(model.id)
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                end_time = time.time()
                
                successful_schedules = [r for r in results if not isinstance(r, Exception)]
                return {
                    'total_time': end_time - start_time,
                    'successful_schedules': len(successful_schedules),
                    'total_models': len(models),
                    'schedules_per_second': len(models) / (end_time - start_time)
                }
        
        result = benchmark(lambda: asyncio.run(scheduling_benchmark()))
        
        # 性能断言
        assert result['successful_schedules'] > 0
        assert result['schedules_per_second'] > 10  # 每秒应调度超过10个模型
        assert result['total_time'] < 30.0  # 总时间应少于30秒
    
    @pytest.mark.asyncio
    async def test_monitoring_data_collection_performance(self, benchmark, monitoring_service):
        """测试监控数据收集性能"""
        async def monitoring_benchmark():
            start_time = time.time()
            
            with patch('app.utils.gpu.get_gpu_info') as mock_gpu, \
                 patch('psutil.cpu_percent', return_value=50.0), \
                 patch('psutil.virtual_memory') as mock_memory, \
                 patch('psutil.disk_usage') as mock_disk:
                
                # Mock监控数据
                mock_gpu.return_value = TestDataGenerator.create_gpu_cluster(8)
                mock_memory.return_value = Mock(total=32*1024**3, used=16*1024**3, percent=50.0)
                mock_disk.return_value = Mock(total=1024*1024**3, used=512*1024**3, percent=50.0)
                
                # 并发收集多次监控数据
                tasks = []
                for _ in range(100):
                    tasks.extend([
                        monitoring_service.collect_gpu_metrics(),
                        monitoring_service.collect_system_metrics()
                    ])
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                end_time = time.time()
                
                exceptions = [r for r in results if isinstance(r, Exception)]
                return {
                    'total_time': end_time - start_time,
                    'total_collections': len(tasks),
                    'exceptions': len(exceptions),
                    'collections_per_second': len(tasks) / (end_time - start_time)
                }
        
        result = benchmark(lambda: asyncio.run(monitoring_benchmark()))
        
        # 性能断言
        assert result['exceptions'] == 0
        assert result['collections_per_second'] > 50  # 每秒应收集超过50次
        assert result['total_time'] < 10.0  # 总时间应少于10秒
    
    def test_memory_usage_benchmark(self, benchmark):
        """测试内存使用基准"""
        import psutil
        import gc
        
        def memory_benchmark():
            process = psutil.Process()
            initial_memory = process.memory_info().rss
            
            # 创建大量对象
            models = TestDataGenerator.create_model_configs(1000)
            gpu_clusters = [TestDataGenerator.create_gpu_cluster(4) for _ in range(100)]
            
            peak_memory = process.memory_info().rss
            
            # 清理对象
            del models
            del gpu_clusters
            gc.collect()
            
            final_memory = process.memory_info().rss
            
            return {
                'initial_memory_mb': initial_memory / 1024 / 1024,
                'peak_memory_mb': peak_memory / 1024 / 1024,
                'final_memory_mb': final_memory / 1024 / 1024,
                'memory_increase_mb': (peak_memory - initial_memory) / 1024 / 1024,
                'memory_leaked_mb': (final_memory - initial_memory) / 1024 / 1024
            }
        
        result = benchmark(memory_benchmark)
        
        # 内存使用断言
        assert result['memory_increase_mb'] < 500  # 内存增长应少于500MB
        assert result['memory_leaked_mb'] < 50   # 内存泄漏应少于50MB
    
    @pytest.mark.asyncio
    async def test_database_operations_performance(self, benchmark, config_manager):
        """测试数据库操作性能"""
        model_configs = TestDataGenerator.create_model_configs(500)
        
        async def database_benchmark():
            start_time = time.time()
            
            # 批量保存配置
            save_tasks = []
            for config in model_configs:
                task = config_manager.save_model_config(config)
                save_tasks.append(task)
            
            await asyncio.gather(*save_tasks)
            
            # 批量加载配置
            load_tasks = []
            for _ in range(10):  # 多次加载测试
                task = config_manager.load_model_configs()
                load_tasks.append(task)
            
            load_results = await asyncio.gather(*load_tasks)
            
            end_time = time.time()
            
            return {
                'total_time': end_time - start_time,
                'configs_saved': len(model_configs),
                'load_operations': len(load_tasks),
                'configs_per_second': len(model_configs) / (end_time - start_time),
                'loaded_configs_count': len(load_results[0]) if load_results else 0
            }
        
        result = benchmark(lambda: asyncio.run(database_benchmark()))
        
        # 数据库性能断言
        assert result['configs_per_second'] > 50  # 每秒应处理超过50个配置
        assert result['loaded_configs_count'] == len(model_configs)
        assert result['total_time'] < 20.0  # 总时间应少于20秒
    
    def test_cpu_intensive_operations_benchmark(self, benchmark):
        """测试CPU密集型操作基准"""
        def cpu_benchmark():
            start_time = time.time()
            
            # 模拟CPU密集型任务
            results = []
            
            # 资源需求计算
            for _ in range(1000):
                model_config = TestDataGenerator.create_model_configs(1)[0]
                # 模拟复杂的资源计算
                memory_requirement = model_config.priority * 1024 + len(model_config.parameters) * 512
                gpu_requirement = len(model_config.gpu_devices) * 2048
                total_requirement = memory_requirement + gpu_requirement
                results.append(total_requirement)
            
            # 优先级排序
            models = TestDataGenerator.create_model_configs(1000)
            sorted_models = sorted(models, key=lambda m: m.priority, reverse=True)
            
            # 统计计算
            priorities = [m.priority for m in sorted_models]
            avg_priority = statistics.mean(priorities)
            median_priority = statistics.median(priorities)
            
            end_time = time.time()
            
            return {
                'total_time': end_time - start_time,
                'calculations_performed': len(results),
                'models_sorted': len(sorted_models),
                'avg_priority': avg_priority,
                'median_priority': median_priority,
                'calculations_per_second': len(results) / (end_time - start_time)
            }
        
        result = benchmark(cpu_benchmark)
        
        # CPU性能断言
        assert result['calculations_per_second'] > 1000  # 每秒应执行超过1000次计算
        assert result['total_time'] < 5.0  # 总时间应少于5秒
    
    @pytest.mark.asyncio
    async def test_stress_test_concurrent_users(self, benchmark, model_manager):
        """测试并发用户压力测试"""
        model_configs = TestDataGenerator.create_model_configs(20)
        
        # 先创建模型
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True):
            
            for config in model_configs:
                await model_manager.create_model(config)
        
        async def simulate_user_session():
            """模拟用户会话"""
            operations = []
            
            # 随机执行各种操作
            import random
            for _ in range(10):
                operation_type = random.choice(['list', 'get', 'status', 'start', 'stop'])
                model_id = random.choice(model_configs).id
                
                try:
                    if operation_type == 'list':
                        result = await model_manager.list_models()
                    elif operation_type == 'get':
                        result = await model_manager.get_model_config(model_id)
                    elif operation_type == 'status':
                        result = await model_manager.get_model_status(model_id)
                    elif operation_type == 'start':
                        with patch('app.adapters.base.BaseFrameworkAdapter._do_start_model', return_value=True):
                            result = await model_manager.start_model(model_id)
                    elif operation_type == 'stop':
                        with patch('app.adapters.base.BaseFrameworkAdapter._do_stop_model', return_value=True):
                            result = await model_manager.stop_model(model_id)
                    
                    operations.append((operation_type, True))
                except Exception:
                    operations.append((operation_type, False))
            
            return operations
        
        async def stress_test():
            start_time = time.time()
            
            # 模拟100个并发用户
            user_tasks = []
            for _ in range(100):
                task = simulate_user_session()
                user_tasks.append(task)
            
            user_results = await asyncio.gather(*user_tasks, return_exceptions=True)
            
            end_time = time.time()
            
            # 统计结果
            total_operations = 0
            successful_operations = 0
            
            for user_result in user_results:
                if not isinstance(user_result, Exception):
                    for operation, success in user_result:
                        total_operations += 1
                        if success:
                            successful_operations += 1
            
            return {
                'total_time': end_time - start_time,
                'concurrent_users': 100,
                'total_operations': total_operations,
                'successful_operations': successful_operations,
                'success_rate': successful_operations / total_operations if total_operations > 0 else 0,
                'operations_per_second': total_operations / (end_time - start_time)
            }
        
        result = benchmark(lambda: asyncio.run(stress_test()))
        
        # 压力测试断言
        assert result['success_rate'] > 0.95  # 成功率应超过95%
        assert result['operations_per_second'] > 100  # 每秒应处理超过100个操作
        assert result['total_time'] < 60.0  # 总时间应少于60秒
    
    def test_latency_benchmark(self, benchmark):
        """测试延迟基准测试"""
        def latency_benchmark():
            latencies = []
            
            # 测试多次操作的延迟
            for _ in range(1000):
                start = time.perf_counter()
                
                # 模拟快速操作
                model_config = TestDataGenerator.create_model_configs(1)[0]
                _ = model_config.id
                _ = model_config.priority
                _ = len(model_config.parameters)
                
                end = time.perf_counter()
                latencies.append((end - start) * 1000)  # 转换为毫秒
            
            return {
                'min_latency_ms': min(latencies),
                'max_latency_ms': max(latencies),
                'avg_latency_ms': statistics.mean(latencies),
                'median_latency_ms': statistics.median(latencies),
                'p95_latency_ms': sorted(latencies)[int(len(latencies) * 0.95)],
                'p99_latency_ms': sorted(latencies)[int(len(latencies) * 0.99)]
            }
        
        result = benchmark(latency_benchmark)
        
        # 延迟断言
        assert result['avg_latency_ms'] < 1.0  # 平均延迟应少于1ms
        assert result['p95_latency_ms'] < 5.0  # 95%的请求应少于5ms
        assert result['p99_latency_ms'] < 10.0  # 99%的请求应少于10ms


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "benchmark"])