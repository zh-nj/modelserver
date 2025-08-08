"""
GPU检测和监控工具
"""
import asyncio
import logging
import subprocess
import json
import re
import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from ..models.schemas import GPUInfo, GPUMetrics
from ..models.enums import GPUVendor

logger = logging.getLogger(__name__)

class GPUDetector:
    """GPU检测器 - 支持NVIDIA和AMD GPU的检测和监控"""
    
    def __init__(self):
        self._gpu_cache: Dict[int, GPUInfo] = {}
        self._cache_expiry: Optional[datetime] = None
        self._cache_duration = timedelta(seconds=30)  # 缓存30秒
        
    async def detect_gpus(self, use_cache: bool = True) -> List[GPUInfo]:
        """
        检测系统中的GPU设备
        
        Args:
            use_cache: 是否使用缓存结果
            
        Returns:
            GPU设备信息列表
        """
        # 检查缓存是否有效
        if (use_cache and self._cache_expiry and 
            datetime.now() < self._cache_expiry and self._gpu_cache):
            return list(self._gpu_cache.values())
        
        gpus = []
        
        # 检测NVIDIA GPU
        nvidia_gpus = await self._detect_nvidia_gpus()
        gpus.extend(nvidia_gpus)
        
        # 检测AMD GPU
        amd_gpus = await self._detect_amd_gpus()
        gpus.extend(amd_gpus)
        
        # 更新缓存
        self._gpu_cache = {gpu.device_id: gpu for gpu in gpus}
        self._cache_expiry = datetime.now() + self._cache_duration
        
        logger.info(f"检测到 {len(gpus)} 个GPU设备")
        return gpus
    
    async def _detect_nvidia_gpus(self) -> List[GPUInfo]:
        """检测NVIDIA GPU设备"""
        gpus = []
        try:
            import pynvml
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            
            for i in range(device_count):
                try:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    gpu_info = await self._get_nvidia_gpu_info(handle, i)
                    if gpu_info:
                        gpus.append(gpu_info)
                except Exception as e:
                    logger.error(f"获取NVIDIA GPU {i} 信息时出错: {e}")
                    
        except ImportError:
            logger.warning("pynvml未安装，无法检测NVIDIA GPU")
        except Exception as e:
            logger.error(f"初始化NVIDIA GPU检测时出错: {e}")
        
        return gpus
    
    async def _get_nvidia_gpu_info(self, handle, device_id: int) -> Optional[GPUInfo]:
        """获取单个NVIDIA GPU的详细信息"""
        try:
            import pynvml
            
            # 基本信息
            name_bytes = pynvml.nvmlDeviceGetName(handle)
            name = name_bytes.decode('utf-8') if isinstance(name_bytes, bytes) else str(name_bytes)
            
            # 内存信息
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            memory_total = mem_info.total // (1024 * 1024)  # 转换为MB
            memory_used = mem_info.used // (1024 * 1024)
            memory_free = mem_info.free // (1024 * 1024)
            
            # GPU利用率
            try:
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                utilization = float(util.gpu)
            except:
                utilization = 0.0
            
            # 温度
            try:
                temperature = float(pynvml.nvmlDeviceGetTemperature(
                    handle, pynvml.NVML_TEMPERATURE_GPU))
            except:
                temperature = 0.0
            
            # 功耗
            try:
                power_usage = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0
            except:
                power_usage = 0.0
            
            # 驱动版本
            try:
                driver_version = pynvml.nvmlSystemGetDriverVersion().decode('utf-8')
            except:
                driver_version = None
            
            return GPUInfo(
                device_id=device_id,
                name=name,
                vendor=GPUVendor.NVIDIA,
                memory_total=memory_total,
                memory_used=memory_used,
                memory_free=memory_free,
                utilization=utilization,
                temperature=temperature,
                power_usage=power_usage,
                driver_version=driver_version
            )
            
        except Exception as e:
            logger.error(f"获取NVIDIA GPU {device_id} 详细信息时出错: {e}")
            return None
    
    async def _detect_amd_gpus(self) -> List[GPUInfo]:
        """检测AMD GPU设备"""
        gpus = []
        
        # 尝试使用rocm-smi命令
        rocm_gpus = await self._detect_amd_rocm_smi()
        gpus.extend(rocm_gpus)
        
        # 如果rocm-smi不可用，尝试其他方法
        if not gpus:
            sysfs_gpus = await self._detect_amd_sysfs()
            gpus.extend(sysfs_gpus)
        
        return gpus
    
    async def _detect_amd_rocm_smi(self) -> List[GPUInfo]:
        """使用rocm-smi检测AMD GPU"""
        gpus = []
        try:
            # 检查rocm-smi是否可用
            result = await self._run_command(['rocm-smi', '--showid'])
            if result.returncode != 0:
                logger.debug("rocm-smi不可用")
                return gpus
            
            # 获取GPU列表
            result = await self._run_command(['rocm-smi', '--showid', '--json'])
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    for gpu_id, gpu_data in data.items():
                        if gpu_id.startswith('card'):
                            device_id = int(gpu_id.replace('card', ''))
                            gpu_info = await self._parse_amd_rocm_info(device_id)
                            if gpu_info:
                                gpus.append(gpu_info)
                except json.JSONDecodeError:
                    logger.error("解析rocm-smi JSON输出失败")
            
        except FileNotFoundError:
            logger.debug("rocm-smi命令未找到")
        except Exception as e:
            logger.error(f"使用rocm-smi检测AMD GPU时出错: {e}")
        
        return gpus
    
    async def _parse_amd_rocm_info(self, device_id: int) -> Optional[GPUInfo]:
        """解析AMD GPU的rocm-smi信息"""
        try:
            # 获取基本信息
            info_result = await self._run_command([
                'rocm-smi', f'--device={device_id}', '--showproductname', '--json'
            ])
            
            # 获取内存信息
            mem_result = await self._run_command([
                'rocm-smi', f'--device={device_id}', '--showmeminfo', 'vram', '--json'
            ])
            
            # 获取利用率信息
            util_result = await self._run_command([
                'rocm-smi', f'--device={device_id}', '--showuse', '--json'
            ])
            
            # 获取温度信息
            temp_result = await self._run_command([
                'rocm-smi', f'--device={device_id}', '--showtemp', '--json'
            ])
            
            # 获取功耗信息
            power_result = await self._run_command([
                'rocm-smi', f'--device={device_id}', '--showpower', '--json'
            ])
            
            # 解析结果
            name = "AMD GPU"  # 默认名称
            memory_total = 0
            memory_used = 0
            utilization = 0.0
            temperature = 0.0
            power_usage = 0.0
            
            # 解析产品名称
            if info_result.returncode == 0:
                try:
                    info_data = json.loads(info_result.stdout)
                    card_key = f'card{device_id}'
                    if card_key in info_data:
                        name = info_data[card_key].get('Product Name', name)
                except:
                    pass
            
            # 解析内存信息
            if mem_result.returncode == 0:
                try:
                    mem_data = json.loads(mem_result.stdout)
                    card_key = f'card{device_id}'
                    if card_key in mem_data:
                        vram_info = mem_data[card_key].get('VRAM Total Memory (B)', '0')
                        memory_total = int(vram_info) // (1024 * 1024)  # 转换为MB
                        
                        vram_used = mem_data[card_key].get('VRAM Total Used Memory (B)', '0')
                        memory_used = int(vram_used) // (1024 * 1024)
                except:
                    pass
            
            # 解析利用率
            if util_result.returncode == 0:
                try:
                    util_data = json.loads(util_result.stdout)
                    card_key = f'card{device_id}'
                    if card_key in util_data:
                        gpu_use = util_data[card_key].get('GPU use (%)', '0')
                        utilization = float(gpu_use.replace('%', ''))
                except:
                    pass
            
            # 解析温度
            if temp_result.returncode == 0:
                try:
                    temp_data = json.loads(temp_result.stdout)
                    card_key = f'card{device_id}'
                    if card_key in temp_data:
                        temp_str = temp_data[card_key].get('Temperature (Sensor edge) (C)', '0.0')
                        temperature = float(temp_str.replace('c', ''))
                except:
                    pass
            
            # 解析功耗
            if power_result.returncode == 0:
                try:
                    power_data = json.loads(power_result.stdout)
                    card_key = f'card{device_id}'
                    if card_key in power_data:
                        power_str = power_data[card_key].get('Average Graphics Package Power (W)', '0.0')
                        power_usage = float(power_str.replace('W', ''))
                except:
                    pass
            
            memory_free = memory_total - memory_used
            
            return GPUInfo(
                device_id=device_id,
                name=name,
                vendor=GPUVendor.AMD,
                memory_total=memory_total,
                memory_used=memory_used,
                memory_free=memory_free,
                utilization=utilization,
                temperature=temperature,
                power_usage=power_usage,
                driver_version=None  # AMD驱动版本获取较复杂，暂时设为None
            )
            
        except Exception as e:
            logger.error(f"解析AMD GPU {device_id} 信息时出错: {e}")
            return None
    
    async def _detect_amd_sysfs(self) -> List[GPUInfo]:
        """通过sysfs检测AMD GPU（备用方法）"""
        gpus = []
        try:
            # 检查/sys/class/drm/目录下的AMD GPU设备
            drm_path = "/sys/class/drm"
            if not os.path.exists(drm_path):
                return gpus
            
            device_id = 0
            for entry in os.listdir(drm_path):
                if entry.startswith('card') and not entry.endswith('-'):
                    card_path = os.path.join(drm_path, entry)
                    device_path = os.path.join(card_path, "device")
                    
                    # 检查是否是AMD GPU
                    vendor_path = os.path.join(device_path, "vendor")
                    if os.path.exists(vendor_path):
                        with open(vendor_path, 'r') as f:
                            vendor_id = f.read().strip()
                            # AMD的vendor ID是0x1002
                            if vendor_id == "0x1002":
                                gpu_info = await self._parse_amd_sysfs_info(device_id, device_path)
                                if gpu_info:
                                    gpus.append(gpu_info)
                                    device_id += 1
        
        except Exception as e:
            logger.error(f"通过sysfs检测AMD GPU时出错: {e}")
        
        return gpus
    
    async def _parse_amd_sysfs_info(self, device_id: int, device_path: str) -> Optional[GPUInfo]:
        """解析sysfs中的AMD GPU信息"""
        try:
            name = "AMD GPU"
            
            # 尝试获取设备名称
            try:
                device_id_path = os.path.join(device_path, "device")
                if os.path.exists(device_id_path):
                    with open(device_id_path, 'r') as f:
                        device_id_hex = f.read().strip()
                        # 这里可以根据设备ID映射到具体的GPU型号
                        name = f"AMD GPU ({device_id_hex})"
            except:
                pass
            
            # sysfs中获取详细信息比较困难，返回基本信息
            return GPUInfo(
                device_id=device_id,
                name=name,
                vendor=GPUVendor.AMD,
                memory_total=0,  # 需要其他方法获取
                memory_used=0,
                memory_free=0,
                utilization=0.0,
                temperature=0.0,
                power_usage=0.0,
                driver_version=None
            )
            
        except Exception as e:
            logger.error(f"解析AMD GPU sysfs信息时出错: {e}")
            return None
    
    async def _run_command(self, cmd: List[str], timeout: int = 10) -> subprocess.CompletedProcess:
        """异步运行系统命令"""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=process.returncode,
                stdout=stdout.decode('utf-8') if stdout else '',
                stderr=stderr.decode('utf-8') if stderr else ''
            )
        except asyncio.TimeoutError:
            logger.error(f"命令执行超时: {' '.join(cmd)}")
            return subprocess.CompletedProcess(args=cmd, returncode=-1, stdout='', stderr='timeout')
        except Exception as e:
            logger.error(f"执行命令时出错 {' '.join(cmd)}: {e}")
            return subprocess.CompletedProcess(args=cmd, returncode=-1, stdout='', stderr=str(e))
    
    async def get_gpu_info(self, device_id: int) -> Optional[GPUInfo]:
        """获取指定GPU的详细信息"""
        gpus = await self.detect_gpus()
        for gpu in gpus:
            if gpu.device_id == device_id:
                return gpu
        return None
    
    async def get_gpu_metrics(self, device_id: int) -> Optional[GPUMetrics]:
        """获取指定GPU的实时指标"""
        gpu_info = await self.get_gpu_info(device_id)
        if not gpu_info:
            return None
        
        return GPUMetrics(
            device_id=device_id,
            timestamp=datetime.now(),
            utilization=gpu_info.utilization,
            memory_used=gpu_info.memory_used,
            memory_total=gpu_info.memory_total,
            temperature=gpu_info.temperature,
            power_usage=gpu_info.power_usage
        )
    
    async def get_all_gpu_metrics(self) -> List[GPUMetrics]:
        """获取所有GPU的实时指标"""
        gpus = await self.detect_gpus()
        metrics = []
        
        for gpu in gpus:
            metric = GPUMetrics(
                device_id=gpu.device_id,
                timestamp=datetime.now(),
                utilization=gpu.utilization,
                memory_used=gpu.memory_used,
                memory_total=gpu.memory_total,
                temperature=gpu.temperature,
                power_usage=gpu.power_usage
            )
            metrics.append(metric)
        
        return metrics
    
    def clear_cache(self):
        """清除GPU信息缓存"""
        self._gpu_cache.clear()
        self._cache_expiry = None
        logger.debug("GPU信息缓存已清除")


