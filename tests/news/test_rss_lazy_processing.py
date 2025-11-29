"""Unit tests for RSS lazy processing functionality."""

import importlib
import os
import time
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

from news import article_cache, constants, rss_parser
from news.rss_parser import (
    RSSEntry,
    _collect_all_rss_entries,
    _collect_entries_from_feed,
    _is_entry_processable,
    _parse_rss_entry,
    _process_entries_until_target,
    fetch_and_cache_articles_for_symbol,
)


class TestRSSEntry:
    """Test RSSEntry dataclass functionality."""

    def test_rsse_entry_creation(self):
        """Test creating RSSEntry with valid data."""
        published_time = datetime.now(UTC)

        entry = RSSEntry(
            source="coindesk",
            title="Bitcoin Price Analysis",
            link="https://coindesk.com/bitcoin-price",
            published_time=published_time,
            published_str="2025-11-05T10:00:00+00:00",
            class_name="document-body",
            raw_entry=Mock(),
        )

        assert entry.source == "coindesk"
        assert entry.title == "Bitcoin Price Analysis"
        assert entry.link == "https://coindesk.com/bitcoin-price"
        assert entry.published_time == published_time
        assert entry.published_str == "2025-11-05T10:00:00+00:00"
        assert entry.class_name == "document-body"
        assert entry.raw_entry is not None

    def test_rsse_entry_slots(self):
        """Test that RSSEntry uses slots for memory efficiency."""
        entry = RSSEntry(
            source="test",
            title="test",
            link="https://test.com",
            published_time=datetime.now(UTC),
            published_str="test",
            class_name="test",
            raw_entry=Mock(),
        )

        # Should not be able to add arbitrary attributes (slots behavior)
        # We test this by checking that the object doesn't have __dict__
        assert not hasattr(entry, "__dict__"), "RSSEntry should use __slots__ and not have __dict__"


class TestParseRSSEntry:
    """Test _parse_rss_entry function."""

    def test_parse_valid_entry(self):
        """Test parsing a valid RSS entry."""
        current_time = datetime.now(UTC)

        # Mock RSS entry
        mock_entry = Mock()
        mock_entry.link = "https://coindesk.com/article"
        mock_entry.title = "Bitcoin News"
        mock_entry.published = "Wed, 05 Nov 2025 10:00:00 +0000"
        mock_entry.published_parsed = None

        result = _parse_rss_entry(
            entry=mock_entry,
            source="coindesk",
            class_name="document-body",
            current_time=current_time,
        )

        assert result is not None
        assert type(result).__name__ == "RSSEntry"
        assert result.source == "coindesk"
        assert result.title == "Bitcoin News"
        assert result.link == "https://coindesk.com/article"
        assert result.class_name == "document-body"
        assert result.published_str == "Wed, 05 Nov 2025 10:00:00 +0000"
        assert isinstance(result.published_time, datetime)

    def test_parse_entry_with_missing_fields(self):
        """Test parsing entry with missing fields returns None."""
        current_time = datetime.now(UTC)

        # Mock entry with missing link
        mock_entry = Mock()
        mock_entry.link = None  # Missing link
        mock_entry.title = "Bitcoin News"
        mock_entry.published = "Wed, 05 Nov 2025 10:00:00 +0000"

        result = _parse_rss_entry(
            entry=mock_entry,
            source="coindesk",
            class_name="document-body",
            current_time=current_time,
        )

        assert result is None

    def test_parse_entry_with_invalid_date(self):
        """Test parsing entry with invalid date uses current time."""
        current_time = datetime.now(UTC)

        # Mock entry with invalid date
        mock_entry = Mock()
        mock_entry.link = "https://coindesk.com/article"
        mock_entry.title = "Bitcoin News"
        mock_entry.published = "invalid date"
        mock_entry.published_parsed = None

        result = _parse_rss_entry(
            entry=mock_entry,
            source="coindesk",
            class_name="document-body",
            current_time=current_time,
        )

        assert result is not None
        assert result.published_time == current_time


