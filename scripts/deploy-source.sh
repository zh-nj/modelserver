#!/bin/bash

# LLM推理服务源码一键部署脚本
# 用法: ./scripts/deploy-source.sh [环境] [选项]
# 环境: development, staging, production
# 选项: --skip-deps, --no-frontend, --logs, --daemon

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 默认配置
ENVIRONMENT=${1:-development}
SKIP_DEPS=false
NO_FRONTEND=false
SHOW_LOGS=false
DAEMON_MODE=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 解析命令行参数
for arg in "$@"; do
    case $arg in
        --skip-deps)
            SKIP_DEPS=true
            shift
            ;;
        --no-frontend)
            NO_FRONTEND=true
            shift
            ;;
        --logs)
            SHOW_LOGS=true
            shift
            ;;
        --daemon)
            DAEMON_MODE=true
            shift
            ;;
    esac
done

# 检查系统依赖
check_system_dependencies() {
    log_info "检查系统依赖..."
    
    # 检查Python
    if ! command -v python3.11 &> /dev/null; then
        if ! command -v python3 &> /dev/null; then
            log_error "Python 3.11或Python 3未安装"
            log_info "请运行: sudo apt install python3.11 python3.11-venv python3.11-dev"
            exit 1
        else
            PYTHON_CMD="python3"
        fi
    else
        PYTHON_CMD="python3.11"
    fi
    
    # 检查TiUP
    if ! command -v tiup &> /dev/null; then
        log_warning "TiUP未安装，正在安装..."
        curl --proto '=https' --tlsv1.2 -sSf https://tiup-mirrors.pingcap.com/install.sh | sh
        source ~/.bashrc
        
        if ! command -v tiup &> /dev/null; then
            log_error "TiUP安装失败，请手动安装"
            exit 1
        fi
    fi
    
    # 检查Node.js (如果需要前端)
    if [ "$NO_FRONTEND" = false ]; then
        if ! command -v node &> /dev/null; then
            log_error "Node.js未安装"
            log_info "请运行: curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash - && sudo apt-get install -y nodejs"
            exit 1
        fi
        
        # 检查Node.js版本
        NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
        if [ "$NODE_VERSION" -lt 16 ]; then
            log_error "Node.js版本过低，需要16+版本"
            exit 1
        fi
    fi
    
    # 检查其他系统工具
    for cmd in curl wget git; do
        if ! command -v $cmd &> /dev/null; then
            log_error "$cmd 未安装"
            log_info "请运行: sudo apt install $cmd"
            exit 1
        fi
    done
    
    log_success "系统依赖检查通过"
}

# 检查TiDB状态
check_tidb_status() {
    # 使用MySQL协议检测TiDB连接状态
    if command -v mysql &> /dev/null; then
        if mysql -h 127.0.0.1 -P 4000 -u root -e "SELECT 1" &>/dev/null; then
            return 0
        else
            return 1
        fi
    else
        # 如果没有mysql客户端，使用netstat检查端口
        if netstat -tlnp 2>/dev/null | grep ":4000 " > /dev/null; then
            return 0
        else
            return 1
        fi
    fi
}

# 启动TiDB Playground
start_tidb_playground() {
    log_info "启动TiDB Playground..."
    
    # 检查TiDB是否已经运行
    if check_tidb_status; then
        log_info "TiDB已经在运行"
        return
    fi
    
    # 创建TiDB数据目录
    TIDB_DATA_DIR="/mnt/DATA/datas/tidb"
    mkdir -p "$TIDB_DATA_DIR"
    
    # 启动TiDB Playground
    log_info "启动TiDB Playground（后台模式）..."
    log_info "数据目录: $TIDB_DATA_DIR"
    
    # 切换到数据目录，这样TiUP会在这里创建数据文件
    cd "$TIDB_DATA_DIR"
    nohup tiup playground --db 1 --pd 1 --kv 1 --tiflash 0 --host 0.0.0.0 --db.port 4000 --pd.port 2379 --tag llm-inference > "$PROJECT_ROOT/tidb.log" 2>&1 &
    cd "$PROJECT_ROOT"
    
    # 等待TiDB启动
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if check_tidb_status; then
            log_success "TiDB Playground启动成功"
            break
        fi
        
        log_info "等待TiDB启动... ($attempt/$max_attempts)"
        sleep 3
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        log_error "TiDB启动超时"
        log_info "请检查 $PROJECT_ROOT/tidb.log 文件获取详细错误信息"
        exit 1
    fi
}

