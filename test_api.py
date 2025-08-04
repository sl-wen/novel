#!/usr/bin/env python3
"""
API测试脚本
用于测试小说搜索API的各项功能
"""

import requests
import json
import time
from typing import Dict, Any

class NovelAPITester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "NovelAPITester/1.0",
            "Accept": "application/json"
        })
    
    def test_health_check(self) -> Dict[str, Any]:
        """测试健康检查端点"""
        print("🔍 测试健康检查...")
        try:
            response = self.session.get(f"{self.base_url}/api/novels/health", timeout=10)
            result = {
                "status": "success" if response.status_code == 200 else "failed",
                "status_code": response.status_code,
                "response": response.json() if response.status_code == 200 else response.text
            }
            print(f"✅ 健康检查: {result['status']}")
            return result
        except Exception as e:
            result = {"status": "error", "error": str(e)}
            print(f"❌ 健康检查失败: {str(e)}")
            return result
    
    def test_search(self, keyword: str = "斗破苍穹") -> Dict[str, Any]:
        """测试搜索功能"""
        print(f"🔍 测试搜索功能，关键词: {keyword}")
        try:
            response = self.session.get(
                f"{self.base_url}/api/novels/search",
                params={"keyword": keyword},
                timeout=30
            )
            result = {
                "status": "success" if response.status_code == 200 else "failed",
                "status_code": response.status_code,
                "response": response.json() if response.status_code == 200 else response.text
            }
            
            if result["status"] == "success":
                data = result["response"].get("data", [])
                print(f"✅ 搜索成功，找到 {len(data)} 条结果")
                for i, item in enumerate(data[:3], 1):  # 显示前3条结果
                    print(f"   {i}. {item.get('bookName', 'N/A')} - {item.get('author', 'N/A')}")
            else:
                print(f"❌ 搜索失败: {result['response']}")
            
            return result
        except Exception as e:
            result = {"status": "error", "error": str(e)}
            print(f"❌ 搜索测试失败: {str(e)}")
            return result
    
    def test_sources(self) -> Dict[str, Any]:
        """测试获取书源列表"""
        print("🔍 测试获取书源列表...")
        try:
            response = self.session.get(f"{self.base_url}/api/novels/sources", timeout=10)
            result = {
                "status": "success" if response.status_code == 200 else "failed",
                "status_code": response.status_code,
                "response": response.json() if response.status_code == 200 else response.text
            }
            
            if result["status"] == "success":
                data = result["response"].get("data", [])
                print(f"✅ 获取书源成功，共 {len(data)} 个书源")
            else:
                print(f"❌ 获取书源失败: {result['response']}")
            
            return result
        except Exception as e:
            result = {"status": "error", "error": str(e)}
            print(f"❌ 书源测试失败: {str(e)}")
            return result
    
    def test_detail(self, url: str, source_id: int = 1) -> Dict[str, Any]:
        """测试获取小说详情"""
        print(f"🔍 测试获取小说详情，URL: {url[:50]}...")
        try:
            response = self.session.get(
                f"{self.base_url}/api/novels/detail",
                params={"url": url, "sourceId": source_id},
                timeout=30
            )
            result = {
                "status": "success" if response.status_code == 200 else "failed",
                "status_code": response.status_code,
                "response": response.json() if response.status_code == 200 else response.text
            }
            
            if result["status"] == "success":
                data = result["response"].get("data", {})
                book_name = data.get("bookName", "N/A")
                print(f"✅ 获取详情成功: {book_name}")
            else:
                print(f"❌ 获取详情失败: {result['response']}")
            
            return result
        except Exception as e:
            result = {"status": "error", "error": str(e)}
            print(f"❌ 详情测试失败: {str(e)}")
            return result
    
    def run_comprehensive_test(self):
        """运行综合测试"""
        print("🚀 开始API综合测试")
        print("=" * 50)
        
        results = {}
        
        # 1. 健康检查
        results["health"] = self.test_health_check()
        print()
        
        # 2. 获取书源
        results["sources"] = self.test_sources()
        print()
        
        # 3. 搜索测试
        results["search"] = self.test_search("斗破苍穹")
        print()
        
        # 4. 如果有搜索结果，测试详情获取
        if results["search"]["status"] == "success":
            search_data = results["search"]["response"].get("data", [])
            if search_data:
                first_result = search_data[0]
                url = first_result.get("url")
                source_id = first_result.get("sourceId", 1)
                if url:
                    results["detail"] = self.test_detail(url, source_id)
                    print()
        
        # 输出测试总结
        print("=" * 50)
        print("📊 测试总结:")
        success_count = sum(1 for r in results.values() if r["status"] == "success")
        total_count = len(results)
        print(f"✅ 成功: {success_count}/{total_count}")
        
        for test_name, result in results.items():
            status_icon = "✅" if result["status"] == "success" else "❌"
            print(f"   {status_icon} {test_name}: {result['status']}")
        
        return results

def main():
    """主函数"""
    print("📚 小说API测试工具")
    print("=" * 50)
    
    # 检查API是否运行
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        if response.status_code == 200:
            print("✅ API服务正在运行")
        else:
            print("❌ API服务响应异常")
            return
    except Exception as e:
        print(f"❌ 无法连接到API服务: {str(e)}")
        print("请确保API服务正在运行: uvicorn app.main:app --reload")
        return
    
    # 运行测试
    tester = NovelAPITester()
    results = tester.run_comprehensive_test()
    
    # 保存测试结果
    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n💾 测试结果已保存到 test_results.json")

if __name__ == "__main__":
    main() 