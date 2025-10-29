#!/bin/bash

# Hypeliquid聪明钱监控机器人部署脚本
# 支持Docker部署和本地部署两种方式

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认配置
DEPLOY_MODE="docker"
ENV_FILE=".env"
COMPOSE_FILE="docker-compose.yml"
BACKUP_DIR="backups"
LOG_DIR="logs"
DATA_DIR="data"

# 函数：输出带颜色的信息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 函数：检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 函数：检查Docker环境
check_docker() {
    if ! command_exists docker; then
        print_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    if ! command_exists docker-compose; then
        print_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    # 检查Docker服务是否运行
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker服务未运行，请先启动Docker服务"
        exit 1
    fi
    
    print_success "Docker环境检查通过"
}

# 函数：检查Python环境
check_python() {
    if ! command_exists python3; then
        print_error "Python3未安装，请先安装Python3"
        exit 1
    fi
    
    if ! command_exists pip3; then
        print_error "pip3未安装，请先安装pip3"
        exit 1
    fi
    
    print_success "Python环境检查通过"
}

# 函数：创建必要的目录
create_directories() {
    print_info "创建必要的目录..."
    
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$DATA_DIR"
    mkdir -p "monitoring"
    mkdir -p "scripts"
    
    print_success "目录创建完成"
}

# 函数：备份现有数据
backup_data() {
    if [ -d "$DATA_DIR" ] && [ "$(ls -A $DATA_DIR)" ]; then
        print_info "备份现有数据..."
        
        BACKUP_NAME="backup_$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR/$BACKUP_NAME"
        
        # 备份数据库和配置文件
        cp -r "$DATA_DIR" "$BACKUP_DIR/$BACKUP_NAME/" 2>/dev/null || true
        cp "$ENV_FILE" "$BACKUP_DIR/$BACKUP_NAME/" 2>/dev/null || true
        
        print_success "数据备份完成: $BACKUP_DIR/$BACKUP_NAME"
    fi
}

# 函数：检查环境变量
check_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        print_warning "环境文件 $ENV_FILE 不存在，创建示例文件..."
        cp .env.example "$ENV_FILE"
        print_warning "请编辑 $ENV_FILE 文件，设置必要的配置项"
        print_warning "特别是 TELEGRAM_BOT_TOKEN 必须设置"
        exit 1
    fi
    
    # 检查必需的配置项
    if ! grep -q "TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here" "$ENV_FILE"; then
        print_success "环境文件检查通过"
    else
        print_error "请编辑 $ENV_FILE 文件，设置 TELEGRAM_BOT_TOKEN"
        exit 1
    fi
}

# 函数：Docker部署
deploy_docker() {
    print_info "使用Docker部署..."
    
    # 检查Docker环境
    check_docker
    
    # 检查环境文件
    check_env_file
    
    # 备份数据
    backup_data
    
    # 构建镜像
    print_info "构建Docker镜像..."
    docker-compose build
    
    # 停止现有容器
    print_info "停止现有容器..."
    docker-compose down --remove-orphans 2>/dev/null || true
    
    # 启动服务
    print_info "启动Docker服务..."
    docker-compose up -d
    
    # 等待服务启动
    print_info "等待服务启动..."
    sleep 10
    
    # 检查服务状态
    if docker-compose ps | grep -q "Up"; then
        print_success "Docker服务启动成功"
        
        # 显示服务状态
        print_info "服务状态:"
        docker-compose ps
        
        # 显示日志
        print_info "最近日志:"
        docker-compose logs --tail=20
    else
        print_error "Docker服务启动失败"
        print_info "查看详细日志:"
        docker-compose logs
        exit 1
    fi
}

# 函数：本地部署
deploy_local() {
    print_info "使用本地Python环境部署..."
    
    # 检查Python环境
    check_python
    
    # 检查环境文件
    check_env_file
    
    # 备份数据
    backup_data
    
    # 创建虚拟环境
    print_info "创建Python虚拟环境..."
    python3 -m venv venv
    source venv/bin/activate
    
    # 安装依赖
    print_info "安装Python依赖..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # 创建systemd服务（可选）
    if command_exists systemctl; then
        create_systemd_service
    fi
    
    print_success "本地部署完成"
    print_info "启动机器人: python main.py"
}

# 函数：创建systemd服务
create_systemd_service() {
    print_info "创建systemd服务..."
    
    SERVICE_FILE="/etc/systemd/system/hypeliquid-bot.service"
    
    sudo tee "$SERVICE_FILE" <<EOF
[Unit]
Description=Hypeliquid Smart Money Monitor Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python $(pwd)/main.py
Restart=always
RestartSec=10

# 日志配置
StandardOutput=append:$(pwd)/logs/systemd.log
StandardError=append:$(pwd)/logs/systemd.log

# 资源限制
MemoryLimit=512M
CPUQuota=50%

[Install]
WantedBy=multi-user.target
EOF

    # 重新加载systemd
    sudo systemctl daemon-reload
    
    # 启用服务
    sudo systemctl enable hypeliquid-bot.service
    
    print_success "systemd服务创建完成"
    print_info "管理服务命令:"
    print_info "  启动: sudo systemctl start hypeliquid-bot"
    print_info "  停止: sudo systemctl stop hypeliquid-bot"
    print_info "  状态: sudo systemctl status hypeliquid-bot"
    print_info "  日志: sudo journalctl -u hypeliquid-bot -f"
}

