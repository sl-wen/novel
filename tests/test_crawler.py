import pytest
import asyncio
import os
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.core.crawler import Crawler
from app.models.book import Book
from app.models.chapter import Chapter
from app.models.search import SearchResult
from app.core.source import Source
from app.core.config import settings # To mock settings.RULES_PATH

# Fixture for Crawler instance
@pytest.fixture
def crawler_instance():
    """Provides a Crawler instance for tests."""
    # Create a temporary directory for rules for this crawler instance if needed
    # For now, tests will manage their own rule paths or mock them.
    return Crawler()

# Fixture for sample Book
@pytest.fixture
def sample_book():
    return Book(
        url="http://example.com/book/1",
        bookName="Test Book",
        author="Test Author",
        intro="A fascinating test introduction.",
        category="Fiction",
        coverUrl="http://example.com/cover.jpg",
        latestChapter="Chapter 10",
        lastUpdateTime="2023-01-01",
        status="Ongoing",
        wordCount="100k"
    )

# Fixture for sample Chapters list
@pytest.fixture
def sample_chapters():
    return [
        Chapter(url="http://example.com/chap/1", title="Chapter 1: The Beginning", content="Content of the first chapter.", order=1),
        Chapter(url="http://example.com/chap/2", title="Chapter 2: The Middle", content="Content of the second chapter.", order=2),
        Chapter(url="http://example.com/chap/3", title="Chapter 3: The End", content="Content of the third chapter.", order=3),
    ]

# Placeholder for tests
def test_crawler_placeholder():
    assert True

# Tests for _get_searchable_sources
def test_get_searchable_sources_loads_valid_rules(crawler_instance, tmp_path, mocker):
    """Test that _get_searchable_sources loads all valid rule files."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()

    # Create dummy rule files
    rule_01_content = {"id": "01", "name": "Test Source 1", "url": "http://test1.com", "search": {"path": "/s1"}}
    rule_02_content = {"id": "02", "name": "Test Source 2", "url": "http://test2.com", "search": {"path": "/s2"}}

    with open(rules_dir / "rule-01.json", "w") as f:
        json.dump(rule_01_content, f)
    with open(rules_dir / "rule-02.json", "w") as f:
        json.dump(rule_02_content, f)

    mocker.patch.object(settings, 'RULES_PATH', str(rules_dir))
    
    # Mock the Source class's _load_rule to prevent it from trying to load from the original settings.RULES_PATH
    # Instead, it will use the rule_data passed during its initialization if we were to test Source directly.
    # For Crawler._get_searchable_sources, it internally creates Source instances.
    # We need to ensure Source instances created by crawler use the mocked path.
    # The Source class itself reads its rule file in __init__ based on source_id and settings.RULES_PATH
    # So, mocking settings.RULES_PATH is the correct approach here.

    sources = crawler_instance._get_searchable_sources()

    assert len(sources) == 2
    source_ids = sorted([s.id for s in sources])
    assert source_ids == ["01", "02"]
    # Check if a specific attribute from the rule is loaded (optional, but good)
    # Find source '01' and check its name
    source_01 = next((s for s in sources if s.id == "01"), None)
    assert source_01 is not None
    assert source_01.rule["name"] == "Test Source 1"


def test_get_searchable_sources_handles_invalid_json(crawler_instance, tmp_path, mocker, caplog):
    """Test graceful handling of one invalid JSON rule file among valid ones."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()

    rule_01_content = {"id": "01", "name": "Test Source 1", "url": "http://test1.com", "search": {"path": "/s1"}}
    with open(rules_dir / "rule-01.json", "w") as f:
        json.dump(rule_01_content, f)
    with open(rules_dir / "rule-invalid.json", "w") as f:
        f.write("this is not json")
    rule_03_content = {"id": "03", "name": "Test Source 3", "url": "http://test3.com", "search": {"path": "/s3"}}
    with open(rules_dir / "rule-03.json", "w") as f:
        json.dump(rule_03_content, f)
    
    mocker.patch.object(settings, 'RULES_PATH', str(rules_dir))

    sources = crawler_instance._get_searchable_sources()

    assert len(sources) == 2 # Only valid rules should be loaded
    source_ids = sorted([s.id for s in sources])
    assert "01" in source_ids
    assert "03" in source_ids
    assert "invalid" not in source_ids # 'invalid' from rule-invalid.json

    # Check logs for error on invalid file
    assert "Failed to load source from" in caplog.text
    assert "rule-invalid.json" in caplog.text


def test_get_searchable_sources_rules_path_not_exist(crawler_instance, tmp_path, mocker, caplog):
    """Test behavior when RULES_PATH does not exist."""
    non_existent_rules_dir = tmp_path / "non_existent_rules"
    mocker.patch.object(settings, 'RULES_PATH', str(non_existent_rules_dir))

    sources = crawler_instance._get_searchable_sources()

    assert len(sources) == 0
    assert f"Rules path {non_existent_rules_dir} is not a directory." in caplog.text


