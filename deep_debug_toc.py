#!/usr/bin/env python3
"""
深度调试目录解析问题
详细分析目录解析失败的原因
"""

import asyncio
import aiohttp
import logging
import requests
from bs4 import BeautifulSoup
from app.core.config import settings
from app.core.source import Source
from app.parsers.toc_parser import TocParser

# 配置详细日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def deep_debug_toc_parser():
    """深度调试目录解析器"""
    print("🔍 深度调试目录解析问题")
    print("=" * 60)
    
    # 测试URL和书源
    test_url = "https://www.0xs.net/txt/1.html"
    source_id = 11  # 零点小说
    
    # 创建书源对象
    source_data = {
        "id": source_id,
        "name": "零点小说",
        "url": "https://www.0xs.net/",
        "enabled": True,
        "type": "html",
        "language": "zh_CN",
        "toc": {
            "list": ".catalog li a",
            "title": "text",
            "url": "href",
            "has_pages": False,
            "next_page": "",
            "baseUri": "https://www.0xs.net/",
            "timeout": 15
        }
    }
    
    source = Source(**source_data)
    parser = TocParser(source)
    
    print(f"测试URL: {test_url}")
    print(f"书源: {source.name}")
    print(f"目录规则: {source.rule.get('toc', {})}")
    
    # 1. 测试获取目录URL
    print("\n1. 测试获取目录URL...")
    toc_url = parser._get_toc_url(test_url)
    print(f"   目录URL: {toc_url}")
    
    # 2. 测试获取HTML - 详细调试
    print("\n2. 测试获取HTML - 详细调试...")
    
    # 创建aiohttp会话进行详细调试
    connector = aiohttp.TCPConnector(
        limit=5,
        ssl=False,
        use_dns_cache=True,
        ttl_dns_cache=300,
    )
    
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Referer": "https://www.0xs.net/",
        }
    ) as session:
        try:
            print(f"   正在请求: {toc_url}")
            async with session.get(toc_url) as response:
                print(f"   响应状态码: {response.status}")
                print(f"   响应头: {dict(response.headers)}")
                
                if response.status == 200:
                    html = await response.text()
                    print(f"   HTML长度: {len(html)}")
                    print(f"   HTML预览: {html[:500]}...")
                    
                    # 3. 详细分析HTML结构
                    print("\n3. 详细分析HTML结构...")
                    soup = BeautifulSoup(html, "html.parser")
                    
                    # 查找所有可能的目录元素
                    print("   查找所有可能的目录元素...")
                    
                    # 查找所有链接
                    all_links = soup.find_all("a")
                    print(f"   总链接数: {len(all_links)}")
                    
                    # 查找包含章节相关文本的链接
                    chapter_links = []
                    for link in all_links:
                        text = link.get_text(strip=True)
                        href = link.get("href", "")
                        if any(keyword in text for keyword in ["第", "章", "节", "回", "txt"]):
                            chapter_links.append((text, href))
                    
                    print(f"   可能的章节链接: {len(chapter_links)}")
                    for i, (text, href) in enumerate(chapter_links[:10]):
                        print(f"     {i+1}. {text} - {href}")
                    
                    # 查找catalog相关元素
                    catalog_elements = soup.find_all(class_=lambda x: x and "catalog" in x)
                    print(f"   catalog相关元素: {len(catalog_elements)}")
                    
                    # 查找list相关元素
                    list_elements = soup.find_all(class_=lambda x: x and "list" in x)
                    print(f"   list相关元素: {len(list_elements)}")
                    
                    # 4. 测试不同的选择器
                    print("\n4. 测试不同的选择器...")
                    selectors = [
                        ".catalog li a",
                        ".catalog > div > ul > ul > li > a",
                        ".catalog a",
                        "li a",
                        "a",
                        "a[href*='txt']",
                        "a[href*='.html']",
                        ".chapter-list a",
                        ".chapter a",
                        "ul li a",
                        "div ul li a"
                    ]
                    
                    for selector in selectors:
                        elements = soup.select(selector)
                        print(f"   选择器 '{selector}': 找到 {len(elements)} 个元素")
                        if elements:
                            print(f"     第一个元素: {elements[0]}")
                            print(f"     第一个元素文本: {elements[0].get_text(strip=True)}")
                            print(f"     第一个元素href: {elements[0].get('href', '无href')}")
                    
                    # 5. 测试完整解析
                    print("\n5. 测试完整解析...")
                    chapters = await parser.parse(test_url)
                    print(f"   解析结果: {len(chapters)} 个章节")
                    
                    if chapters:
                        print("   章节预览:")
                        for i, chapter in enumerate(chapters[:5]):
                            print(f"     {i+1}. {chapter.title} - {chapter.url}")
                    else:
                        print("   ❌ 没有解析到章节")
                        
                        # 6. 详细调试解析过程
                        print("\n6. 详细调试解析过程...")
                        chapters = parser._parse_toc(html, toc_url)
                        print(f"   直接解析结果: {len(chapters)} 个章节")
                        
                        # 7. 分析解析失败的原因
                        print("\n7. 分析解析失败的原因...")
                        
                        # 检查选择器是否正确
                        list_selector = parser.toc_rule.get("list", "")
                        print(f"   配置的选择器: {list_selector}")
                        
                        elements = soup.select(list_selector)
                        print(f"   选择器找到的元素数: {len(elements)}")
                        
                        if elements:
                            print("   前5个元素:")
                            for i, elem in enumerate(elements[:5]):
                                print(f"     {i+1}. {elem}")
                                print(f"        文本: {elem.get_text(strip=True)}")
                                print(f"        href: {elem.get('href', '无href')}")
                        else:
                            print("   ❌ 选择器没有找到任何元素")
                            
                            # 尝试查找可能的父元素
                            print("   尝试查找可能的父元素...")
                            parent_selectors = [
                                ".catalog",
                                ".chapter-list",
                                ".chapter",
                                ".toc",
                                ".directory"
                            ]
                            
                            for parent_selector in parent_selectors:
                                parent_elements = soup.select(parent_selector)
                                if parent_elements:
                                    print(f"     找到父元素 '{parent_selector}': {len(parent_elements)} 个")
                                    for parent in parent_elements:
                                        links = parent.find_all("a")
                                        print(f"       包含 {len(links)} 个链接")
                                        if links:
                                            print(f"        第一个链接: {links[0].get_text(strip=True)}")
                                            print(f"        第一个href: {links[0].get('href', '无href')}")
                
                else:
                    print(f"   ❌ 请求失败: {response.status}")
                    
        except Exception as e:
            print(f"   ❌ 请求异常: {str(e)}")