# 检查和创建环境配置
setup_environment() {
    log_info "设置环境配置..."
    
    cd "$PROJECT_ROOT"
    
    # 创建.env文件
    if [ ! -f ".env" ]; then
        if [ -f "configs/.env.template" ]; then
            log_info "从模板创建.env文件..."
            cp configs/.env.template .env
            
            # 根据环境调整配置
            if [ "$ENVIRONMENT" = "development" ]; then
                sed -i 's/APP_ENV=production/APP_ENV=development/' .env
                sed -i 's/LOG_LEVEL=INFO/LOG_LEVEL=DEBUG/' .env
                sed -i 's/DEBUG=false/DEBUG=true/' .env
                sed -i 's/AUTO_RELOAD=false/AUTO_RELOAD=true/' .env
            fi
            
            # 更新数据库URL为本地TiDB
            sed -i 's|DATABASE_URL=.*|DATABASE_URL=mysql+pymysql://root:@127.0.0.1:4000/llm_inference?charset=utf8mb4|' .env
            
            log_warning "请根据实际环境编辑.env文件中的配置"
        else
            log_error ".env模板文件不存在"
            exit 1
        fi
    fi
    
    # 启动TiDB Playground
    start_tidb_playground
    
    # 加载环境变量
    source .env
    
    log_success "环境配置完成"
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."
    
    cd "$PROJECT_ROOT"
    
    # 创建数据目录
    mkdir -p backend/logs
    mkdir -p backend/data
    mkdir -p models
    mkdir -p configs/ssl
    mkdir -p backups
    
    # 设置权限
    chmod 755 backend/logs backend/data models
    
    log_success "目录创建完成"
}

# 安装Python依赖
install_python_dependencies() {
    if [ "$SKIP_DEPS" = true ]; then
        log_info "跳过Python依赖安装"
        return
    fi
    
    log_info "安装Python依赖..."
    
    cd "$PROJECT_ROOT/backend"
    
    # 创建虚拟环境
    if [ ! -d "venv" ]; then
        log_info "创建Python虚拟环境..."
        $PYTHON_CMD -m venv venv
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 升级pip
    pip install --upgrade pip
    
    # 安装依赖
    log_info "安装Python包..."
    pip install -r requirements.txt
    
    # 安装开发依赖（开发环境）
    if [ "$ENVIRONMENT" = "development" ] && [ -f "requirements-dev.txt" ]; then
        pip install -r requirements-dev.txt
    fi
    
    log_success "Python依赖安装完成"
}

# 安装Node.js依赖
install_nodejs_dependencies() {
    if [ "$NO_FRONTEND" = true ] || [ "$SKIP_DEPS" = true ]; then
        log_info "跳过Node.js依赖安装"
        return
    fi
    
    log_info "安装Node.js依赖..."
    
    cd "$PROJECT_ROOT/frontend"
    
    # 安装依赖
    npm install
    
    log_success "Node.js依赖安装完成"
}

# 构建前端
build_frontend() {
    if [ "$NO_FRONTEND" = true ]; then
        log_info "跳过前端构建"
        return
    fi
    
    log_info "构建前端应用..."
    
    cd "$PROJECT_ROOT/frontend"
    
    if [ "$ENVIRONMENT" = "production" ]; then
        npm run build
        log_success "前端生产版本构建完成"
    else
        log_info "开发环境将使用开发服务器"
    fi
}

# 初始化数据库
initialize_database() {
    log_info "初始化数据库..."
    
    cd "$PROJECT_ROOT/backend"
    source venv/bin/activate
    
    # 检查数据库连接
    if [ -n "$DATABASE_URL" ] && [[ "$DATABASE_URL" == *"mysql"* ]]; then
        log_info "检测到MySQL/TiDB数据库配置"
        
        # 等待数据库服务
        log_info "等待TiDB数据库服务就绪..."
        for i in {1..30}; do
            if python -c "
import sys
sys.path.append('.')
try:
    from app.core.database import sync_engine
    from sqlalchemy import text
    with sync_engine.connect() as conn:
        result = conn.execute(text('SELECT 1'))
        print('TiDB数据库连接成功')
    sys.exit(0)
except Exception as e:
    print(f'TiDB数据库连接失败: {e}')
    sys.exit(1)
" 2>/dev/null; then
                break
            fi
            
            if [ $i -eq 30 ]; then
                log_error "TiDB数据库连接超时"
                log_info "请确保TiDB Playground已启动并且连接配置正确"
                log_info "检查TiDB日志: tail -f $PROJECT_ROOT/tidb.log"
                exit 1
            fi
            
            sleep 2
        done
        
        # 创建数据库（如果不存在）
        log_info "创建数据库（如果不存在）..."
        python -c "
import sys
sys.path.append('.')
try:
    import pymysql
    conn = pymysql.connect(host='127.0.0.1', port=4000, user='root', password='')
    cursor = conn.cursor()
    cursor.execute('CREATE DATABASE IF NOT EXISTS llm_inference')
    conn.commit()
    conn.close()
    print('数据库创建成功')
except Exception as e:
    print(f'数据库创建失败: {e}')
    sys.exit(1)
" || {
            log_warning "数据库创建失败，可能已存在"
        }
        
        # 运行数据库迁移
        log_info "运行数据库迁移..."
        if alembic upgrade head 2>/dev/null; then
            log_success "数据库迁移完成"
        else
            log_warning "数据库迁移失败，尝试使用同步方式创建表..."
            python -c "
