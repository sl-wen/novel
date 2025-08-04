#!/usr/bin/env python3
"""
修复API 500错误的脚本
参考test_actual_search.py的工作方式来修复API问题
"""

import os
import sys
from pathlib import Path


def fix_novels_endpoint():
    """修复小说API端点"""
    print("🔧 修复小说API端点...")

    endpoint_file = Path("app/api/endpoints/novels.py")
    if not endpoint_file.exists():
        print("❌ 找不到API端点文件")
        return False

    # 读取当前内容
    with open(endpoint_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 创建修复后的内容
    fixed_content = '''import logging
import os
import time
import traceback
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.config import settings
from app.models.book import Book
from app.models.chapter import Chapter, ChapterInfo
from app.models.search import SearchResponse, SearchResult
from app.services.novel_service import NovelService

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter(prefix="/novels", tags=["novels"])

# 创建服务实例
novel_service = NovelService()


@router.get("/search", response_model=SearchResponse)
async def search_novels(
    keyword: str = Query(None, description="搜索关键词（书名或作者名）")
):
    """
    根据关键词搜索小说
    """
    try:
        logger.info(f"开始搜索小说，关键词：{keyword}")
        
        # 参考test_actual_search.py的方式
        if not keyword:
            return JSONResponse(
                status_code=400,
                content={"code": 400, "message": "搜索关键词不能为空", "data": None},
            )
        
        # 直接调用服务，就像test_actual_search.py那样
        results = await novel_service.search(keyword)
        logger.info(f"搜索完成，找到 {len(results)} 条结果")
        
        # 确保结果是正确的格式
        formatted_results = []
        for result in results:
            try:
                # 检查结果是否有必要的属性
                if hasattr(result, 'bookName') and hasattr(result, 'author'):
                    formatted_results.append(result)
                else:
                    logger.warning(f"跳过无效结果: {type(result)}")
            except Exception as e:
                logger.error(f"处理搜索结果时出错: {str(e)}")
                continue
        
        return {"code": 200, "message": "success", "data": formatted_results}
    except Exception as e:
        logger.error(f"搜索失败: {str(e)}")
        logger.error(f"详细错误信息:\\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": f"搜索失败: {str(e)}", "data": None},
        )


@router.get("/detail")
async def get_novel_detail(
    url: str = Query(..., description="小说详情页URL"),
    sourceId: int = Query(settings.DEFAULT_SOURCE_ID, description="书源ID"),
):
    """
    获取小说详情
    """
    try:
        logger.info(f"开始获取小说详情，URL：{url}，书源ID：{sourceId}")
        book = await novel_service.get_book_detail(url, sourceId)
        try:
            book_name = getattr(book, "bookName", "未知书名") or "未知书名"
            logger.info(f"获取小说详情成功：{book_name}")
        except Exception as e:
            logger.error(f"获取书籍名称时发生异常: {str(e)}")
            logger.info(f"获取小说详情成功：未知书名")
        return {"code": 200, "message": "success", "data": book}
    except Exception as e:
        logger.error(f"获取小说详情失败: {str(e)}")
        logger.error(f"详细错误信息:\\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"获取小说详情失败: {str(e)}",
                "data": None,
            },
        )


@router.get("/toc")
async def get_novel_toc(
    url: str = Query(..., description="小说详情页URL"),
    sourceId: int = Query(settings.DEFAULT_SOURCE_ID, description="书源ID"),
):
    """
    获取小说目录
    """
    try:
        logger.info(f"开始获取小说目录，URL：{url}，书源ID：{sourceId}")
        toc = await novel_service.get_toc(url, sourceId)
        logger.info(f"获取小说目录成功，共 {len(toc)} 章")
        return {"code": 200, "message": "success", "data": toc}
    except Exception as e:
        logger.error(f"获取小说目录失败: {str(e)}")
        logger.error(f"详细错误信息:\\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"获取小说目录失败: {str(e)}",
                "data": None,
            },
        )


@router.get("/download")
async def download_novel(
    background_tasks: BackgroundTasks,
    url: str = Query(..., description="小说详情页URL"),
    sourceId: int = Query(settings.DEFAULT_SOURCE_ID, description="书源ID"),
    format: str = Query(
        settings.DEFAULT_FORMAT, description="下载格式，支持txt、epub、pdf"
    ),
):
    """
    下载小说
    """
    if format not in settings.SUPPORTED_FORMATS:
        return JSONResponse(
            status_code=400,
            content={
                "code": 400,
                "message": f"不支持的格式: {format}，支持的格式: {', '.join(settings.SUPPORTED_FORMATS)}",
                "data": None,
            },
        )

    try:
        logger.info(f"开始下载小说，URL：{url}，书源ID：{sourceId}，格式：{format}")
        # 获取书籍信息
        book = await novel_service.get_book_detail(url, sourceId)
        try:
            book_name = getattr(book, "bookName", "未知书名") or "未知书名"
            logger.info(f"获取书籍信息成功：{book_name}")
        except Exception as e:
            logger.error(f"获取书籍名称时发生异常: {str(e)}")
            logger.info(f"获取书籍信息成功：未知书名")

        # 异步下载并生成文件
        file_path = await novel_service.download(url, sourceId, format)
        logger.info(f"下载完成，文件路径：{file_path}")
        if not file_path or not os.path.exists(file_path):
            raise ValueError(f"文件生成失败或不存在: {file_path}")

        # 文件名处理 - 解决中文编码问题
        import urllib.parse

        # safe_book_name = book.bookName.replace("/", "_").replace("\\\\", "_").replace(":", "：")  # 替换不安全字符
        # safe_author = book.author.replace("/", "_").replace("\\\\", "_").replace(":", "：")
        # 🔧 修复点1：安全获取书籍信息
        book_name = getattr(book, "bookName", "未知小说") or "未知小说"
        author = getattr(book, "author", "未知作者") or "未知作者"

        # 🔧 修复点2：确保字符串类型
        book_name = str(book_name) if book_name is not None else "未知小说"
        author = str(author) if author is not None else "未知作者"
        filename = f"{book_name}_{author}.{format}"

        # 对文件名进行URL编码，解决中文字符问题
        encoded_filename = urllib.parse.quote(filename, safe="")

        # 返回文件流
        return StreamingResponse(
            open(file_path, "rb"),
            media_type="application/octet-stream",
            headers={
                # 使用RFC 5987标准格式，支持UTF-8编码的文件名
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
                "Access-Control-Expose-Headers": "Content-Disposition",
            },
        )
    except Exception as e:
        logger.error(f"下载小说失败: {str(e)}")
        logger.error(f"下载失败详细信息:\\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": f"下载小说失败: {str(e)}", "data": None},
        )


@router.get("/sources")
async def get_sources():
    """
    获取所有可用书源
    """
    try:
        # 参考test_actual_search.py的方式，直接调用服务
        sources = await novel_service.get_sources()
        return {"code": 200, "message": "success", "data": sources}
    except Exception as e:
        logger.error(f"获取书源失败: {str(e)}")
        logger.error(f"详细错误信息:\\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": f"获取书源失败: {str(e)}", "data": None},
        )


@router.get("/health")
async def health_check():
    """
    健康检查端点
    """
    try:
        # 检查本地服务状态 - 参考test_actual_search.py的方式
        try:
            # 直接访问sources属性，就像test_actual_search.py中那样
            sources_count = len(novel_service.sources)
        except Exception as e:
            logger.error(f"获取书源信息失败: {str(e)}")
            sources_count = 0

        # 检查外部连接（可选）
        external_status = "unknown"
        try:
            import requests

            response = requests.get("https://httpbin.org/get", timeout=5)
            external_status = "connected" if response.status_code == 200 else "failed"
        except Exception as e:
            external_status = f"error: {str(e)}"

        return {
            "code": 200,
            "message": "API服务正常运行",
            "data": {
                "status": "healthy",
                "sources_count": sources_count,
                "external_connectivity": external_status,
                "timestamp": time.time(),
            },
        }
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        logger.error(f"详细错误信息:\\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": f"健康检查失败: {str(e)}", "data": None},
        )
'''

    # 备份原文件
    backup_file = endpoint_file.with_suffix(".py.backup")
    with open(backup_file, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ 原文件已备份到: {backup_file}")

    # 写入修复后的内容
    with open(endpoint_file, "w", encoding="utf-8") as f:
        f.write(fixed_content)

    print("✅ API端点已修复")
    return True


def create_test_api_script():
    """创建测试API的脚本"""
    print("🔧 创建API测试脚本...")

    test_script = '''#!/usr/bin/env python3
"""
测试修复后的API
"""

import requests
import json
import time

def test_api():
    """测试API功能"""
    base_url = "http://localhost:8000"
    
    print("🔍 测试健康检查...")
    try:
        response = requests.get(f"{base_url}/api/novels/health", timeout=10)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
        else:
            print(f"错误: {response.text}")
    except Exception as e:
        print(f"健康检查失败: {str(e)}")
    
    print("\\n🔍 测试书源获取...")
    try:
        response = requests.get(f"{base_url}/api/novels/sources", timeout=10)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"书源数量: {len(data.get('data', []))}")
        else:
            print(f"错误: {response.text}")
    except Exception as e:
        print(f"书源获取失败: {str(e)}")
    
    print("\\n🔍 测试搜索功能...")
    try:
        response = requests.get(f"{base_url}/api/novels/search?keyword=斗破苍穹", timeout=30)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            results = data.get('data', [])
            print(f"搜索结果数量: {len(results)}")
            if results:
                first_result = results[0]
                print(f"第一个结果: {first_result.get('bookName')} - {first_result.get('author')}")
        else:
            print(f"错误: {response.text}")
    except Exception as e:
        print(f"搜索失败: {str(e)}")

if __name__ == "__main__":
    test_api()
'''

    with open("test_fixed_api.py", "w", encoding="utf-8") as f:
        f.write(test_script)

    print("✅ API测试脚本已创建: test_fixed_api.py")


def main():
    """主函数"""
    print("🔧 修复API 500错误")
    print("=" * 50)

    # 修复API端点
    if fix_novels_endpoint():
        print("✅ API端点修复完成")
    else:
        print("❌ API端点修复失败")
        return

    # 创建测试脚本
    create_test_api_script()

    print("\n🎉 修复完成！")
    print("📋 接下来的步骤:")
    print("1. 重启API服务: python start_api.py")
    print("2. 测试修复后的API: python test_fixed_api.py")
    print("3. 或者使用原来的测试: python test_api.py")


if __name__ == "__main__":
    main()
