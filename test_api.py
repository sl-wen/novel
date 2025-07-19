import pytest
import asyncio
import json
import logging
# from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 创建测试客户端 (使用异步客户端)
# client = TestClient(app)

# 使用 pytest.mark.asyncio 标记异步测试函数
@pytest.mark.asyncio
async def test_search_api(async_client: AsyncClient): # 注入异步客户端fixture
    """测试搜索API"""
    logger.info("开始测试搜索API")
    response = await async_client.get("/api/novels/search?keyword=斗破苍穹") # 使用await调用异步方法
    # 记录请求信息和响应
    # 记录请求信息和响应
    logger.info(f"请求搜索 API: {async_client.base_url}/api/novels/search?keyword=斗破苍穹")
    logger.info(f"响应状态码: {response.status_code}")
    try:
        response_json = response.json()
        logger.info(f"响应体 (前500字符): {str(response_json)[:500]}...")
        # 检查响应状态码
        assert response.status_code == 200

        # 检查响应体是否为字典且包含必要字段
        assert isinstance(response_json, dict)
        assert response_json.get("code") == 200
        assert response_json.get("message") == "success"
        assert "data" in response_json
        assert isinstance(response_json["data"], list)
        assert len(response_json["data"]) > 0
    except Exception as e:
        logger.error(f"解析响应体或断言失败: {e}")
        logger.error(f"原始响应文本: {response.text[:500]}...") # 打印原始响应文本
        assert False, f"解析响应体或断言失败: {e}"
    logger.info("搜索API测试通过")

# @pytest.mark.asyncio
# async def test_search_api(): # 注入异步客户端fixture
#     """测试搜索API"""
#     logger.info("开始测试搜索API")
#     response = client.get("/api/novels/search?keyword=斗破苍穹") # 使用await调用异步方法
#     assert response.status_code == 200
#     data = response.json()
#     assert data["code"] == 200
#     assert data["message"] == "success"
#     assert isinstance(data["data"], list)
#     assert len(data["data"]) > 0
#     logger.info("搜索API测试通过")

@pytest.mark.asyncio
async def test_detail_api(async_client: AsyncClient): # 注入异步客户端fixture
    """测试详情API"""
    logger.info("开始测试详情API")
    
    # 先执行搜索获取结果
    search_response = await async_client.get("/api/novels/search?keyword=斗破苍穹") # 使用await调用异步方法
    assert search_response.status_code == 200
    search_data = search_response.json()
    # 先执行搜索获取结果
    search_response = await async_client.get("/api/novels/search?keyword=斗破苍穹") # 使用await调用异步方法
    search_data = search_response.json()
    assert search_response.status_code == 200
    assert isinstance(search_data, dict)
    assert search_data.get("code") == 200
    assert search_data.get("message") == "success"
    assert "data" in search_data
    assert isinstance(search_data["data"], list)
    assert len(search_data["data"]) > 0

    # 获取第一个搜索结果的URL和sourceId
    book_url = search_data["data"][0]["url"]
    source_id = search_data["data"][0]["sourceId"]

    # 使用获取到的URL调用详情API
    response = await async_client.get(f"/api/novels/detail?url={book_url}&sourceId={source_id}") # 使用await调用异步方法
    # 记录请求信息和响应
    logger.info(f"请求详情 API: {async_client.base_url}/api/novels/detail?url={book_url}&sourceId={source_id}")
    logger.info(f"响应状态码: {response.status_code}")
    try:
        response_json = response.json()
        logger.info(f"响应体 (前500字符): {str(response_json)[:500]}...")
        # 检查响应状态码
        assert response.status_code == 200

        # 检查响应体是否为字典且包含必要字段
        assert isinstance(response_json, dict)
        assert response_json.get("code") == 200
        assert response_json.get("message") == "success"
        assert "data" in response_json
        assert isinstance(response_json["data"], dict)
        assert "bookName" in response_json["data"]
        assert "author" in response_json["data"]
    except Exception as e:
        logger.error(f"解析响应体或断言失败: {e}")
        logger.error(f"原始响应文本: {response.text[:500]}...") # 打印原始响应文本
        assert False, f"解析响应体或断言失败: {e}"
    logger.info("详情API测试通过")

# @pytest.mark.asyncio
# async def test_detail_api(): # 注入异步客户端fixture
#     """测试详情API"""
#     logger.info("开始测试详情API")
    
