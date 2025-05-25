from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List, Optional
import os

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
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


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
        raise HTTPException(status_code=500, detail=f"获取小说详情失败: {str(e)}")


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
        raise HTTPException(status_code=500, detail=f"获取小说目录失败: {str(e)}")


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
        return StreamingResponse(
            open(file_path, "rb"),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载小说失败: {str(e)}")


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