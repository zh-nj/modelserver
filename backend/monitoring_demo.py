#!/usr/bin/env python3
"""
监控和指标收集系统演示
展示完整的监控数据收集、存储和查询功能
"""
import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from app.services.monitoring import MonitoringService
from app.services.config_manager import FileConfigManager
from app.services.model_manager import ModelManager
from app.utils.gpu import GPUDetector
from app.models.schemas import TimeRange

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def monitoring_demo():
    """监控系统完整演示"""
    try:
        logger.info("=== 监控和指标收集系统演示 ===")
        
        # 初始化服务
        logger.info("1. 初始化服务...")
        gpu_detector = GPUDetector()
        config_manager = FileConfigManager()
        await config_manager.initialize()
        
        model_manager = ModelManager(config_manager)
        await model_manager.initialize()
        
        monitoring_service = MonitoringService(model_manager, gpu_detector)
        await monitoring_service.initialize()
        
        # 启动监控服务
        logger.info("2. 启动监控服务...")
        await monitoring_service.start_monitoring()
        
        # 模拟一些请求数据
        logger.info("3. 模拟模型请求数据...")
        for i in range(20):
            # 模拟不同的响应时间和成功率
            response_time = 100 + i * 10  # 100-290ms
            success = i % 5 != 0  # 80%成功率
            monitoring_service.record_model_request("demo_model", response_time, success)
            await asyncio.sleep(0.1)
        
        # 让监控服务运行一段时间收集数据
        logger.info("4. 收集监控数据中...")
        await asyncio.sleep(15)
        
        # 展示收集到的数据
        logger.info("5. 展示收集到的数据...")
        
        # GPU指标
        gpu_metrics = await monitoring_service.collect_gpu_metrics()
        logger.info(f"当前GPU指标: {len(gpu_metrics)} 个GPU")
        for metric in gpu_metrics:
            logger.info(f"  GPU {metric.device_id}: 利用率={metric.utilization}%, "
                       f"内存={metric.memory_used}/{metric.memory_total}MB, "
                       f"温度={metric.temperature}°C")
        
        # 系统概览
        system_overview = await monitoring_service.get_system_overview()
        logger.info(f"系统概览: 模型={system_overview.total_models}, "
                   f"GPU={system_overview.total_gpus}, "
                   f"运行时间={system_overview.system_uptime}秒")
        
        # 系统资源指标
        system_metrics = await monitoring_service.system_collector.collect_metrics()
        logger.info(f"系统资源: CPU={system_metrics.cpu_usage}%, "
                   f"内存={system_metrics.memory_usage}%, "
                   f"磁盘={system_metrics.disk_usage}%")
        
        # 查询历史数据
        logger.info("6. 查询历史数据...")
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=5)
        time_range = TimeRange(start_time=start_time, end_time=end_time)
        
        # GPU历史数据
        gpu_history = await monitoring_service.get_gpu_metrics_history(
            device_id=0, time_range=time_range, limit=10
        )
        logger.info(f"GPU历史数据: {len(gpu_history)} 条记录")
        
        # 系统资源历史数据
        system_history = await monitoring_service.get_system_metrics_history(
            time_range=time_range, limit=10
        )
        logger.info(f"系统资源历史数据: {len(system_history)} 条记录")
        
        # 数据聚合和趋势分析
        logger.info("7. 数据聚合和趋势分析...")
        
        # GPU利用率趋势
        gpu_trend = await monitoring_service.get_gpu_utilization_trend(
            device_id=0, time_range=time_range, interval_minutes=1
        )
        logger.info(f"GPU利用率趋势: {len(gpu_trend)} 个数据点")
        for point in gpu_trend[:3]:  # 显示前3个数据点
            logger.info(f"  时间: {point['timestamp']}, "
                       f"平均利用率: {point['avg_utilization']}%, "
                       f"最高利用率: {point['max_utilization']}%")
        
        # 系统资源趋势
        system_trend = await monitoring_service.get_system_resource_trend(
            time_range=time_range, interval_minutes=1
        )
        logger.info(f"系统资源趋势: {len(system_trend)} 个数据点")
        for point in system_trend[:3]:  # 显示前3个数据点
            logger.info(f"  时间: {point['timestamp']}, "
                       f"CPU: {point['avg_cpu_usage']}%, "
                       f"内存: {point['avg_memory_usage']}%")
        
        # 存储统计信息
        logger.info("8. 存储统计信息...")
        storage_stats = await monitoring_service.get_storage_stats()
        logger.info(f"数据库大小: {storage_stats.get('db_size_mb', 0)} MB")
        logger.info(f"GPU指标记录数: {storage_stats.get('gpu_metrics_count', 0)}")
        logger.info(f"系统指标记录数: {storage_stats.get('system_metrics_count', 0)}")
        
        # 告警状态
        logger.info("9. 告警状态...")
        active_alerts = monitoring_service.get_active_alerts()
        logger.info(f"活跃告警: {len(active_alerts)} 个")
        
        alert_history = monitoring_service.get_alert_history(limit=5)
        logger.info(f"告警历史: {len(alert_history)} 个")
        
        # 停止监控服务
        logger.info("10. 停止监控服务...")
        await monitoring_service.stop_monitoring()
        
        # 关闭服务
        await monitoring_service.shutdown()
        await model_manager.shutdown()
        
        logger.info("=== 监控系统演示完成 ===")
        
    except Exception as e:
        logger.error(f"监控系统演示失败: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(monitoring_demo())