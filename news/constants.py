"""Constants for the news module.

This module contains shared constants used across the news package,
extracted here to avoid circular import dependencies.
"""

import os


# Number of relevant articles to fetch from RSS feeds for general news reports
NEWS_ARTICLE_LIMIT = int(os.getenv("NEWS_ARTICLE_LIMIT", "10"))

# Number of relevant articles to fetch for current market reports
# (uses a lower limit since current reports focus on latest/most relevant news)
CURRENT_REPORT_ARTICLE_LIMIT = int(os.getenv("CURRENT_REPORT_ARTICLE_LIMIT", "3"))
