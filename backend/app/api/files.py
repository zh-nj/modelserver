"""
文件浏览API端点
提供服务器端文件系统浏览功能，用于模型文件选择
"""
import os
import logging
from typing import List, Dict, Any
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse

from ..core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/files", tags=["files"])

# 支持的模型文件扩展名
MODEL_EXTENSIONS = {
    '.gguf', '.bin', '.safetensors', '.pt', '.pth', 
    '.onnx', '.tflite', '.h5', '.pkl', '.joblib'
}

def get_allowed_paths() -> List[str]:
    """
    获取允许浏览的路径列表，支持路径展开
    """
    allowed_paths = []
    for path in settings.allowed_browse_paths:
        try:
            # 展开用户目录和相对路径
            expanded_path = os.path.expanduser(path)
            expanded_path = os.path.abspath(expanded_path)
            allowed_paths.append(expanded_path)
        except Exception as e:
            logger.warning(f"展开路径 {path} 失败: {e}")
            continue
    return allowed_paths

def is_safe_path(path: str) -> bool:
    """
    检查路径是否安全，防止目录遍历攻击
    """
    try:
        # 解析路径
        resolved_path = os.path.abspath(path)
        
        # 获取允许的路径列表
        allowed_paths = get_allowed_paths()
        
        # 检查是否在允许的根目录下
        for allowed_root in allowed_paths:
            if resolved_path.startswith(allowed_root):
                return True
        
        # 如果启用了根目录浏览且路径是根目录，也允许
        if settings.enable_root_browse and (resolved_path == "/" or resolved_path == os.path.abspath("/")):
            return True
            
        return False
    except Exception:
        return False

def get_file_info(file_path: Path) -> Dict[str, Any]:
    """
    获取文件信息
    """
    try:
        stat = file_path.stat()
        return {
            "name": file_path.name,
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "is_model": file_path.suffix.lower() in MODEL_EXTENSIONS
        }
    except Exception:
        return {
            "name": file_path.name,
            "size": 0,
            "modified": 0,
            "is_model": False
        }

@router.get("/browse")
async def browse_directory(
    path: str = Query("/", description="要浏览的目录路径")
):
    """
    浏览服务器端目录
    
    返回指定目录下的文件和子目录列表
    """
    try:
        # 安全检查
        if not is_safe_path(path):
            # 如果路径不安全，返回允许的根目录列表
            logger.warning(f"尝试访问不安全路径: {path}")
            allowed_paths = get_allowed_paths()
            existing_roots = [root for root in allowed_paths if os.path.exists(root)]
            return {
                "path": "/",
                "directories": [],
                "files": [],
                "allowed_roots": existing_roots,
                "message": "请选择允许的根目录"
            }
        
        # 转换为Path对象
        dir_path = Path(path)
        
        # 检查目录是否存在
        if not dir_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"目录不存在: {path}"
            )
        
        if not dir_path.is_dir():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"路径不是目录: {path}"
            )
        
        directories = []
        files = []
        
        try:
            # 遍历目录内容
            for item in sorted(dir_path.iterdir()):
                try:
                    if item.is_dir():
                        # 跳过隐藏目录和系统目录
                        if not item.name.startswith('.') and item.name not in ['__pycache__', 'node_modules']:
                            directories.append({
                                "name": item.name,
                                "path": str(item),
                                "accessible": os.access(item, os.R_OK)
                            })
                    elif item.is_file():
                        # 只显示模型文件和一些常见文件
                        if (item.suffix.lower() in MODEL_EXTENSIONS or 
                            item.name.lower() in ['readme.md', 'readme.txt', 'config.json']):
                            file_info = get_file_info(item)
                            file_info["path"] = str(item)
                            files.append(file_info)
                except PermissionError:
                    # 跳过无权限访问的文件/目录
                    continue
                except Exception as e:
                    logger.warning(f"处理文件 {item} 时出错: {e}")
                    continue
                    
        except PermissionError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"没有权限访问目录: {path}"
            )
        
        logger.info(f"浏览目录 {path}: {len(directories)} 个子目录, {len(files)} 个文件")
        
        return {
            "path": str(dir_path),
            "directories": directories,
            "files": files,
            "parent": str(dir_path.parent) if dir_path.parent != dir_path else None,
            "allowed_roots": get_allowed_paths()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"浏览目录失败 {path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"浏览目录失败: {str(e)}"
        )

@router.get("/validate")
async def validate_file_path(
    path: str = Query(..., description="要验证的文件路径")
):
    """
    验证文件路径是否存在且可访问
    """
    try:
        # 安全检查
        if not is_safe_path(path):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="路径不在允许的范围内"
            )
        
        file_path = Path(path)
        
        if not file_path.exists():
            return {
                "valid": False,
                "message": "文件不存在",
                "path": path
            }
        
        if not file_path.is_file():
            return {
                "valid": False,
                "message": "路径不是文件",
                "path": path
            }
        
        # 检查是否是模型文件
        is_model = file_path.suffix.lower() in MODEL_EXTENSIONS
        
        # 获取文件信息
        file_info = get_file_info(file_path)
        
        return {
            "valid": True,
            "is_model": is_model,
            "file_info": file_info,
            "path": path
        }
        
    except Exception as e:
        logger.error(f"验证文件路径失败 {path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"验证文件路径失败: {str(e)}"
        )

@router.get("/roots")
async def get_allowed_roots():
    """
    获取允许浏览的根目录列表
    """
    try:
        available_roots = []
        allowed_paths = get_allowed_paths()
        
        for root_path in allowed_paths:
            try:
                path = Path(root_path)
                if path.exists() and path.is_dir():
                    available_roots.append({
                        "path": str(path.resolve()),
                        "name": path.name or str(path),
                        "accessible": os.access(path, os.R_OK)
                    })
            except Exception as e:
                logger.warning(f"检查根目录 {root_path} 时出错: {e}")
                continue
        
        # 如果启用了根目录浏览，添加系统根目录
        if settings.enable_root_browse:
            try:
                root_path = Path("/")
                if root_path.exists() and root_path.is_dir():
                    available_roots.insert(0, {
                        "path": "/",
                        "name": "系统根目录",
                        "accessible": os.access(root_path, os.R_OK)
                    })
            except Exception as e:
                logger.warning(f"检查系统根目录时出错: {e}")
        
        return {
            "roots": available_roots,
            "total": len(available_roots),
            "settings": {
                "enable_root_browse": settings.enable_root_browse,
                "max_browse_depth": settings.max_browse_depth
            }
        }
        
    except Exception as e:
        logger.error(f"获取允许的根目录失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取允许的根目录失败: {str(e)}"
        )