#!/bin/bash

# LLM推理服务源码部署状态检查脚本

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

# 检查进程状态
check_process_status() {
    local service_name=$1
    local pid_file=$2
    local port=$3
    
    echo "=== $service_name 状态 ==="
    
    # 检查PID文件
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 $pid 2>/dev/null; then
            log_success "进程运行中 (PID: $pid)"
            
            # 显示进程信息
            ps -p $pid -o pid,ppid,cmd --no-headers | while read line; do
                echo "  进程信息: $line"
            done
            
            # 显示内存使用
            local memory=$(ps -p $pid -o rss --no-headers 2>/dev/null || echo "0")
            echo "  内存使用: $((memory / 1024)) MB"
            
            # 显示CPU使用
            local cpu=$(ps -p $pid -o %cpu --no-headers 2>/dev/null || echo "0")
            echo "  CPU使用: ${cpu}%"
        else
            log_error "进程不存在 (PID文件存在但进程已停止)"
            echo "  PID文件: $pid_file"
            echo "  记录的PID: $pid"
        fi
    else
        log_warning "PID文件不存在: $pid_file"
    fi
    
    # 检查端口监听
    if [ -n "$port" ]; then
        if netstat -tlnp 2>/dev/null | grep ":$port " >/dev/null; then
            log_success "端口 $port 正在监听"
            netstat -tlnp 2>/dev/null | grep ":$port " | while read line; do
                echo "  $line"
            done
        else
            log_error "端口 $port 未在监听"
        fi
        
        # 检查HTTP响应
        if curl -f -s http://localhost:$port/health >/dev/null 2>&1; then
            log_success "HTTP健康检查通过"
        elif curl -f -s http://localhost:$port >/dev/null 2>&1; then
            log_success "HTTP服务响应正常"
        else
            log_error "HTTP服务无响应"
        fi
    fi
    
    echo
}

# 检查systemd服务状态
check_systemd_status() {
    echo "=== Systemd服务状态 ==="
    
    for service in llm-inference-backend llm-inference-frontend; do
        if systemctl list-unit-files | grep -q "$service.service"; then
            local status=$(systemctl is-active $service 2>/dev/null || echo "inactive")
            local enabled=$(systemctl is-enabled $service 2>/dev/null || echo "disabled")
            
            echo "$service:"
            if [ "$status" = "active" ]; then
                log_success "  状态: $status (已启用: $enabled)"
            else
                log_warning "  状态: $status (已启用: $enabled)"
            fi
            
            # 显示最近的日志
            echo "  最近日志:"
            journalctl -u $service --no-pager -n 3 --since "1 hour ago" 2>/dev/null | tail -n 3 | sed 's/^/    /'
        else
            echo "$service: 未安装"
        fi
        echo
    done
}

# 检查资源使用情况
check_resource_usage() {
    echo "=== 系统资源使用情况 ==="
    
    # CPU使用率
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    echo "CPU使用率: ${cpu_usage}%"
    
    # 内存使用率
    local memory_info=$(free | grep Mem)
    local total_mem=$(echo $memory_info | awk '{print $2}')
    local used_mem=$(echo $memory_info | awk '{print $3}')
    local memory_percent=$((used_mem * 100 / total_mem))
    echo "内存使用率: ${memory_percent}% (${used_mem}/${total_mem})"
    
    # 磁盘使用率
    echo "磁盘使用率:"
    df -h | grep -E "/$|/opt|/var" | while read line; do
        echo "  $line"
    done
    
    # GPU状态（如果有）
    if command -v nvidia-smi &> /dev/null; then
        echo
        echo "GPU状态:"
        nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits | while read line; do
            echo "  GPU $line"
        done
    fi
    
    echo
}

