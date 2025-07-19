#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import re
import json
from bs4 import BeautifulSoup

def test_toc_url_construction():
    # 测试URL构建逻辑
    book_url = "https://www.tianxibook.com/book/95033088/"
    toc_template = "https://www.tianxibook.com/xiaoshuo/%s/"
    
    # 从URL中提取书籍ID
    match = re.search(r'/(\d+)/?$', book_url)
    if match:
        book_id = match.group(1)
        toc_url = toc_template.replace("%s", book_id)
        print(f"原始书籍URL: {book_url}")
        print(f"提取的书籍ID: {book_id}")
        print(f"构建的目录URL: {toc_url}")
        
        # 尝试访问目录URL
        try:
            response = requests.get(toc_url, timeout=10)
            print(f"目录URL响应状态码: {response.status_code}")
            print(f"响应内容长度: {len(response.text)}")
            
            if response.status_code == 200:
                # 尝试解析目录
                soup = BeautifulSoup(response.text, "html.parser")
                list_selector = "#content_1 > a"
                items = soup.select(list_selector)
                print(f"找到 {len(items)} 个章节元素")
                
                # 打印前几个章节
                for i, item in enumerate(items[:5]):
                    title = item.get_text().strip()
                    href = item.get("href", "")
                    print(f"  章节 {i+1}: {title} - {href}")
                    
                # 如果没有找到章节，打印HTML片段
                if len(items) == 0:
                    print("HTML片段（前1000字符）:")
                    print(response.text[:1000])
            else:
                print(f"访问失败，响应内容: {response.text[:500]}")
                
        except Exception as e:
            print(f"访问目录URL异常: {str(e)}")
    else:
        print("无法从URL中提取书籍ID")

def test_book_detail_meta():
    # 测试书籍详情页面的meta信息
    book_url = "https://www.tianxibook.com/book/95033088/"
    try:
        response = requests.get(book_url, timeout=10)
        print(f"\n书籍详情页响应状态码: {response.status_code}")
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 查找所有meta标签
            meta_tags = soup.find_all("meta")
            print("\n所有meta标签:")
            for meta in meta_tags:
                if meta.get("property") and "og:" in meta.get("property", ""):
                    print(f"  {meta.get('property')}: {meta.get('content', '')}")
                    
    except Exception as e:
        print(f"访问书籍详情页异常: {str(e)}")

if __name__ == "__main__":
    test_toc_url_construction()
    test_book_detail_meta() 