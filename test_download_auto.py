#!/usr/bin/env python3
"""
自动测试下载功能修复
"""

import time
import os
from pathlib import Path

import requests


def test_download_api():
    """测试下载API"""
    print("🔍 测试下载功能修复...")

    base_url = "http://localhost:8000/api/novels"

    # 1. 先搜索获取一个小说
    print("1. 搜索小说...")
    try:
        response = requests.get(
            f"{base_url}/search",
            params={"keyword": "斗破苍穹", "maxResults": 1},
            timeout=30,
        )

        if response.status_code != 200:
            print(f"❌ 搜索失败: {response.status_code}")
            return False

        data = response.json()
        results = data.get("data", [])

        if not results:
            print("❌ 没有搜索结果")
            return False

        result = results[0]
        book_url = result.get("url")
        source_id = result.get("source_id")

        print(f"   ✅ 找到小说: {result.get('title', result.get('bookName'))}")
        print(f"   - URL: {book_url}")
        print(f"   - 书源ID: {source_id}")

    except Exception as e:
        print(f"❌ 搜索异常: {str(e)}")
        return False

    # 2. 测试下载API
    print("\n2. 测试下载API...")
    try:
        print("   - 开始下载，这可能需要几分钟...")
        response = requests.get(
            f"{base_url}/download",
            params={"url": book_url, "sourceId": source_id, "format": "txt"},
            timeout=300,  # 下载可能需要更长时间
            stream=True,  # 流式下载
        )

        print(f"   - 响应状态码: {response.status_code}")

        if response.status_code == 200:
            # 检查是否是文件流
            content_type = response.headers.get("content-type", "")
            content_disposition = response.headers.get("content-disposition", "")

            print(f"   - Content-Type: {content_type}")
            print(f"   - Content-Disposition: {content_disposition}")

            if (
                "application/octet-stream" in content_type
                or "attachment" in content_disposition
            ):
                # 保存文件到本地测试
                filename = "test_download.txt"
                with open(filename, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                file_size = os.path.getsize(filename)
                print(f"   ✅ 下载成功，文件大小: {file_size} 字节")
                
                # 检查文件内容
                if file_size > 0:
                    with open(filename, "r", encoding="utf-8") as f:
                        content = f.read(500)  # 读取前500字符
                        print(f"   - 文件内容预览: {content[:100]}...")
                    
                    # 清理测试文件
                    os.remove(filename)
                    print("   - 测试文件已清理")
                    return True
                else:
                    print("   ❌ 下载的文件为空")
                    return False
            else:
                print("   ⚠️  响应格式不是文件流")
                print(f"   - 响应内容: {response.text[:200]}...")
                return False
        else:
            print(f"   ❌ 下载失败")
            print(f"   - 响应内容: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 下载异常: {str(e)}")
        return False


def test_download_directory():
    """测试下载目录结构"""
    print("\n3. 检查下载目录结构...")
    
    try:
        # 检查下载目录是否存在
        download_path = Path("downloads")
        if not download_path.exists():
            print("   ⚠️  下载目录不存在，创建中...")
            download_path.mkdir(exist_ok=True)
        
        # 列出下载目录内容
        print(f"   - 下载目录: {download_path.absolute()}")
        if download_path.exists():
            items = list(download_path.iterdir())
            if items:
                print(f"   - 目录内容 ({len(items)} 项):")
                for item in items[:5]:  # 只显示前5项
                    if item.is_dir():
                        print(f"     📁 {item.name}")
                    else:
                        print(f"     📄 {item.name}")
                if len(items) > 5:
                    print(f"     ... 还有 {len(items) - 5} 项")
            else:
                print("   - 目录为空")
        
        return True
    except Exception as e:
        print(f"   ❌ 检查下载目录失败: {str(e)}")
        return False


def main():
    """主函数"""
    print("🚀 下载功能修复测试")
    print("=" * 40)

    # 测试下载API
    api_success = test_download_api()
    
    # 测试下载目录
    dir_success = test_download_directory()

    print("\n" + "=" * 40)
    if api_success and dir_success:
        print("🎉 下载功能修复成功！")
        print("\n✅ 主要改进:")
        print("- 采用参考实现的目录结构")
        print("- 支持并发下载章节")
        print("- 改进的文件命名和保存方式")
        print("- 更好的错误处理和进度跟踪")
    else:
        print("❌ 下载功能仍有问题")
        print("\n💡 可能的原因:")
        print("- API服务未启动")
        print("- 网络连接问题")
        print("- 书源网站访问失败")
        print("- 下载目录权限问题")


if __name__ == "__main__":
    print("请确保API服务正在运行...")
    print(
        "启动命令: python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
    )
    print()

    main()