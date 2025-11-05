"""Unit tests for RSS feed functionality with mocked external dependencies."""

import importlib
import os
import time
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import news.rss_parser
from news.article_cache import fetch_and_cache_articles_for_symbol
from news.rss_parser import _collect_entries_from_feed, fetch_rss_news, get_news


class Test24HFiltering:
    """Test 24-hour filtering logic without expensive external calls."""

    def test_24h_filtering_with_recent_articles(self):
        """Test that articles within 24 hours are processed."""
        # Create mock entries - use times relative to "now" to ensure they're within 24h
        now = datetime.now(UTC)

        recent_entry = Mock()
        recent_entry.link = "https://example.com/recent"
        recent_entry.title = "Recent Article"
        recent_entry.published = "2025-11-05T12:00:00+00:00"
        # Set published_parsed to 1 hour ago
        one_hour_ago = now - timedelta(hours=1)
        recent_entry.published_parsed = time.struct_time((
            one_hour_ago.year, one_hour_ago.month, one_hour_ago.day,
            one_hour_ago.hour, one_hour_ago.minute, one_hour_ago.second, -1, -1, -1,
        ))

        old_entry = Mock()
        old_entry.link = "https://example.com/old"
        old_entry.title = "Old Article"
        old_entry.published = "2025-11-03T12:00:00+00:00"
        # Set published_parsed to 48 hours ago (should be filtered out)
        two_days_ago = now - timedelta(hours=48)
        old_entry.published_parsed = time.struct_time((
            two_days_ago.year, two_days_ago.month, two_days_ago.day,
            two_days_ago.hour, two_days_ago.minute, two_days_ago.second, -1, -1, -1,
        ))

        mock_feed = Mock()
        mock_feed.entries = [recent_entry, old_entry]

        with patch("news.rss_parser.feedparser.parse", return_value=mock_feed), \
             patch("news.rss_parser.is_article_cache_enabled", return_value=False), \
             patch("news.rss_parser._load_symbols_for_detection", return_value=[]), \
                          patch("news.rss_parser._process_feed_entry",
                   return_value=(None, {"title": "Recent Article", "is_relevant": True})):

            result = fetch_rss_news("https://example.com/feed", "test", "test-class")

            # Should return 1 article (the recent one, old one filtered out)
            assert len(result) == 1
            assert result[0]["title"] == "Recent Article"

    def test_24h_filtering_with_all_old_articles(self):
        """Test that articles older than 24 hours are filtered out."""
        # Use a fixed current time for consistent testing
        current_time = datetime(2025, 11, 5, 15, 0, 0, tzinfo=UTC)

        # Create mock entries with old timestamps
        old_entry1 = Mock()
        old_entry1.link = "https://example.com/old1"
        old_entry1.title = "Old Article 1"
        old_entry1.published = "2025-11-03T12:00:00+00:00"  # 2 days ago
        old_entry1.published_parsed = time.struct_time((2025, 11, 3, 12, 0, 0, -1, -1, -1))

        old_entry2 = Mock()
        old_entry2.link = "https://example.com/old2"
        old_entry2.title = "Old Article 2"
        old_entry2.published = "2025-11-02T12:00:00+00:00"  # 3 days ago
        old_entry2.published_parsed = time.struct_time((2025, 11, 2, 12, 0, 0, -1, -1, -1))

        mock_feed = Mock()
        mock_feed.entries = [old_entry1, old_entry2]

        with patch("news.rss_parser.feedparser.parse", return_value=mock_feed), \
             patch("news.rss_parser.is_article_cache_enabled", return_value=False), \
             patch("news.rss_parser._load_symbols_for_detection", return_value=[]), \
             patch("news.rss_parser.datetime") as mock_datetime:

            # Mock datetime.now to return our fixed time
            mock_datetime.now.return_value = current_time
            mock_datetime.side_effect = lambda *args, **kwargs: \
                datetime(*args, **kwargs, tzinfo=UTC) if args or kwargs else current_time

            result = fetch_rss_news("https://example.com/feed", "test", "test-class")

            # Should return empty list (all articles filtered out)
            assert len(result) == 0

    def test_24h_filtering_with_cached_articles(self):
        """Test that cached articles are skipped."""
        # Create mock entries
        cached_entry = Mock()
        cached_entry.link = "https://example.com/cached"
        cached_entry.title = "Cached Article"
        cached_entry.published = "2025-11-05T12:00:00+00:00"
        cached_entry.published_parsed = time.struct_time((2025, 11, 5, 12, 0, 0, -1, -1, -1))

        fresh_entry = Mock()
        fresh_entry.link = "https://example.com/fresh"
        fresh_entry.title = "Fresh Article"
        fresh_entry.published = "2025-11-05T13:00:00+00:00"
        fresh_entry.published_parsed = time.struct_time((2025, 11, 5, 13, 0, 0, -1, -1, -1))

        mock_feed = Mock()
        mock_feed.entries = [cached_entry, fresh_entry]

        with patch("news.rss_parser.feedparser.parse", return_value=mock_feed), \
             patch("news.rss_parser.is_article_cache_enabled", return_value=True), \
             patch("news.rss_parser.article_exists_in_cache",
                   side_effect=lambda link: link == "https://example.com/cached"), \
             patch("news.rss_parser._load_symbols_for_detection", return_value=[]), \
             patch("news.rss_parser._process_feed_entry",
                   return_value=(None, {"title": "Fresh Article", "is_relevant": True})):

            result = fetch_rss_news("https://example.com/feed", "test", "test-class")

            # Should return 1 article (the fresh one, cached one skipped)
            assert len(result) == 1
            assert result[0]["title"] == "Fresh Article"

    def test_24h_filtering_with_mixed_relevance(self):
        """Test early stopping when target relevant articles are found."""
        # Create multiple recent entries
        entries = []
        for i in range(15):  # More than NEWS_ARTICLE_LIMIT (10)
            entry = Mock()
            entry.link = f"https://example.com/article{i}"
            entry.title = f"Article {i}"
            entry.published = f"2025-11-05T{i+10:02d}:00:00+00:00"
            entry.published_parsed = (2025, 11, 5, i+10, 0, 0, 0, 0, 0)
            entries.append(entry)

        mock_feed = Mock()
        mock_feed.entries = entries

        # Mock processing to return relevant articles for first 10, then irrelevant
        def mock_process_feed_entry(*args, **kwargs):
            entry = kwargs.get("entry") or (args[0] if args else None)
            if entry and hasattr(entry, "link"):
                article_num = int(entry.link.split("article")[1])
                if article_num < 10:  # First 10 are relevant
                    return (None, {"title": f"Article {article_num}", "is_relevant": True})
                # Rest are not relevant
                return (None, None)
            return (None, None)

        with patch("news.rss_parser.feedparser.parse", return_value=mock_feed), \
             patch("news.rss_parser.is_article_cache_enabled", return_value=False), \
             patch("news.rss_parser._load_symbols_for_detection", return_value=[]), \
             patch("news.rss_parser._process_feed_entry", side_effect=mock_process_feed_entry):

            result = fetch_rss_news("https://example.com/feed", "test", "test-class")

            # Should return exactly NEWS_ARTICLE_LIMIT (10) articles
            assert len(result) == 10
            # Should stop processing after finding 10 relevant articles
            for i, article in enumerate(result):
                assert article["title"] == f"Article {i}"


