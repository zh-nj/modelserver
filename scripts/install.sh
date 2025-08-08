#!/bin/bash

# LLM推理服务安装脚本
# 用法: ./scripts/install.sh

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

# 检查系统
check_system() {
    log_info "检查系统环境..."
    
    # 检查操作系统
    if [[ "$OSTYPE" != "linux-gnu"* ]]; then
        log_error "此脚本仅支持Linux系统"
        exit 1
    fi
    
    # 检查是否为root用户
    if [ "$EUID" -eq 0 ]; then
        log_warning "建议不要使用root用户运行此脚本"
    fi
    
    log_success "系统检查通过"
}

# 安装Docker
install_docker() {
    if command -v docker &> /dev/null; then
        log_info "Docker已安装，版本: $(docker --version)"
        return
    fi
    
    log_info "安装Docker..."
    
    # 更新包索引
    sudo apt-get update
    
    # 安装必要的包
    sudo apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release
    
    # 添加Docker官方GPG密钥
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # 设置稳定版仓库
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # 安装Docker Engine
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io
    
    # 启动Docker服务
    sudo systemctl start docker
    sudo systemctl enable docker
    
    # 将当前用户添加到docker组
    sudo usermod -aG docker $USER
    
    log_success "Docker安装完成"
    log_warning "请重新登录以使docker组权限生效"
}

# 安装Docker Compose
install_docker_compose() {
    if command -v docker-compose &> /dev/null; then
        log_info "Docker Compose已安装，版本: $(docker-compose --version)"
        return
    fi
    
    log_info "安装Docker Compose..."
    
    # 下载Docker Compose
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    
    # 设置执行权限
    sudo chmod +x /usr/local/bin/docker-compose
    
    # 创建符号链接
    sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    
    log_success "Docker Compose安装完成"
}

# 安装Python和依赖
install_python_deps() {
    log_info "安装Python依赖..."
    
    # 安装Python 3.11
    sudo apt-get update
    sudo apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip
    
    # 创建虚拟环境
    if [ ! -d "venv" ]; then
        python3.11 -m venv venv
    fi
    
    # 激活虚拟环境并安装依赖
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r backend/requirements.txt
    
    log_success "Python依赖安装完成"
}

# 安装Node.js和前端依赖
install_nodejs_deps() {
    log_info "安装Node.js依赖..."
    
    # 安装Node.js 18
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
    
    # 安装前端依赖
    cd frontend
    npm install
    cd ..
    
    log_success "Node.js依赖安装完成"
}

# 创建服务用户
create_service_user() {
    log_info "创建服务用户..."
    
    if ! id "llm-service" &>/dev/null; then
        sudo useradd -r -s /bin/false -d /opt/llm-inference-service llm-service
        log_success "服务用户创建完成"
    else
        log_info "服务用户已存在"
    fi
}

# 设置目录和权限
setup_directories() {
    log_info "设置目录和权限..."
    
    # 创建应用目录
    sudo mkdir -p /opt/llm-inference-service
    sudo cp -r . /opt/llm-inference-service/
    
    # 创建数据目录
    sudo mkdir -p /var/lib/llm-inference-service
    sudo mkdir -p /var/log/llm-inference-service
    
    # 设置权限
    sudo chown -R llm-service:llm-service /opt/llm-inference-service
    sudo chown -R llm-service:llm-service /var/lib/llm-inference-service
    sudo chown -R llm-service:llm-service /var/log/llm-inference-service
    
    # 创建符号链接
    sudo ln -sf /var/log/llm-inference-service /opt/llm-inference-service/backend/logs
    sudo ln -sf /var/lib/llm-inference-service /opt/llm-inference-service/backend/data
    
    log_success "目录和权限设置完成"
}

# 安装系统服务
install_system_service() {
    log_info "安装系统服务..."
    
    # 复制服务文件
    sudo cp configs/systemd/llm-inference-service.service /etc/systemd/system/
    sudo cp configs/systemd/llm-inference-backend.service /etc/systemd/system/
    
    # 创建环境文件目录
    sudo mkdir -p /etc/llm-inference
    
    # 复制环境文件
    if [ -f ".env" ]; then
        sudo cp .env /etc/llm-inference/backend.env
    else
        sudo cp configs/.env.template /etc/llm-inference/backend.env
        log_warning "请编辑 /etc/llm-inference/backend.env 配置环境变量"
    fi
    
    # 重新加载systemd
    sudo systemctl daemon-reload
    
    # 启用服务
    sudo systemctl enable llm-inference-service
    
    log_success "系统服务安装完成"
}

# 安装GPU支持（可选）
install_gpu_support() {
    log_info "检查GPU支持..."
    
    if command -v nvidia-smi &> /dev/null; then
        log_info "检测到NVIDIA GPU，安装NVIDIA Docker支持..."
        
        # 安装NVIDIA Docker
        distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
        curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
        curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
        
        sudo apt-get update
        sudo apt-get install -y nvidia-docker2
        
        # 重启Docker服务
        sudo systemctl restart docker
        
        log_success "NVIDIA Docker支持安装完成"
    else
        log_info "未检测到NVIDIA GPU，跳过GPU支持安装"
    fi
}

# 显示安装信息
show_installation_info() {
    log_success "安装完成！"
    echo
    log_info "下一步操作:"
    log_info "1. 编辑配置文件: sudo nano /etc/llm-inference/backend.env"
    log_info "2. 启动服务: sudo systemctl start llm-inference-service"
    log_info "3. 查看服务状态: sudo systemctl status llm-inference-service"
    log_info "4. 查看日志: sudo journalctl -u llm-inference-service -f"
    echo
    log_info "或者使用Docker Compose直接运行:"
    log_info "1. cd /opt/llm-inference-service"
    log_info "2. sudo -u llm-service docker-compose up -d"
    echo
    log_info "服务访问地址:"
    log_info "  前端界面: http://localhost:3000"
    log_info "  后端API: http://localhost:8000"
    log_info "  API文档: http://localhost:8000/docs"
}

# 主函数
main() {
    log_info "开始安装LLM推理服务..."
    
    check_system
    install_docker
    install_docker_compose
    install_python_deps
    install_nodejs_deps
    create_service_user
    setup_directories
    install_system_service
    install_gpu_support
    show_installation_info
}

# 错误处理
trap 'log_error "安装过程中发生错误，请检查日志"; exit 1' ERR

# 执行主函数
main