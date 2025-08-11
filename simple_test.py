#!/usr/bin/env python3
"""
简化版测试脚本 - 无需外部依赖
用于快速验证API接口和基本功能
"""
import json
import sys
import time
import urllib.request
import urllib.parse
import urllib.error

# 配置
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/optimized"

def make_request(url, method="GET", params=None, timeout=30):
    """发送HTTP请求"""
    try:
        if params:
            query_string = urllib.parse.urlencode(params)
            if method == "GET":
                url = f"{url}?{query_string}"
            elif method == "POST":
                # 对于POST请求，参数作为query string发送（因为FastAPI端点使用Query参数）
                url = f"{url}?{query_string}"
        
        req = urllib.request.Request(url)
        if method == "POST":
            req.get_method = lambda: 'POST'
            
        with urllib.request.urlopen(req, timeout=timeout) as response:
            content = response.read().decode('utf-8')
            return {
                "status_code": response.getcode(),
                "content": content,
                "headers": dict(response.headers)
            }
    except urllib.error.HTTPError as e:
        return {
            "status_code": e.code,
            "content": e.read().decode('utf-8') if hasattr(e, 'read') else str(e),
            "headers": {}
        }
    except Exception as e:
        return {
            "status_code": 0,
            "content": str(e),
            "headers": {}
        }

def test_basic_connectivity():
    """测试基本连通性"""
    print("🔗 测试服务连通性...")
    
    response = make_request(BASE_URL, timeout=5)
    if response["status_code"] == 200:
        try:
            data = json.loads(response["content"])
            if data.get("code") == 200:
                print(f"✅ 服务连通正常 - 版本: {data.get('data', {}).get('version', 'unknown')}")
                return True
        except:
            pass
    
    print(f"❌ 服务连通失败 (HTTP {response['status_code']})")
    return False

def test_health():
    """测试健康检查"""
    print("🏥 测试健康检查...")
    
    response = make_request(f"{API_BASE}/health")
    if response["status_code"] == 200:
        try:
            data = json.loads(response["content"])
            if data.get("code") == 200:
                health_data = data.get("data", {})
                status = health_data.get("status", "unknown")
                score = health_data.get("health_score", 0)
                print(f"✅ 健康检查通过 - 状态: {status}, 分数: {score}")
                return True
        except:
            pass
    
    print(f"❌ 健康检查失败 (HTTP {response['status_code']})")
    return False

def test_sources():
    """测试获取书源"""
    print("📖 测试获取书源...")
    
    response = make_request(f"{API_BASE}/sources")
    if response["status_code"] == 200:
        try:
            data = json.loads(response["content"])
            if data.get("code") == 200:
                sources = data.get("data", [])
                print(f"✅ 获取书源成功 - 共 {len(sources)} 个书源")
                return True, sources
        except:
            pass
    
    print(f"❌ 获取书源失败 (HTTP {response['status_code']})")
    return False, []

def test_search(keyword="斗破苍穹"):
    """测试搜索功能"""
    print(f"🔍 测试搜索功能: {keyword}")
    
    response = make_request(f"{API_BASE}/search", params={"keyword": keyword, "maxResults": 5})
    if response["status_code"] == 200:
        try:
            data = json.loads(response["content"])
            if data.get("code") == 200:
                results = data.get("data", [])
                if results:
                    first_result = results[0]
                    print(f"✅ 搜索成功 - 找到 {len(results)} 个结果")
                    print(f"   第一个结果: {first_result.get('title', 'N/A')} - {first_result.get('author', 'N/A')}")
                    return True, results
                else:
                    print("⚠️ 搜索成功但无结果")
                    return False, []
        except Exception as e:
            print(f"❌ 搜索响应解析失败: {e}")
    
    print(f"❌ 搜索失败 (HTTP {response['status_code']})")
    return False, []

def test_detail(url, source_id):
    """测试获取详情"""
    print("📋 测试获取详情...")
    
    response = make_request(f"{API_BASE}/detail", params={"url": url, "sourceId": source_id})
    if response["status_code"] == 200:
        try:
            data = json.loads(response["content"])
            if data.get("code") == 200:
                book = data.get("data", {})
                print(f"✅ 获取详情成功 - 书名: {book.get('title', 'N/A')}")
                return True, book
        except:
            pass
    
    print(f"❌ 获取详情失败 (HTTP {response['status_code']})")
    return False, {}

def test_toc(url, source_id):
    """测试获取目录"""
    print("📑 测试获取目录...")
    
    response = make_request(f"{API_BASE}/toc", params={"url": url, "sourceId": source_id})
    if response["status_code"] == 200:
        try:
            data = json.loads(response["content"])
            if data.get("code") == 200:
                toc = data.get("data", [])
                print(f"✅ 获取目录成功 - 共 {len(toc)} 章")
                if toc:
                    print(f"   第一章: {toc[0].get('title', 'N/A')}")
                    print(f"   最后章: {toc[-1].get('title', 'N/A')}")
                return True, toc
        except:
            pass
    
    print(f"❌ 获取目录失败 (HTTP {response['status_code']})")
    return False, []

def test_async_download_start(url, source_id, format="txt"):
    """测试启动异步下载"""
    print(f"🚀 测试启动异步下载 (格式: {format})...")
    
    response = make_request(
        f"{API_BASE}/download/start", 
        method="POST",
        params={"url": url, "sourceId": source_id, "format": format}
    )
    
    if response["status_code"] == 202:
        try:
            data = json.loads(response["content"])
            if data.get("code") == 202:
                task_id = data.get("data", {}).get("task_id")
                if task_id:
                    print(f"✅ 异步下载启动成功 - task_id: {task_id}")
                    return True, task_id
        except:
            pass
    
    print(f"❌ 启动异步下载失败 (HTTP {response['status_code']})")
    return False, None