class TestCollectEntriesFromFeed:
    """Test _collect_entries_from_feed functionality."""

    def test_collect_entries_success(self):
        """Test successful collection from a feed."""
        current_time = datetime(2025, 11, 5, 15, 0, 0, tzinfo=UTC)

        # Create mock entries
        entry1 = Mock()
        entry1.link = "https://example.com/1"
        entry1.title = "Article 1"
        entry1.published_parsed = time.struct_time((2025, 11, 5, 12, 0, 0, -1, -1, -1))  # Recent

        entry2 = Mock()
        entry2.link = "https://example.com/2"
        entry2.title = "Article 2"
        entry2.published_parsed = time.struct_time((2025, 11, 3, 12, 0, 0, -1, -1, -1))  # Too old

        mock_feed = Mock()
        mock_feed.entries = [entry1, entry2]

        with patch("news.rss_parser.feedparser.parse", return_value=mock_feed), \
             patch("news.rss_parser.is_article_cache_enabled", return_value=False):

            result = _collect_entries_from_feed(
                feed_url="https://example.com/feed",
                source="test",
                class_name="test-class",
                cache_enabled=False,
                current_time=current_time,
            )

            # Should return 1 entry (entry2 filtered out as too old)
            assert len(result) == 1
            assert result[0].title == "Article 1"

    def test_collect_entries_feed_error(self):
        """Test handling of feed parsing errors."""
        current_time = datetime.now(UTC)

        with patch("news.rss_parser.feedparser.parse", side_effect=ValueError("Invalid feed")):

            result = _collect_entries_from_feed(
                feed_url="https://invalid-feed.com",
                source="test",
                class_name="test-class",
                cache_enabled=False,
                current_time=current_time,
            )

            # Should return empty list on error
            assert result == []


