# LLM推理服务

一个全面的大语言模型(LLM)推理管理和监控服务，支持多种推理框架和GPU设备。系统提供智能资源调度、自动模型管理和基于Web的AI模型部署管理功能。

## ✨ 核心特性

- 🚀 **多框架支持**: 支持llama.cpp、vLLM等主流推理框架
- 🧠 **智能调度**: 基于优先级的GPU资源自动分配和抢占机制
- 📊 **实时监控**: 全面的GPU利用率、模型健康状态和性能跟踪
- 🌐 **跨平台界面**: Vue.js + Framework7统一的桌面端、移动端、平板端体验
- 🔄 **高可用性**: 自动故障转移、恢复和持久化配置
- 🔌 **完整API**: RESTful API + WebSocket实时通信
- 📱 **PWA支持**: 支持离线访问和桌面安装

## 🏗️ 系统架构

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

## 🛠️ 技术栈

- **后端**: FastAPI + Python 3.11 + SQLAlchemy + TiDB
- **前端**: Vue.js 3 + Framework7 + TypeScript + Vite
- **数据库**: TiDB + Redis
- **监控**: Prometheus + Grafana
- **部署**: Docker + Docker Compose + systemd
- **代理**: Nginx

## 📋 系统要求

### 最低要求
- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / RHEL 8+
- **CPU**: 4核心
- **内存**: 8GB RAM
- **存储**: 50GB可用空间

### 推荐配置
- **操作系统**: Ubuntu 22.04 LTS
- **CPU**: 8核心或更多
- **内存**: 16GB RAM或更多
- **存储**: 100GB SSD
- **GPU**: NVIDIA GPU (可选，用于模型推理)

## 🚀 快速开始

### 方式一：Docker部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/your-org/llm-inference-service.git
cd llm-inference-service

# 2. 配置环境变量
cp configs/.env.template .env
nano .env  # 编辑配置

# 3. 一键部署
./scripts/deploy.sh production --build

# 4. 验证部署
curl http://localhost:8000/health
```

### 方式二：源码部署

```bash
# 1. 克隆项目
git clone https://github.com/your-org/llm-inference-service.git
cd llm-inference-service

# 2. 一键源码部署
./scripts/deploy-source.sh production --daemon

# 3. 查看服务状态
./scripts/status-source.sh
```

## 🌐 访问服务

部署完成后，您可以通过以下地址访问服务：

- **前端界面**: http://localhost:3000
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001

## 📖 文档

- [用户指南](docs/USER_GUIDE.md) - 详细的用户操作手册
- [API文档](docs/API_REFERENCE.md) - 完整的API参考文档
- [部署指南](DEPLOYMENT.md) - 从开发到生产的部署说明

## 🔧 管理命令

### Docker部署管理
```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 备份数据
./scripts/backup.sh
```

### 源码部署管理
```bash
# 查看服务状态
./scripts/status-source.sh

# 停止服务
./scripts/stop-source.sh

# 查看日志
tail -f backend/logs/uvicorn.log

# 重启服务（重新运行部署脚本）
./scripts/deploy-source.sh production --daemon
```

## 🎯 使用示例

### 创建和启动模型

#### Web界面
1. 访问 http://localhost:3000
2. 点击"模型管理" → "添加模型"
3. 填写模型配置并保存
4. 点击"启动"按钮

#### API调用
```bash
# 创建模型
curl -X POST http://localhost:8000/api/models \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-model",
    "framework": "llama.cpp",
    "config": {
      "model_path": "/models/model.bin",
      "n_ctx": 2048
    }
  }'

# 启动模型
curl -X POST http://localhost:8000/api/models/my-model/start

# 发送推理请求
curl -X POST http://localhost:8000/api/models/my-model/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Hello, world!",
    "max_tokens": 100
  }'
```

## 🔍 监控和告警

系统提供全面的监控功能：

- **GPU监控**: 利用率、内存使用、温度、功耗
- **模型性能**: 响应时间、请求量、错误率
- **系统资源**: CPU、内存、磁盘、网络
- **自动告警**: 邮件、Webhook通知

访问 Grafana 仪表板查看详细监控数据：http://localhost:3001

## 🛡️ 安全特性

- **API认证**: Bearer Token认证机制
- **访问控制**: 基于角色的权限管理
- **数据加密**: HTTPS/TLS加密传输
- **审计日志**: 完整的操作日志记录

## 🔄 高可用性

- **自动故障恢复**: 模型自动重启和资源重新分配
- **健康检查**: 实时监控模型和服务健康状态
- **负载均衡**: 多实例负载分发
- **数据备份**: 自动配置和数据备份

## 🧪 测试

```bash
# 运行后端测试
cd backend
python -m pytest tests/

# 运行前端测试
cd frontend
npm test

# 运行集成测试
python backend/run_tests.py
```

## 📊 性能基准

在标准配置下的性能表现：

- **并发处理**: 支持100+并发推理请求
- **响应时间**: 平均响应时间 < 500ms
- **资源利用**: GPU利用率可达95%+
- **系统稳定性**: 7x24小时稳定运行

## 🤝 贡献指南

我们欢迎社区贡献！请遵循以下步骤：

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📝 更新日志

### v1.0.0 (2024-01-01)
- ✨ 初始版本发布
- 🚀 支持llama.cpp和vLLM框架
- 📊 完整的监控和告警系统
- 🌐 跨平台Web界面
- 🐳 Docker和源码两种部署方式

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🆘 支持

如果您遇到问题或需要帮助：

1. 查看[文档](docs/)
2. 搜索[Issues](https://github.com/your-org/llm-inference-service/issues)
3. 创建新的[Issue](https://github.com/your-org/llm-inference-service/issues/new)
4. 联系技术支持: support@your-domain.com

## 🙏 致谢

感谢以下开源项目的支持：

- [FastAPI](https://fastapi.tiangolo.com/) - 现代、快速的Web框架
- [Vue.js](https://vuejs.org/) - 渐进式JavaScript框架
- [Framework7](https://framework7.io/) - 跨平台移动应用框架
- [TiDB](https://pingcap.com/) - 分布式数据库
- [Prometheus](https://prometheus.io/) - 监控和告警系统

---

⭐ 如果这个项目对您有帮助，请给我们一个星标！