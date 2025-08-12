#!/bin/bash

# 停止服务脚本
# 用法: ./stop.sh

echo "🛑 停止LLM推理服务..."

# 停止后端和前端服务
echo "🔧 停止后端和前端服务..."
./scripts/start-services.sh --stop

# 停止TiDB（可选）
read -p "是否同时停止TiDB数据库? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📊 停止TiDB数据库..."
    ./scripts/start-tidb.sh --stop
fi

echo "✅ 服务停止完成！"