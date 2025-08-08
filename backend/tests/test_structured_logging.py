"""
结构化日志系统测试
"""
import json
import tempfile
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch

from app.utils.logging import (
    setup_structured_logging, 
    get_structured_logger, 
    EventType,
    LogLevel,
    StructuredFormatter
)
from app.utils.log_analyzer import LogAnalyzer, LogEntry


class TestStructuredLogging:
    """结构化日志系统测试类"""
    
    def test_structured_formatter(self):
        """测试结构化格式器"""
        import logging
        
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="测试消息",
            args=(),
            exc_info=None
        )
        
        # 添加额外属性
        record.event_type = EventType.MODEL_LIFECYCLE.value
        record.model_id = "test_model"
        record.gpu_id = 0
        
        formatted = formatter.format(record)
        data = json.loads(formatted)
        
        assert data["level"] == "INFO"
        assert data["message"] == "测试消息"
        assert data["event_type"] == EventType.MODEL_LIFECYCLE.value
        assert data["model_id"] == "test_model"
        assert data["gpu_id"] == 0
        assert "timestamp" in data
    
    def test_structured_logger_basic_logging(self):
        """测试结构化日志器基本功能"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_structured_logging(
                log_dir=temp_dir,
                log_level="DEBUG",
                enable_console=False
            )
            
            logger = get_structured_logger("test_logger")
            
            # 测试不同级别的日志
            logger.debug("调试消息")
            logger.info("信息消息")
            logger.warning("警告消息")
            logger.error("错误消息")
            
            # 检查日志文件是否创建
            log_file = Path(temp_dir) / "application.log"
            assert log_file.exists()
            
            # 检查日志内容
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                assert len(lines) >= 4
                
                # 检查每行都是有效的JSON
                for line in lines:
                    data = json.loads(line.strip())
                    assert "timestamp" in data
                    assert "level" in data
                    assert "message" in data
    
    def test_model_event_logging(self):
        """测试模型事件日志"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_structured_logging(
                log_dir=temp_dir,
                enable_console=False
            )
            
            logger = get_structured_logger("test_logger")
            
            # 记录模型事件
            logger.log_model_event(
                event="start",
                model_id="test_model_1",
                status="running",
                extra_data={"gpu_id": 0, "memory_usage": "2GB"}
            )
            
            # 检查模型事件日志文件
            model_log_file = Path(temp_dir) / "model_events.log"
            assert model_log_file.exists()
            
            with open(model_log_file, 'r', encoding='utf-8') as f:
                line = f.readline().strip()
                data = json.loads(line)
                
                assert data["event_type"] == EventType.MODEL_LIFECYCLE.value
                assert data["model_id"] == "test_model_1"
                assert data["extra_data"]["event"] == "start"
                assert data["extra_data"]["status"] == "running"
    
    def test_resource_event_logging(self):
        """测试资源事件日志"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_structured_logging(
                log_dir=temp_dir,
                enable_console=False
            )
            
            logger = get_structured_logger("test_logger")
            
            # 记录资源事件
            logger.log_resource_event(
                event="allocation",
                gpu_id=1,
                extra_data={"memory_allocated": "4GB", "model_id": "test_model"}
            )
            
            # 检查日志内容
            log_file = Path(temp_dir) / "application.log"
            with open(log_file, 'r', encoding='utf-8') as f:
                line = f.readline().strip()
                data = json.loads(line)
                
                assert data["event_type"] == EventType.RESOURCE_ALLOCATION.value
                assert data["gpu_id"] == 1
                assert data["extra_data"]["event"] == "allocation"
    
    def test_api_request_logging(self):
        """测试API请求日志"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_structured_logging(
                log_dir=temp_dir,
                enable_console=False
            )
            
            logger = get_structured_logger("test_logger")
            
            # 记录API请求
            logger.log_api_request(
                method="POST",
                path="/api/models",
                status_code=201,
                duration=0.5,
                request_id="req_123",
                user_id="user_456"
            )
            
            # 检查日志内容
            log_file = Path(temp_dir) / "application.log"
            with open(log_file, 'r', encoding='utf-8') as f:
                line = f.readline().strip()
                data = json.loads(line)
                
                assert data["event_type"] == EventType.API_REQUEST.value
                assert data["request_id"] == "req_123"
                assert data["user_id"] == "user_456"
                assert data["extra_data"]["method"] == "POST"
                assert data["extra_data"]["status_code"] == 201
    
    def test_error_logging_with_exception(self):
        """测试异常错误日志"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_structured_logging(
                log_dir=temp_dir,
                enable_console=False
            )
            
            logger = get_structured_logger("test_logger")
            
            # 模拟异常
            try:
                raise ValueError("测试异常")
            except ValueError:
                logger.error("发生了测试异常", model_id="test_model")
            
            # 检查错误日志文件
            error_log_file = Path(temp_dir) / "error.log"
            assert error_log_file.exists()
            
            with open(error_log_file, 'r', encoding='utf-8') as f:
                line = f.readline().strip()
                data = json.loads(line)
                
                assert data["level"] == "ERROR"
                assert data["model_id"] == "test_model"
                assert "exception" in data
                assert data["exception"]["type"] == "ValueError"
                assert data["exception"]["message"] == "测试异常"


class TestLogAnalyzer:
    """日志分析器测试类"""
    
    def test_parse_json_log_line(self):
        """测试解析JSON格式日志行"""
        analyzer = LogAnalyzer()
        
        log_line = json.dumps({
            "timestamp": "2024-01-01T12:00:00",
            "level": "INFO",
            "logger": "test_logger",
            "message": "测试消息",
            "event_type": "model_lifecycle",
            "model_id": "test_model",
            "gpu_id": 0
        })
        
        entry = analyzer.parse_log_line(log_line)
        
        assert entry is not None
        assert entry.level == "INFO"
        assert entry.message == "测试消息"
        assert entry.event_type == "model_lifecycle"
        assert entry.model_id == "test_model"
        assert entry.gpu_id == 0
    
    def test_parse_traditional_log_line(self):
        """测试解析传统格式日志行"""
        analyzer = LogAnalyzer()
        
        log_line = "2024-01-01 12:00:00 - test_logger - INFO - 测试消息"
        entry = analyzer.parse_log_line(log_line)
        
        assert entry is not None
        assert entry.level == "INFO"
        assert entry.message == "测试消息"
        assert entry.logger == "test_logger"
    
    def test_read_logs_with_filters(self):
        """测试带过滤条件的日志读取"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试日志文件
            log_file = Path(temp_dir) / "test.log"
            
            test_logs = [
                {
                    "timestamp": "2024-01-01T10:00:00",
                    "level": "INFO",
                    "logger": "test",
                    "message": "消息1",
                    "model_id": "model1"
                },
                {
                    "timestamp": "2024-01-01T11:00:00",
                    "level": "ERROR",
                    "logger": "test",
                    "message": "消息2",
                    "model_id": "model2"
                },
                {
                    "timestamp": "2024-01-01T12:00:00",
                    "level": "INFO",
                    "logger": "test",
                    "message": "消息3",
                    "model_id": "model1"
                }
            ]
            
            with open(log_file, 'w', encoding='utf-8') as f:
                for log in test_logs:
                    f.write(json.dumps(log) + '\n')
            
            analyzer = LogAnalyzer(temp_dir)
            
            # 测试级别过滤
            error_entries = analyzer.read_logs("test.log", level_filter="ERROR")
            assert len(error_entries) == 1
            assert error_entries[0].message == "消息2"
            
            # 测试模型ID过滤
            model1_entries = analyzer.read_logs("test.log", model_id_filter="model1")
            assert len(model1_entries) == 2
            
            # 测试限制数量
            limited_entries = analyzer.read_logs("test.log", limit=2)
            assert len(limited_entries) == 2
    
    def test_get_error_summary(self):
        """测试错误摘要统计"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建错误日志文件
            error_log_file = Path(temp_dir) / "error.log"
            
            test_errors = [
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": "ERROR",
                    "logger": "test",
                    "message": "错误1",
                    "model_id": "model1",
                    "exception": {"type": "ValueError", "message": "值错误"}
                },
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": "ERROR",
                    "logger": "test",
                    "message": "错误2",
                    "model_id": "model1",
                    "exception": {"type": "RuntimeError", "message": "运行时错误"}
                }
            ]
            
            with open(error_log_file, 'w', encoding='utf-8') as f:
                for error in test_errors:
                    f.write(json.dumps(error) + '\n')
            
            analyzer = LogAnalyzer(temp_dir)
            summary = analyzer.get_error_summary(hours=24)
            
            assert summary["total_errors"] == 2
            assert summary["error_types"]["ValueError"] == 1
            assert summary["error_types"]["RuntimeError"] == 1
            assert summary["error_models"]["model1"] == 2
            assert len(summary["recent_errors"]) == 2


if __name__ == "__main__":
    pytest.main([__file__])