class TestIsEntryProcessable:
    """Test _is_entry_processable function."""

    def test_processable_entry(self):
        """Test that a valid, non-cached, recent entry is processable."""
        current_time = datetime.now(UTC)
        published_time = current_time - timedelta(hours=12)  # 12 hours ago

        entry = RSSEntry(
            source="coindesk",
            title="Bitcoin News",
            link="https://coindesk.com/article",
            published_time=published_time,
            published_str="test",
            class_name="test",
            raw_entry=Mock(),
        )

        with patch("news.rss_parser.article_exists_in_cache", return_value=False):
            result = _is_entry_processable(
                entry=entry,
                cache_enabled=True,
                current_time=current_time,
            )

            assert result is True

    def test_not_processable_cached_entry(self):
        """Test that cached entries are not processable."""
        current_time = datetime.now(UTC)
        published_time = current_time - timedelta(hours=12)

        entry = RSSEntry(
            source="coindesk",
            title="Bitcoin News",
            link="https://coindesk.com/article",
            published_time=published_time,
            published_str="test",
            class_name="test",
            raw_entry=Mock(),
        )

        with patch("news.rss_parser.article_exists_in_cache", return_value=True):
            result = _is_entry_processable(
                entry=entry,
                cache_enabled=True,
                current_time=current_time,
            )

            assert result is False

    def test_not_processable_old_entry(self):
        """Test that entries older than 24 hours are not processable."""
        current_time = datetime.now(UTC)
        published_time = current_time - timedelta(hours=25)  # 25 hours ago

        entry = RSSEntry(
            source="coindesk",
            title="Bitcoin News",
            link="https://coindesk.com/article",
            published_time=published_time,
            published_str="test",
            class_name="test",
            raw_entry=Mock(),
        )

        with patch("news.rss_parser.article_exists_in_cache", return_value=False):
            result = _is_entry_processable(
                entry=entry,
                cache_enabled=True,
                current_time=current_time,
            )

            assert result is False

    def test_processable_with_cache_disabled(self):
        """Test that entries are processable when cache is disabled."""
        current_time = datetime.now(UTC)
        published_time = current_time - timedelta(hours=12)

        entry = RSSEntry(
            source="coindesk",
            title="Bitcoin News",
            link="https://coindesk.com/article",
            published_time=published_time,
            published_str="test",
            class_name="test",
            raw_entry=Mock(),
        )

        # Cache disabled, so article_exists_in_cache should not be called
        result = _is_entry_processable(
            entry=entry,
            cache_enabled=False,
            current_time=current_time,
        )

        assert result is True


class TestCollectAllRSSEntries:
    """Test _collect_all_rss_entries functionality."""

    @patch("news.rss_parser.feedparser")
    @patch("news.rss_parser._collect_entries_from_feed")
    @patch("news.rss_parser.app_logger")
    def test_collect_all_rss_entries_success(self, mock_logger, mock_collect_feed, mock_feedparser):
        """Test successful collection from all feeds."""
        # Mock feedparser (not used in this test since we mock _collect_entries_from_feed)
        mock_feedparser.parse.return_value = Mock()

        # Mock _collect_entries_from_feed to return entries for each feed
        current_time = datetime.now(UTC)

        # Create mock entry for the only active feed (cointelegraph)
        cointelegraph_entry = RSSEntry(
            source="cointelegraph",
            title="Cointelegraph Article",
            link="https://cointelegraph.com/article",
            published_time=current_time - timedelta(minutes=30),
            published_str="recent",
            class_name="test",
            raw_entry=Mock(),
        )

        # Only cointelegraph is enabled, so only one call to _collect_entries_from_feed
        mock_collect_feed.side_effect = [
            [cointelegraph_entry],  # cointelegraph (only active feed)
        ]

        result = _collect_all_rss_entries(
            cache_enabled=True,
            current_time=current_time,
        )

        # Should have collected 1 entry from the only active feed
        assert len(result) == 1
        assert result[0].title == "Cointelegraph Article"
        assert result[0].source == "cointelegraph"

        # Verify logger was called with stats
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args[0][0]
        assert "Collected 1 RSS entries from 7 feeds" in log_call
        assert "cointelegraph=1" in log_call

    @patch("news.rss_parser.feedparser")
    @patch("news.rss_parser._collect_entries_from_feed")
    def test_collect_all_rss_entries_empty_feeds(
        self,
        mock_collect_feed,
        _mock_feedparser,
    ):
        """Test collection when all feeds return empty results."""
        mock_collect_feed.return_value = []
        current_time = datetime.now(UTC)

        result = _collect_all_rss_entries(
            cache_enabled=True,
            current_time=current_time,
        )

        assert result == []


