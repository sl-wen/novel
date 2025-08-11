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
    """启动异步下载任务，立即返回任务ID（增强版）"""
    try:
        from app.utils.progress_tracker import progress_tracker
        from app.utils.timeout_manager import timeout_manager
        from app.utils.timeout_monitor import timeout_monitor
        
        # 创建任务
        task_id = progress_tracker.create_task(total_chapters=0)
        progress_tracker.start_task(task_id)
        logger.info(f"启动增强下载任务: {task_id} ({url}, source={sourceId}, format={format})")
        
        async def run_enhanced_download():
            """运行增强版下载任务"""
            try:
                # 注册超时监控
                await timeout_monitor.register_task(
                    task_id, 
                    "download_novel",
                    expected_duration=1800.0,  # 预期30分钟完成
                    custom_thresholds={
                        "warning": 600.0,    # 10分钟警告
                        "error": 1800.0,     # 30分钟错误  
                        "critical": 3600.0,  # 1小时严重
                    }
                )
                
                # 使用超时管理器执行下载
                file_path = await timeout_manager.execute_with_timeout(
                    f"download_task_{task_id}",
                    novel_service.download,
                    url, sourceId, format, task_id,
                    heartbeat_callback=lambda op_id: (
                        progress_tracker.heartbeat(task_id),
                        timeout_monitor.update_heartbeat(task_id),
                        logger.debug(f"下载任务心跳: {task_id}")
                    )
                )
                
                if file_path:
                    progress_tracker.set_file_path(task_id, file_path)
                    progress_tracker.complete_task(task_id, True)
                    logger.info(f"下载任务完成: {task_id} -> {file_path}")
                else:
                    progress_tracker.complete_task(task_id, False, "文件生成失败")
                    logger.error(f"下载任务失败: {task_id} - 文件生成失败")
                    
            except asyncio.TimeoutError:
                error_msg = f"下载任务超时: {task_id}"
                logger.error(error_msg)
                progress_tracker.complete_task(task_id, False, error_msg)
            except Exception as e:
                error_msg = f"后台下载任务失败: {str(e)}"
                logger.error(error_msg)
                progress_tracker.complete_task(task_id, False, error_msg)
            finally:
                # 清理超时监控
                try:
                    await timeout_monitor.unregister_task(task_id)
                except Exception as e:
                    logger.warning(f"清理超时监控失败: {str(e)}")
        
        # 后台执行增强版下载
        import asyncio
        asyncio.create_task(run_enhanced_download())
        
        return {"code": 202, "message": "accepted", "data": {"task_id": task_id}}
    except Exception as e:
        logger.error(f"启动下载任务失败: {str(e)}")
        return JSONResponse(status_code=500, content={"code": 500, "message": str(e), "data": None})


