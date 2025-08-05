#!/usr/bin/env python3
"""
测试修复后的目录解析器
"""

import requests
import json

def test_fixed_toc_parser():
    """测试修复后的目录解析器"""
    print("🧪 测试修复后的目录解析器...")
    
    base_url = "http://localhost:8000"
    
    # 测试获取目录
    try:
        print("1. 测试获取目录...")
        response = requests.get(
            f"{base_url}/api/novels/toc",
            params={
                "url": "https://www.0xs.net/txt/1.html",
                "sourceId": 11
            },
            timeout=60
        )
        
        print(f"   - 状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            chapters = data.get("data", [])
            print(f"   - 章节数量: {len(chapters)}")
            
            if chapters:
                print("   ✅ 获取目录成功")
                print("   - 前5章:")
                for i, chapter in enumerate(chapters[:5]):
                    print(f"     {i+1}. {chapter.get('title', 'Unknown')}")
                    print(f"        URL: {chapter.get('url', 'Unknown')}")
                
                # 测试下载
                print("\n2. 测试下载...")
                download_response = requests.get(
                    f"{base_url}/api/novels/download",
                    params={
                        "url": "https://www.0xs.net/txt/1.html",
                        "sourceId": 11,
                        "format": "txt"
                    },
                    timeout=300,
                    stream=True
                )
                
                print(f"   - 下载状态码: {download_response.status_code}")
                if download_response.status_code == 200:
                    # 保存测试文件
                    filename = "test_fixed_download.txt"
                    with open(filename, "wb") as f:
                        for chunk in download_response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    import os
                    file_size = os.path.getsize(filename)
                    print(f"   ✅ 下载成功，文件大小: {file_size} 字节")
                    
                    # 显示文件内容预览
                    with open(filename, "r", encoding="utf-8") as f:
                        content = f.read()
                        print(f"   - 文件内容预览 (前500字符):")
                        print(f"     {content[:500]}...")
                    
                    # 清理测试文件
                    os.remove(filename)
                    print("   - 测试文件已清理")
                    return True
                else:
                    print(f"   ❌ 下载失败: {download_response.text}")
            else:
                print("   ❌ 没有找到章节")
                
        else:
            print(f"   ❌ 获取目录失败: {response.text}")
            
    except Exception as e:
        print(f"   ❌ 错误: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_fixed_toc_parser()
    if success:
        print("\n🎉 修复成功！下载功能现在应该可以正常工作了。")
    else:
        print("\n❌ 修复失败，需要进一步调试。")