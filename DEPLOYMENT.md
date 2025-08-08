# LLM推理服务部署指南

本文档提供了LLM推理服务的完整部署指南，包括开发环境和生产环境的部署方式。

## 目录

- [系统要求](#系统要求)
- [快速开始](#快速开始)
- [Docker部署](#docker部署)
- [源码部署](#源码部署)
- [生产环境部署](#生产环境部署)
- [配置说明](#配置说明)
- [监控和日志](#监控和日志)
- [故障排除](#故障排除)

## 系统要求

### 最低要求
- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / RHEL 8+
- **CPU**: 4核心
- **内存**: 8GB RAM
- **存储**: 50GB可用空间
- **网络**: 稳定的互联网连接

### 推荐配置
- **操作系统**: Ubuntu 22.04 LTS
- **CPU**: 8核心或更多
- **内存**: 16GB RAM或更多
- **存储**: 100GB SSD
- **GPU**: NVIDIA GPU (可选，用于模型推理)

### 软件依赖
- Docker 20.10+
- Docker Compose 2.0+
- Python 3.11+
- Node.js 18+
- Git

## 快速开始

### 1. 克隆项目
```bash
git clone https://github.com/your-org/llm-inference-service.git
cd llm-inference-service
```

### 2. 安装TiUP和TiDB（必须步骤）
```bash
# 安装TiUP工具
./scripts/install-tiup.sh

# 启动TiDB Playground
./scripts/start-tidb.sh

# 验证TiDB运行状态
./scripts/status-tidb.sh
```

### 3. 配置环境变量
```bash
# 复制环境变量模板
cp configs/.env.template .env

# 编辑配置文件（数据库URL已自动配置为本地TiDB）
nano .env
```

### 4. 选择部署方式

#### 方式一：Docker部署（推荐）
```bash
# 一键部署（自动处理TiDB启动）
./scripts/deploy.sh production --build

# 或者分步执行
./scripts/start-tidb.sh  # 确保TiDB运行
docker-compose up -d --build
```

#### 方式二：源码部署
```bash
# 一键源码部署
./scripts/deploy-source.sh production --daemon

# 或者开发环境
./scripts/deploy-source.sh development
```

### 5. 验证部署
```bash
# 检查TiDB状态
./scripts/status-tidb.sh

# 检查Docker服务状态（如果使用Docker部署）
docker-compose ps

# 检查源码服务状态（如果使用源码部署）
./scripts/status-source.sh

# 测试API服务
curl http://localhost:8000/health

# 访问Web界面
curl http://localhost:3000
```

### 6. 访问服务
- **前端界面**: http://localhost:3000
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **TiDB数据库**: mysql -h 127.0.0.1 -P 4000 -u root
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin)

## Docker部署

Docker部署方式使用容器化的应用服务，但**数据库使用本地安装的TiDB**，不在Docker容器中运行。

### 部署前准备
```bash
# 1. 安装TiUP和启动TiDB（必须）
./scripts/install-tiup.sh
./scripts/start-tidb.sh

# 2. 验证TiDB运行状态
./scripts/status-tidb.sh
```

### 开发环境
```bash
# 启动开发环境（自动启动本地TiDB）
./scripts/deploy.sh development --build --logs

# 或者手动启动
# 先启动TiDB
./scripts/start-tidb.sh
# 再启动Docker服务
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### 生产环境
```bash
# 启动生产环境（自动启动本地TiDB）
./scripts/deploy.sh production --build

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 服务管理命令
```bash
# 启动所有服务（不包括数据库）
docker-compose up -d

# 停止Docker服务（TiDB继续运行）
docker-compose down

# 重启特定服务
docker-compose restart llm-backend

# 查看服务日志
docker-compose logs -f llm-backend

# 进入容器
docker-compose exec llm-backend bash

# 更新服务
docker-compose pull
docker-compose up -d

# 完全停止所有服务（包括TiDB）
docker-compose down
./scripts/stop-tidb.sh
```

### Docker + TiDB架构说明
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │     TiDB        │
│   (Docker)      │    │   (Docker)      │    │   (本地TiUP)     │
│   Port: 3000    │    │   Port: 8000    │    │   Port: 4000    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │     Redis       │
                    │   (Docker)      │
                    │   Port: 6379    │
                    └─────────────────┘
```

### 优势
- **应用服务容器化**: 环境一致性和部署便利性
- **数据库本地化**: 更好的性能和数据持久性
- **混合架构**: 结合容器和本地服务的优势
- **独立管理**: 数据库和应用服务可以独立启停

## 源码部署

源码部署适合需要自定义配置或不使用Docker的环境。这种方式直接在主机上运行Python和Node.js服务。

### 快速源码部署

#### 1. 一键部署（推荐）
```bash
# 开发环境部署
./scripts/deploy-source.sh development

# 生产环境部署
./scripts/deploy-source.sh production --daemon

# 仅后端服务（无前端）
./scripts/deploy-source.sh production --no-frontend --daemon

# 跳过依赖安装（如果已安装）
./scripts/deploy-source.sh development --skip-deps
```

#### 2. 服务管理
```bash
# 查看服务状态
./scripts/status-source.sh

# 停止所有服务
./scripts/stop-source.sh

# 重启服务
./scripts/restart-source.sh production

# 查看日志
tail -f backend/logs/uvicorn.log
tail -f backend/logs/frontend.log
```

### 手动源码部署

#### 1. 环境准备
```bash
# 安装Python 3.11
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# 安装Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# 安装其他依赖
sudo apt install -y git curl wget build-essential
```

#### 2. 项目设置
```bash
# 克隆项目
git clone https://github.com/your-org/llm-inference-service.git
cd llm-inference-service

# 创建环境配置
cp configs/.env.template .env
nano .env  # 编辑配置
```

#### 3. 后端部署
```bash
cd backend

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 数据库迁移
export PYTHONPATH=$PWD
alembic upgrade head

# 启动后端服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 4. 前端部署
```bash
cd frontend

# 安装依赖
npm install

# 开发环境启动
npm run dev

# 生产环境构建和启动
npm run build
npm install -g serve
serve -s dist -l 3000
```

### 生产环境源码部署

#### 1. 系统服务配置
```bash
# 使用部署脚本创建systemd服务
./scripts/deploy-source.sh production --daemon

# 手动管理systemd服务
sudo systemctl start llm-inference-backend
sudo systemctl enable llm-inference-backend
sudo systemctl status llm-inference-backend
```

#### 2. 进程管理
```bash
# 使用PM2管理Node.js进程（可选）
npm install -g pm2

# 启动前端服务
pm2 start "serve -s dist -l 3000" --name llm-frontend

# 启动后端服务
pm2 start "uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4" --name llm-backend

# 保存PM2配置
pm2 save
pm2 startup
```

#### 3. 反向代理配置
```bash
# 安装Nginx
sudo apt install -y nginx

# 使用项目提供的配置
sudo cp configs/nginx.conf /etc/nginx/sites-available/llm-inference
sudo ln -s /etc/nginx/sites-available/llm-inference /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 源码部署优势

- **灵活性高**: 可以直接修改代码和配置
- **调试方便**: 容易进行开发和调试
- **资源占用少**: 无Docker容器开销
- **启动速度快**: 直接启动应用程序

### 源码部署注意事项

- **依赖管理**: 需要手动管理Python和Node.js依赖
- **环境隔离**: 建议使用虚拟环境避免依赖冲突
- **进程管理**: 需要配置进程管理器确保服务稳定运行
- **安全性**: 需要手动配置文件权限和用户权限

## 生产环境部署

### 1. 系统准备
```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础工具
sudo apt install -y curl wget git htop

# 创建应用目录
sudo mkdir -p /opt/llm-inference-service
cd /opt/llm-inference-service
```

### 2. 安装服务
```bash
# 运行安装脚本
sudo ./scripts/install.sh

# 配置环境变量
sudo nano /etc/llm-inference/backend.env
```

### 3. 启动系统服务
```bash
# 启动服务
sudo systemctl start llm-inference-service

# 设置开机自启
sudo systemctl enable llm-inference-service

# 查看服务状态
sudo systemctl status llm-inference-service

# 查看日志
sudo journalctl -u llm-inference-service -f
```

### 4. 配置反向代理（可选）
```bash
# 安装Nginx
sudo apt install -y nginx

# 复制配置文件
sudo cp configs/nginx.conf /etc/nginx/sites-available/llm-inference
sudo ln -s /etc/nginx/sites-available/llm-inference /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx
```

### 5. 配置SSL证书（可选）
```bash
# 安装Certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取SSL证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo crontab -e
# 添加: 0 12 * * * /usr/bin/certbot renew --quiet
```

## 配置说明

### 环境变量配置
主要配置文件位于 `.env`，包含以下关键配置：

```bash
# 数据库配置
DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:4000/llm_inference
REDIS_URL=redis://127.0.0.1:6379/0

# 应用配置
APP_ENV=production
LOG_LEVEL=INFO
SECRET_KEY=your-secret-key

# GPU配置
GPU_MONITOR_INTERVAL=30
MAX_CONCURRENT_MODELS=10

# 监控配置
PROMETHEUS_PORT=9090
GRAFANA_PASSWORD=admin
```

### TiDB数据库配置

本项目使用TiDB作为主数据库，通过TiUP工具进行本地安装和管理，**不使用Docker容器**。

#### 1. 安装TiUP工具
```bash
# 自动安装TiUP（推荐）
./scripts/install-tiup.sh

# 或者手动安装
curl --proto '=https' --tlsv1.2 -sSf https://tiup-mirrors.pingcap.com/install.sh | sh
source ~/.bashrc

# 验证安装
tiup --version
```

#### 2. 开发环境 - TiDB Playground
```bash
# 使用脚本启动（推荐）
./scripts/start-tidb.sh

# 或者直接使用tiup命令
tiup playground --db 1 --pd 1 --kv 1 --tiflash 0 --host 0.0.0.0 --db.port 4000 --pd.port 2379

# 后台模式启动
./scripts/start-tidb.sh --daemon
# 或者
nohup tiup playground --db 1 --pd 1 --kv 1 --tiflash 0 --host 0.0.0.0 --db.port 4000 --pd.port 2379 > tidb.log 2>&1 &
```

#### 3. TiDB服务管理
```bash
# 启动TiDB服务
./scripts/start-tidb.sh

# 前台模式启动（用于调试）
./scripts/start-tidb.sh --foreground

# 停止TiDB服务
./scripts/stop-tidb.sh

# 查看TiDB状态
./scripts/status-tidb.sh

# 查看TiDB日志
tail -f tidb.log
```

#### 4. 数据库连接配置
```bash
# 环境变量配置（.env文件）
DATABASE_URL=mysql+pymysql://root:@127.0.0.1:4000/llm_inference?charset=utf8mb4

# 连接池配置
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_size": 20,
    "max_overflow": 30,
    "pool_pre_ping": True,
    "pool_recycle": 3600,
}
```

#### 5. 生产环境 - TiDB集群
```bash
# 创建集群拓扑配置文件
cat > topology.yaml << EOF
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
EOF

# 部署TiDB集群
tiup cluster deploy llm-inference-prod v7.5.0 topology.yaml --user tidb
tiup cluster start llm-inference-prod

# 查看集群状态
tiup cluster display llm-inference-prod
```

#### 6. 数据库操作
```bash
# 连接TiDB数据库
mysql -h 127.0.0.1 -P 4000 -u root

# 创建数据库
mysql -h 127.0.0.1 -P 4000 -u root -e "CREATE DATABASE IF NOT EXISTS llm_inference"

# 运行数据库迁移
cd backend
source venv/bin/activate
alembic upgrade head
```

### 模型配置
```bash
# 模型存储目录
mkdir -p /opt/llm-inference-service/models

# 下载模型文件
wget -O /opt/llm-inference-service/models/model.bin https://example.com/model.bin
```

## 监控和日志

### 访问监控界面
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin)
- **应用监控**: http://localhost:8000/metrics

### 日志查看
```bash
# 应用日志
docker-compose logs -f llm-backend

# 系统服务日志
sudo journalctl -u llm-inference-service -f

# 文件日志
tail -f backend/logs/application.log
```

### 备份和恢复
```bash
# 创建备份
./scripts/backup.sh

# 恢复备份
tar -xzf backups/llm-inference-backup-20240101_120000.tar.gz
# 恢复数据库和配置文件
```

## 故障排除

### 常见问题

#### 1. 服务无法启动
```bash
# 检查Docker服务
sudo systemctl status docker

# 检查端口占用
sudo netstat -tlnp | grep :8000

# 查看详细错误日志
docker-compose logs llm-backend
```

#### 2. TiDB数据库连接失败
```bash
# 检查TiDB Playground状态
./scripts/status-tidb.sh

# 启动TiDB Playground（如果未运行）
./scripts/start-tidb.sh

# 测试数据库连接
mysql -h 127.0.0.1 -P 4000 -u root -e "SELECT 1"

# 检查TiDB进程
ps aux | grep -E 'tidb-server|tikv-server|pd-server|tiup playground'

# 检查TiDB端口占用
netstat -tlnp | grep -E ':(4000|2379|2380|20160)'

# 查看TiDB日志
tail -f tidb.log

# 重启TiDB服务
./scripts/stop-tidb.sh
./scripts/start-tidb.sh

# 在容器中测试数据库连接
docker-compose exec llm-backend python -c "
import sys
sys.path.append('.')
try:
    from app.core.database import engine
    result = engine.execute('SELECT 1').scalar()
    print(f'数据库连接成功: {result}')
except Exception as e:
    print(f'数据库连接失败: {e}')
"

# 手动创建数据库（如果不存在）
mysql -h 127.0.0.1 -P 4000 -u root -e "CREATE DATABASE IF NOT EXISTS llm_inference"
```

#### 2.1. TiUP安装问题
```bash
# 检查TiUP是否正确安装
tiup --version

# 重新安装TiUP
rm -rf ~/.tiup
curl --proto '=https' --tlsv1.2 -sSf https://tiup-mirrors.pingcap.com/install.sh | sh
source ~/.bashrc

# 安装TiDB组件
tiup install playground tidb tikv pd

# 检查已安装组件
tiup list --installed
```

#### 2.2. TiDB Playground启动失败
```bash
# 检查系统资源
free -h
df -h

# 检查端口冲突
sudo lsof -i :4000
sudo lsof -i :2379

# 清理TiUP数据目录
rm -rf ~/.tiup/data/playground

# 使用详细日志启动
tiup playground --db 1 --pd 1 --kv 1 --tiflash 0 --host 0.0.0.0 --db.port 4000 --pd.port 2379 --log.level debug

# 检查防火墙设置
sudo ufw status
sudo iptables -L
```

#### 3. GPU不可用
```bash
# 检查GPU状态
nvidia-smi

# 检查NVIDIA Docker
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi

# 重启Docker服务
sudo systemctl restart docker
```

#### 4. 内存不足
```bash
# 检查内存使用
free -h
docker stats

# 清理Docker资源
docker system prune -a
```

### 性能优化

#### 1. 数据库优化
```sql
-- TiDB优化配置
SET GLOBAL tidb_enable_clustered_index = ON;
SET GLOBAL tidb_hash_join_concurrency = 8;
```

#### 2. 应用优化
```bash
# 调整工作进程数
export UVICORN_WORKERS=4

# 启用缓存
export REDIS_CACHE_TTL=3600
```

#### 3. 系统优化
```bash
# 调整文件描述符限制
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# 调整内核参数
echo "net.core.somaxconn = 65535" >> /etc/sysctl.conf
sysctl -p
```

## 安全建议

### 1. 网络安全
- 使用防火墙限制访问端口
- 配置SSL/TLS加密
- 使用VPN或专用网络

### 2. 应用安全
- 定期更新依赖包
- 使用强密码和密钥
- 启用访问日志和审计

### 3. 数据安全
- 定期备份数据
- 加密敏感数据
- 限制数据库访问权限

## 更新和维护

### 1. 应用更新
```bash
# 拉取最新代码
git pull origin main

# 重新构建和部署
./scripts/deploy.sh production --build

# 运行数据库迁移
docker-compose exec llm-backend alembic upgrade head
```

### 2. 系统维护
```bash
# 清理日志
find backend/logs -name "*.log" -mtime +30 -delete

# 清理Docker资源
docker system prune -f

# 更新系统包
sudo apt update && sudo apt upgrade -y
```

### 3. 监控检查
```bash
# 检查服务健康状态
curl http://localhost:8000/health

# 检查资源使用情况
docker stats

# 检查磁盘空间
df -h
```

## 支持和帮助

如果遇到问题，请：

1. 查看日志文件获取详细错误信息
2. 检查[故障排除](#故障排除)部分
3. 提交Issue到项目仓库
4. 联系技术支持团队

---

更多详细信息请参考项目文档和API文档。