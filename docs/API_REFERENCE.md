# LLM推理服务 API参考文档

本文档提供了LLM推理服务的完整API参考，包括所有端点、请求/响应格式和使用示例。

## 目录

- [认证](#认证)
- [基础信息](#基础信息)
- [模型管理API](#模型管理api)
- [推理API](#推理api)
- [系统监控API](#系统监控api)
- [配置管理API](#配置管理api)
- [WebSocket API](#websocket-api)
- [错误处理](#错误处理)
- [SDK和客户端库](#sdk和客户端库)

## 认证

### Bearer Token认证
所有API请求都需要在请求头中包含认证令牌：

```http
Authorization: Bearer YOUR_API_TOKEN
```

### 获取API令牌
```bash
curl -X POST http://your-server:8000/api/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'
```

响应：
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

## 基础信息

### 基础URL
```
http://your-server:8000/api
```

### 内容类型
所有请求和响应都使用JSON格式：
```http
Content-Type: application/json
```

### 版本控制
API版本通过URL路径指定：
```
/api/v1/models
```

### 分页
支持分页的端点使用以下参数：
- `page`: 页码（从1开始）
- `size`: 每页大小（默认20，最大100）

响应格式：
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "size": 20,
  "pages": 5
}
```

## 模型管理API

### 获取模型列表
```http
GET /api/models
```

查询参数：
- `page` (int): 页码
- `size` (int): 每页大小
- `status` (string): 过滤状态 (running, stopped, error)
- `framework` (string): 过滤框架 (llama.cpp, vllm)

响应：
```json
{
  "items": [
    {
      "id": "model-123",
      "name": "my-model",
      "display_name": "我的模型",
      "framework": "llama.cpp",
      "status": "running",
      "health": "healthy",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z",
      "config": {
        "model_path": "/models/model.bin",
        "n_ctx": 2048
      },
      "resource_usage": {
        "gpu_memory": 4096,
        "cpu_cores": 4
      }
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20
}
```

### 创建模型
```http
POST /api/models
```

请求体：
```json
{
  "name": "my-model",
  "display_name": "我的模型",
  "description": "模型描述",
  "framework": "llama.cpp",
  "priority": 5,
  "config": {
    "model_path": "/models/model.bin",
    "n_ctx": 2048,
    "n_threads": 4,
    "n_gpu_layers": 32
  },
  "resource_requirements": {
    "gpu_count": 1,
    "gpu_memory": 4096,
    "cpu_cores": 4
  },
  "tags": ["production", "chat"]
}
```

响应：
```json
{
  "id": "model-123",
  "name": "my-model",
  "status": "created",
  "message": "模型创建成功"
}
```

### 获取模型详情
```http
GET /api/models/{model_id}
```

响应：
```json
{
  "id": "model-123",
  "name": "my-model",
  "display_name": "我的模型",
  "description": "模型描述",
  "framework": "llama.cpp",
  "status": "running",
  "health": "healthy",
  "priority": 5,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z",
  "config": {
    "model_path": "/models/model.bin",
    "n_ctx": 2048,
    "n_threads": 4,
    "n_gpu_layers": 32
  },
  "resource_requirements": {
    "gpu_count": 1,
    "gpu_memory": 4096,
    "cpu_cores": 4
  },
  "resource_usage": {
    "gpu_memory": 3800,
    "cpu_cores": 3.5,
    "memory": 2048
  },
  "performance_stats": {
    "avg_response_time": 0.5,
    "requests_per_second": 10.5,
    "error_rate": 0.01
  },
  "tags": ["production", "chat"]
}
```

### 更新模型
```http
PUT /api/models/{model_id}
```

请求体：
```json
{
  "display_name": "更新的模型名称",
  "description": "更新的描述",
  "priority": 7,
  "config": {
    "temperature": 0.8,
    "top_p": 0.9
  },
  "tags": ["production", "chat", "updated"]
}
```

### 删除模型
```http
DELETE /api/models/{model_id}
```

响应：
```json
{
  "message": "模型删除成功"
}
```

### 启动模型
```http
POST /api/models/{model_id}/start
```

请求体（可选）：
```json
{
  "force": false,
  "timeout": 300
}
```

响应：
```json
{
  "message": "模型启动中",
  "task_id": "task-456"
}
```

### 停止模型
```http
POST /api/models/{model_id}/stop
```

请求体（可选）：
```json
{
  "force": false,
  "timeout": 60
}
```

### 重启模型
```http
POST /api/models/{model_id}/restart
```

### 获取模型日志
```http
GET /api/models/{model_id}/logs
```

查询参数：
- `lines` (int): 日志行数（默认100）
- `follow` (bool): 是否实时跟踪日志

响应：
```json
{
  "logs": [
    {
      "timestamp": "2024-01-01T12:00:00Z",
      "level": "INFO",
      "message": "模型加载完成"
    }
  ]
}
```

## 推理API

### 文本生成
```http
POST /api/models/{model_id}/generate
```

请求体：
```json
{
  "prompt": "Hello, how are you?",
  "max_tokens": 100,
  "temperature": 0.7,
  "top_p": 0.9,
  "top_k": 40,
  "stop": ["\n", "Human:"],
  "stream": false
}
```

响应：
```json
{
  "id": "gen-123",
  "model": "my-model",
  "choices": [
    {
      "text": "I'm doing well, thank you for asking!",
      "finish_reason": "stop",
      "index": 0
    }
  ],
  "usage": {
    "prompt_tokens": 5,
    "completion_tokens": 10,
    "total_tokens": 15
  },
  "created": 1704067200
}
```

### 流式生成
```http
POST /api/models/{model_id}/generate
```

请求体：
```json
{
  "prompt": "Tell me a story",
  "max_tokens": 200,
  "stream": true
}
```

响应（Server-Sent Events）：
```
data: {"id":"gen-123","choices":[{"text":"Once","index":0}]}

data: {"id":"gen-123","choices":[{"text":" upon","index":0}]}

data: {"id":"gen-123","choices":[{"text":" a","index":0}]}

data: [DONE]
```

### 聊天完成
```http
POST /api/models/{model_id}/chat/completions
```

请求体：
```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ],
  "max_tokens": 100,
  "temperature": 0.7,
  "stream": false
}
```

响应：
```json
{
  "id": "chat-123",
  "model": "my-model",
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you today?"
      },
      "finish_reason": "stop",
      "index": 0
    }
  ],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 10,
    "total_tokens": 30
  }
}
```

### 嵌入生成
```http
POST /api/models/{model_id}/embeddings
```

请求体：
```json
{
  "input": ["Hello world", "How are you?"],
  "encoding_format": "float"
}
```

响应：
```json
{
  "data": [
    {
      "embedding": [0.1, 0.2, 0.3, ...],
      "index": 0
    },
    {
      "embedding": [0.4, 0.5, 0.6, ...],
      "index": 1
    }
  ],
  "model": "my-model",
  "usage": {
    "prompt_tokens": 6,
    "total_tokens": 6
  }
}
```

## 系统监控API

### 获取系统状态
```http
GET /api/system/status
```

响应：
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": 86400,
  "models": {
    "total": 5,
    "running": 3,
    "stopped": 1,
    "error": 1
  },
  "resources": {
    "cpu_percent": 45.2,
    "memory_percent": 67.8,
    "disk_percent": 23.4
  },
  "gpu": [
    {
      "id": 0,
      "name": "NVIDIA RTX 4090",
      "utilization": 78.5,
      "memory_used": 12288,
      "memory_total": 24576,
      "temperature": 65
    }
  ]
}
```

### 获取GPU信息
```http
GET /api/system/gpu
```

响应：
```json
{
  "gpus": [
    {
      "id": 0,
      "name": "NVIDIA RTX 4090",
      "driver_version": "535.86.10",
      "cuda_version": "12.2",
      "utilization": 78.5,
      "memory_used": 12288,
      "memory_total": 24576,
      "memory_free": 12288,
      "temperature": 65,
      "power_usage": 350,
      "power_limit": 450,
      "processes": [
        {
          "pid": 1234,
          "name": "llama-cpp-server",
          "memory_usage": 8192
        }
      ]
    }
  ]
}
```

### 获取监控指标
```http
GET /api/monitoring/metrics
```

查询参数：
- `start_time` (string): 开始时间 (ISO 8601)
- `end_time` (string): 结束时间 (ISO 8601)
- `metric_type` (string): 指标类型 (gpu, cpu, memory, model)
- `interval` (string): 聚合间隔 (1m, 5m, 1h, 1d)

响应：
```json
{
  "metrics": [
    {
      "timestamp": "2024-01-01T12:00:00Z",
      "gpu_utilization": 78.5,
      "gpu_memory_used": 12288,
      "cpu_percent": 45.2,
      "memory_percent": 67.8
    }
  ],
  "summary": {
    "avg_gpu_utilization": 75.2,
    "max_gpu_utilization": 95.1,
    "avg_response_time": 0.5
  }
}
```

### 获取性能统计
```http
GET /api/monitoring/performance
```

查询参数：
- `model_id` (string): 模型ID（可选）
- `time_range` (string): 时间范围 (1h, 24h, 7d, 30d)

响应：
```json
{
  "time_range": "24h",
  "models": [
    {
      "model_id": "model-123",
      "model_name": "my-model",
      "total_requests": 1000,
      "successful_requests": 995,
      "failed_requests": 5,
      "avg_response_time": 0.5,
      "max_response_time": 2.1,
      "min_response_time": 0.1,
      "requests_per_second": 11.6,
      "error_rate": 0.005
    }
  ],
  "system": {
    "avg_cpu_percent": 45.2,
    "avg_memory_percent": 67.8,
    "avg_gpu_utilization": 75.2
  }
}
```

## 配置管理API

### 获取系统配置
```http
GET /api/config
```

响应：
```json
{
  "gpu_monitor_interval": 30,
  "max_concurrent_models": 10,
  "default_model_timeout": 300,
  "health_check_interval": 60,
  "log_level": "INFO",
  "alert_thresholds": {
    "gpu_utilization_high": 90,
    "gpu_temperature_high": 80,
    "response_time_high": 2.0,
    "error_rate_high": 0.05
  }
}
```

### 更新系统配置
```http
PUT /api/config
```

请求体：
```json
{
  "gpu_monitor_interval": 60,
  "max_concurrent_models": 15,
  "alert_thresholds": {
    "gpu_utilization_high": 85,
    "gpu_temperature_high": 75
  }
}
```

### 获取告警规则
```http
GET /api/config/alerts
```

### 创建告警规则
```http
POST /api/config/alerts
```

请求体：
```json
{
  "name": "高GPU使用率告警",
  "condition": "gpu_utilization > 90",
  "severity": "warning",
  "enabled": true,
  "notification_channels": ["email", "webhook"]
}
```

## WebSocket API

### 连接WebSocket
```javascript
const ws = new WebSocket('ws://your-server:8000/ws/monitor');
```

### 订阅事件
```javascript
ws.send(JSON.stringify({
  "action": "subscribe",
  "events": ["model_status", "gpu_metrics", "system_alerts"]
}));
```

### 事件类型

#### 模型状态更新
```json
{
  "type": "model_status_update",
  "data": {
    "model_id": "model-123",
    "status": "running",
    "health": "healthy",
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

#### GPU指标更新
```json
{
  "type": "gpu_metrics_update",
  "data": {
    "gpu_id": 0,
    "utilization": 78.5,
    "memory_used": 12288,
    "temperature": 65,
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

#### 系统告警
```json
{
  "type": "system_alert",
  "data": {
    "alert_id": "alert-456",
    "severity": "warning",
    "message": "GPU使用率过高",
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

## 错误处理

### 错误响应格式
```json
{
  "error": {
    "code": "MODEL_NOT_FOUND",
    "message": "指定的模型不存在",
    "details": {
      "model_id": "invalid-model-123"
    }
  },
  "timestamp": "2024-01-01T12:00:00Z",
  "path": "/api/models/invalid-model-123"
}
```

### HTTP状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 201 | 资源创建成功 |
| 400 | 请求参数错误 |
| 401 | 未授权访问 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 422 | 请求数据验证失败 |
| 429 | 请求频率超限 |
| 500 | 服务器内部错误 |
| 503 | 服务不可用 |

### 常见错误码

| 错误码 | 说明 |
|--------|------|
| INVALID_REQUEST | 请求格式错误 |
| AUTHENTICATION_FAILED | 认证失败 |
| AUTHORIZATION_FAILED | 授权失败 |
| MODEL_NOT_FOUND | 模型不存在 |
| MODEL_ALREADY_EXISTS | 模型已存在 |
| MODEL_NOT_RUNNING | 模型未运行 |
| INSUFFICIENT_RESOURCES | 资源不足 |
| OPERATION_TIMEOUT | 操作超时 |
| INTERNAL_ERROR | 内部错误 |

## SDK和客户端库

### Python SDK
```bash
pip install llm-inference-client
```

```python
from llm_inference_client import LLMInferenceClient

client = LLMInferenceClient(
    base_url="http://your-server:8000",
    api_token="YOUR_API_TOKEN"
)

# 获取模型列表
models = client.list_models()

# 创建模型
model = client.create_model(
    name="my-model",
    framework="llama.cpp",
    config={"model_path": "/models/model.bin"}
)

# 生成文本
response = client.generate(
    model_id=model.id,
    prompt="Hello, world!",
    max_tokens=100
)
```

### JavaScript SDK
```bash
npm install llm-inference-client
```

```javascript
import { LLMInferenceClient } from 'llm-inference-client';

const client = new LLMInferenceClient({
  baseURL: 'http://your-server:8000',
  apiToken: 'YOUR_API_TOKEN'
});

// 获取模型列表
const models = await client.listModels();

// 创建模型
const model = await client.createModel({
  name: 'my-model',
  framework: 'vllm',
  config: { model_name: 'meta-llama/Llama-2-7b-hf' }
});

// 生成文本
const response = await client.generate({
  modelId: model.id,
  prompt: 'Hello, world!',
  maxTokens: 100
});
```

### cURL示例

#### 创建模型
```bash
curl -X POST http://your-server:8000/api/models \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-model",
    "framework": "llama.cpp",
    "config": {
      "model_path": "/models/model.bin",
      "n_ctx": 2048
    }
  }'
```

#### 启动模型
```bash
curl -X POST http://your-server:8000/api/models/model-123/start \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

#### 生成文本
```bash
curl -X POST http://your-server:8000/api/models/model-123/generate \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Hello, world!",
    "max_tokens": 100,
    "temperature": 0.7
  }'
```

---

更多详细信息和最新更新请参考[在线API文档](http://your-server:8000/docs)。