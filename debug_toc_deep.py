#!/usr/bin/env python3
"""
深度调试目录解析器
"""

import requests
import json
import urllib.request
import ssl
from bs4 import BeautifulSoup
import logging

# 设置详细日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_toc_deep():
    """深度调试目录解析器"""
    print("🔍 深度调试目录解析器...")
    
    # 1. 直接访问网站并分析HTML结构
    print("1. 直接访问网站并分析HTML结构...")
    try:
        url = "https://www.0xs.net/txt/1.html"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 创建SSL上下文
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=context, timeout=30) as response:
            html = response.read().decode('utf-8')
            print(f"   ✅ 网站访问成功，HTML长度: {len(html)}")
            
            # 分析HTML结构
            soup = BeautifulSoup(html, "html.parser")
            
            # 检查目录容器
            catalog = soup.select_one('.catalog')
            if catalog:
                print("   ✅ 找到 .catalog 容器")
                
                # 检查容器内的所有链接
                all_links = catalog.find_all('a')
                print(f"   - 容器内总共有 {len(all_links)} 个链接")
                
                # 过滤出章节链接
                chapter_links = []
                for link in all_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    if '/txt/' in href and text:
                        chapter_links.append({
                            'text': text,
                            'href': href
                        })
                
                print(f"   - 找到 {len(chapter_links)} 个章节链接")
                for i, link in enumerate(chapter_links[:5]):
                    print(f"     {i+1}. {link['text']} -> {link['href']}")
                    
                # 检查选择器
                selector = ".catalog li a"
                elements = soup.select(selector)
                print(f"   - 选择器 '{selector}' 找到 {len(elements)} 个元素")
                
                if elements:
                    print("   - 前3个元素:")
                    for i, elem in enumerate(elements[:3]):
                        text = elem.get_text(strip=True)
                        href = elem.get('href', '')
                        print(f"     {i+1}. {text} -> {href}")
                        
            else:
                print("   ❌ 未找到 .catalog 容器")
                
    except Exception as e:
        print(f"   ❌ 网站访问失败: {str(e)}")
    
    # 2. 模拟目录解析器的完整流程
    print("\n2. 模拟目录解析器的完整流程...")
    try:
        # 模拟 _get_toc_url 方法
        def get_toc_url(url):
            """获取目录URL"""
            return url  # 对于这个书源，目录URL就是原URL
        
        # 模拟 _fetch_html 方法
        def fetch_html(url):
            """获取HTML页面"""
            try:
                import aiohttp
                import asyncio
                
                async def async_fetch():
                    connector = aiohttp.TCPConnector(ssl=False)
                    timeout = aiohttp.ClientTimeout(total=30)
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                    
                    async with aiohttp.ClientSession(
                        timeout=timeout,
                        connector=connector,
                        headers=headers
                    ) as session:
                        async with session.get(url) as response:
                            if response.status == 200:
                                return await response.text()
                            else:
                                print(f"     ❌ 请求失败: {url}, 状态码: {response.status}")
                                return None
                
                # 运行异步函数
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(async_fetch())
                finally:
                    loop.close()
                    
            except Exception as e:
                print(f"     ❌ 获取HTML失败: {str(e)}")
                return None
                
                # 运行异步函数
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(async_fetch())
                finally:
                    loop.close()
                    
            except Exception as e:
                print(f"     ❌ 获取HTML失败: {str(e)}")
                return None
        
        # 模拟 _parse_toc 方法
        def parse_toc(html, toc_url):
            """解析目录"""
            if not html:
                print("     ❌ HTML为空")
                return []
            
            soup = BeautifulSoup(html, "html.parser")
            chapters = []
            
            # 使用修复后的选择器
            selector = ".catalog li a"
            elements = soup.select(selector)
            print(f"     - 选择器 '{selector}' 找到 {len(elements)} 个元素")
            
            if not elements:
                print("     ❌ 未找到章节元素")
                return chapters
            
            # 解析每个章节
            for index, element in enumerate(elements, 1):
                try:
                    # 获取章节标题
                    title = element.get_text(strip=True)
                    
                    # 获取章节URL
                    url = element.get('href', '')
                    
                    # 构建完整URL
                    if url and not url.startswith(("http://", "https://")):
                        base_url = "https://www.0xs.net"
                        url = f"{base_url.rstrip('/')}/{url.lstrip('/')}"
                    
                    if title and url:
                        chapter = {
                            'title': title,
                            'url': url,
                            'order': index
                        }
                        chapters.append(chapter)
                        print(f"     - 解析章节 {index}: {title} -> {url}")
                    
                except Exception as e:
                    print(f"     ❌ 解析章节失败: {str(e)}")
                    continue
            
            return chapters
        
        # 执行模拟流程
        toc_url = get_toc_url("https://www.0xs.net/txt/1.html")
        print(f"   - 目录URL: {toc_url}")
        
        html = fetch_html(toc_url)
        if html:
            print(f"   - 获取HTML成功，长度: {len(html)}")
            chapters = parse_toc(html, toc_url)
            print(f"   - 解析结果: {len(chapters)} 个章节")
            
            if chapters:
                print("   - 前3个章节:")
                for i, chapter in enumerate(chapters[:3]):
                    print(f"     {i+1}. {chapter['title']} -> {chapter['url']}")
            else:
                print("   ❌ 解析结果为空")
        else:
            print("   ❌ 获取HTML失败")
            
    except Exception as e:
        print(f"   ❌ 模拟流程失败: {str(e)}")
    
    # 3. 检查API的详细响应
    print("\n3. 检查API的详细响应...")
    try:
        base_url = "http://localhost:8000"
        response = requests.get(
            f"{base_url}/api/novels/toc",
            params={
                "url": "https://www.0xs.net/txt/1.html",
                "sourceId": 11
            },
            timeout=60
        )
        
        print(f"   - API状态码: {response.status_code}")
        print(f"   - 响应头: {dict(response.headers)}")
        print(f"   - 响应内容: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            chapters = data.get("data", [])
            print(f"   - 章节数量: {len(chapters)}")
            
            if chapters:
                print("   - 前3个章节:")
                for i, chapter in enumerate(chapters[:3]):
                    print(f"     {i+1}. {chapter.get('title', 'Unknown')} -> {chapter.get('url', 'Unknown')}")
            else:
                print("   ❌ API返回空章节列表")
                
    except Exception as e:
        print(f"   ❌ API调用失败: {str(e)}")
    
    # 4. 生成修复建议
    print("\n4. 生成修复建议...")
    print("   💡 可能的问题和解决方案:")
    print("   - 目录解析器的网络请求可能失败")
    print("   - 目录解析器的错误处理可能有问题")
    print("   - 网站可能使用了反爬虫机制")
    print("   - 可能需要添加更多的请求头")
    print("   - 可能需要添加请求延迟")

if __name__ == "__main__":
    debug_toc_deep()