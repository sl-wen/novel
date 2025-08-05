#!/usr/bin/env python3
"""
增强版下载功能测试脚本
测试优化后的下载功能，包括错误处理、恢复机制和性能改进
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from app.core.enhanced_crawler import EnhancedCrawler, DownloadConfig
from app.core.config import settings
from app.services.novel_service import NovelService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('enhanced_download_test.log')
    ]
)

logger = logging.getLogger(__name__)


async def test_enhanced_download():
    """测试增强版下载功能"""
    logger.info("=" * 60)
    logger.info("开始测试增强版下载功能")
    logger.info("=" * 60)
    
    # 创建服务实例
    service = NovelService()
    
    # 检查书源数量
    sources_count = len(service.sources)
    logger.info(f"当前加载的书源数量: {sources_count}")
    
    if sources_count == 0:
        logger.error("没有可用的书源，无法进行测试")
        return
    
    # 测试搜索功能
    logger.info("-" * 40)
    logger.info("步骤1: 测试搜索功能")
    logger.info("-" * 40)
    
    try:
        results = await service.search("完美世界", max_results=5)
        logger.info(f"搜索结果数量: {len(results)}")
        
        if not results:
            logger.error("搜索未找到结果，无法继续测试")
            return
        
        # 选择第一个结果进行下载测试
        book = results[0]
        logger.info(f"选择测试书籍: 《{book.title}》 - {book.author}")
        logger.info(f"书籍URL: {book.url}")
        logger.info(f"书源ID: {book.source_id}")
        
    except Exception as e:
        logger.error(f"搜索测试失败: {str(e)}")
        return
    
    # 测试目录获取
    logger.info("-" * 40)
    logger.info("步骤2: 测试目录获取")
    logger.info("-" * 40)
    
    try:
        toc = await service.get_toc(book.url, book.source_id)
        logger.info(f"目录章节数量: {len(toc)}")
        
        if not toc:
            logger.warning("目录为空，将测试增强版爬虫的多策略解析")
        else:
            logger.info("前5个章节:")
            for i, chapter in enumerate(toc[:5]):
                logger.info(f"  {i+1}. {chapter.title}")
        
    except Exception as e:
        logger.error(f"目录获取失败: {str(e)}")
        logger.info("将使用增强版爬虫的多策略解析")
    
    # 测试增强版下载功能
    logger.info("-" * 40)
    logger.info("步骤3: 测试增强版下载功能")
    logger.info("-" * 40)
    
    try:
        # 创建增强版爬虫
        crawler = EnhancedCrawler(settings)
        
        # 配置下载参数
        crawler.download_config.max_concurrent = 2  # 降低并发数
        crawler.download_config.retry_times = 3
        crawler.download_config.enable_recovery = True
        
        # 设置进度回调
        def progress_callback(completed, total):
            percentage = (completed / total * 100) if total > 0 else 0
            logger.info(f"下载进度: {completed}/{total} ({percentage:.1f}%)")
        
        crawler.download_config.progress_callback = progress_callback
        
        # 开始下载
        start_time = time.time()
        file_path = await crawler.download(book.url, book.source_id, "txt")
        end_time = time.time()
        
        logger.info(f"下载完成！")
        logger.info(f"文件路径: {file_path}")
        logger.info(f"总耗时: {end_time - start_time:.2f} 秒")
        
        # 检查文件
        if Path(file_path).exists():
            file_size = Path(file_path).stat().st_size
            logger.info(f"文件大小: {file_size / 1024:.2f} KB")
            
            # 读取文件前几行验证内容
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:10]
                logger.info("文件内容预览:")
                for i, line in enumerate(lines):
                    logger.info(f"  {i+1}: {line.strip()}")
            
            logger.info("✅ 增强版下载功能测试成功")
        else:
            logger.error("❌ 下载的文件不存在")
        
        # 获取下载统计信息
        progress_info = crawler.get_download_progress()
        logger.info("下载统计信息:")
        for key, value in progress_info.items():
            logger.info(f"  {key}: {value}")
        
    except Exception as e:
        logger.error(f"增强版下载测试失败: {str(e)}", exc_info=True)


async def test_download_recovery():
    """测试下载恢复功能"""
    logger.info("-" * 40)
    logger.info("步骤4: 测试下载恢复功能")
    logger.info("-" * 40)
    
    try:
        # 创建增强版爬虫
        crawler = EnhancedCrawler(settings)
        crawler.download_config.enable_recovery = True
        
        # 模拟中断的下载
        logger.info("模拟下载中断和恢复...")
        
        # 创建一些临时章节文件
        temp_dir = Path(settings.DOWNLOAD_PATH) / "temp"
        temp_dir.mkdir(exist_ok=True)
        
        # 创建模拟章节文件
        for i in range(1, 4):
            chapter_file = temp_dir / f"第{i}章 测试章节.txt"
            with open(chapter_file, 'w', encoding='utf-8') as f:
                f.write(f"这是第{i}章的内容，用于测试恢复功能。")
        
        logger.info(f"创建了 {len(list(temp_dir.glob('*.txt')))} 个临时章节文件")
        
        # 测试检查现有章节功能
        existing = crawler._check_existing_chapters(Path(settings.DOWNLOAD_PATH))
        logger.info(f"检测到已存在章节: {len(existing)} 个")
        
        # 清理测试文件
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        
        logger.info("✅ 下载恢复功能测试完成")
        
    except Exception as e:
        logger.error(f"下载恢复测试失败: {str(e)}")


async def test_error_handling():
    """测试错误处理机制"""
    logger.info("-" * 40)
    logger.info("步骤5: 测试错误处理机制")
    logger.info("-" * 40)
    
    try:
        crawler = EnhancedCrawler(settings)
        
        # 测试无效URL
        logger.info("测试无效URL处理...")
        try:
            await crawler.download("http://invalid-url.com", 1, "txt")
        except Exception as e:
            logger.info(f"✅ 正确捕获无效URL错误: {str(e)}")
        
        # 测试无效书源ID
        logger.info("测试无效书源ID处理...")
        try:
            await crawler.download("https://www.example.com", 999, "txt")
        except Exception as e:
            logger.info(f"✅ 正确捕获无效书源ID错误: {str(e)}")
        
        logger.info("✅ 错误处理机制测试完成")
        
    except Exception as e:
        logger.error(f"错误处理测试失败: {str(e)}")


async def main():
    """主函数"""
    try:
        await test_enhanced_download()
        await test_download_recovery()
        await test_error_handling()
        
        logger.info("=" * 60)
        logger.info("所有测试完成")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())