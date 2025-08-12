#!/bin/bash

# LLM推理服务启动脚本
# 用法: ./scripts/start-services.sh [选项]
# 选项: --backend-only, --frontend-only, --stop, --status, --logs

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
BACKEND_ONLY=false
FRONTEND_ONLY=false
STOP_SERVICES=false
SHOW_STATUS=false
SHOW_LOGS=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 解析命令行参数
for arg in "$@"; do
    case $arg in
        --backend-only)
            BACKEND_ONLY=true
            shift
            ;;
        --frontend-only)
            FRONTEND_ONLY=true
            shift
            ;;
        --stop)
            STOP_SERVICES=true
            shift
            ;;
        --status)
            SHOW_STATUS=true
            shift
            ;;
        --logs)
            SHOW_LOGS=true
            shift
            ;;
    esac
done

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3未安装"
        exit 1
    fi
    
    # 检查Node.js
    if ! command -v node &> /dev/null; then
        log_error "Node.js未安装"
        exit 1
    fi
    
    # 检查npm
    if ! command -v npm &> /dev/null; then
        log_error "npm未安装"
        exit 1
    fi
    
    log_success "依赖检查通过"
}

# 检查服务状态
check_service_status() {
    local service_name=$1
    local port=$2
    
    if netstat -tlnp 2>/dev/null | grep ":$port " > /dev/null; then
        return 0
    else
        return 1
    fi
}

# 停止服务
stop_services() {
    log_info "停止服务..."
    
    # 使用stop-source.sh脚本停止服务
    if [ -f "$PROJECT_ROOT/scripts/stop-source.sh" ]; then
        log_info "使用stop-source.sh脚本停止服务..."
        ./scripts/stop-source.sh
    else
        # 备用停止逻辑
        log_warning "stop-source.sh脚本不存在，使用备用停止逻辑..."
        
        # 停止后端服务
        if [ -f "$PROJECT_ROOT/backend/backend.pid" ]; then
            local backend_pid=$(cat "$PROJECT_ROOT/backend/backend.pid")
            if ps -p $backend_pid > /dev/null 2>&1; then
                log_info "停止后端服务 (PID: $backend_pid)..."
                kill $backend_pid
                sleep 2
                if ps -p $backend_pid > /dev/null 2>&1; then
                    log_warning "强制停止后端服务..."
                    kill -9 $backend_pid
                fi
            fi
            rm -f "$PROJECT_ROOT/backend/backend.pid"
        fi
        
        # 停止前端服务
        if [ -f "$PROJECT_ROOT/frontend/frontend.pid" ]; then
            local frontend_pid=$(cat "$PROJECT_ROOT/frontend/frontend.pid")
            if ps -p $frontend_pid > /dev/null 2>&1; then
                log_info "停止前端服务 (PID: $frontend_pid)..."
                kill $frontend_pid
                sleep 2
                if ps -p $frontend_pid > /dev/null 2>&1; then
                    log_warning "强制停止前端服务..."
                    kill -9 $frontend_pid
                fi
            fi
            rm -f "$PROJECT_ROOT/frontend/frontend.pid"
        fi
        
        # 清理其他可能的进程
        pkill -f "uvicorn.*app.main:app" || true
        pkill -f "vite.*--port 3000" || true
        pkill -f "npm.*run.*dev" || true
        
        log_success "服务已停止"
    fi
}

# 启动后端服务
start_backend() {
    log_info "启动后端服务..."
    
    cd "$PROJECT_ROOT"
    
    # 检查是否已经运行
    if check_service_status "backend" 8000; then
        log_warning "后端服务已经在运行 (端口 8000)"
        return
    fi
    
    # 使用deploy-source.sh脚本启动后端服务
    log_info "使用deploy-source.sh脚本启动后端服务..."
    ./scripts/deploy-source.sh development --no-frontend --daemon
    
    # 等待服务启动
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if check_service_status "backend" 8000; then
            log_success "后端服务启动成功"
            log_info "后端服务地址: http://localhost:8000"
            log_info "API文档: http://localhost:8000/docs"
            break
        fi
        
        log_info "等待后端服务启动... ($attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        log_error "后端服务启动超时"
        log_info "请检查日志文件: $PROJECT_ROOT/backend/logs/uvicorn.log"
        exit 1
    fi
}

# 启动前端服务
start_frontend() {
    log_info "启动前端服务..."
    
    cd "$PROJECT_ROOT/frontend"
    
    # 检查是否已经运行
    if check_service_status "frontend" 3000; then
        log_warning "前端服务已经在运行 (端口 3000)"
        return
    fi
    
    # 安装依赖
    if [ ! -d "node_modules" ]; then
        log_info "安装Node.js依赖..."
        npm install
    fi
    
    # 启动前端服务
    log_info "启动Vite开发服务器..."
    nohup npm run dev > ../frontend.log 2>&1 &
    echo $! > ../frontend.pid
    
    cd ..
    
    # 等待服务启动
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if check_service_status "frontend" 3000; then
            log_success "前端服务启动成功"
            log_info "前端服务地址: http://localhost:3000"
            break
        fi
        
        log_info "等待前端服务启动... ($attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        log_error "前端服务启动超时"
        log_info "请检查日志文件: $PROJECT_ROOT/frontend.log"
        exit 1
    fi
}

