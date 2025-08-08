"""
健康检查器服务
"""
import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
import logging

from ..models.schemas import ModelInfo, ModelConfig
from ..models.enums import HealthStatus, ModelStatus

logger = logging.getLogger(__name__)


@dataclass
class HealthCheckConfig:
    """健康检查配置"""
    enabled: bool = True
    interval: int = 30  # 秒
    timeout: int = 10  # 秒
    max_failures: int = 3
    endpoint: str = "/health"
    retry_interval: int = 60  # 秒


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    model_id: str
    status: HealthStatus
    check_time: datetime
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class HealthChecker:
    """健康检查器"""
    
    def __init__(self, check_interval: int = 30, max_history_size: int = 100):
        self._check_interval = check_interval
        self._max_history_size = max_history_size
        self._registered_models: Dict[str, Dict[str, Any]] = {}
        self._health_callbacks: List[Callable] = []
        self._is_running = False
        self._check_task: Optional[asyncio.Task] = None
    
    async def register_model(self, model_info: ModelInfo):
        """注册模型进行健康检查"""
        self._registered_models[model_info.id] = {
            'model_info': model_info,
            'last_check': None,
            'failure_count': 0,
            'status': HealthStatus.UNKNOWN,
            'check_history': []
        }
        logger.info(f"已注册模型健康检查: {model_info.id}")
    
    async def unregister_model(self, model_id: str):
        """注销模型健康检查"""
        if model_id in self._registered_models:
            del self._registered_models[model_id]
            logger.info(f"已注销模型健康检查: {model_id}")
    
    async def check_model_health(self, model_info: ModelInfo, health_endpoint: Optional[str] = None) -> HealthCheckResult:
        """检查单个模型的健康状态"""
        endpoint = health_endpoint or "/health"
        base_url = model_info.api_endpoint or "http://127.0.0.1:8000"
        url = f"{base_url.rstrip('/')}{endpoint}"
        
        start_time = datetime.now()
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                
                # Use the response's elapsed time if available, otherwise calculate from start_time
                if hasattr(response, 'elapsed') and response.elapsed:
                    response_time = response.elapsed.total_seconds()
                else:
                    response_time = (datetime.now() - start_time).total_seconds()
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        return HealthCheckResult(
                            model_id=model_info.id,
                            status=HealthStatus.HEALTHY,
                            check_time=start_time,
                            response_time=response_time,
                            details=data
                        )
                    except Exception:
                        # JSON解析失败，但状态码是200，认为是健康的
                        return HealthCheckResult(
                            model_id=model_info.id,
                            status=HealthStatus.HEALTHY,
                            check_time=start_time,
                            response_time=response_time
                        )
                else:
                    return HealthCheckResult(
                        model_id=model_info.id,
                        status=HealthStatus.UNHEALTHY,
                        check_time=start_time,
                        response_time=response_time,
                        error_message=f"HTTP {response.status_code}: {response.text}"
                    )
        
        except asyncio.TimeoutError:
            return HealthCheckResult(
                model_id=model_info.id,
                status=HealthStatus.UNHEALTHY,
                check_time=start_time,
                error_message="健康检查超时"
            )
        except Exception as e:
            return HealthCheckResult(
                model_id=model_info.id,
                status=HealthStatus.UNHEALTHY,
                check_time=start_time,
                error_message=str(e)
            )
    
    async def _update_model_status(self, result: HealthCheckResult):
        """更新模型状态"""
        if result.model_id not in self._registered_models:
            return
        
        model_data = self._registered_models[result.model_id]
        old_status = model_data['status']
        
        # 更新状态
        model_data['status'] = result.status
        model_data['last_check'] = result.check_time
        
        # 更新失败计数
        if result.status == HealthStatus.UNHEALTHY:
            model_data['failure_count'] += 1
        else:
            model_data['failure_count'] = 0  # 重置失败计数
        
        # 添加到历史记录
        model_data['check_history'].append(result)
        
        # 限制历史记录大小
        if len(model_data['check_history']) > self._max_history_size:
            model_data['check_history'] = model_data['check_history'][-self._max_history_size:]
        
        # 触发回调
        for callback in self._health_callbacks:
            try:
                await callback(result.model_id, old_status, result.status, result)
            except Exception as e:
                logger.error(f"健康检查回调执行失败: {e}")
    
    async def get_model_health_status(self, model_id: str) -> HealthStatus:
        """获取模型健康状态"""
        if model_id in self._registered_models:
            return self._registered_models[model_id]['status']
        return HealthStatus.UNKNOWN
    
    async def get_model_health_details(self, model_id: str) -> Optional[Dict[str, Any]]:
        """获取模型健康详情"""
        if model_id not in self._registered_models:
            return None
        
        model_data = self._registered_models[model_id]
        return {
            'model_id': model_id,
            'current_status': model_data['status'],
            'last_check': model_data['last_check'],
            'failure_count': model_data['failure_count'],
            'check_history': model_data['check_history'][-10:]  # 最近10次检查
        }
    
    async def get_all_health_status(self) -> Dict[str, HealthStatus]:
        """获取所有模型的健康状态"""
        return {
            model_id: data['status']
            for model_id, data in self._registered_models.items()
        }
    
    def add_health_callback(self, callback: Callable):
        """添加健康状态变更回调"""
        self._health_callbacks.append(callback)
    
    async def start_periodic_checks(self):
        """启动定期健康检查"""
        if self._is_running:
            return
        
        self._is_running = True
        self._check_task = asyncio.create_task(self._periodic_check_loop())
        logger.info("健康检查器已启动")
    
    async def stop_periodic_checks(self):
        """停止定期健康检查"""
        self._is_running = False
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
        logger.info("健康检查器已停止")
    
    async def _periodic_check_loop(self):
        """定期检查循环"""
        while self._is_running:
            try:
                # 检查所有注册的模型
                for model_id, model_data in self._registered_models.items():
                    if not self._is_running:
                        break
                    
                    model_info = model_data['model_info']
                    result = await self.check_model_health(model_info)
                    await self._update_model_status(result)
                
                # 等待下次检查
                await asyncio.sleep(self._check_interval)
                
            except Exception as e:
                logger.error(f"定期健康检查出错: {e}")
                await asyncio.sleep(5)  # 出错后短暂等待
    
    async def get_health_statistics(self, model_id: str) -> Optional[Dict[str, Any]]:
        """获取健康检查统计信息"""
        if model_id not in self._registered_models:
            return None
        
        model_data = self._registered_models[model_id]
        history = model_data['check_history']
        
        if not history:
            return {
                'model_id': model_id,
                'total_checks': 0,
                'successful_checks': 0,
                'failed_checks': 0,
                'success_rate': 0.0
            }
        
        successful_checks = len([r for r in history if r.status == HealthStatus.HEALTHY])
        failed_checks = len(history) - successful_checks
        
        # 计算平均响应时间
        response_times = [r.response_time for r in history if r.response_time is not None]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
        
        return {
            'model_id': model_id,
            'total_checks': len(history),
            'successful_checks': successful_checks,
            'failed_checks': failed_checks,
            'success_rate': successful_checks / len(history),
            'avg_response_time': avg_response_time,
            'last_check_time': model_data['last_check']
        }