#     # 先执行搜索获取结果
#     search_response = client.get("/api/novels/search?keyword=斗破苍穹") # 使用await调用异步方法
#     assert search_response.status_code == 200
#     search_data = search_response.json()
#     assert search_data["code"] == 200
#     assert search_data["message"] == "success"
#     assert isinstance(search_data["data"], list)
#     assert len(search_data["data"]) > 0
    
#     # 获取第一个搜索结果的URL和sourceId
#     book_url = search_data["data"][0]["url"]
#     source_id = search_data["data"][0]["sourceId"]
    
#     # 使用获取到的URL调用详情API
#     response = client.get(f"/api/novels/detail?url={book_url}&sourceId={source_id}") # 使用await调用异步方法
#     assert response.status_code == 200
#     data = response.json()
#     assert data["code"] == 200
#     assert data["message"] == "success"
#     assert isinstance(data["data"], dict)
#     assert "bookName" in data["data"]
#     assert "author" in data["data"]
#     logger.info("详情API测试通过")

@pytest.mark.asyncio
async def test_toc_api(async_client: AsyncClient): # 注入异步客户端fixture
    """测试目录API"""
    logger.info("开始测试目录API")
    
    # 先执行搜索获取结果
    search_response = await async_client.get("/api/novels/search?keyword=斗破苍穹") # 使用await调用异步方法
    assert search_response.status_code == 200
    search_data = search_response.json()
    # 先执行搜索获取结果
    search_response = await async_client.get("/api/novels/search?keyword=斗破苍穹") # 使用await调用异步方法
    search_data = search_response.json()
    assert search_response.status_code == 200
    assert isinstance(search_data, dict)
    assert search_data.get("code") == 200
    assert search_data.get("message") == "success"
    assert "data" in search_data
    assert isinstance(search_data["data"], list)
    assert len(search_data["data"]) > 0

    # 获取第一个搜索结果的URL和sourceId
    book_url = search_data["data"][0]["url"]
    source_id = search_data["data"][0]["sourceId"]

    # 使用获取到的URL调用目录API
    response = await async_client.get(f"/api/novels/toc?url={book_url}&sourceId={source_id}") # 使用await调用异步方法
    # 记录请求信息和响应
    logger.info(f"请求目录 API: {async_client.base_url}/api/novels/toc?url={book_url}&sourceId={source_id}")
    logger.info(f"响应状态码: {response.status_code}")
    try:
        response_json = response.json()
        logger.info(f"响应体 (前500字符): {str(response_json)[:500]}...")
        # 检查响应状态码
        assert response.status_code == 200

        # 检查响应体是否为字典且包含必要字段
        assert isinstance(response_json, dict)
        assert response_json.get("code") == 200
        assert response_json.get("message") == "success"
        assert "data" in response_json
        assert isinstance(response_json["data"], list)
        assert len(response_json["data"]) > 0
    except Exception as e:
        logger.error(f"解析响应体或断言失败: {e}")
        logger.error(f"原始响应文本: {response.text[:500]}...") # 打印原始响应文本
        assert False, f"解析响应体或断言失败: {e}"
    logger.info("目录API测试通过")

# @pytest.mark.asyncio
# async def test_toc_api(): # 注入异步客户端fixture
#     """测试目录API"""
#     logger.info("开始测试目录API")
    
#     # 先执行搜索获取结果
#     search_response = client.get("/api/novels/search?keyword=斗破苍穹") # 使用await调用异步方法
#     assert search_response.status_code == 200
#     search_data = search_response.json()
#     assert search_data["code"] == 200
#     assert search_data["message"] == "success"
#     assert isinstance(search_data["data"], list)
#     assert len(search_data["data"]) > 0
    
#     # 获取第一个搜索结果的URL和sourceId
#     book_url = search_data["data"][0]["url"]
#     source_id = search_data["data"][0]["sourceId"]
    
#     # 使用获取到的URL调用目录API
#     response = client.get(f"/api/novels/toc?url={book_url}&sourceId={source_id}") # 使用await调用异步方法
#     assert response.status_code == 200
#     data = response.json()
#     assert data["code"] == 200
#     assert data["message"] == "success"
#     assert isinstance(data["data"], list)
#     assert len(data["data"]) > 0
#     logger.info("目录API测试通过")

