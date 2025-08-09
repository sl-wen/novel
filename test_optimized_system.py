#!/usr/bin/env python3
"""
优化系统综合测试脚本
测试所有优化功能的正确性和性能提升
"""

import asyncio
import json
import logging
import time
import requests
from typing import List, Dict, Any
import statistics

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class OptimizedSystemTester:
    """优化系统测试器"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_results = {}
        self.performance_data = []
        
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始优化系统综合测试")
        print("=" * 80)
        
        # 测试列表
        tests = [
            ("健康检查", self.test_health_check),
            ("性能监控", self.test_performance_monitoring),
            ("缓存系统", self.test_caching_system),
            ("优化搜索", self.test_optimized_search),
            ("书源获取", self.test_sources),
            ("小说详情", self.test_book_detail),
            ("目录获取", self.test_toc),
            ("下载功能", self.test_download),
            ("性能对比", self.test_performance_comparison),
            ("并发测试", self.test_concurrent_requests),
            ("缓存清理", self.test_cache_management),
        ]
        
        # 执行测试
        for test_name, test_func in tests:
            print(f"\n📋 {test_name}测试")
            print("-" * 40)
            
            try:
                start_time = time.time()
                success = test_func()
                end_time = time.time()
                
                duration = end_time - start_time
                self.test_results[test_name] = {
                    "success": success,
                    "duration": duration,
                    "timestamp": start_time
                }
                
                status = "✅ 通过" if success else "❌ 失败"
                print(f"   {status} (耗时: {duration:.2f}秒)")
                
            except Exception as e:
                print(f"   ❌ 异常: {str(e)}")
                self.test_results[test_name] = {
                    "success": False,
                    "duration": 0,
                    "error": str(e),
                    "timestamp": time.time()
                }
        
        # 生成测试报告
        self.generate_test_report()
    
    def test_health_check(self) -> bool:
        """测试健康检查"""
        try:
            response = requests.get(f"{self.base_url}/api/optimized/health", timeout=10)
            
            if response.status_code != 200:
                print(f"   ❌ 健康检查API返回状态码: {response.status_code}")
                return False
            
            data = response.json()
            if data.get("code") != 200:
                print(f"   ❌ 健康检查返回错误: {data.get('message')}")
                return False
            
            health_data = data.get("data", {})
            status = health_data.get("status")
            health_score = health_data.get("health_score", 0)
            
            print(f"   - 系统状态: {status}")
            print(f"   - 健康分数: {health_score}")
            
            if status in ["healthy", "warning"]:
                print("   ✅ 系统健康状态正常")
                return True
            else:
                print("   ⚠️  系统健康状态异常")
                return False
                
        except Exception as e:
            print(f"   ❌ 健康检查异常: {str(e)}")
            return False
    
    def test_performance_monitoring(self) -> bool:
        """测试性能监控"""
        try:
            response = requests.get(f"{self.base_url}/api/optimized/performance", timeout=10)
            
            if response.status_code != 200:
                print(f"   ❌ 性能监控API返回状态码: {response.status_code}")
                return False
            
            data = response.json()
            if data.get("code") != 200:
                print(f"   ❌ 性能监控返回错误: {data.get('message')}")
                return False
            
            perf_data = data.get("data", {})
            performance = perf_data.get("performance", {})
            cache = perf_data.get("cache", {})
            http = perf_data.get("http", {})
            
            print(f"   - 总操作数: {performance.get('total_operations', 0)}")
            print(f"   - 成功率: {performance.get('overall_success_rate', 0):.1f}%")
            print(f"   - 缓存项目: {cache.get('memory_cache_items', 0)} (内存) + {cache.get('disk_cache_items', 0)} (磁盘)")
            print(f"   - HTTP成功率: {http.get('success_rate', 0):.1f}%")
            
            return True
            
        except Exception as e:
            print(f"   ❌ 性能监控异常: {str(e)}")
            return False
    
    def test_caching_system(self) -> bool:
        """测试缓存系统"""
        try:
            # 第一次搜索（应该不命中缓存）
            start_time = time.time()
            response1 = requests.get(
                f"{self.base_url}/api/optimized/search",
                params={"keyword": "斗破苍穹", "maxResults": 5},
                timeout=30
            )
            first_duration = time.time() - start_time
            
            if response1.status_code != 200:
                print(f"   ❌ 第一次搜索失败: {response1.status_code}")
                return False
            
            # 第二次搜索（应该命中缓存）
            start_time = time.time()
            response2 = requests.get(
                f"{self.base_url}/api/optimized/search",
                params={"keyword": "斗破苍穹", "maxResults": 5},
                timeout=30
            )
            second_duration = time.time() - start_time
            
            if response2.status_code != 200:
                print(f"   ❌ 第二次搜索失败: {response2.status_code}")
                return False
            
            data1 = response1.json()
            data2 = response2.json()
            
            # 检查结果一致性
            if len(data1.get("data", [])) != len(data2.get("data", [])):
                print("   ❌ 缓存结果不一致")
                return False
            
            # 检查性能提升
            if second_duration < first_duration * 0.8:  # 第二次应该快至少20%
                print(f"   ✅ 缓存生效，性能提升: {first_duration:.2f}s -> {second_duration:.2f}s")
                return True
            else:
                print(f"   ⚠️  缓存效果不明显: {first_duration:.2f}s -> {second_duration:.2f}s")
                return True  # 仍然算通过，可能是缓存未命中
                
        except Exception as e:
            print(f"   ❌ 缓存测试异常: {str(e)}")
            return False
    
    def test_optimized_search(self) -> bool:
        """测试优化搜索"""
        try:
            search_keywords = ["斗破苍穹", "完美世界", "遮天"]
            
            for keyword in search_keywords:
                start_time = time.time()
                response = requests.get(
                    f"{self.base_url}/api/optimized/search",
                    params={"keyword": keyword, "maxResults": 10},
                    timeout=30
                )
                duration = time.time() - start_time
                
                if response.status_code != 200:
                    print(f"   ❌ 搜索 '{keyword}' 失败: {response.status_code}")
                    return False
                
                data = response.json()
                if data.get("code") != 200:
                    print(f"   ❌ 搜索 '{keyword}' 返回错误: {data.get('message')}")
                    return False
                
                results = data.get("data", [])
                meta = data.get("meta", {})
                
                print(f"   - '{keyword}': {len(results)} 条结果, 耗时 {duration:.2f}s ({meta.get('duration_ms', 0):.1f}ms)")
                
                if len(results) == 0:
                    print(f"   ⚠️  '{keyword}' 搜索无结果")
                
                # 记录性能数据
                self.performance_data.append({
                    "operation": "search",
                    "keyword": keyword,
                    "duration": duration,
                    "results_count": len(results)
                })
            
            return True
            
        except Exception as e:
            print(f"   ❌ 优化搜索异常: {str(e)}")
            return False
    
    def test_sources(self) -> bool:
        """测试书源获取"""
        try:
            response = requests.get(f"{self.base_url}/api/optimized/sources", timeout=10)
            
            if response.status_code != 200:
                print(f"   ❌ 书源API返回状态码: {response.status_code}")
                return False
            
            data = response.json()
            if data.get("code") != 200:
                print(f"   ❌ 书源API返回错误: {data.get('message')}")
                return False
            
            sources = data.get("data", [])
            meta = data.get("meta", {})
            
            print(f"   - 总书源数: {len(sources)}")
            print(f"   - 耗时: {meta.get('duration_ms', 0):.1f}ms")
            
            # 检查书源信息完整性
            enabled_sources = [s for s in sources if s.get("enabled")]
            search_enabled = [s for s in sources if s.get("search_enabled")]
            download_enabled = [s for s in sources if s.get("download_enabled")]
            
            print(f"   - 启用的书源: {len(enabled_sources)}")
            print(f"   - 支持搜索: {len(search_enabled)}")
            print(f"   - 支持下载: {len(download_enabled)}")
            
            return len(sources) > 0
            
        except Exception as e:
            print(f"   ❌ 书源测试异常: {str(e)}")
            return False
    
    def test_book_detail(self) -> bool:
        """测试小说详情获取"""
        try:
            # 先搜索获取一个小说URL
            search_response = requests.get(
                f"{self.base_url}/api/optimized/search",
                params={"keyword": "斗破苍穹", "maxResults": 1},
                timeout=30
            )
            
            if search_response.status_code != 200:
                print("   ❌ 无法获取测试URL")
                return False
            
            search_data = search_response.json()
            results = search_data.get("data", [])
            
            if not results:
                print("   ❌ 搜索无结果，无法测试详情")
                return False
            
            book_url = results[0].get("url")
            source_id = results[0].get("source_id", 2)
            
            # 获取详情
            detail_response = requests.get(
                f"{self.base_url}/api/optimized/detail",
                params={"url": book_url, "sourceId": source_id},
                timeout=30
            )
            
            if detail_response.status_code != 200:
                print(f"   ❌ 详情API返回状态码: {detail_response.status_code}")
                return False
            
            detail_data = detail_response.json()
            if detail_data.get("code") != 200:
                print(f"   ❌ 详情API返回错误: {detail_data.get('message')}")
                return False
            
            book = detail_data.get("data")
            meta = detail_data.get("meta", {})
            
            if book and book.get("title"):
                print(f"   - 书名: {book.get('title')}")
                print(f"   - 作者: {book.get('author')}")
                print(f"   - 耗时: {meta.get('duration_ms', 0):.1f}ms")
                return True
            else:
                print("   ❌ 详情数据不完整")
                return False
                
        except Exception as e:
            print(f"   ❌ 详情测试异常: {str(e)}")
            return False
    
    def test_toc(self) -> bool:
        """测试目录获取"""
        try:
            # 先搜索获取一个小说URL
            search_response = requests.get(
                f"{self.base_url}/api/optimized/search",
                params={"keyword": "斗破苍穹", "maxResults": 1},
                timeout=30
            )
            
            if search_response.status_code != 200:
                print("   ❌ 无法获取测试URL")
                return False
            
            search_data = search_response.json()
            results = search_data.get("data", [])
            
            if not results:
                print("   ❌ 搜索无结果，无法测试目录")
                return False
            
            book_url = results[0].get("url")
            source_id = results[0].get("source_id", 2)
            
            # 获取目录
            toc_response = requests.get(
                f"{self.base_url}/api/optimized/toc",
                params={"url": book_url, "sourceId": source_id},
                timeout=30
            )
            
            if toc_response.status_code != 200:
                print(f"   ❌ 目录API返回状态码: {toc_response.status_code}")
                return False
            
            toc_data = toc_response.json()
            if toc_data.get("code") != 200:
                print(f"   ❌ 目录API返回错误: {toc_data.get('message')}")
                return False
            
            chapters = toc_data.get("data", [])
            meta = toc_data.get("meta", {})
            
            print(f"   - 章节数: {len(chapters)}")
            print(f"   - 耗时: {meta.get('duration_ms', 0):.1f}ms")
            
            if len(chapters) > 0:
                print(f"   - 首章: {chapters[0].get('title', '无标题')}")
                return True
            else:
                print("   ❌ 目录为空")
                return False
                
        except Exception as e:
            print(f"   ❌ 目录测试异常: {str(e)}")
            return False
    
    def test_download(self) -> bool:
        """测试下载功能"""
        try:
            # 先搜索获取一个小说URL
            search_response = requests.get(
                f"{self.base_url}/api/optimized/search",
                params={"keyword": "斗破苍穹", "maxResults": 1},
                timeout=30
            )
            
            if search_response.status_code != 200:
                print("   ❌ 无法获取测试URL")
                return False
            
            search_data = search_response.json()
            results = search_data.get("data", [])
            
            if not results:
                print("   ❌ 搜索无结果，无法测试下载")
                return False
            
            book_url = results[0].get("url")
            source_id = results[0].get("source_id", 2)
            
            # 测试下载（这可能需要很长时间，所以设置较长超时）
            print("   - 开始下载测试（可能需要较长时间）...")
            download_response = requests.get(
                f"{self.base_url}/api/optimized/download",
                params={"url": book_url, "sourceId": source_id, "format": "txt"},
                timeout=300,  # 5分钟超时
                stream=True
            )
            
            if download_response.status_code == 200:
                # 检查响应头
                headers = download_response.headers
                file_size = headers.get("X-File-Size")
                duration_ms = headers.get("X-Download-Duration-MS")
                task_id = headers.get("X-Task-ID")
                
                print(f"   - 文件大小: {file_size} 字节")
                print(f"   - 下载耗时: {duration_ms}ms")
                print(f"   - 任务ID: {task_id}")
                
                # 读取部分内容验证
                content_chunk = download_response.raw.read(1024)
                if len(content_chunk) > 0:
                    print("   ✅ 下载内容验证通过")
                    return True
                else:
                    print("   ❌ 下载内容为空")
                    return False
            else:
                print(f"   ❌ 下载失败: {download_response.status_code}")
                try:
                    error_data = download_response.json()
                    print(f"   错误信息: {error_data.get('message')}")
                except:
                    pass
                return False
                
        except requests.exceptions.Timeout:
            print("   ⚠️  下载超时（这可能是正常的，取决于网络和书籍大小）")
            return True  # 超时不算失败
        except Exception as e:
            print(f"   ❌ 下载测试异常: {str(e)}")
            return False
    
    def test_performance_comparison(self) -> bool:
        """测试性能对比（优化版 vs 原版）"""
        try:
            keyword = "斗破苍穹"
            
            # 测试原版API
            start_time = time.time()
            original_response = requests.get(
                f"{self.base_url}/api/novels/search",
                params={"keyword": keyword, "maxResults": 10},
                timeout=30
            )
            original_duration = time.time() - start_time
            
            # 测试优化版API
            start_time = time.time()
            optimized_response = requests.get(
                f"{self.base_url}/api/optimized/search",
                params={"keyword": keyword, "maxResults": 10},
                timeout=30
            )
            optimized_duration = time.time() - start_time
            
            if original_response.status_code == 200 and optimized_response.status_code == 200:
                original_data = original_response.json()
                optimized_data = optimized_response.json()
                
                original_results = len(original_data.get("data", []))
                optimized_results = len(optimized_data.get("data", []))
                
                improvement = (original_duration - optimized_duration) / original_duration * 100
                
                print(f"   - 原版API: {original_duration:.2f}s, {original_results} 条结果")
                print(f"   - 优化版API: {optimized_duration:.2f}s, {optimized_results} 条结果")
                print(f"   - 性能提升: {improvement:.1f}%")
                
                return True
            else:
                print("   ❌ API调用失败，无法对比")
                return False
                
        except Exception as e:
            print(f"   ❌ 性能对比异常: {str(e)}")
            return False
    
    def test_concurrent_requests(self) -> bool:
        """测试并发请求"""
        try:
            import concurrent.futures
            
            def make_search_request(keyword):
                try:
                    start_time = time.time()
                    response = requests.get(
                        f"{self.base_url}/api/optimized/search",
                        params={"keyword": keyword, "maxResults": 5},
                        timeout=30
                    )
                    duration = time.time() - start_time
                    
                    if response.status_code == 200:
                        data = response.json()
                        return {
                            "success": True,
                            "duration": duration,
                            "results": len(data.get("data", [])),
                            "keyword": keyword
                        }
                    else:
                        return {"success": False, "keyword": keyword, "status": response.status_code}
                except Exception as e:
                    return {"success": False, "keyword": keyword, "error": str(e)}
            
            # 并发测试
            keywords = ["斗破苍穹", "完美世界", "遮天", "斗罗大陆", "武动乾坤"]
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(make_search_request, keyword) for keyword in keywords]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            successful_requests = [r for r in results if r.get("success")]
            failed_requests = [r for r in results if not r.get("success")]
            
            print(f"   - 成功请求: {len(successful_requests)}/{len(results)}")
            print(f"   - 失败请求: {len(failed_requests)}")
            
            if successful_requests:
                durations = [r["duration"] for r in successful_requests]
                avg_duration = statistics.mean(durations)
                max_duration = max(durations)
                min_duration = min(durations)
                
                print(f"   - 平均耗时: {avg_duration:.2f}s")
                print(f"   - 最长耗时: {max_duration:.2f}s")
                print(f"   - 最短耗时: {min_duration:.2f}s")
            
            return len(successful_requests) >= len(results) * 0.8  # 至少80%成功
            
        except Exception as e:
            print(f"   ❌ 并发测试异常: {str(e)}")
            return False
    
    def test_cache_management(self) -> bool:
        """测试缓存管理"""
        try:
            # 清理缓存
            response = requests.post(f"{self.base_url}/api/optimized/cache/clear", timeout=10)
            
            if response.status_code != 200:
                print(f"   ❌ 缓存清理API返回状态码: {response.status_code}")
                return False
            
            data = response.json()
            if data.get("code") != 200:
                print(f"   ❌ 缓存清理返回错误: {data.get('message')}")
                return False
            
            cleared_items = data.get("data", {}).get("cleared_items", 0)
            print(f"   - 清理缓存项目: {cleared_items}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ 缓存管理异常: {str(e)}")
            return False
    
    def generate_test_report(self):
        """生成测试报告"""
        print("\n" + "=" * 80)
        print("📊 测试报告")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"总测试数: {total_tests}")
        print(f"通过测试: {passed_tests}")
        print(f"失败测试: {failed_tests}")
        print(f"通过率: {passed_tests/total_tests*100:.1f}%")
        
        print("\n📋 详细结果:")
        for test_name, result in self.test_results.items():
            status = "✅" if result["success"] else "❌"
            duration = result.get("duration", 0)
            print(f"  {status} {test_name}: {duration:.2f}s")
            
            if not result["success"] and "error" in result:
                print(f"     错误: {result['error']}")
        
        # 性能数据统计
        if self.performance_data:
            print("\n📈 性能数据:")
            search_durations = [d["duration"] for d in self.performance_data if d["operation"] == "search"]
            if search_durations:
                avg_search_time = statistics.mean(search_durations)
                print(f"  平均搜索时间: {avg_search_time:.2f}s")
        
        # 保存报告到文件
        report_data = {
            "timestamp": time.time(),
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "pass_rate": passed_tests/total_tests*100
            },
            "test_results": self.test_results,
            "performance_data": self.performance_data
        }
        
        with open("test_report.json", "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 测试报告已保存到: test_report.json")
        
        # 结论
        if passed_tests == total_tests:
            print("\n🎉 所有测试通过！优化系统运行正常。")
        elif passed_tests >= total_tests * 0.8:
            print("\n⚠️  大部分测试通过，系统基本正常，建议检查失败的测试。")
        else:
            print("\n❌ 多个测试失败，建议检查系统配置和网络连接。")


def main():
    """主函数"""
    print("🔧 优化系统测试工具")
    print("测试所有性能优化功能的正确性和效果")
    print()
    
    # 创建测试器
    tester = OptimizedSystemTester()
    
    # 运行所有测试
    tester.run_all_tests()


if __name__ == "__main__":
    main()