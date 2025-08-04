#!/usr/bin/env python3
"""
Simple test script to check SearchResult model
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app.models.search import SearchResult
    print("✓ Successfully imported SearchResult")
    
    # Test creating a SearchResult
    result = SearchResult(
        sourceId=1,
        sourceName="test",
        url="http://test.com",
        bookName="test book"
    )
    print(f"✓ Successfully created SearchResult: {result.bookName}")
    print(f"✓ Type: {type(result)}")
    print(f"✓ Has bookName: {hasattr(result, 'bookName')}")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()