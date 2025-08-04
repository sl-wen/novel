#!/usr/bin/env python3
"""
测试下载功能修复
"""

import time

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
        response = requests.get(
            f"{base_url}/download",
            params={"url": book_url, "sourceId": source_id, "format": "txt"},
            timeout=60,  # 下载可能需要更长时间
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
                print("   ✅ 下载成功，返回了文件流")
                print(f"   - 文件大小: {len(response.content)} 字节")
                return True
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


def main():
    """主函数"""
    print("🚀 下载功能修复测试")
    print("=" * 40)

    success = test_download_api()

    print("\n" + "=" * 40)
    if success:
        print("🎉 下载功能修复成功！")
    else:
        print("❌ 下载功能仍有问题")
        print("\n💡 可能的原因:")
        print("- API服务未启动")
        print("- 网络连接问题")
        print("- 书源网站访问失败")


if __name__ == "__main__":
    print("请确保API服务正在运行...")
    print(
        "启动命令: python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
    )
    print()

    input("按回车键开始测试...")
    main()
