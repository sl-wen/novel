#!/usr/bin/env python3
"""
更详细的目录解析器调试
"""

import requests
import json
import urllib.request
from bs4 import BeautifulSoup

def debug_toc_detailed():
    """更详细的目录解析器调试"""
    print("🔍 更详细的目录解析器调试...")
    
    # 1. 直接访问网站获取HTML
    print("1. 直接访问网站获取HTML...")
    try:
        url = "https://www.0xs.net/txt/1.html"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 创建SSL上下文，跳过证书验证
        import ssl
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=context, timeout=30) as response:
            html = response.read().decode('utf-8')
            print(f"   ✅ 网站访问成功，HTML长度: {len(html)}")
            
            # 2. 分析HTML结构
            print("\n2. 分析HTML结构...")
            soup = BeautifulSoup(html, "html.parser")
            
            # 检查新的选择器
            selector = ".catalog li a"
            elements = soup.select(selector)
            print(f"   - 新选择器 '{selector}' 找到 {len(elements)} 个元素")
            
            if elements:
                print("   - 前5个元素:")
                for i, elem in enumerate(elements[:5]):
                    text = elem.get_text(strip=True)
                    href = elem.get('href', '')
                    print(f"     {i+1}. {text} -> {href}")
            
            # 3. 检查目录容器结构
            print("\n3. 检查目录容器结构...")
            catalog = soup.select_one('.catalog')
            if catalog:
                print("   - 找到 .catalog 容器")
                print(f"   - 容器HTML: {str(catalog)[:200]}...")
                
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
                for i, link in enumerate(chapter_links[:10]):
                    print(f"     {i+1}. {link['text']} -> {link['href']}")
            else:
                print("   ❌ 未找到 .catalog 容器")
            
            # 4. 模拟目录解析器逻辑
            print("\n4. 模拟目录解析器逻辑...")
            
            # 模拟 _parse_single_chapter 方法
            def parse_single_chapter(element, order):
                try:
                    # 获取章节标题
                    title = element.get_text(strip=True)
                    
                    # 获取章节URL
                    url = element.get('href', '')
                    
                    # 构建完整URL
                    if url and not url.startswith(("http://", "https://")):
                        base_url = "https://www.0xs.net"
                        url = f"{base_url.rstrip('/')}/{url.lstrip('/')}"
                    
                    return {
                        'title': title or f"第{order}章",
                        'url': url or "",
                        'order': order
                    }
                except Exception as e:
                    print(f"     ❌ 解析章节失败: {str(e)}")
                    return None
            
            # 解析所有找到的元素
            parsed_chapters = []
            for i, elem in enumerate(elements, 1):
                chapter = parse_single_chapter(elem, i)
                if chapter:
                    parsed_chapters.append(chapter)
            
            print(f"   - 成功解析 {len(parsed_chapters)} 个章节")
            for i, chapter in enumerate(parsed_chapters[:5]):
                print(f"     {i+1}. {chapter['title']} -> {chapter['url']}")
            
            # 5. 检查API响应
            print("\n5. 检查API响应...")
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
                if response.status_code == 200:
                    data = response.json()
                    chapters = data.get("data", [])
                    print(f"   - API返回章节数: {len(chapters)}")
                    
                    if chapters:
                        print("   - 前5个章节:")
                        for i, chapter in enumerate(chapters[:5]):
                            print(f"     {i+1}. {chapter.get('title', 'Unknown')} -> {chapter.get('url', 'Unknown')}")
                    else:
                        print("   ❌ API返回空章节列表")
                else:
                    print(f"   - API错误: {response.text}")
                    
            except Exception as e:
                print(f"   ❌ API调用失败: {str(e)}")
            
            # 6. 生成修复建议
            print("\n6. 生成修复建议...")
            if parsed_chapters:
                print("   ✅ 本地解析成功，API可能有问题")
                print("   💡 建议检查:")
                print("   - 目录解析器的网络请求")
                print("   - 目录解析器的错误处理")
                print("   - 目录解析器的日志输出")
            else:
                print("   ❌ 本地解析也失败")
                print("   💡 建议检查:")
                print("   - 网站HTML结构")
                print("   - CSS选择器")
                print("   - 网络请求")
                
    except Exception as e:
        print(f"   ❌ 网站访问失败: {str(e)}")

if __name__ == "__main__":
    debug_toc_detailed()