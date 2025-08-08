"""
配置管理服务
处理模型配置的持久化、验证和备份恢复
"""
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from .base import ConfigManagerInterface
from ..models.schemas import ModelConfig, ValidationResult
from ..core.config import settings

logger = logging.getLogger(__name__)

class FileConfigManager(ConfigManagerInterface):
    """基于文件的配置管理器"""
    
    def __init__(self, config_dir: str = "configs"):
        self.config_dir = Path(config_dir)
        self.models_config_file = self.config_dir / "models.json"
        self.backup_dir = self.config_dir / "backups"
        
        # 确保目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"配置管理器初始化，配置目录: {self.config_dir}")
    
    async def initialize(self):
        """初始化配置管理器"""
        try:
            logger.info("初始化配置管理器...")
            
            # 检查配置文件完整性
            if self.models_config_file.exists():
                configs = await self.load_model_configs()
                logger.info(f"配置管理器初始化完成，加载了 {len(configs)} 个模型配置")
            else:
                logger.info("配置管理器初始化完成，未找到现有配置文件")
                
        except Exception as e:
            logger.error(f"配置管理器初始化失败: {e}")
            raise
    
    def _serialize_config(self, config: ModelConfig) -> Dict[str, Any]:
        """序列化模型配置为字典"""
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
    
    def _deserialize_config(self, data: Dict[str, Any]) -> ModelConfig:
        """从字典反序列化模型配置"""
        from ..models.schemas import ResourceRequirement, HealthCheckConfig, RetryPolicy
        from ..models.enums import FrameworkType
        
        # 处理时间字段
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        
        updated_at = None
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"])
        
        # 构建资源需求
        resource_req_data = data.get("resource_requirements", {})
        resource_requirements = ResourceRequirement(
            gpu_memory=resource_req_data.get("gpu_memory", 0),
            gpu_devices=resource_req_data.get("gpu_devices", []),
            cpu_cores=resource_req_data.get("cpu_cores"),
            system_memory=resource_req_data.get("system_memory")
        )
        
        # 构建健康检查配置
        health_check_data = data.get("health_check", {})
        health_check = HealthCheckConfig(
            enabled=health_check_data.get("enabled", True),
            interval=health_check_data.get("interval", 30),
            timeout=health_check_data.get("timeout", 10),
            max_failures=health_check_data.get("max_failures", 3),
            endpoint=health_check_data.get("endpoint")
        )
        
        # 构建重试策略
        retry_policy_data = data.get("retry_policy", {})
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
    
    async def save_model_config(self, config: ModelConfig) -> bool:
        """保存模型配置"""
        try:
            logger.info(f"保存模型配置: {config.id}")
            
            # 加载现有配置
            configs = {}
            if self.models_config_file.exists():
                with open(self.models_config_file, 'r', encoding='utf-8') as f:
                    configs = json.load(f)
            
            # 更新配置
            configs[config.id] = self._serialize_config(config)
            
            # 写入文件
            with open(self.models_config_file, 'w', encoding='utf-8') as f:
                json.dump(configs, f, ensure_ascii=False, indent=2)
            
            logger.info(f"模型配置 {config.id} 保存成功")
            return True
            
        except Exception as e:
            logger.error(f"保存模型配置 {config.id} 失败: {e}")
            return False
    
    async def load_model_configs(self) -> List[ModelConfig]:
        """加载所有模型配置"""
        try:
            if not self.models_config_file.exists():
                logger.info("配置文件不存在，返回空配置列表")
                return []
            
            with open(self.models_config_file, 'r', encoding='utf-8') as f:
                configs_data = json.load(f)
            
            configs = []
            for config_id, config_data in configs_data.items():
                try:
                    config = self._deserialize_config(config_data)
                    configs.append(config)
                except Exception as e:
                    logger.error(f"反序列化配置 {config_id} 失败: {e}")
                    continue
            
            logger.info(f"加载了 {len(configs)} 个模型配置")
            return configs
            
        except Exception as e:
            logger.error(f"加载模型配置失败: {e}")
            return []
    
    async def delete_model_config(self, model_id: str) -> bool:
        """删除模型配置"""
        try:
            logger.info(f"删除模型配置: {model_id}")
            
            if not self.models_config_file.exists():
                logger.warning("配置文件不存在")
                return True
            
            # 加载现有配置
            with open(self.models_config_file, 'r', encoding='utf-8') as f:
                configs = json.load(f)
            
            # 删除指定配置
            if model_id in configs:
                del configs[model_id]
                
                # 写回文件
                with open(self.models_config_file, 'w', encoding='utf-8') as f:
                    json.dump(configs, f, ensure_ascii=False, indent=2)
                
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
            
            if not config.name or not config.name.strip():
                errors.append("模型名称不能为空")
            
            if not config.model_path or not config.model_path.strip():
                errors.append("模型路径不能为空")
            
            # 优先级验证
            if config.priority < 1 or config.priority > 10:
                errors.append("优先级必须在1-10之间")
            
            # 模型路径验证
            model_path = Path(config.model_path)
            if not model_path.exists():
                errors.append(f"模型文件不存在: {config.model_path}")
            elif model_path.is_dir():
                # 检查目录是否包含模型文件
                model_files = list(model_path.glob("*.bin")) + list(model_path.glob("*.gguf")) + list(model_path.glob("*.safetensors"))
                if not model_files:
                    warnings.append(f"模型目录中未找到常见的模型文件格式")
            
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
            
            # 参数验证（框架特定）
            if config.framework.value == "llama_cpp":
                self._validate_llama_cpp_params(config.parameters, errors, warnings)
            elif config.framework.value == "vllm":
                self._validate_vllm_params(config.parameters, errors, warnings)
            
        except Exception as e:
            errors.append(f"配置验证过程中发生异常: {str(e)}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
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
    
    async def backup_configs(self) -> str:
        """备份配置文件"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"models_backup_{timestamp}.json"
            backup_path = self.backup_dir / backup_filename
            
            if self.models_config_file.exists():
                shutil.copy2(self.models_config_file, backup_path)
                logger.info(f"配置备份成功: {backup_path}")
                return str(backup_path)
            else:
                logger.warning("配置文件不存在，无法备份")
                return ""
                
        except Exception as e:
            logger.error(f"备份配置失败: {e}")
            return ""
    
    async def restore_configs(self, backup_path: str) -> bool:
        """从备份恢复配置"""
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                logger.error(f"备份文件不存在: {backup_path}")
                return False
            
            # 验证备份文件格式
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # 创建当前配置的备份
            if self.models_config_file.exists():
                current_backup = await self.backup_configs()
                logger.info(f"当前配置已备份到: {current_backup}")
            
            # 恢复配置
            shutil.copy2(backup_file, self.models_config_file)
            logger.info(f"配置恢复成功，从: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"恢复配置失败: {e}")
            return False
    
    async def list_backups(self) -> List[Dict[str, Any]]:
        """列出所有备份文件"""
        try:
            backups = []
            for backup_file in self.backup_dir.glob("models_backup_*.json"):
                stat = backup_file.stat()
                backups.append({
                    "filename": backup_file.name,
                    "path": str(backup_file),
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime),
                    "modified_at": datetime.fromtimestamp(stat.st_mtime)
                })
            
            # 按创建时间倒序排列
            backups.sort(key=lambda x: x["created_at"], reverse=True)
            return backups
            
        except Exception as e:
            logger.error(f"列出备份文件失败: {e}")
            return []
    
    async def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """清理旧的备份文件，保留最新的指定数量"""
        try:
            backups = await self.list_backups()
            if len(backups) <= keep_count:
                return 0
            
            # 删除多余的备份
            deleted_count = 0
            for backup in backups[keep_count:]:
                try:
                    Path(backup["path"]).unlink()
                    deleted_count += 1
                    logger.info(f"删除旧备份: {backup['filename']}")
                except Exception as e:
                    logger.error(f"删除备份文件失败: {e}")
            
            logger.info(f"清理完成，删除了 {deleted_count} 个旧备份文件")
            return deleted_count
            
        except Exception as e:
            logger.error(f"清理备份文件失败: {e}")
            return 0