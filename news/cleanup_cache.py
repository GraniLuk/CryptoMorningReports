"""Manual article cache cleanup utility.

This script provides manual cache management with options to:
- Clean up articles older than a specified age
- View cache statistics
- Perform dry-run to preview cleanup

Usage:
    python news/cleanup_cache.py --hours 24        # Clean articles older than 24 hours
    python news/cleanup_cache.py --stats           # Show cache statistics only
    python news/cleanup_cache.py --hours 48 --dry-run  # Preview what would be deleted
"""

import argparse

from news.article_cache import cleanup_old_articles, get_cache_statistics


def display_cache_statistics() -> dict:
    """Display current cache statistics.

    Returns:
        Dictionary with cache statistics
    """
    print("\n=== Article Cache Statistics ===\n")

    stats = get_cache_statistics()

    print(f"📊 Total Articles: {stats['total_articles']}")
    print(f"💾 Total Size: {stats['total_size_mb']} MB")
    print(f"🕒 Oldest Article: {stats['oldest_article_hours']:.1f} hours ago")
    print(f"🆕 Newest Article: {stats['newest_article_hours']:.1f} hours ago")
    print(f"📂 Cache Path: {stats['cache_path']}")
    print()

    return stats


def cleanup_cache(max_age_hours: int, dry_run: bool = False) -> int:
    """Clean up old articles from cache.

    Args:
        max_age_hours: Maximum age of articles to keep
        dry_run: If True, preview what would be deleted without deleting

    Returns:
        Number of articles that would be (or were) deleted
    """
    print(f"\n{'🔍 DRY RUN - ' if dry_run else ''}Cleanup Configuration:")
    print(f"  Max Age: {max_age_hours} hours")
    print(f"  Action: {'Preview only' if dry_run else 'Delete old articles'}\n")

    if dry_run:
        # Show what would be deleted
        print("⚠️  This is a DRY RUN - no files will be deleted\n")

        # Get stats before
        stats_before = get_cache_statistics()
        print(f"Current cache: {stats_before['total_articles']} articles")

        # Calculate what would be deleted by checking ages
        from datetime import UTC, datetime, timedelta

        from news.article_cache import (
            get_cache_directory,
            load_article_from_cache,
        )

        would_delete = 0
        cutoff_time = datetime.now(tz=UTC) - timedelta(hours=max_age_hours)
        days_to_check = (max_age_hours // 24) + 3

        for days_ago in range(days_to_check):
            check_date = datetime.now(tz=UTC) - timedelta(days=days_ago)
            cache_dir = get_cache_directory(check_date)

            if not cache_dir.exists():
                continue

            for markdown_file in cache_dir.glob("*.md"):
                try:
                    article = load_article_from_cache(markdown_file)
                    if article is None:
                        continue

                    published_dt = datetime.fromisoformat(article.published)
                    if published_dt < cutoff_time:
                        would_delete += 1
                        age_hours = (datetime.now(tz=UTC) - published_dt).total_seconds() / 3600
                        print(
                            f"  ❌ Would delete: {article.title[:50]}... "
                            f"({age_hours:.1f}h old)",
                        )

                except Exception:  # noqa: BLE001, S110
                    pass

        print(f"\nWould delete: {would_delete} articles")
        total_articles = int(stats_before["total_articles"])
        print(f"Would remain: {total_articles - would_delete} articles")

        return would_delete

    # Actually perform cleanup
    print("🧹 Starting cleanup...")
    deleted_count = cleanup_old_articles(max_age_hours)

    print(f"✅ Cleanup complete: {deleted_count} articles deleted\n")

    return deleted_count


def main() -> None:
    """Run the cache cleanup utility."""
    parser = argparse.ArgumentParser(
        description="Manage article cache cleanup and statistics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --stats                    # Show cache statistics
  %(prog)s --hours 24                 # Delete articles older than 24 hours
  %(prog)s --hours 48 --dry-run       # Preview deletion of 48h+ old articles
  %(prog)s --hours 0                  # Delete all articles (use with caution!)
        """,
    )

    parser.add_argument(
        "--hours",
        type=int,
        metavar="N",
        help="Delete articles older than N hours",
    )

    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show cache statistics only",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be deleted without actually deleting",
    )

    args = parser.parse_args()

    # Show statistics if requested or if no cleanup specified
    if args.stats or args.hours is None:
        display_cache_statistics()

    # Perform cleanup if hours specified
    if args.hours is not None:
        cleanup_cache(args.hours, dry_run=args.dry_run)

        # Show statistics after cleanup
        print("\n=== Cache Statistics After Cleanup ===\n")
        display_cache_statistics()


if __name__ == "__main__":
    main()