# 检查日志文件
check_logs() {
    echo "=== 日志文件状态 ==="
    
    local log_dir="$PROJECT_ROOT/backend/logs"
    
    if [ -d "$log_dir" ]; then
        echo "日志目录: $log_dir"
        
        for log_file in uvicorn.log application.log error.log frontend.log; do
            local full_path="$log_dir/$log_file"
            if [ -f "$full_path" ]; then
                local size=$(du -h "$full_path" | cut -f1)
                local modified=$(stat -c %y "$full_path" | cut -d'.' -f1)
                echo "  $log_file: $size (修改时间: $modified)"
                
                # 显示最近的错误日志
                if [[ "$log_file" == *"error"* ]] || [[ "$log_file" == *"uvicorn"* ]]; then
                    local error_count=$(grep -i "error\|exception\|traceback" "$full_path" 2>/dev/null | wc -l)
                    if [ $error_count -gt 0 ]; then
                        log_warning "    发现 $error_count 个错误/异常"
                    fi
                fi
            else
                echo "  $log_file: 不存在"
            fi
        done
    else
        log_warning "日志目录不存在: $log_dir"
    fi
    
    echo
}

# 检查配置文件
check_configuration() {
    echo "=== 配置文件状态 ==="
    
    cd "$PROJECT_ROOT"
    
    # 检查.env文件
    if [ -f ".env" ]; then
        log_success ".env文件存在"
        echo "  关键配置:"
        grep -E "^(APP_ENV|DATABASE_URL|REDIS_URL|LOG_LEVEL)" .env 2>/dev/null | sed 's/^/    /' || echo "    未找到关键配置项"
    else
        log_error ".env文件不存在"
    fi
    
    # 检查Python虚拟环境
    if [ -d "backend/venv" ]; then
        log_success "Python虚拟环境存在"
        local python_version=$(backend/venv/bin/python --version 2>&1)
        echo "  Python版本: $python_version"
    else
        log_error "Python虚拟环境不存在"
    fi
    
    # 检查Node.js依赖
    if [ -d "frontend/node_modules" ]; then
        log_success "Node.js依赖已安装"
        if [ -f "frontend/package.json" ]; then
            local node_version=$(node --version 2>/dev/null || echo "未知")
            echo "  Node.js版本: $node_version"
        fi
    else
        log_warning "Node.js依赖未安装"
    fi
    
    echo
}

# 检查网络连接
check_network() {
    echo "=== 网络连接状态 ==="
    
    # 检查端口监听
    echo "监听的端口:"
    netstat -tlnp 2>/dev/null | grep -E ":8000|:3000|:6379|:4000" | while read line; do
        echo "  $line"
    done
    
    # 检查外部连接
    echo
    echo "外部服务连接:"
    
    # 检查数据库连接
    if [ -f ".env" ]; then
        source .env
        if [[ "$DATABASE_URL" == *"mysql"* ]]; then
            local db_host=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
            local db_port=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
            if [ -n "$db_host" ] && [ -n "$db_port" ]; then
                if nc -z $db_host $db_port 2>/dev/null; then
                    log_success "  数据库连接正常 ($db_host:$db_port)"
                else
                    log_error "  数据库连接失败 ($db_host:$db_port)"
                fi
            fi
        fi
        
        # 检查Redis连接
        if [[ "$REDIS_URL" == *"redis"* ]]; then
            local redis_host=$(echo $REDIS_URL | sed -n 's/.*\/\/\([^:]*\):.*/\1/p')
            local redis_port=$(echo $REDIS_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
            if [ -n "$redis_host" ] && [ -n "$redis_port" ]; then
                if nc -z $redis_host $redis_port 2>/dev/null; then
                    log_success "  Redis连接正常 ($redis_host:$redis_port)"
                else
                    log_error "  Redis连接失败 ($redis_host:$redis_port)"
                fi
            fi
        fi
    fi
    
    echo
}

# 主函数
main() {
    echo "========================================"
    echo "    LLM推理服务状态检查报告"
    echo "========================================"
    echo "检查时间: $(date)"
    echo "项目路径: $PROJECT_ROOT"
    echo
    
    cd "$PROJECT_ROOT"
    
    # 检查各个组件状态
    check_process_status "后端服务" "backend/backend.pid" "8000"
    check_process_status "前端服务" "frontend/frontend.pid" "3000"
    check_systemd_status
    check_resource_usage
    check_logs
    check_configuration
    check_network
    
    echo "========================================"
    echo "状态检查完成"
    echo "========================================"
}

# 执行主函数
main