class ModelHealthChecker:
    """模型健康检查器 - 专门用于模型管理器的健康检查"""
    
    def __init__(self, config: HealthCheckConfig = None):
        self.config = config or HealthCheckConfig()
        self.health_checker = HealthChecker(
            check_interval=self.config.interval,
            max_history_size=100
        )
        self._recovery_manager = None
    
    async def start(self):
        """启动健康检查"""
        if self.config.enabled:
            await self.health_checker.start_periodic_checks()
    
    async def stop(self):
        """停止健康检查"""
        await self.health_checker.stop_periodic_checks()
    
    async def register_model(self, model_info: ModelInfo):
        """注册模型"""
        await self.health_checker.register_model(model_info)
    
    async def unregister_model(self, model_id: str):
        """注销模型"""
        await self.health_checker.unregister_model(model_id)
    
    async def check_model_health(self, model_info: ModelInfo) -> HealthCheckResult:
        """检查模型健康状态"""
        return await self.health_checker.check_model_health(
            model_info, 
            self.config.endpoint
        )
    
    async def get_model_health_status(self, model_id: str) -> HealthStatus:
        """获取模型健康状态"""
        return await self.health_checker.get_model_health_status(model_id)
    
    def set_recovery_manager(self, recovery_manager: 'AutoRecoveryManager'):
        """设置恢复管理器"""
        self._recovery_manager = recovery_manager
        self.health_checker.add_health_callback(self._on_health_change)
    
    async def _on_health_change(self, model_id: str, old_status: HealthStatus, 
                               new_status: HealthStatus, result: HealthCheckResult):
        """健康状态变更回调"""
        if self._recovery_manager and new_status == HealthStatus.UNHEALTHY:
            await self._recovery_manager.handle_unhealthy_model(model_id, result)