async def test_api_toc_endpoint():
    """测试API目录端点"""
    print("\n🔧 测试API目录端点")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    
    try:
        # 测试目录API
        response = requests.get(
            f"{base_url}/api/novels/toc",
            params={
                "url": "https://www.0xs.net/txt/1.html",
                "sourceId": 11
            },
            timeout=30
        )
        
        print(f"API响应状态码: {response.status_code}")
        print(f"API响应内容: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            chapters = data.get("data", [])
            print(f"API返回章节数: {len(chapters)}")
            
            if chapters:
                print("API章节预览:")
                for i, chapter in enumerate(chapters[:3]):
                    print(f"  {i+1}. {chapter.get('title', '无标题')}")
            else:
                print("❌ API返回空章节列表")
        else:
            print(f"❌ API请求失败: {response.text}")
            
    except Exception as e:
        print(f"❌ API测试异常: {str(e)}")

async def test_alternative_source():
    """测试其他书源"""
    print("\n🔧 测试其他书源")
    print("=" * 60)
    
    # 测试不同的书源
    test_sources = [
        {
            "id": 2,
            "name": "书海阁小说网",
            "url": "https://www.shuhaige.net/",
            "toc": {
                "list": "#list > dl > dd > a",
                "title": "",
                "url": "",
                "has_pages": False,
                "next_page": "",
                "baseUri": "https://www.shuhaige.net/",
                "timeout": 15
            }
        },
        {
            "id": 8,
            "name": "大熊猫文学",
            "url": "https://www.dxmwx.org/",
            "toc": {
                "list": "div:nth-child(2n+5) > span > a",
                "title": "",
                "url": "",
                "has_pages": False,
                "next_page": "",
                "baseUri": "https://www.dxmwx.org/",
                "timeout": 15
            }
        }
    ]
    
    for source_data in test_sources:
        print(f"\n测试书源: {source_data['name']}")
        
        source = Source(**source_data)
        parser = TocParser(source)
        
        # 测试搜索获取URL
        try:
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
                            "sourceId": source_data["id"]
                        },
                        timeout=30
                    )
                    
                    if toc_response.status_code == 200:
                        toc_data = toc_response.json()
                        chapters = toc_data.get("data", [])
                        print(f"  目录章节数: {len(chapters)}")
                        
                        if chapters:
                            print(f"  ✅ 书源 {source_data['name']} 可用")
                            return source_data
                        else:
                            print(f"  ❌ 书源 {source_data['name']} 目录为空")
                    else:
                        print(f"  ❌ 书源 {source_data['name']} 目录API失败")
                else:
                    print(f"  ❌ 书源 {source_data['name']} 搜索无结果")
            else:
                print(f"  ❌ 书源 {source_data['name']} 搜索API失败")
                
        except Exception as e:
            print(f"  ❌ 书源 {source_data['name']} 测试异常: {str(e)}")
    
    return None

if __name__ == "__main__":
    # 运行深度调试
    asyncio.run(deep_debug_toc_parser())
    asyncio.run(test_api_toc_endpoint())
    asyncio.run(test_alternative_source())