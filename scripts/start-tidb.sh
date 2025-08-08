#!/bin/bash

# TiDB Playground启动脚本
# 用法: ./scripts/start-tidb.sh [选项]
# 选项: --foreground (前台运行), --stop (停止服务)

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
FOREGROUND=false
STOP_SERVICE=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 解析命令行参数
for arg in "$@"; do
    case $arg in
        --foreground)
            FOREGROUND=true
            shift
            ;;
        --stop)
            STOP_SERVICE=true
            shift
            ;;
    esac
done

# 检查TiUP安装
check_tiup() {
    if ! command -v tiup &> /dev/null; then
        log_error "TiUP未安装"
        log_info "请运行以下命令安装TiUP:"
        log_info "curl --proto '=https' --tlsv1.2 -sSf https://tiup-mirrors.pingcap.com/install.sh | sh"
        log_info "source ~/.bashrc"
        exit 1
    fi
}

# 停止TiDB服务
stop_tidb() {
    log_info "停止TiDB Playground..."
    
    # 查找并终止TiDB相关进程
    pkill -f "tiup playground" || true
    pkill -f "tidb-server" || true
    pkill -f "tikv-server" || true
    pkill -f "pd-server" || true
    
    # 等待进程完全停止
    sleep 3
    
    # 清理PID文件
    rm -f "$PROJECT_ROOT/tidb.pid"
    
    log_success "TiDB Playground已停止"
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

# 启动TiDB服务
start_tidb() {
    log_info "启动TiDB Playground..."
    
    # 检查是否已经运行
    if check_tidb_status; then
        log_warning "TiDB已经在运行"
        log_info "如需重启，请先运行: $0 --stop"
        return
    fi
    
    cd "$PROJECT_ROOT"
    
    # 创建日志目录
    mkdir -p logs
    
    if [ "$FOREGROUND" = true ]; then
        log_info "前台模式启动TiDB Playground..."
        tiup playground --db 1 --pd 1 --kv 1 --tiflash 0 --host 0.0.0.0 --db.port 4000 --pd.port 2379
    else
        log_info "后台模式启动TiDB Playground..."
        nohup tiup playground --db 1 --pd 1 --kv 1 --tiflash 0 --host 0.0.0.0 --db.port 4000 --pd.port 2379 > logs/tidb.log 2>&1 &
        
        # 保存PID
        echo $! > tidb.pid
        
        # 等待服务启动
        local max_attempts=30
        local attempt=1
        
        while [ $attempt -le $max_attempts ]; do
            if check_tidb_status; then
                log_success "TiDB Playground启动成功"
                log_info "TiDB服务地址: http://localhost:4000"
                log_info "PD服务地址: http://localhost:2379"
                log_info "日志文件: $PROJECT_ROOT/logs/tidb.log"
                break
            fi
            
            log_info "等待TiDB启动... ($attempt/$max_attempts)"
            sleep 3
            ((attempt++))
        done
        
        if [ $attempt -gt $max_attempts ]; then
            log_error "TiDB启动超时"
            log_info "请检查日志文件: $PROJECT_ROOT/logs/tidb.log"
            exit 1
        fi
    fi
}

# 显示TiDB状态
show_status() {
    log_info "检查TiDB状态..."
    
    if check_tidb_status; then
        log_success "TiDB Playground正在运行"
        log_info "服务信息:"
        log_info "  TiDB服务: http://localhost:4000"
        log_info "  PD服务: http://localhost:2379"
        
        # 显示进程信息
        if [ -f "$PROJECT_ROOT/tidb.pid" ]; then
            local pid=$(cat "$PROJECT_ROOT/tidb.pid")
            if ps -p $pid > /dev/null 2>&1; then
                log_info "  进程ID: $pid"
            else
                log_warning "  PID文件存在但进程不存在，可能异常退出"
                rm -f "$PROJECT_ROOT/tidb.pid"
            fi
        fi
        
        # 测试数据库连接
        if command -v mysql &> /dev/null; then
            log_info "测试数据库连接..."
            if mysql -h 127.0.0.1 -P 4000 -u root -e "SELECT 'TiDB连接正常' as status;" 2>/dev/null; then
                log_success "数据库连接测试通过"
            else
                log_warning "数据库连接测试失败"
            fi
        fi
    else
        log_warning "TiDB Playground未运行"
        log_info "使用以下命令启动: $0"
    fi
}

# 主函数
main() {
    check_tiup
    
    if [ "$STOP_SERVICE" = true ]; then
        stop_tidb
    else
        start_tidb
        show_status
    fi
}

# 错误处理
trap 'log_error "操作过程中发生错误"; exit 1' ERR

# 执行主函数
main