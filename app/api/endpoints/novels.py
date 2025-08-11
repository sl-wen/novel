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

        # 使用生成器确保文件正确关闭
        def file_generator():
            try:
                with open(file_path, "rb") as f:
                    while True:
                        chunk = f.read(8192)  # 8KB chunks
                        if not chunk:
                            break
                        yield chunk
            except Exception as e:
                logger.error(f"读取文件失败: {str(e)}")
                raise
        
        return StreamingResponse(
            file_generator(),
            media_type="application/octet-stream",
            headers={
                # 使用RFC 5987标准格式，支持UTF-8编码的文件名
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
                "Access-Control-Expose-Headers": "Content-Disposition",
                "Content-Length": str(file_obj.stat().st_size),
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


@router.get("/download/progress")
async def get_download_progress(
    task_id: str = Query(..., description="下载任务ID")
):
    """
    获取下载进度（增强版，支持超时监控）
    """
    try:
        logger.info(f"获取下载进度，任务ID：{task_id}")
        
        from app.utils.progress_tracker import progress_tracker
        from app.utils.timeout_manager import timeout_manager
        
        # 更新心跳
        progress_tracker.heartbeat(task_id)
        
        progress = progress_tracker.get_progress(task_id)
        if not progress:
            return JSONResponse(
                status_code=404,
                content={
                    "code": 404,
                    "message": f"任务不存在: {task_id}",
                    "data": None,
                },
            )
        
        # 获取超时统计信息
        timeout_stats = timeout_manager.get_stats(f"download_task_{task_id}")
        
        result_data = progress.to_dict()
        if timeout_stats:
            result_data["timeout_stats"] = timeout_stats
        
        return {"code": 200, "message": "success", "data": result_data}
    except Exception as e:
        logger.error(f"获取下载进度失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"获取下载进度失败: {str(e)}",
                "data": None,
            },
        )


@router.post("/download/start")
async def start_download(
    url: str = Query(..., description="小说详情页URL"),
    sourceId: int = Query(settings.DEFAULT_SOURCE_ID, description="书源ID"),
    format: str = Query(settings.DEFAULT_FORMAT, description="下载格式，支持txt、epub"),
):
    """启动异步下载任务，立即返回任务ID"""
    try:
        from app.utils.progress_tracker import progress_tracker
        
        # 创建任务
        task_id = progress_tracker.create_task(total_chapters=0)
        progress_tracker.start_task(task_id)
        logger.info(f"启动下载任务: {task_id} ({url}, source={sourceId}, format={format})")
        
        async def run_download():
            try:
                file_path = await novel_service.download(url, sourceId, format, task_id=task_id)
                if file_path:
                    progress_tracker.set_file_path(task_id, file_path)
                    progress_tracker.complete_task(task_id, True)
                else:
                    progress_tracker.complete_task(task_id, False, "文件生成失败")
            except Exception as e:
                logger.error(f"后台下载任务失败: {str(e)}")
                progress_tracker.complete_task(task_id, False, str(e))
        
        # 后台执行
        import asyncio
        asyncio.create_task(run_download())
        
        return {"code": 202, "message": "accepted", "data": {"task_id": task_id}}
    except Exception as e:
        logger.error(f"启动下载任务失败: {str(e)}")
        return JSONResponse(status_code=500, content={"code": 500, "message": str(e), "data": None})


@router.get("/download/result")
async def get_download_result(task_id: str = Query(..., description="下载任务ID")):
    """获取已完成任务的文件（若未完成则返回状态）"""
    try:
        from app.utils.progress_tracker import progress_tracker
        from fastapi.responses import StreamingResponse
        import urllib.parse
        from pathlib import Path
        
        progress = progress_tracker.get_progress(task_id)
        if not progress:
            return JSONResponse(status_code=404, content={"code": 404, "message": "任务不存在", "data": None})
        
        # 未完成直接返回状态
        if progress.status not in [progress.status.COMPLETED, progress.status.FAILED]:
            return {"code": 200, "message": "running", "data": progress.to_dict()}
        
        if progress.status == progress.status.FAILED:
            return JSONResponse(status_code=500, content={"code": 500, "message": progress.error_message or "任务失败", "data": progress.to_dict()})
        
        file_path = progress.file_path
        if not file_path or not os.path.exists(file_path):
            return JSONResponse(status_code=500, content={"code": 500, "message": "文件不存在或尚未生成", "data": progress.to_dict()})
        
        file_obj = Path(file_path)
        filename = file_obj.name
        encoded_filename = urllib.parse.quote(filename, safe="")
        
        def file_generator():
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    yield chunk
        
        return StreamingResponse(
            file_generator(),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
                "Access-Control-Expose-Headers": "Content-Disposition",
                "Content-Length": str(file_obj.stat().st_size),
            },
        )
    except Exception as e:
        logger.error(f"获取下载结果失败: {str(e)}")
        return JSONResponse(status_code=500, content={"code": 500, "message": str(e), "data": None})


