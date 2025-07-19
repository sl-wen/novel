#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests

def quick_search_test():
    response = requests.get('http://localhost:8000/api/novels/search', params={'keyword': '斗破苍穹'})
    print(f'状态码: {response.status_code}')
    
    if response.status_code == 200:
        data = response.json()
        results = data.get('data', [])
        print(f'结果数量: {len(results)}')
        
        for i, result in enumerate(results[:5]):
            book_name = result.get('bookName', '')
            author = result.get('author', '')
            score = result.get('score', 0)
            print(f'{i+1}. {book_name} - {author} (相关性: {score:.3f})')
    else:
        print(f'错误: {response.text[:200]}')

if __name__ == "__main__":
    quick_search_test() 