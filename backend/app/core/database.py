"""
数据库连接和会话管理
"""
import logging
from typing import AsyncGenerator
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from .config import settings
from ..models.database import Base

logger = logging.getLogger(__name__)

# 同步数据库引擎（用于Alembic迁移）
sync_engine = create_engine(
    settings.database_url,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.debug
)

# 异步数据库引擎（用于应用程序）
async_database_url = settings.database_url.replace("mysql+pymysql://", "mysql+aiomysql://")
async_engine = create_async_engine(
    async_database_url,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.debug
)

# 会话工厂
SessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

def get_sync_db() -> Session:
    """获取同步数据库会话"""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """获取异步数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"数据库会话异常: {e}")
            raise
        finally:
            await session.close()

async def init_database():
    """初始化数据库"""
    try:
        logger.info("初始化数据库连接...")
        
        # 测试数据库连接
        async with async_engine.begin() as conn:
            # 创建所有表（如果不存在）
            await conn.run_sync(Base.metadata.create_all)
            logger.info("数据库表创建完成")
        
        logger.info("数据库初始化完成")
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise

async def close_database():
    """关闭数据库连接"""
    try:
        logger.info("关闭数据库连接...")
        await async_engine.dispose()
        sync_engine.dispose()
        logger.info("数据库连接关闭完成")
    except Exception as e:
        logger.error(f"关闭数据库连接失败: {e}")

# 数据库事件监听器
@event.listens_for(sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """设置数据库连接参数"""
    if "mysql" in settings.database_url:
        # MySQL特定设置
        cursor = dbapi_connection.cursor()
        cursor.execute("SET SESSION sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO'")
        cursor.execute("SET SESSION time_zone = '+00:00'")
        cursor.close()

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.sync_engine = sync_engine
        self.async_engine = async_engine
        self.SessionLocal = SessionLocal
        self.AsyncSessionLocal = AsyncSessionLocal
    
    async def health_check(self) -> bool:
        """数据库健康检查"""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute("SELECT 1")
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"数据库健康检查失败: {e}")
            return False
    
    async def get_connection_info(self) -> dict:
        """获取数据库连接信息"""
        try:
            async with AsyncSessionLocal() as session:
                # 获取数据库版本
                result = await session.execute("SELECT VERSION()")
                version = result.scalar()
                
                # 获取连接池信息
                pool = self.async_engine.pool
                
                return {
                    "database_url": settings.database_url.split("@")[1] if "@" in settings.database_url else settings.database_url,
                    "database_version": version,
                    "pool_size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "invalid": pool.invalid()
                }
        except Exception as e:
            logger.error(f"获取数据库连接信息失败: {e}")
            return {}
    
    def create_tables(self):
        """创建所有数据库表"""
        try:
            Base.metadata.create_all(bind=self.sync_engine)
            logger.info("数据库表创建成功")
        except Exception as e:
            logger.error(f"创建数据库表失败: {e}")
            raise
    
    def drop_tables(self):
        """删除所有数据库表"""
        try:
            Base.metadata.drop_all(bind=self.sync_engine)
            logger.info("数据库表删除成功")
        except Exception as e:
            logger.error(f"删除数据库表失败: {e}")
            raise

# 全局数据库管理器实例
db_manager = DatabaseManager()

def get_db() -> Session:
    """获取数据库会话（用于依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()