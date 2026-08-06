"""
News Service - Fetches real financial news via Finnhub + free fallback via Yahoo Finance RSS.
"""
import logging
import httpx
from typing import Dict, Any, List
from app.config import settings

logger = logging.getLogger(__name__)


class NewsService:
    """Service to retrieve financial news."""

    def __init__(self):
        self.finnhub_key = settings.FINNHUB_API_KEY

    async def get_market_news(self, category: str = "general", limit: int = 5) -> List[Dict[str, Any]]:
        """Fetch general financial market news. Uses Finnhub with Yahoo RSS fallback."""
        # Try Finnhub first
        if self.finnhub_key:
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    url = f"https://finnhub.io/api/v1/news?category={category}&token={self.finnhub_key}"
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        news = resp.json()
                        if news:
                            return [
                                {
                                    "headline": item.get("headline"),
                                    "summary": item.get("summary"),
                                    "source": item.get("source"),
                                    "url": item.get("url"),
                                    "datetime": item.get("datetime"),
                                }
                                for item in news[:limit]
                            ]
            except Exception as e:
                logger.warning(f"Finnhub news failed: {e}. Trying RSS fallback...")

        # Free fallback: Yahoo Finance RSS
        return await self._fetch_yahoo_rss_news(limit)

    async def get_company_news(self, ticker: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetch news for a specific stock ticker. Uses Finnhub with Yahoo RSS fallback."""
        import datetime
        today = datetime.date.today()
        from_date = (today - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        to_date = today.strftime("%Y-%m-%d")

        if self.finnhub_key:
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    url = (
                        f"https://finnhub.io/api/v1/company-news?"
                        f"symbol={ticker.upper()}&from={from_date}&to={to_date}&token={self.finnhub_key}"
                    )
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        news = resp.json()
                        if news:
                            return [
                                {
                                    "headline": item.get("headline"),
                                    "summary": item.get("summary"),
                                    "source": item.get("source"),
                                    "url": item.get("url"),
                                    "datetime": item.get("datetime"),
                                }
                                for item in news[:limit]
                            ]
            except Exception as e:
                logger.warning(f"Finnhub company news failed for {ticker}: {e}. Trying RSS fallback...")

        # Free fallback: Yahoo Finance RSS for this ticker
        return await self._fetch_yahoo_rss_news(limit, ticker=ticker)

    async def _fetch_yahoo_rss_news(self, limit: int = 5, ticker: str = None) -> List[Dict[str, Any]]:
        """Fetch news from Yahoo Finance RSS feed — completely free, no API key needed."""
        try:
            if ticker:
                url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker.upper()}&region=US&lang=en-US"
            else:
                url = "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC,^IXIC&region=US&lang=en-US"

            async with httpx.AsyncClient(
                timeout=8.0,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                follow_redirects=True,
            ) as client:
                resp = await client.get(url)

            if resp.status_code == 200:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(resp.text)
                items = root.findall(".//item")
                articles = []
                for item in items[:limit]:
                    title = item.findtext("title") or ""
                    description = item.findtext("description") or ""
                    link = item.findtext("link") or ""
                    pub_date = item.findtext("pubDate") or ""
                    articles.append({
                        "headline": title,
                        "summary": description[:300] if description else title,
                        "source": "Yahoo Finance",
                        "url": link,
                        "datetime": pub_date,
                    })
                if articles:
                    return articles

        except Exception as e:
            logger.error(f"Yahoo Finance RSS fallback failed: {e}")

        return [{"headline": "Financial news temporarily unavailable.", "summary": "", "source": "", "url": "", "datetime": ""}]
