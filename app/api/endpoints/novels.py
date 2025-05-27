from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List, Optional
import os
import aiofiles
import aiofiles.os # For potential future use, like background file deletion

from app.models.search import SearchResult, SearchResponse
from app.models.book import Book
from app.models.chapter import Chapter, ChapterInfo
from app.services.novel_service import NovelService
from app.core.config import settings

# 创建路由
router = APIRouter(prefix="/novels", tags=["novels"])

# 创建服务实例
novel_service = NovelService()


@router.get("/search", response_model=SearchResponse)
async def search_novels(keyword: str = Query(..., description="搜索关键词（书名或作者名）")):
    """
    根据关键词搜索小说
    """
    try:
        results = await novel_service.search(keyword)
        return {
            "code": 200,
            "message": "success",
            "data": results
        }
    except Exception as e:
        # Global handler in main.py should log the details of e.
        raise HTTPException(status_code=500, detail="An internal error occurred during the search operation.")


@router.get("/detail")
async def get_novel_detail(url: str = Query(..., description="小说详情页URL"),
                          sourceId: int = Query(settings.DEFAULT_SOURCE_ID, description="书源ID")):
    """
    获取小说详情
    """
    try:
        book = await novel_service.get_book_detail(url, sourceId)
        return {
            "code": 200,
            "message": "success",
            "data": book
        }
    except Exception as e:
        # Global handler in main.py should log the details of e.
        # Consider if novel_service.get_book_detail could return None for not found,
        # then a specific check for `if book is None: raise HTTPException(404, ...)` would be better.
        # Assuming for now that any failure, including not found, results in an exception from the service.
        raise HTTPException(status_code=500, detail="An internal error occurred while fetching novel details.")


@router.get("/toc")
async def get_novel_toc(url: str = Query(..., description="小说详情页URL"),
                      sourceId: int = Query(settings.DEFAULT_SOURCE_ID, description="书源ID")):
    """
    获取小说目录
    """
    try:
        toc = await novel_service.get_toc(url, sourceId)
        return {
            "code": 200,
            "message": "success",
            "data": toc
        }
    except Exception as e:
        # Global handler in main.py should log the details of e.
        # Similar to /detail, a specific None check for not found might be applicable.
        raise HTTPException(status_code=500, detail="An internal error occurred while fetching novel table of contents.")


@router.get("/download")
async def download_novel(background_tasks: BackgroundTasks,
                       url: str = Query(..., description="小说详情页URL"),
                       sourceId: int = Query(settings.DEFAULT_SOURCE_ID, description="书源ID"),
                       format: str = Query(settings.DEFAULT_FORMAT, description="下载格式，支持txt、epub、pdf")):
    """
    下载小说
    """
    if format not in settings.SUPPORTED_FORMATS:
        raise HTTPException(status_code=400, detail=f"不支持的格式: {format}，支持的格式: {', '.join(settings.SUPPORTED_FORMATS)}")
    
    try:
        # 获取书籍信息
        book = await novel_service.get_book_detail(url, sourceId)
        
        # 异步下载并生成文件
        file_path = await novel_service.download(url, sourceId, format)
        
        # 文件名处理
        filename = f"{book.bookName}_{book.author}.{format}"
        
        # 返回文件流
        async def file_iterator(file_path_str: str, chunk_size=8192):
            async with aiofiles.open(file_path_str, "rb") as f:
                while chunk := await f.read(chunk_size):
                    yield chunk
            # Optional: Clean up the file after streaming
            # background_tasks.add_task(aiofiles.os.remove, file_path_str) # Requires aiofiles.os

        return StreamingResponse(
            file_iterator(file_path), # file_path is already a string here
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\"" # Added quotes around filename
            }
        )
    except Exception as e:
        # It's good practice to log the exception here
        # import logging
        # logging.exception("Failed to download novel") # Local logging is optional, main.py handles it.
        raise HTTPException(status_code=500, detail="An internal error occurred during the download process.")


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
        # Global handler in main.py should log the details of e.
        raise HTTPException(status_code=500, detail="An internal error occurred while fetching available sources.")