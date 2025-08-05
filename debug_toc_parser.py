#!/usr/bin/env python3
"""
目录解析器调试工具
帮助诊断目录解析问题
"""

import asyncio
import aiohttp
import logging
from bs4 import BeautifulSoup
from app.core.config import settings
from app.core.source import Source
from app.parsers.toc_parser import TocParser

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def debug_toc_parser():
    """调试目录解析器"""
    print("🔍 目录解析器调试工具")
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
    
    # 2. 测试获取HTML
    print("\n2. 测试获取HTML...")
    html = await parser._fetch_html(toc_url)
    if html:
        print(f"   HTML长度: {len(html)}")
        print(f"   HTML预览: {html[:200]}...")
    else:
        print("   ❌ 获取HTML失败")
        return
    
    # 3. 测试解析目录
    print("\n3. 测试解析目录...")
    soup = BeautifulSoup(html, "html.parser")
    
    # 测试不同的选择器
    selectors = [
        ".catalog li a",
        ".catalog > div > ul > ul > li > a",
        ".catalog a",
        "li a",
        "a"
    ]
    
    for selector in selectors:
        elements = soup.select(selector)
        print(f"   选择器 '{selector}': 找到 {len(elements)} 个元素")
        if elements:
            print(f"   第一个元素: {elements[0]}")
            print(f"   第一个元素文本: {elements[0].get_text(strip=True)}")
            print(f"   第一个元素href: {elements[0].get('href', '无href')}")
    
    # 4. 测试完整解析
    print("\n4. 测试完整解析...")
    chapters = await parser.parse(test_url)
    print(f"   解析结果: {len(chapters)} 个章节")
    
    if chapters:
        print("   章节预览:")
        for i, chapter in enumerate(chapters[:5]):
            print(f"     {i+1}. {chapter.title} - {chapter.url}")
    else:
        print("   ❌ 没有解析到章节")
        
        # 5. 详细调试
        print("\n5. 详细调试...")
        chapters = parser._parse_toc(html, toc_url)
        print(f"   直接解析结果: {len(chapters)} 个章节")

async def test_alternative_selectors():
    """测试替代选择器"""
    print("\n🔧 测试替代选择器")
    print("=" * 60)
    
    test_url = "https://www.0xs.net/txt/1.html"
    
    # 创建aiohttp会话
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
        }
    ) as session:
        try:
            async with session.get(test_url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")
                    
                    # 查找所有可能的目录元素
                    print("查找所有可能的目录元素...")
                    
                    # 查找所有链接
                    all_links = soup.find_all("a")
                    print(f"总链接数: {len(all_links)}")
                    
                    # 查找包含章节相关文本的链接
                    chapter_links = []
                    for link in all_links:
                        text = link.get_text(strip=True)
                        href = link.get("href", "")
                        if any(keyword in text for keyword in ["第", "章", "节", "回"]):
                            chapter_links.append((text, href))
                    
                    print(f"可能的章节链接: {len(chapter_links)}")
                    for i, (text, href) in enumerate(chapter_links[:10]):
                        print(f"  {i+1}. {text} - {href}")
                    
                    # 查找catalog相关元素
                    catalog_elements = soup.find_all(class_=lambda x: x and "catalog" in x)
                    print(f"catalog相关元素: {len(catalog_elements)}")
                    
                    # 查找list相关元素
                    list_elements = soup.find_all(class_=lambda x: x and "list" in x)
                    print(f"list相关元素: {len(list_elements)}")
                    
                else:
                    print(f"请求失败: {response.status}")
                    
        except Exception as e:
            print(f"请求异常: {str(e)}")

if __name__ == "__main__":
    # 运行调试
    asyncio.run(debug_toc_parser())
    asyncio.run(test_alternative_selectors())