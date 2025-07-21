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
    
    
    try:
        print("📥 开始下载，这可能需要较长时间...")
        
        # 增加超时时间到5分钟，使用流式下载
        download_response = requests.get(
            f"{base_url}/api/novels/download",
            params=download_params,
            timeout=300,  # 5分钟超时
            stream=True   # 流式下载
        )
        
        if download_response.status_code != 200:
            print(f"❌ 下载失败: {download_response.status_code}")
            print(f"响应内容: {download_response.text[:200]}")
            return
        
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
        elapsed_time = time.time() - start_time
        
        print(f"✅ 下载测试成功!")
        print(f"📄 文件头: {content_disposition}")
        print(f"📊 实际文件大小: {len(full_content)} 字节")
        print(f"⏱️ 总耗时: {elapsed_time:.2f} 秒")
        print(f"🚀 平均速度: {len(full_content) / elapsed_time / 1024:.2f} KB/s")
        
        # 显示内容预览
        try:
            preview = full_content[:200].decode('utf-8', errors='ignore')
            print(f"📖 内容预览: {preview}...")
        except:
            print("📖 内容预览: [二进制内容]")
            
        print("🎉 下载功能完全正常!")
        
    except requests.exceptions.Timeout:
        print("❌ 下载接口超时 (5分钟)")
        print("💡 建议检查:")
        print("   1. 后端下载逻辑是否有死循环或卡住")
        print("   2. 网络爬取是否遇到反爬限制")
        print("   3. 999章内容是否过多导致处理缓慢")
        print("   4. 数据库或文件IO是否有瓶颈")
        return
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 下载请求异常: {e}")
        return
    except Exception as e:
        print(f"❌ 下载处理异常: {e}")
        return

if __name__ == "__main__":
    quick_test()