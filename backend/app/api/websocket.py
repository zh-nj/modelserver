"""
WebSocket端点
提供实时配置变更通知和系统状态更新
"""
import json
import logging
import asyncio
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime

from ..services.config_hot_reload import get_hot_reload_service, ConfigChangeEvent

logger = logging.getLogger(__name__)

router = APIRouter()

class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 活跃连接
        self.active_connections: Set[WebSocket] = set()
        # 连接信息
        self.connection_info: Dict[WebSocket, dict] = {}
        
    async def connect(self, websocket: WebSocket, client_id: str = None):
        """接受WebSocket连接"""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.connection_info[websocket] = {
            "client_id": client_id or f"client_{len(self.active_connections)}",
            "connected_at": datetime.now(),
            "subscriptions": set()
        }
        
        logger.info(f"WebSocket客户端连接: {self.connection_info[websocket]['client_id']}")
        
        # 发送连接确认消息
        await self.send_personal_message(websocket, {
            "type": "connection_established",
            "client_id": self.connection_info[websocket]["client_id"],
            "timestamp": datetime.now().isoformat()
        })
    
    def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        if websocket in self.active_connections:
            client_info = self.connection_info.get(websocket, {})
            client_id = client_info.get("client_id", "unknown")
            
            self.active_connections.remove(websocket)
            if websocket in self.connection_info:
                del self.connection_info[websocket]
            
            logger.info(f"WebSocket客户端断开: {client_id}")
    
    async def send_personal_message(self, websocket: WebSocket, message: dict):
        """发送个人消息"""
        try:
            await websocket.send_text(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            logger.error(f"发送WebSocket消息失败: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: dict, subscription_type: str = None):
        """广播消息"""
        if not self.active_connections:
            return
        
        disconnected = set()
        
        for websocket in self.active_connections.copy():
            try:
                # 检查订阅
                if subscription_type:
                    client_info = self.connection_info.get(websocket, {})
                    subscriptions = client_info.get("subscriptions", set())
                    if subscription_type not in subscriptions:
                        continue
                
                await websocket.send_text(json.dumps(message, ensure_ascii=False))
            except Exception as e:
                logger.error(f"广播WebSocket消息失败: {e}")
                disconnected.add(websocket)
        
        # 清理断开的连接
        for websocket in disconnected:
            self.disconnect(websocket)
    
    def subscribe(self, websocket: WebSocket, subscription_type: str):
        """订阅消息类型"""
        if websocket in self.connection_info:
            self.connection_info[websocket]["subscriptions"].add(subscription_type)
            logger.info(f"客户端 {self.connection_info[websocket]['client_id']} 订阅: {subscription_type}")
    
    def unsubscribe(self, websocket: WebSocket, subscription_type: str):
        """取消订阅消息类型"""
        if websocket in self.connection_info:
            self.connection_info[websocket]["subscriptions"].discard(subscription_type)
            logger.info(f"客户端 {self.connection_info[websocket]['client_id']} 取消订阅: {subscription_type}")
    
    def get_connection_count(self) -> int:
        """获取连接数量"""
        return len(self.active_connections)
    
    def get_connection_info(self) -> list:
        """获取连接信息"""
        info = []
        for websocket, client_info in self.connection_info.items():
            info.append({
                "client_id": client_info["client_id"],
                "connected_at": client_info["connected_at"].isoformat(),
                "subscriptions": list(client_info["subscriptions"])
            })
        return info

# 全局WebSocket管理器
websocket_manager = WebSocketManager()

@router.websocket("/ws/config-changes")
async def websocket_config_changes(websocket: WebSocket):
    """配置变更WebSocket端点"""
    await websocket_manager.connect(websocket)
    
    try:
        # 注册配置变更监听器
        hot_reload_service = get_hot_reload_service()
        if hot_reload_service:
            hot_reload_service.add_change_listener(config_change_listener)
        
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                await handle_client_message(websocket, message)
            except json.JSONDecodeError:
                await websocket_manager.send_personal_message(websocket, {
                    "type": "error",
                    "message": "无效的JSON格式",
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"处理客户端消息失败: {e}")
                await websocket_manager.send_personal_message(websocket, {
                    "type": "error",
                    "message": f"处理消息失败: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                })
    
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket连接异常: {e}")
        websocket_manager.disconnect(websocket)

async def handle_client_message(websocket: WebSocket, message: dict):
    """处理客户端消息"""
    message_type = message.get("type")
    
    if message_type == "subscribe":
        # 订阅消息类型
        subscription_type = message.get("subscription_type")
        if subscription_type:
            websocket_manager.subscribe(websocket, subscription_type)
            await websocket_manager.send_personal_message(websocket, {
                "type": "subscription_confirmed",
                "subscription_type": subscription_type,
                "timestamp": datetime.now().isoformat()
            })
    
    elif message_type == "unsubscribe":
        # 取消订阅
        subscription_type = message.get("subscription_type")
        if subscription_type:
            websocket_manager.unsubscribe(websocket, subscription_type)
            await websocket_manager.send_personal_message(websocket, {
                "type": "unsubscription_confirmed",
                "subscription_type": subscription_type,
                "timestamp": datetime.now().isoformat()
            })
    
    elif message_type == "ping":
        # 心跳检测
        await websocket_manager.send_personal_message(websocket, {
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        })
    
    elif message_type == "get_status":
        # 获取服务状态
        hot_reload_service = get_hot_reload_service()
        if hot_reload_service:
            status = hot_reload_service.get_status()
            await websocket_manager.send_personal_message(websocket, {
                "type": "status_response",
                "status": status,
                "timestamp": datetime.now().isoformat()
            })
        else:
            await websocket_manager.send_personal_message(websocket, {
                "type": "status_response",
                "status": {"available": False, "message": "热重载服务未启用"},
                "timestamp": datetime.now().isoformat()
            })
    
    else:
        await websocket_manager.send_personal_message(websocket, {
            "type": "error",
            "message": f"未知消息类型: {message_type}",
            "timestamp": datetime.now().isoformat()
        })

async def config_change_listener(event: ConfigChangeEvent):
    """配置变更监听器"""
    try:
        # 构建通知消息
        message = {
            "type": "config_change",
            "event": {
                "change_type": event.change_type.value,
                "model_id": event.model_id,
                "timestamp": event.timestamp.isoformat(),
                "changed_fields": event.change_fields or []
            }
        }
        
        # 添加配置详情
        if event.new_config:
            message["event"]["new_config"] = {
                "id": event.new_config.id,
                "name": event.new_config.name,
                "framework": event.new_config.framework.value,
                "priority": event.new_config.priority,
                "model_path": event.new_config.model_path
            }
        
        if event.old_config:
            message["event"]["old_config"] = {
                "id": event.old_config.id,
                "name": event.old_config.name,
                "framework": event.old_config.framework.value,
                "priority": event.old_config.priority,
                "model_path": event.old_config.model_path
            }
        
        # 广播配置变更通知
        await websocket_manager.broadcast(message, "config_changes")
        
        logger.info(f"配置变更通知已发送: {event.change_type.value} - {event.model_id}")
        
    except Exception as e:
        logger.error(f"发送配置变更通知失败: {e}")

@router.websocket("/ws/system-status")
async def websocket_system_status(websocket: WebSocket):
    """系统状态WebSocket端点"""
    await websocket_manager.connect(websocket)
    
    try:
        # 启动状态推送任务
        status_task = asyncio.create_task(push_system_status(websocket))
        
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                await handle_status_client_message(websocket, message)
            except json.JSONDecodeError:
                await websocket_manager.send_personal_message(websocket, {
                    "type": "error",
                    "message": "无效的JSON格式",
                    "timestamp": datetime.now().isoformat()
                })
    
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
        if not status_task.done():
            status_task.cancel()
    except Exception as e:
        logger.error(f"系统状态WebSocket连接异常: {e}")
        websocket_manager.disconnect(websocket)
        if not status_task.done():
            status_task.cancel()

async def handle_status_client_message(websocket: WebSocket, message: dict):
    """处理系统状态客户端消息"""
    message_type = message.get("type")
    
    if message_type == "ping":
        await websocket_manager.send_personal_message(websocket, {
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        })
    elif message_type == "get_immediate_status":
        # 立即获取系统状态
        await send_system_status(websocket)

async def push_system_status(websocket: WebSocket):
    """推送系统状态"""
    try:
        while websocket in websocket_manager.active_connections:
            await send_system_status(websocket)
            await asyncio.sleep(5)  # 每5秒推送一次
    except asyncio.CancelledError:
        logger.info("系统状态推送任务被取消")
    except Exception as e:
        logger.error(f"推送系统状态失败: {e}")

async def send_system_status(websocket: WebSocket):
    """发送系统状态"""
    try:
        # 获取热重载服务状态
        hot_reload_service = get_hot_reload_service()
        hot_reload_status = None
        if hot_reload_service:
            hot_reload_status = hot_reload_service.get_status()
        
        # 构建状态消息
        status_message = {
            "type": "system_status",
            "status": {
                "hot_reload": hot_reload_status,
                "websocket_connections": websocket_manager.get_connection_count(),
                "timestamp": datetime.now().isoformat()
            }
        }
        
        await websocket_manager.send_personal_message(websocket, status_message)
        
    except Exception as e:
        logger.error(f"发送系统状态失败: {e}")

# WebSocket管理API端点

@router.get("/ws/connections")
async def get_websocket_connections():
    """获取WebSocket连接信息"""
    return {
        "connection_count": websocket_manager.get_connection_count(),
        "connections": websocket_manager.get_connection_info()
    }

@router.post("/ws/broadcast")
async def broadcast_message(message: dict):
    """广播消息到所有WebSocket连接"""
    try:
        broadcast_message = {
            "type": "broadcast",
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        await websocket_manager.broadcast(broadcast_message)
        
        return {
            "success": True,
            "message": "消息广播成功",
            "connection_count": websocket_manager.get_connection_count()
        }
    except Exception as e:
        logger.error(f"广播消息失败: {e}")
        return {
            "success": False,
            "message": f"广播消息失败: {str(e)}"
        }