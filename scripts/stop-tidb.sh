#!/bin/bash

# TiDB Playground停止脚本

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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 停止TiDB服务
stop_tidb() {
    log_info "停止TiDB Playground..."
    
    # 查找并终止TiDB相关进程
    local processes_found=false
    
    # 停止tiup playground进程
    if pgrep -f "tiup playground" > /dev/null; then
        log_info "终止tiup playground进程..."
        pkill -f "tiup playground" || true
        processes_found=true
    fi
    
    # 停止TiDB组件进程
    for component in tidb-server tikv-server pd-server; do
        if pgrep -f "$component" > /dev/null; then
            log_info "终止$component进程..."
            pkill -f "$component" || true
            processes_found=true
        fi
    done
    
    if [ "$processes_found" = false ]; then
        log_warning "未找到运行中的TiDB进程"
    else
        # 等待进程完全停止
        log_info "等待进程完全停止..."
        sleep 5
        
        # 强制终止残留进程
        pkill -9 -f "tiup playground" 2>/dev/null || true
        pkill -9 -f "tidb-server" 2>/dev/null || true
        pkill -9 -f "tikv-server" 2>/dev/null || true
        pkill -9 -f "pd-server" 2>/dev/null || true
    fi
    
    # 清理PID文件
    if [ -f "$PROJECT_ROOT/tidb.pid" ]; then
        rm -f "$PROJECT_ROOT/tidb.pid"
        log_info "清理PID文件"
    fi
    
    # 验证停止状态
    if curl -f http://localhost:4000/status &>/dev/null; then
        log_warning "TiDB服务可能仍在运行，请手动检查"
    else
        log_success "TiDB Playground已完全停止"
    fi
}

# 清理临时文件
cleanup_temp_files() {
    log_info "清理临时文件..."
    
    # 清理TiUP临时目录（谨慎操作）
    if [ -d "$HOME/.tiup/data" ]; then
        log_info "清理TiUP临时数据..."
        rm -rf "$HOME/.tiup/data/playground" 2>/dev/null || true
    fi
    
    # 清理项目临时文件
    rm -f "$PROJECT_ROOT/tidb.log" 2>/dev/null || true
    
    log_success "临时文件清理完成"
}

# 显示停止后状态
show_final_status() {
    log_info "最终状态检查..."
    
    # 检查端口占用
    local ports_in_use=false
    for port in 4000 2379 2380 20160; do
        if netstat -tlnp 2>/dev/null | grep ":$port " > /dev/null; then
            log_warning "端口 $port 仍被占用"
            ports_in_use=true
        fi
    done
    
    if [ "$ports_in_use" = false ]; then
        log_success "所有TiDB相关端口已释放"
    else
        log_warning "部分端口仍被占用，可能需要手动处理"
        log_info "使用以下命令检查端口占用:"
        log_info "  netstat -tlnp | grep -E ':(4000|2379|2380|20160) '"
    fi
    
    # 检查进程
    if pgrep -f "tidb-server\|tikv-server\|pd-server\|tiup playground" > /dev/null; then
        log_warning "仍有TiDB相关进程在运行"
        log_info "使用以下命令检查进程:"
        log_info "  ps aux | grep -E 'tidb-server|tikv-server|pd-server|tiup playground'"
    else
        log_success "所有TiDB相关进程已停止"
    fi
}

# 主函数
main() {
    log_info "开始停止TiDB Playground..."
    
    stop_tidb
    cleanup_temp_files
    show_final_status
    
    log_success "TiDB Playground停止操作完成"
}

# 错误处理
trap 'log_error "停止过程中发生错误"; exit 1' ERR

# 执行主函数
main