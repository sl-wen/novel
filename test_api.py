#!/usr/bin/env python3
"""
测试小说搜索API
"""

import requests
import json
import sys
from urllib.parse import quote

def test_novel_search_api():
    """测试小说搜索API"""
    
    # 测试URL
    base_url = "https://slwen.cn"
    search_endpoint = "/api/novels/search"
    
    # 测试关键词
    keywords = ["修真", "都市", "玄幻", "修仙"]
    
    print("=== 小说搜索API测试 ===")
    print(f"基础URL: {base_url}")
    print(f"搜索端点: {search_endpoint}")
    print()
    
    for keyword in keywords:
        print(f"测试关键词: {keyword}")
        
        # 构建URL
        encoded_keyword = quote(keyword)
        url = f"{base_url}{search_endpoint}?keyword={encoded_keyword}"
        
        print(f"请求URL: {url}")
        
        try:
            # 发送请求
            headers = {
                "Accept": "application/json",
                "User-Agent": "Novel-API-Test/1.0"
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            
            print(f"状态码: {response.status_code}")
            print(f"响应头: {dict(response.headers)}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
                    
                    # 检查响应结构
                    if "results" in data:
                        print(f"找到 {len(data['results'])} 个结果")
                        if data['results']:
                            first_result = data['results'][0]
                            print(f"第一个结果: {first_result.get('title', 'N/A')} - {first_result.get('author', 'N/A')}")
                    else:
                        print("响应中没有找到 'results' 字段")
                        
                except json.JSONDecodeError as e:
                    print(f"JSON解析错误: {e}")
                    print(f"响应内容: {response.text[:500]}...")
            else:
                print(f"请求失败: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"请求异常: {e}")
        
        print("-" * 50)
        print()

def test_health_check():
    """测试健康检查端点"""
    print("=== 健康检查测试 ===")
    
    health_url = "https://slwen.cn/novel/health"
    print(f"健康检查URL: {health_url}")
    
    try:
        response = requests.get(health_url, timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"健康检查失败: {e}")
    
    print("-" * 50)
    print()

def test_api_docs():
    """测试API文档端点"""
    print("=== API文档测试 ===")
    
    docs_url = "https://slwen.cn/novel/docs"
    print(f"API文档URL: {docs_url}")
    
    try:
        response = requests.get(docs_url, timeout=10)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            print("API文档可访问")
        else:
            print(f"API文档访问失败: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"API文档测试失败: {e}")
    
    print("-" * 50)
    print()

if __name__ == "__main__":
    print("开始测试小说搜索API...")
    print()
    
    # 测试健康检查
    test_health_check()
    
    # 测试API文档
    test_api_docs()
    
    # 测试搜索API
    test_novel_search_api()
    
    print("测试完成！")