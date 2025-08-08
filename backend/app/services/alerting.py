"""
告警和通知系统
提供告警规则引擎、通知发送和告警历史管理功能
"""
import asyncio
import json
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.database import AlertRule, AlertHistory
from ..models.schemas import AlertRuleCreate, AlertRuleUpdate
from ..utils.logging import get_structured_logger, EventType

logger = get_structured_logger(__name__)

class AlertSeverity(Enum):
    """告警严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertStatus(Enum):
    """告警状态"""
    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"

class NotificationChannel(Enum):
    """通知渠道"""
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    DINGTALK = "dingtalk"

@dataclass
class AlertCondition:
    """告警条件"""
    metric: str  # 监控指标名称
    operator: str  # 比较操作符: >, <, >=, <=, ==, !=
    threshold: float  # 阈值
    duration: int  # 持续时间（秒）
    
    def evaluate(self, value: float, duration: int) -> bool:
        """评估告警条件"""
        # 检查持续时间
        if duration < self.duration:
            return False
            
        # 检查阈值条件
        if self.operator == ">":
            return value > self.threshold
        elif self.operator == "<":
            return value < self.threshold
        elif self.operator == ">=":
            return value >= self.threshold
        elif self.operator == "<=":
            return value <= self.threshold
        elif self.operator == "==":
            return value == self.threshold
        elif self.operator == "!=":
            return value != self.threshold
        else:
            return False

@dataclass
class Alert:
    """告警实例"""
    id: str
    rule_id: str
    rule_name: str
    severity: AlertSeverity
    message: str
    labels: Dict[str, str]
    annotations: Dict[str, str]
    starts_at: datetime
    ends_at: Optional[datetime] = None
    status: AlertStatus = AlertStatus.ACTIVE
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "message": self.message,
            "labels": self.labels,
            "annotations": self.annotations,
            "starts_at": self.starts_at.isoformat(),
            "ends_at": self.ends_at.isoformat() if self.ends_at else None,
            "status": self.status.value
        }

class NotificationSender:
    """通知发送器基类"""
    
    async def send(self, alert: Alert, config: Dict[str, Any]) -> bool:
        """发送通知"""
        raise NotImplementedError

class EmailNotificationSender(NotificationSender):
    """邮件通知发送器"""
    
    async def send(self, alert: Alert, config: Dict[str, Any]) -> bool:
        """发送邮件通知"""
        try:
            smtp_server = config.get("smtp_server")
            smtp_port = config.get("smtp_port", 587)
            username = config.get("username")
            password = config.get("password")
            from_email = config.get("from_email")
            to_emails = config.get("to_emails", [])
            
            if not all([smtp_server, username, password, from_email, to_emails]):
                logger.error("邮件配置不完整", extra_data={"config": config})
                return False
            
            # 创建邮件内容
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.rule_name}"
            
            # 邮件正文
            body = self._create_email_body(alert)
            msg.attach(MIMEText(body, 'html', 'utf-8'))
            
            # 发送邮件
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(username, password)
                server.send_message(msg)
            
            logger.info(f"邮件告警发送成功: {alert.rule_name}", 
                       extra_data={"alert_id": alert.id, "recipients": to_emails})
            return True
            
        except Exception as e:
            logger.error(f"邮件告警发送失败: {e}", 
                        extra_data={"alert_id": alert.id, "error": str(e)})
            return False
    
    def _create_email_body(self, alert: Alert) -> str:
        """创建邮件正文"""
        severity_colors = {
            AlertSeverity.LOW: "#28a745",
            AlertSeverity.MEDIUM: "#ffc107", 
            AlertSeverity.HIGH: "#fd7e14",
            AlertSeverity.CRITICAL: "#dc3545"
        }
        
        color = severity_colors.get(alert.severity, "#6c757d")
        
        return f"""
        <html>
        <body>
            <h2 style="color: {color};">告警通知</h2>
            <table border="1" cellpadding="5" cellspacing="0">
                <tr><td><strong>告警规则</strong></td><td>{alert.rule_name}</td></tr>
                <tr><td><strong>严重程度</strong></td><td style="color: {color};">{alert.severity.value.upper()}</td></tr>
                <tr><td><strong>告警消息</strong></td><td>{alert.message}</td></tr>
                <tr><td><strong>开始时间</strong></td><td>{alert.starts_at.strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
                <tr><td><strong>状态</strong></td><td>{alert.status.value}</td></tr>
            </table>
            
            <h3>标签信息</h3>
            <table border="1" cellpadding="5" cellspacing="0">
                {"".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in alert.labels.items())}
            </table>
            
            <h3>注释信息</h3>
            <table border="1" cellpadding="5" cellspacing="0">
                {"".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in alert.annotations.items())}
            </table>
            
            <p><small>此邮件由LLM推理服务告警系统自动发送</small></p>
        </body>
        </html>
        """

class WebhookNotificationSender(NotificationSender):
    """Webhook通知发送器"""
    
    async def send(self, alert: Alert, config: Dict[str, Any]) -> bool:
        """发送Webhook通知"""
        try:
            url = config.get("url")
            headers = config.get("headers", {})
            timeout = config.get("timeout", 30)
            
            if not url:
                logger.error("Webhook URL未配置")
                return False
            
            # 准备请求数据
            payload = {
                "alert": alert.to_dict(),
                "timestamp": datetime.now().isoformat(),
                "source": "llm-inference-service"
            }
            
            # 发送HTTP请求
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, 
                    json=payload, 
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    if response.status == 200:
                        logger.info(f"Webhook告警发送成功: {alert.rule_name}",
                                   extra_data={"alert_id": alert.id, "url": url})
                        return True
                    else:
                        logger.error(f"Webhook告警发送失败: HTTP {response.status}",
                                    extra_data={"alert_id": alert.id, "url": url})
                        return False
                        
        except Exception as e:
            logger.error(f"Webhook告警发送失败: {e}",
                        extra_data={"alert_id": alert.id, "error": str(e)})
            return False

class SlackNotificationSender(NotificationSender):
    """Slack通知发送器"""
    
    async def send(self, alert: Alert, config: Dict[str, Any]) -> bool:
        """发送Slack通知"""
        try:
            webhook_url = config.get("webhook_url")
            channel = config.get("channel", "#alerts")
            username = config.get("username", "LLM Alert Bot")
            
            if not webhook_url:
                logger.error("Slack Webhook URL未配置")
                return False
            
            # 创建Slack消息
            color = self._get_slack_color(alert.severity)
            
            payload = {
                "channel": channel,
                "username": username,
                "attachments": [{
                    "color": color,
                    "title": f"告警: {alert.rule_name}",
                    "text": alert.message,
                    "fields": [
                        {"title": "严重程度", "value": alert.severity.value.upper(), "short": True},
                        {"title": "状态", "value": alert.status.value, "short": True},
                        {"title": "开始时间", "value": alert.starts_at.strftime('%Y-%m-%d %H:%M:%S'), "short": True}
                    ],
                    "footer": "LLM推理服务告警系统",
                    "ts": int(alert.starts_at.timestamp())
                }]
            }
            
            # 发送到Slack
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info(f"Slack告警发送成功: {alert.rule_name}",
                                   extra_data={"alert_id": alert.id})
                        return True
                    else:
                        logger.error(f"Slack告警发送失败: HTTP {response.status}",
                                    extra_data={"alert_id": alert.id})
                        return False
                        
        except Exception as e:
            logger.error(f"Slack告警发送失败: {e}",
                        extra_data={"alert_id": alert.id, "error": str(e)})
            return False
    
    def _get_slack_color(self, severity: AlertSeverity) -> str:
        """获取Slack消息颜色"""
        colors = {
            AlertSeverity.LOW: "good",
            AlertSeverity.MEDIUM: "warning",
            AlertSeverity.HIGH: "danger",
            AlertSeverity.CRITICAL: "danger"
        }
        return colors.get(severity, "good")

class AlertingService:
    """告警服务"""
    
    def __init__(self):
        self.active_alerts: Dict[str, Alert] = {}
        self.notification_senders = {
            NotificationChannel.EMAIL: EmailNotificationSender(),
            NotificationChannel.WEBHOOK: WebhookNotificationSender(),
            NotificationChannel.SLACK: SlackNotificationSender()
        }
        self.metric_history: Dict[str, List[tuple]] = {}  # (timestamp, value)
        
    async def create_alert_rule(self, rule_data: AlertRuleCreate, db: Session) -> AlertRule:
        """创建告警规则"""
        try:
            # 验证告警条件
            condition = AlertCondition(**rule_data.condition)
            
            # 创建数据库记录
            db_rule = AlertRule(
                name=rule_data.name,
                description=rule_data.description,
                condition=rule_data.condition,
                severity=rule_data.severity,
                enabled=rule_data.enabled,
                notification_channels=rule_data.notification_channels,
                notification_config=rule_data.notification_config,
                labels=rule_data.labels or {},
                annotations=rule_data.annotations or {}
            )
            
            db.add(db_rule)
            db.commit()
            db.refresh(db_rule)
            
            logger.info(f"告警规则创建成功: {rule_data.name}",
                       event_type=EventType.CONFIGURATION,
                       extra_data={"rule_id": db_rule.id})
            
            return db_rule
            
        except Exception as e:
            logger.error(f"创建告警规则失败: {e}",
                        extra_data={"rule_name": rule_data.name, "error": str(e)})
            db.rollback()
            raise
    
    async def update_alert_rule(self, rule_id: str, rule_data: AlertRuleUpdate, db: Session) -> Optional[AlertRule]:
        """更新告警规则"""
        try:
            db_rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
            if not db_rule:
                return None
            
            # 更新字段
            for field, value in rule_data.dict(exclude_unset=True).items():
                setattr(db_rule, field, value)
            
            db.commit()
            db.refresh(db_rule)
            
            logger.info(f"告警规则更新成功: {db_rule.name}",
                       event_type=EventType.CONFIGURATION,
                       extra_data={"rule_id": rule_id})
            
            return db_rule
            
        except Exception as e:
            logger.error(f"更新告警规则失败: {e}",
                        extra_data={"rule_id": rule_id, "error": str(e)})
            db.rollback()
            raise
    
    async def delete_alert_rule(self, rule_id: str, db: Session) -> bool:
        """删除告警规则"""
        try:
            db_rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
            if not db_rule:
                return False
            
            db.delete(db_rule)
            db.commit()
            
            logger.info(f"告警规则删除成功: {db_rule.name}",
                       event_type=EventType.CONFIGURATION,
                       extra_data={"rule_id": rule_id})
            
            return True
            
        except Exception as e:
            logger.error(f"删除告警规则失败: {e}",
                        extra_data={"rule_id": rule_id, "error": str(e)})
            db.rollback()
            raise
    
    async def evaluate_metrics(self, metrics: Dict[str, float], db: Session):
        """评估指标并触发告警"""
        current_time = datetime.now()
        
        # 更新指标历史
        for metric_name, value in metrics.items():
            if metric_name not in self.metric_history:
                self.metric_history[metric_name] = []
            
            self.metric_history[metric_name].append((current_time, value))
            
            # 保留最近1小时的数据
            cutoff_time = current_time - timedelta(hours=1)
            self.metric_history[metric_name] = [
                (ts, val) for ts, val in self.metric_history[metric_name]
                if ts > cutoff_time
            ]
        
        # 获取启用的告警规则
        alert_rules = db.query(AlertRule).filter(AlertRule.enabled == True).all()
        
        for rule in alert_rules:
            try:
                await self._evaluate_rule(rule, metrics, current_time, db)
            except Exception as e:
                logger.error(f"评估告警规则失败: {rule.name} - {e}",
                            extra_data={"rule_id": rule.id, "error": str(e)})
    
    async def _evaluate_rule(self, rule: AlertRule, metrics: Dict[str, float], 
                           current_time: datetime, db: Session):
        """评估单个告警规则"""
        condition = AlertCondition(**rule.condition)
        metric_name = condition.metric
        
        if metric_name not in metrics:
            return
        
        current_value = metrics[metric_name]
        
        # 计算指标持续时间
        duration = self._calculate_metric_duration(metric_name, condition, current_time)
        
        # 评估告警条件
        should_alert = condition.evaluate(current_value, duration)
        alert_key = f"{rule.id}_{metric_name}"
        
        if should_alert and alert_key not in self.active_alerts:
            # 触发新告警
            alert = Alert(
                id=f"alert_{rule.id}_{int(current_time.timestamp())}",
                rule_id=rule.id,
                rule_name=rule.name,
                severity=AlertSeverity(rule.severity),
                message=f"{rule.name}: {metric_name} = {current_value} {condition.operator} {condition.threshold}",
                labels=rule.labels or {},
                annotations=rule.annotations or {},
                starts_at=current_time
            )
            
            self.active_alerts[alert_key] = alert
            
            # 保存告警历史
            await self._save_alert_history(alert, db)
            
            # 发送通知
            await self._send_notifications(alert, rule.notification_channels, rule.notification_config)
            
            logger.warning(f"告警触发: {rule.name}",
                          event_type=EventType.SYSTEM_ERROR,
                          extra_data={
                              "alert_id": alert.id,
                              "metric": metric_name,
                              "value": current_value,
                              "threshold": condition.threshold
                          })
        
        elif not should_alert and alert_key in self.active_alerts:
            # 解决告警
            alert = self.active_alerts[alert_key]
            alert.status = AlertStatus.RESOLVED
            alert.ends_at = current_time
            
            # 更新告警历史
            await self._update_alert_history(alert, db)
            
            # 发送解决通知
            await self._send_notifications(alert, rule.notification_channels, rule.notification_config)
            
            del self.active_alerts[alert_key]
            
            logger.info(f"告警解决: {rule.name}",
                       event_type=EventType.SYSTEM_ERROR,
                       extra_data={"alert_id": alert.id})
    
    def _calculate_metric_duration(self, metric_name: str, condition: AlertCondition, 
                                 current_time: datetime) -> int:
        """计算指标满足条件的持续时间"""
        if metric_name not in self.metric_history:
            return 0
        
        history = self.metric_history[metric_name]
        if not history:
            return 0
        
        # 从最新时间向前查找连续满足条件的时间
        duration = 0
        for i in range(len(history) - 1, -1, -1):
            timestamp, value = history[i]
            
            # 检查是否满足条件
            if condition.operator == ">" and value > condition.threshold:
                duration = int((current_time - timestamp).total_seconds())
            elif condition.operator == "<" and value < condition.threshold:
                duration = int((current_time - timestamp).total_seconds())
            elif condition.operator == ">=" and value >= condition.threshold:
                duration = int((current_time - timestamp).total_seconds())
            elif condition.operator == "<=" and value <= condition.threshold:
                duration = int((current_time - timestamp).total_seconds())
            elif condition.operator == "==" and value == condition.threshold:
                duration = int((current_time - timestamp).total_seconds())
            elif condition.operator == "!=" and value != condition.threshold:
                duration = int((current_time - timestamp).total_seconds())
            else:
                break
        
        return duration
    
    async def _save_alert_history(self, alert: Alert, db: Session):
        """保存告警历史"""
        try:
            history = AlertHistory(
                alert_id=alert.id,
                rule_id=alert.rule_id,
                rule_name=alert.rule_name,
                severity=alert.severity.value,
                message=alert.message,
                labels=alert.labels,
                annotations=alert.annotations,
                starts_at=alert.starts_at,
                status=alert.status.value
            )
            
            db.add(history)
            db.commit()
            
        except Exception as e:
            logger.error(f"保存告警历史失败: {e}",
                        extra_data={"alert_id": alert.id, "error": str(e)})
            db.rollback()
    
    async def _update_alert_history(self, alert: Alert, db: Session):
        """更新告警历史"""
        try:
            history = db.query(AlertHistory).filter(AlertHistory.alert_id == alert.id).first()
            if history:
                history.status = alert.status.value
                history.ends_at = alert.ends_at
                db.commit()
                
        except Exception as e:
            logger.error(f"更新告警历史失败: {e}",
                        extra_data={"alert_id": alert.id, "error": str(e)})
            db.rollback()
    
    async def _send_notifications(self, alert: Alert, channels: List[str], config: Dict[str, Any]):
        """发送通知"""
        for channel_name in channels:
            try:
                channel = NotificationChannel(channel_name)
                sender = self.notification_senders.get(channel)
                
                if sender and channel_name in config:
                    channel_config = config[channel_name]
                    await sender.send(alert, channel_config)
                    
            except Exception as e:
                logger.error(f"发送通知失败: {channel_name} - {e}",
                            extra_data={"alert_id": alert.id, "channel": channel_name, "error": str(e)})
    
    async def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        return list(self.active_alerts.values())
    
    async def get_alert_history(self, db: Session, limit: int = 100, 
                              rule_id: Optional[str] = None) -> List[AlertHistory]:
        """获取告警历史"""
        query = db.query(AlertHistory)
        
        if rule_id:
            query = query.filter(AlertHistory.rule_id == rule_id)
        
        return query.order_by(AlertHistory.starts_at.desc()).limit(limit).all()
    
    async def suppress_alert(self, alert_id: str, duration_minutes: int = 60):
        """抑制告警"""
        for alert_key, alert in self.active_alerts.items():
            if alert.id == alert_id:
                alert.status = AlertStatus.SUPPRESSED
                
                # 设置定时器自动恢复
                asyncio.create_task(self._unsuppress_alert_after_delay(alert_key, duration_minutes * 60))
                
                logger.info(f"告警已抑制: {alert.rule_name}",
                           extra_data={"alert_id": alert_id, "duration_minutes": duration_minutes})
                return True
        
        return False
    
    async def _unsuppress_alert_after_delay(self, alert_key: str, delay_seconds: int):
        """延迟后取消告警抑制"""
        await asyncio.sleep(delay_seconds)
        
        if alert_key in self.active_alerts:
            alert = self.active_alerts[alert_key]
            if alert.status == AlertStatus.SUPPRESSED:
                alert.status = AlertStatus.ACTIVE
                logger.info(f"告警抑制已解除: {alert.rule_name}",
                           extra_data={"alert_id": alert.id})

# 全局告警服务实例
alerting_service = AlertingService()