#!/usr/bin/env python3
"""
并行下载性能测试工具

测试和对比优化前后的下载性能，分析性能改进效果
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Dict, List

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from app.core.source import Source
from app.core.crawler import Crawler, DownloadConfig
from app.parsers.toc_parser import TocParser


class PerformanceTestRunner:
    """性能测试运行器"""
    
    def __init__(self):
        self.test_results = []
    
    async def run_performance_test(self, source_id: int, url: str, test_name: str = "默认测试"):
        """运行性能测试"""
        print(f"\n🚀 开始性能测试: {test_name}")
        print("=" * 60)
        
        try:
            # 创建书源和解析器
            source = Source(source_id)
            parser = TocParser(source)
            
            print(f"📚 书源: {source.name}")
            print(f"🔗 URL: {url}")
            
            # 获取目录
            print("\n⏳ 获取目录...")
            toc_start = time.time()
            chapters = await parser.parse(url)
            toc_time = time.time() - toc_start
            
            if not chapters:
                print("❌ 未获取到章节")
                return None
            
            print(f"✅ 获取到 {len(chapters)} 个章节 (耗时: {toc_time:.2f}s)")
            
            # 测试不同的下载配置
            test_configs = [
                ("保守配置", DownloadConfig(
                    max_concurrent=5,
                    retry_times=3,
                    retry_delay=1.0,
                    batch_delay=0.5,
                    timeout=30,
                    enable_batch_write=False,
                    skip_quality_check=False
                )),
                ("平衡配置", DownloadConfig(
                    max_concurrent=10,
                    retry_times=3,
                    retry_delay=0.5,
                    batch_delay=0.2,
                    timeout=30,
                    enable_batch_write=True,
                    skip_quality_check=False
                )),
                ("激进配置", DownloadConfig(
                    max_concurrent=15,
                    retry_times=2,
                    retry_delay=0.3,
                    batch_delay=0.1,
                    timeout=20,
                    enable_batch_write=True,
                    skip_quality_check=True
                ))
            ]
            
            results = []
            
            for config_name, config in test_configs:
                print(f"\n📊 测试配置: {config_name}")
                print(f"   并发数: {config.max_concurrent}")
                print(f"   重试次数: {config.retry_times}")
                print(f"   批量写入: {'启用' if config.enable_batch_write else '禁用'}")
                print(f"   质量检查: {'跳过' if config.skip_quality_check else '启用'}")
                
                # 限制测试章节数量以加快测试
                test_chapters = chapters[:min(20, len(chapters))]
                
                result = await self._test_download_performance(
                    source_id, test_chapters, config, config_name
                )
                
                if result:
                    results.append(result)
                    self._print_test_result(result)
            
            # 对比结果
            if len(results) > 1:
                self._compare_results(results)
            
            return results
            
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    async def _test_download_performance(
        self, source_id: int, chapters: List, config: DownloadConfig, config_name: str
    ) -> Dict:
        """测试下载性能"""
        from app.parsers.chapter_parser import ChapterParser
        
        print(f"   ⏳ 开始下载 {len(chapters)} 个章节...")
        
        start_time = time.time()
        
        source = Source(source_id)
        parser = ChapterParser(source)
        
        # 模拟下载过程
        successful_downloads = 0
        failed_downloads = 0
        total_content_length = 0
        download_times = []
        
        # 使用信号量控制并发
        semaphore = asyncio.Semaphore(config.max_concurrent)
        
        async def download_chapter(chapter_info):
            nonlocal successful_downloads, failed_downloads, total_content_length
            
            async with semaphore:
                chapter_start = time.time()
                
                try:
                    # 模拟下载延迟
                    if config.batch_delay > 0:
                        await asyncio.sleep(config.batch_delay)
                    
                    chapter = await asyncio.wait_for(
                        parser.parse(chapter_info.url, chapter_info.title, chapter_info.order),
                        timeout=config.timeout
                    )
                    
                    if chapter and chapter.content:
                        download_time = time.time() - chapter_start
                        download_times.append(download_time)
                        successful_downloads += 1
                        total_content_length += len(chapter.content)
                    else:
                        failed_downloads += 1
                        
                except Exception as e:
                    failed_downloads += 1
                    print(f"     ⚠️ 章节下载失败: {chapter_info.title}")
        
        # 并发下载
        tasks = [download_chapter(ch) for ch in chapters]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 计算统计指标
        success_rate = successful_downloads / len(chapters) if chapters else 0
        avg_download_time = sum(download_times) / len(download_times) if download_times else 0
        download_speed = successful_downloads / total_time if total_time > 0 else 0
        avg_content_length = total_content_length / successful_downloads if successful_downloads > 0 else 0
        
        return {
            "config_name": config_name,
            "config": config,
            "total_chapters": len(chapters),
            "successful_downloads": successful_downloads,
            "failed_downloads": failed_downloads,
            "total_time": total_time,
            "success_rate": success_rate,
            "avg_download_time": avg_download_time,
            "download_speed": download_speed,
            "total_content_length": total_content_length,
            "avg_content_length": avg_content_length
        }
    
    def _print_test_result(self, result: Dict):
        """打印测试结果"""
        print(f"   ✅ 测试完成:")
        print(f"      总章节: {result['total_chapters']}")
        print(f"      成功: {result['successful_downloads']}")
        print(f"      失败: {result['failed_downloads']}")
        print(f"      成功率: {result['success_rate']:.1%}")
        print(f"      总耗时: {result['total_time']:.2f}s")
        print(f"      平均下载时间: {result['avg_download_time']:.2f}s")
        print(f"      下载速度: {result['download_speed']:.2f} 章/秒")
        print(f"      平均章节长度: {result['avg_content_length']:.0f} 字符")
    
    def _compare_results(self, results: List[Dict]):
        """对比测试结果"""
        print(f"\n📈 性能对比分析")
        print("=" * 60)
        
        # 找出最佳配置
        best_speed = max(results, key=lambda x: x['download_speed'])
        best_success = max(results, key=lambda x: x['success_rate'])
        
        print(f"🏆 最快下载速度: {best_speed['config_name']} ({best_speed['download_speed']:.2f} 章/秒)")
        print(f"🎯 最高成功率: {best_success['config_name']} ({best_success['success_rate']:.1%})")
        
        # 详细对比表
        print(f"\n📊 详细对比:")
        print(f"{'配置名称':<12} {'成功率':<8} {'速度(章/s)':<10} {'平均时间(s)':<12} {'总耗时(s)':<10}")
        print("-" * 60)
        
        for result in results:
            print(f"{result['config_name']:<12} "
                  f"{result['success_rate']:<8.1%} "
                  f"{result['download_speed']:<10.2f} "
                  f"{result['avg_download_time']:<12.2f} "
                  f"{result['total_time']:<10.2f}")
        
        # 性能改进分析
        if len(results) >= 2:
            baseline = results[0]  # 保守配置作为基线
            best = max(results, key=lambda x: x['download_speed'])
            
            if best != baseline:
                speed_improvement = (best['download_speed'] - baseline['download_speed']) / baseline['download_speed'] * 100
                time_improvement = (baseline['total_time'] - best['total_time']) / baseline['total_time'] * 100
                
                print(f"\n🚀 性能改进:")
                print(f"   下载速度提升: {speed_improvement:.1f}%")
                print(f"   总时间减少: {time_improvement:.1f}%")
                
                if speed_improvement > 50:
                    print("   💡 建议: 采用高性能配置可显著提升下载速度")
                elif speed_improvement > 20:
                    print("   💡 建议: 平衡配置可在性能和稳定性之间取得良好平衡")
                else:
                    print("   💡 建议: 保守配置可能更适合当前网络环境")
    
    def get_optimization_recommendations(self, results: List[Dict]) -> List[str]:
        """获取优化建议"""
        if not results:
            return []
        
        recommendations = []
        
        # 分析成功率
        avg_success_rate = sum(r['success_rate'] for r in results) / len(results)
        if avg_success_rate < 0.8:
            recommendations.append("整体成功率较低，建议检查网络连接和目标服务器状态")
        
        # 分析下载速度
        speeds = [r['download_speed'] for r in results]
        if max(speeds) - min(speeds) > 2.0:
            recommendations.append("不同配置间性能差异较大，建议根据实际情况选择合适的配置")
        
        # 分析并发效果
        concurrent_configs = [(r['config'].max_concurrent, r['download_speed']) for r in results]
        concurrent_configs.sort()
        
        if len(concurrent_configs) >= 2:
            low_concurrent = concurrent_configs[0]
            high_concurrent = concurrent_configs[-1]
            
            if high_concurrent[1] > low_concurrent[1] * 1.5:
                recommendations.append("增加并发数可显著提升性能")
            elif high_concurrent[1] < low_concurrent[1]:
                recommendations.append("过高的并发数可能导致性能下降，建议适当降低")
        
        return recommendations


async def main():
    """主函数"""
    print("并行下载性能测试工具")
    print("====================")
    
    # 默认测试用例
    test_cases = [
        {
            "source_id": 4,
            "url": "http://wap.99xs.info/124310/",
            "name": "书源4性能测试"
        }
    ]
    
    runner = PerformanceTestRunner()
    
    for test_case in test_cases:
        results = await runner.run_performance_test(
            test_case["source_id"],
            test_case["url"],
            test_case["name"]
        )
        
        if results:
            recommendations = runner.get_optimization_recommendations(results)
            if recommendations:
                print(f"\n💡 优化建议:")
                for i, rec in enumerate(recommendations, 1):
                    print(f"   {i}. {rec}")
        
        print("\n" + "="*60)


if __name__ == "__main__":
    asyncio.run(main())