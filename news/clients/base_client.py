"""Base abstract class for AI clients."""

from abc import ABC, abstractmethod


class AIClient(ABC):
    """Abstract base class for AI client implementations."""

    @abstractmethod
    def get_detailed_crypto_analysis_with_news(
        self, indicators_message, news_feeded, conn=None
    ) -> str:
        """
        Get detailed crypto analysis with news context.
        
        Args:
            indicators_message (str): Indicators message for analysis
            news_feeded (str): News articles to analyze
            conn (object, optional): Database connection object
            
        Returns:
            str: Analysis result or error message
        """
        pass

    @abstractmethod
    def highlight_articles(self, user_crypto_list, news_feeded) -> str:
        """
        Highlight relevant articles based on user crypto list.
        
        Args:
            user_crypto_list (list): List of user crypto symbols
            news_feeded (str): News articles to analyze
            
        Returns:
            str: Highlighted articles or error message
        """
        pass