class TestCollectEntriesFromFeed:
    """Test _collect_entries_from_feed functionality."""

    @patch("news.rss_parser.feedparser")
    @patch("news.rss_parser._parse_rss_entry")
    @patch("news.rss_parser._is_entry_processable")
    @patch("news.rss_parser.app_logger")
    def test_collect_entries_from_feed_success(
        self,
        _mock_logger,
        mock_is_processable,
        mock_parse_entry,
        mock_feedparser,
    ):
        """Test successful collection from a single feed."""
        # Mock feed with entries
        mock_feed = Mock()
        mock_entry1 = Mock()
        mock_entry2 = Mock()
        mock_feed.entries = [mock_entry1, mock_entry2]
        mock_feedparser.parse.return_value = mock_feed

        current_time = datetime.now(UTC)

        # Mock parsing - first entry parses successfully, second fails
        parsed_entry = RSSEntry(
            source="coindesk",
            title="Test Article",
            link="https://coindesk.com/test",
            published_time=current_time - timedelta(hours=1),
            published_str="test",
            class_name="document-body",
            raw_entry=mock_entry1,
        )

        mock_parse_entry.side_effect = [parsed_entry, None]  # Second entry fails to parse
        mock_is_processable.return_value = True  # First entry is processable

        result = _collect_entries_from_feed(
            feed_url="https://coindesk.com/feed",
            source="coindesk",
            class_name="document-body",
            cache_enabled=True,
            current_time=current_time,
        )

        assert len(result) == 1
        assert result[0] == parsed_entry

    @patch("news.rss_parser.feedparser")
    @patch("news.rss_parser.app_logger")
    def test_collect_entries_from_feed_parse_error(self, mock_logger, mock_feedparser):
        """Test handling of feed parsing errors."""
        # Mock feedparser to raise an exception
        mock_feedparser.parse.side_effect = ValueError("Invalid feed")

        current_time = datetime.now(UTC)

        result = _collect_entries_from_feed(
            feed_url="https://invalid-feed.com",
            source="invalid",
            class_name="test",
            cache_enabled=True,
            current_time=current_time,
        )

        assert result == []
        # Verify warning was logged
        mock_logger.warning.assert_called_once()
        log_call = mock_logger.warning.call_args[0][0]
        assert "Failed to collect entries from https://invalid-feed.com" in log_call


