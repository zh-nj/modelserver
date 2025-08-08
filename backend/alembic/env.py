"""
Alembic环境配置
用于数据库迁移管理
"""
import logging
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection
from alembic import context

# 导入模型以确保元数据可用
from app.models.database import Base
from app.core.config import settings

# Alembic配置对象
config = context.config

# 设置数据库URL
config.set_main_option("sqlalchemy.url", settings.database_url)

# 解释日志配置文件
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 目标元数据
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """在'离线'模式下运行迁移。
    
    这将配置上下文，只使用URL而不是Engine，
    尽管这里也需要一个Engine，但我们不创建连接。
    通过跳过Engine创建，我们甚至不需要DBAPI可用。
    
    调用context.execute()将发出给定的字符串到脚本输出。
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    """运行迁移的核心函数"""
    context.configure(
        connection=connection, 
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """在'在线'模式下运行迁移（同步模式）"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()