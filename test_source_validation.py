#!/usr/bin/env python3
"""
书源验证和目录获取测试脚本
检查每个书源的可用性和目录获取情况
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from app.services.novel_service import NovelService
from app.core.source import Source

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SourceValidator:
    """书源验证器"""
    
    def __init__(self):
        self.novel_service = NovelService()
    
    async def test_all_sources(self):
        """测试所有书源"""
        logger.info("开始测试所有书源...")
        
        results = {}
        for source_id in range(1, 21):  # 测试书源1-20
            try:
                logger.info(f"\n{'='*50}")
                logger.info(f"测试书源 {source_id}")
                logger.info(f"{'='*50}")
                
                result = await self.test_single_source(source_id)
                results[source_id] = result
                
            except Exception as e:
                logger.error(f"测试书源 {source_id} 时出现异常: {str(e)}")
                results[source_id] = {
                    'status': 'error',
                    'error': str(e),
                    'toc_count': 0,
                    'sample_chapters': []
                }
        
        # 输出总结
        self.print_summary(results)
    
    async def test_single_source(self, source_id: int):
        """测试单个书源"""
        try:
            # 检查书源是否存在
            source = self.novel_service.sources.get(source_id)
            if not source:
                return {
                    'status': 'not_found',
                    'error': f'书源 {source_id} 不存在',
                    'toc_count': 0,
                    'sample_chapters': []
                }
            
            source_name = source.rule.get('name', f'书源{source_id}')
            logger.info(f"书源名称: {source_name}")
            logger.info(f"书源URL: {source.rule.get('url', 'N/A')}")
            
            # 测试书源基本配置
            config_status = self.check_source_config(source)
            if not config_status['valid']:
                return {
                    'status': 'config_error',
                    'error': config_status['error'],
                    'toc_count': 0,
                    'sample_chapters': []
                }
            
            # 测试目录获取
            toc_result = await self.test_toc_parsing(source_id, source)
            
            # 测试章节内容获取
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
                'sample_chapters': []
            }
    
    def check_source_config(self, source: Source):
        """检查书源配置"""
        rule = source.rule
        
        # 检查必要的配置项
        required_sections = ['search', 'book', 'toc', 'chapter']
        for section in required_sections:
            if section not in rule:
                return {
                    'valid': False,
                    'error': f'缺少 {section} 配置节'
                }
        
        # 检查目录配置
        toc_rule = rule.get('toc', {})
        if not toc_rule.get('list'):
            return {
                'valid': False,
                'error': '目录配置缺少 list 选择器'
            }
        
        # 检查章节配置
        chapter_rule = rule.get('chapter', {})
        if not chapter_rule.get('content'):
            return {
                'valid': False,
                'error': '章节配置缺少 content 选择器'
            }
        
        return {'valid': True}
    
    async def test_toc_parsing(self, source_id: int, source: Source):
        """测试目录解析"""
        try:
            # 使用一个测试URL（这里使用书源的主页）
            test_url = source.rule.get('url', '')
            if not test_url:
                return {'count': 0, 'error': '书源URL为空'}
            
            logger.info(f"测试目录解析: {test_url}")
            
            # 尝试获取目录
            from app.parsers.toc_parser import TocParser
            toc_parser = TocParser(source)
            
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
    
    async def test_chapter_parsing(self, source_id: int, source: Source):
        """测试章节内容解析"""
        try:
            # 先获取目录
            test_url = source.rule.get('url', '')
            if not test_url:
                return {'success_count': 0, 'failed_count': 0, 'samples': []}
            
            from app.parsers.toc_parser import TocParser
            toc_parser = TocParser(source)
            chapters = await toc_parser.parse(test_url, 1, 5)  # 只测试前5章
            
            if not chapters:
                return {'success_count': 0, 'failed_count': 0, 'samples': []}
            
            # 测试章节内容获取
            from app.parsers.chapter_parser import ChapterParser
            chapter_parser = ChapterParser(source)
            
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
    
    def print_summary(self, results):
        """输出测试总结"""
        logger.info(f"\n{'='*60}")
        logger.info("书源测试总结")
        logger.info(f"{'='*60}")
        
        working_sources = []
        problematic_sources = []
        
        for source_id, result in results.items():
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
        
        # 输出优化建议
        logger.info(f"\n优化建议:")
        if problematic_sources:
            logger.info("1. 检查问题书源的网络连接和反爬虫机制")
            logger.info("2. 更新书源规则以适应当前网站结构")
            logger.info("3. 增加更多的错误处理和重试机制")
        else:
            logger.info("所有书源都工作正常！")

async def main():
    """主函数"""
    validator = SourceValidator()
    await validator.test_all_sources()

if __name__ == "__main__":
    asyncio.run(main())