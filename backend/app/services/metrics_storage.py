"""
指标存储服务
"""
import asyncio
import sqlite3
import aiosqlite
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json
import logging

from ..models.schemas import TimeRange

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """性能指标"""
    model_id: str
    time_range: TimeRange
    avg_response_time: float
    max_response_time: float
    min_response_time: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    requests_per_second: float
    error_rate: float


@dataclass
class MetricsQuery:
    """指标查询"""
    metric_type: str
    time_range: TimeRange
    filters: Optional[Dict[str, Any]] = None
    aggregation: Optional[str] = None
    interval_minutes: Optional[int] = None


class TimeSeriesMetrics:
    """时间序列指标"""
    
    def __init__(self):
        self._data_points: List[Dict[str, Any]] = []
    
    def add_data_point(self, timestamp: datetime, metric_name: str, value: float, tags: Dict[str, Any] = None):
        """添加数据点"""
        self._data_points.append({
            'timestamp': timestamp,
            'metric_name': metric_name,
            'value': value,
            'tags': tags or {}
        })
    
    def get_data_points_in_range(self, metric_name: str, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """获取时间范围内的数据点"""
        return [
            point for point in self._data_points
            if (point['metric_name'] == metric_name and 
                start_time <= point['timestamp'] <= end_time)
        ]
    
    def calculate_average(self, metric_name: str, start_time: datetime, end_time: datetime) -> float:
        """计算平均值"""
        points = self.get_data_points_in_range(metric_name, start_time, end_time)
        if not points:
            return 0.0
        return sum(point['value'] for point in points) / len(points)
    
    def calculate_percentile(self, metric_name: str, start_time: datetime, end_time: datetime, percentile: float) -> float:
        """计算百分位数"""
        points = self.get_data_points_in_range(metric_name, start_time, end_time)
        if not points:
            return 0.0
        
        values = sorted([point['value'] for point in points])
        index = int(len(values) * percentile / 100)
        return values[min(index, len(values) - 1)]
    
    def detect_anomalies(self, metric_name: str, start_time: datetime, end_time: datetime, 
                        threshold_multiplier: float = 2.0) -> List[Dict[str, Any]]:
        """检测异常值"""
        points = self.get_data_points_in_range(metric_name, start_time, end_time)
        if len(points) < 10:  # 需要足够的数据点
            return []
        
        values = [point['value'] for point in points]
        mean_value = statistics.mean(values)
        std_dev = statistics.stdev(values) if len(values) > 1 else 0
        
        anomalies = []
        threshold = std_dev * threshold_multiplier
        
        for point in points:
            if abs(point['value'] - mean_value) > threshold:
                anomalies.append({
                    'timestamp': point['timestamp'],
                    'metric_name': metric_name,
                    'value': point['value'],
                    'expected_range': (mean_value - threshold, mean_value + threshold),
                    'deviation': abs(point['value'] - mean_value)
                })
        
        return anomalies


class SQLiteMetricsStorage:
    """SQLite指标存储"""
    
    def __init__(self, db_path: str = "metrics.db"):
        self._db_path = db_path
        self._connection: Optional[aiosqlite.Connection] = None
    
    async def initialize(self):
        """初始化数据库"""
        self._connection = await aiosqlite.connect(self._db_path)
        await self._create_tables()
    
    async def close(self):
        """关闭数据库连接"""
        if self._connection:
            await self._connection.close()
    
    async def _create_tables(self):
        """创建数据表"""
        # GPU指标表
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS gpu_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                device_id INTEGER NOT NULL,
                utilization REAL NOT NULL,
                memory_used INTEGER NOT NULL,
                memory_total INTEGER NOT NULL,
                temperature REAL NOT NULL,
                power_usage REAL NOT NULL
            )
        """)
        
        # 模型指标表
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS model_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                model_id TEXT NOT NULL,
                status TEXT NOT NULL,
                health TEXT NOT NULL,
                response_time REAL,
                requests_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0
            )
        """)
        
        # 系统指标表
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                cpu_percent REAL NOT NULL,
                memory_percent REAL NOT NULL,
                disk_percent REAL NOT NULL,
                network_bytes_sent INTEGER DEFAULT 0,
                network_bytes_recv INTEGER DEFAULT 0
            )
        """)
        
        await self._connection.commit()
    
    async def _get_connection(self):
        """获取数据库连接"""
        if not self._connection:
            await self.initialize()
        return self._connection
    
    async def store_metrics(self, metrics_data: Dict[str, Any]):
        """存储指标数据"""
        conn = await self._get_connection()
        timestamp = metrics_data.get('timestamp', datetime.now())
        
        # 存储GPU指标
        if 'gpu_metrics' in metrics_data:
            for gpu_metric in metrics_data['gpu_metrics']:
                await conn.execute("""
                    INSERT INTO gpu_metrics 
                    (timestamp, device_id, utilization, memory_used, memory_total, temperature, power_usage)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp,
                    gpu_metric['device_id'],
                    gpu_metric['utilization'],
                    gpu_metric['memory_used'],
                    gpu_metric['memory_total'],
                    gpu_metric['temperature'],
                    gpu_metric['power_usage']
                ))
        
        # 存储模型指标
        if 'model_metrics' in metrics_data:
            for model_metric in metrics_data['model_metrics']:
                await conn.execute("""
                    INSERT INTO model_metrics 
                    (timestamp, model_id, status, health, response_time, requests_count, error_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp,
                    model_metric['model_id'],
                    model_metric['status'],
                    model_metric['health'],
                    model_metric.get('response_time'),
                    model_metric.get('requests_count', 0),
                    model_metric.get('error_count', 0)
                ))
        
        # 存储系统指标
        if 'system_metrics' in metrics_data:
            system_metric = metrics_data['system_metrics']
            await conn.execute("""
                INSERT INTO system_metrics 
                (timestamp, cpu_percent, memory_percent, disk_percent, network_bytes_sent, network_bytes_recv)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                system_metric['cpu_percent'],
                system_metric['memory_percent'],
                system_metric['disk_percent'],
                system_metric.get('network_bytes_sent', 0),
                system_metric.get('network_bytes_recv', 0)
            ))
        
        await conn.commit()
    
    async def query_metrics(self, query: MetricsQuery) -> List[Dict[str, Any]]:
        """查询指标数据"""
        conn = await self._get_connection()
        
        if query.metric_type == "GPU_UTILIZATION":
            sql = """
                SELECT timestamp, device_id, utilization 
                FROM gpu_metrics 
                WHERE timestamp BETWEEN ? AND ?
            """
            params = [query.time_range.start_time, query.time_range.end_time]
            
            if query.filters and 'device_id' in query.filters:
                sql += " AND device_id = ?"
                params.append(query.filters['device_id'])
            
            cursor = await conn.execute(sql, params)
            rows = await cursor.fetchall()
            
            return [
                {
                    'timestamp': row[0],
                    'device_id': row[1],
                    'utilization': row[2]
                }
                for row in rows
            ]
        
        elif query.metric_type == "RESPONSE_TIME":
            sql = """
                SELECT timestamp, model_id, response_time 
                FROM model_metrics 
                WHERE timestamp BETWEEN ? AND ? AND response_time IS NOT NULL
            """
            params = [query.time_range.start_time, query.time_range.end_time]
            
            if query.filters and 'model_id' in query.filters:
                sql += " AND model_id = ?"
                params.append(query.filters['model_id'])
            
            cursor = await conn.execute(sql, params)
            rows = await cursor.fetchall()
            
            return [
                {
                    'timestamp': row[0],
                    'model_id': row[1],
                    'response_time': row[2]
                }
                for row in rows
            ]
        
        elif query.metric_type == "CPU_USAGE":
            sql = """
                SELECT timestamp, cpu_percent 
                FROM system_metrics 
                WHERE timestamp BETWEEN ? AND ?
            """
            params = [query.time_range.start_time, query.time_range.end_time]
            
            cursor = await conn.execute(sql, params)
            rows = await cursor.fetchall()
            
            return [
                {
                    'timestamp': row[0],
                    'cpu_percent': row[1]
                }
                for row in rows
            ]
        
        return []
    
    async def get_performance_metrics(self, model_id: str, time_range: TimeRange) -> PerformanceMetrics:
        """获取性能指标"""
        conn = await self._get_connection()
        
        # 查询模型指标
        cursor = await conn.execute("""
            SELECT response_time, requests_count, error_count
            FROM model_metrics 
            WHERE model_id = ? AND timestamp BETWEEN ? AND ?
            AND response_time IS NOT NULL
        """, (model_id, time_range.start_time, time_range.end_time))
        
        rows = await cursor.fetchall()
        
        if not rows:
            return PerformanceMetrics(
                model_id=model_id,
                time_range=time_range,
                avg_response_time=0.0,
                max_response_time=0.0,
                min_response_time=0.0,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                requests_per_second=0.0,
                error_rate=0.0
            )
        
        response_times = [row[0] for row in rows if row[0] is not None]
        total_requests = sum(row[1] for row in rows)
        total_errors = sum(row[2] for row in rows)
        
        duration_seconds = (time_range.end_time - time_range.start_time).total_seconds()
        
        return PerformanceMetrics(
            model_id=model_id,
            time_range=time_range,
            avg_response_time=sum(response_times) / len(response_times) if response_times else 0.0,
            max_response_time=max(response_times) if response_times else 0.0,
            min_response_time=min(response_times) if response_times else 0.0,
            total_requests=total_requests,
            successful_requests=total_requests - total_errors,
            failed_requests=total_errors,
            requests_per_second=total_requests / duration_seconds if duration_seconds > 0 else 0.0,
            error_rate=total_errors / total_requests if total_requests > 0 else 0.0
        )
    
    async def cleanup_old_metrics(self, days: int = 30):
        """清理旧指标数据"""
        conn = await self._get_connection()
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # 清理各个表的旧数据
        for table in ['gpu_metrics', 'model_metrics', 'system_metrics']:
            await conn.execute(f"DELETE FROM {table} WHERE timestamp < ?", (cutoff_date,))
        
        await conn.commit()
    
    async def export_metrics(self, time_range: TimeRange, format: str = 'json') -> Dict[str, Any]:
        """导出指标数据"""
        conn = await self._get_connection()
        
        # 导出GPU指标
        cursor = await conn.execute("""
            SELECT * FROM gpu_metrics 
            WHERE timestamp BETWEEN ? AND ?
            ORDER BY timestamp
        """, (time_range.start_time, time_range.end_time))
        gpu_metrics = await cursor.fetchall()
        
        # 导出模型指标
        cursor = await conn.execute("""
            SELECT * FROM model_metrics 
            WHERE timestamp BETWEEN ? AND ?
            ORDER BY timestamp
        """, (time_range.start_time, time_range.end_time))
        model_metrics = await cursor.fetchall()
        
        # 导出系统指标
        cursor = await conn.execute("""
            SELECT * FROM system_metrics 
            WHERE timestamp BETWEEN ? AND ?
            ORDER BY timestamp
        """, (time_range.start_time, time_range.end_time))
        system_metrics = await cursor.fetchall()
        
        return {
            'time_range': time_range,
            'gpu_metrics': gpu_metrics,
            'model_metrics': model_metrics,
            'system_metrics': system_metrics
        }
    
    async def get_metrics_summary(self, time_range: TimeRange) -> Dict[str, Any]:
        """获取指标摘要"""
        conn = await self._get_connection()
        
        # GPU摘要
        cursor = await conn.execute("""
            SELECT 
                AVG(utilization) as avg_utilization,
                MAX(temperature) as max_temperature,
                SUM(memory_used) as total_memory_used
            FROM gpu_metrics 
            WHERE timestamp BETWEEN ? AND ?
        """, (time_range.start_time, time_range.end_time))
        gpu_summary = await cursor.fetchone()
        
        # 模型摘要
        cursor = await conn.execute("""
            SELECT 
                SUM(requests_count) as total_requests,
                AVG(response_time) as avg_response_time,
                SUM(error_count) as total_errors
            FROM model_metrics 
            WHERE timestamp BETWEEN ? AND ?
        """, (time_range.start_time, time_range.end_time))
        model_summary = await cursor.fetchone()
        
        # 系统摘要
        cursor = await conn.execute("""
            SELECT 
                AVG(cpu_percent) as avg_cpu,
                AVG(memory_percent) as avg_memory,
                AVG(disk_percent) as avg_disk
            FROM system_metrics 
            WHERE timestamp BETWEEN ? AND ?
        """, (time_range.start_time, time_range.end_time))
        system_summary = await cursor.fetchone()
        
        return {
            'gpu_summary': {
                'avg_utilization': gpu_summary[0] or 0.0,
                'max_temperature': gpu_summary[1] or 0.0,
                'total_memory_used': gpu_summary[2] or 0
            },
            'model_summary': {
                'total_requests': model_summary[0] or 0,
                'avg_response_time': model_summary[1] or 0.0,
                'error_rate': (model_summary[2] or 0) / (model_summary[0] or 1)
            },
            'system_summary': {
                'avg_cpu': system_summary[0] or 0.0,
                'avg_memory': system_summary[1] or 0.0,
                'avg_disk': system_summary[2] or 0.0
            }
        }


