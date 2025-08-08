"""
日志分析工具
提供日志查询、统计和分析功能
"""
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

@dataclass
class LogEntry:
    """日志条目数据类"""
    timestamp: datetime
    level: str
    logger: str
    message: str
    event_type: Optional[str] = None
    model_id: Optional[str] = None
    gpu_id: Optional[int] = None
    request_id: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None
    exception: Optional[Dict[str, Any]] = None

class LogAnalyzer:
    """日志分析器"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
    
    def parse_log_line(self, line: str) -> Optional[LogEntry]:
        """解析单行日志"""
        try:
            # 尝试解析JSON格式日志
            data = json.loads(line.strip())
            return LogEntry(
                timestamp=datetime.fromisoformat(data["timestamp"]),
                level=data["level"],
                logger=data["logger"],
                message=data["message"],
                event_type=data.get("event_type"),
                model_id=data.get("model_id"),
                gpu_id=data.get("gpu_id"),
                request_id=data.get("request_id"),
                extra_data=data.get("extra_data"),
                exception=data.get("exception")
            )
        except (json.JSONDecodeError, KeyError):
            # 尝试解析传统格式日志
            pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - (.*?) - (.*?) - (.*)'
            match = re.match(pattern, line.strip())
            if match:
                timestamp_str, logger, level, message = match.groups()
                return LogEntry(
                    timestamp=datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S'),
                    level=level,
                    logger=logger,
                    message=message
                )
        return None
    
    def read_logs(self, log_file: str, 
                  start_time: Optional[datetime] = None,
                  end_time: Optional[datetime] = None,
                  level_filter: Optional[str] = None,
                  event_type_filter: Optional[str] = None,
                  model_id_filter: Optional[str] = None,
                  limit: Optional[int] = None) -> List[LogEntry]:
        """读取和过滤日志"""
        log_path = self.log_dir / log_file
        if not log_path.exists():
            return []
        
        entries = []
        count = 0
        
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if limit and count >= limit:
                        break
                        
                    entry = self.parse_log_line(line)
                    if not entry:
                        continue
                    
                    # 应用过滤条件
                    if start_time and entry.timestamp < start_time:
                        continue
                    if end_time and entry.timestamp > end_time:
                        continue
                    if level_filter and entry.level != level_filter:
                        continue
                    if event_type_filter and entry.event_type != event_type_filter:
                        continue
                    if model_id_filter and entry.model_id != model_id_filter:
                        continue
                    
                    entries.append(entry)
                    count += 1
                    
        except Exception as e:
            print(f"读取日志文件失败: {e}")
        
        return entries
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取错误摘要统计"""
        start_time = datetime.now() - timedelta(hours=hours)
        error_entries = self.read_logs(
            "error.log",
            start_time=start_time,
            level_filter="ERROR"
        )
        
        # 统计错误类型
        error_types = {}
        error_models = {}
        
        for entry in error_entries:
            # 统计异常类型
            if entry.exception:
                error_type = entry.exception.get("type", "Unknown")
                error_types[error_type] = error_types.get(error_type, 0) + 1
            
            # 统计模型错误
            if entry.model_id:
                error_models[entry.model_id] = error_models.get(entry.model_id, 0) + 1
        
        return {
            "total_errors": len(error_entries),
            "error_types": error_types,
            "error_models": error_models,
            "recent_errors": [
                {
                    "timestamp": entry.timestamp.isoformat(),
                    "message": entry.message,
                    "model_id": entry.model_id,
                    "exception_type": entry.exception.get("type") if entry.exception else None
                }
                for entry in error_entries[-10:]  # 最近10个错误
            ]
        }
    
    def get_model_activity_summary(self, model_id: str, hours: int = 24) -> Dict[str, Any]:
        """获取模型活动摘要"""
        start_time = datetime.now() - timedelta(hours=hours)
        model_entries = self.read_logs(
            "model_events.log",
            start_time=start_time,
            model_id_filter=model_id
        )
        
        # 统计事件类型
        events = {}
        timeline = []
        
        for entry in model_entries:
            if entry.extra_data and "event" in entry.extra_data:
                event = entry.extra_data["event"]
                events[event] = events.get(event, 0) + 1
                
                timeline.append({
                    "timestamp": entry.timestamp.isoformat(),
                    "event": event,
                    "status": entry.extra_data.get("status"),
                    "message": entry.message
                })
        
        return {
            "model_id": model_id,
            "total_events": len(model_entries),
            "event_counts": events,
            "timeline": sorted(timeline, key=lambda x: x["timestamp"])
        }
    
    def get_api_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取API性能摘要"""
        start_time = datetime.now() - timedelta(hours=hours)
        api_entries = self.read_logs(
            "application.log",
            start_time=start_time,
            event_type_filter="api_request"
        )
        
        # 统计API性能
        endpoints = {}
        total_requests = 0
        total_duration = 0
        status_codes = {}
        
        for entry in api_entries:
            if entry.extra_data:
                path = entry.extra_data.get("path", "unknown")
                duration = entry.extra_data.get("duration_ms", 0)
                status_code = entry.extra_data.get("status_code", 0)
                
                if path not in endpoints:
                    endpoints[path] = {
                        "count": 0,
                        "total_duration": 0,
                        "avg_duration": 0,
                        "max_duration": 0,
                        "min_duration": float('inf')
                    }
                
                endpoints[path]["count"] += 1
                endpoints[path]["total_duration"] += duration
                endpoints[path]["max_duration"] = max(endpoints[path]["max_duration"], duration)
                endpoints[path]["min_duration"] = min(endpoints[path]["min_duration"], duration)
                
                total_requests += 1
                total_duration += duration
                
                status_codes[status_code] = status_codes.get(status_code, 0) + 1
        
        # 计算平均响应时间
        for endpoint in endpoints.values():
            if endpoint["count"] > 0:
                endpoint["avg_duration"] = endpoint["total_duration"] / endpoint["count"]
                if endpoint["min_duration"] == float('inf'):
                    endpoint["min_duration"] = 0
        
        return {
            "total_requests": total_requests,
            "avg_response_time": total_duration / total_requests if total_requests > 0 else 0,
            "status_codes": status_codes,
            "endpoints": endpoints
        }
    
    def cleanup_old_logs(self, days: int = 30):
        """清理旧日志文件"""
        cutoff_date = datetime.now() - timedelta(days=days)
        cleaned_files = []
        
        for log_file in self.log_dir.glob("*.log*"):
            try:
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    log_file.unlink()
                    cleaned_files.append(str(log_file))
            except Exception as e:
                print(f"清理日志文件失败 {log_file}: {e}")
        
        return cleaned_files
    
    def get_log_files_info(self) -> List[Dict[str, Any]]:
        """获取日志文件信息"""
        files_info = []
        
        for log_file in self.log_dir.glob("*.log*"):
            try:
                stat = log_file.stat()
                files_info.append({
                    "name": log_file.name,
                    "size_mb": stat.st_size / (1024 * 1024),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "path": str(log_file)
                })
            except Exception as e:
                print(f"获取日志文件信息失败 {log_file}: {e}")
        
        return sorted(files_info, key=lambda x: x["modified"], reverse=True)