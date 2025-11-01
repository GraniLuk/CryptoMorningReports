# News Module Documentation

The news module provides RSS article fetching, caching, symbol detection, and AI-enhanced analysis for cryptocurrency news.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Features](#features)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## Architecture Overview

```
news/
├── rss_parser.py          # RSS feed fetching and parsing
├── article_cache.py       # Article caching and retrieval
├── symbol_detector.py     # Cryptocurrency symbol detection
├── news_agent.py          # AI-powered news analysis
├── cleanup_cache.py       # Manual cache management utility
└── cache/                 # Cached articles (gitignored)
    └── YYYY-MM-DD/        # Date-based directories
        └── *.md           # Markdown files with YAML frontmatter
```

### Data Flow

```
1. RSS Feeds → 2. Article Fetching → 3. Symbol Detection → 4. Cache Storage
                                                                    ↓
5. Report Generation ← 4. Cache Retrieval ← 3. Symbol Filtering ← 
```

## Features

### 1. RSS Feed Fetching

- **6 Active RSS Sources**: decrypt, coindesk, newsBTC, coinJournal, coinpedia, ambcrypto
- **24-hour Filtering**: Only fetches articles from the last 24 hours
- **Full Content Extraction**: Downloads complete article content with HTML parsing
- **Concurrent Fetching**: Fetches multiple feeds simultaneously
- **Error Resilience**: Continues fetching even if individual sources fail

### 2. Article Caching

- **Markdown Format**: Articles saved as markdown with YAML frontmatter
- **Metadata Storage**: source, title, link, published date, fetched date, symbols
- **Date-based Organization**: `cache/YYYY-MM-DD/source-slug.md`
- **Automatic Cleanup**: Articles older than 24 hours automatically removed
- **Disk-based Storage**: Local file system for easy verification

### 3. Symbol Detection

- **Intelligent Matching**: Detects cryptocurrency symbols in article content
- **Multiple Formats**: BTC, Bitcoin, Bitcoin's, BTC/USD, Ethereum-based
- **Confidence Scoring**: Prevents false positives (e.g., "BIT" ≠ Bitcoin)
- **Context Awareness**: Higher confidence for symbols in meaningful context
- **Case Insensitive**: Matches regardless of capitalization

### 4. AI-Enhanced Analysis

- **News Integration**: Automatically includes relevant articles in reports
- **Trading Context**: AI analyzes news alongside technical indicators
- **Sentiment Analysis**: Evaluates news impact on price movements
- **Catalyst Identification**: Highlights news-driven market catalysts
- **Position Sizing**: Adjusts recommendations based on news confidence

### 5. Cache Management

- **Automatic Cleanup**: Runs before each daily report generation
- **Manual Utility**: `cleanup_cache.py` for on-demand management
- **Statistics Tracking**: Monitor cache size, article count, age
- **Dry-run Mode**: Preview cleanup before execution
- **Configurable TTL**: Default 24 hours, adjustable

## Quick Start

### Fetch and Cache Articles

```python
from news.rss_parser import get_news

# Fetch fresh articles from all RSS feeds
articles = get_news()
# Articles are automatically cached to disk

print(f"Fetched {len(articles)} articles")
```

### Retrieve Cached Articles

```python
from news.article_cache import get_articles_for_symbol, get_recent_articles

# Get all BTC articles from last 24 hours
btc_articles = get_articles_for_symbol("BTC", hours=24)

# Get all recent articles
all_articles = get_recent_articles(hours=24)

for article in btc_articles:
    print(f"{article.title} - {article.source}")
    print(f"Symbols: {', '.join(article.symbols)}")
```

### Auto-fetch Fresh Articles

```python
from news.article_cache import fetch_and_cache_articles_for_symbol

# Automatically fetch fresh RSS + return cached articles
btc_articles = fetch_and_cache_articles_for_symbol("BTC", hours=24)
# This ensures cache is up-to-date before retrieving
```

### Manual Cache Cleanup

```bash
# View cache statistics
python news/cleanup_cache.py --stats

# Delete articles older than 24 hours
python news/cleanup_cache.py --hours 24

# Preview what would be deleted (dry-run)
python news/cleanup_cache.py --hours 48 --dry-run

# Delete all articles
python news/cleanup_cache.py --hours 0
```

## API Reference

### article_cache.py

#### `CachedArticle`

Dataclass representing a cached article.

```python
@dataclass
class CachedArticle:
    source: str           # RSS source name
    title: str            # Article title
    link: str             # Original URL
    published: str        # ISO 8601 timestamp
    fetched: str          # ISO 8601 timestamp
    content: str          # Full article content
    symbols: list[str]    # Detected crypto symbols
```

#### `save_article_to_cache(article, date=None)`

Save an article to disk cache.

**Parameters:**
- `article` (CachedArticle): Article to save
- `date` (datetime, optional): Date directory to save to (default: today)

**Returns:** Path to saved file

**Example:**
```python
article = CachedArticle(
    source="coindesk",
    title="Bitcoin Hits $100k",
    link="https://...",
    published=datetime.now(UTC).isoformat(),
    fetched=datetime.now(UTC).isoformat(),
    content="...",
    symbols=["BTC"]
)
save_article_to_cache(article)
```

#### `load_article_from_cache(filepath)`

Load an article from disk cache.

**Parameters:**
- `filepath` (Path): Path to cached article file

**Returns:** CachedArticle or None if loading fails

#### `get_articles_for_symbol(symbol, hours=24)`

Retrieve cached articles mentioning a specific symbol.

**Parameters:**
- `symbol` (str): Cryptocurrency symbol (e.g., "BTC", "ETH")
- `hours` (int): Number of hours to look back (default: 24)

**Returns:** List[CachedArticle] sorted by published date (newest first)

**Example:**
```python
# Get ETH articles from last 48 hours
eth_articles = get_articles_for_symbol("ETH", hours=48)
for article in eth_articles:
    print(article.title)
```

#### `get_recent_articles(hours=24)`

Retrieve all cached articles from the last N hours.

**Parameters:**
- `hours` (int): Number of hours to look back (default: 24)

**Returns:** List[CachedArticle] sorted by published date (newest first)

#### `fetch_and_cache_articles_for_symbol(symbol, hours=24)`

Fetch fresh RSS articles, cache new ones, and return all for a symbol.

**Parameters:**
- `symbol` (str): Cryptocurrency symbol
- `hours` (int): Number of hours to look back (default: 24)

**Returns:** List[CachedArticle] for the specified symbol

**Example:**
```python
# Always get fresh articles
btc_articles = fetch_and_cache_articles_for_symbol("BTC")
```

#### `cleanup_old_articles(max_age_hours=24)`

Delete cached articles older than specified age.

**Parameters:**
- `max_age_hours` (int): Maximum age of articles to keep (default: 24)

**Returns:** int (number of articles deleted)

**Example:**
```python
deleted = cleanup_old_articles(max_age_hours=48)
print(f"Deleted {deleted} old articles")
```

#### `get_cache_statistics()`

Get statistics about the article cache.

**Returns:** dict with keys:
- `total_articles` (int): Number of cached articles
- `total_size_mb` (float): Disk space used in MB
- `oldest_article_hours` (float): Age of oldest article in hours
- `newest_article_hours` (float): Age of newest article in hours
- `cache_path` (str): Path to cache root directory

**Example:**
```python
stats = get_cache_statistics()
print(f"Cache has {stats['total_articles']} articles")
print(f"Using {stats['total_size_mb']} MB")
```

### symbol_detector.py

#### `detect_symbols_in_text(text, symbols)`

Detect cryptocurrency symbols mentioned in text.

**Parameters:**
- `text` (str): Text to search for symbols
- `symbols` (List[Symbol]): List of Symbol objects from database

**Returns:** List[str] of detected symbol names

**Features:**
- Detects symbol names (BTC, ETH)
- Detects full names (Bitcoin, Ethereum)
- Handles possessive forms (Bitcoin's)
- Detects trading pairs (BTC/USD)
- Detects hyphenated forms (Bitcoin-based)
- Confidence scoring prevents false positives
- Context boost for symbols in meaningful sentences

**Example:**
```python
from source_repository import fetch_symbols
from news.symbol_detector import detect_symbols_in_text

symbols = fetch_symbols(conn)
text = "Bitcoin and Ethereum lead the market recovery"
detected = detect_symbols_in_text(text, symbols)
# Returns: ["BTC", "ETH"]
```

### rss_parser.py

#### `get_news()`

Fetch articles from all RSS feeds.

**Returns:** List of article dictionaries

**Behavior:**
- Fetches from 6 RSS sources concurrently
- Filters to last 24 hours
- Downloads full article content
- Detects symbols in content
- Automatically caches articles
- Returns list of articles

### news_agent.py

#### `get_detailed_crypto_analysis_with_news(symbol, ...)`

Generate AI-powered trading analysis with news context.

**Parameters:**
- `symbol` (Symbol): Cryptocurrency to analyze
- Various technical indicators and market data

**Returns:** dict with analysis results

**Features:**
- Integrates news articles with technical analysis
- AI evaluates news impact on price movements
- Generates trading recommendations with news context
- Provides sentiment scoring (1-10 scale)
- Ranks news catalysts by importance

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Article Cache Settings (Optional - defaults shown)
ENABLE_ARTICLE_CACHE=true           # Enable/disable caching
ARTICLE_CACHE_DIR=news/cache        # Cache directory path
ARTICLE_CACHE_MAX_AGE_HOURS=24      # Auto-cleanup threshold
```

### Cache Structure

Articles are stored in this format:

```
news/cache/
  2025-11-01/
    coindesk_bitcoin-hits-100k.md
    decrypt_ethereum-upgrade-complete.md
    ...
  2025-11-02/
    ...
```

### File Format

Each article is stored as markdown with YAML frontmatter:

```markdown
---
source: coindesk
title: Bitcoin Surges Past $100k
link: https://www.coindesk.com/...
published: '2025-11-01T14:30:00+00:00'
fetched: '2025-11-01T15:00:00+00:00'
symbols:
  - BTC
  - ETH
---

Article content goes here...
```

## Testing

### Run All Tests

```bash
# Article cache tests
python news/test_article_cache.py

# Symbol detection tests
python news/test_symbol_detector.py

# Phase 4 integration tests
python news/test_phase4_integration.py

# Cleanup tests
python news/test_cleanup.py

# End-to-end integration tests
python news/test_e2e_integration.py

# RSS feed verification
python news/test_rss_feeds.py
```

### Test Coverage

- ✅ Article caching (save, load, retrieve)
- ✅ Symbol detection (confidence scoring, false positives)
- ✅ Cache cleanup (age-based deletion)
- ✅ Statistics calculation
- ✅ Error handling (corrupted files, missing files)
- ✅ Integration with reports
- ✅ RSS fetching
- ✅ Full end-to-end workflow

## Troubleshooting

### Common Issues

#### Cache Not Updating

**Problem:** Articles not appearing in reports

**Solutions:**
1. Check cache directory exists: `news/cache/`
2. Verify RSS feeds are accessible
3. Check last fetch time in logs
4. Run manual fetch: `python -c "from news.rss_parser import get_news; get_news()"`

**Debug:**
```python
from news.article_cache import get_cache_statistics
stats = get_cache_statistics()
print(f"Total articles: {stats['total_articles']}")
print(f"Newest: {stats['newest_article_hours']} hours ago")
```

#### Symbol Not Detected

**Problem:** Articles not tagged with expected symbols

**Solutions:**
1. Check symbol exists in database
2. Verify symbol appears in article title or content
3. Check confidence threshold (0.6 minimum)
4. Test detection manually:

```python
from source_repository import fetch_symbols
from news.symbol_detector import detect_symbols_in_text

symbols = fetch_symbols(conn)
text = "Your article text here"
detected = detect_symbols_in_text(text, symbols)
print(f"Detected: {detected}")
```

#### Cleanup Not Working

**Problem:** Old articles not being deleted

**Solutions:**
1. Check cleanup runs in daily_report.py
2. Verify article published dates are in ISO format
3. Run manual cleanup: `python news/cleanup_cache.py --hours 24`
4. Check logs for cleanup errors

**Debug:**
```python
from news.article_cache import cleanup_old_articles
deleted = cleanup_old_articles(max_age_hours=0)  # Delete all
print(f"Deleted: {deleted} articles")
```

#### Cache Size Too Large

**Problem:** Cache using too much disk space

**Solutions:**
1. Reduce max_age_hours: `cleanup_old_articles(max_age_hours=12)`
2. Run cleanup more frequently
3. Check for duplicate articles
4. Monitor with statistics:

```python
stats = get_cache_statistics()
if stats['total_size_mb'] > 100:  # 100 MB threshold
    cleanup_old_articles(max_age_hours=6)
```

#### RSS Feed Failures

**Problem:** Some feeds not returning articles

**Solutions:**
1. Run feed verification: `python news/test_rss_feeds.py`
2. Check network connectivity
3. Verify feed URLs haven't changed
4. Check for rate limiting (wait 1 hour and retry)
5. Review logs for specific error messages

**Note:** The system is designed to continue working even if some feeds fail.

#### Windows Emoji Display Issues

**Problem:** Test output shows garbled emojis

**Solution:**
```powershell
# Set UTF-8 encoding before running tests
$env:PYTHONIOENCODING="utf-8"
python news/test_e2e_integration.py
```

### Logging

All news module operations are logged to the application logger:

```python
from infra.telegram_logging_handler import app_logger

# Logs appear in console and Telegram (if configured)
# Look for these prefixes:
# - "🧹 Cleaning up old cached articles..."
# - "✓ Cleanup complete: X articles deleted"
# - "📡 Fetching articles from RSS feeds..."
# - "⚠️ Article cache cleanup failed: ..."
```

### Performance

- **RSS Fetch Time**: 5-15 seconds for 6 feeds (concurrent)
- **Cache Read Time**: <100ms for 100 articles
- **Symbol Detection**: <50ms per article
- **Cleanup Time**: <1 second for 100 articles

### Limitations

1. **24-hour TTL**: Articles older than 24 hours are deleted
2. **No Full-text Search**: Use symbol-based filtering only
3. **Local Storage**: Not suitable for distributed systems
4. **RSS-dependent**: Quality depends on feed availability
5. **Symbol Detection**: May miss uncommon symbol variations

## Contributing

When modifying the news module:

1. Update tests for new features
2. Maintain backward compatibility
3. Follow existing code style (ruff + pyright)
4. Add docstrings to new functions
5. Update this README for API changes

## Related Documentation

- [Feature Plan](../plan/feature-rss-article-caching-1.md) - Implementation plan
- [Local Development](../LOCAL_DEVELOPMENT.md) - Setup guide
- [Main README](../readme.md) - Project overview
