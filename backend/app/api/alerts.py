"""
告警系统API端点
提供告警规则管理、告警查询和通知配置功能
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

from ..core.database import get_db
from ..services.alerting import alerting_service
from ..models.schemas import (
    AlertRuleCreate, AlertRuleUpdate, AlertRuleResponse,
    AlertResponse, AlertHistoryResponse, AlertSummary
)
from ..utils.logging import get_structured_logger, EventType

logger = get_structured_logger(__name__)
router = APIRouter(prefix="/api/alerts", tags=["告警系统"])

@router.post("/rules", response_model=AlertRuleResponse)
async def create_alert_rule(
    rule_data: AlertRuleCreate,
    db: Session = Depends(get_db)
):
    """创建告警规则"""
    try:
        # 生成规则ID
        rule_data_dict = rule_data.dict()
        rule_data_dict['id'] = f"rule_{uuid.uuid4().hex[:8]}"
        
        # 创建规则
        db_rule = await alerting_service.create_alert_rule(
            AlertRuleCreate(**rule_data_dict), db
        )
        
        # 转换为响应格式
        return AlertRuleResponse(
            id=db_rule.id,
            name=db_rule.name,
            description=db_rule.description,
            condition=db_rule.condition,
            severity=db_rule.severity,
            enabled=db_rule.enabled,
            notification_channels=db_rule.notification_channels or [],
            notification_config=db_rule.notification_config or {},
            labels=db_rule.labels or {},
            annotations=db_rule.annotations or {},
            created_at=db_rule.created_at,
            updated_at=db_rule.updated_at
        )
        
    except Exception as e:
        logger.error(f"创建告警规则失败: {e}",
                    event_type=EventType.SYSTEM_ERROR,
                    extra_data={"rule_name": rule_data.name, "error": str(e)})
        raise HTTPException(status_code=500, detail=f"创建告警规则失败: {str(e)}")

@router.get("/rules", response_model=List[AlertRuleResponse])
async def list_alert_rules(
    enabled: Optional[bool] = Query(None, description="是否启用"),
    severity: Optional[str] = Query(None, description="严重程度"),
    db: Session = Depends(get_db)
):
    """获取告警规则列表"""
    try:
        from ..models.database import AlertRule
        
        query = db.query(AlertRule)
        
        if enabled is not None:
            query = query.filter(AlertRule.enabled == enabled)
        if severity:
            query = query.filter(AlertRule.severity == severity)
        
        rules = query.all()
        
        return [
            AlertRuleResponse(
                id=rule.id,
                name=rule.name,
                description=rule.description,
                condition=rule.condition,
                severity=rule.severity,
                enabled=rule.enabled,
                notification_channels=rule.notification_channels or [],
                notification_config=rule.notification_config or {},
                labels=rule.labels or {},
                annotations=rule.annotations or {},
                created_at=rule.created_at,
                updated_at=rule.updated_at
            )
            for rule in rules
        ]
        
    except Exception as e:
        logger.error(f"获取告警规则列表失败: {e}",
                    event_type=EventType.SYSTEM_ERROR,
                    extra_data={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"获取告警规则列表失败: {str(e)}")

@router.get("/rules/{rule_id}", response_model=AlertRuleResponse)
async def get_alert_rule(
    rule_id: str,
    db: Session = Depends(get_db)
):
    """获取单个告警规则"""
    try:
        from ..models.database import AlertRule
        
        rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
        if not rule:
            raise HTTPException(status_code=404, detail="告警规则不存在")
        
        return AlertRuleResponse(
            id=rule.id,
            name=rule.name,
            description=rule.description,
            condition=rule.condition,
            severity=rule.severity,
            enabled=rule.enabled,
            notification_channels=rule.notification_channels or [],
            notification_config=rule.notification_config or {},
            labels=rule.labels or {},
            annotations=rule.annotations or {},
            created_at=rule.created_at,
            updated_at=rule.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取告警规则失败: {e}",
                    event_type=EventType.SYSTEM_ERROR,
                    extra_data={"rule_id": rule_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=f"获取告警规则失败: {str(e)}")

@router.put("/rules/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    rule_id: str,
    rule_data: AlertRuleUpdate,
    db: Session = Depends(get_db)
):
    """更新告警规则"""
    try:
        db_rule = await alerting_service.update_alert_rule(rule_id, rule_data, db)
        if not db_rule:
            raise HTTPException(status_code=404, detail="告警规则不存在")
        
        return AlertRuleResponse(
            id=db_rule.id,
            name=db_rule.name,
            description=db_rule.description,
            condition=db_rule.condition,
            severity=db_rule.severity,
            enabled=db_rule.enabled,
            notification_channels=db_rule.notification_channels or [],
            notification_config=db_rule.notification_config or {},
            labels=db_rule.labels or {},
            annotations=db_rule.annotations or {},
            created_at=db_rule.created_at,
            updated_at=db_rule.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新告警规则失败: {e}",
                    event_type=EventType.SYSTEM_ERROR,
                    extra_data={"rule_id": rule_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=f"更新告警规则失败: {str(e)}")

@router.delete("/rules/{rule_id}")
async def delete_alert_rule(
    rule_id: str,
    db: Session = Depends(get_db)
):
    """删除告警规则"""
    try:
        success = await alerting_service.delete_alert_rule(rule_id, db)
        if not success:
            raise HTTPException(status_code=404, detail="告警规则不存在")
        
        return {"message": "告警规则删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除告警规则失败: {e}",
                    event_type=EventType.SYSTEM_ERROR,
                    extra_data={"rule_id": rule_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=f"删除告警规则失败: {str(e)}")

@router.get("/active", response_model=List[AlertResponse])
async def get_active_alerts():
    """获取活跃告警列表"""
    try:
        active_alerts = await alerting_service.get_active_alerts()
        
        return [
            AlertResponse(
                id=alert.id,
                rule_id=alert.rule_id,
                rule_name=alert.rule_name,
                severity=alert.severity.value,
                message=alert.message,
                labels=alert.labels,
                annotations=alert.annotations,
                starts_at=alert.starts_at,
                ends_at=alert.ends_at,
                status=alert.status.value
            )
            for alert in active_alerts
        ]
        
    except Exception as e:
        logger.error(f"获取活跃告警失败: {e}",
                    event_type=EventType.SYSTEM_ERROR,
                    extra_data={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"获取活跃告警失败: {str(e)}")

@router.get("/history", response_model=List[AlertHistoryResponse])
async def get_alert_history(
    rule_id: Optional[str] = Query(None, description="规则ID"),
    severity: Optional[str] = Query(None, description="严重程度"),
    status: Optional[str] = Query(None, description="状态"),
    limit: int = Query(100, description="返回数量限制"),
    db: Session = Depends(get_db)
):
    """获取告警历史"""
    try:
        from ..models.database import AlertHistory
        
        query = db.query(AlertHistory)
        
        if rule_id:
            query = query.filter(AlertHistory.rule_id == rule_id)
        if severity:
            query = query.filter(AlertHistory.severity == severity)
        if status:
            query = query.filter(AlertHistory.status == status)
        
        history_records = query.order_by(AlertHistory.starts_at.desc()).limit(limit).all()
        
        return [
            AlertHistoryResponse(
                id=record.id,
                alert_id=record.alert_id,
                rule_id=record.rule_id,
                rule_name=record.rule_name,
                severity=record.severity,
                message=record.message,
                labels=record.labels or {},
                annotations=record.annotations or {},
                starts_at=record.starts_at,
                ends_at=record.ends_at,
                status=record.status,
                notification_sent=record.notification_sent,
                created_at=record.created_at,
                updated_at=record.updated_at
            )
            for record in history_records
        ]
        
    except Exception as e:
        logger.error(f"获取告警历史失败: {e}",
                    event_type=EventType.SYSTEM_ERROR,
                    extra_data={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"获取告警历史失败: {str(e)}")

@router.get("/summary", response_model=AlertSummary)
async def get_alert_summary(
    hours: int = Query(24, description="统计时间范围(小时)"),
    db: Session = Depends(get_db)
):
    """获取告警摘要统计"""
    try:
        from ..models.database import AlertHistory
        
        # 计算时间范围
        start_time = datetime.now() - timedelta(hours=hours)
        
        # 查询告警历史
        query = db.query(AlertHistory).filter(AlertHistory.starts_at >= start_time)
        all_alerts = query.all()
        
        # 统计各种状态的告警
        total_alerts = len(all_alerts)
        active_alerts = len([a for a in all_alerts if a.status == "active"])
        resolved_alerts = len([a for a in all_alerts if a.status == "resolved"])
        suppressed_alerts = len([a for a in all_alerts if a.status == "suppressed"])
        
        # 统计各种严重程度的告警
        critical_alerts = len([a for a in all_alerts if a.severity == "critical"])
        high_alerts = len([a for a in all_alerts if a.severity == "high"])
        medium_alerts = len([a for a in all_alerts if a.severity == "medium"])
        low_alerts = len([a for a in all_alerts if a.severity == "low"])
        
        return AlertSummary(
            total_alerts=total_alerts,
            active_alerts=active_alerts,
            resolved_alerts=resolved_alerts,
            suppressed_alerts=suppressed_alerts,
            critical_alerts=critical_alerts,
            high_alerts=high_alerts,
            medium_alerts=medium_alerts,
            low_alerts=low_alerts,
            last_updated=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"获取告警摘要失败: {e}",
                    event_type=EventType.SYSTEM_ERROR,
                    extra_data={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"获取告警摘要失败: {str(e)}")

@router.post("/suppress/{alert_id}")
async def suppress_alert(
    alert_id: str,
    duration_minutes: int = Query(60, description="抑制时长(分钟)")
):
    """抑制告警"""
    try:
        success = await alerting_service.suppress_alert(alert_id, duration_minutes)
        if not success:
            raise HTTPException(status_code=404, detail="告警不存在或已解决")
        
        return {"message": f"告警已抑制 {duration_minutes} 分钟"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"抑制告警失败: {e}",
                    event_type=EventType.SYSTEM_ERROR,
                    extra_data={"alert_id": alert_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=f"抑制告警失败: {str(e)}")

@router.post("/test-notification")
async def test_notification(
    channel: str = Query(..., description="通知渠道"),
    config: dict = {}
):
    """测试通知配置"""
    try:
        from ..services.alerting import Alert, AlertSeverity, AlertStatus
        
        # 创建测试告警
        test_alert = Alert(
            id="test_alert",
            rule_id="test_rule",
            rule_name="测试告警规则",
            severity=AlertSeverity.MEDIUM,
            message="这是一个测试告警消息",
            labels={"test": "true"},
            annotations={"description": "用于测试通知配置"},
            starts_at=datetime.now(),
            status=AlertStatus.ACTIVE
        )
        
        # 发送测试通知
        await alerting_service._send_notifications(test_alert, [channel], {channel: config})
        
        return {"message": "测试通知发送成功"}
        
    except Exception as e:
        logger.error(f"测试通知失败: {e}",
                    event_type=EventType.SYSTEM_ERROR,
                    extra_data={"channel": channel, "error": str(e)})
        raise HTTPException(status_code=500, detail=f"测试通知失败: {str(e)}")

@router.post("/evaluate")
async def manual_evaluate_metrics(
    metrics: dict,
    db: Session = Depends(get_db)
):
    """手动触发指标评估"""
    try:
        await alerting_service.evaluate_metrics(metrics, db)
        return {"message": "指标评估完成"}
        
    except Exception as e:
        logger.error(f"手动评估指标失败: {e}",
                    event_type=EventType.SYSTEM_ERROR,
                    extra_data={"metrics": metrics, "error": str(e)})
        raise HTTPException(status_code=500, detail=f"手动评估指标失败: {str(e)}")