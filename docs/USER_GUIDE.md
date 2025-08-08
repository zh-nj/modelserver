# LLM推理服务用户指南

欢迎使用LLM推理服务！本指南将帮助您快速上手并充分利用系统的各项功能。

## 目录

- [系统概述](#系统概述)
- [快速开始](#快速开始)
- [模型管理](#模型管理)
- [系统监控](#系统监控)
- [API使用](#api使用)
- [常见问题](#常见问题)
- [最佳实践](#最佳实践)

## 系统概述

LLM推理服务是一个全面的大语言模型管理和监控平台，提供以下核心功能：

### 主要特性
- **多框架支持**: 支持llama.cpp、vLLM等主流推理框架
- **智能调度**: 基于优先级的GPU资源自动分配
- **实时监控**: 全面的系统和模型性能监控
- **Web界面**: 直观的管理和监控界面
- **RESTful API**: 完整的编程接口

### 系统架构
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web前端界面   │    │   RESTful API   │    │   模型推理引擎  │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ • 模型管理      │    │ • 模型CRUD      │    │ • llama.cpp     │
│ • 系统监控      │    │ • 系统监控      │    │ • vLLM          │
│ • 配置管理      │    │ • 资源调度      │    │ • Docker容器    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   资源调度器    │
                    ├─────────────────┤
                    │ • GPU资源管理   │
                    │ • 优先级调度    │
                    │ • 自动恢复      │
                    └─────────────────┘
```

## 快速开始

### 1. 访问系统
打开浏览器，访问系统地址：
- **Web界面**: http://your-server:3000
- **API文档**: http://your-server:8000/docs

### 2. 系统概览
登录后，您将看到系统仪表板，包含：
- **系统状态**: CPU、内存、GPU使用情况
- **模型概览**: 当前运行的模型数量和状态
- **资源使用**: 实时资源使用图表
- **最近活动**: 系统操作日志

### 3. 部署方式说明
系统支持两种主要的部署方式：

#### Docker部署（推荐）
- **优势**: 环境隔离、部署简单、易于管理
- **适用场景**: 生产环境、容器化基础设施
- **管理命令**: 
  ```bash
  ./scripts/deploy.sh production --build
  docker-compose ps
  docker-compose logs -f
  ```

#### 源码部署
- **优势**: 灵活性高、调试方便、资源占用少
- **适用场景**: 开发环境、需要自定义配置的场景
- **管理命令**:
  ```bash
  ./scripts/deploy-source.sh development
  ./scripts/status-source.sh
  ./scripts/stop-source.sh
  ```

### 3. 第一个模型
让我们创建并启动您的第一个模型：

1. 点击左侧菜单的"模型管理"
2. 点击"添加模型"按钮
3. 填写模型信息：
   ```
   模型名称: my-first-model
   框架类型: llama.cpp
   模型路径: /path/to/your/model.bin
   优先级: 5 (1-10，数字越大优先级越高)
   ```
4. 点击"保存"创建模型
5. 在模型列表中找到新创建的模型，点击"启动"

## 模型管理

### 创建模型配置

#### 基本信息
- **模型名称**: 唯一标识符，用于API调用
- **显示名称**: 用户友好的显示名称
- **描述**: 模型的详细描述
- **标签**: 用于分类和搜索的标签

#### 框架配置
根据选择的框架类型，配置相应参数：

**llama.cpp配置**:
```json
{
  "model_path": "/models/llama-7b.bin",
  "n_ctx": 2048,
  "n_threads": 4,
  "n_gpu_layers": 32,
  "temperature": 0.7,
  "top_p": 0.9
}
```

**vLLM配置**:
```json
{
  "model_name": "meta-llama/Llama-2-7b-hf",
  "tensor_parallel_size": 1,
  "max_num_seqs": 256,
  "max_model_len": 2048,
  "gpu_memory_utilization": 0.9
}
```

#### 资源配置
- **GPU需求**: 所需的GPU数量
- **内存需求**: 预估的GPU内存使用量
- **CPU核心**: CPU核心数需求
- **优先级**: 资源调度优先级 (1-10)

### 模型生命周期管理

#### 启动模型
1. 在模型列表中选择要启动的模型
2. 点击"启动"按钮
3. 系统会自动分配资源并启动模型
4. 启动过程可在"活动日志"中查看

#### 停止模型
1. 选择正在运行的模型
2. 点击"停止"按钮
3. 系统会优雅地关闭模型并释放资源

#### 重启模型
1. 选择要重启的模型
2. 点击"重启"按钮
3. 系统会先停止模型，然后重新启动

#### 删除模型
1. 确保模型已停止
2. 选择要删除的模型
3. 点击"删除"按钮
4. 确认删除操作

### 模型状态说明

| 状态 | 说明 | 操作 |
|------|------|------|
| 未启动 | 模型配置已创建但未启动 | 可启动 |
| 启动中 | 模型正在启动过程中 | 等待完成 |
| 运行中 | 模型正常运行，可接受请求 | 可停止、重启 |
| 停止中 | 模型正在停止过程中 | 等待完成 |
| 错误 | 模型启动或运行出现错误 | 查看日志，重启 |
| 等待资源 | 等待GPU资源分配 | 等待或调整优先级 |

## 系统监控

### 实时监控仪表板

#### GPU监控
- **GPU利用率**: 实时GPU使用率图表
- **显存使用**: GPU内存使用情况
- **温度监控**: GPU温度变化趋势
- **功耗监控**: GPU功耗使用情况

#### 系统资源
- **CPU使用率**: 系统CPU使用情况
- **内存使用**: 系统内存使用情况
- **磁盘I/O**: 磁盘读写性能
- **网络流量**: 网络收发流量

#### 模型性能
- **响应时间**: 模型推理响应时间
- **请求量**: 每秒处理的请求数
- **错误率**: 请求失败率统计
- **并发数**: 当前并发请求数

### 告警和通知

#### 告警规则
系统预设了以下告警规则：
- GPU使用率超过90%
- GPU温度超过80°C
- 模型响应时间超过2秒
- 错误率超过5%
- 磁盘空间不足10%

#### 通知方式
- **Web通知**: 浏览器内通知
- **邮件通知**: 发送告警邮件
- **Webhook**: 调用外部API接口

### 历史数据查询

#### 时间范围选择
- 最近1小时
- 最近24小时
- 最近7天
- 最近30天
- 自定义时间范围

#### 数据导出
支持导出监控数据为以下格式：
- CSV格式
- JSON格式
- Excel格式

## API使用

### 认证方式
API使用Bearer Token认证：
```bash
curl -H "Authorization: Bearer YOUR_API_TOKEN" \
     http://your-server:8000/api/models
```

### 常用API端点

#### 模型管理
```bash
# 获取模型列表
GET /api/models

# 创建模型
POST /api/models
{
  "name": "my-model",
  "framework": "llama.cpp",
  "config": {...}
}

# 启动模型
POST /api/models/{model_id}/start

# 停止模型
POST /api/models/{model_id}/stop

# 获取模型状态
GET /api/models/{model_id}/status
```

#### 推理请求
```bash
# 发送推理请求
POST /api/models/{model_id}/generate
{
  "prompt": "Hello, how are you?",
  "max_tokens": 100,
  "temperature": 0.7
}
```

#### 系统监控
```bash
# 获取系统状态
GET /api/system/status

# 获取GPU信息
GET /api/system/gpu

# 获取监控指标
GET /api/monitoring/metrics?start_time=2024-01-01&end_time=2024-01-02
```

### SDK使用示例

#### Python SDK
```python
from llm_inference_client import LLMInferenceClient

# 创建客户端
client = LLMInferenceClient(
    base_url="http://your-server:8000",
    api_token="YOUR_API_TOKEN"
)

# 创建模型
model = client.create_model(
    name="my-model",
    framework="llama.cpp",
    config={
        "model_path": "/models/model.bin",
        "n_ctx": 2048
    }
)

# 启动模型
client.start_model(model.id)

# 发送推理请求
response = client.generate(
    model_id=model.id,
    prompt="Hello, world!",
    max_tokens=100
)

print(response.text)
```

#### JavaScript SDK
```javascript
import { LLMInferenceClient } from 'llm-inference-client';

// 创建客户端
const client = new LLMInferenceClient({
  baseURL: 'http://your-server:8000',
  apiToken: 'YOUR_API_TOKEN'
});

// 创建模型
const model = await client.createModel({
  name: 'my-model',
  framework: 'vllm',
  config: {
    model_name: 'meta-llama/Llama-2-7b-hf'
  }
});

// 启动模型
await client.startModel(model.id);

// 发送推理请求
const response = await client.generate({
  modelId: model.id,
  prompt: 'Hello, world!',
  maxTokens: 100
});

console.log(response.text);
```

## 常见问题

### Q: 模型启动失败怎么办？
A: 请检查以下几点：
1. 模型文件路径是否正确
2. GPU资源是否充足
3. 查看错误日志获取详细信息
4. 检查模型配置参数是否正确

### Q: 如何提高模型推理性能？
A: 可以尝试以下优化方法：
1. 调整批处理大小
2. 使用更多GPU并行
3. 优化模型量化设置
4. 调整上下文长度

### Q: 系统资源不足怎么办？
A: 建议采取以下措施：
1. 停止不必要的模型
2. 调整模型优先级
3. 增加硬件资源
4. 优化模型配置

### Q: 如何备份和恢复配置？
A: 使用以下命令：
```bash
# 备份
./scripts/backup.sh

# 恢复
tar -xzf backup.tar.gz
./scripts/restore.sh
```

### Q: 如何更新系统？
A: 按照以下步骤：
1. 备份当前配置和数据
2. 拉取最新代码
3. 重新构建和部署
4. 运行数据库迁移

## 最佳实践

### 模型配置
1. **合理设置优先级**: 重要模型设置高优先级
2. **资源预估**: 准确估算模型资源需求
3. **参数调优**: 根据使用场景调整推理参数
4. **定期更新**: 及时更新模型版本

### 资源管理
1. **监控资源使用**: 定期检查资源使用情况
2. **合理分配**: 避免资源过度分配
3. **弹性扩展**: 根据负载动态调整资源
4. **故障恢复**: 配置自动故障恢复机制

### 安全建议
1. **访问控制**: 设置适当的访问权限
2. **数据加密**: 加密敏感数据传输
3. **定期备份**: 定期备份重要数据
4. **日志审计**: 启用详细的操作日志

### 性能优化
1. **缓存策略**: 合理使用缓存提高性能
2. **负载均衡**: 使用负载均衡分散请求
3. **异步处理**: 使用异步方式处理长时间任务
4. **资源池化**: 复用资源减少开销

---

如需更多帮助，请参考[API文档](API_REFERENCE.md)或联系技术支持。