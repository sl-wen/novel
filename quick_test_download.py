#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试下载功能修复
"""

import requests
import time

def quick_test():
    """快速测试核心功能"""
    base_url = "http://localhost:8000"
    
    print("🚀 快速测试下载功能修复")
    print("=" * 50)
    
    # 等待服务器启动
    print("等待服务器启动...")
    for i in range(10):
        try:
            response = requests.get(f"{base_url}/", timeout=3)
            if response.status_code == 200:
                print(f"✅ 服务器已启动 (第{i+1}次尝试)")
                break
        except:
            if i < 9:
                time.sleep(2)
            else:
                print("❌ 服务器启动失败")
                return
    
    # 1. 测试搜索
    print("\n1️⃣ 测试搜索功能")
    search_response = requests.get(f"{base_url}/api/novels/search", 
                                 params={"keyword": "修真"}, 
                                 timeout=15)
    
    if search_response.status_code != 200:
        print(f"❌ 搜索失败: {search_response.status_code}")
        return
    
    results = search_response.json().get('data', [])
    if not results:
        print("❌ 没有搜索结果")
        return
        
    print(f"✅ 搜索成功，找到 {len(results)} 条结果")
    
    # 选择第一个结果
    book = results[0]
    print(f"选择测试书籍: {book.get('bookName')} - {book.get('author')}")
    
    # 2. 测试目录获取
    print("\n2️⃣ 测试目录获取")
    toc_response = requests.get(f"{base_url}/api/novels/toc", 
                               params={
                                   "url": book.get('url'),
                                   "sourceId": book.get('sourceId')
                               },
                               timeout=15)
    
    if toc_response.status_code != 200:
        print(f"❌ 目录获取失败: {toc_response.status_code}")
        print(f"错误: {toc_response.text[:100]}")
        return
    
    chapters = toc_response.json().get('data', [])
    if not chapters:
        print("❌ 目录为空")
        return
    
    print(f"✅ 目录获取成功: {len(chapters)} 章")
    print(f"前3章: {[ch.get('title') for ch in chapters[:3]]}")
    
    # 3. 测试下载
    print("\n3️⃣ 测试下载功能")
    download_response = requests.get(f"{base_url}/api/novels/download",
                                   params={
                                       "url": book.get('url'),
                                       "sourceId": book.get('sourceId'),
                                       "format": "txt"
                                   },
                                   timeout=30)
    
    if download_response.status_code == 200:
        print("✅ 下载测试成功!")
        
        # 检查Content-Disposition头是否正确处理中文
        disposition = download_response.headers.get('Content-Disposition', '')
        print(f"文件头: {disposition}")
        
        # 检查响应大小
        content_length = len(download_response.content)
        print(f"文件大小: {content_length} 字节")
        
        if content_length > 0:
            print("🎉 下载功能完全正常!")
        else:
            print("⚠️  下载文件为空")
    else:
        print(f"❌ 下载失败: {download_response.status_code}")
        print(f"错误: {download_response.text[:100]}")

if __name__ == "__main__":
    quick_test() 