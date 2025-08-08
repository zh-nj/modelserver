#!/bin/bash

# LLM推理服务备份脚本
# 用法: ./scripts/backup.sh [备份目录]

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

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 配置
BACKUP_DIR=${1:-./backups}
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="llm-inference-backup-$TIMESTAMP"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

# 创建备份目录
create_backup_dir() {
    log_info "创建备份目录: $BACKUP_PATH"
    mkdir -p "$BACKUP_PATH"
}

# 备份数据库
backup_database() {
    log_info "备份数据库..."
    
    # 备份TiDB数据
    docker-compose exec -T tidb mysqldump -u root --all-databases > "$BACKUP_PATH/database.sql" || {
        log_error "数据库备份失败"
        return 1
    }
    
    log_success "数据库备份完成"
}

# 备份配置文件
backup_configs() {
    log_info "备份配置文件..."
    
    cp -r configs "$BACKUP_PATH/"
    cp .env "$BACKUP_PATH/" 2>/dev/null || log_info ".env文件不存在，跳过"
    cp docker-compose.yml "$BACKUP_PATH/"
    
    log_success "配置文件备份完成"
}

# 备份应用数据
backup_data() {
    log_info "备份应用数据..."
    
    # 备份日志
    if [ -d "backend/logs" ]; then
        cp -r backend/logs "$BACKUP_PATH/"
    fi
    
    # 备份指标数据
    if [ -d "backend/data" ]; then
        cp -r backend/data "$BACKUP_PATH/"
    fi
    
    # 备份模型文件（如果存在）
    if [ -d "models" ]; then
        cp -r models "$BACKUP_PATH/"
    fi
    
    log_success "应用数据备份完成"
}

# 创建备份压缩包
create_archive() {
    log_info "创建备份压缩包..."
    
    cd "$BACKUP_DIR"
    tar -czf "$BACKUP_NAME.tar.gz" "$BACKUP_NAME"
    rm -rf "$BACKUP_NAME"
    
    log_success "备份压缩包创建完成: $BACKUP_DIR/$BACKUP_NAME.tar.gz"
}

# 清理旧备份
cleanup_old_backups() {
    log_info "清理旧备份（保留最近7个）..."
    
    cd "$BACKUP_DIR"
    ls -t llm-inference-backup-*.tar.gz | tail -n +8 | xargs -r rm -f
    
    log_success "旧备份清理完成"
}

# 主函数
main() {
    log_info "开始备份LLM推理服务..."
    
    create_backup_dir
    backup_database
    backup_configs
    backup_data
    create_archive
    cleanup_old_backups
    
    log_success "备份完成！"
    log_info "备份文件: $BACKUP_DIR/$BACKUP_NAME.tar.gz"
}

# 错误处理
trap 'log_error "备份过程中发生错误"; exit 1' ERR

# 执行主函数
main