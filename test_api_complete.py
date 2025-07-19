#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整的API测试脚本
"""

import requests
import json
import time


class APITester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def test_root(self):
        """测试根目录API"""
        print("=" * 50)
        print("测试根目录API")
        try:
            response = self.session.get(f"{self.base_url}/")
            print(f"状态码: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
                return True
            else:
                print(f"错误: {response.text}")
                return False
        except Exception as e:
            print(f"异常: {str(e)}")
            return False
            
    def test_sources(self):
        """测试获取书源列表API"""
        print("=" * 50)
        print("测试获取书源列表API")
        try:
            response = self.session.get(f"{self.base_url}/api/novels/sources")
            print(f"状态码: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                sources_count = len(data.get('data', []))
                print(f"找到 {sources_count} 个书源")
                for source in data.get('data', []):
                    source_info = source.get('rule', {})
                    print(f"  - ID: {source_info.get('id')}, 名称: {source_info.get('name')}, URL: {source_info.get('url')}")
                return data.get('data', [])
            else:
                print(f"错误: {response.text}")
                return []
        except Exception as e:
            print(f"异常: {str(e)}")
            return []
            
    def test_search(self, keyword="斗破苍穹"):
        """测试搜索API"""
        print("=" * 50)
        print(f"测试搜索API - 关键词: {keyword}")
        try:
            response = self.session.get(f"{self.base_url}/api/novels/search", 
                                      params={"keyword": keyword})
            print(f"状态码: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                results = data.get('data', [])
                print(f"找到 {len(results)} 条搜索结果")
                
                for i, result in enumerate(results[:3]):  # 只显示前3个结果
                    print(f"  结果 {i+1}:")
                    print(f"    书名: {result.get('bookName')}")
                    print(f"    作者: {result.get('author')}")
                    print(f"    书源: {result.get('sourceName')}")
                    print(f"    URL: {result.get('url')}")
                    print(f"    最新章节: {result.get('latestChapter')}")
                    
                return results
            else:
                print(f"错误: {response.text}")
                return []
        except Exception as e:
            print(f"异常: {str(e)}")
            return []
            
    def test_book_detail(self, book_url, source_id=1):
        """测试获取书籍详情API"""
        print("=" * 50)
        print(f"测试获取书籍详情API")
        print(f"URL: {book_url}")
        print(f"书源ID: {source_id}")
        try:
            response = self.session.get(f"{self.base_url}/api/novels/detail", 
                                      params={"url": book_url, "sourceId": source_id})
            print(f"状态码: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                book_info = data.get('data', {})
                print(f"书名: {book_info.get('bookName')}")
                print(f"作者: {book_info.get('author')}")
                print(f"简介: {book_info.get('intro', '')[:100]}...")
                print(f"分类: {book_info.get('category')}")
                print(f"状态: {book_info.get('status')}")
                return book_info
            else:
                print(f"错误: {response.text}")
                return None
        except Exception as e:
            print(f"异常: {str(e)}")
            return None
            
    def test_toc(self, book_url, source_id=1):
        """测试获取目录API"""
        print("=" * 50)
        print(f"测试获取目录API")
        try:
            response = self.session.get(f"{self.base_url}/api/novels/toc", 
                                      params={"url": book_url, "sourceId": source_id})
            print(f"状态码: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                chapters = data.get('data', [])
                print(f"找到 {len(chapters)} 个章节")
                
                # 显示前5个章节
                for i, chapter in enumerate(chapters[:5]):
                    print(f"  章节 {chapter.get('order')}: {chapter.get('title')}")
                    
                return chapters
            else:
                print(f"错误: {response.text}")
                return []
        except Exception as e:
            print(f"异常: {str(e)}")
            return []
            
    def run_all_tests(self):
        """运行所有测试"""
        print("开始完整的API功能测试")
        print("=" * 50)
        
        # 1. 测试根目录
        self.test_root()
        
        # 2. 测试书源列表
        sources = self.test_sources()
        
        # 3. 测试搜索
        search_results = self.test_search("斗破苍穹")
        
        # 如果有搜索结果，继续测试其他API
        if search_results:
            first_result = search_results[0]
            book_url = first_result.get('url')
            source_id = first_result.get('sourceId')
            
            if book_url:
                # 4. 测试书籍详情
                book_info = self.test_book_detail(book_url, source_id)
                
                # 5. 测试目录
                chapters = self.test_toc(book_url, source_id)
                
        print("=" * 50)
        print("API测试完成！")


if __name__ == "__main__":
    tester = APITester()
    tester.run_all_tests() 