class GPUMonitor:
    """GPU监控器 - 提供持续的GPU状态监控和更新机制"""
    
    def __init__(self, detector: GPUDetector, update_interval: int = 5):
        self.detector = detector
        self.update_interval = update_interval
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._callbacks: List[callable] = []
    
    def add_callback(self, callback: callable):
        """添加GPU状态更新回调函数"""
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: callable):
        """移除GPU状态更新回调函数"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    async def start_monitoring(self):
        """开始GPU监控"""
        if self._monitoring:
            logger.warning("GPU监控已在运行中")
            return
        
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info(f"GPU监控已启动，更新间隔: {self.update_interval}秒")
    
    async def stop_monitoring(self):
        """停止GPU监控"""
        if not self._monitoring:
            return
        
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("GPU监控已停止")
    
    async def _monitor_loop(self):
        """监控循环"""
        try:
            while self._monitoring:
                try:
                    # 获取最新的GPU指标
                    metrics = await self.detector.get_all_gpu_metrics()
                    
                    # 调用所有回调函数
                    for callback in self._callbacks:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(metrics)
                            else:
                                callback(metrics)
                        except Exception as e:
                            logger.error(f"GPU监控回调函数执行出错: {e}")
                    
                    # 等待下次更新
                    await asyncio.sleep(self.update_interval)
                    
                except Exception as e:
                    logger.error(f"GPU监控循环出错: {e}")
                    await asyncio.sleep(self.update_interval)
                    
        except asyncio.CancelledError:
            logger.debug("GPU监控循环被取消")
        except Exception as e:
            logger.error(f"GPU监控循环异常退出: {e}")


# 全局GPU检测器和监控器实例
gpu_detector = GPUDetector()
gpu_monitor = GPUMonitor(gpu_detector)
# 模块级别的便捷函数
async def get_gpu_info() -> List[GPUInfo]:
    """获取所有GPU信息的便捷函数"""
    return await gpu_detector.detect_gpus()

async def get_gpu_metrics() -> List[GPUMetrics]:
    """获取所有GPU指标的便捷函数"""
    return await gpu_detector.get_all_gpu_metrics()

async def get_single_gpu_info(device_id: int) -> Optional[GPUInfo]:
    """获取单个GPU信息的便捷函数"""
    return await gpu_detector.get_gpu_info(device_id)

async def get_single_gpu_metrics(device_id: int) -> Optional[GPUMetrics]:
    """获取单个GPU指标的便捷函数"""
    return await gpu_detector.get_gpu_metrics(device_id)