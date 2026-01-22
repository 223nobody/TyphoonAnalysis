"""
数据库迁移脚本：为 askhistory 表添加 is_ai_generated 字段
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from app.core.database import engine


async def migrate():
    """执行数据库迁移"""
    async with engine.begin() as conn:
        # 检查字段是否已存在（SQLite语法）
        check_sql = """
        PRAGMA table_info(askhistory)
        """
        result = await conn.execute(text(check_sql))
        columns = result.fetchall()

        # 检查是否已存在 is_ai_generated 字段
        column_names = [col[1] for col in columns]
        if 'is_ai_generated' in column_names:
            print("字段 is_ai_generated 已存在，跳过迁移")
            return

        # 添加字段（SQLite语法）
        alter_sql = """
        ALTER TABLE askhistory
        ADD COLUMN is_ai_generated INTEGER NOT NULL DEFAULT 0
        """
        await conn.execute(text(alter_sql))
        print("成功添加字段 is_ai_generated")


if __name__ == "__main__":
    print("开始数据库迁移...")
    asyncio.run(migrate())
    print("数据库迁移完成！")

