import pytest
import asyncio
import json
import logging
from fastapi.testclient import TestClient

from app.main import app

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 创建测试客户端
client = TestClient(app)

# 使用 pytest.mark.asyncio 标记异步测试函数
@pytest.mark.asyncio
async def test_search_api():
    """测试搜索API"""
    logger.info("开始测试搜索API")
    response = client.get("/api/novels/search/?keyword=斗破苍穹")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["message"] == "success"
    assert isinstance(data["data"], list)
    assert len(data["data"]) > 0
    logger.info("搜索API测试通过")

@pytest.mark.asyncio
async def test_detail_api():
    """测试详情API"""
    logger.info("开始测试详情API")
    
    # 先执行搜索获取结果
    search_response = client.get("/api/novels/search/?keyword=斗破苍穹")
    assert search_response.status_code == 200
    search_data = search_response.json()
    assert search_data["code"] == 200
    assert search_data["message"] == "success"
    assert isinstance(search_data["data"], list)
    assert len(search_data["data"]) > 0
    
    # 获取第一个搜索结果的URL和sourceId
    book_url = search_data["data"][0]["url"]
    source_id = search_data["data"][0]["sourceId"]
    
    # 使用获取到的URL调用详情API
    response = client.get(f"/api/novels/detail/?url={book_url}&sourceId={source_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["message"] == "success"
    assert isinstance(data["data"], dict)
    assert "bookName" in data["data"]
    assert "author" in data["data"]
    logger.info("详情API测试通过")

@pytest.mark.asyncio
async def test_toc_api():
    """测试目录API"""
    logger.info("开始测试目录API")
    
    # 先执行搜索获取结果
    search_response = client.get("/api/novels/search/?keyword=斗破苍穹")
    assert search_response.status_code == 200
    search_data = search_response.json()
    assert search_data["code"] == 200
    assert search_data["message"] == "success"
    assert isinstance(search_data["data"], list)
    assert len(search_data["data"]) > 0
    
    # 获取第一个搜索结果的URL和sourceId
    book_url = search_data["data"][0]["url"]
    source_id = search_data["data"][0]["sourceId"]
    
    # 使用获取到的URL调用目录API
    response = client.get(f"/api/novels/toc/?url={book_url}&sourceId={source_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["message"] == "success"
    assert isinstance(data["data"], list)
    assert len(data["data"]) > 0
    logger.info("目录API测试通过")

@pytest.mark.asyncio
async def test_download_api():
    """测试下载API"""
    logger.info("开始测试下载API")
    
    # 先执行搜索获取结果
    search_response = client.get("/api/novels/search/?keyword=斗破苍穹")
    assert search_response.status_code == 200
    search_data = search_response.json()
    assert search_data["code"] == 200
    assert search_data["message"] == "success"
    assert isinstance(search_data["data"], list)
    assert len(search_data["data"]) > 0
    
    # 获取第一个搜索结果的URL和sourceId
    book_url = search_data["data"][0]["url"]
    source_id = search_data["data"][0]["sourceId"]
    
    # 使用获取到的URL调用下载API
    response = client.get(f"/api/novels/download/?url={book_url}&sourceId={source_id}&format=txt")
    assert response.status_code == 200
    # 下载API返回的是文件流，这里只检查状态码
    logger.info("下载API测试通过")

@pytest.mark.asyncio
async def test_sources_api():
    """测试获取书源API"""
    logger.info("开始测试获取书源API")
    
    response = client.get("/api/novels/sources")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["message"] == "success"
    assert isinstance(data["data"], list)
    assert len(data["data"]) > 0
    logger.info("获取书源API测试通过")

# async def run_tests():
# ... (原始 run_tests 代码)

# if __name__ == "__main__":
#    asyncio.run(run_tests())