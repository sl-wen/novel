#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试多格式下载功能
"""

import requests

def test_formats():
    """测试不同格式下载"""
    base_url = "http://localhost:8000"
    
    print("📚 测试多格式下载功能")
    print("=" * 50)
    
    # 搜索获取测试书籍
    search_response = requests.get(f"{base_url}/api/novels/search", 
                                 params={"keyword": "修真"}, 
                                 timeout=15)
    
    if search_response.status_code != 200:
        print("❌ 搜索失败")
        return
    
    results = search_response.json().get('data', [])
    if not results:
        print("❌ 没有搜索结果")
        return
    
    book = results[0]
    print(f"测试书籍: {book.get('bookName')} - {book.get('author')}")
    
    # 测试不同格式
    formats = ["txt", "epub", "pdf"]
    
    for fmt in formats:
        print(f"\n📄 测试 {fmt.upper()} 格式:")
        
        download_response = requests.get(f"{base_url}/api/novels/download",
                                       params={
                                           "url": book.get('url'),
                                           "sourceId": book.get('sourceId'),
                                           "format": fmt
                                       },
                                       timeout=60)
        
        if download_response.status_code == 200:
            content_length = len(download_response.content)
            content_type = download_response.headers.get('content-type', '')
            disposition = download_response.headers.get('Content-Disposition', '')
            
            print(f"   ✅ 下载成功")
            print(f"   📊 文件大小: {content_length} 字节")
            print(f"   📋 内容类型: {content_type}")
            print(f"   📁 文件头: {disposition[:80]}...")
            
            if content_length > 0:
                print(f"   🎉 {fmt.upper()} 格式完全正常!")
            else:
                print(f"   ⚠️  {fmt.upper()} 文件为空")
        else:
            print(f"   ❌ 下载失败: {download_response.status_code}")
    
    print(f"\n{'='*50}")
    print("🏆 多格式下载测试完成!")

if __name__ == "__main__":
    test_formats() 