#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试改进后的搜索功能
"""

import requests
import json


def test_search_relevance():
    """测试搜索结果的相关性"""
    base_url = "http://localhost:8000"
    
    # 测试不同的搜索关键词
    test_cases = [
        "斗破苍穹",
        "天蚕土豆",
        "玄幻",
        "修真",
        "都市",
    ]
    
    for keyword in test_cases:
        print(f"\n{'='*60}")
        print(f"测试搜索关键词: {keyword}")
        print('='*60)
        
        try:
            response = requests.get(f"{base_url}/api/novels/search", 
                                  params={"keyword": keyword})
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('data', [])
                
                print(f"找到 {len(results)} 条结果")
                
                # 显示前10个结果，重点关注相关性
                for i, result in enumerate(results[:10]):
                    score = result.get('score', 0)
                    print(f"\n{i+1}. 【相关性: {score:.2f}】")
                    print(f"   书名: {result.get('bookName')}")
                    print(f"   作者: {result.get('author')}")
                    print(f"   书源: {result.get('sourceName')}")
                    
                    # 分析相关性
                    book_name = result.get('bookName', '').lower()
                    author = result.get('author', '').lower()
                    keyword_lower = keyword.lower()
                    
                    relevance_reasons = []
                    if keyword_lower in book_name:
                        relevance_reasons.append("书名匹配")
                    if keyword_lower in author:
                        relevance_reasons.append("作者匹配")
                    
                    if relevance_reasons:
                        print(f"   匹配原因: {', '.join(relevance_reasons)}")
                    else:
                        print("   匹配原因: 部分相似")
                        
            else:
                print(f"搜索失败，状态码: {response.status_code}")
                print(f"错误信息: {response.text}")
                
        except Exception as e:
            print(f"搜索异常: {str(e)}")


def test_search_quality():
    """测试搜索结果质量"""
    base_url = "http://localhost:8000"
    keyword = "斗破苍穹"
    
    print(f"\n{'='*60}")
    print(f"搜索质量详细分析 - 关键词: {keyword}")
    print('='*60)
    
    try:
        response = requests.get(f"{base_url}/api/novels/search", 
                              params={"keyword": keyword})
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('data', [])
            
            print(f"总结果数: {len(results)}")
            
            if len(results) == 0:
                print("没有找到搜索结果")
                return
            
            # 统计分析
            valid_count = 0
            high_relevance_count = 0
            exact_match_count = 0
            author_match_count = 0
            
            for result in results:
                book_name = result.get('bookName', '')
                author = result.get('author', '')
                score = result.get('score', 0)
                
                # 有效结果统计
                if book_name and len(book_name.strip()) >= 2:
                    valid_count += 1
                
                # 高相关性结果统计
                if score > 0.5:
                    high_relevance_count += 1
                
                # 精确匹配统计
                if keyword.lower() in book_name.lower():
                    exact_match_count += 1
                
                # 作者匹配统计
                if keyword.lower() in author.lower():
                    author_match_count += 1
            
            print(f"\n质量分析:")
            print(f"- 有效结果: {valid_count}/{len(results)} ({valid_count/len(results)*100:.1f}%)")
            print(f"- 高相关性结果(>0.5): {high_relevance_count}/{len(results)} ({high_relevance_count/len(results)*100:.1f}%)")
            print(f"- 书名精确匹配: {exact_match_count}/{len(results)} ({exact_match_count/len(results)*100:.1f}%)")
            print(f"- 作者匹配: {author_match_count}/{len(results)} ({author_match_count/len(results)*100:.1f}%)")
            
            # 显示最相关的前5个结果
            print(f"\n最相关的前5个结果:")
            for i, result in enumerate(results[:5]):
                print(f"{i+1}. {result.get('bookName')} - {result.get('author')} (相关性: {result.get('score', 0):.2f})")
                
        else:
            print(f"搜索失败，状态码: {response.status_code}")
            
    except Exception as e:
        print(f"测试异常: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("开始测试改进后的搜索功能...")
    
    # 测试搜索相关性
    test_search_relevance()
    
    # 测试搜索质量
    test_search_quality()
    
    print(f"\n{'='*60}")
    print("搜索功能测试完成！")
    print('='*60) 