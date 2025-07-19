#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import time

def debug_search():
    base_url = "http://localhost:8000"
    keyword = "斗破苍穹"
    
    print(f"调试搜索API - 关键词: {keyword}")
    print("="*50)
    
    # 多次测试，检查一致性
    for i in range(3):
        print(f"\n第 {i+1} 次测试:")
        try:
            response = requests.get(f"{base_url}/api/novels/search", 
                                  params={"keyword": keyword},
                                  timeout=30)
            
            print(f"状态码: {response.status_code}")
            print(f"响应头: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('data', [])
                print(f"结果数量: {len(results)}")
                
                if len(results) > 0:
                    print("前3个结果:")
                    for j, result in enumerate(results[:3]):
                        print(f"  {j+1}. {result.get('bookName')} - {result.get('score', 0):.3f}")
                else:
                    print("返回数据结构:", data)
            else:
                print(f"错误响应: {response.text[:500]}")
                
        except Exception as e:
            print(f"异常: {str(e)}")
            import traceback
            traceback.print_exc()
        
        if i < 2:  # 不是最后一次
            time.sleep(2)  # 等待2秒

    # 检查API基本功能
    print(f"\n检查根路径:")
    try:
        response = requests.get(f"{base_url}/")
        print(f"根路径状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"服务信息: {data}")
    except Exception as e:
        print(f"根路径异常: {str(e)}")

if __name__ == "__main__":
    debug_search() 