#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试完整的搜索→下载流程
"""

import requests
import json
import time
from urllib.parse import quote

def test_search_and_download():
    """测试完整的搜索和下载流程"""
    base_url = "http://localhost:8000"
    
    print("🔍 开始测试搜索→下载完整流程")
    print("=" * 60)
    
    # 1. 搜索小说
    print("第1步: 搜索小说")
    keyword = "斗破苍穹"
    
    try:
        search_response = requests.get(f"{base_url}/api/novels/search", 
                                     params={"keyword": keyword}, 
                                     timeout=30)
        
        if search_response.status_code != 200:
            print(f"❌ 搜索失败，状态码: {search_response.status_code}")
            return
        
        search_data = search_response.json()
        results = search_data.get('data', [])
        
        if not results:
            print("❌ 没有搜索结果")
            return
            
        print(f"✅ 找到 {len(results)} 条搜索结果")
        
        # 选择第一个结果进行测试
        selected_book = results[0]
        print(f"📖 选择小说: {selected_book.get('bookName')} - {selected_book.get('author')}")
        print(f"   书源: {selected_book.get('sourceName')}")
        print(f"   URL: {selected_book.get('url')}")
        print(f"   相关性: {selected_book.get('score', 0):.2f}")
        
        # 2. 获取小说详情
        print(f"\n第2步: 获取小说详情")
        book_url = selected_book.get('url')
        source_id = selected_book.get('sourceId')
        
        if not book_url or not source_id:
            print("❌ 缺少必要的书籍信息")
            return
        
        detail_response = requests.get(f"{base_url}/api/novels/detail", 
                                     params={"url": book_url, "sourceId": source_id},
                                     timeout=30)
        
        if detail_response.status_code == 200:
            detail_data = detail_response.json()
            book_detail = detail_data.get('data', {})
            print(f"✅ 获取小说详情成功")
            print(f"   书名: {book_detail.get('bookName')}")
            print(f"   作者: {book_detail.get('author')}")
            print(f"   简介: {book_detail.get('intro', '')[:100]}...")
        else:
            print(f"⚠️  获取详情失败，状态码: {detail_response.status_code}")
            print("继续测试目录获取...")
        
        # 3. 获取目录
        print(f"\n第3步: 获取小说目录")
        toc_response = requests.get(f"{base_url}/api/novels/toc", 
                                   params={"url": book_url, "sourceId": source_id},
                                   timeout=30)
        
        if toc_response.status_code != 200:
            print(f"❌ 获取目录失败，状态码: {toc_response.status_code}")
            print(f"错误信息: {toc_response.text[:200]}")
            return
        
        toc_data = toc_response.json()
        chapters = toc_data.get('data', [])
        
        if not chapters:
            print("❌ 目录为空，无法下载")
            return
            
        print(f"✅ 获取目录成功，共 {len(chapters)} 章")
        print("前5章:")
        for i, chapter in enumerate(chapters[:5]):
            print(f"   {i+1}. {chapter.get('title')}")
        
        # 4. 下载小说
        print(f"\n第4步: 开始下载小说")
        download_params = {
            "url": book_url,
            "sourceId": source_id,
            "format": "txt"  # 先测试txt格式
        }
        
        print(f"下载参数: {download_params}")
        
        # 修正：使用GET方法，参数作为query string
        download_response = requests.get(f"{base_url}/api/novels/download", 
                                        params=download_params,
                                        timeout=120,  # 下载可能需要更长时间
                                        stream=True)
        
        if download_response.status_code == 200:
            # 检查响应类型
            content_type = download_response.headers.get('content-type', '')
            
            if 'application/octet-stream' in content_type or 'text/plain' in content_type:
                # 这是文件下载
                filename = f"测试下载_{selected_book.get('bookName', 'unknown')}.txt"
                with open(filename, 'wb') as f:
                    for chunk in download_response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                print(f"✅ 下载成功! 文件保存为: {filename}")
                
                # 检查文件大小和内容
                import os
                file_size = os.path.getsize(filename)
                print(f"   文件大小: {file_size} 字节")
                
                if file_size > 0:
                    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                        content_preview = f.read(200)
                        print(f"   内容预览: {content_preview}...")
                else:
                    print("   ⚠️  文件为空")
                    
            else:
                # 这可能是JSON错误响应
                try:
                    error_data = download_response.json()
                    print(f"❌ 下载失败: {error_data}")
                except:
                    print(f"❌ 下载失败，响应: {download_response.text[:200]}")
        else:
            print(f"❌ 下载失败，状态码: {download_response.status_code}")
            print(f"错误信息: {download_response.text[:200]}")
            
    except Exception as e:
        print(f"❌ 测试过程中发生异常: {str(e)}")
        import traceback
        traceback.print_exc()

def test_different_formats():
    """测试不同格式的下载"""
    base_url = "http://localhost:8000"
    
    print(f"\n🎯 测试不同格式下载")
    print("=" * 60)
    
    # 先搜索获取一个结果
    search_response = requests.get(f"{base_url}/api/novels/search", 
                                 params={"keyword": "修真"}, 
                                 timeout=30)
    
    if search_response.status_code != 200:
        print("❌ 搜索失败，无法测试格式")
        return
    
    results = search_response.json().get('data', [])
    if not results:
        print("❌ 没有搜索结果")
        return
    
    book = results[0]
    book_url = book.get('url')
    source_id = book.get('sourceId')
    
    # 测试不同格式
    formats = ["txt", "epub", "pdf"]
    
    for fmt in formats:
        print(f"\n测试 {fmt.upper()} 格式:")
        
        download_params = {
            "url": book_url,
            "sourceId": source_id,
            "format": fmt
        }
        
        try:
            # 修正：使用GET方法
            download_response = requests.get(f"{base_url}/api/novels/download", 
                                           params=download_params,
                                           timeout=60)
            
            if download_response.status_code == 200:
                print(f"✅ {fmt.upper()} 格式下载成功")
            else:
                error_text = download_response.text[:100]
                print(f"❌ {fmt.upper()} 格式下载失败: {error_text}")
                
        except Exception as e:
            print(f"❌ {fmt.upper()} 格式测试异常: {str(e)}")

if __name__ == "__main__":
    # 测试完整流程
    test_search_and_download()
    
    # 测试不同格式
    test_different_formats()
    
    print(f"\n{'='*60}")
    print("🎉 搜索→下载流程测试完成！")
    print('='*60) 