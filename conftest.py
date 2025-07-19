import sys
import pytest
import asyncio
import pytest_asyncio

@pytest.fixture(scope="session")
def event_loop_policy():
    # 配置 pytest-asyncio 使用特定的事件循环策略
    # 这是一个 fixture，用于覆盖默认策略
    if sys.platform == "win32":
        policy = asyncio.WindowsSelectorEventLoopPolicy()
    else:
        policy = asyncio.DefaultEventLoopPolicy()
    return policy

@pytest_asyncio.fixture(scope="function")
async def async_client():
    """Fixture that provides an asynchronous test client for the FastAPI application."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client