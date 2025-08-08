#!/bin/bash

# LLM推理服务源码部署停止脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 停止后端服务
stop_backend() {
    log_info "停止后端服务..."
    
    cd "$PROJECT_ROOT/backend"
    
    if [ -f "backend.pid" ]; then
        BACKEND_PID=$(cat backend.pid)
        if kill -0 $BACKEND_PID 2>/dev/null; then
            log_info "停止后端进程 (PID: $BACKEND_PID)..."
            kill -TERM $BACKEND_PID
            
            # 等待进程结束
            for i in {1..10}; do
                if ! kill -0 $BACKEND_PID 2>/dev/null; then
                    break
                fi
                sleep 1
            done
            
            # 强制结束
            if kill -0 $BACKEND_PID 2>/dev/null; then
                log_warning "强制结束后端进程..."
                kill -KILL $BACKEND_PID
            fi
            
            rm -f backend.pid
            log_success "后端服务已停止"
        else
            log_warning "后端进程不存在"
            rm -f backend.pid
        fi
    else
        log_info "未找到后端进程ID文件"
    fi
    
    # 查找并停止其他uvicorn进程
    pkill -f "uvicorn.*app.main:app" || true
}

# 停止前端服务
stop_frontend() {
    log_info "停止前端服务..."
    
    cd "$PROJECT_ROOT/frontend"
    
    if [ -f "frontend.pid" ]; then
        FRONTEND_PID=$(cat frontend.pid)
        if kill -0 $FRONTEND_PID 2>/dev/null; then
            log_info "停止前端进程 (PID: $FRONTEND_PID)..."
            kill -TERM $FRONTEND_PID
            
            # 等待进程结束
            for i in {1..10}; do
                if ! kill -0 $FRONTEND_PID 2>/dev/null; then
                    break
                fi
                sleep 1
            done
            
            # 强制结束
            if kill -0 $FRONTEND_PID 2>/dev/null; then
                log_warning "强制结束前端进程..."
                kill -KILL $FRONTEND_PID
            fi
            
            rm -f frontend.pid
            log_success "前端服务已停止"
        else
            log_warning "前端进程不存在"
            rm -f frontend.pid
        fi
    else
        log_info "未找到前端进程ID文件"
    fi
    
    # 查找并停止其他相关进程
    pkill -f "serve.*dist" || true
    pkill -f "npm.*run.*dev" || true
    pkill -f "vite.*dev" || true
}

# 停止systemd服务
stop_systemd_services() {
    log_info "停止systemd服务..."
    
    if systemctl is-active --quiet llm-inference-backend 2>/dev/null; then
        sudo systemctl stop llm-inference-backend
        log_success "后端systemd服务已停止"
    fi
    
    if systemctl is-active --quiet llm-inference-frontend 2>/dev/null; then
        sudo systemctl stop llm-inference-frontend
        log_success "前端systemd服务已停止"
    fi
}

# 主函数
main() {
    log_info "停止LLM推理服务..."
    
    cd "$PROJECT_ROOT"
    
    stop_systemd_services
    stop_backend
    stop_frontend
    
    log_success "所有服务已停止"
}

# 执行主函数
main