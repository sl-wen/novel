#!/usr/bin/env python3
"""
测试优化后的下载功能
验证书源目录获取和文章爬取优化效果
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OptimizedDownloadTester:
    """优化下载测试器"""
    
    def __init__(self):
        self.test_results = {}
    
    async def test_all_sources(self):
        """测试所有书源"""
        logger.info("开始测试优化后的书源...")
        
        # 测试几个主要的书源
        test_sources = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        
        for source_id in test_sources:
            try:
                logger.info(f"\n{'='*50}")
                logger.info(f"测试书源 {source_id}")
                logger.info(f"{'='*50}")
                
                result = await self.test_single_source(source_id)
                self.test_results[source_id] = result
                
            except Exception as e:
                logger.error(f"测试书源 {source_id} 时出现异常: {str(e)}")
                self.test_results[source_id] = {
                    'status': 'error',
                    'error': str(e),
                    'toc_count': 0,
                    'chapter_success': 0,
                    'chapter_failed': 0
                }
        
        # 输出总结
        self.print_summary()
    
    async def test_single_source(self, source_id: int):
        """测试单个书源"""
        try:
            # 导入必要的模块
            from app.core.source import Source
            from app.parsers.enhanced_toc_parser import EnhancedTocParser
            from app.parsers.enhanced_chapter_parser import EnhancedChapterParser
            
            # 创建书源对象
            source = Source(source_id)
            source_name = source.rule.get('name', f'书源{source_id}')
            logger.info(f"书源名称: {source_name}")
            logger.info(f"书源URL: {source.rule.get('url', 'N/A')}")
            
            # 测试目录解析
            toc_result = await self.test_toc_parsing(source_id, source)
            
            # 测试章节内容解析
            chapter_result = await self.test_chapter_parsing(source_id, source)
            
            return {
                'status': 'success',
                'source_name': source_name,
                'toc_count': toc_result['count'],
                'toc_error': toc_result.get('error'),
                'chapter_success': chapter_result['success_count'],
                'chapter_failed': chapter_result['failed_count'],
                'sample_chapters': chapter_result['samples']
            }
            
        except Exception as e:
            logger.error(f"测试书源 {source_id} 失败: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'toc_count': 0,
                'chapter_success': 0,
                'chapter_failed': 0
            }
    
    async def test_toc_parsing(self, source_id: int, source):
        """测试目录解析"""
        try:
            # 使用一个测试URL（这里使用书源的主页）
            test_url = source.rule.get('url', '')
            if not test_url:
                return {'count': 0, 'error': '书源URL为空'}
            
            logger.info(f"测试目录解析: {test_url}")
            
            # 尝试获取目录
            toc_parser = EnhancedTocParser(source)
            chapters = await toc_parser.parse(test_url, 1, 10)  # 只获取前10章
            
            logger.info(f"目录解析结果: 找到 {len(chapters)} 章")
            
            if chapters:
                logger.info("前5章标题:")
                for i, chapter in enumerate(chapters[:5]):
                    logger.info(f"  {i+1}. {chapter.title}")
            
            return {'count': len(chapters)}
            
        except Exception as e:
            logger.error(f"目录解析失败: {str(e)}")
            return {'count': 0, 'error': str(e)}
    
    async def test_chapter_parsing(self, source_id: int, source):
        """测试章节内容解析"""
        try:
            # 先获取目录
            test_url = source.rule.get('url', '')
            if not test_url:
                return {'success_count': 0, 'failed_count': 0, 'samples': []}
            
            toc_parser = EnhancedTocParser(source)
            chapters = await toc_parser.parse(test_url, 1, 5)  # 只测试前5章
            
            if not chapters:
                return {'success_count': 0, 'failed_count': 0, 'samples': []}
            
            # 测试章节内容获取
            chapter_parser = EnhancedChapterParser(source)
            
            success_count = 0
            failed_count = 0
            samples = []
            
            for i, chapter_info in enumerate(chapters[:3]):  # 只测试前3章
                try:
                    logger.info(f"测试章节 {i+1}: {chapter_info.title}")
                    
                    chapter = await chapter_parser.parse(
                        chapter_info.url, 
                        chapter_info.title, 
                        chapter_info.order
                    )
                    
                    if chapter and chapter.content and len(chapter.content) > 50:
                        success_count += 1
                        samples.append({
                            'title': chapter.title,
                            'content_length': len(chapter.content),
                            'content_preview': chapter.content[:100] + '...'
                        })
                        logger.info(f"  成功: {len(chapter.content)} 字符")
                    else:
                        failed_count += 1
                        logger.warning(f"  失败: 内容为空或过短")
                        
                except Exception as e:
                    failed_count += 1
                    logger.error(f"  异常: {str(e)}")
            
            return {
                'success_count': success_count,
                'failed_count': failed_count,
                'samples': samples
            }
            
        except Exception as e:
            logger.error(f"章节解析测试失败: {str(e)}")
            return {'success_count': 0, 'failed_count': 0, 'samples': []}
    
    def print_summary(self):
        """输出测试总结"""
        logger.info(f"\n{'='*60}")
        logger.info("优化后书源测试总结")
        logger.info(f"{'='*60}")
        
        working_sources = []
        problematic_sources = []
        
        for source_id, result in self.test_results.items():
            if result['status'] == 'success':
                working_sources.append((source_id, result))
            else:
                problematic_sources.append((source_id, result))
        
        logger.info(f"可用书源: {len(working_sources)} 个")
        for source_id, result in working_sources:
            logger.info(f"  书源 {source_id} ({result.get('source_name', 'Unknown')}): "
                       f"目录 {result['toc_count']} 章, "
                       f"章节测试 {result['chapter_success']}/{result['chapter_success'] + result['chapter_failed']}")
        
        logger.info(f"\n问题书源: {len(problematic_sources)} 个")
        for source_id, result in problematic_sources:
            logger.info(f"  书源 {source_id}: {result.get('error', 'Unknown error')}")
        
        # 计算成功率
        total_sources = len(self.test_results)
        working_rate = len(working_sources) / total_sources * 100 if total_sources > 0 else 0
        
        logger.info(f"\n成功率: {working_rate:.1f}% ({len(working_sources)}/{total_sources})")
        
        # 输出优化建议
        logger.info(f"\n优化建议:")
        if problematic_sources:
            logger.info("1. 检查问题书源的网络连接和反爬虫机制")
            logger.info("2. 更新书源规则以适应当前网站结构")
            logger.info("3. 增加更多的错误处理和重试机制")
        else:
            logger.info("所有书源都工作正常！优化效果显著！")

async def main():
    """主函数"""
    tester = OptimizedDownloadTester()
    await tester.test_all_sources()

if __name__ == "__main__":
    asyncio.run(main())