def test_download_progress(task_id, max_attempts=30):
    """测试下载进度轮询"""
    print("⏳ 测试下载进度轮询...")
    
    for attempt in range(max_attempts):
        response = make_request(f"{API_BASE}/download/progress", params={"task_id": task_id})
        
        if response["status_code"] == 200:
            try:
                data = json.loads(response["content"])
                if data.get("code") == 200:
                    progress = data.get("data", {})
                    status = progress.get("status", "unknown")
                    completed = progress.get("completed_chapters", 0)
                    total = progress.get("total_chapters", 0)
                    
                    print(f"   轮询 #{attempt + 1}: {status} - {completed}/{total}")
                    
                    if status == "completed":
                        print("✅ 下载完成")
                        return True, "completed"
                    elif status == "failed":
                        error_msg = progress.get("error_message", "未知错误")
                        print(f"❌ 下载失败: {error_msg}")
                        return False, "failed"
                    elif attempt < max_attempts - 1:
                        time.sleep(2)  # 等待2秒后重试
            except:
                pass
        
        if attempt == max_attempts - 1:
            print(f"❌ 轮询超时 (尝试了 {max_attempts} 次)")
            return False, "timeout"
    
    return False, "unknown"

def test_download_result(task_id):
    """测试获取下载结果"""
    print("📥 测试获取下载结果...")
    
    response = make_request(f"{API_BASE}/download/result", params={"task_id": task_id})
    if response["status_code"] == 200:
        content_length = response["headers"].get("Content-Length", "0")
        filename = response["headers"].get("Content-Disposition", "")
        
        # 验证内容不为空
        content = response["content"]
        if content and len(content) > 100:  # 基本内容检查
            print(f"✅ 获取下载结果成功 - 大小: {content_length} 字节")
            print(f"   文件名: {filename}")
            print(f"   内容预览: {content[:100]}...")
            return True
    
    print(f"❌ 获取下载结果失败 (HTTP {response['status_code']})")
    return False

def main():
    """主函数"""
    print("🚀 启动简化版功能测试...\n")
    
    test_results = {}
    
    # 1. 基本连通性测试
    test_results["connectivity"] = test_basic_connectivity()
    if not test_results["connectivity"]:
        print("\n❌ 服务连通性测试失败，终止测试")
        return 1
    
    # 2. 健康检查
    test_results["health"] = test_health()
    
    # 3. 获取书源
    test_results["sources"], sources = test_sources()
    
    # 4. 搜索测试
    test_results["search"], search_results = test_search()
    
    if test_results["search"] and search_results:
        # 使用第一个搜索结果进行后续测试
        first_book = search_results[0]
        book_url = first_book.get("url")
        source_id = first_book.get("sourceId", 1)
        
        # 5. 获取详情
        test_results["detail"], _ = test_detail(book_url, source_id)
        
        # 6. 获取目录
        test_results["toc"], toc = test_toc(book_url, source_id)
        
        # 7. 异步下载和轮询测试
        if test_results["toc"]:
            print(f"\n💾 开始下载测试...")
            
            # 启动异步下载
            test_results["download_start"], task_id = test_async_download_start(book_url, source_id)
            
            if test_results["download_start"] and task_id:
                # 轮询进度
                test_results["polling"], final_status = test_download_progress(task_id)
                
                # 获取结果
                if final_status == "completed":
                    test_results["download_result"] = test_download_result(task_id)
                else:
                    test_results["download_result"] = False
    
    # 生成简化报告
    print(f"\n{'='*50}")
    print("简化版测试报告")
    print(f"{'='*50}")
    
    test_names = {
        "connectivity": "服务连通性",
        "health": "健康检查",
        "sources": "获取书源",
        "search": "搜索功能", 
        "detail": "获取详情",
        "toc": "获取目录",
        "download_start": "启动下载",
        "polling": "轮询功能",
        "download_result": "获取结果"
    }
    
    success_count = 0
    total_count = 0
    
    for key, name in test_names.items():
        if key in test_results:
            total_count += 1
            if test_results[key]:
                success_count += 1
                print(f"✅ {name}")
            else:
                print(f"❌ {name}")
    
    success_rate = (success_count / total_count * 100) if total_count > 0 else 0
    
    print(f"\n📊 统计: {success_count}/{total_count} 通过 ({success_rate:.1f}%)")
    
    # 核心功能验证
    core_functions = ["connectivity", "search", "detail", "toc"]
    core_working = all(test_results.get(func, False) for func in core_functions)
    
    async_functions = ["download_start", "polling", "download_result"]
    async_working = all(test_results.get(func, False) for func in async_functions)
    
    print(f"\n🎯 功能状态:")
    print(f"{'核心功能':<10} {'✅ 正常' if core_working else '❌ 异常'}")
    print(f"{'异步下载':<10} {'✅ 正常' if async_working else '❌ 异常'}")
    
    if core_working and async_working:
        print(f"\n🎉 所有功能测试通过！")
        return 0
    elif core_working:
        print(f"\n⚠️ 核心功能正常，异步功能有问题")
        return 1
    else:
        print(f"\n❌ 核心功能异常")
        return 1

if __name__ == "__main__":
    try:
        exit(main())
    except KeyboardInterrupt:
        print(f"\n⚠️ 测试被用户中断")
        exit(1)
    except Exception as e:
        print(f"\n❌ 测试脚本异常: {e}")
        exit(1)