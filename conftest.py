import pytest
# import asyncio
# import httpx
from app.main import app as fastapi_app

# 配置 pytest-asyncio
# def pytest_configure(config):
#     """配置 pytest-asyncio 插件"""
#     config.option.asyncio_mode = "auto"

# 创建一个事件循环策略
# @pytest.fixture(scope="session")
# def event_loop():
#     """创建一个事件循环，供所有测试使用"""
#     # 使用新的事件循环策略
#     policy = asyncio.get_event_loop_policy()
#     loop = policy.new_event_loop()
#     asyncio.set_event_loop(loop)
#     
#     # 返回循环，但不在测试结束后关闭它
#     # 这样可以避免 "Event loop is closed" 错误
#     yield loop
#     
#     # 关闭所有未完成的任务
#     pending = asyncio.all_tasks(loop)
#     for task in pending:
#         task.cancel()
#     
#     # 运行直到所有任务完成
#     if pending:
#         loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
#     
#     # 现在安全地关闭循环
#     loop.run_until_complete(loop.shutdown_asyncgens())
#     loop.close()

# 创建一个 FastAPI 应用 fixture
@pytest.fixture(scope="session")
def app():
    """创建一个 FastAPI 应用，供所有测试使用"""
    return fastapi_app

# 创建一个 AsyncClient fixture
# @pytest.fixture
# async def async_client(app):
#     """创建一个 AsyncClient，供测试使用"""
#     async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
#         yield client