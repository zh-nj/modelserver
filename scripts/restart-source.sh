#!/bin/bash

# LLM推理服务源码部署重启脚本

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

# 解析命令行参数
ENVIRONMENT=${1:-production}
DAEMON_MODE=true

for arg in "$@"; do
    case $arg in
        --foreground)
            DAEMON_MODE=false
            shift
            ;;
    esac
done

# 主函数
main() {
    log_info "重启LLM推理服务..."
    log_info "环境: $ENVIRONMENT"
    
    cd "$PROJECT_ROOT"
    
    # 停止现有服务
    log_info "停止现有服务..."
    ./scripts/stop-source.sh
    
    # 等待进程完全停止
    sleep 3
    
    # 重新启动服务
    log_info "重新启动服务..."
    if [ "$DAEMON_MODE" = true ]; then
        ./scripts/deploy-source.sh $ENVIRONMENT --daemon --skip-deps
    else
        ./scripts/deploy-source.sh $ENVIRONMENT --skip-deps
    fi
    
    log_success "服务重启完成！"
}

# 执行主函数
main