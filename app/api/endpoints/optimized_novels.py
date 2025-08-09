import logging
import os
import time
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse

from app.core.config import settings
from app.models.search import SearchResponse
from app.services.optimized_novel_service import OptimizedNovelService
from app.utils.cache_manager import cache_manager
from app.utils.enhanced_http_client import http_client
from app.utils.performance_monitor import monitor_performance, performance_monitor

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter(prefix="/optimized", tags=["optimized-novels"])

# 创建优化版服务实例
optimized_service = OptimizedNovelService()


@router.get("/search", response_model=SearchResponse)
@monitor_performance("optimized_search")
async def optimized_search_novels(
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
    优化版小说搜索API

    优化特性:
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
            logger.info(f"开始优化搜索，关键词：{keyword}，maxResults={maxResults}")

            # 使用优化版搜索服务
            results = await optimized_service.optimized_search(
                keyword, max_results=maxResults
            )

            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000

            logger.info(
                f"优化搜索完成，找到 {len(results)} 条结果，耗时 {duration_ms:.1f}ms"
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
        logger.error(f"优化搜索失败: {str(e)}")
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
@monitor_performance("optimized_get_detail")
async def optimized_get_novel_detail(
    url: str = Query(..., description="小说详情页URL"),
    sourceId: int = Query(settings.DEFAULT_SOURCE_ID, description="书源ID"),
):
    """
    优化版获取小说详情API

    优化特性:
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

            book = await optimized_service.get_book_detail(url, sourceId)

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
@monitor_performance("optimized_get_toc")
async def optimized_get_novel_toc(
    url: str = Query(..., description="小说详情页URL"),
    sourceId: int = Query(settings.DEFAULT_SOURCE_ID, description="书源ID"),
):
    """
    优化版获取小说目录API

    优化特性:
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

            toc = await optimized_service.get_toc(url, sourceId)

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
@monitor_performance("optimized_download")
async def optimized_download_novel(
    background_tasks: BackgroundTasks,
    url: str = Query(..., description="小说详情页URL"),
    sourceId: int = Query(settings.DEFAULT_SOURCE_ID, description="书源ID"),
    format: str = Query("txt", description="下载格式，支持txt、epub"),
):
    """
    优化版小说下载API

    优化特性:
    - 智能并发：优化章节下载并发数
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
            logger.info(f"开始优化下载，URL：{url}，书源ID：{sourceId}，格式：{format}")

            # 使用优化版下载服务
            file_path = await optimized_service.optimized_download(
                url, sourceId, format, task_id
            )

            if not file_path or not os.path.exists(file_path):
                raise HTTPException(status_code=500, detail="下载文件生成失败")

            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            file_size = os.path.getsize(file_path)

            logger.info(
                f"优化下载完成，文件：{file_path}，大小：{file_size} 字节，耗时 {duration_ms:.1f}ms"
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
        logger.error(f"优化下载失败: {str(e)}")
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
async def get_optimized_sources():
    """
    获取所有书源信息（优化版）

    优化特性:
    - 智能缓存：缓存书源列表
    - 状态检测：显示书源可用状态
    """
    start_time = time.time()

    try:
        async with performance_monitor.monitor_operation("get_sources"):
            logger.info("开始获取书源列表")

            sources = await optimized_service.get_sources()

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
