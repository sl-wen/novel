#!/usr/bin/env python3
"""
书源5 URL转换测试脚本
测试新天禧小说的URL转换逻辑
"""

import json
import re

def test_source_5_url_transform():
    """测试书源5的URL转换"""
    print("书源5 (新天禧小说) URL转换测试")
    print("=" * 50)
    
    # 加载规则文件
    try:
        with open("rules/rule-05.json", 'r', encoding='utf-8') as f:
            rule = json.load(f)
    except Exception as e:
        print(f"加载规则文件失败: {e}")
        return
    
    toc_rule = rule.get('toc', {})
    source_name = rule.get('name', 'Unknown')
    
    print(f"书源名称: {source_name}")
    
    # 获取URL转换配置
    url_transform = toc_rule.get('url_transform', {})
    
    print(f"URL转换规则: {url_transform}")
    
    # 测试URL列表 - 假设的详情页URL格式
    test_urls = [
        # 假设详情页是 book 格式
        "https://www.tianxibook.com/book/95144367/",
        "https://www.tianxibook.com/book/95144367",
        "https://www.tianxibook.com/book/12345/",
        "https://www.tianxibook.com/book/67890",
        
        # 假设详情页是 novel 格式
        "https://www.tianxibook.com/novel/95144367/",
        "https://www.tianxibook.com/novel/95144367",
        "https://www.tianxibook.com/novel/12345/",
        "https://www.tianxibook.com/novel/67890",
        
        # 已经是正确格式的情况
        "https://www.tianxibook.com/xiaoshuo/95144367/",
        "https://www.tianxibook.com/xiaoshuo/12345/",
        
        # 不匹配的URL（不应该被转换）
        "https://www.tianxibook.com/other/95144367/",
        "https://other-site.com/book/95144367/"
    ]
    
    print(f"\n测试URL转换:")
    print("-" * 30)
    
    # 测试每个URL
    for test_url in test_urls:
        print(f"\n原始URL: {test_url}")
        
        # 应用URL转换规则
        toc_url = test_url
        
        if url_transform:
            pattern = url_transform.get('pattern', '')
            replacement = url_transform.get('replacement', '')
            if pattern and replacement:
                original_url = toc_url
                toc_url = re.sub(pattern, replacement, test_url)
                
                if toc_url != original_url:
                    print(f"转换后URL: {toc_url}")
                    
                    # 验证转换结果
                    if "/xiaoshuo/" in toc_url and toc_url.startswith("https://www.tianxibook.com/"):
                        print("✅ 转换成功")
                    else:
                        print("❌ 转换结果异常")
                else:
                    print("⚪ 无需转换（已是正确格式或不匹配）")
            else:
                print("❌ 缺少转换规则")
        else:
            print("❌ 未配置URL转换")
        
        print(f"最终目录URL: {toc_url}")
    
    print(f"\n" + "=" * 50)
    print("测试完成")

if __name__ == "__main__":
    test_source_5_url_transform()