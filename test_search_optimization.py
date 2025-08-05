#!/usr/bin/env python3
"""
搜索功能优化测试脚本
测试每个书源最多返回2个结果的限制功能
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from app.services.novel_service import NovelService
from app.core.config import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('search_optimization_test.log')
    ]
)

logger = logging.getLogger(__name__)


async def test_search_optimization():
    """测试搜索功能优化"""
    logger.info("=" * 60)
    logger.info("开始测试搜索功能优化")
    logger.info("=" * 60)
    
    # 创建服务实例
    service = NovelService()
    
    # 检查书源数量
    sources_count = len(service.sources)
    logger.info(f"当前加载的书源数量: {sources_count}")
    
    if sources_count == 0:
        logger.error("没有可用的书源，无法进行测试")
        return
    
    # 显示配置信息
    logger.info(f"每个书源最大结果数: {settings.MAX_RESULTS_PER_SOURCE}")
    logger.info(f"总体最大搜索结果数: {settings.MAX_SEARCH_RESULTS}")
    
    # 测试用例
    test_keywords = [
        "斗破苍穹",
        "完美世界", 
        "遮天",
        "西游记",
        "三国演义"
    ]
    
    for keyword in test_keywords:
        logger.info("-" * 40)
        logger.info(f"测试搜索关键词: {keyword}")
        logger.info("-" * 40)
        
        try:
            # 执行搜索
            results = await service.search(keyword, max_results=30)
            
            # 统计结果
            logger.info(f"搜索结果总数: {len(results)}")
            
            # 按书源统计结果
            source_stats = {}
            for result in results:
                source_name = result.source_name or f"Source-{result.source_id}"
                source_stats[source_name] = source_stats.get(source_name, 0) + 1
            
            logger.info("各书源结果统计:")
            for source_name, count in source_stats.items():
                logger.info(f"  {source_name}: {count} 个结果")
                if count > settings.MAX_RESULTS_PER_SOURCE:
                    logger.warning(f"  ⚠️  {source_name} 超过限制 ({count} > {settings.MAX_RESULTS_PER_SOURCE})")
            
            # 显示前几个结果
            logger.info("前5个搜索结果:")
            for i, result in enumerate(results[:5]):
                logger.info(f"  {i+1}. 《{result.title}》 - {result.author} "
                          f"[{result.source_name}] (得分: {getattr(result, 'score', 'N/A')})")
            
            # 验证限制是否生效
            max_per_source = max(source_stats.values()) if source_stats else 0
            if max_per_source <= settings.MAX_RESULTS_PER_SOURCE:
                logger.info("✅ 每个书源结果数量限制正常")
            else:
                logger.error(f"❌ 检测到书源结果数量超限: {max_per_source}")
                
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}", exc_info=True)
        
        # 等待一下再进行下一个测试
        await asyncio.sleep(2)
    
    logger.info("=" * 60)
    logger.info("搜索功能优化测试完成")
    logger.info("=" * 60)


async def test_single_source_limit():
    """测试单个书源的结果限制"""
    logger.info("=" * 60)
    logger.info("测试单个书源结果限制")
    logger.info("=" * 60)
    
    service = NovelService()
    
    # 选择一个书源进行详细测试
    if not service.sources:
        logger.error("没有可用的书源")
        return
    
    source_id = list(service.sources.keys())[0]
    source = service.sources[source_id]
    
    logger.info(f"测试书源: {source.rule.get('name', source_id)} (ID: {source_id})")
    
    # 导入搜索解析器
    from app.parsers.search_parser import SearchParser
    
    parser = SearchParser(source)
    
    try:
        # 执行搜索
        results = await parser.parse("完美世界")
        
        logger.info(f"该书源返回结果数: {len(results)}")
        
        if len(results) <= settings.MAX_RESULTS_PER_SOURCE:
            logger.info("✅ 单个书源结果数量限制正常")
        else:
            logger.error(f"❌ 单个书源结果数量超限: {len(results)} > {settings.MAX_RESULTS_PER_SOURCE}")
        
        # 显示结果详情
        for i, result in enumerate(results):
            score = getattr(result, 'score', 'N/A')
            logger.info(f"  {i+1}. 《{result.title}》 - {result.author} (得分: {score})")
            
    except Exception as e:
        logger.error(f"单个书源测试失败: {str(e)}", exc_info=True)


async def main():
    """主函数"""
    try:
        await test_search_optimization()
        await test_single_source_limit()
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())