"""Base abstract class for AI clients."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    import pyodbc

    from infra.sql_connection import SQLiteConnectionWrapper
    from source_repository import Symbol


class AIClient(ABC):
    """Abstract base class for AI client implementations."""

    @abstractmethod
    def get_detailed_crypto_analysis_with_news(
        self,
        indicators_message: str,
        news_feeded: str,
        conn: "pyodbc.Connection | SQLiteConnectionWrapper | None" = None,
    ) -> tuple[str, str]:
        """Get detailed crypto analysis with news context.

        Args:
            indicators_message (str): Indicators message for analysis
            news_feeded (str): News articles to analyze
            conn (object, optional): Database connection object

        Returns:
            tuple[str, str]: (Analysis result or error message, model_used)

        """

    @abstractmethod
    def highlight_articles(self, user_crypto_list: list["Symbol"], news_feeded: str) -> str:
        """Highlight relevant articles based on user crypto list.

        Args:
            user_crypto_list (list): List of user crypto symbols
            news_feeded (str): News articles to analyze

        Returns:
            str: Highlighted articles or error message

        """
