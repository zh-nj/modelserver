"""
监控服务 - 实现实时监控数据收集
提供GPU指标收集、模型性能指标收集和系统资源监控功能
"""
import asyncio
import logging
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque

from .base import MonitoringServiceInterface
from .metrics_storage import SQLiteMetricsStorage, MetricsStorageService
from ..models.schemas import (
    GPUInfo, GPUMetrics, SystemOverview, ModelInfo, 
    TimeRange, Metrics, AlertRule, ModelPerformanceMetrics,
    SystemResourceMetrics, AlertEvent
)
from ..models.enums import ModelStatus, HealthStatus, AlertLevel
from ..utils.gpu import GPUDetector, GPUMonitor
from ..core.config import settings

logger = logging.getLogger(__name__)

class MetricsCollector:
    """指标收集器基类"""
    
    def __init__(self, collection_interval: int = 5):
        self.collection_interval = collection_interval
        self._collecting = False
        self._collection_task: Optional[asyncio.Task] = None
        self._callbacks: List[Callable] = []
    
    def add_callback(self, callback: Callable):
        """添加指标更新回调"""
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        """移除指标更新回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    async def start_collection(self):
        """开始收集指标"""
        if self._collecting:
            logger.warning(f"{self.__class__.__name__} 已在收集中")
            return
        
        self._collecting = True
        self._collection_task = asyncio.create_task(self._collection_loop())
        logger.info(f"{self.__class__.__name__} 开始收集指标，间隔: {self.collection_interval}秒")
    
    async def stop_collection(self):
        """停止收集指标"""
        if not self._collecting:
            return
        
        self._collecting = False
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"{self.__class__.__name__} 停止收集指标")
    
    async def _collection_loop(self):
        """收集循环"""
        try:
            while self._collecting:
                try:
                    # 收集指标
                    metrics = await self.collect_metrics()
                    
                    # 通知回调函数
                    for callback in self._callbacks:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(metrics)
                            else:
                                callback(metrics)
                        except Exception as e:
                            logger.error(f"指标回调执行失败: {e}")
                    
                    # 等待下次收集
                    await asyncio.sleep(self.collection_interval)
                    
                except Exception as e:
                    logger.error(f"指标收集循环出错: {e}")
                    await asyncio.sleep(self.collection_interval)
                    
        except asyncio.CancelledError:
            logger.debug(f"{self.__class__.__name__} 收集循环被取消")
        except Exception as e:
            logger.error(f"{self.__class__.__name__} 收集循环异常退出: {e}")
    
    async def collect_metrics(self) -> Any:
        """收集指标 - 子类需要实现"""
        raise NotImplementedError

class GPUMetricsCollector(MetricsCollector):
    """GPU指标收集器"""
    
    def __init__(self, gpu_detector: GPUDetector, collection_interval: int = 5):
        super().__init__(collection_interval)
        self.gpu_detector = gpu_detector
        self._metrics_history: Dict[int, deque] = defaultdict(lambda: deque(maxlen=1000))
    
    async def collect_metrics(self) -> List[GPUMetrics]:
        """收集GPU指标"""
        try:
            metrics = await self.gpu_detector.get_all_gpu_metrics()
            
            # 存储历史数据
            for metric in metrics:
                self._metrics_history[metric.device_id].append(metric)
            
            return metrics
            
        except Exception as e:
            logger.error(f"收集GPU指标失败: {e}")
            return []
    
    def get_metrics_history(self, device_id: int, time_range: TimeRange) -> List[GPUMetrics]:
        """获取GPU指标历史数据"""
        history = self._metrics_history.get(device_id, deque())
        filtered_metrics = []
        
        for metric in history:
            if time_range.start_time <= metric.timestamp <= time_range.end_time:
                filtered_metrics.append(metric)
        
        return filtered_metrics

class ModelPerformanceCollector(MetricsCollector):
    """模型性能指标收集器"""
    
    def __init__(self, model_manager, collection_interval: int = 10):
        super().__init__(collection_interval)
        self.model_manager = model_manager
        self._metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._request_counters: Dict[str, int] = defaultdict(int)
        self._response_times: Dict[str, List[float]] = defaultdict(list)
        self._error_counters: Dict[str, int] = defaultdict(int)
    
    async def collect_metrics(self) -> List[ModelPerformanceMetrics]:
        """收集模型性能指标"""
        try:
            metrics = []
            models = await self.model_manager.list_models()
            
            for model in models:
                if model.status == ModelStatus.RUNNING:
                    metric = await self._collect_model_metrics(model)
                    if metric:
                        metrics.append(metric)
                        # 存储历史数据
                        self._metrics_history[model.id].append(metric)
            
            return metrics
            
        except Exception as e:
            logger.error(f"收集模型性能指标失败: {e}")
            return []
    
    async def _collect_model_metrics(self, model: ModelInfo) -> Optional[ModelPerformanceMetrics]:
        """收集单个模型的性能指标"""
        try:
            # 获取模型进程信息
            memory_usage = model.memory_usage or 0
            
            # 计算平均响应时间
            response_times = self._response_times.get(model.id, [])
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
            
            # 创建性能指标
            metric = ModelPerformanceMetrics(
                model_id=model.id,
                timestamp=datetime.now(),
                request_count=self._request_counters.get(model.id, 0),
                total_response_time=sum(response_times),
                error_count=self._error_counters.get(model.id, 0),
                memory_usage=memory_usage,
                gpu_utilization=0.0  # 需要从GPU指标中获取
            )
            
            # 重置计数器（可选，根据需求决定）
            # self._request_counters[model.id] = 0
            # self._response_times[model.id] = []
            # self._error_counters[model.id] = 0
            
            return metric
            
        except Exception as e:
            logger.error(f"收集模型 {model.id} 性能指标失败: {e}")
            return None
    
    def record_request(self, model_id: str, response_time: float, success: bool = True):
        """记录请求指标"""
        self._request_counters[model_id] += 1
        self._response_times[model_id].append(response_time)
        
        if not success:
            self._error_counters[model_id] += 1
        
        # 限制响应时间历史记录数量
        if len(self._response_times[model_id]) > 1000:
            self._response_times[model_id] = self._response_times[model_id][-500:]
    
    def get_metrics_history(self, model_id: str, time_range: TimeRange) -> List[ModelPerformanceMetrics]:
        """获取模型性能指标历史数据"""
        history = self._metrics_history.get(model_id, deque())
        filtered_metrics = []
        
        for metric in history:
            if time_range.start_time <= metric.timestamp <= time_range.end_time:
                filtered_metrics.append(metric)
        
        return filtered_metrics

class SystemResourceCollector(MetricsCollector):
    """系统资源指标收集器"""
    
    def __init__(self, collection_interval: int = 10):
        super().__init__(collection_interval)
        self._metrics_history: deque = deque(maxlen=1000)
        self._network_counters = None
    
    async def collect_metrics(self) -> SystemResourceMetrics:
        """收集系统资源指标"""
        try:
            # CPU使用率
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            memory_total = memory.total // (1024 * 1024)  # MB
            memory_used = memory.used // (1024 * 1024)  # MB
            memory_usage = memory.percent
            
            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            disk_total = disk.total // (1024 * 1024 * 1024)  # GB
            disk_used = disk.used // (1024 * 1024 * 1024)  # GB
            disk_usage = (disk.used / disk.total) * 100
            
            # 网络使用情况
            network = psutil.net_io_counters()
            network_sent = network.bytes_sent
            network_recv = network.bytes_recv
            
            # 系统负载
            load_average = list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else [0.0, 0.0, 0.0]
            
            metric = SystemResourceMetrics(
                timestamp=datetime.now(),
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                memory_total=memory_total,
                memory_used=memory_used,
                disk_usage=disk_usage,
                disk_total=disk_total,
                disk_used=disk_used,
                network_sent=network_sent,
                network_recv=network_recv,
                load_average=load_average
            )
            
            # 存储历史数据
            self._metrics_history.append(metric)
            
            return metric
            
        except Exception as e:
            logger.error(f"收集系统资源指标失败: {e}")
            return SystemResourceMetrics(timestamp=datetime.now())
    
    def get_metrics_history(self, time_range: TimeRange) -> List[SystemResourceMetrics]:
        """获取系统资源指标历史数据"""
        filtered_metrics = []
        
        for metric in self._metrics_history:
            if time_range.start_time <= metric.timestamp <= time_range.end_time:
                filtered_metrics.append(metric)
        
        return filtered_metrics

class AlertManager:
    """告警管理器"""
    
    def __init__(self):
        self._alert_rules: Dict[str, AlertRule] = {}
        self._active_alerts: Dict[str, AlertEvent] = {}
        self._alert_history: deque = deque(maxlen=10000)
        self._notification_callbacks: List[Callable] = []
    
    def add_alert_rule(self, rule: AlertRule):
        """添加告警规则"""
        self._alert_rules[rule.id] = rule
        logger.info(f"添加告警规则: {rule.name}")
    
    def remove_alert_rule(self, rule_id: str):
        """移除告警规则"""
        if rule_id in self._alert_rules:
            del self._alert_rules[rule_id]
            logger.info(f"移除告警规则: {rule_id}")
    
    def add_notification_callback(self, callback: Callable):
        """添加通知回调"""
        self._notification_callbacks.append(callback)
    
    async def check_alerts(self, gpu_metrics: List[GPUMetrics], 
                          model_metrics: List[ModelPerformanceMetrics],
                          system_metrics: SystemResourceMetrics):
        """检查告警条件"""
        try:
            for rule in self._alert_rules.values():
                if not rule.enabled:
                    continue
                
                triggered = await self._evaluate_alert_rule(
                    rule, gpu_metrics, model_metrics, system_metrics
                )
                
                if triggered:
                    await self._trigger_alert(rule)
                else:
                    await self._resolve_alert(rule.id)
                    
        except Exception as e:
            logger.error(f"检查告警失败: {e}")
    
    async def _evaluate_alert_rule(self, rule: AlertRule, 
                                 gpu_metrics: List[GPUMetrics],
                                 model_metrics: List[ModelPerformanceMetrics],
                                 system_metrics: SystemResourceMetrics) -> bool:
        """评估告警规则"""
        try:
            # 这里实现简单的条件评估逻辑
            # 实际应用中可以使用更复杂的表达式引擎
            
            if "gpu_temperature" in rule.condition:
                for gpu_metric in gpu_metrics:
                    if gpu_metric.temperature > rule.threshold:
                        return True
            
            if "gpu_utilization" in rule.condition:
                for gpu_metric in gpu_metrics:
                    if gpu_metric.utilization > rule.threshold:
                        return True
            
            if "memory_usage" in rule.condition:
                if system_metrics.memory_usage > rule.threshold:
                    return True
            
            if "cpu_usage" in rule.condition:
                if system_metrics.cpu_usage > rule.threshold:
                    return True
            
            if "model_error_rate" in rule.condition:
                for model_metric in model_metrics:
                    if model_metric.request_count > 0:
                        error_rate = (model_metric.error_count / model_metric.request_count) * 100
                        if error_rate > rule.threshold:
                            return True
            
            return False
            
        except Exception as e:
            logger.error(f"评估告警规则 {rule.id} 失败: {e}")
            return False
    
    async def _trigger_alert(self, rule: AlertRule):
        """触发告警"""
        alert_id = f"{rule.id}_{int(time.time())}"
        
        # 检查是否已有活跃告警
        if rule.id in self._active_alerts:
            return
        
        alert = AlertEvent(
            id=alert_id,
            rule_id=rule.id,
            level=rule.level,
            message=f"告警规则 '{rule.name}' 被触发: {rule.condition} > {rule.threshold}",
            timestamp=datetime.now()
        )
        
        self._active_alerts[rule.id] = alert
        self._alert_history.append(alert)
        
        # 发送通知
        for callback in self._notification_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"发送告警通知失败: {e}")
        
        logger.warning(f"触发告警: {alert.message}")
    
    async def _resolve_alert(self, rule_id: str):
        """解决告警"""
        if rule_id in self._active_alerts:
            alert = self._active_alerts[rule_id]
            alert.resolved = True
            alert.resolved_at = datetime.now()
            del self._active_alerts[rule_id]
            logger.info(f"告警已解决: {alert.message}")
    
    def get_active_alerts(self) -> List[AlertEvent]:
        """获取活跃告警"""
        return list(self._active_alerts.values())
    
    def get_alert_history(self, limit: int = 100) -> List[AlertEvent]:
        """获取告警历史"""
        return list(self._alert_history)[-limit:]

class MonitoringService(MonitoringServiceInterface):
    """监控服务实现"""
    
    def __init__(self, model_manager, gpu_detector: GPUDetector):
        self.model_manager = model_manager
        self.gpu_detector = gpu_detector
        
        # 初始化存储和查询服务
        self.storage = SQLiteMetricsStorage()
        self.query_service = MetricsStorageService()
        
        # 初始化收集器
        self.gpu_collector = GPUMetricsCollector(gpu_detector)
        self.model_collector = ModelPerformanceCollector(model_manager)
        self.system_collector = SystemResourceCollector()
        
        # 初始化告警管理器
        self.alert_manager = AlertManager()
        
        # 监控状态
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        # 回调函数
        self._metrics_callbacks: List[Callable] = []
        
        # 设置收集器回调
        self.gpu_collector.add_callback(self._on_gpu_metrics_update)
        self.model_collector.add_callback(self._on_model_metrics_update)
        self.system_collector.add_callback(self._on_system_metrics_update)
    
    async def initialize(self):
        """初始化监控服务"""
        try:
            logger.info("初始化监控服务...")
            
            # 初始化默认告警规则
            await self._setup_default_alert_rules()
            
            logger.info("监控服务初始化完成")
            
        except Exception as e:
            logger.error(f"初始化监控服务失败: {e}")
            raise
    
    async def _setup_default_alert_rules(self):
        """设置默认告警规则"""
        default_rules = [
            AlertRule(
                id="gpu_temperature_high",
                name="GPU温度过高",
                condition="gpu_temperature",
                threshold=80.0,
                level=AlertLevel.WARNING,
                enabled=True
            ),
            AlertRule(
                id="gpu_memory_high",
                name="GPU内存使用率过高",
                condition="gpu_memory_usage",
                threshold=90.0,
                level=AlertLevel.WARNING,
                enabled=True
            ),
            AlertRule(
                id="system_memory_high",
                name="系统内存使用率过高",
                condition="memory_usage",
                threshold=85.0,
                level=AlertLevel.WARNING,
                enabled=True
            ),
            AlertRule(
                id="cpu_usage_high",
                name="CPU使用率过高",
                condition="cpu_usage",
                threshold=90.0,
                level=AlertLevel.WARNING,
                enabled=True
            )
        ]
        
        for rule in default_rules:
            self.alert_manager.add_alert_rule(rule)
    
    async def start_monitoring(self):
        """开始监控"""
        if self._monitoring:
            logger.warning("监控服务已在运行中")
            return
        
        try:
            self._monitoring = True
            
            # 启动各个收集器
            await self.gpu_collector.start_collection()
            await self.model_collector.start_collection()
            await self.system_collector.start_collection()
            
            # 启动监控任务
            self._monitor_task = asyncio.create_task(self._monitoring_loop())
            
            logger.info("监控服务已启动")
            
        except Exception as e:
            logger.error(f"启动监控服务失败: {e}")
            self._monitoring = False
            raise
    
    async def stop_monitoring(self):
        """停止监控"""
        if not self._monitoring:
            return
        
        try:
            self._monitoring = False
            
            # 停止监控任务
            if self._monitor_task:
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass
            
            # 停止各个收集器
            await self.gpu_collector.stop_collection()
            await self.model_collector.stop_collection()
            await self.system_collector.stop_collection()
            
            logger.info("监控服务已停止")
            
        except Exception as e:
            logger.error(f"停止监控服务失败: {e}")
    
    async def _monitoring_loop(self):
        """监控主循环"""
        try:
            while self._monitoring:
                try:
                    # 等待一段时间
                    await asyncio.sleep(30)  # 每30秒检查一次告警
                    
                    # 获取最新指标
                    gpu_metrics = await self.gpu_collector.collect_metrics()
                    model_metrics = await self.model_collector.collect_metrics()
                    system_metrics = await self.system_collector.collect_metrics()
                    
                    # 检查告警
                    await self.alert_manager.check_alerts(
                        gpu_metrics, model_metrics, system_metrics
                    )
                    
                except Exception as e:
                    logger.error(f"监控循环出错: {e}")
                    await asyncio.sleep(30)
                    
        except asyncio.CancelledError:
            logger.debug("监控循环被取消")
        except Exception as e:
            logger.error(f"监控循环异常退出: {e}")
    
    async def _on_gpu_metrics_update(self, metrics: List[GPUMetrics]):
        """GPU指标更新回调"""
        # 存储指标到数据库
        try:
            await self.storage.store_gpu_metrics(metrics)
        except Exception as e:
            logger.error(f"存储GPU指标失败: {e}")
        
        # 通知其他回调函数
        for callback in self._metrics_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback("gpu_metrics", metrics)
                else:
                    callback("gpu_metrics", metrics)
            except Exception as e:
                logger.error(f"GPU指标回调执行失败: {e}")
    
    async def _on_model_metrics_update(self, metrics: List[ModelPerformanceMetrics]):
        """模型指标更新回调"""
        # 存储指标到数据库
        try:
            await self.storage.store_model_metrics(metrics)
        except Exception as e:
            logger.error(f"存储模型性能指标失败: {e}")
        
        # 通知其他回调函数
        for callback in self._metrics_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback("model_metrics", metrics)
                else:
                    callback("model_metrics", metrics)
            except Exception as e:
                logger.error(f"模型指标回调执行失败: {e}")
    
    async def _on_system_metrics_update(self, metrics: SystemResourceMetrics):
        """系统指标更新回调"""
        # 存储指标到数据库
        try:
            await self.storage.store_system_metrics(metrics)
        except Exception as e:
            logger.error(f"存储系统资源指标失败: {e}")
        
        # 通知其他回调函数
        for callback in self._metrics_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback("system_metrics", metrics)
                else:
                    callback("system_metrics", metrics)
            except Exception as e:
                logger.error(f"系统指标回调执行失败: {e}")
    
    def add_metrics_callback(self, callback: Callable):
        """添加指标更新回调"""
        self._metrics_callbacks.append(callback)
    
    def remove_metrics_callback(self, callback: Callable):
        """移除指标更新回调"""
        if callback in self._metrics_callbacks:
            self._metrics_callbacks.remove(callback)
    
    # 实现接口方法
    async def collect_gpu_metrics(self) -> List[GPUMetrics]:
        """收集GPU指标"""
        return await self.gpu_collector.collect_metrics()
    
    async def collect_system_metrics(self) -> SystemResourceMetrics:
        """收集系统资源指标"""
        return await self.system_collector.collect_metrics()
    
    async def check_model_health(self, model_id: str) -> HealthStatus:
        """检查模型健康状态"""
        return await self.model_manager.get_model_health(model_id)
    
    async def get_system_overview(self) -> SystemOverview:
        """获取系统概览"""
        try:
            # 获取模型信息
            models = await self.model_manager.list_models()
            total_models = len(models)
            running_models = sum(1 for model in models if model.status == ModelStatus.RUNNING)
            
            # 获取GPU信息
            gpus = await self.gpu_detector.detect_gpus()
            total_gpus = len(gpus)
            available_gpus = sum(1 for gpu in gpus if gpu.utilization < 80)  # 利用率低于80%认为可用
            total_gpu_memory = sum(gpu.memory_total for gpu in gpus)
            used_gpu_memory = sum(gpu.memory_used for gpu in gpus)
            
            # 系统运行时间（简化实现）
            system_uptime = int(time.time() - psutil.boot_time())
            
            return SystemOverview(
                total_models=total_models,
                running_models=running_models,
                total_gpus=total_gpus,
                available_gpus=available_gpus,
                total_gpu_memory=total_gpu_memory,
                used_gpu_memory=used_gpu_memory,
                system_uptime=system_uptime,
                last_updated=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"获取系统概览失败: {e}")
            return SystemOverview(
                total_models=0,
                running_models=0,
                total_gpus=0,
                available_gpus=0,
                total_gpu_memory=0,
                used_gpu_memory=0,
                system_uptime=0,
                last_updated=datetime.now()
            )
    
    async def setup_alerts(self, rules: List[AlertRule]) -> bool:
        """设置告警规则"""
        try:
            for rule in rules:
                self.alert_manager.add_alert_rule(rule)
            return True
        except Exception as e:
            logger.error(f"设置告警规则失败: {e}")
            return False
    
    async def get_performance_metrics(self, model_id: str, time_range: TimeRange) -> Metrics:
        """获取模型性能指标"""
        try:
            # 使用查询服务获取性能摘要
            return await self.query_service.get_model_performance_summary(model_id, time_range)
            
        except Exception as e:
            logger.error(f"获取模型 {model_id} 性能指标失败: {e}")
            return Metrics(
                model_id=model_id,
                time_range=time_range,
                request_count=0,
                average_response_time=0.0,
                error_rate=0.0,
                throughput=0.0,
                gpu_utilization=[]
            )
    
    def record_model_request(self, model_id: str, response_time: float, success: bool = True):
        """记录模型请求指标"""
        self.model_collector.record_request(model_id, response_time, success)
    
    def get_active_alerts(self) -> List[AlertEvent]:
        """获取活跃告警"""
        return self.alert_manager.get_active_alerts()
    
    def get_alert_history(self, limit: int = 100) -> List[AlertEvent]:
        """获取告警历史"""
        return self.alert_manager.get_alert_history(limit)
    
    # 扩展查询接口
    async def get_gpu_metrics_history(self, device_id: Optional[int] = None, 
                                     time_range: Optional[TimeRange] = None,
                                     limit: int = 1000) -> List[GPUMetrics]:
        """获取GPU指标历史数据"""
        return await self.storage.query_gpu_metrics(device_id, time_range, limit)
    
    async def get_model_metrics_history(self, model_id: str, 
                                       time_range: Optional[TimeRange] = None,
                                       limit: int = 1000) -> List[ModelPerformanceMetrics]:
        """获取模型性能指标历史数据"""
        return await self.storage.query_model_metrics(model_id, time_range, limit)
    
    async def get_system_metrics_history(self, time_range: Optional[TimeRange] = None,
                                        limit: int = 1000) -> List[SystemResourceMetrics]:
        """获取系统资源指标历史数据"""
        return await self.storage.query_system_metrics(time_range, limit)
    
    async def get_gpu_utilization_trend(self, device_id: int, time_range: TimeRange,
                                       interval_minutes: int = 5) -> List[Dict[str, Any]]:
        """获取GPU利用率趋势"""
        return await self.query_service.get_gpu_utilization_trend(device_id, time_range, interval_minutes)
    
    async def get_system_resource_trend(self, time_range: TimeRange,
                                       interval_minutes: int = 5) -> List[Dict[str, Any]]:
        """获取系统资源使用趋势"""
        return await self.query_service.get_system_resource_trend(time_range, interval_minutes)
    
    async def get_top_models_by_requests(self, time_range: TimeRange, limit: int = 10) -> List[Dict[str, Any]]:
        """获取请求量最高的模型"""
        return await self.query_service.get_top_models_by_requests(time_range, limit)
    
    async def aggregate_gpu_metrics(self, device_id: int, time_range: TimeRange,
                                   interval_minutes: int = 5) -> List[Dict[str, Any]]:
        """聚合GPU指标数据"""
        return await self.storage.aggregate_gpu_metrics(device_id, time_range, interval_minutes)
    
    async def aggregate_model_metrics(self, model_id: str, time_range: TimeRange,
                                     interval_minutes: int = 5) -> List[Dict[str, Any]]:
        """聚合模型性能指标数据"""
        return await self.storage.aggregate_model_metrics(model_id, time_range, interval_minutes)
    
    async def cleanup_old_metrics(self, retention_days: int = 30) -> Dict[str, int]:
        """清理过期的历史数据"""
        return await self.storage.cleanup_old_data(retention_days)
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        return await self.storage.get_storage_stats()
    
    async def shutdown(self):
        """关闭监控服务"""
        try:
            logger.info("关闭监控服务...")
            await self.stop_monitoring()
            logger.info("监控服务关闭完成")
        except Exception as e:
            logger.error(f"关闭监控服务失败: {e}")