# 函数：显示状态
show_status() {
    print_info "显示服务状态..."
    
    if [ "$DEPLOY_MODE" = "docker" ]; then
        if docker-compose ps | grep -q "Up"; then
            print_success "Docker服务运行中"
            docker-compose ps
        else
            print_error "Docker服务未运行"
        fi
    else
        if command_exists systemctl && systemctl is-active --quiet hypeliquid-bot; then
            print_success "本地服务运行中"
            systemctl status hypeliquid-bot
        else
            print_error "本地服务未运行"
        fi
    fi
}

# 函数：查看日志
show_logs() {
    print_info "显示日志..."
    
    if [ "$DEPLOY_MODE" = "docker" ]; then
        docker-compose logs -f --tail=100
    else
        if [ -f "logs/bot.log" ]; then
            tail -f logs/bot.log
        else
            print_error "日志文件不存在"
        fi
    fi
}

# 函数：停止服务
stop_service() {
    print_info "停止服务..."
    
    if [ "$DEPLOY_MODE" = "docker" ]; then
        docker-compose down --remove-orphans
        print_success "Docker服务已停止"
    else
        if command_exists systemctl; then
            sudo systemctl stop hypeliquid-bot
            print_success "本地服务已停止"
        else
            print_warning "请手动停止Python进程"
        fi
    fi
}

# 函数：重启服务
restart_service() {
    print_info "重启服务..."
    
    if [ "$DEPLOY_MODE" = "docker" ]; then
        docker-compose restart
        print_success "Docker服务已重启"
    else
        if command_exists systemctl; then
            sudo systemctl restart hypeliquid-bot
            print_success "本地服务已重启"
        else
            print_warning "请手动重启Python进程"
        fi
    fi
}

# 函数：更新代码
update_code() {
    print_info "更新代码..."
    
    # 备份当前代码
    if [ -d ".git" ]; then
        git stash
        git pull origin main
        git stash pop
    else
        print_warning "不是Git仓库，请手动更新代码"
    fi
    
    if [ "$DEPLOY_MODE" = "docker" ]; then
        print_info "重新构建Docker镜像..."
        docker-compose build
        restart_service
    else
        print_info "重新安装Python依赖..."
        source venv/bin/activate
        pip install -r requirements.txt
        restart_service
    fi
    
    print_success "代码更新完成"
}

# 函数：清理数据
cleanup_data() {
    print_warning "这将清理所有监控数据，是否继续？(y/N)"
    read -r response
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        print_info "清理数据..."
        
        # 停止服务
        stop_service
        
        # 清理数据目录
        rm -rf "$DATA_DIR"/*
        rm -rf "$LOG_DIR"/*
        
        print_success "数据清理完成"
        
        # 重新启动服务
        if [ "$DEPLOY_MODE" = "docker" ]; then
            deploy_docker
        else
            print_info "请手动启动服务"
        fi
    else
        print_info "取消清理操作"
    fi
}

# 函数：显示帮助信息
show_help() {
    echo "Hypeliquid聪明钱监控机器人部署脚本"
    echo
    echo "用法: $0 [选项] [命令]"
    echo
    echo "部署模式:"
    echo "  --docker    使用Docker部署（默认）"
    echo "  --local     使用本地Python环境部署"
    echo
    echo "命令:"
    echo "  deploy      部署服务"
    echo "  status      显示服务状态"
    echo "  logs        查看日志"
    echo "  stop        停止服务"
    echo "  restart     重启服务"
    echo "  update      更新代码并重启"
    echo "  cleanup     清理所有数据"
    echo "  help        显示帮助信息"
    echo
    echo "示例:"
    echo "  $0 --docker deploy     # 使用Docker部署"
    echo "  $0 --local deploy      # 使用本地环境部署"
    echo "  $0 status              # 查看服务状态"
    echo "  $0 logs                # 查看日志"
}

# 主函数
main() {
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --docker)
                DEPLOY_MODE="docker"
                shift
                ;;
            --local)
                DEPLOY_MODE="local"
                shift
                ;;
            deploy|status|logs|stop|restart|update|cleanup|help)
                COMMAND=$1
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                print_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 默认命令
    if [ -z "$COMMAND" ]; then
        COMMAND="deploy"
    fi
    
    # 创建必要目录
    create_directories
    
    # 执行命令
    case $COMMAND in
        deploy)
            if [ "$DEPLOY_MODE" = "docker" ]; then
                deploy_docker
            else
                deploy_local
            fi
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        stop)
            stop_service
            ;;
        restart)
            restart_service
            ;;
        update)
            update_code
            ;;
        cleanup)
            cleanup_data
            ;;
        help)
            show_help
            ;;
        *)
            print_error "未知命令: $COMMAND"
            show_help
            exit 1
            ;;
    esac
}

# 脚本入口
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi