import logging
import os
import time
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse

from app.core.config import settings
from app.models.search import SearchResponse
from app.services.novel_service import NovelService
from app.utils.cache_manager import cache_manager
from app.utils.enhanced_http_client import http_client
from app.utils.performance_monitor import monitor_performance, performance_monitor

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter(prefix="/optimized", tags=["novels"])

# 创建服务实例
novel_service = NovelService()


@router.get("/search", response_model=SearchResponse)
@monitor_performance("search")
async def search_novels(
    request: Request,
    keyword: str = Query(None, description="搜索关键词（书名或作者名）"),
    maxResults: int = Query(
        30,
        ge=1,
        le=100,
        description="最大返回结果数，默认30，最大100",
    ),
):
    """
    小说搜索API

    特性:
    - 智能缓存：自动缓存搜索结果
    - 并发搜索：同时搜索多个书源
    - 超时控制：避免长时间等待
    - 结果去重：智能去除重复结果
    - 性能监控：实时监控搜索性能
    """
    if not keyword:
        raise HTTPException(status_code=400, detail="搜索关键词不能为空")

    start_time = time.time()

    try:
        async with performance_monitor.monitor_operation(
            "search_novels", {"keyword": keyword, "max_results": maxResults}
        ):
            logger.info(f"开始搜索，关键词：{keyword}，maxResults={maxResults}")

            # 使用搜索服务
            results = await novel_service.search(keyword, max_results=maxResults)

            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000

            logger.info(
                f"搜索完成，找到 {len(results)} 条结果，耗时 {duration_ms:.1f}ms"
            )

            return {
                "code": 200,
                "message": "success",
                "data": results,
                "meta": {
                    "duration_ms": round(duration_ms, 1),
                    "total_results": len(results),
                    "cached": False,  # 这里可以根据实际情况设置
                },
            }

    except Exception as e:
        logger.error(f"搜索失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"搜索失败: {str(e)}",
                "data": None,
                "meta": {
                    "duration_ms": round((time.time() - start_time) * 1000, 1),
                    "error": str(e),
                },
            },
        )


@router.get("/detail")
@monitor_performance("get_detail")
async def get_novel_detail(
    url: str = Query(..., description="小说详情页URL"),
    sourceId: int = Query(settings.DEFAULT_SOURCE_ID, description="书源ID"),
):
    """
    获取小说详情API

    特性:
    - 智能缓存：缓存书籍详情
    - 快速响应：优化网络请求
    - 错误重试：自动重试失败请求
    """
    start_time = time.time()

    try:
        async with performance_monitor.monitor_operation(
            "get_book_detail", {"url": url, "source_id": sourceId}
        ):
            logger.info(f"开始获取小说详情，URL：{url}，书源ID：{sourceId}")

            book = await novel_service.get_book_detail(url, sourceId)

            if not book:
                raise HTTPException(status_code=404, detail="未找到小说详情")

            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000

            logger.info(f"获取小说详情成功：{book.title}，耗时 {duration_ms:.1f}ms")

            return {
                "code": 200,
                "message": "success",
                "data": book,
                "meta": {"duration_ms": round(duration_ms, 1), "source_id": sourceId},
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取小说详情失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"获取小说详情失败: {str(e)}",
                "data": None,
                "meta": {
                    "duration_ms": round((time.time() - start_time) * 1000, 1),
                    "error": str(e),
                },
            },
        )


@router.get("/toc")
@monitor_performance("get_toc")
async def get_novel_toc(
    url: str = Query(..., description="小说详情页URL"),
    sourceId: int = Query(settings.DEFAULT_SOURCE_ID, description="书源ID"),
):
    """
    获取小说目录API

    特性:
    - 智能缓存：缓存目录信息
    - 并发处理：快速解析目录
    - 数据验证：验证目录完整性
    """
    start_time = time.time()

    try:
        async with performance_monitor.monitor_operation(
            "get_toc", {"url": url, "source_id": sourceId}
        ):
            logger.info(f"开始获取小说目录，URL：{url}，书源ID：{sourceId}")

            toc = await novel_service.get_toc(url, sourceId)

            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000

            logger.info(f"获取小说目录成功，共 {len(toc)} 章，耗时 {duration_ms:.1f}ms")

            return {
                "code": 200,
                "message": "success",
                "data": toc,
                "meta": {
                    "duration_ms": round(duration_ms, 1),
                    "total_chapters": len(toc),
                    "source_id": sourceId,
                },
            }

    except Exception as e:
        logger.error(f"获取小说目录失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"获取小说目录失败: {str(e)}",
                "data": None,
                "meta": {
                    "duration_ms": round((time.time() - start_time) * 1000, 1),
                    "error": str(e),
                },
            },
        )


@router.get("/download")
@monitor_performance("download")
async def download_novel(
    background_tasks: BackgroundTasks,
    url: str = Query(..., description="小说详情页URL"),
    sourceId: int = Query(settings.DEFAULT_SOURCE_ID, description="书源ID"),
    format: str = Query("txt", description="下载格式，支持txt、epub"),
    addChapterNumbers: bool = Query(
        None, description="是否添加章节序号（第X章），默认自动检测"
    ),
    chapterPrefix: str = Query("第", description="章节序号前缀，默认'第'"),
    chapterSuffix: str = Query("章", description="章节序号后缀，默认'章'"),
):
    """
    小说下载API

    特性:
    - 智能并发：章节下载并发控制
    - 断点续传：支持下载恢复
    - 进度跟踪：实时跟踪下载进度
    - 错误恢复：自动重试失败章节
    - 内存优化：流式处理大文件
    """
    start_time = time.time()

    try:
        # 生成任务ID用于跟踪下载进度
        import uuid

        from app.utils.progress_tracker import progress_tracker

        task_id = str(uuid.uuid4())
        # 在优化端点也创建并启动任务，避免后续进度更新时出现“任务不存在”
        progress_tracker.create_task(total_chapters=0, task_id=task_id)
        progress_tracker.start_task(task_id)

        async with performance_monitor.monitor_operation(
            "download_novel",
            {"url": url, "source_id": sourceId, "format": format, "task_id": task_id},
        ):
            logger.info(f"开始下载，URL：{url}，书源ID：{sourceId}，格式：{format}")

            # 准备章节格式化选项
            format_options = {}
            if addChapterNumbers is not None:
                format_options["add_numbers"] = addChapterNumbers
            if chapterPrefix:
                format_options["prefix"] = chapterPrefix
            if chapterSuffix:
                format_options["suffix"] = chapterSuffix

            # 使用下载服务
            file_path = await novel_service.download(
                url, sourceId, format, task_id, format_options
            )

            if not file_path or not os.path.exists(file_path):
                raise HTTPException(status_code=500, detail="下载文件生成失败")

            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            file_size = os.path.getsize(file_path)

            logger.info(
                f"下载完成，文件：{file_path}，大小：{file_size} 字节，耗时 {duration_ms:.1f}ms"
            )

            # 设置清理任务
            def cleanup_file():
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.info(f"清理临时文件：{file_path}")
                except Exception as e:
                    logger.error(f"清理文件失败：{str(e)}")

            # 延迟清理文件（给用户足够时间下载）
            background_tasks.add_task(cleanup_file)

            # 返回文件
            import urllib.parse

            filename = os.path.basename(file_path)
            encoded_filename = urllib.parse.quote(filename, safe="")
            return FileResponse(
                path=file_path,
                filename=filename,
                media_type="application/octet-stream",
                headers={
                    # RFC 5987 encoding to avoid non-Latin-1 header errors
                    "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
                    "X-Download-Duration-MS": str(round(duration_ms, 1)),
                    "X-File-Size": str(file_size),
                    "X-Task-ID": task_id,
                },
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"下载失败: {str(e)}",
                "data": None,
                "meta": {
                    "duration_ms": round((time.time() - start_time) * 1000, 1),
                    "error": str(e),
                },
            },
        )


@router.get("/sources")
@monitor_performance("get_sources")
async def get_sources():
    """
    获取所有书源信息

    特性:
    - 智能缓存：缓存书源列表
    - 状态检测：显示书源可用状态
    """
    start_time = time.time()

    try:
        async with performance_monitor.monitor_operation("get_sources"):
            logger.info("开始获取书源列表")

            sources = await novel_service.get_sources()

            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000

            logger.info(
                f"获取书源列表成功，共 {len(sources)} 个书源，耗时 {duration_ms:.1f}ms"
            )

            return {
                "code": 200,
                "message": "success",
                "data": sources,
                "meta": {
                    "duration_ms": round(duration_ms, 1),
                    "total_sources": len(sources),
                },
            }

    except Exception as e:
        logger.error(f"获取书源列表失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"获取书源列表失败: {str(e)}",
                "data": None,
                "meta": {
                    "duration_ms": round((time.time() - start_time) * 1000, 1),
                    "error": str(e),
                },
            },
        )


@router.get("/performance")
async def get_performance_stats():
    """
    获取性能统计信息

    返回系统性能指标，包括：
    - 操作统计
    - 慢查询信息
    - 缓存统计
    - 连接统计
    """
    try:
        # 获取性能监控统计
        perf_stats = performance_monitor.get_summary()

        # 获取缓存统计
        cache_stats = cache_manager.get_cache_stats()

        # 获取HTTP客户端统计
        http_stats = http_client.get_stats()

        # 获取最近的慢查询
        slow_operations = performance_monitor.get_slow_operations(limit=10)
        slow_ops_data = [
            {
                "operation_name": op.operation_name,
                "duration_ms": op.duration_ms,
                "timestamp": op.end_time,
                "success": op.success,
                "error_message": op.error_message,
            }
            for op in slow_operations
        ]

        return {
            "code": 200,
            "message": "success",
            "data": {
                "performance": perf_stats,
                "cache": cache_stats,
                "http": http_stats,
                "slow_operations": slow_ops_data,
            },
        }

    except Exception as e:
        logger.error(f"获取性能统计失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"获取性能统计失败: {str(e)}",
                "data": None,
            },
        )


@router.post("/cache/clear")
async def clear_cache():
    """
    清理缓存
    """
    try:
        # 清理过期缓存
        cleared_count = await cache_manager.clear_expired()

        return {
            "code": 200,
            "message": "success",
            "data": {"cleared_items": cleared_count, "timestamp": time.time()},
        }

    except Exception as e:
        logger.error(f"清理缓存失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": f"清理缓存失败: {str(e)}", "data": None},
        )


@router.post("/download/start")
@monitor_performance("download_start")
async def start_download(
    url: str = Query(..., description="小说详情页URL"),
    sourceId: int = Query(settings.DEFAULT_SOURCE_ID, description="书源ID"),
    format: str = Query("txt", description="下载格式，支持txt、epub"),
    addChapterNumbers: bool = Query(
        None, description="是否添加章节序号（第X章），默认自动检测"
    ),
    chapterPrefix: str = Query("第", description="章节序号前缀，默认'第'"),
    chapterSuffix: str = Query("章", description="章节序号后缀，默认'章'"),
):
    """
    启动异步下载任务，立即返回任务ID

    特性:
    - 任务管理：智能任务调度
    - 进度跟踪：实时下载进度
    - 错误处理：完善的错误恢复
    """
    try:
        import uuid

        from app.utils.progress_tracker import progress_tracker

        # 创建任务
        task_id = str(uuid.uuid4())
        progress_tracker.create_task(total_chapters=0, task_id=task_id)
        progress_tracker.start_task(task_id)
        logger.info(
            f"启动下载任务: {task_id} ({url}, source={sourceId}, format={format})"
        )

        async def run_download():
            try:
                # 准备章节格式化选项
                format_options = {}
                if addChapterNumbers is not None:
                    format_options["add_numbers"] = addChapterNumbers
                if chapterPrefix:
                    format_options["prefix"] = chapterPrefix
                if chapterSuffix:
                    format_options["suffix"] = chapterSuffix

                file_path = await novel_service.download(
                    url,
                    sourceId,
                    format,
                    task_id=task_id,
                    format_options=format_options,
                )
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

        return JSONResponse(
            status_code=202,
            content={"code": 202, "message": "accepted", "data": {"task_id": task_id}},
        )
    except Exception as e:
        logger.error(f"启动下载任务失败: {str(e)}")
        return JSONResponse(
            status_code=500, content={"code": 500, "message": str(e), "data": None}
        )


@router.get("/download/progress")
@monitor_performance("download_progress")
async def get_download_progress(task_id: str = Query(..., description="下载任务ID")):
    """
    获取下载进度

    特性:
    - 详细进度：章节级别的进度信息
    - 性能指标：下载速度和质量统计
    - 错误信息：详细的错误诊断
    """
    try:
        logger.info(f"获取下载进度，任务ID：{task_id}")

        from app.utils.progress_tracker import progress_tracker

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

        return {"code": 200, "message": "success", "data": progress.to_dict()}
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


