#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试多个书源的目录获取功能
"""

import requests

def test_toc_from_multiple_sources():
    """测试多个书源的目录获取"""
    base_url = "http://localhost:8000"
    
    print("🔍 测试多个书源的目录获取功能")
    print("=" * 60)
    
    # 1. 搜索获取多个书源的结果
    search_response = requests.get(f"{base_url}/api/novels/search", 
                                 params={"keyword": "斗破苍穹"}, 
                                 timeout=30)
    
    if search_response.status_code != 200:
        print("❌ 搜索失败")
        return
    
    results = search_response.json().get('data', [])
    
    if not results:
        print("❌ 没有搜索结果")
        return
    
    # 按书源分组
    source_books = {}
    for book in results:
        source_name = book.get('sourceName')
        if source_name not in source_books:
            source_books[source_name] = []
        source_books[source_name].append(book)
    
    print(f"找到 {len(source_books)} 个不同书源的结果")
    
    # 测试每个书源的第一本书
    for source_name, books in source_books.items():
        print(f"\n📚 测试书源: {source_name}")
        book = books[0]  # 取第一本书
        
        book_url = book.get('url')
        source_id = book.get('sourceId')
        
        print(f"   书名: {book.get('bookName')}")
        print(f"   作者: {book.get('author')}")
        print(f"   URL: {book_url}")
        
        try:
            # 获取目录
            toc_response = requests.get(f"{base_url}/api/novels/toc", 
                                      params={"url": book_url, "sourceId": source_id},
                                      timeout=30)
            
            if toc_response.status_code == 200:
                toc_data = toc_response.json()
                chapters = toc_data.get('data', [])
                
                if chapters:
                    print(f"   ✅ 目录获取成功: {len(chapters)} 章")
                    print(f"      前3章: {[ch.get('title') for ch in chapters[:3]]}")
                    
                    # 如果找到有效目录，尝试下载
                    if len(chapters) > 0:
                        print(f"      🔽 尝试下载测试...")
                        download_response = requests.get(f"{base_url}/api/novels/download",
                                                       params={
                                                           "url": book_url,
                                                           "sourceId": source_id,
                                                           "format": "txt"
                                                       },
                                                       timeout=60)
                        
                        if download_response.status_code == 200:
                            print(f"      ✅ 下载测试成功")
                        else:
                            error_msg = download_response.text[:100] if download_response.text else "无错误信息"
                            print(f"      ❌ 下载测试失败: {error_msg}")
                else:
                    print(f"   ❌ 目录为空")
            else:
                error_msg = toc_response.text[:100] if toc_response.text else f"状态码: {toc_response.status_code}"
                print(f"   ❌ 获取目录失败: {error_msg}")
                
        except Exception as e:
            print(f"   ❌ 测试异常: {str(e)}")
        
        print()  # 空行分隔

if __name__ == "__main__":
    test_toc_from_multiple_sources() 