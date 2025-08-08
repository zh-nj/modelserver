---
inclusion: always
---

# 技术栈规范

## 后端框架
- **FastAPI (Python)**: 高性能异步API框架，用于REST端点
- **Python 3.8+**: 核心开发语言，支持async/await异步编程
- **Pydantic**: 数据验证和序列化框架
- **SQLAlchemy**: 数据库ORM，用于配置持久化

## 前端框架
- **Framework7 + Vue.js 3**: 统一的跨平台UI框架，支持桌面端和移动端
- **TypeScript**: 类型安全的JavaScript开发
- **Vite**: 快速构建工具和开发服务器
- **Chart.js/D3.js**: 实时监控数据可视化

## 多终端适配
- **桌面端**: Framework7桌面主题，适配大屏幕操作和鼠标交互
- **移动端**: Framework7移动主题，原生iOS/Android体验
- **平板端**: Framework7自适应主题，平板优化布局
- **PWA支持**: 支持离线访问和桌面安装
- **统一组件库**: Framework7组件在所有平台保持一致性

## 数据存储
- **TiDB**: 本地安装的分布式数据库，配置和状态持久化
- **Redis**: 实时通信、缓存和消息队列
- **Prometheus**: 时间序列指标存储
- **文件日志**: 结构化日志记录和轮转

## 实时通信架构
- **WebSocket**: 前端后端实时消息交互的核心技术
- **FastAPI WebSocket**: 后端WebSocket服务器实现
- **Socket.IO**: 前端WebSocket客户端库，支持自动重连和降级
- **Redis Pub/Sub**: WebSocket消息广播和集群支持

## 基础设施
- **Docker**: vLLM容器化和部署
- **systemd/supervisor**: 进程生命周期管理
- **nginx**: 反向代理和负载均衡，WebSocket升级支持

## AI框架集成
- **llama.cpp**: 直接进程管理和API集成
- **vLLM**: Docker容器编排
- **CUDA/ROCm**: GPU资源检测和管理

## 监控和可观测性
- **Prometheus**: 指标收集
- **Grafana**: 仪表板可视化
- **AlertManager**: 告警路由和通知
- **结构化日志**: JSON格式日志和轮转

## TiDB配置规范

### 数据库连接配置
```python
# SQLAlchemy连接字符串
DATABASE_URL = "mysql+pymysql://root:@127.0.0.1:4000/llm_inference?charset=utf8mb4"

# 连接池配置
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_size": 20,
    "max_overflow": 30,
    "pool_pre_ping": True,
    "pool_recycle": 3600,
}
```

### TiDB集群拓扑配置
```yaml
# topology.yaml
global:
  user: "tidb"
  ssh_port: 22
  deploy_dir: "/tidb-deploy"
  data_dir: "/tidb-data"

pd_servers:
  - host: 127.0.0.1
    client_port: 2379
    peer_port: 2380

tidb_servers:
  - host: 127.0.0.1
    port: 4000
    status_port: 10080

tikv_servers:
  - host: 127.0.0.1
    port: 20160
    status_port: 20180
```

### 数据库优化配置
```sql
-- 设置TiDB系统变量
SET GLOBAL tidb_enable_clustered_index = ON;
SET GLOBAL tidb_hash_join_concurrency = 8;
SET GLOBAL tidb_index_lookup_concurrency = 8;
SET GLOBAL tidb_distsql_scan_concurrency = 15;
```

## WebSocket实时通信规范

### 后端WebSocket实现
```python
# FastAPI WebSocket端点
from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict
import json
import asyncio

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.client_data: Dict[WebSocket, dict] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.client_data[websocket] = {"client_id": client_id}

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        self.client_data.pop(websocket, None)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                await self.disconnect(connection)

# WebSocket消息类型定义
class MessageType:
    MODEL_STATUS_UPDATE = "model_status_update"
    GPU_METRICS_UPDATE = "gpu_metrics_update"
    SYSTEM_ALERT = "system_alert"
    RESOURCE_SCHEDULE = "resource_schedule"
```

