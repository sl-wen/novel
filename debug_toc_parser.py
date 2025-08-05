#!/usr/bin/env python3
"""
详细的目录解析器调试
"""

import requests
import json
import urllib.request
from bs4 import BeautifulSoup

def debug_toc_parser():
    """调试目录解析器"""
    print("🔍 详细的目录解析器调试...")
    
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
            
            # 检查目录相关的元素
            print("   - 查找目录相关元素...")
            
            # 检查原始选择器
            selector = ".catalog > div > ul > ul > li > a"
            elements = soup.select(selector)
            print(f"   - 原始选择器 '{selector}' 找到 {len(elements)} 个元素")
            
            # 尝试不同的选择器
            alternative_selectors = [
                ".catalog a",
                ".catalog li a", 
                ".catalog ul li a",
                ".catalog div ul li a",
                "a[href*='/txt/']",
                "a[href*='.html']",
                ".chapter-list a",
                ".chapter a",
                "ul li a",
                "div ul li a"
            ]
            
            print("   - 尝试其他选择器:")
            for alt_selector in alternative_selectors:
                alt_elements = soup.select(alt_selector)
                if alt_elements:
                    print(f"     '{alt_selector}' 找到 {len(alt_elements)} 个元素")
                    if len(alt_elements) > 0:
                        print(f"       第一个元素: {alt_elements[0].get_text(strip=True)[:50]}...")
                        print(f"       第一个链接: {alt_elements[0].get('href', 'No href')}")
            
            # 3. 检查页面结构
            print("\n3. 检查页面结构...")
            
            # 查找所有包含"章"字的链接
            chapter_links = []
            for link in soup.find_all('a', href=True):
                text = link.get_text(strip=True)
                href = link.get('href', '')
                if '章' in text or 'txt' in href or '.html' in href:
                    chapter_links.append({
                        'text': text,
                        'href': href
                    })
            
            print(f"   - 找到 {len(chapter_links)} 个可能的章节链接")
            for i, link in enumerate(chapter_links[:10]):  # 只显示前10个
                print(f"     {i+1}. {link['text']} -> {link['href']}")
            
            # 4. 检查目录容器
            print("\n4. 检查目录容器...")
            
            # 查找可能的目录容器
            containers = [
                '.catalog',
                '.chapter-list',
                '.chapter',
                '.toc',
                '.directory',
                '#catalog',
                '#chapter-list',
                '#chapter',
                '#toc',
                '#directory'
            ]
            
            for container in containers:
                container_elements = soup.select(container)
                if container_elements:
                    print(f"   - 找到容器 '{container}': {len(container_elements)} 个")
                    for elem in container_elements:
                        links = elem.find_all('a')
                        print(f"     包含 {len(links)} 个链接")
                        if links:
                            print(f"     第一个链接: {links[0].get_text(strip=True)[:30]}...")
            
            # 5. 生成修复建议
            print("\n5. 生成修复建议...")
            if chapter_links:
                print("   ✅ 找到章节链接，建议更新选择器")
                # 分析最常见的链接模式
                href_patterns = {}
                for link in chapter_links:
                    href = link['href']
                    if href.startswith('/'):
                        pattern = 'relative'
                    elif href.startswith('http'):
                        pattern = 'absolute'
                    else:
                        pattern = 'other'
                    href_patterns[pattern] = href_patterns.get(pattern, 0) + 1
                
                print(f"   - 链接模式: {href_patterns}")
                
                # 建议新的选择器
                if len(chapter_links) > 0:
                    first_link = chapter_links[0]
                    parent = first_link.get('parent', '')
                    print(f"   - 建议选择器: a[href*='.html'] 或 a[href*='/txt/']")
            else:
                print("   ❌ 未找到章节链接，可能需要检查网站结构")
                
    except Exception as e:
        print(f"   ❌ 网站访问失败: {str(e)}")
    
    # 6. 测试API
    print("\n6. 测试API...")
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
        else:
            print(f"   - API错误: {response.text}")
            
    except Exception as e:
        print(f"   ❌ API调用失败: {str(e)}")

if __name__ == "__main__":
    debug_toc_parser()