#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试下载功能修复
"""

import requests
import time
from urllib.parse import quote

def quick_test():
    base_url = "http://localhost:8000"
    print("🚀 快速测试下载功能修复")
    print("=" * 50)
    
    print("等待服务器启动...")
    for i in range(10):
        try:
            response = requests.get(f"{base_url}/", timeout=3)
            if response.status_code == 200:
                print(f"✅ 服务器已启动 (第{i+1}次尝试)")
                break
        except Exception as e:
            print(f"第{i+1}次连接失败: {e}")
            if i < 9:
                time.sleep(2)
            else:
                print("❌ 服务器启动失败")
                return
    
    # 1. 测试搜索功能
    print("\n1️⃣ 测试搜索功能")
    params = {"keyword": "修真"}
    try:
        search_response = requests.get(
            f"{base_url}/api/novels/search",
            params=params,
            timeout=90
        )
    except requests.exceptions.Timeout:
        print(f"❌ 搜索接口超时: {base_url}/api/novels/search?keyword=%E4%BF%AE%E7%9C%9F")
        print("   可能后端接口耗时过长或未正常响应，请检查后端服务及其依赖网络。")
        return
    except requests.exceptions.RequestException as e:
        print(f"❌ 搜索请求异常: {e}")
        return

    if search_response.status_code != 200:
        print(f"❌ 搜索失败: {search_response.status_code}，响应内容: {search_response.text[:100]}")
        return

    try:
        results = search_response.json().get('data', [])
    except Exception as e:
        print(f"❌ 返回结果不是合法JSON: {e}, 原始响应: {search_response.text[:100]}")
        return
        
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
                               timeout=200)
    
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
    download_params = {
        "url": book.get('url'),
        "format": "txt"
    }
    
    print(f"📤 请求参数: {download_params}")
    
    try:
        download_response = requests.get(
            f"{base_url}/api/novels/download",
            params=download_params,
            timeout=600
        )
        
        print(f"📊 响应状态: {download_response.status_code}")
        print(f"📋 响应头: {dict(download_response.headers)}")
        
        if download_response.status_code == 500:
            error_detail = download_response.json()
            print(f"❌ 详细错误信息:")
            print(f"   Code: {error_detail.get('code')}")
            print(f"   Message: {error_detail.get('message')}")
            print(f"   Data: {error_detail.get('data')}")
            
            # 分析错误
            error_msg = error_detail.get('message', '')
            if 'NoneType' in error_msg:
                print("\n💡 分析：这是空值处理问题")
                print("   可能原因：")
                print("   1. 章节内容爬取失败返回None")
                print("   2. 小说标题/作者信息为空")
                print("   3. URL解析失败")
                print("   4. 网站反爬导致内容获取失败")
        else:
        
            # 获取文件信息
            content_disposition = download_response.headers.get('content-disposition', '')
            content_length = download_response.headers.get('content-length', '0')
        
            print(f"📄 Content-Disposition: {content_disposition}")
            print(f"📊 预计文件大小: {content_length} 字节")
        
        # 流式读取内容并显示进度
            total_size = int(content_length) if content_length.isdigit() else 0
            downloaded_size = 0
            start_time = time.time()
        
            content_chunks = []
            for chunk in download_response.iter_content(chunk_size=8192):
                if chunk:
                    content_chunks.append(chunk)
                    downloaded_size += len(chunk)
                
                    # 每1MB显示一次进度
                    if downloaded_size % (1024 * 1024) == 0 or downloaded_size < 1024 * 1024:
                        elapsed = time.time() - start_time
                        if total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            print(f"📥 下载进度: {progress:.1f}% ({downloaded_size}/{total_size} 字节) - 耗时: {elapsed:.1f}s")
                        else:
                            print(f"📥 已下载: {downloaded_size} 字节 - 耗时: {elapsed:.1f}s")
        
            # 合并所有内容
            full_content = b''.join(content_chunks)

        # 显示内容预览
        try:
            preview = full_content[:200].decode('utf-8', errors='ignore')
            print(f"📖 内容预览: {preview}...")
        except:
            print("📖 内容预览: [二进制内容]")
            
        print("🎉 下载功能完全正常!")
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")

if __name__ == "__main__":
    quick_test() 