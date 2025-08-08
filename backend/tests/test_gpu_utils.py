"""
GPU工具模块测试
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from app.utils.gpu import GPUDetector, GPUMonitor, gpu_detector, gpu_monitor
from app.models.schemas import GPUInfo, GPUMetrics
from app.models.enums import GPUVendor


class TestGPUDetector:
    """GPU检测器测试"""
    
    @pytest.fixture
    def detector(self):
        """创建GPU检测器实例"""
        return GPUDetector()
    
    @pytest.mark.asyncio
    async def test_detect_gpus_with_cache(self, detector):
        """测试GPU检测缓存功能"""
        # 模拟GPU信息
        mock_gpu = GPUInfo(
            device_id=0,
            name="Test GPU",
            vendor=GPUVendor.NVIDIA,
            memory_total=8192,
            memory_used=2048,
            memory_free=6144,
            utilization=50.0,
            temperature=65.0,
            power_usage=150.0,
            driver_version="525.60.11"
        )
        
        # 设置缓存
        detector._gpu_cache = {0: mock_gpu}
        detector._cache_expiry = datetime.now() + timedelta(minutes=1)
        
        # 测试使用缓存
        gpus = await detector.detect_gpus(use_cache=True)
        assert len(gpus) == 1
        assert gpus[0].device_id == 0
        assert gpus[0].name == "Test GPU"
    
    @pytest.mark.asyncio
    async def test_detect_gpus_without_cache(self, detector):
        """测试不使用缓存的GPU检测"""
        with patch.object(detector, '_detect_nvidia_gpus', return_value=[]) as mock_nvidia, \
             patch.object(detector, '_detect_amd_gpus', return_value=[]) as mock_amd:
            
            gpus = await detector.detect_gpus(use_cache=False)
            
            mock_nvidia.assert_called_once()
            mock_amd.assert_called_once()
            assert gpus == []
    
    @pytest.mark.asyncio
    async def test_detect_nvidia_gpus_success(self, detector):
        """测试NVIDIA GPU检测成功"""
        mock_handle = Mock()
        
        with patch('pynvml.nvmlInit') as mock_init, \
             patch('pynvml.nvmlDeviceGetCount', return_value=1) as mock_count, \
             patch('pynvml.nvmlDeviceGetHandleByIndex', return_value=mock_handle) as mock_handle_func, \
             patch.object(detector, '_get_nvidia_gpu_info') as mock_get_info:
            
            mock_gpu = GPUInfo(
                device_id=0,
                name="NVIDIA RTX 4090",
                vendor=GPUVendor.NVIDIA,
                memory_total=24576,
                memory_used=1024,
                memory_free=23552,
                utilization=25.0,
                temperature=45.0,
                power_usage=200.0,
                driver_version="525.60.11"
            )
            mock_get_info.return_value = mock_gpu
            
            gpus = await detector._detect_nvidia_gpus()
            
            assert len(gpus) == 1
            assert gpus[0].vendor == GPUVendor.NVIDIA
            assert gpus[0].name == "NVIDIA RTX 4090"
            mock_init.assert_called_once()
            mock_count.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_detect_nvidia_gpus_import_error(self, detector):
        """测试NVIDIA GPU检测导入错误"""
        with patch('pynvml.nvmlInit', side_effect=ImportError("pynvml not found")):
            gpus = await detector._detect_nvidia_gpus()
            assert gpus == []
    
    @pytest.mark.asyncio
    async def test_get_nvidia_gpu_info(self, detector):
        """测试获取NVIDIA GPU详细信息"""
        mock_handle = Mock()
        
        # 模拟pynvml函数返回值
        mock_mem_info = Mock()
        mock_mem_info.total = 24 * 1024 * 1024 * 1024  # 24GB
        mock_mem_info.used = 2 * 1024 * 1024 * 1024   # 2GB
        mock_mem_info.free = 22 * 1024 * 1024 * 1024  # 22GB
        
        mock_util = Mock()
        mock_util.gpu = 30.0
        
        with patch('pynvml.nvmlDeviceGetName', return_value=b'NVIDIA RTX 4090'), \
             patch('pynvml.nvmlDeviceGetMemoryInfo', return_value=mock_mem_info), \
             patch('pynvml.nvmlDeviceGetUtilizationRates', return_value=mock_util), \
             patch('pynvml.nvmlDeviceGetTemperature', return_value=55.0), \
             patch('pynvml.nvmlDeviceGetPowerUsage', return_value=250000), \
             patch('pynvml.nvmlSystemGetDriverVersion', return_value=b'525.60.11'):
            
            gpu_info = await detector._get_nvidia_gpu_info(mock_handle, 0)
            
            assert gpu_info is not None
            assert gpu_info.device_id == 0
            assert gpu_info.name == "NVIDIA RTX 4090"
            assert gpu_info.vendor == GPUVendor.NVIDIA
            assert gpu_info.memory_total == 24576  # MB
            assert gpu_info.memory_used == 2048    # MB
            assert gpu_info.memory_free == 22528   # MB
            assert gpu_info.utilization == 30.0
            assert gpu_info.temperature == 55.0
            assert gpu_info.power_usage == 250.0
            assert gpu_info.driver_version == "525.60.11"
    
    @pytest.mark.asyncio
    async def test_detect_amd_gpus_rocm_smi_available(self, detector):
        """测试AMD GPU检测 - rocm-smi可用"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = '{"card0": {"Product Name": "AMD RX 7900 XTX"}}'
        
        with patch.object(detector, '_run_command', return_value=mock_result) as mock_run, \
             patch.object(detector, '_parse_amd_rocm_info') as mock_parse:
            
            mock_gpu = GPUInfo(
                device_id=0,
                name="AMD RX 7900 XTX",
                vendor=GPUVendor.AMD,
                memory_total=24576,
                memory_used=1024,
                memory_free=23552,
                utilization=20.0,
                temperature=60.0,
                power_usage=300.0,
                driver_version=None
            )
            mock_parse.return_value = mock_gpu
            
            gpus = await detector._detect_amd_gpus()
            
            assert len(gpus) == 1
            assert gpus[0].vendor == GPUVendor.AMD
            assert gpus[0].name == "AMD RX 7900 XTX"
    
    @pytest.mark.asyncio
    async def test_detect_amd_gpus_rocm_smi_unavailable(self, detector):
        """测试AMD GPU检测 - rocm-smi不可用，使用sysfs"""
        mock_result = Mock()
        mock_result.returncode = 1  # rocm-smi不可用
        
        with patch.object(detector, '_run_command', return_value=mock_result), \
             patch.object(detector, '_detect_amd_sysfs', return_value=[]) as mock_sysfs:
            
            gpus = await detector._detect_amd_gpus()
            
            mock_sysfs.assert_called_once()
            assert gpus == []
    
    @pytest.mark.asyncio
    async def test_run_command_success(self, detector):
        """测试命令执行成功"""
        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_process = Mock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b'output', b''))
            mock_exec.return_value = mock_process
            
            result = await detector._run_command(['echo', 'test'])
            
            assert result.returncode == 0
            assert result.stdout == 'output'
            assert result.stderr == ''
    
    @pytest.mark.asyncio
    async def test_run_command_timeout(self, detector):
        """测试命令执行超时"""
        with patch('asyncio.create_subprocess_exec') as mock_exec, \
             patch('asyncio.wait_for', side_effect=asyncio.TimeoutError()):
            
            mock_process = Mock()
            mock_exec.return_value = mock_process
            
            result = await detector._run_command(['sleep', '100'], timeout=1)
            
            assert result.returncode == -1
            assert result.stderr == 'timeout'
    
    @pytest.mark.asyncio
    async def test_get_gpu_info(self, detector):
        """测试获取指定GPU信息"""
        mock_gpu = GPUInfo(
            device_id=1,
            name="Test GPU",
            vendor=GPUVendor.NVIDIA,
            memory_total=8192,
            memory_used=2048,
            memory_free=6144,
            utilization=50.0,
            temperature=65.0,
            power_usage=150.0,
            driver_version="525.60.11"
        )
        
        with patch.object(detector, 'detect_gpus', return_value=[mock_gpu]):
            gpu_info = await detector.get_gpu_info(1)
            assert gpu_info is not None
            assert gpu_info.device_id == 1
            
            # 测试不存在的GPU
            gpu_info = await detector.get_gpu_info(999)
            assert gpu_info is None
    
    @pytest.mark.asyncio
    async def test_get_gpu_metrics(self, detector):
        """测试获取GPU指标"""
        mock_gpu = GPUInfo(
            device_id=0,
            name="Test GPU",
            vendor=GPUVendor.NVIDIA,
            memory_total=8192,
            memory_used=2048,
            memory_free=6144,
            utilization=50.0,
            temperature=65.0,
            power_usage=150.0,
            driver_version="525.60.11"
        )
        
        with patch.object(detector, 'get_gpu_info', return_value=mock_gpu):
            metrics = await detector.get_gpu_metrics(0)
            
            assert metrics is not None
            assert metrics.device_id == 0
            assert metrics.utilization == 50.0
            assert metrics.memory_used == 2048
            assert metrics.memory_total == 8192
            assert metrics.temperature == 65.0
            assert metrics.power_usage == 150.0
            assert isinstance(metrics.timestamp, datetime)
    
    @pytest.mark.asyncio
    async def test_get_all_gpu_metrics(self, detector):
        """测试获取所有GPU指标"""
        mock_gpus = [
            GPUInfo(
                device_id=0,
                name="GPU 0",
                vendor=GPUVendor.NVIDIA,
                memory_total=8192,
                memory_used=2048,
                memory_free=6144,
                utilization=50.0,
                temperature=65.0,
                power_usage=150.0,
                driver_version="525.60.11"
            ),
            GPUInfo(
                device_id=1,
                name="GPU 1",
                vendor=GPUVendor.AMD,
                memory_total=16384,
                memory_used=4096,
                memory_free=12288,
                utilization=30.0,
                temperature=55.0,
                power_usage=200.0,
                driver_version=None
            )
        ]
        
        with patch.object(detector, 'detect_gpus', return_value=mock_gpus):
            metrics = await detector.get_all_gpu_metrics()
            
            assert len(metrics) == 2
            assert metrics[0].device_id == 0
            assert metrics[1].device_id == 1
            assert all(isinstance(m.timestamp, datetime) for m in metrics)
    
    def test_clear_cache(self, detector):
        """测试清除缓存"""
        # 设置缓存
        detector._gpu_cache = {0: Mock()}
        detector._cache_expiry = datetime.now() + timedelta(minutes=1)
        
        detector.clear_cache()
        
        assert detector._gpu_cache == {}
        assert detector._cache_expiry is None