class TestComprehensiveLazyProcessing:
    """Comprehensive tests for the complete lazy processing pipeline with realistic data."""

    def create_mock_feed_entries(self, source: str, count: int, base_time: datetime) -> list[Mock]:
        """Create mock RSS entries for a feed with realistic data."""
        entries = []

        for i in range(count):
            # Create entries with varying timestamps (newest first within feed)
            published_time = base_time - timedelta(minutes=i * 30)  # 30 min intervals

            entry = Mock()
            entry.title = f"{source.upper()} Article {i + 1}: Crypto Market Update"
            entry.link = f"https://{source.lower()}.com/article-{i + 1}"
            entry.published = published_time.isoformat()
            entry.published_parsed = time.struct_time(
                (
                    published_time.year,
                    published_time.month,
                    published_time.day,
                    published_time.hour,
                    published_time.minute,
                    published_time.second,
                    -1,
                    -1,
                    -1,
                ),
            )

            # Add some content that might be relevant to crypto symbols
            if i % 3 == 0:
                entry.summary = (
                    "Bitcoin and Ethereum showing strong performance in today's "
                    "market. BTC up 5%, ETH up 3%."
                )
            elif i % 3 == 1:
                entry.summary = "New developments in DeFi space with innovative protocols emerging."
            else:
                entry.summary = (
                    "Market analysis shows increased institutional interest in digital assets."
                )

            entries.append(entry)

        return entries

    def test_comprehensive_cross_feed_sorting(self):
        """Test that articles from the active feed (cointelegraph) are properly.

        sorted by date (newest first).
        """
        base_time = datetime.now(UTC)

        # Create mock feed for the only active feed (cointelegraph)
        feed_data = {
            "cointelegraph": {"count": 10, "base_offset": timedelta(hours=0)},  # active feed
        }

        mock_feeds = {}
        for source, config in feed_data.items():
            feed_time = base_time - config["base_offset"]
            mock_feeds[source] = Mock()
            mock_feeds[source].entries = self.create_mock_feed_entries(
                source,
                config["count"],
                feed_time,
            )

        with (
            patch("news.rss_parser.feedparser.parse") as mock_feedparser,
            patch("news.rss_parser._collect_entries_from_feed") as mock_collect_feed,
            patch("news.rss_parser._has_required_hashtags") as mock_hashtags,
        ):
            # Mock feedparser to return our mock feed
            def feedparser_side_effect(url):
                if "cointelegraph.com" in url:
                    return mock_feeds["cointelegraph"]
                return Mock(entries=[])

            mock_feedparser.side_effect = feedparser_side_effect

            # Mock hashtag checking to allow all articles through
            mock_hashtags.return_value = True

            # Mock _collect_entries_from_feed to return all entries for cointelegraph
            def collect_feed_side_effect(**kwargs):
                source = None
                if "cointelegraph.com" in kwargs["feed_url"]:
                    source = "cointelegraph"

                if source and source in mock_feeds:
                    return [
                        Mock(
                            source=source,
                            title=entry.title,
                            link=entry.link,
                            published_time=datetime.fromisoformat(entry.published),
                            published_str=entry.published,
                            class_name="test-class",
                            raw_entry=entry,
                        )
                        for entry in mock_feeds[source].entries
                    ]
                return []

            mock_collect_feed.side_effect = collect_feed_side_effect

            # Collect all entries
            result = _collect_all_rss_entries(cache_enabled=False, current_time=base_time)

            # Should have collected entries from the active feed
            assert len(result) == 10, f"Expected 10 entries, got {len(result)}"

            # Verify entries are sorted by published_time (newest first)
            for i in range(len(result) - 1):
                assert result[i].published_time >= result[i + 1].published_time, (
                    f"Entry {i} ({result[i].published_time}) should be newer than "
                    f"entry {i + 1} ({result[i + 1].published_time})"
                )

            # Verify we have entries from cointelegraph
            sources_found = {entry.source for entry in result}
            expected_sources = {"cointelegraph"}
            assert sources_found == expected_sources, (
                f"Expected sources {expected_sources}, got {sources_found}"
            )

    def test_early_stopping_behavior(self):
        """Test that processing stops after finding target relevant articles."""
        # Create 20 test entries with varying relevance
        base_time = datetime.now(UTC)
        entries = []

        for i in range(20):
            # Create entries with decreasing timestamps
            published_time = base_time - timedelta(minutes=i * 5)

            entry = RSSEntry(
                source="test",
                title=f"Article {i + 1}",
                link=f"https://test.com/article-{i + 1}",
                published_time=published_time,
                published_str=published_time.isoformat(),
                class_name="test-class",
                raw_entry=Mock(),
            )
            entries.append(entry)

        # Mock the processing function to return relevant results for first 7 entries
        relevant_count = 0

        def mock_process_entry(*_args, **_kwargs):
            nonlocal relevant_count
            relevant_count += 1
            title = f"Article {relevant_count}"
            is_relevant = relevant_count <= 5  # First 5 are relevant
            payload = {
                "source": "test",
                "title": title,
                "link": f"https://test.com/article-{relevant_count}",
                "is_relevant": is_relevant,
                "relevance_score": 0.8 if is_relevant else 0.2,
                "elapsed_time": 1.5,
            }
            return (Mock(), payload)

        with (
            patch("news.rss_parser._process_feed_entry", side_effect=mock_process_entry),
            patch("news.rss_parser.is_article_cache_enabled", return_value=False),
            patch("news.rss_parser._load_symbols_for_detection", return_value=["BTC"]),
        ):
            relevant_articles, total_processed = _process_entries_until_target(
                entries=entries,
                current_time=base_time,
                cache_enabled=False,
                symbols_list=["BTC"],
                target_relevant=5,
            )

            # Should have found exactly 5 relevant articles
            assert len(relevant_articles) == 5, (
                f"Expected 5 relevant articles, got {len(relevant_articles)}"
            )

            # Should have processed exactly 5 articles (stopped early)
            assert total_processed == 5, (
                f"Expected to process 5 articles, but processed {total_processed}"
            )

            # Verify the articles are the first 5 (most recent)
            expected_titles = [f"Article {i + 1}" for i in range(5)]
            actual_titles = [article["title"] for article in relevant_articles]
            assert actual_titles == expected_titles, (
                f"Expected {expected_titles}, got {actual_titles}"
            )

    def test_cached_articles_are_skipped(self):
        """Test that articles already in cache are properly skipped during collection."""
        # Use a fixed recent date to avoid timing issues
        base_time = datetime(2025, 11, 7, 12, 0, 0, tzinfo=UTC)

        # Create mock entries
        mock_entries = []
        for i in range(5):
            entry = Mock()
            entry.title = f"Cached Article {i + 1}"
            entry.link = f"https://test.com/cached-{i + 1}"
            entry.published = (base_time - timedelta(hours=i)).isoformat()
            entry.published_parsed = time.struct_time(
                (
                    (base_time - timedelta(hours=i)).year,
                    (base_time - timedelta(hours=i)).month,
                    (base_time - timedelta(hours=i)).day,
                    (base_time - timedelta(hours=i)).hour,
                    (base_time - timedelta(hours=i)).minute,
                    (base_time - timedelta(hours=i)).second,
                    -1,
                    -1,
                    -1,
                ),
            )
            mock_entries.append(entry)

        mock_feed = Mock()
        mock_feed.entries = mock_entries

        with (
            patch("news.rss_parser.feedparser.parse", return_value=mock_feed),
            patch("news.rss_parser._parse_rss_entry") as mock_parse,
            patch("news.rss_parser.article_exists_in_cache") as mock_cache_check,
        ):
            # Mock parsing to return RSSEntry objects
            def parse_side_effect(entry, source, class_name, current_time):
                published_time = datetime.fromisoformat(entry.published)

                return RSSEntry(
                    source=source,
                    title=entry.title,
                    link=entry.link,
                    published_time=published_time,
                    published_str=entry.published,
                    class_name=class_name,
                    raw_entry=entry,
                )

            mock_parse.side_effect = parse_side_effect

            # Mock cache check - first 2 are cached, last 3 are not
            def cache_side_effect(link):
                return "cached-1" in link or "cached-2" in link

            mock_cache_check.side_effect = cache_side_effect

            result = _collect_entries_from_feed(
                feed_url="https://test.com/feed",
                source="test",
                class_name="test-class",
                cache_enabled=True,
                current_time=base_time,
            )

            # Should only return 3 entries (last 3 are not cached)
            assert len(result) == 3, f"Expected 3 entries, got {len(result)}"

            # Verify the returned entries are the non-cached ones
            expected_titles = ["Cached Article 3", "Cached Article 4", "Cached Article 5"]
            actual_titles = [entry.title for entry in result]
            assert actual_titles == expected_titles, (
                f"Expected {expected_titles}, got {actual_titles}"
            )

            # Verify cache check was called for all entries
            assert mock_cache_check.call_count == 5, (
                f"Expected 5 cache checks, got {mock_cache_check.call_count}"
            )

    def test_24h_age_filtering(self):
        """Test that articles older than 24 hours are filtered out."""
        # Use a fixed recent date to avoid timing issues
        base_time = datetime(2025, 11, 7, 12, 0, 0, tzinfo=UTC)

        # Create mock entries with varying ages
        mock_entries = []
        for i in range(5):
            entry = Mock()
            entry.title = f"Age Test Article {i + 1}"
            entry.link = f"https://test.com/age-{i + 1}"
            # Article 0: 1 hour old (should be included)
            # Article 1: 12 hours old (should be included)
            # Article 2: 25 hours old (should be excluded)
            # Article 3: 48 hours old (should be excluded)
            # Article 4: 2 hours old (should be included)
            ages_hours = [1, 12, 25, 48, 2]
            published_time = base_time - timedelta(hours=ages_hours[i])
            entry.published = published_time.isoformat()
            entry.published_parsed = time.struct_time(
                (
                    published_time.year,
                    published_time.month,
                    published_time.day,
                    published_time.hour,
                    published_time.minute,
                    published_time.second,
                    -1,
                    -1,
                    -1,
                ),
            )
            mock_entries.append(entry)

        mock_feed = Mock()
        mock_feed.entries = mock_entries

        with (
            patch("news.rss_parser.feedparser.parse", return_value=mock_feed),
            patch("news.rss_parser._parse_rss_entry") as mock_parse,
            patch("news.rss_parser.article_exists_in_cache", return_value=False),
        ):
            # Mock parsing to return RSSEntry objects
            def parse_side_effect(entry, source, class_name, current_time):
                published_time = datetime.fromisoformat(entry.published)

                return RSSEntry(
                    source=source,
                    title=entry.title,
                    link=entry.link,
                    published_time=published_time,
                    published_str=entry.published,
                    class_name=class_name,
                    raw_entry=entry,
                )

            mock_parse.side_effect = parse_side_effect

            result = _collect_entries_from_feed(
                feed_url="https://test.com/feed",
                source="test",
                class_name="test-class",
                cache_enabled=True,
                current_time=base_time,
            )

            # Should only return 3 entries (articles 0, 1, and 4 are within 24h)
            assert len(result) == 3, f"Expected 3 entries within 24h, got {len(result)}"

            # Verify the returned entries are the recent ones
            expected_titles = ["Age Test Article 1", "Age Test Article 2", "Age Test Article 5"]
            actual_titles = [entry.title for entry in result]
            assert actual_titles == expected_titles, (
                f"Expected {expected_titles}, got {actual_titles}"
            )

    def test_symbol_specific_filtering(self):
        """Test that articles are properly filtered by cryptocurrency symbol."""

        # Mock the function to return different results based on symbol
        def mock_get_side_effect(symbol, **kwargs):
            if symbol.upper() == "BTC":
                return [
                    Mock(title="Bitcoin surges to new highs", symbols=["BTC"]),
                    Mock(title="BTC and ETH correlation analysis", symbols=["BTC", "ETH"]),
                ]
            if symbol.upper() == "ETH":
                return [
                    Mock(title="Ethereum network upgrade completed", symbols=["ETH"]),
                    Mock(title="BTC and ETH correlation analysis", symbols=["BTC", "ETH"]),
                ]
            if symbol.upper() == "SOL":
                return [Mock(title="Solana ecosystem grows rapidly", symbols=["SOL"])]
            return []

        with patch.object(
            article_cache, "get_articles_for_symbol", side_effect=mock_get_side_effect,
        ):
            # Test BTC filtering
            btc_articles = article_cache.get_articles_for_symbol("BTC", hours=24)
            assert len(btc_articles) == 2, f"Expected 2 BTC articles, got {len(btc_articles)}"
            btc_titles = [article.title for article in btc_articles]
            expected_btc = ["Bitcoin surges to new highs", "BTC and ETH correlation analysis"]
            assert btc_titles == expected_btc, f"Expected {expected_btc}, got {btc_titles}"

            # Test ETH filtering
            eth_articles = article_cache.get_articles_for_symbol("ETH", hours=24)
            assert len(eth_articles) == 2, f"Expected 2 ETH articles, got {len(eth_articles)}"
            eth_titles = [article.title for article in eth_articles]
            expected_eth = [
                "Ethereum network upgrade completed",
                "BTC and ETH correlation analysis",
            ]
            assert eth_titles == expected_eth, f"Expected {expected_eth}, got {eth_titles}"

            # Test SOL filtering
            sol_articles = article_cache.get_articles_for_symbol("SOL", hours=24)
            assert len(sol_articles) == 1, f"Expected 1 SOL article, got {len(sol_articles)}"
            assert sol_articles[0].title == "Solana ecosystem grows rapidly"

            # Test symbol with no articles
            xyz_articles = article_cache.get_articles_for_symbol("XYZ", hours=24)
            assert len(xyz_articles) == 0, f"Expected 0 XYZ articles, got {len(xyz_articles)}"

    @patch.dict("os.environ", {"CURRENT_REPORT_ARTICLE_LIMIT": "5"})
    def test_current_report_article_limit_configuration(self):
        """Test that CURRENT_REPORT_ARTICLE_LIMIT configuration is properly respected.

        in lazy processing.
        """
        importlib.reload(constants)
        importlib.reload(rss_parser)
        importlib.reload(article_cache)

        # Verify the configuration is loaded
        assert rss_parser.CURRENT_REPORT_ARTICLE_LIMIT == 5

        # Test that fetch_and_cache_articles_for_symbol uses CURRENT_REPORT_ARTICLE_LIMIT
        with (
            patch("news.rss_parser.get_articles_for_symbol") as mock_get_articles,
            patch("news.rss_parser.get_news") as mock_get_news,
        ):
            mock_get_news.return_value = None
            mock_get_articles.return_value = []

            result = fetch_and_cache_articles_for_symbol("BTC", hours=24)

            # Verify get_news was called with CURRENT_REPORT_ARTICLE_LIMIT
            mock_get_news.assert_called_once_with(target_relevant=5)

            # Verify get_articles_for_symbol was called with correct parameters
            mock_get_articles.assert_called_once_with("BTC", 24)

            # Verify return value
            assert result == []

    def test_current_report_article_limit_default(self):
        """Test that CURRENT_REPORT_ARTICLE_LIMIT defaults to 3 when not set."""
        os.environ.pop("CURRENT_REPORT_ARTICLE_LIMIT", None)

        importlib.reload(constants)
        importlib.reload(rss_parser)
        importlib.reload(article_cache)

        # Verify the default value
        assert rss_parser.CURRENT_REPORT_ARTICLE_LIMIT == 3

    def test_shared_cache_integration_lazy_processing(self):
        """Test that lazy processing properly integrates with shared cache for current reports."""
        # Mock articles that would be cached during RSS processing
        mock_cached_articles = [
            Mock(
                title="Bitcoin ETF approval news",
                symbols=["BTC"],
                published_time=datetime.now(UTC),
            ),
            Mock(
                title="Ethereum upgrade completed",
                symbols=["ETH"],
                published_time=datetime.now(UTC),
            ),
            Mock(
                title="Solana network congestion",
                symbols=["SOL"],
                published_time=datetime.now(UTC),
            ),
        ]

        # Test the integration: lazy processing should cache articles that are then
        # available for current reports
        with (
            patch(
                "news.rss_parser.get_articles_for_symbol", return_value=mock_cached_articles,
            ) as mock_get_articles,
            patch("news.rss_parser.get_news") as mock_get_news,
        ):
            mock_get_news.return_value = None  # RSS processing completes without error

            # Simulate current report requesting articles for BTC
            result = fetch_and_cache_articles_for_symbol("BTC", hours=24)

            # Verify that get_news was called (lazy processing triggered)
            mock_get_news.assert_called_once_with(target_relevant=3)  # Default limit

            # Verify that get_articles_for_symbol was called to retrieve from cache
            mock_get_articles.assert_called_once_with("BTC", 24)

            # Verify the result contains the expected cached articles
            assert result == mock_cached_articles
            assert len(result) == 3

            # Verify the articles have the expected symbols
            btc_articles = [article for article in result if "BTC" in article.symbols]
            assert len(btc_articles) == 1
            assert btc_articles[0].title == "Bitcoin ETF approval news"
