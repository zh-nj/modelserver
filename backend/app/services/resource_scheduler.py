"""
资源调度器服务 - 实现基于优先级的资源分配和调度
"""
import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

from .base import ResourceSchedulerInterface
from ..models.schemas import (
    ModelConfig, ModelInfo, GPUInfo, ResourceRequirement, ResourceAllocation,
    ScheduleResult as ScheduleResultEnum
)
from ..models.enums import ModelStatus, ScheduleResult
from ..utils.resource_calculator import resource_calculator
from ..utils.gpu import gpu_monitor


class PreemptionReason(str, Enum):
    """抢占原因"""
    HIGHER_PRIORITY = "higher_priority"  # 高优先级模型需要资源
    RESOURCE_SHORTAGE = "resource_shortage"  # 资源不足
    MANUAL_PREEMPTION = "manual_preemption"  # 手动抢占


class RecoveryReason(str, Enum):
    """恢复原因"""
    RESOURCE_AVAILABLE = "resource_available"  # 资源可用
    SCHEDULED_RECOVERY = "scheduled_recovery"  # 定时恢复
    MANUAL_RECOVERY = "manual_recovery"  # 手动恢复
    FAILURE_RECOVERY = "failure_recovery"  # 故障恢复


@dataclass
class RecoveryAttempt:
    """恢复尝试记录"""
    model_id: str
    attempt_time: datetime
    reason: RecoveryReason
    success: bool
    error_message: Optional[str] = None
    retry_count: int = 0


@dataclass
class ScheduleState:
    """调度状态持久化"""
    model_states: Dict[str, Dict[str, Any]]
    schedule_history: List[Dict[str, Any]]
    recovery_queue: List[str]
    last_saved: datetime
    version: str = "1.0"


@dataclass
class ScheduleDecision:
    """调度决策记录"""
    model_id: str
    decision_time: datetime
    result: ScheduleResult
    allocated_resources: Optional[ResourceAllocation] = None
    preempted_models: List[str] = field(default_factory=list)
    reason: str = ""
    gpu_state_before: List[GPUInfo] = field(default_factory=list)
    gpu_state_after: List[GPUInfo] = field(default_factory=list)


@dataclass
class ModelResourceState:
    """模型资源状态"""
    model_id: str
    config: ModelConfig
    status: ModelStatus
    allocated_resources: Optional[ResourceAllocation] = None
    last_scheduled: Optional[datetime] = None
    preemption_count: int = 0
    total_runtime: timedelta = field(default_factory=lambda: timedelta())


