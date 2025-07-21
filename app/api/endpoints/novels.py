from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import os
import logging
import traceback

from app.models.search import SearchResult, SearchResponse
from app.models.book import Book
from app.models.chapter import Chapter, ChapterInfo
from app.services.novel_service import NovelService
from app.core.config import settings

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter(prefix="/novels", tags=["novels"])

# 创建服务实例
novel_service = NovelService()


@router.get("/search", response_model=SearchResponse)
async def search_novels(
    keyword: str = Query(None, description="搜索关键词（书名或作者名）"),
    maxResults: int = Query(30, ge=1, le=100, description="最大返回结果数，默认30，最大100")
):
    """
    根据关键词搜索小说
    """
    try:
        logger.info(f"开始搜索小说，关键词：{keyword}，maxResults={maxResults}")
        results = await novel_service.search(keyword, max_results=maxResults)
        logger.info(f"搜索完成，找到 {len(results)} 条结果")
        return {
            "code": 200,
            "message": "success",
            "data": results
        }
    except Exception as e:
        logger.error(f"搜索失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"搜索失败: {str(e)}",
                "data": None
            }
        )


@router.get("/detail")
async def get_novel_detail(url: str = Query(..., description="小说详情页URL"),
                          sourceId: int = Query(settings.DEFAULT_SOURCE_ID, description="书源ID")):
    """
    获取小说详情
    """
    try:
        logger.info(f"开始获取小说详情，URL：{url}，书源ID：{sourceId}")
        book = await novel_service.get_book_detail(url, sourceId)
        logger.info(f"获取小说详情成功：{book.bookName}")
        return {
            "code": 200,
            "message": "success",
            "data": book
        }
    except Exception as e:
        logger.error(f"获取小说详情失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"获取小说详情失败: {str(e)}",
                "data": None
            }
        )


@router.get("/toc")
async def get_novel_toc(url: str = Query(..., description="小说详情页URL"),
                      sourceId: int = Query(settings.DEFAULT_SOURCE_ID, description="书源ID")):
    """
    获取小说目录
    """
    try:
        logger.info(f"开始获取小说目录，URL：{url}，书源ID：{sourceId}")
        toc = await novel_service.get_toc(url, sourceId)
        logger.info(f"获取小说目录成功，共 {len(toc)} 章")
        return {
            "code": 200,
            "message": "success",
            "data": toc
        }
    except Exception as e:
        logger.error(f"获取小说目录失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"获取小说目录失败: {str(e)}",
                "data": None
            }
        )


@router.get("/download")
async def download_novel(background_tasks: BackgroundTasks,
                       url: str = Query(..., description="小说详情页URL"),
                       sourceId: int = Query(settings.DEFAULT_SOURCE_ID, description="书源ID"),
                       format: str = Query(settings.DEFAULT_FORMAT, description="下载格式，支持txt、epub、pdf")):
    """
    下载小说
    """
    if format not in settings.SUPPORTED_FORMATS:
        return JSONResponse(
            status_code=400,
            content={
                "code": 400,
                "message": f"不支持的格式: {format}，支持的格式: {', '.join(settings.SUPPORTED_FORMATS)}",
                "data": None
            }
        )
    
    try:
        logger.info(f"开始下载小说，URL：{url}，书源ID：{sourceId}，格式：{format}")
        # 获取书籍信息
        book = await novel_service.get_book_detail(url, sourceId)
        logger.info(f"获取书籍信息成功：{book.bookName}")
        
        # 异步下载并生成文件
        file_path = await novel_service.download(url, sourceId, format)
        logger.info(f"下载完成，文件路径：{file_path}")
        if not file_path or not os.path.exists(file_path):
            raise ValueError(f"文件生成失败或不存在: {file_path}")
        
        # 文件名处理 - 解决中文编码问题
        import urllib.parse
        # safe_book_name = book.bookName.replace("/", "_").replace("\\", "_").replace(":", "：")  # 替换不安全字符
        # safe_author = book.author.replace("/", "_").replace("\\", "_").replace(":", "：")
        # 🔧 修复点1：安全获取书籍信息
        book_name = getattr(book, 'bookName', '未知小说') or '未知小说'
        author = getattr(book, 'author', '未知作者') or '未知作者'
    
        # 🔧 修复点2：确保字符串类型
        book_name = str(book_name) if book_name is not None else '未知小说'
        author = str(author) if author is not None else '未知作者'
        filename = f"{book_name}_{author}.{format}"
        
        # 对文件名进行URL编码，解决中文字符问题
        encoded_filename = urllib.parse.quote(filename, safe='')
        
        # 返回文件流
        return StreamingResponse(
            open(file_path, "rb"),
            media_type="application/octet-stream",
            headers={
                # 使用RFC 5987标准格式，支持UTF-8编码的文件名
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        logger.error(f"下载小说失败: {str(e)}")
        logger.error(f"下载失败详细信息:\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"下载小说失败: {str(e)}",
                "data": None
            }
        )


@router.get("/sources")
async def get_sources():
    """
    获取所有可用书源
    """
    try:
        sources = await novel_service.get_sources()
        return {
            "code": 200,
            "message": "success",
            "data": sources
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取书源失败: {str(e)}")