# 显示服务状态
show_status() {
    log_info "检查服务状态..."
    
    # 检查后端服务
    if check_service_status "backend" 8000; then
        log_success "后端服务: 运行中 (http://localhost:8000)"
        # 检查多个可能的PID文件位置
        if [ -f "$PROJECT_ROOT/backend/backend.pid" ]; then
            local pid=$(cat "$PROJECT_ROOT/backend/backend.pid")
            log_info "  进程ID: $pid"
        elif [ -f "$PROJECT_ROOT/backend.pid" ]; then
            local pid=$(cat "$PROJECT_ROOT/backend.pid")
            log_info "  进程ID: $pid"
        fi
    else
        log_warning "后端服务: 未运行"
    fi
    
    # 检查前端服务
    if check_service_status "frontend" 3000; then
        log_success "前端服务: 运行中 (http://localhost:3000)"
        # 检查多个可能的PID文件位置
        if [ -f "$PROJECT_ROOT/frontend/frontend.pid" ]; then
            local pid=$(cat "$PROJECT_ROOT/frontend/frontend.pid")
            log_info "  进程ID: $pid"
        elif [ -f "$PROJECT_ROOT/frontend.pid" ]; then
            local pid=$(cat "$PROJECT_ROOT/frontend.pid")
            log_info "  进程ID: $pid"
        fi
    else
        log_warning "前端服务: 未运行"
    fi
    
    # 检查TiDB
    if netstat -tlnp 2>/dev/null | grep ":4000 " > /dev/null; then
        log_success "TiDB数据库: 运行中 (http://localhost:4000)"
    else
        log_warning "TiDB数据库: 未运行"
        log_info "请运行: ./scripts/start-tidb.sh"
    fi
}

# 显示日志
show_logs() {
    log_info "显示服务日志..."
    
    # 检查多个可能的后端日志文件位置
    if [ -f "$PROJECT_ROOT/backend/logs/uvicorn.log" ]; then
        log_info "=== 后端服务日志 (uvicorn.log) ==="
        tail -n 20 "$PROJECT_ROOT/backend/logs/uvicorn.log"
        echo
    elif [ -f "$PROJECT_ROOT/backend.log" ]; then
        log_info "=== 后端服务日志 (backend.log) ==="
        tail -n 20 "$PROJECT_ROOT/backend.log"
        echo
    else
        log_warning "未找到后端服务日志文件"
    fi
    
    # 检查多个可能的前端日志文件位置
    if [ -f "$PROJECT_ROOT/backend/logs/frontend.log" ]; then
        log_info "=== 前端服务日志 (backend/logs/frontend.log) ==="
        tail -n 20 "$PROJECT_ROOT/backend/logs/frontend.log"
        echo
    elif [ -f "$PROJECT_ROOT/frontend.log" ]; then
        log_info "=== 前端服务日志 (frontend.log) ==="
        tail -n 20 "$PROJECT_ROOT/frontend.log"
        echo
    else
        log_warning "未找到前端服务日志文件"
    fi
    
    log_info "实时日志监控:"
    if [ -f "$PROJECT_ROOT/backend/logs/uvicorn.log" ]; then
        log_info "  后端日志: tail -f $PROJECT_ROOT/backend/logs/uvicorn.log"
    elif [ -f "$PROJECT_ROOT/backend.log" ]; then
        log_info "  后端日志: tail -f $PROJECT_ROOT/backend.log"
    fi
    
    if [ -f "$PROJECT_ROOT/backend/logs/frontend.log" ]; then
        log_info "  前端日志: tail -f $PROJECT_ROOT/backend/logs/frontend.log"
    elif [ -f "$PROJECT_ROOT/frontend.log" ]; then
        log_info "  前端日志: tail -f $PROJECT_ROOT/frontend.log"
    fi
}

# 主函数
main() {
    cd "$PROJECT_ROOT"
    
    if [ "$STOP_SERVICES" = true ]; then
        stop_services
        return
    fi
    
    if [ "$SHOW_STATUS" = true ]; then
        show_status
        return
    fi
    
    if [ "$SHOW_LOGS" = true ]; then
        show_logs
        return
    fi
    
    check_dependencies
    
    if [ "$BACKEND_ONLY" = true ]; then
        start_backend
    elif [ "$FRONTEND_ONLY" = true ]; then
        start_frontend
    else
        start_backend
        start_frontend
    fi
    
    echo
    log_success "服务启动完成！"
    log_info "访问地址:"
    log_info "  前端界面: http://localhost:3000"
    log_info "  后端API: http://localhost:8000"
    log_info "  API文档: http://localhost:8000/docs"
    echo
    log_info "管理命令:"
    log_info "  查看状态: $0 --status"
    log_info "  查看日志: $0 --logs"
    log_info "  停止服务: $0 --stop"
    echo
    log_info "日志文件:"
    log_info "  后端日志: $PROJECT_ROOT/backend.log"
    log_info "  前端日志: $PROJECT_ROOT/frontend.log"
}

# 错误处理
trap 'log_error "操作过程中发生错误"; exit 1' ERR

# 执行主函数
main