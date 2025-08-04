import logging
import os

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.models.search import SearchResponse
from app.services.novel_service import NovelService

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter(prefix="/novels", tags=["novels"])

# 创建服务实例
novel_service = NovelService()


@router.get("/search", response_model=SearchResponse)
async def search_novels(
    keyword: str = Query(None, description="搜索关键词（书名或作者名）"),
    maxResults: int = Query(
        30,
        ge=1,
        le=100,
        description="最大返回结果数，默认30，最大100",
    ),
):
    """
    根据关键词搜索小说
    """
    try:
        logger.info(f"开始搜索小说，关键词：{keyword}，maxResults={maxResults}")
        results = await novel_service.search(keyword, max_results=maxResults)
        logger.info(f"搜索完成，找到 {len(results)} 条结果")

        # 尝试序列化结果，如果出现bookName错误则跳过有问题的结果
        try:
            return {"code": 200, "message": "success", "data": results}
        except AttributeError as e:
            if "bookName" in str(e):
                logger.warning(
                    f"搜索结果序列化时出现bookName错误，跳过有问题的结果: {str(e)}"
                )
                # 过滤掉有问题的结果
                filtered_results = []
                for result in results:
                    try:
                        # 尝试访问bookName属性，如果失败则跳过
                        _ = getattr(result, "bookName", None)
                        filtered_results.append(result)
                    except AttributeError:
                        logger.warning(f"跳过有bookName问题的搜索结果")
                        continue
                return {"code": 200, "message": "success", "data": filtered_results}
            else:
                raise e
    except Exception as e:
        logger.error(f"搜索失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"搜索失败: {str(e)}",
                "data": None,
            },
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
        logger.info(f"获取小说详情成功：{book.title}")
        return {"code": 200, "message": "success", "data": book}
    except Exception as e:
        logger.error(f"获取小说详情失败: {str(e)}")
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
    format: str = Query(settings.DEFAULT_FORMAT, description="下载格式，支持txt、epub"),
):
    """
    下载小说
    """
    try:
        logger.info(f"开始下载小说，URL：{url}，书源ID：{sourceId}，格式：{format}")

        # 异步下载小说
        file_path = await novel_service.download(url, sourceId, format)

        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=500, detail="文件生成失败")

        # 获取文件信息
        from pathlib import Path

        file_obj = Path(file_path)
        filename = file_obj.name

        # 返回文件流
        import urllib.parse

        from fastapi.responses import StreamingResponse

        # 对文件名进行URL编码，解决中文字符问题
        encoded_filename = urllib.parse.quote(filename, safe="")

        return StreamingResponse(
            open(file_path, "rb"),
            media_type="application/octet-stream",
            headers={
                # 使用RFC 5987标准格式，支持UTF-8编码的文件名
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
                "Access-Control-Expose-Headers": "Content-Disposition",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载小说失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": f"下载小说失败: {str(e)}", "data": None},
        )


@router.get("/chapter")
async def get_chapter_content(
    url: str = Query(..., description="章节URL"),
    sourceId: int = Query(settings.DEFAULT_SOURCE_ID, description="书源ID"),
):
    """
    获取章节内容
    """
    try:
        logger.info(f"开始获取章节内容，URL：{url}，书源ID：{sourceId}")
        chapter = await novel_service.get_chapter_content(url, sourceId)
        logger.info(f"获取章节内容成功：{chapter.title}")
        return {"code": 200, "message": "success", "data": chapter}
    except Exception as e:
        logger.error(f"获取章节内容失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"获取章节内容失败: {str(e)}",
                "data": None,
            },
        )


@router.get("/sources")
async def get_sources():
    """
    获取所有书源信息
    """
    try:
        logger.info("开始获取书源信息")
        sources = novel_service.get_sources()
        logger.info(f"获取书源信息成功，共 {len(sources)} 个书源")
        return {"code": 200, "message": "success", "data": sources}
    except Exception as e:
        logger.error(f"获取书源信息失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"获取书源信息失败: {str(e)}",
                "data": None,
            },
        )