@router.get("/download/result")
async def get_download_result(task_id: str = Query(..., description="下载任务ID")):
    """
    获取已完成任务的下载文件
    
    注意：
    - 只有任务状态为 'completed' 时才返回文件流
    - 任务未完成时返回 202 状态码和进度信息
    - 任务失败时返回 500 状态码和错误信息
    - 建议先通过 /download/progress 确认任务完成后再调用此接口
    """
    try:
        from app.utils.progress_tracker import progress_tracker
        from fastapi.responses import StreamingResponse
        import urllib.parse
        from pathlib import Path
        
        progress = progress_tracker.get_progress(task_id)
        if not progress:
            logger.warning(f"任务不存在: {task_id}")
            return JSONResponse(status_code=404, content={"code": 404, "message": "任务不存在", "data": None})
        
        # 导入TaskStatus枚举
        from app.utils.progress_tracker import TaskStatus
        
        # 验证任务状态一致性
        progress_tracker.validate_task_status(task_id)
        
        # 添加详细的调试日志
        logger.info(f"检查任务状态: {task_id}, 状态: {progress.status.value}, 进度: {progress.progress_percentage:.1f}%")
        
        # 特殊处理：如果任务有文件路径且文件存在，但状态不是COMPLETED，尝试修复
        if (progress.status != TaskStatus.COMPLETED and 
            progress.file_path and 
            os.path.exists(progress.file_path)):
            logger.warning(f"发现状态异常的任务，尝试修复: {task_id}, 当前状态: {progress.status.value}")
            success = progress_tracker.force_complete_task(task_id, progress.file_path)
            if success:
                # 重新获取进度信息
                progress = progress_tracker.get_progress(task_id)
                logger.info(f"任务状态已修复: {task_id}, 新状态: {progress.status.value}")
        
        # 未完成返回适当的状态码和消息，而不是JSON数据
        if progress.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            logger.warning(f"任务 {task_id} 尚未完成，当前状态: {progress.status.value}")
            return JSONResponse(
                status_code=202, 
                content={
                    "code": 202, 
                    "message": f"任务还在进行中，状态：{progress.status.value}，进度：{progress.progress_percentage:.1f}%", 
                    "data": None
                }
            )
        
        if progress.status == TaskStatus.FAILED:
            logger.error(f"任务 {task_id} 已失败: {progress.error_message}")
            return JSONResponse(status_code=500, content={"code": 500, "message": progress.error_message or "任务失败", "data": progress.to_dict()})
        
        # 任务已完成，检查文件是否存在
        file_path = progress.file_path
        if not file_path or not os.path.exists(file_path):
            logger.error(f"任务 {task_id} 已完成但文件不存在: {file_path}")
            return JSONResponse(status_code=500, content={"code": 500, "message": "文件不存在或尚未生成", "data": progress.to_dict()})
        
        logger.info(f"返回已完成任务的文件: {task_id} -> {file_path}")
        
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
async def get_download_progress_smart(
    task_id: str = Query(..., description="下载任务ID"),
    timeout: int = Query(120, description="轮询超时时间（秒）")
):
    """
    智能轮询下载进度（推荐使用）
    自动调整轮询间隔，基于进度智能优化，减少无效请求
    """
    try:
        logger.info(f"智能轮询下载进度，任务ID：{task_id}, 超时：{timeout}秒")
        
        from app.utils.progress_tracker import progress_tracker
        from app.utils.timeout_manager import timeout_manager
        from app.utils.enhanced_polling_strategy import polling_manager, PollingConfig, PollingStrategy
        
        # 配置智能轮询
        config = PollingConfig(
            strategy=PollingStrategy.SMART_POLLING,
            base_interval=2.0,
            max_interval=min(30.0, timeout / 10),  # 动态调整最大间隔
            min_interval=0.5,
            max_attempts=max(50, timeout // 2)  # 基于超时时间计算最大尝试次数
        )
        
        # 定义检查函数
        def check_progress():
            progress = progress_tracker.get_progress(task_id)
            if not progress:
                raise ValueError(f"任务不存在: {task_id}")
            
            # 更新心跳
            progress_tracker.heartbeat(task_id)
            return progress
        
        # 定义完成检查函数
        def is_completed(progress):
            from app.utils.progress_tracker import TaskStatus
            return progress.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
        
        # 启动智能轮询
        try:
            polling_task_id = await polling_manager.start_polling_task(
                f"smart_poll_{task_id}",
                check_function=check_progress,
                completion_check=is_completed,
                config=config
            )
            
            # 等待轮询完成或超时
            final_progress = await asyncio.wait_for(
                polling_manager.wait_for_completion(polling_task_id),
                timeout=timeout
            )
            
            # 获取轮询统计
            polling_stats = polling_manager.get_task_stats(polling_task_id)
            
            # 获取超时统计信息
            timeout_stats = timeout_manager.get_stats(f"download_task_{task_id}")
            
            result_data = final_progress.to_dict()
            if timeout_stats:
                result_data["timeout_stats"] = timeout_stats
            if polling_stats:
                result_data["polling_stats"] = polling_stats
            
            return {"code": 200, "message": "success", "data": result_data}
            
        except asyncio.TimeoutError:
            # 智能轮询超时，返回当前进度
            logger.warning(f"智能轮询超时: {task_id}")
            progress = progress_tracker.get_progress(task_id)
            if progress:
                result_data = progress.to_dict()
                result_data["polling_timeout"] = True
                return {"code": 200, "message": "polling_timeout", "data": result_data}
            else:
                return JSONResponse(
                    status_code=404,
                    content={"code": 404, "message": f"任务不存在: {task_id}", "data": None}
                )
        
    except Exception as e:
        logger.error(f"智能轮询下载进度失败: {str(e)}")
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


@router.get("/debug/task")
async def debug_task_status(task_id: str = Query(..., description="下载任务ID")):
    """
    调试端点：获取任务的详细状态信息
    用于排查任务状态异常问题
    """
    try:
        from app.utils.progress_tracker import progress_tracker, TaskStatus
        from app.utils.timeout_monitor import timeout_monitor
        
        progress = progress_tracker.get_progress(task_id)
        if not progress:
            return JSONResponse(
                status_code=404, 
                content={
                    "code": 404, 
                    "message": f"任务不存在: {task_id}", 
                    "data": None
                }
            )
        
        # 获取所有任务信息
        all_tasks = progress_tracker.get_all_tasks()
        
        # 获取超时监控信息
        monitor_info = None
        try:
            # 检查timeout_monitor中是否有这个任务
            if hasattr(timeout_monitor, 'monitored_tasks'):
                monitor_info = timeout_monitor.monitored_tasks.get(task_id)
        except Exception as e:
            logger.warning(f"获取超时监控信息失败: {str(e)}")
        
        debug_data = {
            "task_id": task_id,
            "progress_info": progress.to_dict(),
            "raw_status": progress.status.value,
            "raw_progress": progress.progress_percentage,
            "file_exists": os.path.exists(progress.file_path) if progress.file_path else False,
            "file_path": progress.file_path,
            "total_tasks_count": len(all_tasks),
            "monitor_info": monitor_info,
            "task_in_monitor": task_id in (timeout_monitor.monitored_tasks if hasattr(timeout_monitor, 'monitored_tasks') else {}),
        }
        
        return {"code": 200, "message": "debug_info", "data": debug_data}
        
    except Exception as e:
        logger.error(f"调试任务状态失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"调试失败: {str(e)}",
                "data": None,
            },
        )


