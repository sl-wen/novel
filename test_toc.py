#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests

def test_toc():
    url = 'http://localhost:8000/api/novels/toc'
    params = {
        'url': 'https://www.tianxibook.com/book/95033088/',
        'sourceId': 5
    }
    
    response = requests.get(url, params=params)
    print(f'状态码: {response.status_code}')
    
    if response.status_code == 200:
        data = response.json()
        chapters = data.get('data', [])
        print(f'找到 {len(chapters)} 个章节')
        
        for i, chapter in enumerate(chapters[:5]):
            print(f'  章节 {i+1}: {chapter.get("title")} - {chapter.get("url")}')
    else:
        print(f'错误: {response.text}')

if __name__ == "__main__":
    test_toc() 