@router.get("/download/progress/smart")
async def smart_poll_download_progress(
    task_id: str = Query(..., description="下载任务ID"),
    timeout: float = Query(60.0, description="轮询超时时间（秒）"),
):
    """
    智能轮询下载进度，自动调整轮询间隔
    """
    try:
        from app.utils.progress_tracker import progress_tracker
        from app.utils.enhanced_polling_strategy import polling_manager, PollingConfig
        
        logger.info(f"开始智能轮询任务进度: {task_id}")
        
        # 配置智能轮询
        config = PollingConfig(
            base_interval=2.0,
            max_interval=15.0,
            min_interval=0.5,
            max_attempts=int(timeout / 0.5),  # 基于超时时间计算最大尝试次数
        )
        
        async def check_progress():
            progress = progress_tracker.get_progress(task_id)
            if not progress:
                raise Exception(f"任务不存在: {task_id}")
            
            # 更新心跳
            progress_tracker.heartbeat(task_id)
            return progress
        
        def is_complete(progress):
            return progress.status.value in ["completed", "failed", "cancelled"]
        
        def progress_callback(progress):
            logger.debug(f"轮询进度更新: {task_id} - {progress.progress_percentage:.1f}%")
        
        def heartbeat_callback(polling_task_id):
            logger.debug(f"轮询心跳: {polling_task_id}")
        
        # 启动智能轮询
        polling_task_id = f"poll_{task_id}"
        await polling_manager.start_polling_task(
            polling_task_id,
            check_progress,
            is_complete,
            config,
            progress_callback,
            heartbeat_callback
        )
        
        # 等待结果
        final_progress = await polling_manager.get_task_result(
            polling_task_id, wait=True, timeout=timeout
        )
        
        if not final_progress:
            raise Exception("轮询超时或失败")
        
        # 获取轮询统计
        polling_stats = polling_manager.get_task_stats(polling_task_id)
        
        result_data = final_progress.to_dict()
        if polling_stats:
            result_data["polling_stats"] = polling_stats
        
        return {"code": 200, "message": "success", "data": result_data}
        
    except Exception as e:
        logger.error(f"智能轮询失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"智能轮询失败: {str(e)}",
                "data": None,
            },
        )


@router.get("/monitor/timeout")
async def get_timeout_monitor_stats():
    """
    获取超时监控统计信息
    """
    try:
        from app.utils.timeout_monitor import timeout_monitor
        
        monitor_stats = timeout_monitor.get_monitor_stats()
        recent_alerts = timeout_monitor.get_recent_alerts(minutes=60)
        
        # 转换告警为字典格式
        alerts_data = []
        for alert in recent_alerts:
            alerts_data.append({
                "task_id": alert.task_id,
                "operation_name": alert.operation_name,
                "alert_level": alert.alert_level.value,
                "message": alert.message,
                "timestamp": alert.timestamp,
                "duration": alert.duration,
                "retry_count": alert.retry_count,
            })
        
        return {
            "code": 200,
            "message": "success",
            "data": {
                "monitor_stats": monitor_stats,
                "recent_alerts": alerts_data,
            }
        }
    except Exception as e:
        logger.error(f"获取超时监控统计失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"获取超时监控统计失败: {str(e)}",
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
