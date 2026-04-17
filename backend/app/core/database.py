"""
数据库连接和会话管理
"""
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # 禁用SQL日志输出
    future=True,
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 创建基类
Base = declarative_base()


async def get_db():
    """
    获取数据库会话的依赖注入函数

    Yields:
        AsyncSession: 数据库会话
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """初始化数据库，创建所有表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _run_schema_migrations(conn)


async def close_db():
    """关闭数据库连接"""
    await engine.dispose()


async def _run_schema_migrations(conn):
    """执行轻量级 SQLite 结构迁移"""
    await _migrate_typhoon_images(conn)
    await _migrate_image_analysis_results(conn)


async def _migrate_typhoon_images(conn):
    table_exists = await conn.execute(
        text(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='typhoon_images'"
        )
    )
    if table_exists.first() is None:
        return

    analysis_table_exists = await conn.execute(
        text(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='image_analysis_results'"
        )
    )
    has_analysis_table = analysis_table_exists.first() is not None

    duplicate_rows = await conn.execute(
        text(
            "SELECT filename FROM typhoon_images "
            "GROUP BY filename HAVING COUNT(*) > 1"
        )
    )
    project_root = Path(__file__).resolve().parents[3]

    for (filename,) in duplicate_rows.fetchall():
        image_rows = await conn.execute(
            text(
                "SELECT id, file_path FROM typhoon_images "
                "WHERE filename = :filename ORDER BY id ASC"
            ),
            {"filename": filename},
        )
        records = image_rows.fetchall()
        if len(records) <= 1:
            continue

        for duplicate_id, duplicate_path in records[1:]:
            if has_analysis_table:
                await conn.execute(
                    text("DELETE FROM image_analysis_results WHERE image_id = :image_id"),
                    {"image_id": duplicate_id},
                )
            await conn.execute(
                text("DELETE FROM typhoon_images WHERE id = :image_id"),
                {"image_id": duplicate_id},
            )

            if duplicate_path:
                try:
                    resolved_path = Path(duplicate_path).resolve()
                except OSError:
                    resolved_path = None

                if (
                    resolved_path
                    and resolved_path.exists()
                    and project_root in resolved_path.parents
                ):
                    resolved_path.unlink()

    index_rows = await conn.execute(text("PRAGMA index_list(typhoon_images)"))
    unique_filename_index_exists = False
    for index_row in index_rows.fetchall():
        index_name = index_row[1]
        is_unique = bool(index_row[2])
        if not is_unique:
            continue

        index_info = await conn.execute(text(f"PRAGMA index_info('{index_name}')"))
        indexed_columns = [row[2] for row in index_info.fetchall()]
        if indexed_columns == ["filename"]:
            unique_filename_index_exists = True
            break

    if not unique_filename_index_exists:
        await conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS "
                "uq_typhoon_images_filename ON typhoon_images(filename)"
            )
        )


async def _migrate_image_analysis_results(conn):
    table_exists = await conn.execute(
        text(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='image_analysis_results'"
        )
    )
    if table_exists.first() is None:
        return

    column_rows = await conn.execute(text("PRAGMA table_info(image_analysis_results)"))
    columns = {row[1] for row in column_rows.fetchall()}

    alter_statements = {
        "status": (
            "ALTER TABLE image_analysis_results "
            "ADD COLUMN status VARCHAR(20) DEFAULT 'pending'"
        ),
        "method": "ALTER TABLE image_analysis_results ADD COLUMN method VARCHAR(50)",
        "summary": "ALTER TABLE image_analysis_results ADD COLUMN summary TEXT",
        "ai_report": "ALTER TABLE image_analysis_results ADD COLUMN ai_report TEXT",
        "consistency_score": (
            "ALTER TABLE image_analysis_results ADD COLUMN consistency_score FLOAT"
        ),
        "risk_flags": "ALTER TABLE image_analysis_results ADD COLUMN risk_flags TEXT",
        "fewshot_examples": (
            "ALTER TABLE image_analysis_results ADD COLUMN fewshot_examples TEXT"
        ),
        "error_message": (
            "ALTER TABLE image_analysis_results ADD COLUMN error_message TEXT"
        ),
    }

    for column_name, statement in alter_statements.items():
        if column_name not in columns:
            await conn.execute(text(statement))

