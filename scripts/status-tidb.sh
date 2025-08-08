#!/bin/bash

# TiDB Playground状态检查脚本

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

# 检查TiDB服务状态
check_tidb_service() {
    log_info "检查TiDB服务状态..."
    
    # 使用MySQL协议检查TiDB服务
    if command -v mysql &> /dev/null; then
        if mysql -h 127.0.0.1 -P 4000 -u root -e "SELECT 'TiDB服务正在运行' as status;" 2>/dev/null; then
            log_success "TiDB服务正在运行 (端口: 4000)"
            
            # 获取TiDB版本信息
            local version_info=$(mysql -h 127.0.0.1 -P 4000 -u root -e "SELECT VERSION() as version;" -s -N 2>/dev/null || echo "未知")
            log_info "  版本: $version_info"
        else
            log_error "TiDB服务未运行或连接失败 (端口: 4000)"
            return 1
        fi
    else
        # 如果没有mysql客户端，使用端口检查
        if netstat -tlnp 2>/dev/null | grep ":4000 " > /dev/null; then
            log_success "TiDB服务端口已监听 (端口: 4000)"
        else
            log_error "TiDB服务端口未监听 (端口: 4000)"
            return 1
        fi
    fi
    
    # 检查PD服务端口
    if netstat -tlnp 2>/dev/null | grep ":2379 " > /dev/null; then
        log_success "PD服务正在运行 (端口: 2379)"
    else
        log_warning "PD服务未运行 (端口: 2379)"
    fi
}

# 检查进程状态
check_processes() {
    log_info "检查TiDB相关进程..."
    
    local processes_found=false
    
    # 检查tiup playground进程
    if pgrep -f "tiup playground" > /dev/null; then
        local pid=$(pgrep -f "tiup playground")
        log_success "tiup playground进程运行中 (PID: $pid)"
        processes_found=true
    else
        log_warning "tiup playground进程未运行"
    fi
    
    # 检查TiDB组件进程
    for component in tidb-server tikv-server pd-server; do
        if pgrep -f "$component" > /dev/null; then
            local pid=$(pgrep -f "$component")
            log_success "$component进程运行中 (PID: $pid)"
            processes_found=true
        else
            log_warning "$component进程未运行"
        fi
    done
    
    if [ "$processes_found" = false ]; then
        log_error "未找到任何TiDB相关进程"
        return 1
    fi
}

# 检查端口占用
check_ports() {
    log_info "检查端口占用情况..."
    
    local ports=(4000 2379 2380 20160)
    local port_names=("TiDB" "PD-Client" "PD-Peer" "TiKV")
    
    for i in "${!ports[@]}"; do
        local port=${ports[$i]}
        local name=${port_names[$i]}
        
        if netstat -tlnp 2>/dev/null | grep ":$port " > /dev/null; then
            local process=$(netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | head -1)
            log_success "$name端口 $port 已占用 ($process)"
        else
            log_warning "$name端口 $port 未占用"
        fi
    done
}

# 测试数据库连接
test_database_connection() {
    log_info "测试数据库连接..."
    
    # 检查是否安装了mysql客户端
    if ! command -v mysql &> /dev/null; then
        log_warning "mysql客户端未安装，跳过数据库连接测试"
        log_info "安装mysql客户端: sudo apt install mysql-client"
        return
    fi
    
    # 测试基本连接
    if mysql -h 127.0.0.1 -P 4000 -u root -e "SELECT 'TiDB连接正常' as status;" 2>/dev/null; then
        log_success "数据库连接测试通过"
        
        # 获取数据库信息
        local db_version=$(mysql -h 127.0.0.1 -P 4000 -u root -e "SELECT VERSION() as version;" -s -N 2>/dev/null || echo "未知")
        log_info "  数据库版本: $db_version"
        
        # 检查数据库列表
        local databases=$(mysql -h 127.0.0.1 -P 4000 -u root -e "SHOW DATABASES;" -s -N 2>/dev/null | grep -v -E "^(information_schema|mysql|performance_schema|sys)$" | wc -l)
        log_info "  用户数据库数量: $databases"
        
        # 检查llm_inference数据库
        if mysql -h 127.0.0.1 -P 4000 -u root -e "USE llm_inference; SELECT 'llm_inference数据库存在' as status;" 2>/dev/null; then
            log_success "llm_inference数据库存在"
        else
            log_warning "llm_inference数据库不存在"
        fi
    else
        log_error "数据库连接测试失败"
        return 1
    fi
}

