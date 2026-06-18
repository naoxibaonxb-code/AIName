# core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData

from settings.config import settings

# ================== 1. 数据库 (SQLAlchemy) ==================
# 1. 数据库引擎配置
engine = create_async_engine(
    settings.db_url,
    echo=True,
    pool_size=10,
    max_overflow=20,
    pool_timeout=10,
    pool_recycle=3600,
    pool_pre_ping=True,
)

# 2. 会话工厂
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    autoflush=True,
    expire_on_commit=False
)


# 3. 声明性基类 (所有模型都要继承这个)
class Base(DeclarativeBase):
    metadata = MetaData(naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    })
