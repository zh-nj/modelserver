#!/usr/bin/env python3
"""
测试数据库连接脚本
"""
import sys
import os

# 添加backend目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_database_connection():
    """测试数据库连接"""
    try:
        print("正在测试数据库连接...")
        
        # 导入配置
        from app.core.config import settings
        print(f"数据库URL: {settings.database_url}")
        
        # 导入数据库引擎
        from app.core.database import sync_engine
        from sqlalchemy import text
        print("数据库引擎导入成功")
        
        # 测试连接
        with sync_engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            print(f"数据库连接测试成功: {row[0]}")
            
            # 测试数据库版本
            result = conn.execute(text("SELECT VERSION() as version"))
            version = result.fetchone()
            print(f"数据库版本: {version[0]}")
            
        print("✅ 数据库连接测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 数据库连接测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_database_connection()
    sys.exit(0 if success else 1)