class AutoRecoveryManager:
    """自动恢复管理器"""
    
    def __init__(self, model_manager=None, config: HealthCheckConfig = None):
        self.model_manager = model_manager
        self.config = config or HealthCheckConfig()
        self._recovery_attempts: Dict[str, int] = {}
        self._last_recovery_time: Dict[str, datetime] = {}
    
    async def handle_unhealthy_model(self, model_id: str, health_result: HealthCheckResult):
        """处理不健康的模型"""
        if not self.model_manager:
            logger.warning(f"模型管理器未设置，无法恢复模型: {model_id}")
            return
        
        # 检查是否超过最大失败次数
        current_attempts = self._recovery_attempts.get(model_id, 0)
        if current_attempts >= self.config.max_failures:
            logger.error(f"模型 {model_id} 恢复尝试次数已达上限，停止自动恢复")
            return
        
        # 检查恢复间隔
        last_recovery = self._last_recovery_time.get(model_id)
        if last_recovery:
            time_since_last = datetime.now() - last_recovery
            if time_since_last.total_seconds() < self.config.retry_interval:
                logger.debug(f"模型 {model_id} 恢复间隔未到，跳过恢复")
                return
        
        # 尝试恢复模型
        try:
            logger.info(f"尝试恢复不健康的模型: {model_id}")
            success = await self.model_manager.restart_model(model_id)
            
            if success:
                logger.info(f"模型 {model_id} 恢复成功")
                self._recovery_attempts[model_id] = 0  # 重置恢复计数
            else:
                self._recovery_attempts[model_id] = current_attempts + 1
                logger.warning(f"模型 {model_id} 恢复失败，尝试次数: {self._recovery_attempts[model_id]}")
            
            self._last_recovery_time[model_id] = datetime.now()
            
        except Exception as e:
            self._recovery_attempts[model_id] = current_attempts + 1
            self._last_recovery_time[model_id] = datetime.now()
            logger.error(f"模型 {model_id} 恢复过程中出错: {e}")
    
    def reset_recovery_attempts(self, model_id: str):
        """重置恢复尝试次数"""
        if model_id in self._recovery_attempts:
            del self._recovery_attempts[model_id]
        if model_id in self._last_recovery_time:
            del self._last_recovery_time[model_id]
    
    def get_recovery_status(self, model_id: str) -> Dict[str, Any]:
        """获取恢复状态"""
        return {
            'model_id': model_id,
            'recovery_attempts': self._recovery_attempts.get(model_id, 0),
            'last_recovery_time': self._last_recovery_time.get(model_id),
            'max_failures': self.config.max_failures,
            'retry_interval': self.config.retry_interval
        }