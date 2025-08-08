#!/bin/bash

# TiUP安装脚本

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

# 检查系统要求
check_system_requirements() {
    log_info "检查系统要求..."
    
    # 检查操作系统
    if [[ "$OSTYPE" != "linux-gnu"* ]]; then
        log_error "此脚本仅支持Linux系统"
        exit 1
    fi
    
    # 检查架构
    local arch=$(uname -m)
    if [[ "$arch" != "x86_64" ]] && [[ "$arch" != "aarch64" ]]; then
        log_warning "TiUP可能不支持当前架构: $arch"
    fi
    
    # 检查必要工具
    for cmd in curl tar; do
        if ! command -v $cmd &> /dev/null; then
            log_error "$cmd 未安装，请先安装: sudo apt install $cmd"
            exit 1
        fi
    done
    
    log_success "系统要求检查通过"
}

# 安装TiUP
install_tiup() {
    log_info "开始安装TiUP..."
    
    # 检查是否已安装
    if command -v tiup &> /dev/null; then
        local version=$(tiup --version | head -1 | awk '{print $3}')
        log_warning "TiUP已安装 (版本: $version)"
        log_info "如需重新安装，请先运行: rm -rf ~/.tiup"
        return
    fi
    
    # 下载并安装TiUP
    log_info "下载TiUP安装脚本..."
    curl --proto '=https' --tlsv1.2 -sSf https://tiup-mirrors.pingcap.com/install.sh | sh
    
    # 重新加载环境变量
    if [ -f "$HOME/.bashrc" ]; then
        source "$HOME/.bashrc"
    fi
    
    # 添加到PATH（如果需要）
    if ! echo "$PATH" | grep -q "$HOME/.tiup/bin"; then
        log_info "添加TiUP到PATH..."
        echo 'export PATH=$HOME/.tiup/bin:$PATH' >> "$HOME/.bashrc"
        export PATH="$HOME/.tiup/bin:$PATH"
    fi
    
    # 验证安装
    if command -v tiup &> /dev/null; then
        local version=$(tiup --version | head -1 | awk '{print $3}')
        log_success "TiUP安装成功 (版本: $version)"
    else
        log_error "TiUP安装失败"
        exit 1
    fi
}

# 安装TiDB组件
install_tidb_components() {
    log_info "安装TiDB组件..."
    
    # 安装playground组件
    log_info "安装playground组件..."
    tiup install playground
    
    # 安装最新版本的TiDB组件
    log_info "安装TiDB核心组件..."
    tiup install tidb tikv pd
    
    # 列出已安装的组件
    log_info "已安装的组件:"
    tiup list --installed
    
    log_success "TiDB组件安装完成"
}

# 配置TiUP
configure_tiup() {
    log_info "配置TiUP..."
    
    # 设置镜像源（可选）
    # tiup mirror set https://tiup-mirrors.pingcap.com
    
    # 创建配置目录
    mkdir -p "$HOME/.tiup"
    
    log_success "TiUP配置完成"
}

# 测试安装
test_installation() {
    log_info "测试TiUP安装..."
    
    # 检查TiUP版本
    local tiup_version=$(tiup --version | head -1 | awk '{print $3}')
    log_info "TiUP版本: $tiup_version"
    
    # 检查可用组件
    log_info "可用组件:"
    tiup list | head -10
    
    # 测试playground（快速测试）
    log_info "测试playground组件..."
    timeout 10s tiup playground --help > /dev/null 2>&1 || true
    
    log_success "TiUP安装测试完成"
}

# 显示使用说明
show_usage_instructions() {
    log_success "TiUP安装完成！"
    echo
    log_info "使用说明:"
    log_info "1. 启动TiDB Playground:"
    log_info "   ./scripts/start-tidb.sh"
    log_info "   或者: tiup playground --db 1 --pd 1 --kv 1 --tiflash 0 --host 0.0.0.0"
    echo
    log_info "2. 连接TiDB数据库:"
    log_info "   mysql -h 127.0.0.1 -P 4000 -u root"
    echo
    log_info "3. 查看TiDB状态:"
    log_info "   ./scripts/status-tidb.sh"
    echo
    log_info "4. 停止TiDB Playground:"
    log_info "   ./scripts/stop-tidb.sh"
    echo
    log_info "更多信息请参考: https://docs.pingcap.com/tidb/stable/tiup-overview"
}

# 主函数
main() {
    log_info "开始安装TiUP..."
    
    check_system_requirements
    install_tiup
    install_tidb_components
    configure_tiup
    test_installation
    show_usage_instructions
}

# 错误处理
trap 'log_error "安装过程中发生错误"; exit 1' ERR

# 执行主函数
main