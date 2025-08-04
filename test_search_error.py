#!/usr/bin/env python3
"""
Test script to simulate the search process and identify the bookName attribute error
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.search import SearchResult
import asyncio

async def test_search_process():
    """Test the search process to identify the bookName error"""
    try:
        # Create a mock SearchResult list to simulate search results
        mock_results = [
            SearchResult(
                sourceId=1,
                sourceName="test source",
                url="http://test.com/book1",
                bookName="测试小说1"
            ),
            SearchResult(
                sourceId=2,
                sourceName="test source 2",
                url="http://test.com/book2",
                bookName="测试小说2"
            )
        ]
        
        print(f"Created {len(mock_results)} mock results")
        
        # Test accessing bookName attribute
        for i, result in enumerate(mock_results):
            print(f"Result {i}: Type={type(result)}")
            print(f"  Has bookName: {hasattr(result, 'bookName')}")
            print(f"  bookName value: {result.bookName}")
            print(f"  Available attributes: {[attr for attr in dir(result) if not attr.startswith('_')]}")
            print()
        
        # Test the specific line that might be causing the error
        for i, result in enumerate(mock_results):
            try:
                print(f"Processing result {i+1}: 书名='{result.bookName}', 作者='{result.author}', URL='{result.url}'")
            except AttributeError as e:
                print(f"Error accessing bookName on result {i}: {e}")
                print(f"Result type: {type(result)}")
                print(f"Result dir: {dir(result)}")
                break
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_search_process())