class TestCurrentReportLimits:
    """Test CURRENT_REPORT_ARTICLE_LIMIT configuration and behavior."""

    @patch.dict("os.environ", {"CURRENT_REPORT_ARTICLE_LIMIT": "5"})
    def test_current_report_article_limit_from_env(self):
        """Test that CURRENT_REPORT_ARTICLE_LIMIT is read from environment."""
        # Force reimport to pick up env var
        importlib.reload(news.rss_parser)

        assert news.rss_parser.CURRENT_REPORT_ARTICLE_LIMIT == 5

    def test_current_report_article_limit_default(self):
        """Test that CURRENT_REPORT_ARTICLE_LIMIT defaults to 3."""
        # Remove env var if it exists and force reimport
        os.environ.pop("CURRENT_REPORT_ARTICLE_LIMIT", None)

        importlib.reload(news.rss_parser)

        assert news.rss_parser.CURRENT_REPORT_ARTICLE_LIMIT == 3

    @patch("news.rss_parser._collect_all_rss_entries")
    @patch("news.rss_parser._process_entries_until_target")
    @patch("news.rss_parser.is_article_cache_enabled", return_value=False)
    @patch("news.rss_parser._load_symbols_for_detection", return_value=[])
    def test_get_news_uses_custom_target_relevant(self, mock_collect, mock_process):
        """Test that get_news() accepts and uses custom target_relevant parameter."""
        mock_collect.return_value = []
        mock_process.return_value = ([], 0)

        # Test with custom limit
        get_news(target_relevant=7)

        # Verify _process_entries_until_target was called with target_relevant=7
        mock_process.assert_called_once()
        call_args = mock_process.call_args
        assert call_args[1]["target_relevant"] == 7

    @patch("news.rss_parser.get_news")
    @patch("news.article_cache.get_articles_for_symbol")
    def test_fetch_and_cache_articles_for_symbol_integration(self, mock_get_articles,
                                                          mock_get_news):
        """Test that fetch_and_cache_articles_for_symbol uses CURRENT_REPORT_ARTICLE_LIMIT."""
        # Mock the dependencies
        mock_get_news.return_value = None
        mock_get_articles.return_value = []

        # Call the function
        result = fetch_and_cache_articles_for_symbol("BTC", hours=24)

        # Verify get_news was called with CURRENT_REPORT_ARTICLE_LIMIT
        mock_get_news.assert_called_once_with(target_relevant=3)  # Default value

        # Verify get_articles_for_symbol was called with correct parameters
        mock_get_articles.assert_called_once_with("BTC", 24)

        # Verify return value
        assert result == []