@router.get("/debug/tasks")
async def debug_all_tasks():
    """
    调试端点：获取所有任务的状态信息
    用于排查任务管理问题
    """
    try:
        from app.utils.progress_tracker import progress_tracker
        
        all_tasks = progress_tracker.get_all_tasks()
        
        tasks_data = []
        for task_id, progress in all_tasks.items():
            task_data = progress.to_dict()
            task_data["file_exists"] = os.path.exists(progress.file_path) if progress.file_path else False
            tasks_data.append(task_data)
        
        return {
            "code": 200, 
            "message": "success", 
            "data": {
                "total_tasks": len(tasks_data),
                "tasks": tasks_data
            }
        }
        
    except Exception as e:
        logger.error(f"获取所有任务状态失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"调试失败: {str(e)}",
                "data": None,
            },
        )


@router.post("/debug/recover-tasks")
async def recover_broken_tasks():
    """
    调试端点：恢复状态异常的任务
    检查所有任务，如果发现有文件但状态不正确的任务，自动修复
    """
    try:
        from app.utils.progress_tracker import progress_tracker, TaskStatus
        
        all_tasks = progress_tracker.get_all_tasks()
        recovered_tasks = []
        
        for task_id, progress in all_tasks.items():
            # 检查是否有文件但状态不是COMPLETED的任务
            if (progress.status != TaskStatus.COMPLETED and 
                progress.file_path and 
                os.path.exists(progress.file_path)):
                
                logger.info(f"发现需要恢复的任务: {task_id}, 状态: {progress.status.value}")
                success = progress_tracker.force_complete_task(task_id, progress.file_path)
                if success:
                    recovered_tasks.append({
                        "task_id": task_id,
                        "old_status": progress.status.value,
                        "new_status": "completed",
                        "file_path": progress.file_path
                    })
        
        return {
            "code": 200, 
            "message": "recovery_completed", 
            "data": {
                "recovered_count": len(recovered_tasks),
                "recovered_tasks": recovered_tasks
            }
        }
        
    except Exception as e:
        logger.error(f"恢复任务状态失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"恢复失败: {str(e)}",
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
