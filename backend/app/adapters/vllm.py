"""
vLLM框架适配器实现
"""
import asyncio
import docker
import aiohttp
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

from .base import BaseFrameworkAdapter, register_adapter
from ..models.schemas import ModelConfig, ModelStatus, HealthStatus, ValidationResult
from ..models.enums import FrameworkType

logger = logging.getLogger(__name__)

@register_adapter(FrameworkType.VLLM)
class VllmAdapter(BaseFrameworkAdapter):
    """vLLM适配器"""
    
    def __init__(self, framework_type: FrameworkType):
        super().__init__(framework_type)
        self.docker_client = docker.from_env()
        self.default_image = "vllm/vllm-openai:latest"
    
    def validate_config(self, config: ModelConfig) -> ValidationResult:
        """验证vLLM特定配置"""
        # 先进行通用验证
        result = self._validate_common_config(config)
        
        if not result.is_valid:
            return result
        
        errors = []
        warnings = []
        
        # 检查Docker是否可用
        try:
            self.docker_client.ping()
        except Exception as e:
            errors.append(f"Docker服务不可用: {e}")
            return ValidationResult(
                is_valid=False,
                errors=result.errors + errors,
                warnings=result.warnings + warnings
            )
        
        params = config.parameters
        
        # 检查端口配置
        port = params.get('port', 8000)
        if not isinstance(port, int) or port < 1024 or port > 65535:
            errors.append("端口必须是1024-65535之间的整数")
        
        # 检查主机配置
        host = params.get('host', '0.0.0.0')
        if not isinstance(host, str) or not host:
            errors.append("主机地址不能为空")
        
        # 检查模型名称或路径
        model_name = params.get('model_name', config.model_path)
        if not model_name:
            errors.append("模型名称或路径不能为空")
        
        # 检查张量并行度
        tensor_parallel_size = params.get('tensor_parallel_size', 1)
        if not isinstance(tensor_parallel_size, int) or tensor_parallel_size <= 0:
            errors.append("张量并行度必须是正整数")
        
        # 检查最大模型长度
        max_model_len = params.get('max_model_len')
        if max_model_len is not None:
            if not isinstance(max_model_len, int) or max_model_len <= 0:
                errors.append("最大模型长度必须是正整数")
        
        # 检查GPU内存利用率
        gpu_memory_utilization = params.get('gpu_memory_utilization', 0.9)
        if not isinstance(gpu_memory_utilization, (int, float)) or gpu_memory_utilization <= 0 or gpu_memory_utilization > 1:
            errors.append("GPU内存利用率必须是0-1之间的数值")
        
        # 检查Docker镜像
        docker_image = params.get('docker_image', self.default_image)
        try:
            self.docker_client.images.get(docker_image)
        except docker.errors.ImageNotFound:
            warnings.append(f"Docker镜像 {docker_image} 不存在，将尝试拉取")
        
        # 检查挂载路径
        model_volume_path = params.get('model_volume_path')
        if model_volume_path:
            if not Path(model_volume_path).exists():
                errors.append(f"模型挂载路径不存在: {model_volume_path}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=result.errors + errors,
            warnings=result.warnings + warnings
        )
    
    def _build_docker_config(self, config: ModelConfig) -> Dict[str, Any]:
        """构建Docker容器配置"""
        params = config.parameters
        
        # 基本配置
        docker_config = {
            'image': params.get('docker_image', self.default_image),
            'name': f"vllm-{config.id}",
            'detach': True,
            'remove': True,  # 容器停止后自动删除
            'ports': {
                f"{params.get('port', 8000)}/tcp": params.get('port', 8000)
            },
            'environment': {
                'CUDA_VISIBLE_DEVICES': ','.join(map(str, config.gpu_devices)) if config.gpu_devices else 'all'
            }
        }
        
        # 构建命令行参数
        cmd = [
            'python', '-m', 'vllm.entrypoints.openai.api_server',
            '--model', params.get('model_name', config.model_path),
            '--host', params.get('host', '0.0.0.0'),
            '--port', str(params.get('port', 8000)),
            '--tensor-parallel-size', str(params.get('tensor_parallel_size', 1)),
            '--gpu-memory-utilization', str(params.get('gpu_memory_utilization', 0.9))
        ]
        
        # 可选参数
        if params.get('max_model_len'):
            cmd.extend(['--max-model-len', str(params['max_model_len'])])
        
        if params.get('dtype'):
            cmd.extend(['--dtype', params['dtype']])
        
        if params.get('quantization'):
            cmd.extend(['--quantization', params['quantization']])
        
        if params.get('seed'):
            cmd.extend(['--seed', str(params['seed'])])
        
        if params.get('max_num_seqs'):
            cmd.extend(['--max-num-seqs', str(params['max_num_seqs'])])
        
        if params.get('max_num_batched_tokens'):
            cmd.extend(['--max-num-batched-tokens', str(params['max_num_batched_tokens'])])
        
        if params.get('trust_remote_code', False):
            cmd.append('--trust-remote-code')
        
        if params.get('disable_log_stats', False):
            cmd.append('--disable-log-stats')
        
        docker_config['command'] = cmd
        
        # 挂载卷
        volumes = {}
        model_volume_path = params.get('model_volume_path')
        if model_volume_path:
            volumes[model_volume_path] = {'bind': '/models', 'mode': 'ro'}
        
        # 缓存目录挂载
        cache_volume_path = params.get('cache_volume_path')
        if cache_volume_path:
            volumes[cache_volume_path] = {'bind': '/root/.cache', 'mode': 'rw'}
        
        if volumes:
            docker_config['volumes'] = volumes
        
        # 资源限制
        if params.get('memory_limit'):
            docker_config['mem_limit'] = params['memory_limit']
        
        if params.get('cpu_limit'):
            docker_config['nano_cpus'] = int(params['cpu_limit'] * 1e9)
        
        # GPU支持
        if config.gpu_devices:
            docker_config['device_requests'] = [
                docker.types.DeviceRequest(
                    device_ids=[str(gpu_id) for gpu_id in config.gpu_devices],
                    capabilities=[['gpu']]
                )
            ]
        
        # 网络配置
        if params.get('network_mode'):
            docker_config['network_mode'] = params['network_mode']
        
        # 环境变量
        env_vars = params.get('environment', {})
        docker_config['environment'].update(env_vars)
        
        return docker_config
    
    async def _pull_image_if_needed(self, image: str) -> bool:
        """如果需要则拉取Docker镜像"""
        try:
            self.docker_client.images.get(image)
            return True
        except docker.errors.ImageNotFound:
            logger.info(f"拉取Docker镜像: {image}")
            try:
                # 在后台拉取镜像
                def pull_image():
                    self.docker_client.images.pull(image)
                
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, pull_image)
                return True
            except Exception as e:
                logger.error(f"拉取Docker镜像失败: {e}")
                return False
    
    async def _do_start_model(self, config: ModelConfig) -> bool:
        """启动vLLM Docker容器"""
        try:
            # 构建Docker配置
            docker_config = self._build_docker_config(config)
            
            # 拉取镜像（如果需要）
            if not await self._pull_image_if_needed(docker_config['image']):
                return False
            
            logger.info(f"启动vLLM容器: {docker_config['name']}")
            
            # 启动容器
            def run_container():
                return self.docker_client.containers.run(**docker_config)
            
            loop = asyncio.get_event_loop()
            container = await loop.run_in_executor(None, run_container)
            
            # 保存容器信息
            params = config.parameters
            model_info = {
                'container': container,
                'container_id': container.id,
                'status': ModelStatus.STARTING,
                'host': params.get('host', '0.0.0.0'),
                'port': params.get('port', 8000),
                'api_endpoint': f"http://localhost:{params.get('port', 8000)}"
            }
            self._set_model_info(config.id, model_info)
            
            # 等待服务就绪
            if await self._wait_for_service_ready(config.id, timeout=120):
                model_info['status'] = ModelStatus.RUNNING
                self._set_model_info(config.id, model_info)
                logger.info(f"vLLM模型 {config.id} 启动成功")
                return True
            else:
                logger.error(f"vLLM模型 {config.id} 启动超时")
                await self._do_stop_model(config.id)
                return False
                
        except Exception as e:
            logger.error(f"启动vLLM模型 {config.id} 时发生异常: {e}")
            return False
    
    async def _wait_for_service_ready(self, model_id: str, timeout: int = 120) -> bool:
        """等待vLLM服务就绪"""
        model_info = self._get_model_info(model_id)
        if not model_info:
            return False
        
        api_endpoint = model_info['api_endpoint']
        health_url = f"{api_endpoint}/health"
        
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                # 检查容器状态
                container = model_info['container']
                container.reload()
                
                if container.status == 'exited':
                    logger.error(f"vLLM容器 {container.id} 已退出")
                    return False
                
                # 检查API端点
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        health_url, 
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 200:
                            return True
                        
            except Exception as e:
                logger.debug(f"等待vLLM服务就绪: {e}")
            
            await asyncio.sleep(2)
        
        return False
    
    async def _do_stop_model(self, model_id: str) -> bool:
        """停止vLLM Docker容器"""
        try:
            model_info = self._get_model_info(model_id)
            if not model_info:
                return True
            
            container = model_info.get('container')
            if not container:
                return True
            
            logger.info(f"停止vLLM容器: {container.id}")
            
            # 停止容器
            def stop_container():
                try:
                    container.stop(timeout=10)
                except docker.errors.NotFound:
                    # 容器已经不存在
                    pass
                except Exception as e:
                    logger.warning(f"停止容器时发生异常: {e}")
                    try:
                        container.kill()
                    except docker.errors.NotFound:
                        pass
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, stop_container)
            
            self._remove_model_info(model_id)
            logger.info(f"vLLM模型 {model_id} 停止成功")
            return True
            
        except Exception as e:
            logger.error(f"停止vLLM模型 {model_id} 时发生异常: {e}")
            return False
    
    async def _check_model_process(self, model_id: str) -> bool:
        """检查vLLM容器是否运行"""
        model_info = self._get_model_info(model_id)
        if not model_info:
            return False
        
        container = model_info.get('container')
        if not container:
            return False
        
        try:
            container.reload()
            return container.status == 'running'
        except docker.errors.NotFound:
            return False
        except Exception as e:
            logger.error(f"检查容器状态时发生异常: {e}")
            return False
    
    async def check_health(self, model_id: str) -> HealthStatus:
        """检查vLLM模型健康状态"""
        try:
            model_info = self._get_model_info(model_id)
            if not model_info:
                return HealthStatus.UNKNOWN
            
            # 检查容器状态
            if not await self._check_model_process(model_id):
                return HealthStatus.UNHEALTHY
            
            # 检查API端点
            api_endpoint = model_info.get('api_endpoint')
            if not api_endpoint:
                return HealthStatus.UNKNOWN
            
            health_url = f"{api_endpoint}/health"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    health_url, 
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return HealthStatus.HEALTHY
                    else:
                        return HealthStatus.UNHEALTHY
                        
        except Exception as e:
            logger.error(f"检查vLLM模型 {model_id} 健康状态时发生异常: {e}")
            return HealthStatus.UNHEALTHY
    
    async def get_api_endpoint(self, model_id: str) -> Optional[str]:
        """获取vLLM模型API端点"""
        model_info = self._get_model_info(model_id)
        if not model_info:
            return None
        
        return model_info.get('api_endpoint')
    
    async def get_container_logs(self, model_id: str, tail: int = 100) -> Optional[str]:
        """获取容器日志"""
        model_info = self._get_model_info(model_id)
        if not model_info:
            return None
        
        container = model_info.get('container')
        if not container:
            return None
        
        try:
            def get_logs():
                return container.logs(tail=tail, timestamps=True).decode('utf-8')
            
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, get_logs)
        except Exception as e:
            logger.error(f"获取容器日志时发生异常: {e}")
            return None
    
    def get_default_parameters(self) -> Dict[str, Any]:
        """获取默认参数"""
        return {
            'host': '0.0.0.0',
            'port': 8000,
            'tensor_parallel_size': 1,
            'gpu_memory_utilization': 0.9,
            'max_model_len': None,
            'dtype': 'auto',
            'quantization': None,
            'seed': None,
            'max_num_seqs': 256,
            'max_num_batched_tokens': None,
            'trust_remote_code': False,
            'disable_log_stats': False,
            'docker_image': self.default_image,
            'model_volume_path': None,
            'cache_volume_path': None,
            'memory_limit': None,
            'cpu_limit': None,
            'network_mode': None,
            'environment': {}
        }