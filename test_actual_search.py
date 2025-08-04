#!/usr/bin/env python3
"""
Test script to run actual search and identify the bookName error
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
import logging

# Set up logging to see debug messages
logging.basicConfig(level=logging.DEBUG)

from app.services.novel_service import NovelService

async def test_actual_search():
    """Test the actual search functionality"""
    try:
        service = NovelService()
        
        # Test search with a simple keyword
        print("Starting search...")
        results = await service.search("斗破苍穹")
        
        print(f"Search completed. Found {len(results)} results.")
        
        # Check each result
        for i, result in enumerate(results):
            print(f"Result {i+1}: Type={type(result)}")
            if hasattr(result, 'bookName'):
                print(f"  bookName: {result.bookName}")
            else:
                print(f"  No bookName attribute!")
                print(f"  Available attributes: {dir(result)}")
        
    except Exception as e:
        print(f"Error during search: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_actual_search())