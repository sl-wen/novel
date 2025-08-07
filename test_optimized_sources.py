#!/usr/bin/env python3
"""
书源优化测试脚本
测试各个书源的目录获取和章节爬取功能
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.core.source import Source
from app.parsers.book_parser import BookParser
from app.parsers.toc_parser import TocParser
from app.parsers.chapter_parser import ChapterParser
from app.services.novel_service import NovelService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_sources.log')
    ]
)
logger = logging.getLogger(__name__)


class SourceTester:
    """书源测试器"""
    
    def __init__(self):
        self.novel_service = NovelService()
    
    async def test_all_sources(self):
        """测试所有书源"""
        logger.info("开始测试所有书源...")
        
        # 获取所有书源
        sources = self.novel_service.get_sources()
        
        results = []
        for source_info in sources[:5]:  # 只测试前5个书源
            source_id = source_info['id']
            source_name = source_info['rule'].get('name', f'书源{source_id}')
            
            logger.info(f"\n{'='*50}")
            logger.info(f"测试书源: {source_name} (ID: {source_id})")
            logger.info(f"{'='*50}")
            
            result = await self.test_source(source_id, source_name)
            results.append(result)
        
        # 输出测试总结
        self._print_summary(results)
    
    async def test_source(self, source_id: int, source_name: str) -> dict:
        """测试单个书源"""
        result = {
            'id': source_id,
            'name': source_name,
            'search_ok': False,
            'detail_ok': False,
            'toc_ok': False,
            'chapter_ok': False,
            'error_msg': ''
        }
        
        try:
            # 1. 测试搜索功能
            logger.info("1. 测试搜索功能...")
            search_results = await self._test_search(source_id)
            if search_results:
                result['search_ok'] = True
                logger.info(f"✅ 搜索成功，找到 {len(search_results)} 个结果")
                
                # 选择第一个搜索结果进行后续测试
                test_book = search_results[0]
                book_url = test_book.url
                
                # 2. 测试获取详情
                logger.info("2. 测试获取小说详情...")
                book_detail = await self._test_book_detail(source_id, book_url)
                if book_detail:
                    result['detail_ok'] = True
                    logger.info(f"✅ 详情获取成功: {book_detail.title}")
                    
                    # 3. 测试获取目录
                    logger.info("3. 测试获取小说目录...")
                    toc = await self._test_toc(source_id, book_url)
                    if toc:
                        result['toc_ok'] = True
                        logger.info(f"✅ 目录获取成功，共 {len(toc)} 章")
                        
                        # 4. 测试获取章节内容
                        if len(toc) > 0:
                            logger.info("4. 测试获取章节内容...")
                            chapter_url = toc[0].url
                            chapter_title = toc[0].title
                            chapter = await self._test_chapter(source_id, chapter_url, chapter_title)
                            if chapter and len(chapter.content) > 100:
                                result['chapter_ok'] = True
                                logger.info(f"✅ 章节获取成功: {chapter.title} ({len(chapter.content)} 字符)")
                            else:
                                logger.warning("❌ 章节内容获取失败或过短")
                        else:
                            logger.warning("❌ 目录为空，无法测试章节")
                    else:
                        logger.warning("❌ 目录获取失败")
                        result['error_msg'] = '目录获取失败'
                else:
                    logger.warning("❌ 详情获取失败")
                    result['error_msg'] = '详情获取失败'
            else:
                logger.warning("❌ 搜索失败")
                result['error_msg'] = '搜索失败'
                
        except Exception as e:
            logger.error(f"❌ 测试书源时出错: {str(e)}")
            result['error_msg'] = str(e)
        
        return result
    
    async def _test_search(self, source_id: int):
        """测试搜索功能"""
        try:
            # 使用常见的搜索关键词
            keywords = ["斗破苍穹", "完美世界", "遮天", "凡人修仙传"]
            
            for keyword in keywords:
                try:
                    results = await self.novel_service.search(keyword, max_results=5)
                    if results:
                        return results
                except Exception as e:
                    logger.debug(f"搜索 '{keyword}' 失败: {str(e)}")
                    continue
            
            return None
        except Exception as e:
            logger.error(f"搜索测试失败: {str(e)}")
            return None
    
    async def _test_book_detail(self, source_id: int, url: str):
        """测试获取书籍详情"""
        try:
            return await self.novel_service.get_book_detail(url, source_id)
        except Exception as e:
            logger.error(f"获取详情失败: {str(e)}")
            return None
    
    async def _test_toc(self, source_id: int, url: str):
        """测试获取目录"""
        try:
            return await self.novel_service.get_toc(url, source_id)
        except Exception as e:
            logger.error(f"获取目录失败: {str(e)}")
            return None
    
    async def _test_chapter(self, source_id: int, url: str, title: str):
        """测试获取章节内容"""
        try:
            return await self.novel_service.get_chapter_content(url, source_id)
        except Exception as e:
            logger.error(f"获取章节内容失败: {str(e)}")
            return None
    
    def _print_summary(self, results):
        """打印测试总结"""
        logger.info(f"\n{'='*60}")
        logger.info("测试总结")
        logger.info(f"{'='*60}")
        
        total_sources = len(results)
        working_sources = 0
        
        for result in results:
            status_icons = []
            status_icons.append("🔍" if result['search_ok'] else "❌")
            status_icons.append("📖" if result['detail_ok'] else "❌")
            status_icons.append("📑" if result['toc_ok'] else "❌")
            status_icons.append("📝" if result['chapter_ok'] else "❌")
            
            if result['search_ok'] and result['detail_ok'] and result['toc_ok'] and result['chapter_ok']:
                working_sources += 1
                status = "✅ 完全正常"
            elif result['search_ok'] and result['toc_ok']:
                status = "⚠️ 部分功能正常"
            else:
                status = f"❌ 不可用 ({result['error_msg']})"
            
            logger.info(f"{result['name']:20} {' '.join(status_icons)} {status}")
        
        logger.info(f"\n总计: {total_sources} 个书源")
        logger.info(f"完全正常: {working_sources} 个")
        logger.info(f"成功率: {working_sources/total_sources*100:.1f}%")
        
        logger.info(f"\n图例:")
        logger.info(f"🔍 搜索功能  📖 详情获取  📑 目录获取  📝 章节获取")


async def main():
    """主函数"""
    tester = SourceTester()
    await tester.test_all_sources()


if __name__ == "__main__":
    asyncio.run(main())