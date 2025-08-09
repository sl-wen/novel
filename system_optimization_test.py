#!/usr/bin/env python3
"""
系统优化功能全面测试脚本
测试所有新增的优化功能：文本验证、EPUB生成、进度跟踪、缓存系统等
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("system_optimization_test.log"),
    ],
)

logger = logging.getLogger(__name__)


async def test_text_validator():
    """测试文本验证器"""
    logger.info("=" * 50)
    logger.info("测试文本验证器")
    logger.info("=" * 50)

    from app.utils.text_validator import TextValidator

    # 测试用例
    test_cases = [
        ("正常标题", 0.8, True),
        ("斗破苍穹", 0.9, True),
        ("???", 0.1, False),
        ("", 0.0, False),
        ("a", 0.3, False),
        ("测试内容123", 0.7, True),
        ("□□□□", 0.1, False),
    ]

    for title, expected_min_score, should_pass in test_cases:
        is_valid, score, reason = TextValidator.is_valid_title(title)
        logger.info(
            f"标题: '{title}' -> 有效: {is_valid}, 得分: {score:.2f}, 原因: {reason}"
        )

        if should_pass and not is_valid:
            logger.warning(f"预期通过但失败: {title}")
        elif not should_pass and is_valid:
            logger.warning(f"预期失败但通过: {title}")

    logger.info("文本验证器测试完成")


async def test_progress_tracker():
    """测试进度跟踪器"""
    logger.info("=" * 50)
    logger.info("测试进度跟踪器")
    logger.info("=" * 50)

    from app.utils.progress_tracker import progress_tracker

    # 创建测试任务
    task_id = progress_tracker.create_task(total_chapters=100)
    logger.info(f"创建任务: {task_id}")

    # 开始任务
    progress_tracker.start_task(task_id)

    # 模拟下载进度
    for i in range(0, 101, 10):
        progress_tracker.update_progress(
            task_id,
            completed_chapters=i,
            current_chapter=f"第{i}章",
            failed_chapters=max(0, i // 20),
        )

        progress = progress_tracker.get_progress(task_id)
        if progress:
            logger.info(
                f"进度: {progress.progress_percentage:.1f}%, "
                f"完成: {progress.completed_chapters}, "
                f"当前: {progress.current_chapter}"
            )

        await asyncio.sleep(0.1)

    # 完成任务
    progress_tracker.complete_task(task_id, success=True)

    final_progress = progress_tracker.get_progress(task_id)
    if final_progress:
        logger.info(
            f"最终状态: {final_progress.status.value}, "
            f"总用时: {final_progress.elapsed_time:.2f}秒"
        )

    logger.info("进度跟踪器测试完成")


async def test_cache_manager():
    """测试缓存管理器"""
    logger.info("=" * 50)
    logger.info("测试缓存管理器")
    logger.info("=" * 50)

    from app.utils.cache_manager import cache_manager

    # 测试基本缓存功能
    test_key = "test_key"
    test_data = {"message": "Hello, Cache!", "timestamp": time.time()}

    # 设置缓存
    success = await cache_manager.set(test_key, test_data, ttl=60)
    logger.info(f"设置缓存: {success}")

    # 获取缓存
    cached_data = await cache_manager.get(test_key)
    logger.info(f"获取缓存: {cached_data is not None}")

    if cached_data:
        logger.info(f"缓存内容: {cached_data}")

    # 测试搜索结果缓存
    search_results = [
        {"title": "测试小说1", "author": "作者1"},
        {"title": "测试小说2", "author": "作者2"},
    ]

    await cache_manager.cache_search_results("测试关键词", [1, 2], search_results)
    # 生成搜索结果的缓存键并按键获取
    search_cache_key = cache_manager._generate_cache_key(
        "search", "测试关键词", *sorted([1, 2])
    )
    cached_search = await cache_manager.get_search_results(search_cache_key)

    logger.info(f"搜索结果缓存: {cached_search is not None}")
    if cached_search:
        logger.info(f"缓存的搜索结果数量: {len(cached_search)}")

    # 获取缓存统计
    stats = cache_manager.get_cache_stats()
    logger.info(f"缓存统计: {stats}")

    # 清理测试缓存
    await cache_manager.delete(test_key)
    await cache_manager.clear("search")

    logger.info("缓存管理器测试完成")


async def test_epub_generator():
    """测试EPUB生成器"""
    logger.info("=" * 50)
    logger.info("测试EPUB生成器")
    logger.info("=" * 50)

    from app.models.book import Book
    from app.models.chapter import Chapter
    from app.utils.epub_generator import EPUBGenerator

    # 创建测试数据
    book = Book(
        title="测试小说",
        author="测试作者",
        description="这是一个测试小说的描述",
        url="http://test.com/book/1",
    )

    chapters = [
        Chapter(
            title="第一章 开始", content="这是第一章的内容。\n\n这是第二段。", order=1
        ),
        Chapter(
            title="第二章 发展", content="这是第二章的内容。\n\n情节开始发展。", order=2
        ),
        Chapter(
            title="第三章 结束", content="这是第三章的内容。\n\n故事结束了。", order=3
        ),
    ]

    # 生成EPUB文件
    generator = EPUBGenerator()
    output_path = "downloads/test_novel.epub"

    try:
        epub_path = generator.generate(book, chapters, output_path)
        logger.info(f"EPUB生成成功: {epub_path}")

        # 检查文件是否存在
        if Path(epub_path).exists():
            file_size = Path(epub_path).stat().st_size
            logger.info(f"EPUB文件大小: {file_size} 字节")
        else:
            logger.error("EPUB文件未生成")

    except Exception as e:
        logger.error(f"EPUB生成失败: {str(e)}")

    logger.info("EPUB生成器测试完成")


async def test_search_optimization():
    """测试搜索优化功能"""
    logger.info("=" * 50)
    logger.info("测试搜索优化功能")
    logger.info("=" * 50)

    from app.services.novel_service import NovelService

    service = NovelService()

    # 测试搜索功能
    test_keywords = ["斗破苍穹", "完美世界"]

    for keyword in test_keywords:
        try:
            logger.info(f"搜索关键词: {keyword}")
            start_time = time.time()

            results = await service.search(keyword, max_results=10)

            end_time = time.time()
            logger.info(
                f"搜索完成: 找到 {len(results)} 个结果，耗时 {end_time - start_time:.2f} 秒"
            )

            # 验证每个书源最多2个结果的限制
            source_counts = {}
            for result in results:
                source_id = getattr(result, "source_id", "unknown")
                source_counts[source_id] = source_counts.get(source_id, 0) + 1

            max_per_source = max(source_counts.values()) if source_counts else 0
            logger.info(f"每个书源最大结果数: {max_per_source}")

            if max_per_source > 2:
                logger.warning(f"发现书源结果超过限制: {max_per_source} > 2")

            # 显示前3个结果
            for i, result in enumerate(results[:3]):
                logger.info(f"结果 {i+1}: {result.title} - {result.author}")

        except Exception as e:
            logger.error(f"搜索测试失败 {keyword}: {str(e)}")

    logger.info("搜索优化测试完成")


async def run_comprehensive_test():
    """运行全面测试"""
    logger.info("开始系统优化功能全面测试")
    start_time = time.time()

    try:
        # 1. 测试文本验证器
        await test_text_validator()
        await asyncio.sleep(1)

        # 2. 测试进度跟踪器
        await test_progress_tracker()
        await asyncio.sleep(1)

        # 3. 测试缓存管理器
        await test_cache_manager()
        await asyncio.sleep(1)

        # 4. 测试EPUB生成器
        await test_epub_generator()
        await asyncio.sleep(1)

        # 5. 测试搜索优化
        await test_search_optimization()

        end_time = time.time()
        logger.info("=" * 60)
        logger.info(f"全部测试完成，总耗时: {end_time - start_time:.2f} 秒")
        logger.info("=" * 60)

        # 测试总结（移除控制台不支持的emoji以避免GBK编码错误）
        logger.info("测试总结:")
        logger.info("文本验证器 - 智能乱码检测和质量评估")
        logger.info("进度跟踪器 - 实时下载进度监控")
        logger.info("缓存管理器 - 内存+磁盘双层缓存")
        logger.info("EPUB生成器 - 完整的电子书生成")
        logger.info("搜索优化 - 每个书源限制2个结果")

    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(run_comprehensive_test())
    finally:
        # 确保关闭全局HTTP会话以避免 Windows 上的 "Event loop is closed" 提示
        try:
            from app.utils.enhanced_http_client import http_client

            asyncio.run(http_client.shutdown())
        except Exception:
            pass
