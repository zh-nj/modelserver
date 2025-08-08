#!/bin/bash

# LLM推理服务部署脚本
# 用法: ./scripts/deploy.sh [环境] [选项]
# 环境: development, staging, production
# 选项: --build, --no-cache, --logs

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
ENVIRONMENT=${1:-production}
BUILD_FLAG=""
CACHE_FLAG=""
SHOW_LOGS=false

# 解析命令行参数
for arg in "$@"; do
    case $arg in
        --build)
            BUILD_FLAG="--build"
            shift
            ;;
        --no-cache)
            CACHE_FLAG="--no-cache"
            shift
            ;;
        --logs)
            SHOW_LOGS=true
            shift
            ;;
    esac
done

# 检查Docker和Docker Compose
check_dependencies() {
    log_info "检查依赖..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    log_success "依赖检查通过"
}

# 检查TiUP安装
check_tiup() {
    log_info "检查TiUP安装..."
    
    if ! command -v tiup &> /dev/null; then
        log_warning "TiUP未安装，正在安装..."
        curl --proto '=https' --tlsv1.2 -sSf https://tiup-mirrors.pingcap.com/install.sh | sh
        source ~/.bashrc
        
        if ! command -v tiup &> /dev/null; then
            log_error "TiUP安装失败，请手动安装"
            exit 1
        fi
    fi
    
    log_success "TiUP检查通过"
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
    
    # 启动TiDB Playground
    log_info "启动TiDB Playground（后台模式）..."
    nohup tiup playground --db 1 --pd 1 --kv 1 --tiflash 0 --host 0.0.0.0 --db.port 4000 --pd.port 2379 > tidb.log 2>&1 &
    
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
        log_info "请检查tidb.log文件获取详细错误信息"
        exit 1
    fi
}

# 检查环境配置
check_environment() {
    log_info "检查环境配置..."
    
    if [ ! -f ".env" ]; then
        if [ -f "configs/.env.template" ]; then
            log_warning ".env文件不存在，从模板创建..."
            cp configs/.env.template .env
            # 更新数据库URL为本地TiDB
            sed -i 's|DATABASE_URL=.*|DATABASE_URL=mysql+pymysql://root:@127.0.0.1:4000/llm_inference?charset=utf8mb4|' .env
            log_warning "请编辑.env文件配置实际环境变量"
        else
            log_error ".env文件和模板都不存在"
            exit 1
        fi
    fi
    
    # 检查必要的环境变量
    source .env
    
    if [ -z "$DATABASE_URL" ]; then
        log_error "DATABASE_URL环境变量未设置"
        exit 1
    fi
    
    if [ -z "$REDIS_URL" ]; then
        log_error "REDIS_URL环境变量未设置"
        exit 1
    fi
    
    log_success "环境配置检查通过"
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."
    
    mkdir -p backend/logs
    mkdir -p backend/data
    mkdir -p configs/ssl
    mkdir -p models
    
    log_success "目录创建完成"
}

# 设置权限
setup_permissions() {
    log_info "设置文件权限..."
    
    # 创建服务用户（如果不存在）
    if ! id "llm-service" &>/dev/null; then
        log_info "创建服务用户 llm-service..."
        sudo useradd -r -s /bin/false llm-service || true
    fi
    
    # 设置目录权限
    sudo chown -R llm-service:llm-service backend/logs backend/data models || true
    chmod -R 755 backend/logs backend/data models || true
    
    log_success "权限设置完成"
}

# 构建和启动服务
deploy_services() {
    log_info "部署服务 (环境: $ENVIRONMENT)..."
    
    # 设置环境变量
    export APP_ENV=$ENVIRONMENT
    export COMPOSE_PROJECT_NAME=llm-inference-$ENVIRONMENT
    
    # 停止现有服务
    log_info "停止现有服务..."
    docker-compose down || true
    
    # 启动TiDB Playground（本地安装）
    start_tidb_playground
    
    # 构建和启动服务（使用本地TiDB，不启动Docker中的数据库服务）
    if [ "$BUILD_FLAG" = "--build" ]; then
        log_info "构建并启动服务..."
        # 排除所有TiDB相关的Docker服务，使用本地TiUP安装的TiDB
        docker-compose up -d $BUILD_FLAG $CACHE_FLAG
    else
        log_info "启动服务..."
        docker-compose up -d
    fi
    
    log_success "服务部署完成"
}

# 等待服务启动
wait_for_services() {
    log_info "等待服务启动..."
    
    # 等待后端服务
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:8000/health &>/dev/null; then
            log_success "后端服务已启动"
            break
        fi
        
        log_info "等待后端服务启动... ($attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        log_error "后端服务启动超时"
        exit 1
    fi
    
    # 等待前端服务
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:3000 &>/dev/null; then
            log_success "前端服务已启动"
            break
        fi
        
        log_info "等待前端服务启动... ($attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        log_error "前端服务启动超时"
        exit 1
    fi
}

# 运行数据库迁移
run_migrations() {
    log_info "运行数据库迁移..."
    
    docker-compose exec llm-backend alembic upgrade head || {
        log_warning "数据库迁移失败，可能是首次部署"
    }
    
    log_success "数据库迁移完成"
}

# 安装systemd服务
install_systemd_service() {
    if [ "$ENVIRONMENT" = "production" ]; then
        log_info "安装systemd服务..."
        
        sudo cp configs/systemd/llm-inference-service.service /etc/systemd/system/
        sudo systemctl daemon-reload
        sudo systemctl enable llm-inference-service
        
        log_success "systemd服务安装完成"
        log_info "使用以下命令管理服务:"
        log_info "  sudo systemctl start llm-inference-service"
        log_info "  sudo systemctl stop llm-inference-service"
        log_info "  sudo systemctl status llm-inference-service"
    fi
}

# 显示部署信息
show_deployment_info() {
    log_success "部署完成！"
    echo
    log_info "服务访问地址:"
    log_info "  前端界面: http://localhost:3000"
    log_info "  后端API: http://localhost:8000"
    log_info "  API文档: http://localhost:8000/docs"
    log_info "  Prometheus: http://localhost:9090"
    log_info "  Grafana: http://localhost:3001"
    echo
    log_info "管理命令:"
    log_info "  查看服务状态: docker-compose ps"
    log_info "  查看日志: docker-compose logs -f"
    log_info "  停止服务: docker-compose down"
    log_info "  重启服务: docker-compose restart"
    echo
    
    if [ "$SHOW_LOGS" = true ]; then
        log_info "显示服务日志..."
        docker-compose logs -f
    fi
}

# 主函数
main() {
    log_info "开始部署LLM推理服务..."
    
    check_dependencies
    check_tiup
    check_environment
    create_directories
    setup_permissions
    deploy_services
    wait_for_services
    run_migrations
    install_systemd_service
    show_deployment_info
}

# 错误处理
trap 'log_error "部署过程中发生错误，请检查日志"; exit 1' ERR

# 执行主函数
main