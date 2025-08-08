"""
告警系统测试
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.alerting import (
    AlertingService, Alert, AlertCondition, AlertSeverity, AlertStatus,
    EmailNotificationSender, WebhookNotificationSender, SlackNotificationSender
)
from app.models.schemas import AlertRuleCreate, AlertConditionSchema, NotificationConfig


class TestAlertCondition:
    """告警条件测试类"""
    
    def test_evaluate_greater_than(self):
        """测试大于条件"""
        condition = AlertCondition(
            metric="cpu_usage",
            operator=">",
            threshold=80.0,
            duration=60
        )
        
        # 满足条件
        assert condition.evaluate(85.0, 60) == True
        assert condition.evaluate(90.0, 120) == True
        
        # 不满足条件
        assert condition.evaluate(75.0, 60) == False
        assert condition.evaluate(85.0, 30) == False  # 持续时间不够
    
    def test_evaluate_less_than(self):
        """测试小于条件"""
        condition = AlertCondition(
            metric="memory_free",
            operator="<",
            threshold=1000.0,
            duration=30
        )
        
        # 满足条件
        assert condition.evaluate(500.0, 30) == True
        assert condition.evaluate(800.0, 60) == True
        
        # 不满足条件
        assert condition.evaluate(1200.0, 30) == False
        assert condition.evaluate(500.0, 15) == False
    
    def test_evaluate_equal(self):
        """测试等于条件"""
        condition = AlertCondition(
            metric="model_count",
            operator="==",
            threshold=0.0,
            duration=10
        )
        
        assert condition.evaluate(0.0, 10) == True
        assert condition.evaluate(1.0, 10) == False


class TestNotificationSenders:
    """通知发送器测试类"""
    
    @pytest.mark.asyncio
    async def test_email_notification_sender(self):
        """测试邮件通知发送器"""
        sender = EmailNotificationSender()
        
        alert = Alert(
            id="test_alert",
            rule_id="test_rule",
            rule_name="测试规则",
            severity=AlertSeverity.HIGH,
            message="测试告警消息",
            labels={"env": "test"},
            annotations={"description": "测试描述"},
            starts_at=datetime.now()
        )
        
        config = {
            "smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "username": "test@example.com",
            "password": "password",
            "from_email": "alerts@example.com",
            "to_emails": ["admin@example.com"]
        }
        
        # 模拟SMTP服务器
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            result = await sender.send(alert, config)
            
            assert result == True
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with("test@example.com", "password")
            mock_server.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_webhook_notification_sender(self):
        """测试Webhook通知发送器"""
        sender = WebhookNotificationSender()
        
        alert = Alert(
            id="test_alert",
            rule_id="test_rule", 
            rule_name="测试规则",
            severity=AlertSeverity.CRITICAL,
            message="测试告警消息",
            labels={},
            annotations={},
            starts_at=datetime.now()
        )
        
        config = {
            "url": "https://webhook.example.com/alerts",
            "headers": {"Authorization": "Bearer token"},
            "timeout": 30
        }
        
        # 模拟HTTP响应
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await sender.send(alert, config)
            
            assert result == True
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_slack_notification_sender(self):
        """测试Slack通知发送器"""
        sender = SlackNotificationSender()
        
        alert = Alert(
            id="test_alert",
            rule_id="test_rule",
            rule_name="测试规则",
            severity=AlertSeverity.MEDIUM,
            message="测试告警消息",
            labels={},
            annotations={},
            starts_at=datetime.now()
        )
        
        config = {
            "webhook_url": "https://hooks.slack.com/services/xxx",
            "channel": "#alerts",
            "username": "Alert Bot"
        }
        
        # 模拟Slack响应
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await sender.send(alert, config)
            
            assert result == True
            mock_post.assert_called_once()


class TestAlertingService:
    """告警服务测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.alerting_service = AlertingService()
    
    @pytest.mark.asyncio
    async def test_create_alert_rule(self):
        """测试创建告警规则"""
        mock_db = MagicMock()
        
        rule_data = AlertRuleCreate(
            name="CPU使用率告警",
            description="CPU使用率过高告警",
            condition=AlertConditionSchema(
                metric="cpu_usage",
                operator=">",
                threshold=80.0,
                duration=300
            ),
            severity="high",
            enabled=True,
            notification_channels=["email"],
            notification_config=NotificationConfig(
                email={"to_emails": ["admin@example.com"]}
            )
        )
        
        # 模拟数据库操作
        mock_rule = MagicMock()
        mock_rule.id = "rule_123"
        mock_rule.name = rule_data.name
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        with patch('app.models.database.AlertRule', return_value=mock_rule):
            result = await self.alerting_service.create_alert_rule(rule_data, mock_db)
            
            assert result == mock_rule
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_evaluate_metrics_trigger_alert(self):
        """测试指标评估触发告警"""
        mock_db = MagicMock()
        
        # 创建模拟告警规则
        mock_rule = MagicMock()
        mock_rule.id = "rule_123"
        mock_rule.name = "CPU告警"
        mock_rule.condition = {
            "metric": "cpu_usage",
            "operator": ">",
            "threshold": 80.0,
            "duration": 60
        }
        mock_rule.severity = "high"
        mock_rule.enabled = True
        mock_rule.labels = {}
        mock_rule.annotations = {}
        mock_rule.notification_channels = ["email"]
        mock_rule.notification_config = {"email": {"to_emails": ["admin@example.com"]}}
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_rule]
        
        # 设置指标历史数据
        current_time = datetime.now()
        self.alerting_service.metric_history["cpu_usage"] = [
            (current_time - timedelta(seconds=120), 85.0),
            (current_time - timedelta(seconds=60), 90.0),
            (current_time, 95.0)
        ]
        
        # 模拟通知发送
        with patch.object(self.alerting_service, '_send_notifications') as mock_send:
            with patch.object(self.alerting_service, '_save_alert_history') as mock_save:
                await self.alerting_service.evaluate_metrics({"cpu_usage": 95.0}, mock_db)
                
                # 验证告警被触发
                assert len(self.alerting_service.active_alerts) == 1
                mock_send.assert_called_once()
                mock_save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_evaluate_metrics_resolve_alert(self):
        """测试指标评估解决告警"""
        mock_db = MagicMock()
        
        # 创建模拟告警规则
        mock_rule = MagicMock()
        mock_rule.id = "rule_123"
        mock_rule.name = "CPU告警"
        mock_rule.condition = {
            "metric": "cpu_usage",
            "operator": ">",
            "threshold": 80.0,
            "duration": 60
        }
        mock_rule.severity = "high"
        mock_rule.enabled = True
        mock_rule.labels = {}
        mock_rule.annotations = {}
        mock_rule.notification_channels = ["email"]
        mock_rule.notification_config = {"email": {"to_emails": ["admin@example.com"]}}
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_rule]
        
        # 添加活跃告警
        alert_key = f"{mock_rule.id}_cpu_usage"
        active_alert = Alert(
            id="alert_123",
            rule_id=mock_rule.id,
            rule_name=mock_rule.name,
            severity=AlertSeverity.HIGH,
            message="CPU使用率过高",
            labels={},
            annotations={},
            starts_at=datetime.now() - timedelta(minutes=5)
        )
        self.alerting_service.active_alerts[alert_key] = active_alert
        
        # 模拟通知发送和历史更新
        with patch.object(self.alerting_service, '_send_notifications') as mock_send:
            with patch.object(self.alerting_service, '_update_alert_history') as mock_update:
                await self.alerting_service.evaluate_metrics({"cpu_usage": 70.0}, mock_db)
                
                # 验证告警被解决
                assert alert_key not in self.alerting_service.active_alerts
                assert active_alert.status == AlertStatus.RESOLVED
                mock_send.assert_called_once()
                mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_suppress_alert(self):
        """测试抑制告警"""
        # 添加活跃告警
        alert = Alert(
            id="alert_123",
            rule_id="rule_123",
            rule_name="测试规则",
            severity=AlertSeverity.HIGH,
            message="测试告警",
            labels={},
            annotations={},
            starts_at=datetime.now()
        )
        
        alert_key = "rule_123_cpu_usage"
        self.alerting_service.active_alerts[alert_key] = alert
        
        # 抑制告警
        result = await self.alerting_service.suppress_alert("alert_123", 30)
        
        assert result == True
        assert alert.status == AlertStatus.SUPPRESSED
    
    def test_calculate_metric_duration(self):
        """测试指标持续时间计算"""
        current_time = datetime.now()
        
        # 设置指标历史
        self.alerting_service.metric_history["cpu_usage"] = [
            (current_time - timedelta(seconds=180), 85.0),
            (current_time - timedelta(seconds=120), 90.0),
            (current_time - timedelta(seconds=60), 95.0),
            (current_time, 88.0)
        ]
        
        condition = AlertCondition(
            metric="cpu_usage",
            operator=">",
            threshold=80.0,
            duration=60
        )
        
        duration = self.alerting_service._calculate_metric_duration(
            "cpu_usage", condition, current_time
        )
        
        # 应该返回从最新时间开始连续满足条件的时间
        assert duration >= 0
    
    @pytest.mark.asyncio
    async def test_get_active_alerts(self):
        """测试获取活跃告警"""
        # 添加测试告警
        alert1 = Alert(
            id="alert_1",
            rule_id="rule_1",
            rule_name="规则1",
            severity=AlertSeverity.HIGH,
            message="告警1",
            labels={},
            annotations={},
            starts_at=datetime.now()
        )
        
        alert2 = Alert(
            id="alert_2",
            rule_id="rule_2",
            rule_name="规则2",
            severity=AlertSeverity.MEDIUM,
            message="告警2",
            labels={},
            annotations={},
            starts_at=datetime.now()
        )
        
        self.alerting_service.active_alerts["key1"] = alert1
        self.alerting_service.active_alerts["key2"] = alert2
        
        active_alerts = await self.alerting_service.get_active_alerts()
        
        assert len(active_alerts) == 2
        assert alert1 in active_alerts
        assert alert2 in active_alerts


if __name__ == "__main__":
    pytest.main([__file__])