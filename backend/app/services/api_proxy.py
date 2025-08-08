"""
API代理服务
"""
import asyncio
import httpx
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging
import re

from ..models.schemas import ModelInfo
from ..models.enums import ModelStatus, HealthStatus

logger = logging.getLogger(__name__)


class LoadBalancingStrategy(Enum):
    """负载均衡策略"""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    RANDOM = "random"


@dataclass
class ProxyRule:
    """代理规则"""
    path_pattern: str
    target_path: str
    methods: List[str]
    auth_required: bool = False
    rate_limit: Optional[int] = None


@dataclass
class RequestMetrics:
    """请求指标"""
    request_id: str
    method: str
    path: str
    target_url: str
    status_code: int
    response_time: float
    request_size: int
    response_size: int
    timestamp: datetime
    error_message: Optional[str] = None


class APIProxyService:
    """API代理服务"""
    
    def __init__(self, load_balancing_strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN):
        self._model_endpoints: Dict[str, Dict[str, Any]] = {}
        self._proxy_rules: List[ProxyRule] = []
        self._load_balancing_strategy = load_balancing_strategy
        self._round_robin_index = 0
        self._connection_counts: Dict[str, int] = {}
        self._request_counts: Dict[str, int] = {}
        self._rate_limits: Dict[str, Dict[str, Any]] = {}
        self._enable_failover = True
    
    async def register_model_endpoint(self, model_info: ModelInfo):
        """注册模型端点"""
        self._model_endpoints[model_info.id] = {
            'model_info': model_info,
            'endpoint': model_info.api_endpoint or model_info.endpoint,
            'status': model_info.status,
            'health': getattr(model_info, 'health', HealthStatus.UNKNOWN),
            'last_updated': datetime.now(),
            'last_health_check': None
        }
        
        # 初始化计数器
        self._connection_counts[model_info.id] = 0
        self._request_counts[model_info.id] = 0
        
        logger.info(f"已注册模型端点: {model_info.id} -> {self._model_endpoints[model_info.id]['endpoint']}")
    
    async def unregister_model_endpoint(self, model_id: str):
        """注销模型端点"""
        if model_id in self._model_endpoints:
            del self._model_endpoints[model_id]
            self._connection_counts.pop(model_id, None)
            self._request_counts.pop(model_id, None)
            self._rate_limits.pop(model_id, None)
            logger.info(f"已注销模型端点: {model_id}")
    
    async def update_model_status(self, model_id: str, status: ModelStatus):
        """更新模型状态"""
        if model_id in self._model_endpoints:
            self._model_endpoints[model_id]['status'] = status
            self._model_endpoints[model_id]['last_updated'] = datetime.now()
    
    async def update_model_health(self, model_id: str, health: HealthStatus):
        """更新模型健康状态"""
        if model_id in self._model_endpoints:
            self._model_endpoints[model_id]['health'] = health
            self._model_endpoints[model_id]['last_health_check'] = datetime.now()
    
    async def get_available_endpoints(self) -> Dict[str, Dict[str, Any]]:
        """获取可用的端点"""
        available = {}
        for model_id, endpoint_info in self._model_endpoints.items():
            if (endpoint_info['status'] == ModelStatus.RUNNING and 
                endpoint_info['health'] == HealthStatus.HEALTHY):
                available[model_id] = endpoint_info
        return available
    
    async def select_endpoint(self) -> Optional[Dict[str, Any]]:
        """根据负载均衡策略选择端点"""
        available_endpoints = await self.get_available_endpoints()
        
        if not available_endpoints:
            return None
        
        if self._load_balancing_strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._select_round_robin(available_endpoints)
        elif self._load_balancing_strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._select_least_connections(available_endpoints)
        else:  # RANDOM
            import random
            model_id = random.choice(list(available_endpoints.keys()))
            endpoint_info = available_endpoints[model_id]
            endpoint_info['model_id'] = model_id
            return endpoint_info
    
    def _select_round_robin(self, available_endpoints: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """轮询选择端点"""
        endpoint_list = list(available_endpoints.items())
        if not endpoint_list:
            return None
        
        model_id, endpoint_info = endpoint_list[self._round_robin_index % len(endpoint_list)]
        self._round_robin_index += 1
        
        endpoint_info['model_id'] = model_id
        return endpoint_info
    
    def _select_least_connections(self, available_endpoints: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """选择连接数最少的端点"""
        if not available_endpoints:
            return None
        
        # 找到连接数最少的端点
        min_connections = float('inf')
        selected_model_id = None
        
        for model_id in available_endpoints.keys():
            connections = self._connection_counts.get(model_id, 0)
            if connections < min_connections:
                min_connections = connections
                selected_model_id = model_id
        
        if selected_model_id:
            endpoint_info = available_endpoints[selected_model_id]
            endpoint_info['model_id'] = selected_model_id
            return endpoint_info
        
        return None
    
    async def proxy_request(self, model_id: str, path: str, method: str = "POST", 
                          data: Optional[Dict[str, Any]] = None, 
                          headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """代理请求到指定模型"""
        if model_id not in self._model_endpoints:
            return {
                'status_code': 404,
                'error': '模型不存在或不可用'
            }
        
        endpoint_info = self._model_endpoints[model_id]
        
        # 检查模型状态
        if (endpoint_info['status'] != ModelStatus.RUNNING or 
            endpoint_info['health'] != HealthStatus.HEALTHY):
            return {
                'status_code': 503,
                'error': '模型当前不可用'
            }
        
        # 检查速率限制
        if not self._check_rate_limit(model_id):
            return {
                'status_code': 429,
                'error': '请求频率超限'
            }
        
        # 增加连接计数
        self.increment_connection_count(model_id)
        
        try:
            endpoint = endpoint_info['endpoint']
            url = f"{endpoint.rstrip('/')}{path}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method.upper() == "POST":
                    response = await client.post(url, json=data, headers=headers)
                elif method.upper() == "GET":
                    response = await client.get(url, headers=headers)
                elif method.upper() == "PUT":
                    response = await client.put(url, json=data, headers=headers)
                elif method.upper() == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    return {
                        'status_code': 405,
                        'error': f'不支持的HTTP方法: {method}'
                    }
                
                # 增加请求计数
                self._request_counts[model_id] = self._request_counts.get(model_id, 0) + 1
                
                # 返回响应
                try:
                    response_data = response.json()
                except:
                    response_data = response.text
                
                return {
                    'status_code': response.status_code,
                    'data': response_data,
                    'headers': dict(response.headers)
                }
        
        except Exception as e:
            logger.error(f"代理请求失败: {e}")
            return {
                'status_code': 500,
                'error': f'代理请求失败: {str(e)}'
            }
        
        finally:
            # 减少连接计数
            self.decrement_connection_count(model_id)
    
    async def proxy_request_with_failover(self, path: str, method: str = "POST",
                                        data: Optional[Dict[str, Any]] = None,
                                        headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """带故障转移的代理请求"""
        if not self._enable_failover:
            endpoint = await self.select_endpoint()
            if not endpoint:
                return {
                    'status_code': 503,
                    'error': '没有可用的端点'
                }
            return await self.proxy_request(endpoint['model_id'], path, method, data, headers)
        
        # 尝试多个端点
        available_endpoints = await self.get_available_endpoints()
        
        for model_id in available_endpoints.keys():
            try:
                result = await self.proxy_request(model_id, path, method, data, headers)
                if result['status_code'] < 500:  # 非服务器错误
                    return result
            except Exception as e:
                logger.warning(f"端点 {model_id} 请求失败，尝试下一个: {e}")
                continue
        
        return {
            'status_code': 503,
            'error': '所有端点都不可用'
        }
    
    def add_proxy_rule(self, rule: ProxyRule):
        """添加代理规则"""
        self._proxy_rules.append(rule)
    
    def remove_proxy_rule(self, path_pattern: str):
        """移除代理规则"""
        self._proxy_rules = [rule for rule in self._proxy_rules if rule.path_pattern != path_pattern]
    
    def _match_proxy_rule(self, path: str, method: str) -> tuple[Optional[ProxyRule], Dict[str, str]]:
        """匹配代理规则"""
        for rule in self._proxy_rules:
            if method not in rule.methods:
                continue
            
            # 简单的路径匹配（支持参数）
            pattern = rule.path_pattern.replace('{', '(?P<').replace('}', '>[^/]+)')
            match = re.match(f"^{pattern}$", path)
            
            if match:
                return rule, match.groupdict()
        
        return None, {}
    
    def increment_connection_count(self, model_id: str):
        """增加连接计数"""
        self._connection_counts[model_id] = self._connection_counts.get(model_id, 0) + 1
    
    def decrement_connection_count(self, model_id: str):
        """减少连接计数"""
        if model_id in self._connection_counts:
            self._connection_counts[model_id] = max(0, self._connection_counts[model_id] - 1)
    
    def _check_rate_limit(self, model_id: str) -> bool:
        """检查速率限制"""
        if model_id not in self._rate_limits:
            return True
        
        rate_limit_info = self._rate_limits[model_id]
        current_time = datetime.now()
        
        # 检查时间窗口
        if (current_time - rate_limit_info['window_start']).total_seconds() >= 60:
            # 重置窗口
            rate_limit_info['window_start'] = current_time
            rate_limit_info['current_count'] = 0
        
        # 检查是否超过限制
        if rate_limit_info['current_count'] >= rate_limit_info['requests_per_minute']:
            return False
        
        rate_limit_info['current_count'] += 1
        return True
    
    async def get_proxy_stats(self) -> Dict[str, Any]:
        """获取代理统计信息"""
        available_endpoints = await self.get_available_endpoints()
        
        return {
            'total_endpoints': len(self._model_endpoints),
            'available_endpoints': len(available_endpoints),
            'total_requests': sum(self._request_counts.values()),
            'total_connections': sum(self._connection_counts.values()),
            'model_stats': {
                model_id: {
                    'requests': self._request_counts.get(model_id, 0),
                    'connections': self._connection_counts.get(model_id, 0),
                    'status': endpoint_info['status'].value if hasattr(endpoint_info['status'], 'value') else str(endpoint_info['status']),
                    'health': endpoint_info['health'].value if hasattr(endpoint_info['health'], 'value') else str(endpoint_info['health'])
                }
                for model_id, endpoint_info in self._model_endpoints.items()
            }
        }
    
    async def health_check_endpoints(self):
        """检查所有端点的健康状态"""
        for model_id, endpoint_info in self._model_endpoints.items():
            try:
                endpoint = endpoint_info['endpoint']
                health_url = f"{endpoint.rstrip('/')}/health"
                
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(health_url)
                    
                    if response.status_code == 200:
                        await self.update_model_health(model_id, HealthStatus.HEALTHY)
                    else:
                        await self.update_model_health(model_id, HealthStatus.UNHEALTHY)
            
            except Exception as e:
                logger.warning(f"端点 {model_id} 健康检查失败: {e}")
                await self.update_model_health(model_id, HealthStatus.UNHEALTHY)