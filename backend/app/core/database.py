from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine

from app.core.config import settings

# Async Engine and Session
if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
    )
else:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Sync Engine and Session (optional for sync scripts or jobs)
if settings.SYNC_DATABASE_URL.startswith("sqlite"):
    sync_engine = create_engine(
        settings.SYNC_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
else:
    sync_engine = create_engine(
        settings.SYNC_DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )

sync_session_maker = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database session in FastAPI requests."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