# 检查资源使用情况
check_resource_usage() {
    log_info "检查资源使用情况..."
    
    # 检查内存使用
    local total_mem=$(free -m | awk 'NR==2{printf "%.1f", $2/1024}')
    local used_mem=$(free -m | awk 'NR==2{printf "%.1f", $3/1024}')
    local mem_percent=$(free | awk 'NR==2{printf "%.1f", $3*100/$2}')
    log_info "  内存使用: ${used_mem}GB / ${total_mem}GB (${mem_percent}%)"
    
    # 检查磁盘使用
    local disk_usage=$(df -h . | awk 'NR==2{print $5}' | sed 's/%//')
    log_info "  磁盘使用: ${disk_usage}%"
    
    # 检查TiDB进程的资源使用
    if pgrep -f "tidb-server" > /dev/null; then
        local tidb_pid=$(pgrep -f "tidb-server")
        local cpu_usage=$(ps -p $tidb_pid -o %cpu --no-headers 2>/dev/null || echo "0")
        local mem_usage=$(ps -p $tidb_pid -o %mem --no-headers 2>/dev/null || echo "0")
        log_info "  TiDB进程资源: CPU ${cpu_usage}%, 内存 ${mem_usage}%"
    fi
}

# 显示日志信息
show_log_info() {
    log_info "日志文件信息..."
    
    local log_files=("$PROJECT_ROOT/logs/tidb.log" "$PROJECT_ROOT/tidb.log")
    
    for log_file in "${log_files[@]}"; do
        if [ -f "$log_file" ]; then
            local file_size=$(du -h "$log_file" | cut -f1)
            local last_modified=$(stat -c %y "$log_file" | cut -d'.' -f1)
            log_info "  日志文件: $log_file"
            log_info "    大小: $file_size"
            log_info "    最后修改: $last_modified"
            
            # 显示最后几行日志
            log_info "    最近日志:"
            tail -3 "$log_file" 2>/dev/null | sed 's/^/      /' || log_warning "    无法读取日志内容"
            break
        fi
    done
    
    if [ ! -f "$PROJECT_ROOT/logs/tidb.log" ] && [ ! -f "$PROJECT_ROOT/tidb.log" ]; then
        log_warning "未找到TiDB日志文件"
    fi
}

# 显示管理命令
show_management_commands() {
    log_info "TiDB管理命令:"
    log_info "  启动服务: ./scripts/start-tidb.sh"
    log_info "  停止服务: ./scripts/stop-tidb.sh"
    log_info "  查看状态: ./scripts/status-tidb.sh"
    log_info "  查看日志: tail -f logs/tidb.log"
    log_info "  连接数据库: mysql -h 127.0.0.1 -P 4000 -u root"
}

# 主函数
main() {
    echo "========================================"
    echo "         TiDB Playground 状态检查"
    echo "========================================"
    echo
    
    local overall_status=0
    
    # 执行各项检查
    check_tidb_service || overall_status=1
    echo
    
    check_processes || overall_status=1
    echo
    
    check_ports
    echo
    
    test_database_connection || overall_status=1
    echo
    
    check_resource_usage
    echo
    
    show_log_info
    echo
    
    show_management_commands
    echo
    
    # 显示总体状态
    if [ $overall_status -eq 0 ]; then
        log_success "TiDB Playground运行正常"
    else
        log_warning "TiDB Playground存在问题，请检查上述输出"
    fi
    
    echo "========================================"
}

# 执行主函数
main