class PriorityResourceScheduler(ResourceSchedulerInterface):
    """
    基于优先级的资源调度器
    
    实现功能:
    1. 基于优先级的资源分配
    2. 模型抢占和资源释放
    3. 调度决策记录和审计
    """
    
    def __init__(self, state_file: str = "scheduler_state.json"):
        self.logger = logging.getLogger(__name__)
        
        # 模型资源状态跟踪
        self._model_states: Dict[str, ModelResourceState] = {}
        
        # 调度决策历史
        self._schedule_history: List[ScheduleDecision] = []
        
        # 调度锁，防止并发调度冲突
        self._schedule_lock = asyncio.Lock()
        
        # 恢复队列 - 等待恢复的模型
        self._recovery_queue: List[str] = []
        
        # 恢复尝试历史
        self._recovery_attempts: List[RecoveryAttempt] = []
        
        # 状态持久化文件路径
        self._state_file = state_file
        
        # 抢占策略配置
        self._preemption_config = {
            'enable_preemption': True,
            'min_priority_diff': 1,  # 最小优先级差异
            'preemption_grace_period': 30,  # 抢占宽限期(秒)
            'max_preemptions_per_hour': 10,  # 每小时最大抢占次数
        }
        
        # 自动重启和恢复配置
        self._recovery_config = {
            'enable_auto_recovery': True,
            'recovery_check_interval': 60,  # 恢复检查间隔(秒)
            'max_recovery_attempts': 3,  # 最大恢复尝试次数
            'recovery_backoff_factor': 2.0,  # 恢复退避因子
            'min_recovery_interval': 30,  # 最小恢复间隔(秒)
            'max_recovery_interval': 300,  # 最大恢复间隔(秒)
            'enable_failure_recovery': True,  # 启用故障恢复
            'failure_detection_timeout': 120,  # 故障检测超时(秒)
        }
        
        # 启动恢复任务
        self._recovery_task: Optional[asyncio.Task] = None
        self._recovery_started = False
        
        # 加载持久化状态
        self._load_state()
        
        self.logger.info("优先级资源调度器初始化完成")
    
    async def start_recovery_task(self):
        """启动恢复任务"""
        if (self._recovery_config['enable_auto_recovery'] and 
            not self._recovery_started and 
            self._recovery_task is None):
            try:
                self._recovery_task = asyncio.create_task(self._recovery_loop())
                self._recovery_started = True
                self.logger.info("恢复任务已启动")
            except Exception as e:
                self.logger.error(f"启动恢复任务失败: {e}")
    
    async def schedule_model(self, model_id: str) -> ScheduleResult:
        """
        调度模型资源
        
        Args:
            model_id: 模型ID
            
        Returns:
            调度结果
        """
        async with self._schedule_lock:
            try:
                self.logger.info(f"开始调度模型: {model_id}")
                
                # 获取模型状态
                model_state = self._model_states.get(model_id)
                if not model_state:
                    self.logger.error(f"模型状态不存在: {model_id}")
                    return ScheduleResult.FAILED
                
                # 记录调度开始时的GPU状态
                gpu_state_before = await self.get_gpu_info()
                
                # 计算资源需求
                resource_req = await self.calculate_resource_requirements(model_state.config)
                
                # 尝试直接分配资源
                allocation = await self.find_available_resources(resource_req)
                
                if allocation:
                    # 直接分配成功
                    result = await self._allocate_resources(model_id, allocation)
                    decision = ScheduleDecision(
                        model_id=model_id,
                        decision_time=datetime.now(),
                        result=result,
                        allocated_resources=allocation,
                        reason="直接分配成功",
                        gpu_state_before=gpu_state_before,
                        gpu_state_after=await self.get_gpu_info()
                    )
                    self._schedule_history.append(decision)
                    return result
                
                # 直接分配失败，尝试抢占
                if self._preemption_config['enable_preemption']:
                    preemption_result = await self._attempt_preemption(model_id, resource_req)
                    
                    if preemption_result['success']:
                        # 抢占成功，重新尝试分配
                        allocation = await self.find_available_resources(resource_req)
                        if allocation:
                            result = await self._allocate_resources(model_id, allocation)
                            decision = ScheduleDecision(
                                model_id=model_id,
                                decision_time=datetime.now(),
                                result=result,
                                allocated_resources=allocation,
                                preempted_models=preemption_result['preempted_models'],
                                reason=f"抢占成功: {preemption_result['reason']}",
                                gpu_state_before=gpu_state_before,
                                gpu_state_after=await self.get_gpu_info()
                            )
                            self._schedule_history.append(decision)
                            return result
                
                # 调度失败
                decision = ScheduleDecision(
                    model_id=model_id,
                    decision_time=datetime.now(),
                    result=ScheduleResult.INSUFFICIENT_RESOURCES,
                    reason="资源不足且无法抢占",
                    gpu_state_before=gpu_state_before,
                    gpu_state_after=await self.get_gpu_info()
                )
                self._schedule_history.append(decision)
                
                self.logger.warning(f"模型 {model_id} 调度失败: 资源不足")
                return ScheduleResult.INSUFFICIENT_RESOURCES
                
            except Exception as e:
                self.logger.error(f"调度模型 {model_id} 时出错: {e}")
                return ScheduleResult.FAILED
    
    async def _attempt_preemption(
        self, 
        requesting_model_id: str, 
        resource_req: ResourceRequirement
    ) -> Dict[str, Any]:
        """
        尝试抢占低优先级模型
        
        Args:
            requesting_model_id: 请求资源的模型ID
            resource_req: 资源需求
            
        Returns:
            抢占结果字典
        """
        requesting_model = self._model_states.get(requesting_model_id)
        if not requesting_model:
            return {'success': False, 'reason': '请求模型不存在'}
        
        requesting_priority = requesting_model.config.priority
        
        # 查找可抢占的模型
        preemptable_models = await self._find_preemptable_models(
            requesting_priority, resource_req
        )
        
        if not preemptable_models:
            return {'success': False, 'reason': '没有可抢占的模型'}
        
        # 检查抢占频率限制
        if not self._check_preemption_rate_limit():
            return {'success': False, 'reason': '抢占频率超限'}
        
        # 执行抢占
        preempted_models = []
        total_freed_memory = 0
        
        for model_id, freed_memory in preemptable_models:
            try:
                success = await self._preempt_model(model_id, PreemptionReason.HIGHER_PRIORITY)
                if success:
                    preempted_models.append(model_id)
                    total_freed_memory += freed_memory
                    
                    # 检查是否已释放足够资源
                    if total_freed_memory >= resource_req.gpu_memory:
                        break
                        
            except Exception as e:
                self.logger.error(f"抢占模型 {model_id} 时出错: {e}")
        
        if preempted_models:
            self.logger.info(
                f"成功抢占模型 {preempted_models}，释放内存 {total_freed_memory}MB"
            )
            return {
                'success': True,
                'preempted_models': preempted_models,
                'freed_memory': total_freed_memory,
                'reason': f'抢占 {len(preempted_models)} 个低优先级模型'
            }
        
        return {'success': False, 'reason': '抢占执行失败'}
    
    async def _find_preemptable_models(
        self, 
        requesting_priority: int, 
        resource_req: ResourceRequirement
    ) -> List[Tuple[str, int]]:
        """
        查找可抢占的模型
        
        Args:
            requesting_priority: 请求模型的优先级
            resource_req: 资源需求
            
        Returns:
            (模型ID, 可释放内存)列表，按优先级排序
        """
        preemptable = []
        
        for model_id, model_state in self._model_states.items():
            # 只考虑运行中的模型
            if model_state.status != ModelStatus.RUNNING:
                continue
            
            # 只抢占优先级更低的模型
            if model_state.config.priority >= requesting_priority:
                continue
            
            # 检查优先级差异是否足够
            priority_diff = requesting_priority - model_state.config.priority
            if priority_diff < self._preemption_config['min_priority_diff']:
                continue
            
            # 估算可释放的内存
            if model_state.allocated_resources:
                freed_memory = model_state.allocated_resources.memory_allocated
                preemptable.append((model_id, freed_memory))
        
        # 按优先级排序（优先级低的先抢占）
        preemptable.sort(key=lambda x: self._model_states[x[0]].config.priority)
        
        return preemptable
    
    async def _preempt_model(self, model_id: str, reason: PreemptionReason) -> bool:
        """
        抢占指定模型
        
        Args:
            model_id: 模型ID
            reason: 抢占原因
            
        Returns:
            是否成功
        """
        try:
            model_state = self._model_states.get(model_id)
            if not model_state:
                return False
            
            self.logger.info(f"抢占模型 {model_id}，原因: {reason.value}")
            
            # 更新模型状态为被抢占
            model_state.status = ModelStatus.PREEMPTED
            model_state.preemption_count += 1
            
            # 这里应该调用模型管理器停止模型
            # 暂时模拟停止操作
            await asyncio.sleep(0.1)
            
            # 释放资源分配
            if model_state.allocated_resources:
                await self._release_resources(model_id)
            
            self.logger.info(f"模型 {model_id} 抢占完成")
            return True
            
        except Exception as e:
            self.logger.error(f"抢占模型 {model_id} 失败: {e}")
            return False
    
    def _check_preemption_rate_limit(self) -> bool:
        """检查抢占频率限制"""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        
        # 统计过去一小时的抢占次数
        recent_preemptions = [
            decision for decision in self._schedule_history
            if decision.decision_time > one_hour_ago and decision.preempted_models
        ]
        
        total_preemptions = sum(len(d.preempted_models) for d in recent_preemptions)
        
        return total_preemptions < self._preemption_config['max_preemptions_per_hour']
    
    async def _allocate_resources(
        self, 
        model_id: str, 
        allocation: ResourceAllocation
    ) -> ScheduleResult:
        """
        分配资源给模型
        
        Args:
            model_id: 模型ID
            allocation: 资源分配方案
            
        Returns:
            分配结果
        """
        try:
            model_state = self._model_states.get(model_id)
            if not model_state:
                return ScheduleResult.FAILED
            
            # 更新模型状态
            model_state.allocated_resources = allocation
            model_state.status = ModelStatus.STARTING
            model_state.last_scheduled = datetime.now()
            
            self.logger.info(
                f"为模型 {model_id} 分配资源: GPU {allocation.gpu_devices}, "
                f"内存 {allocation.memory_allocated}MB"
            )
            
            return ScheduleResult.SUCCESS
            
        except Exception as e:
            self.logger.error(f"分配资源给模型 {model_id} 失败: {e}")
            return ScheduleResult.FAILED
    
    async def _release_resources(self, model_id: str) -> bool:
        """
        释放模型资源
        
        Args:
            model_id: 模型ID
            
        Returns:
            是否成功
        """
        try:
            model_state = self._model_states.get(model_id)
            if not model_state:
                return False
            
            if model_state.allocated_resources:
                self.logger.info(
                    f"释放模型 {model_id} 的资源: GPU {model_state.allocated_resources.gpu_devices}"
                )
                model_state.allocated_resources = None
            
            return True
            
        except Exception as e:
            self.logger.error(f"释放模型 {model_id} 资源失败: {e}")
            return False
    
    async def get_gpu_info(self) -> List[GPUInfo]:
        """获取GPU信息"""
        try:
            return await gpu_monitor.get_gpu_info()
        except Exception as e:
            self.logger.error(f"获取GPU信息失败: {e}")
            return []
    
    async def calculate_resource_requirements(self, config: ModelConfig) -> ResourceRequirement:
        """计算资源需求"""
        try:
            return resource_calculator.calculate_model_memory_requirement(config)
        except Exception as e:
            self.logger.error(f"计算资源需求失败: {e}")
            # 返回默认需求
            return ResourceRequirement(
                gpu_memory=8192,
                gpu_devices=config.gpu_devices.copy()
            )
    
    async def find_available_resources(
        self, 
        requirement: ResourceRequirement
    ) -> Optional[ResourceAllocation]:
        """查找可用资源"""
        try:
            gpu_info = await self.get_gpu_info()
            is_valid, errors, allocation = resource_calculator.validate_resource_allocation(
                requirement, gpu_info
            )
            
            if is_valid and allocation:
                return allocation
            else:
                self.logger.debug(f"资源分配验证失败: {errors}")
                return None
                
        except Exception as e:
            self.logger.error(f"查找可用资源失败: {e}")
            return None
    
    async def preempt_lower_priority_models(
        self, 
        required_memory: int, 
        target_gpu: int
    ) -> List[str]:
        """
        抢占指定GPU上的低优先级模型
        
        Args:
            required_memory: 需要的内存大小(MB)
            target_gpu: 目标GPU设备ID
            
        Returns:
            被抢占的模型ID列表
        """
        try:
            preempted_models = []
            freed_memory = 0
            
            # 查找在目标GPU上运行的模型，按优先级排序
            gpu_models = []
            for model_id, model_state in self._model_states.items():
                if (model_state.status == ModelStatus.RUNNING and 
                    model_state.allocated_resources and
                    target_gpu in model_state.allocated_resources.gpu_devices):
                    gpu_models.append((model_id, model_state))
            
            # 按优先级排序（低优先级先抢占）
            gpu_models.sort(key=lambda x: x[1].config.priority)
            
            for model_id, model_state in gpu_models:
                if freed_memory >= required_memory:
                    break
                
                # 抢占模型
                success = await self._preempt_model(model_id, PreemptionReason.RESOURCE_SHORTAGE)
                if success:
                    preempted_models.append(model_id)
                    if model_state.allocated_resources:
                        freed_memory += model_state.allocated_resources.memory_allocated
            
            self.logger.info(
                f"在GPU {target_gpu} 上抢占了 {len(preempted_models)} 个模型，"
                f"释放内存 {freed_memory}MB"
            )
            
            return preempted_models
            
        except Exception as e:
            self.logger.error(f"抢占GPU {target_gpu} 上的模型失败: {e}")
            return []
    
    # 管理接口方法
    
    def register_model(self, config: ModelConfig) -> None:
        """注册模型到调度器"""
        model_state = ModelResourceState(
            model_id=config.id,
            config=config,
            status=ModelStatus.STOPPED
        )
        self._model_states[config.id] = model_state
        self.logger.info(f"注册模型到调度器: {config.id}")
    
    def unregister_model(self, model_id: str) -> None:
        """从调度器注销模型"""
        if model_id in self._model_states:
            del self._model_states[model_id]
            self.logger.info(f"从调度器注销模型: {model_id}")
    
    def update_model_status(self, model_id: str, status: ModelStatus) -> None:
        """更新模型状态"""
        if model_id in self._model_states:
            self._model_states[model_id].status = status
            self.logger.debug(f"更新模型 {model_id} 状态: {status}")
    
    def get_schedule_history(self, limit: int = 100) -> List[ScheduleDecision]:
        """获取调度历史"""
        return self._schedule_history[-limit:]
    
    def get_model_states(self) -> Dict[str, ModelResourceState]:
        """获取所有模型状态"""
        return self._model_states.copy()
    
    def get_preemption_stats(self) -> Dict[str, Any]:
        """获取抢复统计信息"""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(days=1)
        
        # 统计抢占次数
        recent_preemptions = [
            d for d in self._schedule_history
            if d.decision_time > one_hour_ago and d.preempted_models
        ]
        daily_preemptions = [
            d for d in self._schedule_history
            if d.decision_time > one_day_ago and d.preempted_models
        ]
        
        # 统计被抢占最多的模型
        preemption_counts = {}
        for model_id, model_state in self._model_states.items():
            preemption_counts[model_id] = model_state.preemption_count
        
        return {
            'total_preemptions_last_hour': sum(len(d.preempted_models) for d in recent_preemptions),
            'total_preemptions_last_day': sum(len(d.preempted_models) for d in daily_preemptions),
            'preemption_rate_limit': self._preemption_config['max_preemptions_per_hour'],
            'model_preemption_counts': preemption_counts,
            'most_preempted_models': sorted(
                preemption_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]
        }
    
    # 自动重启和恢复机制
    
    async def _recovery_loop(self):
        """恢复循环任务"""
        self.logger.info("启动自动恢复循环")
        
        while True:
            try:
                await asyncio.sleep(self._recovery_config['recovery_check_interval'])
                
                if not self._recovery_config['enable_auto_recovery']:
                    continue
                
                # 检查需要恢复的模型
                await self._check_and_recover_models()
                
                # 检查故障模型
                if self._recovery_config['enable_failure_recovery']:
                    await self._check_failed_models()
                
                # 保存状态
                self._save_state()
                
            except asyncio.CancelledError:
                self.logger.info("恢复循环任务被取消")
                break
            except Exception as e:
                self.logger.error(f"恢复循环出错: {e}")
    
    async def _check_and_recover_models(self):
        """检查并恢复被抢占的模型"""
        try:
            # 查找被抢占的模型
            preempted_models = [
                model_id for model_id, state in self._model_states.items()
                if state.status == ModelStatus.PREEMPTED
            ]
            
            if not preempted_models:
                return
            
            self.logger.debug(f"发现 {len(preempted_models)} 个被抢占的模型")
            
            # 按优先级排序，优先级高的先恢复
            preempted_models.sort(
                key=lambda x: self._model_states[x].config.priority,
                reverse=True
            )
            
            for model_id in preempted_models:
                if await self._should_attempt_recovery(model_id):
                    await self._attempt_model_recovery(model_id, RecoveryReason.RESOURCE_AVAILABLE)
                    
        except Exception as e:
            self.logger.error(f"检查恢复模型时出错: {e}")
    
    async def _check_failed_models(self):
        """检查故障模型并尝试恢复"""
        try:
            now = datetime.now()
            timeout = timedelta(seconds=self._recovery_config['failure_detection_timeout'])
            
            for model_id, state in self._model_states.items():
                # 检查运行中但长时间无响应的模型
                if (state.status == ModelStatus.RUNNING and 
                    state.last_scheduled and
                    now - state.last_scheduled > timeout):
                    
                    self.logger.warning(f"检测到模型 {model_id} 可能故障")
                    
                    # 标记为错误状态
                    state.status = ModelStatus.ERROR
                    
                    # 尝试故障恢复
                    await self._attempt_model_recovery(model_id, RecoveryReason.FAILURE_RECOVERY)
                    
        except Exception as e:
            self.logger.error(f"检查故障模型时出错: {e}")
    
    async def _should_attempt_recovery(self, model_id: str) -> bool:
        """判断是否应该尝试恢复模型"""
        try:
            model_state = self._model_states.get(model_id)
            if not model_state:
                return False
            
            # 检查恢复尝试次数
            recent_attempts = [
                attempt for attempt in self._recovery_attempts
                if (attempt.model_id == model_id and 
                    datetime.now() - attempt.attempt_time < timedelta(hours=1))
            ]
            
            if len(recent_attempts) >= self._recovery_config['max_recovery_attempts']:
                self.logger.debug(f"模型 {model_id} 恢复尝试次数已达上限")
                return False
            
            # 检查最后一次恢复尝试的时间间隔
            if recent_attempts:
                last_attempt = max(recent_attempts, key=lambda x: x.attempt_time)
                min_interval = timedelta(seconds=self._recovery_config['min_recovery_interval'])
                
                if datetime.now() - last_attempt.attempt_time < min_interval:
                    self.logger.debug(f"模型 {model_id} 恢复间隔不足")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"判断恢复条件时出错: {e}")
            return False
    
    async def _attempt_model_recovery(self, model_id: str, reason: RecoveryReason) -> bool:
        """尝试恢复模型"""
        try:
            self.logger.info(f"尝试恢复模型 {model_id}，原因: {reason.value}")
            
            # 记录恢复尝试
            attempt = RecoveryAttempt(
                model_id=model_id,
                attempt_time=datetime.now(),
                reason=reason,
                success=False
            )
            
            # 尝试调度模型
            result = await self.schedule_model(model_id)
            
            if result == ScheduleResult.SUCCESS:
                attempt.success = True
                self.logger.info(f"模型 {model_id} 恢复成功")
                
                # 从恢复队列中移除
                if model_id in self._recovery_queue:
                    self._recovery_queue.remove(model_id)
                    
            else:
                attempt.error_message = f"调度失败: {result.value}"
                self.logger.warning(f"模型 {model_id} 恢复失败: {result.value}")
                
                # 添加到恢复队列
                if model_id not in self._recovery_queue:
                    self._recovery_queue.append(model_id)
            
            self._recovery_attempts.append(attempt)
            return attempt.success
            
        except Exception as e:
            self.logger.error(f"恢复模型 {model_id} 时出错: {e}")
            
            # 记录失败的恢复尝试
            attempt = RecoveryAttempt(
                model_id=model_id,
                attempt_time=datetime.now(),
                reason=reason,
                success=False,
                error_message=str(e)
            )
            self._recovery_attempts.append(attempt)
            return False
    
    async def manual_recover_model(self, model_id: str) -> bool:
        """手动恢复模型"""
        return await self._attempt_model_recovery(model_id, RecoveryReason.MANUAL_RECOVERY)
    
    async def restart_model(self, model_id: str) -> bool:
        """重启模型"""
        try:
            model_state = self._model_states.get(model_id)
            if not model_state:
                self.logger.error(f"模型 {model_id} 不存在")
                return False
            
            self.logger.info(f"重启模型 {model_id}")
            
            # 如果模型正在运行，先停止
            if model_state.status == ModelStatus.RUNNING:
                await self._release_resources(model_id)
                model_state.status = ModelStatus.STOPPED
            
            # 重新调度
            result = await self.schedule_model(model_id)
            return result == ScheduleResult.SUCCESS
            
        except Exception as e:
            self.logger.error(f"重启模型 {model_id} 失败: {e}")
            return False
    
    def add_to_recovery_queue(self, model_id: str) -> None:
        """添加模型到恢复队列"""
        if model_id not in self._recovery_queue:
            self._recovery_queue.append(model_id)
            self.logger.info(f"模型 {model_id} 已添加到恢复队列")
    
    def remove_from_recovery_queue(self, model_id: str) -> None:
        """从恢复队列移除模型"""
        if model_id in self._recovery_queue:
            self._recovery_queue.remove(model_id)
            self.logger.info(f"模型 {model_id} 已从恢复队列移除")
    
    def get_recovery_queue(self) -> List[str]:
        """获取恢复队列"""
        return self._recovery_queue.copy()
    
    def get_recovery_stats(self) -> Dict[str, Any]:
        """获取恢复统计信息"""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(days=1)
        
        # 统计恢复尝试
        recent_attempts = [
            attempt for attempt in self._recovery_attempts
            if attempt.attempt_time > one_hour_ago
        ]
        daily_attempts = [
            attempt for attempt in self._recovery_attempts
            if attempt.attempt_time > one_day_ago
        ]
        
        # 成功率统计
        recent_success = sum(1 for a in recent_attempts if a.success)
        daily_success = sum(1 for a in daily_attempts if a.success)
        
        # 按模型统计恢复次数
        model_recovery_counts = {}
        for attempt in self._recovery_attempts:
            model_id = attempt.model_id
            if model_id not in model_recovery_counts:
                model_recovery_counts[model_id] = {'total': 0, 'success': 0}
            model_recovery_counts[model_id]['total'] += 1
            if attempt.success:
                model_recovery_counts[model_id]['success'] += 1
        
        return {
            'recovery_queue_size': len(self._recovery_queue),
            'recovery_attempts_last_hour': len(recent_attempts),
            'recovery_attempts_last_day': len(daily_attempts),
            'recovery_success_rate_hour': recent_success / len(recent_attempts) if recent_attempts else 0,
            'recovery_success_rate_day': daily_success / len(daily_attempts) if daily_attempts else 0,
            'model_recovery_counts': model_recovery_counts,
            'pending_recovery_models': self._recovery_queue.copy(),
            'auto_recovery_enabled': self._recovery_config['enable_auto_recovery'],
            'failure_recovery_enabled': self._recovery_config['enable_failure_recovery']
        }
    
    # 状态持久化
    
    def _save_state(self):
        """保存调度状态到文件"""
        try:
            # 转换模型状态为可序列化格式
            serializable_states = {}
            for model_id, state in self._model_states.items():
                serializable_states[model_id] = {
                    'model_id': state.model_id,
                    'status': state.status.value,
                    'preemption_count': state.preemption_count,
                    'last_scheduled': state.last_scheduled.isoformat() if state.last_scheduled else None,
                    'allocated_resources': asdict(state.allocated_resources) if state.allocated_resources else None
                }
            
            # 转换调度历史为可序列化格式
            serializable_history = []
            for decision in self._schedule_history[-100:]:  # 只保存最近100条
                serializable_history.append({
                    'model_id': decision.model_id,
                    'decision_time': decision.decision_time.isoformat(),
                    'result': decision.result.value,
                    'preempted_models': decision.preempted_models,
                    'reason': decision.reason
                })
            
            # 创建状态对象
            state = ScheduleState(
                model_states=serializable_states,
                schedule_history=serializable_history,
                recovery_queue=self._recovery_queue.copy(),
                last_saved=datetime.now()
            )
            
            # 保存到文件
            with open(self._state_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(state), f, ensure_ascii=False, indent=2, default=str)
            
            self.logger.debug(f"调度状态已保存到 {self._state_file}")
            
        except Exception as e:
            self.logger.error(f"保存调度状态失败: {e}")
    
    def _load_state(self):
        """从文件加载调度状态"""
        try:
            if not os.path.exists(self._state_file):
                self.logger.info("状态文件不存在，使用默认状态")
                return
            
            with open(self._state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 恢复恢复队列
            self._recovery_queue = data.get('recovery_queue', [])
            
            self.logger.info(f"从 {self._state_file} 加载调度状态成功")
            self.logger.info(f"恢复队列中有 {len(self._recovery_queue)} 个模型")
            
        except Exception as e:
            self.logger.error(f"加载调度状态失败: {e}")
    
    async def shutdown(self):
        """关闭调度器"""
        try:
            self.logger.info("正在关闭资源调度器...")
            
            # 取消恢复任务
            if self._recovery_task:
                self._recovery_task.cancel()
                try:
                    await self._recovery_task
                except asyncio.CancelledError:
                    pass
            
            # 保存最终状态
            self._save_state()
            
            self.logger.info("资源调度器已关闭")
            
        except Exception as e:
            self.logger.error(f"关闭调度器时出错: {e}")
    
    def __del__(self):
        """析构函数"""
        try:
            # 尝试保存状态
            self._save_state()
        except:
            pass


# 全局调度器实例 - 延迟初始化
priority_scheduler = None

def get_priority_scheduler() -> PriorityResourceScheduler:
    """获取全局调度器实例"""
    global priority_scheduler
    if priority_scheduler is None:
        priority_scheduler = PriorityResourceScheduler()
    return priority_scheduler