"""
Finnhub Extended Services — Analyst ratings, insider transactions, economic calendar.
All data sourced directly from Finnhub's official API.
"""
import logging
import httpx
from typing import Dict, Any, List
from datetime import date, timedelta
from app.config import settings

logger = logging.getLogger(__name__)


class FinnhubService:
    """Extended Finnhub data: analyst ratings, insiders, economic events."""

    def __init__(self):
        self.key = settings.FINNHUB_API_KEY
        self.base = "https://finnhub.io/api/v1"

    async def get_analyst_ratings(self, ticker: str) -> Dict[str, Any]:
        """Fetch analyst consensus, price target, and recent upgrades/downgrades."""
        if not self.key:
            return {"error": "Finnhub API key not configured."}
        ticker = ticker.upper().strip()
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                # Recommendation trends
                rec_resp = await client.get(
                    f"{self.base}/stock/recommendation?symbol={ticker}&token={self.key}"
                )
                # Price target
                pt_resp = await client.get(
                    f"{self.base}/stock/price-target?symbol={ticker}&token={self.key}"
                )
                # Recent upgrade/downgrade
                ud_resp = await client.get(
                    f"{self.base}/stock/upgrade-downgrade?symbol={ticker}&token={self.key}"
                )

                result = {"ticker": ticker}

                if rec_resp.status_code == 200:
                    recs = rec_resp.json()
                    if recs:
                        latest = recs[0]
                        result["recommendation"] = {
                            "period": latest.get("period"),
                            "strong_buy": latest.get("strongBuy"),
                            "buy": latest.get("buy"),
                            "hold": latest.get("hold"),
                            "sell": latest.get("sell"),
                            "strong_sell": latest.get("strongSell"),
                        }

                if pt_resp.status_code == 200:
                    pt = pt_resp.json()
                    result["price_target"] = {
                        "target_high": pt.get("targetHigh"),
                        "target_low": pt.get("targetLow"),
                        "target_mean": pt.get("targetMean"),
                        "target_median": pt.get("targetMedian"),
                        "last_updated": pt.get("lastUpdated"),
                    }

                if ud_resp.status_code == 200:
                    upgrades = ud_resp.json()
                    result["recent_rating_changes"] = [
                        {
                            "date": u.get("gradeDate"),
                            "firm": u.get("company"),
                            "from_grade": u.get("fromGrade"),
                            "to_grade": u.get("toGrade"),
                            "action": u.get("action"),
                        }
                        for u in (upgrades[:5] if upgrades else [])
                    ]

                result["source"] = "Finnhub"
                return result

        except Exception as e:
            logger.error(f"Analyst ratings error for {ticker}: {e}")
        return {"error": f"Could not fetch analyst ratings for {ticker}."}

    async def get_insider_transactions(self, ticker: str) -> Dict[str, Any]:
        """Fetch recent insider buying and selling activity."""
        if not self.key:
            return {"error": "Finnhub API key not configured."}
        ticker = ticker.upper().strip()
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    f"{self.base}/stock/insider-transactions?symbol={ticker}&token={self.key}"
                )
                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                    transactions = [
                        {
                            "name": t.get("name"),
                            "share": t.get("share"),
                            "change": t.get("change"),
                            "transaction_date": t.get("transactionDate"),
                            "transaction_code": t.get("transactionCode"),
                            "transaction_price": t.get("transactionPrice"),
                        }
                        for t in (data[:8] if data else [])
                    ]
                    return {
                        "ticker": ticker,
                        "transactions": transactions,
                        "source": "Finnhub SEC Form 4",
                    }
        except Exception as e:
            logger.error(f"Insider transactions error for {ticker}: {e}")
        return {"error": f"Could not fetch insider transactions for {ticker}."}

    async def get_economic_calendar(self) -> Dict[str, Any]:
        """Fetch upcoming economic events: FOMC, CPI, jobs report, GDP, etc."""
        if not self.key:
            return {"error": "Finnhub API key not configured."}
        try:
            today = date.today()
            to_date = today + timedelta(days=14)
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    f"{self.base}/calendar/economic?token={self.key}"
                )
                if resp.status_code == 200:
                    events = resp.json().get("economicCalendar", [])
                    upcoming = [
                        {
                            "event": e.get("event"),
                            "date": e.get("time"),
                            "country": e.get("country"),
                            "impact": e.get("impact"),
                            "actual": e.get("actual"),
                            "estimate": e.get("estimate"),
                            "previous": e.get("prev"),
                        }
                        for e in (events[:15] if events else [])
                        if e.get("impact") in ("high", "medium")
                    ]
                    return {"events": upcoming, "source": "Finnhub Economic Calendar"}
        except Exception as e:
            logger.error(f"Economic calendar error: {e}")
        return {"error": "Could not fetch economic calendar."}

    async def get_earnings_calendar(self, ticker: str = None) -> Dict[str, Any]:
        """Fetch upcoming earnings releases for a specific stock or market-wide."""
        if not self.key:
            return {"error": "Finnhub API key not configured."}
        try:
            today = date.today()
            to_date = today + timedelta(days=30)
            url = f"{self.base}/calendar/earnings?from={today}&to={to_date}&token={self.key}"
            if ticker:
                url += f"&symbol={ticker.upper()}"

            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    earnings = resp.json().get("earningsCalendar", [])
                    results = [
                        {
                            "ticker": e.get("symbol"),
                            "date": e.get("date"),
                            "eps_estimate": e.get("epsEstimate"),
                            "revenue_estimate": e.get("revenueEstimate"),
                            "quarter": e.get("quarter"),
                            "year": e.get("year"),
                        }
                        for e in (earnings[:20] if earnings else [])
                    ]
                    return {"earnings_calendar": results, "source": "Finnhub"}
        except Exception as e:
            logger.error(f"Earnings calendar error: {e}")
        return {"error": "Could not fetch earnings calendar."}
