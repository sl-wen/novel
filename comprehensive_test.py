#!/usr/bin/env python3
"""
综合功能测试脚本
测试搜索、文章内容获取、下载和轮询功能
"""
import json
import os
import time
from typing import Dict, List, Optional

import requests

# 配置
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/optimized"
TIMEOUT = 30
DOWNLOAD_TIMEOUT = 300
MAX_POLL_ATTEMPTS = 60  # 最多轮询2分钟

# 测试用例配置
TEST_CASES = [
    {
        "name": "测试案例1 - 热门小说",
        "search_keyword": "斗破苍穹",
        "expected_results": 1,
        "test_download": True,
        "download_format": "txt"
    },
    {
        "name": "测试案例2 - 经典小说", 
        "search_keyword": "完美世界",
        "expected_results": 1,
        "test_download": True,
        "download_format": "epub"
    }
]

class TestResult:
    """测试结果类"""
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.success = False
        self.error_message = ""
        self.duration_ms = 0
        self.details = {}

class ComprehensiveTest:
    """综合测试类"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.session = requests.Session()
        
    def log(self, message: str, level: str = "INFO"):
        """日志输出"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def test_health_check(self) -> TestResult:
        """测试健康检查"""
        result = TestResult("健康检查")
        start_time = time.time()
        
        try:
            self.log("开始健康检查...")
            response = self.session.get(f"{API_BASE}/health", timeout=TIMEOUT)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 200:
                    health_data = data.get("data", {})
                    health_status = health_data.get("status", "unknown")
                    health_score = health_data.get("health_score", 0)
                    
                    result.success = True
                    result.details = {
                        "status": health_status,
                        "health_score": health_score,
                        "response_time_ms": (time.time() - start_time) * 1000
                    }
                    self.log(f"✅ 健康检查通过 - 状态: {health_status}, 分数: {health_score}")
                else:
                    result.error_message = f"健康检查返回错误: {data.get('message')}"
            else:
                result.error_message = f"健康检查HTTP错误: {response.status_code}"
                
        except Exception as e:
            result.error_message = f"健康检查异常: {str(e)}"
            self.log(f"❌ 健康检查失败: {str(e)}", "ERROR")
            
        result.duration_ms = (time.time() - start_time) * 1000
        return result
    
    def test_get_sources(self) -> TestResult:
        """测试获取书源"""
        result = TestResult("获取书源")
        start_time = time.time()
        
        try:
            self.log("开始获取书源列表...")
            response = self.session.get(f"{API_BASE}/sources", timeout=TIMEOUT)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 200:
                    sources = data.get("data", [])
                    result.success = True
                    result.details = {
                        "source_count": len(sources),
                        "sources": [{"id": s.get("id"), "name": s.get("rule", {}).get("name")} for s in sources[:3]]
                    }
                    self.log(f"✅ 获取书源成功 - 共 {len(sources)} 个书源")
                else:
                    result.error_message = f"获取书源返回错误: {data.get('message')}"
            else:
                result.error_message = f"获取书源HTTP错误: {response.status_code}"
                
        except Exception as e:
            result.error_message = f"获取书源异常: {str(e)}"
            self.log(f"❌ 获取书源失败: {str(e)}", "ERROR")
            
        result.duration_ms = (time.time() - start_time) * 1000
        return result
    
    def test_search(self, keyword: str, expected_results: int = 1) -> TestResult:
        """测试搜索功能"""
        result = TestResult(f"搜索-{keyword}")
        start_time = time.time()
        
        try:
            self.log(f"开始搜索: {keyword}")
            response = self.session.get(
                f"{API_BASE}/search",
                params={"keyword": keyword, "maxResults": 10},
                timeout=TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 200:
                    search_results = data.get("data", [])
                    if len(search_results) >= expected_results:
                        result.success = True
                        result.details = {
                            "keyword": keyword,
                            "result_count": len(search_results),
                            "first_result": search_results[0] if search_results else None,
                            "duration_ms": data.get("meta", {}).get("duration_ms", 0)
                        }
                        self.log(f"✅ 搜索成功 - 关键词: {keyword}, 结果数: {len(search_results)}")
                        return result, search_results
                    else:
                        result.error_message = f"搜索结果不足，期望≥{expected_results}，实际{len(search_results)}"
                else:
                    result.error_message = f"搜索返回错误: {data.get('message')}"
            else:
                result.error_message = f"搜索HTTP错误: {response.status_code}"
                
        except Exception as e:
            result.error_message = f"搜索异常: {str(e)}"
            self.log(f"❌ 搜索失败: {str(e)}", "ERROR")
            
        result.duration_ms = (time.time() - start_time) * 1000
        return result, []
    
    def test_get_detail(self, url: str, source_id: int) -> TestResult:
        """测试获取书籍详情"""
        result = TestResult("获取详情")
        start_time = time.time()
        
        try:
            self.log(f"开始获取详情: {url}")
            response = self.session.get(
                f"{API_BASE}/detail",
                params={"url": url, "sourceId": source_id},
                timeout=TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 200:
                    book_detail = data.get("data", {})
                    result.success = True
                    result.details = {
                        "title": book_detail.get("title"),
                        "author": book_detail.get("author"),
                        "intro_length": len(book_detail.get("intro", "")),
                        "category": book_detail.get("category"),
                        "duration_ms": data.get("meta", {}).get("duration_ms", 0)
                    }
                    self.log(f"✅ 获取详情成功 - 书名: {book_detail.get('title')}")
                    return result, book_detail
                else:
                    result.error_message = f"获取详情返回错误: {data.get('message')}"
            else:
                result.error_message = f"获取详情HTTP错误: {response.status_code}"
                
        except Exception as e:
            result.error_message = f"获取详情异常: {str(e)}"
            self.log(f"❌ 获取详情失败: {str(e)}", "ERROR")
            
        result.duration_ms = (time.time() - start_time) * 1000
        return result, {}
    
    def test_get_toc(self, url: str, source_id: int) -> TestResult:
        """测试获取目录"""
        result = TestResult("获取目录")
        start_time = time.time()
        
        try:
            self.log(f"开始获取目录: {url}")
            response = self.session.get(
                f"{API_BASE}/toc",
                params={"url": url, "sourceId": source_id},
                timeout=TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 200:
                    toc = data.get("data", [])
                    result.success = True
                    result.details = {
                        "chapter_count": len(toc),
                        "first_chapter": toc[0] if toc else None,
                        "last_chapter": toc[-1] if toc else None,
                        "duration_ms": data.get("meta", {}).get("duration_ms", 0)
                    }
                    self.log(f"✅ 获取目录成功 - 章节数: {len(toc)}")
                    return result, toc
                else:
                    result.error_message = f"获取目录返回错误: {data.get('message')}"
            else:
                result.error_message = f"获取目录HTTP错误: {response.status_code}"
                
        except Exception as e:
            result.error_message = f"获取目录异常: {str(e)}"
            self.log(f"❌ 获取目录失败: {str(e)}", "ERROR")
            
        result.duration_ms = (time.time() - start_time) * 1000
        return result, []
    
    def test_sync_download(self, url: str, source_id: int, format: str = "txt") -> TestResult:
        """测试同步下载"""
        result = TestResult(f"同步下载-{format}")
        start_time = time.time()
        
        try:
            self.log(f"开始同步下载: {url} (格式: {format})")
            response = self.session.get(
                f"{API_BASE}/download",
                params={"url": url, "sourceId": source_id, "format": format},
                timeout=DOWNLOAD_TIMEOUT,
                stream=True
            )
            
            if response.status_code == 200:
                # 获取文件信息
                content_length = response.headers.get("Content-Length", "0")
                filename = response.headers.get("Content-Disposition", "")
                task_id = response.headers.get("X-Task-ID", "")
                
                # 读取部分内容验证
                content_chunk = b""
                chunk_count = 0
                for chunk in response.iter_content(chunk_size=8192):
                    content_chunk += chunk
                    chunk_count += 1
                    if chunk_count >= 3:  # 只读取前几个chunk验证
                        break
                
                result.success = True
                result.details = {
                    "format": format,
                    "file_size": int(content_length) if content_length.isdigit() else 0,
                    "filename": filename,
                    "task_id": task_id,
                    "content_preview": content_chunk[:200].decode('utf-8', errors='ignore'),
                    "chunk_count": chunk_count
                }
                self.log(f"✅ 同步下载成功 - 格式: {format}, 大小: {content_length} 字节")
            else:
                result.error_message = f"同步下载HTTP错误: {response.status_code}"
                
        except Exception as e:
            result.error_message = f"同步下载异常: {str(e)}"
            self.log(f"❌ 同步下载失败: {str(e)}", "ERROR")
            
        result.duration_ms = (time.time() - start_time) * 1000
        return result
    
    def test_async_download_with_polling(self, url: str, source_id: int, format: str = "txt") -> TestResult:
        """测试异步下载和轮询功能"""
        result = TestResult(f"异步下载+轮询-{format}")
        start_time = time.time()
        
        try:
            # 1. 启动异步下载任务
            self.log(f"启动异步下载任务: {url} (格式: {format})")
            start_response = self.session.post(
                f"{API_BASE}/download/start",
                params={"url": url, "sourceId": source_id, "format": format},
                timeout=TIMEOUT
            )
            
            if start_response.status_code != 202:
                result.error_message = f"启动任务失败: HTTP {start_response.status_code}"
                return result
                
            start_data = start_response.json()
            if start_data.get("code") != 202:
                result.error_message = f"启动任务失败: {start_data.get('message')}"
                return result
                
            task_id = start_data.get("data", {}).get("task_id")
            if not task_id:
                result.error_message = "启动任务失败: 未获取到task_id"
                return result
                
            self.log(f"✅ 任务启动成功 - task_id: {task_id}")
            
            # 2. 轮询下载进度
            self.log("开始轮询下载进度...")
            poll_count = 0
            final_status = None
            progress_history = []
            
            for attempt in range(MAX_POLL_ATTEMPTS):
                poll_count += 1
                time.sleep(2)  # 等待2秒
                
                try:
                    progress_response = self.session.get(
                        f"{API_BASE}/download/progress",
                        params={"task_id": task_id},
                        timeout=TIMEOUT
                    )
                    
                    if progress_response.status_code == 200:
                        progress_data = progress_response.json()
                        if progress_data.get("code") == 200:
                            progress_info = progress_data.get("data", {})
                            status = progress_info.get("status", "unknown")
                            completed_chapters = progress_info.get("completed_chapters", 0)
                            total_chapters = progress_info.get("total_chapters", 0)
                            
                            progress_history.append({
                                "attempt": attempt + 1,
                                "status": status,
                                "progress": f"{completed_chapters}/{total_chapters}"
                            })
                            
                            self.log(f"进度查询 #{attempt + 1}: {status} - {completed_chapters}/{total_chapters}")
                            
                            if status in ["completed", "failed"]:
                                final_status = status
                                break
                        else:
                            self.log(f"⚠️ 进度查询返回错误: {progress_data.get('message')}")
                    else:
                        self.log(f"⚠️ 进度查询HTTP错误: {progress_response.status_code}")
                        
                except Exception as e:
                    self.log(f"⚠️ 进度查询异常: {str(e)}")
                    
            if final_status != "completed":
                result.error_message = f"下载未完成，最终状态: {final_status}, 轮询次数: {poll_count}"
                return result
                
            # 3. 获取下载结果
            self.log("获取下载结果...")
            result_response = self.session.get(
                f"{API_BASE}/download/result",
                params={"task_id": task_id},
                timeout=DOWNLOAD_TIMEOUT,
                stream=True
            )
            
            if result_response.status_code == 200:
                # 获取文件信息
                content_length = result_response.headers.get("Content-Length", "0")
                filename = result_response.headers.get("Content-Disposition", "")
                
                # 读取部分内容验证
                content_chunk = b""
                chunk_count = 0
                for chunk in result_response.iter_content(chunk_size=8192):
                    content_chunk += chunk
                    chunk_count += 1
                    if chunk_count >= 3:  # 只读取前几个chunk验证
                        break
                
                result.success = True
                result.details = {
                    "task_id": task_id,
                    "format": format,
                    "file_size": int(content_length) if content_length.isdigit() else 0,
                    "filename": filename,
                    "poll_count": poll_count,
                    "progress_history": progress_history[-5:],  # 最后5次进度记录
                    "content_preview": content_chunk[:200].decode('utf-8', errors='ignore')
                }
                self.log(f"✅ 异步下载+轮询成功 - 轮询次数: {poll_count}, 文件大小: {content_length} 字节")
            else:
                result.error_message = f"获取结果HTTP错误: {result_response.status_code}"
                
        except Exception as e:
            result.error_message = f"异步下载+轮询异常: {str(e)}"
            self.log(f"❌ 异步下载+轮询失败: {str(e)}", "ERROR")
            
        result.duration_ms = (time.time() - start_time) * 1000
        return result
    
    def test_performance_stats(self) -> TestResult:
        """测试性能统计"""
        result = TestResult("性能统计")
        start_time = time.time()
        
        try:
            self.log("获取性能统计...")
            response = self.session.get(f"{API_BASE}/performance", timeout=TIMEOUT)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 200:
                    perf_data = data.get("data", {})
                    result.success = True
                    result.details = {
                        "performance": perf_data.get("performance", {}),
                        "cache": perf_data.get("cache", {}),
                        "http": perf_data.get("http", {}),
                        "slow_operations_count": len(perf_data.get("slow_operations", []))
                    }
                    self.log("✅ 性能统计获取成功")
                else:
                    result.error_message = f"性能统计返回错误: {data.get('message')}"
            else:
                result.error_message = f"性能统计HTTP错误: {response.status_code}"
                
        except Exception as e:
            result.error_message = f"性能统计异常: {str(e)}"
            self.log(f"❌ 性能统计失败: {str(e)}", "ERROR")
            
        result.duration_ms = (time.time() - start_time) * 1000
        return result
    
    def run_comprehensive_test(self):
        """运行综合测试"""
        self.log("=" * 60)
        self.log("开始综合功能测试")
        self.log("=" * 60)
        
        total_start_time = time.time()
        
        # 1. 基础功能测试
        self.log("\n🔍 [阶段1] 基础功能测试")
        self.results.append(self.test_health_check())
        self.results.append(self.test_get_sources())
        self.results.append(self.test_performance_stats())
        
        # 2. 搜索和内容获取测试
        self.log("\n📚 [阶段2] 搜索和内容测试")
        
        for test_case in TEST_CASES:
            self.log(f"\n--- {test_case['name']} ---")
            
            # 搜索测试
            search_result, search_results = self.test_search(
                test_case["search_keyword"], 
                test_case["expected_results"]
            )
            self.results.append(search_result)
            
            if search_result.success and search_results:
                # 使用第一个搜索结果进行后续测试
                first_book = search_results[0]
                book_url = first_book.get("url")
                source_id = first_book.get("sourceId", 2)  # 默认使用书海阁小说网
                
                # 获取详情测试
                detail_result, book_detail = self.test_get_detail(book_url, source_id)
                self.results.append(detail_result)
                
                # 获取目录测试
                toc_result, toc = self.test_get_toc(book_url, source_id)
                self.results.append(toc_result)
                
                # 下载测试（如果启用）
                if test_case.get("test_download", False) and toc_result.success:
                    self.log(f"\n💾 [阶段3] 下载测试 - {test_case['name']}")
                    
                    # 同步下载测试
                    sync_download_result = self.test_sync_download(
                        book_url, source_id, test_case["download_format"]
                    )
                    self.results.append(sync_download_result)
                    
                    # 异步下载+轮询测试
                    async_download_result = self.test_async_download_with_polling(
                        book_url, source_id, test_case["download_format"]
                    )
                    self.results.append(async_download_result)
                    
                    # 只测试第一个案例的下载，避免过长
                    break
            else:
                self.log(f"⚠️ 跳过 {test_case['name']} 的后续测试（搜索失败）")
        
        # 生成测试报告
        total_duration = (time.time() - total_start_time) * 1000
        self.generate_test_report(total_duration)
    
    def generate_test_report(self, total_duration_ms: float):
        """生成测试报告"""
        self.log("\n" + "=" * 60)
        self.log("测试报告")
        self.log("=" * 60)
        
        success_count = sum(1 for r in self.results if r.success)
        total_count = len(self.results)
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0
        
        self.log(f"\n📊 总体统计:")
        self.log(f"  总测试数: {total_count}")
        self.log(f"  成功数: {success_count}")
        self.log(f"  失败数: {total_count - success_count}")
        self.log(f"  成功率: {success_rate:.1f}%")
        self.log(f"  总耗时: {total_duration_ms:.1f}ms")
        
        self.log(f"\n📋 详细结果:")
        for i, result in enumerate(self.results, 1):
            status = "✅ 成功" if result.success else "❌ 失败"
            self.log(f"  {i:2d}. {result.test_name:<20} {status:<8} ({result.duration_ms:6.1f}ms)")
            if not result.success:
                self.log(f"      错误: {result.error_message}")
            elif result.details:
                # 显示关键信息
                key_info = []
                details = result.details
                if "result_count" in details:
                    key_info.append(f"结果数:{details['result_count']}")
                if "chapter_count" in details:
                    key_info.append(f"章节数:{details['chapter_count']}")
                if "file_size" in details and details["file_size"] > 0:
                    key_info.append(f"文件大小:{details['file_size']}字节")
                if "poll_count" in details:
                    key_info.append(f"轮询次数:{details['poll_count']}")
                if key_info:
                    self.log(f"      详情: {', '.join(key_info)}")
        
        # 功能验证总结
        self.log(f"\n🎯 功能验证:")
        function_tests = {
            "搜索功能": any("搜索" in r.test_name and r.success for r in self.results),
            "详情获取": any("获取详情" in r.test_name and r.success for r in self.results),
            "目录获取": any("获取目录" in r.test_name and r.success for r in self.results),
            "同步下载": any("同步下载" in r.test_name and r.success for r in self.results),
            "异步下载": any("异步下载" in r.test_name and r.success for r in self.results),
            "轮询功能": any("轮询" in r.test_name and r.success for r in self.results),
            "健康检查": any("健康检查" in r.test_name and r.success for r in self.results),
            "性能统计": any("性能统计" in r.test_name and r.success for r in self.results),
        }
        
        for func_name, is_working in function_tests.items():
            status = "✅ 正常" if is_working else "❌ 异常"
            self.log(f"  {func_name:<8} {status}")
        
        # 最终结论
        all_core_working = all([
            function_tests["搜索功能"],
            function_tests["详情获取"], 
            function_tests["目录获取"],
            function_tests["同步下载"] or function_tests["异步下载"]  # 至少一种下载方式工作
        ])
        
        self.log(f"\n🏆 最终结论:")
        if all_core_working:
            self.log("✅ 核心功能全部正常！")
            if function_tests["异步下载"] and function_tests["轮询功能"]:
                self.log("✅ 异步下载和轮询功能正常！")
            self.log("✅ 系统运行状态良好！")
        else:
            self.log("❌ 部分核心功能异常！")
            
        return all_core_working

def main():
    """主函数"""
    print("🚀 启动综合功能测试...")
    
    # 检查服务是否运行
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code != 200:
            print(f"❌ 服务未运行或异常 (HTTP {response.status_code})")
            print("请先启动服务: python app/main.py")
            return 1
    except Exception as e:
        print(f"❌ 无法连接到服务: {str(e)}")
        print("请确保服务正在运行: python app/main.py")
        return 1
    
    # 运行测试
    tester = ComprehensiveTest()
    success = tester.run_comprehensive_test()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())