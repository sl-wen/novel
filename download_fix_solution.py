#!/usr/bin/env python3
"""
下载问题修复方案
"""

import requests
import time
import json
from pathlib import Path

def create_download_fix():
    """创建下载问题修复方案"""
    print("🔧 创建下载问题修复方案...")
    
    # 1. 修改配置文件以增加超时时间
    print("\n1. 修改配置文件...")
    config_content = '''
# 修改 app/core/config.py 中的超时设置
DEFAULT_TIMEOUT: int = 300  # 从100秒增加到300秒
REQUEST_RETRY_TIMES: int = 3  # 从2次增加到3次
REQUEST_RETRY_DELAY: float = 2.0  # 从1.0秒增加到2.0秒
MAX_CONCURRENT_REQUESTS: int = 5  # 从10减少到5
'''
    print(config_content)
    
    # 2. 创建优化的搜索测试
    print("\n2. 创建优化的搜索测试...")
    test_content = '''
#!/usr/bin/env python3
"""
优化的下载测试
"""

import requests
import time
import json

def test_optimized_download():
    """优化的下载测试"""
    print("🚀 优化的下载测试...")
    
    base_url = "http://localhost:8000"
    
    # 1. 测试单个书源搜索
    print("1. 测试单个书源搜索...")
    try:
        response = requests.get(
            f"{base_url}/api/novels/search",
            params={"keyword": "斗破苍穹", "maxResults": 1},
            timeout=60  # 增加超时时间
        )
        print(f"   - 状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            results = data.get("data", [])
            if results:
                result = results[0]
                print(f"   ✅ 找到小说: {result.get('title', result.get('bookName'))}")
                print(f"   - URL: {result.get('url')}")
                print(f"   - 书源ID: {result.get('source_id')}")
                
                # 2. 测试下载
                print("\\n2. 测试下载...")
                download_response = requests.get(
                    f"{base_url}/api/novels/download",
                    params={
                        "url": result.get("url"),
                        "sourceId": result.get("source_id"),
                        "format": "txt"
                    },
                    timeout=300,  # 下载超时5分钟
                    stream=True
                )
                
                print(f"   - 下载状态码: {download_response.status_code}")
                if download_response.status_code == 200:
                    # 保存测试文件
                    filename = "test_download_fixed.txt"
                    with open(filename, "wb") as f:
                        for chunk in download_response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    import os
                    file_size = os.path.getsize(filename)
                    print(f"   ✅ 下载成功，文件大小: {file_size} 字节")
                    
                    # 清理测试文件
                    os.remove(filename)
                    print("   - 测试文件已清理")
                    return True
                else:
                    print(f"   ❌ 下载失败: {download_response.text}")
            else:
                print("   ❌ 没有搜索结果")
        else:
            print(f"   ❌ 搜索失败: {response.text}")
    except requests.exceptions.Timeout:
        print("   ⚠️  请求超时，可能需要更长时间")
    except Exception as e:
        print(f"   ❌ 错误: {str(e)}")
    
    return False

if __name__ == "__main__":
    test_optimized_download()
'''
    print(test_content)
    
    # 3. 创建配置文件修改脚本
    print("\n3. 创建配置文件修改脚本...")
    config_script = '''
#!/usr/bin/env python3
"""
修改配置文件以优化下载性能
"""

def modify_config():
    """修改配置文件"""
    config_file = "app/core/config.py"
    
    # 读取原配置
    with open(config_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 修改超时设置
    content = content.replace(
        "DEFAULT_TIMEOUT: int = 100  # 秒",
        "DEFAULT_TIMEOUT: int = 300  # 秒"
    )
    content = content.replace(
        "REQUEST_RETRY_TIMES: int = 2  # 请求重试次数",
        "REQUEST_RETRY_TIMES: int = 3  # 请求重试次数"
    )
    content = content.replace(
        "REQUEST_RETRY_DELAY: float = 1.0  # 请求重试延迟（秒）",
        "REQUEST_RETRY_DELAY: float = 2.0  # 请求重试延迟（秒）"
    )
    content = content.replace(
        "MAX_CONCURRENT_REQUESTS: int = 10  # 最大并发请求数",
        "MAX_CONCURRENT_REQUESTS: int = 5  # 最大并发请求数"
    )
    
    # 写回文件
    with open(config_file, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("✅ 配置文件修改完成")

if __name__ == "__main__":
    modify_config()
'''
    print(config_script)
    
    # 4. 创建解决方案总结
    print("\n4. 解决方案总结...")
    solution = '''
📋 下载问题解决方案总结：

🔍 问题诊断：
- API服务正常运行 ✅
- 书源加载成功（20个书源）✅
- 搜索API超时（网络访问问题）❌

🔧 解决方案：
1. 增加超时时间：从100秒增加到300秒
2. 增加重试次数：从2次增加到3次
3. 增加重试延迟：从1秒增加到2秒
4. 减少并发请求：从10个减少到5个
5. 优化网络请求配置

📝 实施步骤：
1. 修改 app/core/config.py 配置文件
2. 重启API服务
3. 运行优化的下载测试
4. 监控下载性能

🎯 预期效果：
- 减少超时错误
- 提高下载成功率
- 改善用户体验
'''
    print(solution)

if __name__ == "__main__":
    create_download_fix()