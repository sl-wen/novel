#!/usr/bin/env python3
"""
简化的目录解析调试工具
直接测试核心逻辑
"""

import requests
import json
from bs4 import BeautifulSoup

def simple_toc_debug():
    """简化的目录解析调试"""
    print("🔍 简化的目录解析调试")
    print("=" * 50)
    
    # 测试URL
    test_url = "https://www.0xs.net/txt/1.html"
    
    print(f"测试URL: {test_url}")
    
    # 1. 直接获取HTML
    print("\n1. 直接获取HTML...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://www.0xs.net/',
        }
        
        response = requests.get(test_url, headers=headers, timeout=30, verify=False)
        print(f"   响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            html = response.text
            print(f"   HTML长度: {len(html)}")
            print(f"   HTML预览: {html[:200]}...")
            
            # 2. 解析HTML
            print("\n2. 解析HTML...")
            soup = BeautifulSoup(html, "html.parser")
            
            # 3. 查找所有链接
            print("\n3. 查找所有链接...")
            all_links = soup.find_all("a")
            print(f"   总链接数: {len(all_links)}")
            
            # 4. 查找章节相关链接
            print("\n4. 查找章节相关链接...")
            chapter_links = []
            for link in all_links:
                text = link.get_text(strip=True)
                href = link.get("href", "")
                if any(keyword in text for keyword in ["第", "章", "节", "回"]) or "txt" in href:
                    chapter_links.append((text, href))
            
            print(f"   章节相关链接数: {len(chapter_links)}")
            for i, (text, href) in enumerate(chapter_links[:10]):
                print(f"     {i+1}. {text} - {href}")
            
            # 5. 测试选择器
            print("\n5. 测试选择器...")
            selectors = [
                ".catalog li a",
                ".catalog > div > ul > ul > li > a",
                ".catalog a",
                "li a",
                "a",
                "a[href*='txt']",
                "a[href*='.html']"
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                print(f"   选择器 '{selector}': 找到 {len(elements)} 个元素")
                if elements:
                    print(f"     第一个元素: {elements[0].get_text(strip=True)}")
                    print(f"     第一个href: {elements[0].get('href', '无href')}")
            
            # 6. 查找catalog元素
            print("\n6. 查找catalog元素...")
            catalog_elements = soup.find_all(class_=lambda x: x and "catalog" in x)
            print(f"   catalog相关元素: {len(catalog_elements)}")
            
            for i, elem in enumerate(catalog_elements):
                print(f"     {i+1}. {elem}")
                links = elem.find_all("a")
                print(f"       包含 {len(links)} 个链接")
                if links:
                    for j, link in enumerate(links[:3]):
                        print(f"         {j+1}. {link.get_text(strip=True)} - {link.get('href', '无href')}")
            
            # 7. 测试API
            print("\n7. 测试API...")
            api_response = requests.get(
                "http://localhost:8000/api/novels/toc",
                params={
                    "url": test_url,
                    "sourceId": 11
                },
                timeout=30
            )
            
            print(f"   API响应状态码: {api_response.status_code}")
            if api_response.status_code == 200:
                data = api_response.json()
                chapters = data.get("data", [])
                print(f"   API返回章节数: {len(chapters)}")
                
                if chapters:
                    print("   API章节预览:")
                    for i, chapter in enumerate(chapters[:3]):
                        print(f"     {i+1}. {chapter.get('title', '无标题')}")
                else:
                    print("   ❌ API返回空章节列表")
            else:
                print(f"   ❌ API请求失败: {api_response.text}")
                
        else:
            print(f"   ❌ 请求失败: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ 调试异常: {str(e)}")

def test_different_source():
    """测试不同的书源"""
    print("\n🔧 测试不同的书源")
    print("=" * 50)
    
    # 测试不同的书源
    test_sources = [
        {
            "id": 2,
            "name": "书海阁小说网",
            "url": "https://www.shuhaige.net/"
        },
        {
            "id": 8,
            "name": "大熊猫文学",
            "url": "https://www.dxmwx.org/"
        },
        {
            "id": 12,
            "name": "得奇小说网",
            "url": "https://www.deqixs.com/"
        }
    ]
    
    for source in test_sources:
        print(f"\n测试书源: {source['name']}")
        
        try:
            # 搜索获取URL
            search_response = requests.get(
                "http://localhost:8000/api/novels/search",
                params={"keyword": "斗破苍穹", "maxResults": 1},
                timeout=30
            )
            
            if search_response.status_code == 200:
                search_data = search_response.json()
                results = search_data.get("data", [])
                if results:
                    result = results[0]
                    test_url = result.get("url")
                    
                    print(f"  测试URL: {test_url}")
                    
                    # 测试目录解析
                    toc_response = requests.get(
                        "http://localhost:8000/api/novels/toc",
                        params={
                            "url": test_url,
                            "sourceId": source["id"]
                        },
                        timeout=30
                    )
                    
                    if toc_response.status_code == 200:
                        toc_data = toc_response.json()
                        chapters = toc_data.get("data", [])
                        print(f"  目录章节数: {len(chapters)}")
                        
                        if chapters:
                            print(f"  ✅ 书源 {source['name']} 可用")
                            return source
                        else:
                            print(f"  ❌ 书源 {source['name']} 目录为空")
                    else:
                        print(f"  ❌ 书源 {source['name']} 目录API失败")
                else:
                    print(f"  ❌ 书源 {source['name']} 搜索无结果")
            else:
                print(f"  ❌ 书源 {source['name']} 搜索API失败")
                
        except Exception as e:
            print(f"  ❌ 书源 {source['name']} 测试异常: {str(e)}")
    
    return None

if __name__ == "__main__":
    # 运行简化调试
    simple_toc_debug()
    test_different_source()