import sys
sys.path.append('.')
try:
    from app.core.database import db_manager
    db_manager.create_tables()
    print('数据库表创建成功')
except Exception as e:
    print(f'数据库表创建失败: {e}')
" || log_warning "数据库表创建失败，但服务仍可启动"
        fi
    else
        log_info "使用SQLite数据库，无需额外配置"
    fi
    
    log_success "数据库初始化完成"
}

# 启动后端服务
start_backend() {
    log_info "启动后端服务..."
    
    cd "$PROJECT_ROOT/backend"
    source venv/bin/activate
    
    # 设置环境变量
    export PYTHONPATH="$PROJECT_ROOT/backend"
    export APP_ENV="$ENVIRONMENT"
    
    # 启动参数
    HOST="0.0.0.0"
    PORT="8000"
    WORKERS=1
    
    if [ "$ENVIRONMENT" = "production" ]; then
        WORKERS=4
        LOG_LEVEL="info"
        RELOAD=""
    else
        LOG_LEVEL="debug"
        RELOAD="--reload"
    fi
    
    # 启动命令
    if [ "$DAEMON_MODE" = true ]; then
        log_info "以守护进程模式启动后端服务..."
        nohup uvicorn app.main:app \
            --host $HOST \
            --port $PORT \
            --workers $WORKERS \
            --log-level $LOG_LEVEL \
            $RELOAD \
            > backend/logs/uvicorn.log 2>&1 &
        
        BACKEND_PID=$!
        echo $BACKEND_PID > "$PROJECT_ROOT/backend/backend.pid"
        log_success "后端服务已启动 (PID: $BACKEND_PID)"
    else
        log_info "启动后端服务 (前台模式)..."
        uvicorn app.main:app \
            --host $HOST \
            --port $PORT \
            --workers $WORKERS \
            --log-level $LOG_LEVEL \
            $RELOAD &
        
        BACKEND_PID=$!
        echo $BACKEND_PID > "$PROJECT_ROOT/backend/backend.pid"
    fi
}

# 启动前端服务
start_frontend() {
    if [ "$NO_FRONTEND" = true ]; then
        log_info "跳过前端服务启动"
        return
    fi
    
    log_info "启动前端服务..."
    
    cd "$PROJECT_ROOT/frontend"
    
    if [ "$ENVIRONMENT" = "production" ]; then
        # 生产环境使用静态文件服务
        if command -v serve &> /dev/null; then
            if [ "$DAEMON_MODE" = true ]; then
                nohup serve -s dist -l 3000 > ../backend/logs/frontend.log 2>&1 &
                FRONTEND_PID=$!
                echo $FRONTEND_PID > frontend.pid
                log_success "前端服务已启动 (PID: $FRONTEND_PID)"
            else
                serve -s dist -l 3000 &
                FRONTEND_PID=$!
                echo $FRONTEND_PID > frontend.pid
            fi
        else
            log_warning "serve命令未找到，请安装: npm install -g serve"
            log_info "或使用nginx等Web服务器托管dist目录"
        fi
    else
        # 开发环境使用开发服务器
        if [ "$DAEMON_MODE" = true ]; then
            nohup npm run dev > ../backend/logs/frontend.log 2>&1 &
            FRONTEND_PID=$!
            echo $FRONTEND_PID > frontend.pid
            log_success "前端开发服务器已启动 (PID: $FRONTEND_PID)"
        else
            npm run dev &
            FRONTEND_PID=$!
            echo $FRONTEND_PID > frontend.pid
        fi
    fi
}

# 等待服务启动
wait_for_services() {
    log_info "等待服务启动..."
    
    # 等待后端服务
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:8000/health &>/dev/null; then
            log_success "后端服务已就绪"
            break
        fi
        
        log_info "等待后端服务启动... ($attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        log_error "后端服务启动超时"
        return 1
    fi
    
    # 等待前端服务（如果启用）
    if [ "$NO_FRONTEND" = false ]; then
        attempt=1
        while [ $attempt -le $max_attempts ]; do
            if curl -f http://localhost:3000 &>/dev/null; then
                log_success "前端服务已就绪"
                break
            fi
            
            log_info "等待前端服务启动... ($attempt/$max_attempts)"
            sleep 2
            ((attempt++))
        done
        
        if [ $attempt -gt $max_attempts ]; then
            log_warning "前端服务启动超时，但后端服务可正常使用"
        fi
    fi
}