def test_get_searchable_sources_no_rules_found(crawler_instance, tmp_path, mocker, caplog):
    """Test behavior when RULES_PATH exists but contains no rule files."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir() # Empty rules directory
    
    mocker.patch.object(settings, 'RULES_PATH', str(rules_dir))

    sources = crawler_instance._get_searchable_sources()

    assert len(sources) == 0
    assert f"No searchable sources found in {rules_dir}" in caplog.text


# Tests for _sort_search_results
def test_sort_search_results(crawler_instance):
    """Test sorting of search results based on keyword matching."""
    results = [
        SearchResult(sourceId=1, sourceName="s1", url="url1", bookName="The Great Book", author="John Doe"),
        SearchResult(sourceId=1, sourceName="s1", url="url2", bookName="Another Book", author="Jane Great"),
        SearchResult(sourceId=1, sourceName="s1", url="url3", bookName="Keyword Match", author="Author Name"),
        SearchResult(sourceId=1, sourceName="s1", url="url4", bookName="Great Expectations", author="Charles Dickens"),
        SearchResult(sourceId=1, sourceName="s1", url="url5", bookName="My Life by Great Author", author="Great Author"),
        SearchResult(sourceId=1, sourceName="s1", url="url6", bookName="Unrelated Title", author="Some Writer"),
        SearchResult(sourceId=1, sourceName="s1", url="url7", bookName="Book by Keyword", author="Keyword Author"),
    ]

    keyword = "Great"
    sorted_results = crawler_instance._sort_search_results(results, keyword)

    # Expected order:
    # 1. Exact bookName match (case-insensitive, not present here for "Great" exactly)
    # 2. Keyword in bookName (case-insensitive)
    #    - "The Great Book"
    #    - "Great Expectations"
    # 3. Exact author match (case-insensitive)
    #    - "My Life by Great Author" (author: "Great Author")
    # 4. Keyword in author (case-insensitive)
    #    - "Another Book" (author: "Jane Great")
    # 5. Others, sorted by bookName
    #    - "Book by Keyword"
    #    - "Keyword Match"
    #    - "Unrelated Title"

    # Convert to a list of (bookName, author) for easier comparison
    sorted_names_authors = [(r.bookName, r.author) for r in sorted_results]

    expected_order_names_authors = [
        ("The Great Book", "John Doe"),          # Keyword "Great" in bookName
        ("Great Expectations", "Charles Dickens"), # Keyword "Great" in bookName
        ("My Life by Great Author", "Great Author"), # Keyword "Great" (exact) in author
        ("Another Book", "Jane Great"),          # Keyword "Great" in author
        # Alphabetical for the rest:
        ("Book by Keyword", "Keyword Author"),
        ("Keyword Match", "Author Name"),
        ("Unrelated Title", "Some Writer"),
    ]
    
    assert sorted_names_authors == expected_order_names_authors

    keyword_author_match = "Keyword Author"
    sorted_results_author = crawler_instance._sort_search_results(results, keyword_author_match)
    sorted_names_authors_author = [(r.bookName, r.author) for r in sorted_results_author]
    
    # Expected for "Keyword Author":
    # 1. "Book by Keyword" (exact author match)
    # Then alphabetically for others as "Keyword Author" is not in their book names
    expected_author_match_order = [
        ("Book by Keyword", "Keyword Author"), # Exact author match
        ("Another Book", "Jane Great"),
        ("Great Expectations", "Charles Dickens"),
        ("Keyword Match", "Author Name"),
        ("My Life by Great Author", "Great Author"),
        ("The Great Book", "John Doe"),
        ("Unrelated Title", "Some Writer"),
    ]
    assert sorted_names_authors_author == expected_author_match_order

    keyword_exact_book_match = "Keyword Match"
    sorted_results_book = crawler_instance._sort_search_results(results, keyword_exact_book_match)
    sorted_names_authors_book = [(r.bookName, r.author) for r in sorted_results_book]

    # Expected for "Keyword Match" (exact book name):
    # 1. "Keyword Match" (exact book name match)
    # Then alphabetically for others
    expected_book_match_order = [
        ("Keyword Match", "Author Name"), # Exact book name
        ("Another Book", "Jane Great"),
        ("Book by Keyword", "Keyword Author"),
        ("Great Expectations", "Charles Dickens"),
        ("My Life by Great Author", "Great Author"),
        ("The Great Book", "John Doe"),
        ("Unrelated Title", "Some Writer"),
    ]
    assert sorted_names_authors_book == expected_book_match_order


# Tests for _generate_epub
def test_generate_epub(crawler_instance, sample_book, sample_chapters, tmp_path):
    """Test EPUB file generation."""
    output_file_path = tmp_path / "test_book.epub"
    
    # Ensure the parent directory for the output file exists (tmp_path itself)
    # No, _generate_epub itself doesn't create parent dirs, it expects file_path to be writeable.
    # The _generate_file method in Crawler handles creating the download_dir.
    # Here, we are testing _generate_epub directly, so tmp_path is the directory.

    returned_path_str = crawler_instance._generate_epub(sample_book, sample_chapters, output_file_path)

    assert str(output_file_path) == returned_path_str
    assert output_file_path.exists()
    assert output_file_path.stat().st_size > 0
    # Add a basic check for epub validity if possible and simple, e.g. by trying to read it with ebooklib
    # For now, just existence and non-empty as per requirements.
    try:
        import ebooklib.epub
        ebooklib.epub.read_epub(str(output_file_path))
        epub_valid = True
    except Exception:
        epub_valid = False
    assert epub_valid, "Generated EPUB file is not valid or readable by ebooklib"


# Tests for _generate_pdf
def test_generate_pdf(crawler_instance, sample_book, sample_chapters, tmp_path):
    """Test PDF file generation."""
    output_file_path = tmp_path / "test_book.pdf"

    returned_path_str = crawler_instance._generate_pdf(sample_book, sample_chapters, output_file_path)

    assert str(output_file_path) == returned_path_str
    assert output_file_path.exists()
    assert output_file_path.stat().st_size > 0
    # Basic check for PDF validity (e.g., starts with %PDF)
    with open(output_file_path, "rb") as f:
        assert f.read(4) == b'%PDF', "Generated PDF file does not start with %PDF"
