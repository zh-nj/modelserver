"""
资源需求计算器
"""
import logging
import math
from typing import Dict, List, Optional, Tuple, Any
from ..models.schemas import ResourceRequirement, ModelConfig, GPUInfo, ResourceAllocation
from ..models.enums import FrameworkType, GPUVendor

logger = logging.getLogger(__name__)


class ResourceCalculator:
    """
    资源需求计算器 - 预估模型资源需求并验证资源分配
    """
    
    # 不同框架的基础内存开销 (MB)
    FRAMEWORK_OVERHEAD = {
        FrameworkType.LLAMA_CPP: 512,    # llama.cpp基础开销
        FrameworkType.VLLM: 1024,        # vLLM基础开销
        FrameworkType.DOCKER: 256        # Docker容器基础开销
    }
    
    # 不同精度的内存系数
    PRECISION_MULTIPLIERS = {
        'fp32': 4.0,    # 32位浮点
        'fp16': 2.0,    # 16位浮点
        'int8': 1.0,    # 8位整数
        'int4': 0.5,    # 4位整数
    }
    
    # 模型类型的参数密度估算 (参数数量/GB)
    MODEL_PARAM_DENSITY = {
        'llama': 1.0,      # 标准密度
        'mistral': 1.0,    # 类似llama
        'qwen': 1.2,       # 稍高密度
        'baichuan': 1.0,   # 标准密度
        'chatglm': 0.8,    # 稍低密度
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_model_memory_requirement(
        self, 
        model_config: ModelConfig
    ) -> ResourceRequirement:
        """
        计算模型的内存需求
        
        Args:
            model_config: 模型配置
            
        Returns:
            资源需求信息
        """
        try:
            # 从模型配置中提取参数
            model_size_gb = self._extract_model_size(model_config)
            precision = self._extract_precision(model_config)
            context_length = self._extract_context_length(model_config)
            batch_size = self._extract_batch_size(model_config)
            
            # 计算基础模型内存需求
            base_memory = self._calculate_base_model_memory(
                model_size_gb, precision, model_config.framework
            )
            
            # 计算上下文内存需求
            context_memory = self._calculate_context_memory(
                model_size_gb, context_length, batch_size, precision
            )
            
            # 计算框架开销
            framework_overhead = self.FRAMEWORK_OVERHEAD.get(
                model_config.framework, 512
            )
            
            # 总内存需求 (添加20%的安全边距)
            total_memory = int((base_memory + context_memory + framework_overhead) * 1.2)
            
            # 创建资源需求对象
            resource_req = ResourceRequirement(
                gpu_memory=total_memory,
                gpu_devices=model_config.gpu_devices.copy(),
                cpu_cores=self._estimate_cpu_cores(model_config),
                system_memory=self._estimate_system_memory(total_memory)
            )
            
            self.logger.info(
                f"模型 {model_config.name} 资源需求计算完成: "
                f"GPU内存={total_memory}MB, CPU核心={resource_req.cpu_cores}, "
                f"系统内存={resource_req.system_memory}MB"
            )
            
            return resource_req
            
        except Exception as e:
            self.logger.error(f"计算模型 {model_config.name} 资源需求时出错: {e}")
            # 返回保守的默认值
            return ResourceRequirement(
                gpu_memory=8192,  # 默认8GB
                gpu_devices=model_config.gpu_devices.copy(),
                cpu_cores=4,
                system_memory=4096
            )
    
    def _extract_model_size(self, model_config: ModelConfig) -> float:
        """从模型配置中提取模型大小 (GB)"""
        try:
            # 尝试从参数中获取模型大小
            if 'model_size_gb' in model_config.parameters:
                return float(model_config.parameters['model_size_gb'])
            
            # 尝试从模型名称中推断大小
            model_name = model_config.name.lower()
            size_patterns = {
                '7b': 7.0, '13b': 13.0, '30b': 30.0, '65b': 65.0,
                '70b': 70.0, '175b': 175.0, '1.8b': 1.8, '3b': 3.0,
                '6b': 6.0, '14b': 14.0, '34b': 34.0, '72b': 72.0
            }
            
            for pattern, size in size_patterns.items():
                if pattern in model_name:
                    return size
            
            # 尝试从模型路径获取文件大小
            import os
            if os.path.exists(model_config.model_path):
                file_size_bytes = os.path.getsize(model_config.model_path)
                file_size_gb = file_size_bytes / (1024 ** 3)
                # 模型文件通常是压缩的，实际内存需求会更大
                return file_size_gb * 1.5
            
            # 默认值
            return 7.0
            
        except Exception as e:
            self.logger.warning(f"无法确定模型大小，使用默认值: {e}")
            return 7.0
    
    def _extract_precision(self, model_config: ModelConfig) -> str:
        """从模型配置中提取精度信息"""
        try:
            # 从参数中获取精度
            if 'precision' in model_config.parameters:
                return model_config.parameters['precision']
            
            # 从其他参数推断
            if 'quantization' in model_config.parameters:
                quant = model_config.parameters['quantization'].lower()
                if 'int8' in quant or 'q8' in quant:
                    return 'int8'
                elif 'int4' in quant or 'q4' in quant:
                    return 'int4'
            
            # 从模型名称推断
            model_name = model_config.name.lower()
            if 'int8' in model_name or 'q8' in model_name:
                return 'int8'
            elif 'int4' in model_name or 'q4' in model_name:
                return 'int4'
            elif 'fp16' in model_name or 'half' in model_name:
                return 'fp16'
            
            # 默认精度
            return 'fp16'
            
        except Exception:
            return 'fp16'
    
    def _extract_context_length(self, model_config: ModelConfig) -> int:
        """从模型配置中提取上下文长度"""
        try:
            # 常见的上下文长度参数名
            context_params = ['context_length', 'max_seq_len', 'n_ctx', 'max_position_embeddings']
            
            for param in context_params:
                if param in model_config.parameters:
                    return int(model_config.parameters[param])
            
            # 默认上下文长度
            return 2048
            
        except Exception:
            return 2048
    
    def _extract_batch_size(self, model_config: ModelConfig) -> int:
        """从模型配置中提取批处理大小"""
        try:
            batch_params = ['batch_size', 'max_batch_size', 'n_batch']
            
            for param in batch_params:
                if param in model_config.parameters:
                    return int(model_config.parameters[param])
            
            # 默认批处理大小
            return 1
            
        except Exception:
            return 1
    
    def _calculate_base_model_memory(
        self, 
        model_size_gb: float, 
        precision: str, 
        framework: FrameworkType
    ) -> int:
        """计算基础模型内存需求 (MB)"""
        # 获取精度系数
        precision_multiplier = self.PRECISION_MULTIPLIERS.get(precision, 2.0)
        
        # 基础内存 = 模型大小 * 精度系数 * 1024 (转换为MB)
        base_memory = model_size_gb * precision_multiplier * 1024
        
        # 不同框架的额外系数
        framework_multipliers = {
            FrameworkType.LLAMA_CPP: 1.0,    # llama.cpp内存效率较高
            FrameworkType.VLLM: 1.3,         # vLLM需要额外内存用于优化
            FrameworkType.DOCKER: 1.1        # Docker有少量额外开销
        }
        
        multiplier = framework_multipliers.get(framework, 1.0)
        return int(base_memory * multiplier)
    
    def _calculate_context_memory(
        self, 
        model_size_gb: float, 
        context_length: int, 
        batch_size: int, 
        precision: str
    ) -> int:
        """计算上下文内存需求 (MB)"""
        # 上下文内存主要用于存储KV缓存
        # 估算公式: context_length * batch_size * hidden_size * num_layers * precision_bytes
        
        # 根据模型大小估算隐藏层维度和层数
        if model_size_gb <= 1.0:
            hidden_size, num_layers = 2048, 24
        elif model_size_gb <= 3.0:
            hidden_size, num_layers = 2560, 32
        elif model_size_gb <= 7.0:
            hidden_size, num_layers = 4096, 32
        elif model_size_gb <= 13.0:
            hidden_size, num_layers = 5120, 40
        elif model_size_gb <= 30.0:
            hidden_size, num_layers = 6656, 60
        elif model_size_gb <= 70.0:
            hidden_size, num_layers = 8192, 80
        else:
            hidden_size, num_layers = 12288, 96
        
        # 精度字节数
        precision_bytes = self.PRECISION_MULTIPLIERS.get(precision, 2.0)
        
        # KV缓存内存 = context_length * batch_size * hidden_size * num_layers * 2 (K和V) * precision_bytes
        kv_cache_memory = (
            context_length * batch_size * hidden_size * num_layers * 2 * precision_bytes
        ) / (1024 * 1024)  # 转换为MB
        
        return int(kv_cache_memory)
    
    def _estimate_cpu_cores(self, model_config: ModelConfig) -> int:
        """估算CPU核心需求"""
        try:
            if 'cpu_cores' in model_config.parameters:
                return int(model_config.parameters['cpu_cores'])
            
            # 根据框架类型估算
            if model_config.framework == FrameworkType.LLAMA_CPP:
                return 4  # llama.cpp通常需要较少CPU
            elif model_config.framework == FrameworkType.VLLM:
                return 8  # vLLM需要更多CPU用于调度
            else:
                return 4
                
        except Exception:
            return 4
    
    def _estimate_system_memory(self, gpu_memory_mb: int) -> int:
        """估算系统内存需求 (MB)"""
        # 系统内存通常是GPU内存的1/4到1/2
        return max(2048, gpu_memory_mb // 4)
    
    def validate_resource_allocation(
        self, 
        requirement: ResourceRequirement, 
        available_gpus: List[GPUInfo]
    ) -> Tuple[bool, List[str], Optional[ResourceAllocation]]:
        """
        验证资源分配是否可行
        
        Args:
            requirement: 资源需求
            available_gpus: 可用GPU列表
            
        Returns:
            (是否可行, 错误信息列表, 资源分配方案)
        """
        errors = []
        
        try:
            # 如果指定了特定GPU设备
            if requirement.gpu_devices:
                return self._validate_specific_gpu_allocation(
                    requirement, available_gpus
                )
            else:
                return self._validate_automatic_gpu_allocation(
                    requirement, available_gpus
                )
                
        except Exception as e:
            self.logger.error(f"验证资源分配时出错: {e}")
            errors.append(f"资源分配验证失败: {str(e)}")
            return False, errors, None
    
    def _validate_specific_gpu_allocation(
        self, 
        requirement: ResourceRequirement, 
        available_gpus: List[GPUInfo]
    ) -> Tuple[bool, List[str], Optional[ResourceAllocation]]:
        """验证指定GPU设备的资源分配"""
        errors = []
        
        # 创建GPU设备映射
        gpu_map = {gpu.device_id: gpu for gpu in available_gpus}
        
        # 检查指定的GPU是否存在
        missing_gpus = []
        for device_id in requirement.gpu_devices:
            if device_id not in gpu_map:
                missing_gpus.append(device_id)
        
        if missing_gpus:
            errors.append(f"指定的GPU设备不存在: {missing_gpus}")
            return False, errors, None
        
        # 检查每个指定GPU的内存是否足够
        insufficient_gpus = []
        total_available_memory = 0
        
        for device_id in requirement.gpu_devices:
            gpu = gpu_map[device_id]
            if gpu.memory_free < requirement.gpu_memory:
                insufficient_gpus.append(
                    f"GPU {device_id}: 需要{requirement.gpu_memory}MB, "
                    f"可用{gpu.memory_free}MB"
                )
            total_available_memory += gpu.memory_free
        
        # 如果单个GPU内存不足，检查是否可以跨GPU分配
        if insufficient_gpus:
            if len(requirement.gpu_devices) > 1 and total_available_memory >= requirement.gpu_memory:
                # 可以跨GPU分配
                self.logger.info(f"单GPU内存不足，但可跨GPU分配: 总可用内存{total_available_memory}MB")
            else:
                errors.extend(insufficient_gpus)
                return False, errors, None
        
        # 创建资源分配方案
        allocation = ResourceAllocation(
            gpu_devices=requirement.gpu_devices.copy(),
            memory_allocated=requirement.gpu_memory,
            allocation_time=self._get_current_time()
        )
        
        return True, [], allocation
    
    def _validate_automatic_gpu_allocation(
        self, 
        requirement: ResourceRequirement, 
        available_gpus: List[GPUInfo]
    ) -> Tuple[bool, List[str], Optional[ResourceAllocation]]:
        """验证自动GPU分配"""
        errors = []
        
        if not available_gpus:
            errors.append("没有可用的GPU设备")
            return False, errors, None
        
        # 按可用内存排序GPU
        sorted_gpus = sorted(
            available_gpus, 
            key=lambda x: x.memory_free, 
            reverse=True
        )
        
        # 尝试单GPU分配
        for gpu in sorted_gpus:
            if gpu.memory_free >= requirement.gpu_memory:
                allocation = ResourceAllocation(
                    gpu_devices=[gpu.device_id],
                    memory_allocated=requirement.gpu_memory,
                    allocation_time=self._get_current_time()
                )
                return True, [], allocation
        
        # 尝试多GPU分配
        selected_gpus = []
        total_memory = 0
        
        for gpu in sorted_gpus:
            if total_memory < requirement.gpu_memory:
                selected_gpus.append(gpu.device_id)
                total_memory += gpu.memory_free
        
        if total_memory >= requirement.gpu_memory:
            allocation = ResourceAllocation(
                gpu_devices=selected_gpus,
                memory_allocated=requirement.gpu_memory,
                allocation_time=self._get_current_time()
            )
            return True, [], allocation
        
        # 无法满足内存需求
        errors.append(
            f"GPU内存不足: 需要{requirement.gpu_memory}MB, "
            f"总可用{total_memory}MB"
        )
        return False, errors, None
    
    def calculate_memory_fragmentation(self, gpus: List[GPUInfo]) -> Dict[str, Any]:
        """
        计算GPU内存碎片化程度
        
        Args:
            gpus: GPU设备列表
            
        Returns:
            碎片化分析结果
        """
        if not gpus:
            return {
                'total_memory': 0,
                'used_memory': 0,
                'free_memory': 0,
                'fragmentation_ratio': 0.0,
                'largest_free_block': 0,
                'gpu_count': 0
            }
        
        total_memory = sum(gpu.memory_total for gpu in gpus)
        used_memory = sum(gpu.memory_used for gpu in gpus)
        free_memory = sum(gpu.memory_free for gpu in gpus)
        largest_free_block = max(gpu.memory_free for gpu in gpus)
        
        # 碎片化比率 = 1 - (最大可用块 / 总可用内存)
        fragmentation_ratio = 1.0 - (largest_free_block / free_memory) if free_memory > 0 else 0.0
        
        return {
            'total_memory': total_memory,
            'used_memory': used_memory,
            'free_memory': free_memory,
            'fragmentation_ratio': fragmentation_ratio,
            'largest_free_block': largest_free_block,
            'gpu_count': len(gpus),
            'average_utilization': sum(gpu.utilization for gpu in gpus) / len(gpus)
        }
    
    def suggest_optimal_allocation(
        self, 
        requirements: List[ResourceRequirement], 
        available_gpus: List[GPUInfo]
    ) -> List[Tuple[int, Optional[ResourceAllocation]]]:
        """
        为多个资源需求建议最优分配方案
        
        Args:
            requirements: 资源需求列表
            available_gpus: 可用GPU列表
            
        Returns:
            (需求索引, 分配方案)列表
        """
        allocations = []
        remaining_gpus = available_gpus.copy()
        
        # 按内存需求降序排序
        sorted_requirements = sorted(
            enumerate(requirements),
            key=lambda x: x[1].gpu_memory,
            reverse=True
        )
        
        for req_index, requirement in sorted_requirements:
            is_valid, errors, allocation = self.validate_resource_allocation(
                requirement, remaining_gpus
            )
            
            if is_valid and allocation:
                allocations.append((req_index, allocation))
                
                # 更新剩余GPU资源
                for gpu in remaining_gpus:
                    if gpu.device_id in allocation.gpu_devices:
                        # 简化处理：假设完全占用GPU
                        gpu.memory_free = 0
                        gpu.memory_used = gpu.memory_total
            else:
                allocations.append((req_index, None))
        
        return allocations
    
    def _get_current_time(self):
        """获取当前时间"""
        from datetime import datetime
        return datetime.now()


# 全局资源计算器实例
resource_calculator = ResourceCalculator()