# 创建systemd服务文件
create_systemd_service() {
    if [ "$ENVIRONMENT" != "production" ]; then
        return
    fi
    
    log_info "创建systemd服务文件..."
    
    # 后端服务文件
    cat > /tmp/llm-inference-backend.service << EOF
[Unit]
Description=LLM推理服务后端
After=network.target

[Service]
Type=exec
User=$USER
Group=$USER
WorkingDirectory=$PROJECT_ROOT/backend
Environment=PYTHONPATH=$PROJECT_ROOT/backend
Environment=APP_ENV=production
EnvironmentFile=$PROJECT_ROOT/.env
ExecStart=$PROJECT_ROOT/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=mixed
Restart=on-failure
RestartSec=5
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF
    
    # 前端服务文件（如果需要）
    if [ "$NO_FRONTEND" = false ]; then
        cat > /tmp/llm-inference-frontend.service << EOF
[Unit]
Description=LLM推理服务前端
After=network.target llm-inference-backend.service

[Service]
Type=exec
User=$USER
Group=$USER
WorkingDirectory=$PROJECT_ROOT/frontend
ExecStart=/usr/bin/serve -s dist -l 3000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    fi
    
    # 安装服务文件
    sudo mv /tmp/llm-inference-backend.service /etc/systemd/system/
    if [ "$NO_FRONTEND" = false ]; then
        sudo mv /tmp/llm-inference-frontend.service /etc/systemd/system/
    fi
    
    # 重新加载systemd
    sudo systemctl daemon-reload
    
    log_success "systemd服务文件已创建"
    log_info "使用以下命令管理服务:"
    log_info "  sudo systemctl start llm-inference-backend"
    log_info "  sudo systemctl enable llm-inference-backend"
    if [ "$NO_FRONTEND" = false ]; then
        log_info "  sudo systemctl start llm-inference-frontend"
        log_info "  sudo systemctl enable llm-inference-frontend"
    fi
}

# 显示部署信息
show_deployment_info() {
    log_success "源码部署完成！"
    echo
    log_info "服务信息:"
    log_info "  环境: $ENVIRONMENT"
    log_info "  后端服务: http://localhost:8000"
    if [ "$NO_FRONTEND" = false ]; then
        log_info "  前端界面: http://localhost:3000"
    fi
    log_info "  API文档: http://localhost:8000/docs"
    echo
    
    log_info "进程信息:"
    if [ -f "backend/backend.pid" ]; then
        BACKEND_PID=$(cat backend/backend.pid)
        log_info "  后端进程ID: $BACKEND_PID"
    fi
    if [ -f "frontend/frontend.pid" ]; then
        FRONTEND_PID=$(cat frontend/frontend.pid)
        log_info "  前端进程ID: $FRONTEND_PID"
    fi
    echo
    
    log_info "管理命令:"
    log_info "  停止服务: ./scripts/stop-source.sh"
    log_info "  重启服务: ./scripts/restart-source.sh"
    log_info "  查看日志: tail -f backend/logs/uvicorn.log"
    log_info "  查看状态: ./scripts/status-source.sh"
    echo
    
    log_info "配置文件:"
    log_info "  环境配置: .env"
    log_info "  后端配置: backend/app/core/config.py"
    log_info "  前端配置: frontend/vite.config.ts"
    echo
    
    if [ "$SHOW_LOGS" = true ]; then
        log_info "显示服务日志..."
        if [ -f "backend/logs/uvicorn.log" ]; then
            tail -f backend/logs/uvicorn.log
        else
            log_warning "日志文件不存在，服务可能未正常启动"
        fi
    fi
}

# 清理函数
cleanup() {
    log_info "清理临时文件..."
    # 清理临时文件
    rm -f /tmp/llm-inference-*.service
}

# 主函数
main() {
    log_info "开始源码部署LLM推理服务..."
    log_info "环境: $ENVIRONMENT"
    
    # 设置清理陷阱
    trap cleanup EXIT
    
    check_system_dependencies
    setup_environment
    create_directories
    install_python_dependencies
    install_nodejs_dependencies
    build_frontend
    initialize_database
    start_backend
    start_frontend
    wait_for_services
    create_systemd_service
    show_deployment_info
}

# 错误处理
trap 'log_error "部署过程中发生错误，请检查日志"; cleanup; exit 1' ERR

# 执行主函数
main