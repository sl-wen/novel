#!/usr/bin/env python3
"""
Debug script to test SearchResult model and identify the issue
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.search import SearchResult
from app.services.novel_service import NovelService
import asyncio

async def test_search():
    """Test the search functionality"""
    try:
        service = NovelService()
        
        # Test creating a SearchResult
        test_result = SearchResult(
            sourceId=1,
            sourceName="test",
            url="http://test.com",
            bookName="test book"
        )
        print(f"Test SearchResult created: {test_result.bookName}")
        print(f"Type: {type(test_result)}")
        print(f"Has bookName: {hasattr(test_result, 'bookName')}")
        
        # Test search
        print("\nTesting search...")
        results = await service.search("斗破苍穹")
        print(f"Search returned {len(results)} results")
        
        if results:
            for i, result in enumerate(results):
                print(f"Result {i}: Type={type(result)}")
                if hasattr(result, 'bookName'):
                    print(f"  bookName: {result.bookName}")
                else:
                    print(f"  No bookName attribute!")
                    print(f"  Available attributes: {dir(result)}")
                    break
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_search())