@pytest.mark.asyncio
async def test_download_api(async_client: AsyncClient): # 注入异步客户端fixture
    """测试下载API"""
    logger.info("开始测试下载API")
    
    # 先执行搜索获取结果
    search_response = await async_client.get("/api/novels/search?keyword=斗破苍穹") # 使用await调用异步方法
    assert search_response.status_code == 200
    search_data = search_response.json()
    # 先执行搜索获取结果
    search_response = await async_client.get("/api/novels/search?keyword=斗破苍穹") # 使用await调用异步方法
    search_data = search_response.json()
    assert search_response.status_code == 200
    assert isinstance(search_data, dict)
    assert search_data.get("code") == 200
    assert search_data.get("message") == "success"
    assert "data" in search_data
    assert isinstance(search_data["data"], list)
    assert len(search_data["data"]) > 0

    # 获取第一个搜索结果的URL和sourceId
    book_url = search_data["data"][0]["url"]
    source_id = search_data["data"][0]["sourceId"]

    # 使用获取到的URL调用下载API
    response = await async_client.get(f"/api/novels/download?url={book_url}&sourceId={source_id}&format=txt") # 使用await调用异步方法
    # 记录请求信息和响应
    logger.info(f"请求下载 API: {async_client.base_url}/api/novels/download?url={book_url}&sourceId={source_id}&format=txt")
    logger.info(f"响应状态码: {response.status_code}")
    try:
        # 检查响应状态码
        assert response.status_code == 200
        # 对于文件下载，检查响应内容类型或头部信息
        assert response.headers["content-type"] == "application/octet-stream"
        assert "attachment" in response.headers["content-disposition"]
    except Exception as e:
        logger.error(f"断言失败: {e}")
        logger.error(f"原始响应文本: {response.text[:500]}...") # 打印原始响应文本
        assert False, f"断言失败: {e}"
    logger.info("下载API测试通过")

# @pytest.mark.asyncio
# async def test_download_api(): # 注入异步客户端fixture
#     """测试下载API"""
#     logger.info("开始测试下载API")
    
#     # 先执行搜索获取结果
#     search_response = client.get("/api/novels/search?keyword=斗破苍穹") # 使用await调用异步方法
#     assert search_response.status_code == 200
#     search_data = search_response.json()
#     assert search_data["code"] == 200
#     assert search_data["message"] == "success"
#     assert isinstance(search_data["data"], list)
#     assert len(search_data["data"]) > 0
    
#     # 获取第一个搜索结果的URL和sourceId
#     book_url = search_data["data"][0]["url"]
#     source_id = search_data["data"][0]["sourceId"]
    
#     # 使用获取到的URL调用下载API
#     response = client.get(f"/api/novels/download?url={book_url}&sourceId={source_id}&format=txt") # 使用await调用异步方法
#     assert response.status_code == 200
#     # 对于文件下载，检查响应内容类型或头部信息
#     assert response.headers["content-type"] == "application/octet-stream"
#     assert "attachment" in response.headers["content-disposition"]
#     logger.info("下载API测试通过")

@pytest.mark.asyncio
async def test_sources_api(async_client: AsyncClient): # 注入异步客户端fixture
    """测试书源API"""
    logger.info("开始测试书源API")
    response = await async_client.get("/api/novels/sources") # 使用await调用异步方法
    # 记录请求信息和响应
    # 记录请求信息和响应
    logger.info(f"请求书源 API: {async_client.base_url}/api/novels/sources")
    logger.info(f"响应状态码: {response.status_code}")
    try:
        response_json = response.json()
        logger.info(f"响应体 (前500字符): {str(response_json)[:500]}...")
        # 检查响应状态码
        assert response.status_code == 200

        # 检查响应体是否为字典且包含必要字段
        assert isinstance(response_json, dict)
        assert response_json.get("code") == 200
        assert response_json.get("message") == "success"
        assert "data" in response_json
        assert isinstance(response_json["data"], list)
        assert len(response_json["data"]) > 0
    except Exception as e:
        logger.error(f"解析响应体或断言失败: {e}")
        logger.error(f"原始响应文本: {response.text[:500]}...") # 打印原始响应文本
        assert False, f"解析响应体或断言失败: {e}"
    logger.info("书源API测试通过")

# @pytest.mark.asyncio
# async def test_sources_api(): # 注入异步客户端fixture
#     """测试书源API"""
#     logger.info("开始测试书源API")
#     response = client.get("/api/novels/sources") # 使用await调用异步方法
#     assert response.status_code == 200
#     data = response.json()
#     assert data["code"] == 200
#     assert data["message"] == "success"
#     assert isinstance(data["data"], list)
#     assert len(data["data"]) > 0
#     logger.info("书源API测试通过")

# async def run_tests():
# ... (原始 run_tests 代码)

# if __name__ == "__main__":
#    asyncio.run(run_tests())