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
