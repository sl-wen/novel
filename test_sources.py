#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试书源连通性
"""

import requests
import json
from pathlib import Path
import time
import urllib.parse

def test_source_connectivity():
    """测试所有书源的连通性"""
    rules_path = Path("resources/rule/new")
    
    print("书源连通性测试")
    print("=" * 60)
    
    working_sources = []
    failed_sources = []
    
    for rule_file in sorted(rules_path.glob("rule-*.json")):
        try:
            with open(rule_file, 'r', encoding='utf-8') as f:
                rule = json.load(f)
            
            source_id = rule.get('id')
            source_name = rule.get('name')
            base_url = rule.get('url')
            
            print(f"\n测试书源 {source_id}: {source_name}")
            print(f"基础URL: {base_url}")
            
            # 测试基础URL连通性
            success = test_url(base_url)
            
            if success:
                # 测试搜索功能
                search_rule = rule.get('search', {})
                if search_rule:
                    search_success = test_search_url(rule, "test")
                    if search_success:
                        working_sources.append((source_id, source_name))
                        print(f"✅ 工作正常")
                    else:
                        failed_sources.append((source_id, source_name, "搜索失败"))
                        print(f"❌ 搜索功能异常")
                else:
                    failed_sources.append((source_id, source_name, "无搜索规则"))
                    print(f"⚠️  无搜索规则")
            else:
                failed_sources.append((source_id, source_name, "连接失败"))
                print(f"❌ 连接失败")
                
        except Exception as e:
            print(f"❌ 规则文件错误: {str(e)}")
    
    print(f"\n" + "=" * 60)
    print("测试总结:")
    print(f"可用书源: {len(working_sources)}")
    print(f"失败书源: {len(failed_sources)}")
    
    if working_sources:
        print(f"\n可用书源列表:")
        for source_id, source_name in working_sources:
            print(f"  {source_id}: {source_name}")
    
    if failed_sources:
        print(f"\n失败书源列表:")
        for source_id, source_name, reason in failed_sources:
            print(f"  {source_id}: {source_name} - {reason}")

def test_url(url: str, timeout: int = 10) -> bool:
    """测试URL连通性"""
    try:
        response = requests.get(url, timeout=timeout, 
                              headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        return response.status_code == 200
    except Exception:
        return False

def test_search_url(rule: dict, keyword: str) -> bool:
    """测试搜索URL"""
    try:
        search_rule = rule.get('search', {})
        search_url = search_rule.get('url', '')
        method = search_rule.get('method', 'get').lower()
        
        if not search_url:
            return False
        
        # 处理URL中的占位符
        encoded_keyword = urllib.parse.quote(keyword)
        search_url = search_url.replace("%s", encoded_keyword)
        search_url = search_url.replace("{keyword}", encoded_keyword)
        
        # 如果URL不是以http开头，则添加baseUri
        if not search_url.startswith("http"):
            base_url = rule.get('url', '').rstrip('/')
            search_url = f"{base_url}/{search_url.lstrip('/')}"
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        if method == 'post':
            data_template = search_rule.get('data', '')
            if data_template:
                # 处理POST数据
                data = data_template.replace("%s", keyword)
                try:
                    json_data = json.loads(data)
                    response = requests.post(search_url, json=json_data, headers=headers, timeout=10)
                except json.JSONDecodeError:
                    # 尝试表单数据
                    if ":" in data and "{" in data:
                        parts = data.strip("{}").split(":", 1)
                        key = parts[0].strip()
                        value = parts[1].strip()
                        form_data = {key: value}
                    else:
                        form_data = {"keyword": keyword}
                    response = requests.post(search_url, data=form_data, headers=headers, timeout=10)
            else:
                response = requests.post(search_url, headers=headers, timeout=10)
        else:
            response = requests.get(search_url, headers=headers, timeout=10)
        
        return response.status_code in [200, 201]
        
    except Exception as e:
        print(f"    搜索测试异常: {str(e)}")
        return False

if __name__ == "__main__":
    test_source_connectivity() 