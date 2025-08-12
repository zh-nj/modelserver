# 设计文档

## 概述

修复前端控制台中出现的404错误，统一前后端的API端点路径，确保前端能够正确调用后端提供的系统指标API。

## 架构

### API端点统一策略
- **系统相关端点**: 统一使用 `/api/system/` 前缀
- **监控相关端点**: 统一使用 `/api/monitoring/` 前缀
- **模型相关端点**: 统一使用 `/api/models/` 前缀

### 当前问题分析
- 前端调用: `/api/system/metrics`
- 后端提供: `/api/monitoring/metrics/system`
- 解决方案: 统一到一个端点路径

## 组件和接口

### 前端API服务
```typescript
class MonitoringApiService {
  // 获取系统指标 - 需要修复的方法
  static async getSystemMetrics(timeRange: string = '1h') {
    return ApiService.get(`/api/system/metrics?range=${timeRange}`)
  }
}
```

### 后端API端点
```python
# 选项1: 在system.py中添加metrics端点
@router.get("/metrics")
async def get_system_metrics(range: str = "1h"):
    # 调用监控服务获取系统指标
    pass

# 选项2: 修改前端调用现有的监控端点
# 前端改为调用: /api/monitoring/metrics/system
```

## 数据模型

### 系统指标响应格式
```typescript
interface SystemMetrics {
  timestamp: string
  cpu_usage: number
  memory_usage: number
  disk_usage: number
  gpu_metrics: GPUMetrics[]
  network_stats: NetworkStats
}
```

## 错误处理

### 404错误处理
- 确保端点路径匹配
- 添加适当的错误响应
- 提供清晰的错误信息

### 向后兼容性
- 保持现有端点可用
- 添加重定向或别名支持
- 逐步迁移到统一的端点结构

## 测试策略

### API端点测试
- 测试端点可访问性
- 验证响应格式正确性
- 确保错误处理正常

### 集成测试
- 前后端端点调用测试
- 数据传输完整性验证
- 错误场景处理测试