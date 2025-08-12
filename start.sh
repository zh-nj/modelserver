#!/bin/bash

# 快速启动脚本 - 后台运行后端和前端服务
# 用法: ./start.sh

echo "🚀 启动LLM推理服务..."

# 检查并启动TiDB
if ! netstat -tlnp 2>/dev/null | grep ":4000 " > /dev/null; then
    echo "📊 启动TiDB数据库..."
    ./scripts/start-tidb.sh
fi

# 启动后端和前端服务
echo "🔧 启动后端和前端服务..."
./scripts/start-services.sh

echo "✅ 服务启动完成！"
echo ""
echo "🌐 访问地址:"
echo "   前端界面: http://localhost:3000"
echo "   后端API:  http://localhost:8000"
echo "   API文档:  http://localhost:8000/docs"
echo ""
echo "📋 管理命令:"
echo "   查看状态: ./scripts/start-services.sh --status"
echo "   查看日志: ./scripts/start-services.sh --logs"
echo "   停止服务: ./scripts/start-services.sh --stop"