### 前端WebSocket客户端
```typescript
// WebSocket客户端封装
class WebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 3000;

  constructor(private url: string) {}

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.url);
      
      this.ws.onopen = () => {
        console.log('WebSocket连接已建立');
        this.reconnectAttempts = 0;
        resolve();
      };

      this.ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        this.handleMessage(message);
      };

      this.ws.onclose = () => {
        console.log('WebSocket连接已关闭');
        this.attemptReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket错误:', error);
        reject(error);
      };
    });
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        this.connect();
      }, this.reconnectInterval);
    }
  }

  private handleMessage(message: any) {
    // 根据消息类型分发到不同的处理器
    switch (message.type) {
      case 'model_status_update':
        this.handleModelStatusUpdate(message.data);
        break;
      case 'gpu_metrics_update':
        this.handleGpuMetricsUpdate(message.data);
        break;
      // 其他消息类型处理...
    }
  }
}
```

### Redis Pub/Sub集群支持
```python
# Redis发布订阅配置
import redis.asyncio as redis
import json

class RedisMessageBroker:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        
    async def publish(self, channel: str, message: dict):
        await self.redis.publish(channel, json.dumps(message))
        
    async def subscribe(self, channel: str, callback):
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        
        async for message in pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                await callback(data)
```

## 开发规范

### 代码风格
- Python代码遵循PEP 8规范
- 使用black进行代码格式化
- 使用mypy进行类型检查
- Vue组件使用Composition API风格

### WebSocket通信规范
- 使用JSON格式进行消息传输
- 定义统一的消息类型和数据结构
- 实现客户端自动重连机制
- 使用心跳检测保持连接活跃

### 数据库设计规范
- 使用AUTO_RANDOM主键避免热点问题
- 合理设计分区表提高查询性能
- 使用TiDB特有的SHARD_ROW_ID_BITS优化写入
- 避免大事务，控制事务大小在100MB以内

### 依赖管理
- 后端使用requirements.txt管理Python依赖
- 前端使用package.json管理Node.js依赖
- 固定版本号避免依赖冲突
- 定期更新安全补丁

## 常用命令

### 开发环境
```bash
# TiDB数据库启动
tiup playground --db 1 --pd 1 --kv 1 --tiflash 0 --host 0.0.0.0

# 或使用TiUP集群管理
tiup cluster start llm-inference-dev

# 后端开发
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 前端开发 (Framework7 + Vue.js)
cd frontend
npm install
npm run dev

# 桌面端模式开发
npm run dev:desktop

# 移动端模式开发  
npm run dev:mobile

# PWA构建和测试
npm run build:pwa
npm run preview:pwa

# 运行测试
pytest tests/
npm run test
```

### 生产部署
```bash
# TiDB生产集群部署
tiup cluster deploy llm-inference-prod v7.5.0 topology.yaml --user tidb
tiup cluster start llm-inference-prod

# 构建前端应用 (Framework7统一构建)
cd frontend
npm run build            # 构建生产版本
npm run build:pwa        # 构建PWA版本

# 构建容器
docker-compose build
docker-compose up -d

# 服务管理
systemctl start llm-inference-service
systemctl enable llm-inference-service
systemctl status llm-inference-service

# 数据库迁移
alembic upgrade head

# 部署静态资源
nginx -s reload          # 重载nginx配置
```

### 监控运维
```bash
# TiDB集群状态检查
tiup cluster display llm-inference-prod
tiup cluster status llm-inference-prod

# TiDB性能监控
tiup cluster exec llm-inference-prod --command "tidb-ctl schema in mysql"

# 检查GPU状态
nvidia-smi
rocm-smi

# 查看日志
journalctl -u llm-inference-service -f
tail -f logs/application.log

# 获取指标
curl http://localhost:8000/metrics

# TiDB监控指标
curl http://localhost:10080/metrics  # TiDB metrics
curl http://localhost:2379/metrics   # PD metrics
```

