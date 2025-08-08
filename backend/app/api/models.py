"""
模型管理API端点
实现模型CRUD操作、生命周期管理和状态查询功能
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse

from ..models.schemas import (
    ModelConfig, ModelInfo, ModelStatus, ValidationResult,
    HealthStatus, ResourceRequirement
)
from ..services.model_manager import ModelManager
from ..core.dependencies import get_model_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/models", tags=["models"])

@router.get("/", response_model=List[ModelInfo])
async def list_models(
    model_manager: ModelManager = Depends(get_model_manager)
):
    """
    获取所有模型列表
    
    返回系统中所有已配置模型的信息，包括状态、资源使用等
    """
    try:
        models = await model_manager.list_models()
        logger.info(f"获取模型列表成功，共 {len(models)} 个模型")
        return models
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模型列表失败: {str(e)}"
        )

@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_model(
    config: ModelConfig,
    model_manager: ModelManager = Depends(get_model_manager)
):
    """
    创建新模型配置
    
    根据提供的配置信息创建新的模型实例，包括验证配置有效性
    """
    try:
        model_id = await model_manager.create_model(config)
        logger.info(f"创建模型成功: {model_id}")
        return {
            "success": True,
            "message": "模型配置创建成功",
            "model_id": model_id
        }
    except ValueError as e:
        logger.warning(f"创建模型失败，配置错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"配置验证失败: {str(e)}"
        )
    except Exception as e:
        logger.error(f"创建模型失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建模型失败: {str(e)}"
        )

@router.get("/{model_id}", response_model=ModelInfo)
async def get_model(
    model_id: str,
    model_manager: ModelManager = Depends(get_model_manager)
):
    """
    获取指定模型信息
    
    返回指定模型的详细信息，包括配置、状态、资源使用等
    """
    try:
        # 获取模型配置
        config = await model_manager.get_model_config(model_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"模型不存在: {model_id}"
            )
        
        # 获取模型状态
        model_status = await model_manager.get_model_status(model_id)
        
        # 获取API端点（如果模型正在运行）
        api_endpoint = None
        if model_status == ModelStatus.RUNNING:
            # 这里可以从适配器获取实际的API端点
            api_endpoint = f"http://localhost:{config.parameters.get('port', 8000)}"
        
        # 构建模型信息
        model_info = ModelInfo(
            id=config.id,
            name=config.name,
            framework=config.framework,
            status=model_status,
            priority=config.priority,
            gpu_devices=config.gpu_devices,
            memory_usage=config.resource_requirements.gpu_memory if model_status == ModelStatus.RUNNING else None,
            api_endpoint=api_endpoint,
            uptime=None,  # 需要从适配器获取
            last_health_check=None  # 需要从健康检查器获取
        )
        
        logger.info(f"获取模型信息成功: {model_id}")
        return model_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模型信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模型信息失败: {str(e)}"
        )

@router.put("/{model_id}", response_model=dict)
async def update_model(
    model_id: str,
    config: ModelConfig,
    model_manager: ModelManager = Depends(get_model_manager)
):
    """
    更新模型配置
    
    更新指定模型的配置信息，如果模型正在运行会自动重启以应用新配置
    """
    try:
        # 确保配置ID与路径参数一致
        config.id = model_id
        
        success = await model_manager.update_model_config(model_id, config)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"模型不存在或更新失败: {model_id}"
            )
        
        # 获取更新后的模型配置
        updated_config = await model_manager.get_model_config(model_id)
        if not updated_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"无法获取更新后的模型配置: {model_id}"
            )
        
        logger.info(f"更新模型配置成功: {model_id}")
        # 返回更新后的模型配置
        return updated_config.model_dump()
        
    except ValueError as e:
        logger.warning(f"更新模型失败，配置错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"配置验证失败: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新模型配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新模型配置失败: {str(e)}"
        )

@router.delete("/{model_id}", response_model=dict)
async def delete_model(
    model_id: str,
    model_manager: ModelManager = Depends(get_model_manager)
):
    """
    删除模型配置
    
    删除指定的模型配置，如果模型正在运行会先停止模型
    """
    try:
        success = await model_manager.delete_model(model_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"模型不存在或删除失败: {model_id}"
            )
        
        logger.info(f"删除模型成功: {model_id}")
        return {
            "success": True,
            "message": "模型删除成功",
            "model_id": model_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除模型失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除模型失败: {str(e)}"
        )

@router.post("/{model_id}/start", response_model=dict)
async def start_model(
    model_id: str,
    model_manager: ModelManager = Depends(get_model_manager)
):
    """
    启动模型
    
    启动指定的模型实例，包括资源分配和健康检查
    """
    try:
        success = await model_manager.start_model(model_id)
        if not success:
            # 获取更详细的错误信息
            config = await model_manager.get_model_config(model_id)
            if not config:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"模型不存在: {model_id}"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"模型启动失败，请检查资源可用性和配置"
                )
        
        logger.info(f"启动模型成功: {model_id}")
        return {
            "success": True,
            "message": "模型启动成功",
            "model_id": model_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动模型失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启动模型失败: {str(e)}"
        )

@router.post("/{model_id}/stop", response_model=dict)
async def stop_model(
    model_id: str,
    model_manager: ModelManager = Depends(get_model_manager)
):
    """
    停止模型
    
    停止指定的模型实例，释放占用的资源
    """
    try:
        success = await model_manager.stop_model(model_id)
        if not success:
            # 获取更详细的错误信息
            config = await model_manager.get_model_config(model_id)
            if not config:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"模型不存在: {model_id}"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"模型停止失败"
                )
        
        logger.info(f"停止模型成功: {model_id}")
        return {
            "success": True,
            "message": "模型停止成功",
            "model_id": model_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"停止模型失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"停止模型失败: {str(e)}"
        )

@router.post("/{model_id}/restart", response_model=dict)
async def restart_model(
    model_id: str,
    model_manager: ModelManager = Depends(get_model_manager)
):
    """
    重启模型
    
    重启指定的模型实例，先停止再启动
    """
    try:
        success = await model_manager.restart_model(model_id)
        if not success:
            # 获取更详细的错误信息
            config = await model_manager.get_model_config(model_id)
            if not config:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"模型不存在: {model_id}"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"模型重启失败"
                )
        
        logger.info(f"重启模型成功: {model_id}")
        return {
            "success": True,
            "message": "模型重启成功",
            "model_id": model_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重启模型失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重启模型失败: {str(e)}"
        )

@router.get("/{model_id}/status", response_model=dict)
async def get_model_status(
    model_id: str,
    model_manager: ModelManager = Depends(get_model_manager)
):
    """
    获取模型状态
    
    返回指定模型的当前运行状态
    """
    try:
        # 检查模型是否存在
        config = await model_manager.get_model_config(model_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"模型不存在: {model_id}"
            )
        
        # 获取模型状态
        model_status = await model_manager.get_model_status(model_id)
        
        # 获取模型健康状态
        health_status = "unknown"
        try:
            if hasattr(model_manager, 'health_checker') and model_manager.health_checker:
                health_status = await model_manager.health_checker.check_model_health(model_id)
            else:
                # 如果没有健康检查器，根据模型状态推断健康状态
                if model_status == "running":
                    health_status = "healthy"
                elif model_status == "stopped":
                    health_status = "stopped"
                else:
                    health_status = "unhealthy"
        except Exception:
            health_status = "unknown"
        
        logger.info(f"获取模型状态成功: {model_id} - {model_status}")
        return {
            "model_id": model_id,
            "status": model_status,
            "health": health_status,
            "timestamp": None  # 可以添加状态更新时间戳
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模型状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模型状态失败: {str(e)}"
        )

@router.get("/{model_id}/health", response_model=dict)
async def get_model_health(
    model_id: str,
    model_manager: ModelManager = Depends(get_model_manager)
):
    """
    获取模型健康状态
    
    返回指定模型的健康检查结果
    """
    try:
        # 检查模型是否存在
        config = await model_manager.get_model_config(model_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"模型不存在: {model_id}"
            )
        
        # 获取健康状态
        health_status = await model_manager.get_model_health(model_id)
        
        # 获取健康检查详细结果
        health_result = await model_manager.get_model_health_result(model_id)
        
        logger.info(f"获取模型健康状态成功: {model_id} - {health_status}")
        return {
            "model_id": model_id,
            "health_status": health_status,
            "health_result": health_result,
            "timestamp": None  # 可以添加检查时间戳
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模型健康状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模型健康状态失败: {str(e)}"
        )

@router.post("/{model_id}/health-check", response_model=dict)
async def manual_health_check(
    model_id: str,
    model_manager: ModelManager = Depends(get_model_manager)
):
    """
    手动执行健康检查
    
    立即对指定模型执行一次健康检查
    """
    try:
        # 检查模型是否存在
        config = await model_manager.get_model_config(model_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"模型不存在: {model_id}"
            )
        
        # 执行手动健康检查
        health_result = await model_manager.manual_health_check(model_id)
        
        logger.info(f"手动健康检查完成: {model_id}")
        return {
            "success": True,
            "message": "健康检查执行完成",
            "model_id": model_id,
            "health_result": health_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"手动健康检查失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"手动健康检查失败: {str(e)}"
        )

@router.get("/{model_id}/config", response_model=ModelConfig)
async def get_model_config(
    model_id: str,
    model_manager: ModelManager = Depends(get_model_manager)
):
    """
    获取模型配置
    
    返回指定模型的完整配置信息
    """
    try:
        config = await model_manager.get_model_config(model_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"模型不存在: {model_id}"
            )
        
        logger.info(f"获取模型配置成功: {model_id}")
        return config
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模型配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模型配置失败: {str(e)}"
        )

@router.post("/validate", response_model=ValidationResult)
async def validate_model_config(
    config: ModelConfig,
    model_manager: ModelManager = Depends(get_model_manager)
):
    """
    验证模型配置
    
    验证提供的模型配置是否有效，不实际创建模型
    """
    try:
        # 调用模型管理器的公共验证方法
        validation_result = await model_manager.validate_model_config(config)
        
        logger.info(f"配置验证完成: {config.id} - {'有效' if validation_result.is_valid else '无效'}")
        return validation_result
        
    except Exception as e:
        logger.error(f"配置验证失败: {e}")
        return ValidationResult(
            is_valid=False,
            errors=[f"验证过程发生异常: {str(e)}"]
        )