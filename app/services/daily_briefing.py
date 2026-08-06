"""
Daily Briefing Service - Generator for morning and evening personalized financial summaries.
"""
import logging
from app.database.models import User
from app.services.market_data import MarketDataService
from app.services.news import NewsService
from app.ai.prompts import BRIEFING_PROMPT
from app.ai.models import model_chain

logger = logging.getLogger(__name__)


class DailyBriefingService:
    """Generates personalized daily intelligence briefings."""

    def __init__(self):
        self.market_service = MarketDataService()
        self.news_service = NewsService()

    async def generate_morning_briefing(self, user: User) -> str:
        """Create a morning market briefing tailored to user watchlist & interests."""

        # Fetch market overview
        market_data = await self.market_service.get_market_overview()

        # Fetch watchlist stock updates
        watchlist_data = {}
        if user.watchlist:
            for ticker in user.watchlist[:5]:
                data = await self.market_service.get_stock_price(ticker)
                if "error" not in data:
                    watchlist_data[ticker] = {
                        "price": data.get("price"),
                        "change": data.get("change"),
                        "pct_change": data.get("percent_change")
                    }

        # Fetch relevant news
        news_items = await self.news_service.get_market_news(category="general", limit=3)

        # Format prompt
        prompt = BRIEFING_PROMPT.format(
            user_name=user.first_name or "there",
            role=user.role or "Finance Professional",
            interests=", ".join(user.interests) if user.interests else "General Finance",
            watchlist=", ".join(user.watchlist) if user.watchlist else "S&P 500",
            sectors=", ".join(user.sectors) if user.sectors else "Technology",
            detail_level=user.preferred_detail_level or "concise",
            market_data=str(market_data),
            watchlist_data=str(watchlist_data),
            news_data=str(news_items),
        )

        return await model_chain.generate(
            system_prompt=prompt,
            user_message="Generate my morning briefing now."
        )