@router.get("/download/result")
@monitor_performance("download_result")
async def get_download_result(task_id: str = Query(..., description="下载任务ID")):
    """
    获取已完成任务的文件（若未完成则返回状态）

    特性:
    - 流式传输：高效的文件传输
    - 智能缓存：避免重复传输
    - 自动清理：防止磁盘空间浪费
    - 文件就绪检查：确保文件完全生成后再返回
    """
    try:
        import asyncio
        import urllib.parse
        from pathlib import Path

        from fastapi.responses import StreamingResponse

        from app.utils.progress_tracker import progress_tracker

        progress = progress_tracker.get_progress(task_id)
        if not progress:
            return JSONResponse(
                status_code=404,
                content={"code": 404, "message": "任务不存在", "data": None},
            )

        # 失败直接返回错误
        if progress.status == progress.status.FAILED:
            return JSONResponse(
                status_code=500,
                content={
                    "code": 500,
                    "message": progress.error_message or "任务失败",
                    "data": progress.to_dict(),
                },
            )

        file_path = progress.file_path

        # 允许在状态仍为 RUNNING 但进度达到 100% 且文件已生成时直接返回文件
        ready_to_stream = False
        if file_path and os.path.exists(file_path):
            try:
                # 条件1：显式完成
                if progress.status == progress.status.COMPLETED:
                    ready_to_stream = True
                # 条件2：进度达到或超过100%
                elif progress.progress_percentage >= 100.0:
                    ready_to_stream = True
                # 条件3：章节数达到总数（避免浮点精度问题）
                elif (
                    progress.total_chapters > 0
                    and progress.completed_chapters >= progress.total_chapters
                ):
                    ready_to_stream = True
            except Exception:
                ready_to_stream = False

        # 未完成且未达到就绪条件，返回状态
        if progress.status not in [progress.status.COMPLETED, progress.status.FAILED] and not ready_to_stream:
            return {"code": 200, "message": "running", "data": progress.to_dict()}

        if not file_path:
            return JSONResponse(
                status_code=500,
                content={
                    "code": 500,
                    "message": "文件路径未设置",
                    "data": progress.to_dict(),
                },
            )

        # 文件就绪检查：确保文件存在且完全写入完成
        async def is_file_ready(
            file_path: str, max_retries: int = 20, retry_delay: float = 0.5
        ) -> bool:
            """检查文件是否已经完全写入完成"""
            # 对EPUB文件使用更多重试次数和更长延迟
            if file_path.lower().endswith(".epub"):
                max_retries = 25  # 进一步增加EPUB文件的重试次数
                retry_delay = 0.8  # 增加延迟时间

            logger.info(f"开始文件就绪检查: {file_path} (最大重试次数: {max_retries})")

            for attempt in range(max_retries):
                try:
                    if not os.path.exists(file_path):
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"文件不存在 (尝试 {attempt + 1}/{max_retries}): {file_path}"
                            )
                            await asyncio.sleep(retry_delay)
                            continue
                        logger.error(f"文件最终不存在: {file_path}")
                        return False

                    # 检查文件是否可以正常读取且大小稳定
                    file_obj = Path(file_path)
                    initial_size = file_obj.stat().st_size

                    # 如果文件大小为0，说明还在写入中
                    if initial_size == 0:
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"文件大小为0 (尝试 {attempt + 1}/{max_retries}): {file_path}"
                            )
                            await asyncio.sleep(retry_delay)
                            continue
                        logger.error(f"文件大小始终为0: {file_path}")
                        return False

                    # 等待文件写入稳定 - 增加等待时间
                    stability_wait = 0.8 if file_path.lower().endswith(".epub") else 0.3
                    await asyncio.sleep(stability_wait)

                    # 检查文件大小是否稳定
                    try:
                        final_size = file_obj.stat().st_size
                    except (FileNotFoundError, OSError) as e:
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"文件状态检查失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}"
                            )
                            await asyncio.sleep(retry_delay)
                            continue
                        logger.error(f"文件状态检查最终失败: {str(e)}")
                        return False

                    # 如果文件大小不稳定，继续等待
                    if initial_size != final_size:
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"文件大小不稳定 (尝试 {attempt + 1}/{max_retries}): {initial_size} -> {final_size}"
                            )
                            await asyncio.sleep(retry_delay)
                            continue
                        logger.error(
                            f"文件大小始终不稳定: {initial_size} -> {final_size}"
                        )
                        return False

                    # 尝试打开和读取文件
                    try:
                        with open(file_path, "rb") as f:
                            # 对于EPUB文件，进行更详细的验证
                            if file_path.lower().endswith(".epub"):
                                # 读取并验证EPUB文件头
                                header = f.read(4)
                                if header != b"PK\x03\x04":
                                    if attempt < max_retries - 1:
                                        logger.warning(
                                            f"EPUB文件头验证失败 (尝试 {attempt + 1}/{max_retries}): {header}"
                                        )
                                        await asyncio.sleep(retry_delay)
                                        continue
                                    logger.error(f"EPUB文件头最终验证失败: {header}")
                                    return False

                                # 尝试读取更多内容确保文件完整
                                f.seek(0)
                                content_sample = f.read(16384)  # 读取更多内容
                                if len(content_sample) < 16384 and final_size > 16384:
                                    if attempt < max_retries - 1:
                                        logger.warning(
                                            f"EPUB文件内容读取不完整 (尝试 {attempt + 1}/{max_retries})"
                                        )
                                        await asyncio.sleep(retry_delay)
                                        continue
                                    logger.error("EPUB文件内容读取最终不完整")
                                    return False
                            else:
                                # TXT文件验证 - 读取更多内容确保完整性
                                content_sample = f.read(4096)
                                if len(content_sample) == 0:
                                    if attempt < max_retries - 1:
                                        logger.warning(
                                            f"TXT文件内容为空 (尝试 {attempt + 1}/{max_retries})"
                                        )
                                        await asyncio.sleep(retry_delay)
                                        continue
                                    logger.error("TXT文件内容为空")
                                    return False

                        logger.info(
                            f"文件就绪检查通过: {file_path} (大小: {final_size} 字节)"
                        )
                        return True

                    except (IOError, OSError, PermissionError) as e:
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"文件读取检查失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}"
                            )
                            await asyncio.sleep(retry_delay)
                            continue
                        logger.error(f"文件读取检查最终失败: {str(e)}")
                        return False

                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"文件检查异常 (尝试 {attempt + 1}/{max_retries}): {str(e)}"
                        )
                        await asyncio.sleep(retry_delay)
                        continue
                    logger.error(f"文件检查最终异常: {str(e)}")
                    return False

            logger.error(f"文件就绪检查最终失败: {file_path}")
            return False

        # 执行文件就绪检查
        if not await is_file_ready(file_path):
            return JSONResponse(
                status_code=500,
                content={
                    "code": 500,
                    "message": "文件不存在或尚未生成完成",
                    "data": progress.to_dict(),
                },
            )

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
                "X-Task-ID": task_id,
            },
        )
    except Exception as e:
        logger.error(f"获取下载结果失败: {str(e)}")
        return JSONResponse(
            status_code=500, content={"code": 500, "message": str(e), "data": None}
        )


