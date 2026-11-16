from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Entrega una sesión de base de datos por request."""
    async with SessionLocal() as session:
        yield session


async def check_database() -> None:
    """Comprueba que la base de datos responde."""
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