### 调试工具
```bash
# TiDB数据库调试
mysql -h 127.0.0.1 -P 4000 -u root -D llm_inference
tiup ctl:v7.5.0 pd -u http://127.0.0.1:2379 store

# TiDB慢查询分析
mysql -h 127.0.0.1 -P 4000 -u root -e "SELECT * FROM INFORMATION_SCHEMA.SLOW_QUERY LIMIT 10;"

# WebSocket连接调试
wscat -c ws://localhost:8000/ws/monitor  # 测试WebSocket连接
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" http://localhost:8000/ws/monitor

# 进入容器调试
docker exec -it llm-service bash

# 查看进程状态
ps aux | grep llama
ps aux | grep vllm

# 网络连接检查
netstat -tlnp | grep 8000
netstat -tlnp | grep 4000  # TiDB端口
netstat -tlnp | grep 6379  # Redis端口

# 移动端调试
npm run dev:mobile -- --host 0.0.0.0  # 局域网访问
npm run build:mobile:debug             # 调试版本构建
```

## WebSocket部署配置

### Nginx WebSocket代理配置
```nginx
# nginx.conf
upstream backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name llm-inference.local;

    # 静态文件服务
    location / {
        root /var/www/llm-inference;
        try_files $uri $uri/ /index.html;
    }

    # API代理
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket代理
    location /ws/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket特定配置
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
        proxy_connect_timeout 86400;
    }
}
```

### Redis集群配置
```yaml
# redis-cluster.conf
port 6379
cluster-enabled yes
cluster-config-file nodes.conf
cluster-node-timeout 5000
appendonly yes

# 发布订阅频道定义
channels:
  - model_events      # 模型状态变更
  - gpu_metrics      # GPU指标更新
  - system_alerts    # 系统告警
  - resource_schedule # 资源调度事件
```

## 多终端适配策略

### 设备检测和路由
```javascript
// 自动检测设备类型并路由到对应应用
const isMobile = /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
const isTablet = /iPad|Android.*(?!Mobile)/i.test(navigator.userAgent);

if (isMobile && !isTablet) {
  // 重定向到移动端应用
  window.location.href = '/mobile/';
} else {
  // 加载桌面端应用
  window.location.href = '/desktop/';
}
```

### Framework7统一配置
```javascript
// Framework7桌面端和移动端统一配置
const f7params = {
  name: 'LLM推理服务',
  theme: 'auto', // 自动检测iOS/Android/Desktop主题
  colors: {
    primary: '#007aff',
  },
  routes: routes,
  
  // 桌面端特定配置
  desktop: {
    enabled: true,
    theme: 'desktop',
    width: 1200,
    height: 800,
  },
  
  // 移动端配置
  input: {
    scrollIntoViewOnFocus: true,
  },
  statusbar: {
    iosOverlaysWebView: true,
    androidOverlaysWebView: false,
  },
  
  // 通用配置
  view: {
    pushState: true,
    animate: true,
  },
  
  // 自适应配置
  touch: {
    tapHold: true,
    disableContextMenu: false,
  },
  
  // 数据表格配置（桌面端优化）
  dataTable: {
    resizableColumns: true,
    sortable: true,
  }
};
```

### 响应式断点
```css
/* 移动端优先的响应式设计 */
@media (max-width: 767px) {
  /* 手机端样式 */
}

@media (min-width: 768px) and (max-width: 1023px) {
  /* 平板端样式 */
}

@media (min-width: 1024px) {
  /* 桌面端样式 */
}
```

### PWA配置
```json
// manifest.json
{
  "name": "LLM推理服务",
  "short_name": "LLM服务",
  "description": "大语言模型推理管理平台",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#007aff",
  "icons": [
    {
      "src": "/icons/icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    }
  ]
}
```