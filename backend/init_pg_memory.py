import asyncio
import sys
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from settings.config import settings

PG_URI = settings.pg_url


async def setup_memory_db():
    print("正在连接 PostgreSQL...")
    async with AsyncPostgresSaver.from_conn_string(PG_URI) as saver:
        await saver.setup()
        print("✅ PostgreSQL 记忆持久化数据表创建成功！")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(setup_memory_db())
