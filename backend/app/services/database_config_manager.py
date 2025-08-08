"""
基于数据库的配置管理服务
实现配置持久化、验证和迁移逻辑
"""
import json
import logging
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import select, delete, update, and_, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload

from .base import ConfigManagerInterface
from ..models.schemas import ModelConfig, ValidationResult, ResourceRequirement, HealthCheckConfig, RetryPolicy
from ..models.database import (
    ModelConfigDB, SystemConfigDB, ConfigBackupDB, ConfigChangeLogDB, 
    ModelStatusDB, AlertRuleDB
)
from ..models.enums import FrameworkType
from ..core.database import AsyncSessionLocal, get_async_db

logger = logging.getLogger(__name__)

class DatabaseConfigManager(ConfigManagerInterface):
    """基于数据库的配置管理器"""
    
    def __init__(self):
        self.session_factory = AsyncSessionLocal
        logger.info("数据库配置管理器初始化")
    
    async def initialize(self):
        """初始化配置管理器"""
        try:
            logger.info("初始化数据库配置管理器...")
            
            # 检查数据库连接
            async with self.session_factory() as session:
                result = await session.execute(select(1))
                if result.scalar() != 1:
                    raise Exception("数据库连接测试失败")
            
            # 执行配置迁移
            await self._migrate_configs()
            
            # 清理过期数据
            await self._cleanup_old_data()
            
            logger.info("数据库配置管理器初始化完成")
            
        except Exception as e:
            logger.error(f"数据库配置管理器初始化失败: {e}")
            raise
    
    async def save_model_config(self, config: ModelConfig) -> bool:
        """保存模型配置到数据库"""
        try:
            logger.info(f"保存模型配置到数据库: {config.id}")
            
            async with self.session_factory() as session:
                # 检查是否已存在
                existing = await session.execute(
                    select(ModelConfigDB).where(ModelConfigDB.id == config.id)
                )
                existing_config = existing.scalar_one_or_none()
                
                if existing_config:
                    # 记录变更日志
                    await self._log_config_change(
                        session, config.id, "update", 
                        self._db_to_dict(existing_config), 
                        self._config_to_dict(config)
                    )
                    
                    # 更新现有配置
                    await self._update_db_config(session, existing_config, config)
                else:
                    # 创建新配置
                    db_config = self._config_to_db(config)
                    session.add(db_config)
                    
                    # 记录变更日志
                    await self._log_config_change(
                        session, config.id, "create", 
                        None, self._config_to_dict(config)
                    )
                
                await session.commit()
                logger.info(f"模型配置 {config.id} 保存成功")
                return True
                
        except Exception as e:
            logger.error(f"保存模型配置 {config.id} 失败: {e}")
            return False
    
    async def load_model_configs(self) -> List[ModelConfig]:
        """从数据库加载所有模型配置"""
        try:
            async with self.session_factory() as session:
                result = await session.execute(
                    select(ModelConfigDB).where(ModelConfigDB.is_active == True)
                    .order_by(ModelConfigDB.priority.desc(), ModelConfigDB.created_at)
                )
                db_configs = result.scalars().all()
                
                configs = []
                for db_config in db_configs:
                    try:
                        config = self._db_to_config(db_config)
                        configs.append(config)
                    except Exception as e:
                        logger.error(f"反序列化配置 {db_config.id} 失败: {e}")
                        continue
                
                logger.info(f"从数据库加载了 {len(configs)} 个模型配置")
                return configs
                
        except Exception as e:
            logger.error(f"从数据库加载模型配置失败: {e}")
            return []
    
    async def delete_model_config(self, model_id: str) -> bool:
        """从数据库删除模型配置"""
        try:
            logger.info(f"从数据库删除模型配置: {model_id}")
            
            async with self.session_factory() as session:
                # 获取现有配置用于日志记录
                existing = await session.execute(
                    select(ModelConfigDB).where(ModelConfigDB.id == model_id)
                )
                existing_config = existing.scalar_one_or_none()
                
                if existing_config:
                    # 软删除：标记为非活跃
                    existing_config.is_active = False
                    existing_config.updated_at = datetime.now()
                    
                    # 记录变更日志
                    await self._log_config_change(
                        session, model_id, "delete", 
                        self._db_to_dict(existing_config), None
                    )
                    
                    await session.commit()
                    logger.info(f"模型配置 {model_id} 删除成功")
                else:
                    logger.warning(f"模型配置 {model_id} 不存在")
                
                return True
                
        except Exception as e:
            logger.error(f"删除模型配置 {model_id} 失败: {e}")
            return False
    
    async def validate_config(self, config: ModelConfig) -> ValidationResult:
        """验证模型配置"""
        errors = []
        warnings = []
        
        try:
            # 基本字段验证
            if not config.id or not config.id.strip():
                errors.append("模型ID不能为空")
            elif len(config.id) > 255:
                errors.append("模型ID长度不能超过255个字符")
            
            if not config.name or not config.name.strip():
                errors.append("模型名称不能为空")
            elif len(config.name) > 255:
                errors.append("模型名称长度不能超过255个字符")
            
            if not config.model_path or not config.model_path.strip():
                errors.append("模型路径不能为空")
            
            # 优先级验证
            if config.priority < 1 or config.priority > 10:
                errors.append("优先级必须在1-10之间")
            
            # 检查ID唯一性
            if config.id:
                async with self.session_factory() as session:
                    existing = await session.execute(
                        select(ModelConfigDB).where(
                            and_(
                                ModelConfigDB.id == config.id,
                                ModelConfigDB.is_active == True
                            )
                        )
                    )
                    if existing.scalar_one_or_none():
                        warnings.append(f"模型ID {config.id} 已存在，将更新现有配置")
            
            # GPU设备验证
            for gpu_id in config.gpu_devices:
                if gpu_id < 0:
                    errors.append(f"无效的GPU设备ID: {gpu_id}")
            
            # 资源需求验证
            if config.resource_requirements.gpu_memory <= 0:
                errors.append("GPU内存需求必须大于0")
            
            if config.resource_requirements.gpu_memory > 80 * 1024:  # 80GB
                warnings.append("GPU内存需求超过80GB，请确认是否正确")
            
            # 健康检查配置验证
            if config.health_check.enabled:
                if config.health_check.interval <= 0:
                    errors.append("健康检查间隔必须大于0")
                
                if config.health_check.timeout <= 0:
                    errors.append("健康检查超时时间必须大于0")
                
                if config.health_check.timeout >= config.health_check.interval:
                    warnings.append("健康检查超时时间不应大于等于检查间隔")
                
                if config.health_check.max_failures <= 0:
                    errors.append("最大失败次数必须大于0")
            
            # 重试策略验证
            if config.retry_policy.enabled:
                if config.retry_policy.max_attempts <= 0:
                    errors.append("最大重试次数必须大于0")
                
                if config.retry_policy.initial_delay < 0:
                    errors.append("初始延迟不能为负数")
                
                if config.retry_policy.max_delay < config.retry_policy.initial_delay:
                    errors.append("最大延迟不能小于初始延迟")
                
                if config.retry_policy.backoff_factor <= 0:
                    errors.append("退避因子必须大于0")
            
            # 框架特定参数验证
            if config.framework == FrameworkType.LLAMA_CPP:
                self._validate_llama_cpp_params(config.parameters, errors, warnings)
            elif config.framework == FrameworkType.VLLM:
                self._validate_vllm_params(config.parameters, errors, warnings)
            
        except Exception as e:
            errors.append(f"配置验证过程中发生异常: {str(e)}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    async def backup_configs(self) -> str:
        """备份配置到数据库"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"models_backup_{timestamp}"
            
            async with self.session_factory() as session:
                # 获取所有活跃配置
                result = await session.execute(
                    select(ModelConfigDB).where(ModelConfigDB.is_active == True)
                )
                configs = result.scalars().all()
                
                # 序列化配置数据
                backup_data = {
                    "timestamp": timestamp,
                    "version": "1.0",
                    "configs": [self._db_to_dict(config) for config in configs]
                }
                
                backup_json = json.dumps(backup_data, ensure_ascii=False, indent=2)
                backup_size = len(backup_json.encode('utf-8'))
                
                # 计算校验和
                checksum = hashlib.sha256(backup_json.encode('utf-8')).hexdigest()
                
                # 创建备份记录
                backup_record = ConfigBackupDB(
                    backup_name=backup_name,
                    backup_type="model_configs",
                    backup_data=backup_json,
                    backup_size=backup_size,
                    checksum=checksum,
                    description=f"模型配置自动备份，包含 {len(configs)} 个配置"
                )
                
                session.add(backup_record)
                await session.commit()
                
                logger.info(f"配置备份成功: {backup_name}")
                return backup_name
                
        except Exception as e:
            logger.error(f"备份配置失败: {e}")
            return ""
    
    async def restore_configs(self, backup_name: str) -> bool:
        """从备份恢复配置"""
        try:
            logger.info(f"从备份恢复配置: {backup_name}")
            
            async with self.session_factory() as session:
                # 获取备份记录
                result = await session.execute(
                    select(ConfigBackupDB).where(ConfigBackupDB.backup_name == backup_name)
                )
                backup_record = result.scalar_one_or_none()
                
                if not backup_record:
                    logger.error(f"备份记录不存在: {backup_name}")
                    return False
                
                # 验证备份数据完整性
                backup_json = backup_record.backup_data
                checksum = hashlib.sha256(backup_json.encode('utf-8')).hexdigest()
                
                if checksum != backup_record.checksum:
                    logger.error(f"备份数据校验失败: {backup_name}")
                    return False
                
                # 解析备份数据
                backup_data = json.loads(backup_json)
                configs_data = backup_data.get("configs", [])
                
                # 创建当前配置的备份
                current_backup = await self.backup_configs()
                logger.info(f"当前配置已备份到: {current_backup}")
                
                # 恢复配置
                restored_count = 0
                for config_data in configs_data:
                    try:
                        # 转换为ModelConfig对象
                        config = self._dict_to_config(config_data)
                        
                        # 保存配置
                        if await self.save_model_config(config):
                            restored_count += 1
                    except Exception as e:
                        logger.error(f"恢复配置 {config_data.get('id', 'unknown')} 失败: {e}")
                        continue
                
                logger.info(f"配置恢复完成，成功恢复 {restored_count}/{len(configs_data)} 个配置")
                return restored_count > 0
                
        except Exception as e:
            logger.error(f"恢复配置失败: {e}")
            return False
    
    async def list_backups(self) -> List[Dict[str, Any]]:
        """列出所有备份"""
        try:
            async with self.session_factory() as session:
                result = await session.execute(
                    select(ConfigBackupDB)
                    .order_by(ConfigBackupDB.created_at.desc())
                )
                backup_records = result.scalars().all()
                
                backups = []
                for record in backup_records:
                    backups.append({
                        "backup_name": record.backup_name,
                        "backup_type": record.backup_type,
                        "backup_size": record.backup_size,
                        "description": record.description,
                        "created_at": record.created_at,
                        "checksum": record.checksum
                    })
                
                return backups
                
        except Exception as e:
            logger.error(f"列出备份失败: {e}")
            return []
    
    async def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """清理旧的备份记录"""
        try:
            async with self.session_factory() as session:
                # 获取所有备份，按创建时间倒序
                result = await session.execute(
                    select(ConfigBackupDB)
                    .order_by(ConfigBackupDB.created_at.desc())
                )
                all_backups = result.scalars().all()
                
                if len(all_backups) <= keep_count:
                    return 0
                
                # 删除多余的备份
                old_backups = all_backups[keep_count:]
                deleted_count = 0
                
                for backup in old_backups:
                    await session.delete(backup)
                    deleted_count += 1
                    logger.info(f"删除旧备份: {backup.backup_name}")
                
                await session.commit()
                logger.info(f"清理完成，删除了 {deleted_count} 个旧备份")
                return deleted_count
                
        except Exception as e:
            logger.error(f"清理备份失败: {e}")
            return 0
    
    # 私有辅助方法
    
    def _config_to_db(self, config: ModelConfig) -> ModelConfigDB:
        """将ModelConfig转换为数据库模型"""
        return ModelConfigDB(
            id=config.id,
            name=config.name,
            framework=config.framework.value,
            model_path=config.model_path,
            priority=config.priority,
            gpu_devices=config.gpu_devices,
            parameters=config.parameters,
            gpu_memory=config.resource_requirements.gpu_memory,
            cpu_cores=config.resource_requirements.cpu_cores,
            system_memory=config.resource_requirements.system_memory,
            health_check_enabled=config.health_check.enabled,
            health_check_interval=config.health_check.interval,
            health_check_timeout=config.health_check.timeout,
            health_check_max_failures=config.health_check.max_failures,
            health_check_endpoint=config.health_check.endpoint,
            retry_enabled=config.retry_policy.enabled,
            retry_max_attempts=config.retry_policy.max_attempts,
            retry_initial_delay=config.retry_policy.initial_delay,
            retry_max_delay=config.retry_policy.max_delay,
            retry_backoff_factor=config.retry_policy.backoff_factor,
            created_at=config.created_at or datetime.now(),
            updated_at=config.updated_at or datetime.now()
        )
    
    def _db_to_config(self, db_config: ModelConfigDB) -> ModelConfig:
        """将数据库模型转换为ModelConfig"""
        resource_requirements = ResourceRequirement(
            gpu_memory=db_config.gpu_memory,
            gpu_devices=db_config.gpu_devices or [],
            cpu_cores=db_config.cpu_cores,
            system_memory=db_config.system_memory
        )
        
        health_check = HealthCheckConfig(
            enabled=db_config.health_check_enabled,
            interval=db_config.health_check_interval,
            timeout=db_config.health_check_timeout,
            max_failures=db_config.health_check_max_failures,
            endpoint=db_config.health_check_endpoint
        )
        
        retry_policy = RetryPolicy(
            enabled=db_config.retry_enabled,
            max_attempts=db_config.retry_max_attempts,
            initial_delay=db_config.retry_initial_delay,
            max_delay=db_config.retry_max_delay,
            backoff_factor=db_config.retry_backoff_factor
        )
        
        return ModelConfig(
            id=db_config.id,
            name=db_config.name,
            framework=FrameworkType(db_config.framework),
            model_path=db_config.model_path,
            priority=db_config.priority,
            gpu_devices=db_config.gpu_devices or [],
            parameters=db_config.parameters or {},
            resource_requirements=resource_requirements,
            health_check=health_check,
            retry_policy=retry_policy,
            created_at=db_config.created_at,
            updated_at=db_config.updated_at
        )
    
    async def _update_db_config(self, session, db_config: ModelConfigDB, config: ModelConfig):
        """更新数据库配置记录"""
        db_config.name = config.name
        db_config.framework = config.framework.value
        db_config.model_path = config.model_path
        db_config.priority = config.priority
        db_config.gpu_devices = config.gpu_devices
        db_config.parameters = config.parameters
        db_config.gpu_memory = config.resource_requirements.gpu_memory
        db_config.cpu_cores = config.resource_requirements.cpu_cores
        db_config.system_memory = config.resource_requirements.system_memory
        db_config.health_check_enabled = config.health_check.enabled
        db_config.health_check_interval = config.health_check.interval
        db_config.health_check_timeout = config.health_check.timeout
        db_config.health_check_max_failures = config.health_check.max_failures
        db_config.health_check_endpoint = config.health_check.endpoint
        db_config.retry_enabled = config.retry_policy.enabled
        db_config.retry_max_attempts = config.retry_policy.max_attempts
        db_config.retry_initial_delay = config.retry_policy.initial_delay
        db_config.retry_max_delay = config.retry_policy.max_delay
        db_config.retry_backoff_factor = config.retry_policy.backoff_factor
        db_config.updated_at = datetime.now()
    
    def _config_to_dict(self, config: ModelConfig) -> Dict[str, Any]:
        """将ModelConfig转换为字典"""
        return {
            "id": config.id,
            "name": config.name,
            "framework": config.framework.value,
            "model_path": config.model_path,
            "priority": config.priority,
            "gpu_devices": config.gpu_devices,
            "parameters": config.parameters,
            "resource_requirements": {
                "gpu_memory": config.resource_requirements.gpu_memory,
                "gpu_devices": config.resource_requirements.gpu_devices,
                "cpu_cores": config.resource_requirements.cpu_cores,
                "system_memory": config.resource_requirements.system_memory
            },
            "health_check": {
                "enabled": config.health_check.enabled,
                "interval": config.health_check.interval,
                "timeout": config.health_check.timeout,
                "max_failures": config.health_check.max_failures,
                "endpoint": config.health_check.endpoint
            },
            "retry_policy": {
                "enabled": config.retry_policy.enabled,
                "max_attempts": config.retry_policy.max_attempts,
                "initial_delay": config.retry_policy.initial_delay,
                "max_delay": config.retry_policy.max_delay,
                "backoff_factor": config.retry_policy.backoff_factor
            },
            "created_at": config.created_at.isoformat() if config.created_at else None,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None
        }
    
    def _db_to_dict(self, db_config: ModelConfigDB) -> Dict[str, Any]:
        """将数据库模型转换为字典"""
        return {
            "id": db_config.id,
            "name": db_config.name,
            "framework": db_config.framework,
            "model_path": db_config.model_path,
            "priority": db_config.priority,
            "gpu_devices": db_config.gpu_devices,
            "parameters": db_config.parameters,
            "gpu_memory": db_config.gpu_memory,
            "cpu_cores": db_config.cpu_cores,
            "system_memory": db_config.system_memory,
            "health_check_enabled": db_config.health_check_enabled,
            "health_check_interval": db_config.health_check_interval,
            "health_check_timeout": db_config.health_check_timeout,
            "health_check_max_failures": db_config.health_check_max_failures,
            "health_check_endpoint": db_config.health_check_endpoint,
            "retry_enabled": db_config.retry_enabled,
            "retry_max_attempts": db_config.retry_max_attempts,
            "retry_initial_delay": db_config.retry_initial_delay,
            "retry_max_delay": db_config.retry_max_delay,
            "retry_backoff_factor": db_config.retry_backoff_factor,
            "is_active": db_config.is_active,
            "created_at": db_config.created_at.isoformat() if db_config.created_at else None,
            "updated_at": db_config.updated_at.isoformat() if db_config.updated_at else None
        }
    
    def _dict_to_config(self, data: Dict[str, Any]) -> ModelConfig:
        """将字典转换为ModelConfig"""
        # 处理时间字段
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        
        updated_at = None
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"])
        
        # 构建资源需求
        if "resource_requirements" in data:
            resource_req_data = data["resource_requirements"]
        else:
            # 兼容旧格式
            resource_req_data = {
                "gpu_memory": data.get("gpu_memory", 0),
                "gpu_devices": data.get("gpu_devices", []),
                "cpu_cores": data.get("cpu_cores"),
                "system_memory": data.get("system_memory")
            }
        
        resource_requirements = ResourceRequirement(
            gpu_memory=resource_req_data.get("gpu_memory", 0),
            gpu_devices=resource_req_data.get("gpu_devices", []),
            cpu_cores=resource_req_data.get("cpu_cores"),
            system_memory=resource_req_data.get("system_memory")
        )
        
        # 构建健康检查配置
        if "health_check" in data:
            health_check_data = data["health_check"]
        else:
            # 兼容旧格式
            health_check_data = {
                "enabled": data.get("health_check_enabled", True),
                "interval": data.get("health_check_interval", 30),
                "timeout": data.get("health_check_timeout", 10),
                "max_failures": data.get("health_check_max_failures", 3),
                "endpoint": data.get("health_check_endpoint")
            }
        
        health_check = HealthCheckConfig(
            enabled=health_check_data.get("enabled", True),
            interval=health_check_data.get("interval", 30),
            timeout=health_check_data.get("timeout", 10),
            max_failures=health_check_data.get("max_failures", 3),
            endpoint=health_check_data.get("endpoint")
        )
        
        # 构建重试策略
        if "retry_policy" in data:
            retry_policy_data = data["retry_policy"]
        else:
            # 兼容旧格式
            retry_policy_data = {
                "enabled": data.get("retry_enabled", True),
                "max_attempts": data.get("retry_max_attempts", 3),
                "initial_delay": data.get("retry_initial_delay", 5),
                "max_delay": data.get("retry_max_delay", 300),
                "backoff_factor": data.get("retry_backoff_factor", 2.0)
            }
        
        retry_policy = RetryPolicy(
            enabled=retry_policy_data.get("enabled", True),
            max_attempts=retry_policy_data.get("max_attempts", 3),
            initial_delay=retry_policy_data.get("initial_delay", 5),
            max_delay=retry_policy_data.get("max_delay", 300),
            backoff_factor=retry_policy_data.get("backoff_factor", 2.0)
        )
        
        return ModelConfig(
            id=data["id"],
            name=data["name"],
            framework=FrameworkType(data["framework"]),
            model_path=data["model_path"],
            priority=data["priority"],
            gpu_devices=data.get("gpu_devices", []),
            parameters=data.get("parameters", {}),
            resource_requirements=resource_requirements,
            health_check=health_check,
            retry_policy=retry_policy,
            created_at=created_at,
            updated_at=updated_at
        )
    
    async def _log_config_change(self, session, model_id: str, change_type: str, 
                                old_value: Optional[Dict], new_value: Optional[Dict]):
        """记录配置变更日志"""
        try:
            # 计算变更字段
            changed_fields = []
            if old_value and new_value:
                for key in new_value:
                    if key not in old_value or old_value[key] != new_value[key]:
                        changed_fields.append(key)
            
            change_log = ConfigChangeLogDB(
                model_id=model_id,
                change_type=change_type,
                old_value=old_value,
                new_value=new_value,
                changed_fields=changed_fields,
                change_reason=f"通过API {change_type} 配置",
                changed_by="system",
                created_at=datetime.now()
            )
            
            session.add(change_log)
            
        except Exception as e:
            logger.error(f"记录配置变更日志失败: {e}")
    
    async def _migrate_configs(self):
        """执行配置迁移"""
        try:
            # 这里可以添加配置迁移逻辑
            # 例如：从旧版本格式迁移到新版本格式
            logger.info("配置迁移检查完成")
        except Exception as e:
            logger.error(f"配置迁移失败: {e}")
    
    async def _cleanup_old_data(self):
        """清理过期数据"""
        try:
            async with self.session_factory() as session:
                # 清理30天前的变更日志
                cutoff_date = datetime.now().replace(day=datetime.now().day - 30)
                await session.execute(
                    delete(ConfigChangeLogDB).where(
                        ConfigChangeLogDB.created_at < cutoff_date
                    )
                )
                
                # 清理旧的备份（保留最新20个）
                await self.cleanup_old_backups(20)
                
                await session.commit()
                logger.info("过期数据清理完成")
                
        except Exception as e:
            logger.error(f"清理过期数据失败: {e}")
    
    def _validate_llama_cpp_params(self, params: Dict[str, Any], errors: List[str], warnings: List[str]):
        """验证llama.cpp特定参数"""
        # 检查端口
        if "port" in params:
            port = params["port"]
            if not isinstance(port, int) or port <= 0 or port > 65535:
                errors.append("端口必须是1-65535之间的整数")
        
        # 检查上下文长度
        if "ctx_size" in params:
            ctx_size = params["ctx_size"]
            if not isinstance(ctx_size, int) or ctx_size <= 0:
                errors.append("上下文长度必须是正整数")
            elif ctx_size > 32768:
                warnings.append("上下文长度超过32768，可能会消耗大量内存")
        
        # 检查线程数
        if "threads" in params:
            threads = params["threads"]
            if not isinstance(threads, int) or threads <= 0:
                errors.append("线程数必须是正整数")
    
    def _validate_vllm_params(self, params: Dict[str, Any], errors: List[str], warnings: List[str]):
        """验证vLLM特定参数"""
        # 检查端口
        if "port" in params:
            port = params["port"]
            if not isinstance(port, int) or port <= 0 or port > 65535:
                errors.append("端口必须是1-65535之间的整数")
        
        # 检查最大序列长度
        if "max_model_len" in params:
            max_len = params["max_model_len"]
            if not isinstance(max_len, int) or max_len <= 0:
                errors.append("最大模型长度必须是正整数")
        
        # 检查GPU内存利用率
        if "gpu_memory_utilization" in params:
            gpu_util = params["gpu_memory_utilization"]
            if not isinstance(gpu_util, (int, float)) or gpu_util <= 0 or gpu_util > 1:
                errors.append("GPU内存利用率必须是0-1之间的数值")