class MetricsStorageService:
    """指标存储服务"""
    
    def __init__(self, storage_backend: Optional[SQLiteMetricsStorage] = None):
        self._storage = storage_backend or SQLiteMetricsStorage()
        self._initialized = False
        self._cache: Dict[str, Any] = {}
    
    async def initialize(self):
        """初始化服务"""
        await self._storage.initialize()
        self._initialized = True
    
    async def store_metrics_batch(self, metrics_batch: List[Dict[str, Any]]):
        """批量存储指标"""
        if not self._initialized:
            await self.initialize()
        
        for metrics_data in metrics_batch:
            await self._storage.store_metrics(metrics_data)
    
    async def query_metrics(self, query: MetricsQuery) -> List[Dict[str, Any]]:
        """查询指标"""
        if not self._initialized:
            await self.initialize()
        
        return await self._storage.query_metrics(query)
    
    async def get_real_time_metrics(self) -> Dict[str, Any]:
        """获取实时指标"""
        if not self._initialized:
            await self.initialize()
        
        # 获取最近5分钟的指标
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=5)
        time_range = TimeRange(start_time=start_time, end_time=end_time)
        
        # 查询各类指标
        gpu_query = MetricsQuery(metric_type="GPU_UTILIZATION", time_range=time_range)
        model_query = MetricsQuery(metric_type="RESPONSE_TIME", time_range=time_range)
        system_query = MetricsQuery(metric_type="CPU_USAGE", time_range=time_range)
        
        gpu_metrics = await self.query_metrics(gpu_query)
        model_metrics = await self.query_metrics(model_query)
        system_metrics = await self.query_metrics(system_query)
        
        return {
            'timestamp': end_time,
            'gpu_metrics': gpu_metrics,
            'model_metrics': model_metrics,
            'system_metrics': system_metrics
        }
    
    async def calculate_trends(self, metric_type: str, time_range: TimeRange) -> Dict[str, Any]:
        """计算趋势"""
        query = MetricsQuery(metric_type=metric_type, time_range=time_range)
        data = await self.query_metrics(query)
        
        if len(data) < 2:
            return {
                'trend_direction': 'stable',
                'trend_rate': 0.0,
                'prediction': None
            }
        
        # 简单的线性趋势计算
        values = []
        if metric_type == "GPU_UTILIZATION":
            values = [point['utilization'] for point in data]
        elif metric_type == "RESPONSE_TIME":
            values = [point['response_time'] for point in data]
        elif metric_type == "CPU_USAGE":
            values = [point['cpu_percent'] for point in data]
        
        if not values:
            return {
                'trend_direction': 'stable',
                'trend_rate': 0.0,
                'prediction': None
            }
        
        # 计算趋势
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        trend_rate = (second_avg - first_avg) / first_avg if first_avg != 0 else 0.0
        
        if trend_rate > 0.05:
            trend_direction = 'increasing'
        elif trend_rate < -0.05:
            trend_direction = 'decreasing'
        else:
            trend_direction = 'stable'
        
        return {
            'trend_direction': trend_direction,
            'trend_rate': trend_rate,
            'prediction': second_avg + (second_avg - first_avg)  # 简单预测
        }
    
    async def generate_alerts_from_metrics(self, current_metrics: Dict[str, Any], 
                                         alert_thresholds: Dict[str, float]) -> List[Dict[str, Any]]:
        """从指标生成告警"""
        alerts = []
        
        # 检查GPU指标
        if 'gpu_metrics' in current_metrics:
            for gpu_metric in current_metrics['gpu_metrics']:
                if gpu_metric['utilization'] > alert_thresholds.get('gpu_utilization_high', 90.0):
                    alerts.append({
                        'type': 'gpu_utilization_high',
                        'message': f"GPU {gpu_metric['device_id']} 使用率过高: {gpu_metric['utilization']:.1f}%",
                        'severity': 'warning',
                        'timestamp': datetime.now()
                    })
                
                if gpu_metric['temperature'] > alert_thresholds.get('gpu_temperature_high', 80.0):
                    alerts.append({
                        'type': 'gpu_temperature_high',
                        'message': f"GPU {gpu_metric['device_id']} 温度过高: {gpu_metric['temperature']:.1f}°C",
                        'severity': 'critical',
                        'timestamp': datetime.now()
                    })
        
        # 检查模型指标
        if 'model_metrics' in current_metrics:
            for model_metric in current_metrics['model_metrics']:
                if model_metric.get('response_time', 0) > alert_thresholds.get('response_time_high', 2.0):
                    alerts.append({
                        'type': 'response_time_high',
                        'message': f"模型 {model_metric['model_id']} 响应时间过长: {model_metric['response_time']:.2f}s",
                        'severity': 'warning',
                        'timestamp': datetime.now()
                    })
                
                if model_metric.get('error_count', 0) > alert_thresholds.get('error_count_high', 5):
                    alerts.append({
                        'type': 'error_count_high',
                        'message': f"模型 {model_metric['model_id']} 错误数过多: {model_metric['error_count']}",
                        'severity': 'critical',
                        'timestamp': datetime.now()
                    })
        
        return alerts