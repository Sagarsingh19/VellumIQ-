import asyncio
from typing import AsyncGenerator, Generator
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import settings

# Force SQLite and Eager/Local setups for test runs
settings.DATABASE_PROVIDER = "sqlite"
settings.DATABASE_URL = "sqlite+aiosqlite:///./test_db.db"
settings.SYNC_DATABASE_URL = "sqlite:///./test_db.db"
settings.CELERY_TASK_ALWAYS_EAGER = True
settings.STORAGE_BACKEND = "local"

from app.core.database import Base, get_db
from app.main import app

# Create a separate database engine for testing.
test_db_url = "sqlite+aiosqlite:///./test_db.db"
test_engine = create_async_engine(
    test_db_url,
    echo=False,
)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


import pytest_asyncio

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


import os
import shutil

@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_db():
    """Ensure database tables are created before running tests."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    # Cleanup local storage files created during tests
    if os.path.exists("storage_local"):
        shutil.rmtree("storage_local", ignore_errors=True)
        
    # Cleanup test sqlite database files
    for ext in ["", "-journal", "-wal"]:
        path = f"test_db.db{ext}"
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a standard database session committing directly."""
    async with TestingSessionLocal() as session:
        yield session
        await session.close()


@pytest_asyncio.fixture(autouse=True)
async def clean_database_tables():
    """Clean database tables after each test case to preserve isolation."""
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTPX AsyncClient for API testing, overriding database dependency."""

    async def _get_db_override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _get_db_override
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as async_client:
        yield async_client
    app.dependency_overrides.clear()
