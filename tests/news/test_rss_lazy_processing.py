"""Unit tests for RSS lazy processing functionality."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

from news.rss_parser import RSSEntry, _is_entry_processable, _parse_rss_entry


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
        assert isinstance(result, RSSEntry)
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
        from news.rss_parser import _collect_all_rss_entries

        # Mock feedparser (not used in this test since we mock _collect_entries_from_feed)
        mock_feedparser.parse.return_value = Mock()

        # Mock _collect_entries_from_feed to return entries for each feed
        current_time = datetime.now(UTC)

        # Create mock entries with different published times
        old_entry = RSSEntry(
            source="coindesk",
            title="Old Article",
            link="https://coindesk.com/old",
            published_time=current_time - timedelta(hours=2),
            published_str="old",
            class_name="test",
            raw_entry=Mock(),
        )

        new_entry = RSSEntry(
            source="decrypt",
            title="New Article",
            link="https://decrypt.co/new",
            published_time=current_time - timedelta(minutes=30),
            published_str="new",
            class_name="test",
            raw_entry=Mock(),
        )

        mock_collect_feed.side_effect = [
            [old_entry],  # coindesk
            [new_entry],  # decrypt
            [],  # newsBTC
            [],  # coinJournal
            [],  # coinpedia
            [],  # ambcrypto
        ]

        result = _collect_all_rss_entries(
            cache_enabled=True,
            current_time=current_time,
        )

        # Should have collected 2 entries
        assert len(result) == 2
        # Should be sorted by published_time descending (newest first)
        assert result[0].title == "New Article"  # newer
        assert result[1].title == "Old Article"  # older

        # Verify logger was called with stats
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args[0][0]
        assert "Collected 2 RSS entries from 6 feeds" in log_call

    @patch("news.rss_parser.feedparser")
    @patch("news.rss_parser._collect_entries_from_feed")
    def test_collect_all_rss_entries_empty_feeds(self, mock_collect_feed, mock_feedparser):
        """Test collection when all feeds return empty results."""
        from news.rss_parser import _collect_all_rss_entries

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
    def test_collect_entries_from_feed_success(self, mock_logger, mock_is_processable, mock_parse_entry, mock_feedparser):
        """Test successful collection from a single feed."""
        from news.rss_parser import _collect_entries_from_feed

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
        from news.rss_parser import _collect_entries_from_feed

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