@router.get("/health")
async def health_check():
    """
    健康检查端点

    返回系统健康状态和关键指标
    """
    try:
        # 获取系统状态
        perf_summary = performance_monitor.get_summary()
        cache_stats = cache_manager.get_cache_stats()
        http_stats = http_client.get_stats()

        # 计算健康分数
        health_score = 100

        # 根据成功率调整健康分数
        if perf_summary["overall_success_rate"] < 90:
            health_score -= 20
        elif perf_summary["overall_success_rate"] < 95:
            health_score -= 10

        # 根据慢查询数量调整健康分数
        if perf_summary["slow_operations_count"] > 100:
            health_score -= 15
        elif perf_summary["slow_operations_count"] > 50:
            health_score -= 5

        # 确定健康状态
        if health_score >= 90:
            status = "healthy"
        elif health_score >= 70:
            status = "warning"
        else:
            status = "unhealthy"

        return {
            "code": 200,
            "message": "success",
            "data": {
                "status": status,
                "health_score": health_score,
                "timestamp": time.time(),
                "metrics": {
                    "performance": perf_summary,
                    "cache": cache_stats,
                    "http": http_stats,
                },
            },
        }

    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return {
            "code": 500,
            "message": f"健康检查失败: {str(e)}",
            "data": {"status": "error", "health_score": 0, "timestamp": time.time()},
        }

