#!/usr/bin/env python3
"""
最终的下载问题解决方案
"""

import requests
import time
import json

def create_final_solution():
    """创建最终的解决方案"""
    print("🎯 最终的下载问题解决方案...")
    
    # 1. 问题总结
    print("\n1. 问题总结:")
    print("   ✅ 搜索功能正常")
    print("   ✅ API服务正常运行")
    print("   ✅ 书源加载成功")
    print("   ❌ SSL证书验证失败")
    print("   ❌ 网站访问被阻止")
    print("   ❌ 解析器无法获取内容")
    
    # 2. 解决方案
    print("\n2. 解决方案:")
    solution = '''
🔧 解决方案实施步骤：

1. 修复SSL证书问题
   - 在 aiohttp 请求中禁用SSL验证
   - 添加更宽松的SSL配置

2. 改进错误处理
   - 添加更详细的错误日志
   - 实现优雅的降级机制

3. 尝试不同的书源
   - 测试其他可用的书源
   - 验证书源规则配置

4. 优化网络请求
   - 增加重试机制
   - 添加请求头伪装
   - 实现请求延迟

5. 创建备用方案
   - 实现本地测试数据
   - 提供模拟下载功能
'''
    print(solution)
    
    # 3. 创建修复脚本
    print("\n3. 创建修复脚本:")
    fix_script = '''
#!/usr/bin/env python3
"""
下载功能最终修复
"""

import requests
import time
import json

def test_final_fix():
    """测试最终修复"""
    print("🚀 测试最终修复...")
    
    base_url = "http://localhost:8000"
    
    # 1. 测试搜索功能
    print("1. 测试搜索功能...")
    try:
        response = requests.get(
            f"{base_url}/api/novels/search",
            params={"keyword": "斗破苍穹", "maxResults": 3},
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("data", [])
            print(f"   ✅ 搜索成功，找到 {len(results)} 个结果")
            
            # 尝试不同的书源
            for i, result in enumerate(results[:3]):
                print(f"\\n   测试结果 {i+1}:")
                print(f"   - 标题: {result.get('title', result.get('bookName'))}")
                print(f"   - URL: {result.get('url')}")
                print(f"   - 书源ID: {result.get('source_id')}")
                
                # 测试下载
                try:
                    download_response = requests.get(
                        f"{base_url}/api/novels/download",
                        params={
                            "url": result.get("url"),
                            "sourceId": result.get("source_id"),
                            "format": "txt"
                        },
                        timeout=300,
                        stream=True
                    )
                    
                    if download_response.status_code == 200:
                        # 保存测试文件
                        filename = f"test_download_{i+1}.txt"
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
                        
                except Exception as e:
                    print(f"   ❌ 下载异常: {str(e)}")
        else:
            print(f"   ❌ 搜索失败: {response.text}")
            
    except Exception as e:
        print(f"   ❌ 搜索异常: {str(e)}")
    
    return False

if __name__ == "__main__":
    test_final_fix()
'''
    print(fix_script)
    
    # 4. 创建SSL修复
    print("\n4. 创建SSL修复:")
    ssl_fix = '''
# 修改 app/parsers/book_parser.py 中的 _fetch_html 方法

async def _fetch_html(self, url: str) -> Optional[str]:
    """获取HTML页面"""
    try:
        # 创建SSL上下文，跳过证书验证
        connector = aiohttp.TCPConnector(
            limit=settings.MAX_CONCURRENT_REQUESTS,
            ssl=False,  # 跳过SSL证书验证
            use_dns_cache=True,
            ttl_dns_cache=300,
        )
        
        timeout = aiohttp.ClientTimeout(
            total=self.timeout,
            connect=10,
            sock_read=30
        )
        
        async with aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers=self.headers
        ) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.error(f"请求失败: {url}, 状态码: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"请求异常: {url}, 错误: {str(e)}")
        return None
'''
    print(ssl_fix)
    
    # 5. 总结
    print("\n5. 解决方案总结:")
    summary = '''
📋 下载问题解决方案总结：

🔍 问题诊断：
- API服务正常运行 ✅
- 搜索功能正常 ✅
- 书源加载成功 ✅
- SSL证书验证失败 ❌
- 网站访问被阻止 ❌
- 解析器无法获取内容 ❌

🔧 解决方案：
1. 修复SSL证书验证问题
2. 改进网络请求配置
3. 尝试不同的书源
4. 添加更详细的错误处理
5. 实现优雅的降级机制

📝 实施步骤：
1. 修改网络请求配置，禁用SSL验证
2. 重启API服务
3. 测试不同的书源
4. 验证下载功能
5. 监控下载性能

🎯 预期效果：
- 解决SSL证书问题
- 提高网站访问成功率
- 改善下载功能稳定性
- 提供更好的用户体验
'''
    print(summary)

if __name__ == "__main__":
    create_final_solution()