class TestGPUMonitor:
    """GPU监控器测试"""
    
    @pytest.fixture
    def detector(self):
        """创建模拟GPU检测器"""
        return Mock(spec=GPUDetector)
    
    @pytest.fixture
    def monitor(self, detector):
        """创建GPU监控器实例"""
        return GPUMonitor(detector, update_interval=1)
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, monitor):
        """测试启动和停止监控"""
        assert not monitor._monitoring
        
        # 启动监控
        await monitor.start_monitoring()
        assert monitor._monitoring
        assert monitor._monitor_task is not None
        
        # 停止监控
        await monitor.stop_monitoring()
        assert not monitor._monitoring
    
    @pytest.mark.asyncio
    async def test_start_monitoring_already_running(self, monitor):
        """测试重复启动监控"""
        monitor._monitoring = True
        
        await monitor.start_monitoring()
        # 应该不会创建新的任务
        assert monitor._monitor_task is None
    
    def test_add_remove_callback(self, monitor):
        """测试添加和移除回调函数"""
        callback1 = Mock()
        callback2 = Mock()
        
        # 添加回调
        monitor.add_callback(callback1)
        monitor.add_callback(callback2)
        assert len(monitor._callbacks) == 2
        
        # 移除回调
        monitor.remove_callback(callback1)
        assert len(monitor._callbacks) == 1
        assert callback2 in monitor._callbacks
        
        # 移除不存在的回调
        monitor.remove_callback(Mock())
        assert len(monitor._callbacks) == 1
    
    @pytest.mark.asyncio
    async def test_monitor_loop_with_callbacks(self, monitor, detector):
        """测试监控循环和回调执行"""
        # 模拟GPU指标
        mock_metrics = [
            GPUMetrics(
                device_id=0,
                timestamp=datetime.now(),
                utilization=50.0,
                memory_used=2048,
                memory_total=8192,
                temperature=65.0,
                power_usage=150.0
            )
        ]
        
        detector.get_all_gpu_metrics = AsyncMock(return_value=mock_metrics)
        
        # 添加同步和异步回调
        sync_callback = Mock()
        async_callback = AsyncMock()
        
        monitor.add_callback(sync_callback)
        monitor.add_callback(async_callback)
        
        # 启动监控并运行一小段时间
        await monitor.start_monitoring()
        await asyncio.sleep(1.5)  # 让监控循环运行至少一次
        await monitor.stop_monitoring()
        
        # 验证回调被调用
        sync_callback.assert_called()
        async_callback.assert_called()
        detector.get_all_gpu_metrics.assert_called()


class TestGlobalInstances:
    """测试全局实例"""
    
    def test_global_gpu_detector(self):
        """测试全局GPU检测器实例"""
        assert gpu_detector is not None
        assert isinstance(gpu_detector, GPUDetector)
    
    def test_global_gpu_monitor(self):
        """测试全局GPU监控器实例"""
        assert gpu_monitor is not None
        assert isinstance(gpu_monitor, GPUMonitor)
        assert gpu_monitor.detector is gpu_detector


if __name__ == "__main__":
    pytest.main([__file__])