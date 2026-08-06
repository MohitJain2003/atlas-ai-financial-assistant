"""
Market Data Services - Real-time financial data via yfinance, Yahoo Finance Chart API, and Finnhub.
Includes: stock prices, company profiles, comparisons, market overview, earnings data, stock search.
All data is REAL — no mocks, no dummy values.
"""
import logging
import asyncio
from typing import Dict, Any, List
import yfinance as yf
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class MarketDataService:
    """Service for fetching real-time financial market data."""

    def __init__(self):
        self.finnhub_key = settings.FINNHUB_API_KEY

    async def get_stock_price(self, ticker: str) -> Dict[str, Any]:
        """Fetch current stock price, changes, and basic metrics — 100% real data."""
        ticker = ticker.upper().strip()

        # 1. Yahoo Finance Chart API (fast, no rate limits, real-time)
        data = await self._fetch_yf_chart_price(ticker)
        if data:
            return data

        # 2. Stooq CSV API (free, reliable backup)
        data = await self._fetch_stooq_price(ticker)
        if data:
            return data

        # 3. yfinance library
        try:
            data = await asyncio.to_thread(self._fetch_yf_price, ticker)
            if data:
                return data
        except Exception as e:
            logger.warning(f"yfinance failed for {ticker}: {e}")

        # 4. Finnhub
        if self.finnhub_key:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(
                        f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={self.finnhub_key}"
                    )
                    if resp.status_code == 200:
                        q = resp.json()
                        if q.get("c"):
                            return {
                                "ticker": ticker,
                                "company_name": ticker,
                                "price": round(q["c"], 2),
                                "change": round(q["d"], 2),
                                "percent_change": round(q["dp"], 2),
                                "high": round(q["h"], 2) if q.get("h") else None,
                                "low": round(q["l"], 2) if q.get("l") else None,
                                "open": round(q["o"], 2) if q.get("o") else None,
                                "previous_close": round(q["pc"], 2) if q.get("pc") else None,
                                "source": "Finnhub",
                            }
            except Exception as e:
                logger.error(f"Finnhub quote error for {ticker}: {e}")

        return {"error": f"Could not retrieve real market data for '{ticker}'. The ticker may be invalid."}

    async def _fetch_yf_chart_price(self, ticker: str) -> Dict[str, Any]:
        """Fetch real-time price from Yahoo Finance Chart API."""
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        try:
            async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    result = resp.json().get("chart", {}).get("result")
                    if result:
                        meta = result[0].get("meta", {})
                        price = meta.get("regularMarketPrice")
                        prev_close = meta.get("chartPreviousClose") or price
                        if price is not None:
                            change = price - prev_close
                            pct_change = (change / prev_close) * 100 if prev_close else 0.0
                            return {
                                "ticker": ticker,
                                "company_name": meta.get("shortName") or meta.get("symbol") or ticker,
                                "price": round(price, 2),
                                "change": round(change, 2),
                                "percent_change": round(pct_change, 2),
                                "previous_close": round(prev_close, 2),
                                "currency": meta.get("currency", "USD"),
                                "market_state": meta.get("marketState", ""),
                                "source": "Yahoo Finance Live",
                            }
        except Exception as e:
            logger.warning(f"Yahoo chart fetch failed for {ticker}: {e}")
        return None

    async def _fetch_stooq_price(self, ticker: str) -> Dict[str, Any]:
        """Fetch stock price from Stooq CSV API (free, no key needed)."""
        stooq_symbol = f"{ticker.lower()}.us"
        url = f"https://stooq.com/q/l/?s={stooq_symbol}&f=sdgl1ohc&e=csv"
        try:
            async with httpx.AsyncClient(timeout=5.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    lines = resp.text.strip().splitlines()
                    if len(lines) >= 2:
                        cols = [c.strip() for c in lines[1].split(",")]
                        if len(cols) >= 7 and cols[6] != "N/A":
                            close = float(cols[6])
                            open_p = float(cols[3]) if cols[3] != "N/A" else close
                            high = float(cols[4]) if cols[4] != "N/A" else close
                            low = float(cols[5]) if cols[5] != "N/A" else close
                            change = round(close - open_p, 2)
                            pct_change = round((change / open_p) * 100, 2) if open_p else 0.0
                            return {
                                "ticker": ticker,
                                "company_name": ticker,
                                "price": round(close, 2),
                                "change": change,
                                "percent_change": pct_change,
                                "open": round(open_p, 2),
                                "high": round(high, 2),
                                "low": round(low, 2),
                                "previous_close": round(open_p, 2),
                                "currency": "USD",
                                "source": "Stooq Financial",
                            }
        except Exception as e:
            logger.warning(f"Stooq fetch failed for {ticker}: {e}")
        return None

    def _fetch_yf_price(self, ticker: str) -> Dict[str, Any]:
        """Fetch via yfinance library (synchronous, run in thread)."""
        import requests
        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        t = yf.Ticker(ticker, session=session)
        try:
            hist = t.history(period="2d")
            if not hist.empty and len(hist) >= 1:
                price = float(hist["Close"].iloc[-1])
                prev_close = float(hist["Close"].iloc[-2]) if len(hist) > 1 else price
                change = price - prev_close
                pct = (change / prev_close) * 100 if prev_close else 0.0
                return {
                    "ticker": ticker,
                    "company_name": ticker,
                    "price": round(price, 2),
                    "change": round(change, 2),
                    "percent_change": round(pct, 2),
                    "previous_close": round(prev_close, 2),
                    "currency": "USD",
                    "source": "Yahoo Finance",
                }
        except Exception as e:
            logger.warning(f"yfinance history failed for {ticker}: {e}")
        return None

    async def get_company_profile(self, ticker: str) -> Dict[str, Any]:
        """Fetch full company profile with fundamentals via yfinance."""
        ticker = ticker.upper().strip()
        try:
            profile = await asyncio.to_thread(self._fetch_yf_profile, ticker)
            if profile:
                return profile
        except Exception as e:
            logger.error(f"Company profile failed for {ticker}: {e}")
        return {"error": f"Company profile unavailable for '{ticker}'."}

    def _fetch_yf_profile(self, ticker: str) -> Dict[str, Any]:
        t = yf.Ticker(ticker)
        info = t.info
        if not info or "shortName" not in info:
            return None
        return {
            "ticker": ticker,
            "name": info.get("longName") or info.get("shortName"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "description": (info.get("longBusinessSummary") or "")[:600],
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "peg_ratio": info.get("pegRatio"),
            "dividend_yield": info.get("dividendYield"),
            "eps": info.get("trailingEps"),
            "revenue": info.get("totalRevenue"),
            "profit_margin": info.get("profitMargins"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "target_price": info.get("targetMeanPrice"),
            "recommendation": info.get("recommendationKey"),
            "employees": info.get("fullTimeEmployees"),
            "country": info.get("country"),
            "website": info.get("website"),
        }

    async def get_earnings(self, ticker: str) -> Dict[str, Any]:
        """Fetch earnings data: upcoming earnings date + historical EPS actuals vs estimates."""
        ticker = ticker.upper().strip()
        try:
            result = await asyncio.to_thread(self._fetch_yf_earnings, ticker)
            if result:
                return result
        except Exception as e:
            logger.error(f"Earnings fetch failed for {ticker}: {e}")
        return {"error": f"Earnings data unavailable for '{ticker}'."}

    def _fetch_yf_earnings(self, ticker: str) -> Dict[str, Any]:
        t = yf.Ticker(ticker)
        info = t.info

        # Upcoming earnings date
        calendar = None
        try:
            cal = t.calendar
            if cal is not None and not cal.empty:
                earnings_date = str(cal.iloc[0].get("Earnings Date", "")) if hasattr(cal, 'iloc') else str(cal.get("Earnings Date", ""))
                calendar = {"next_earnings_date": earnings_date}
        except Exception:
            pass

        # Historical earnings
        earnings_history = []
        try:
            hist = t.earnings_history
            if hist is not None and not hist.empty:
                for _, row in hist.head(4).iterrows():
                    earnings_history.append({
                        "period": str(row.get("Period", "")),
                        "eps_estimate": row.get("EPS Estimate"),
                        "eps_actual": row.get("Reported EPS"),
                        "surprise_pct": row.get("Surprise(%)"),
                    })
        except Exception:
            pass

        return {
            "ticker": ticker,
            "company_name": info.get("shortName") or ticker,
            "calendar": calendar,
            "earnings_history": earnings_history,
            "source": "Yahoo Finance",
        }

    async def compare_companies(self, tickers: List[str]) -> Dict[str, Any]:
        """Compare multiple companies on key financial metrics."""
        results = []
        for ticker in tickers[:5]:
            price_data = await self.get_stock_price(ticker)
            profile_data = await self.get_company_profile(ticker)
            if "error" not in price_data:
                combined = {**price_data}
                if "error" not in profile_data:
                    combined.update({
                        "name": profile_data.get("name"),
                        "sector": profile_data.get("sector"),
                        "pe_ratio": profile_data.get("pe_ratio"),
                        "forward_pe": profile_data.get("forward_pe"),
                        "market_cap": profile_data.get("market_cap"),
                        "profit_margin": profile_data.get("profit_margin"),
                        "revenue": profile_data.get("revenue"),
                        "recommendation": profile_data.get("recommendation"),
                        "52w_high": profile_data.get("52w_high"),
                        "52w_low": profile_data.get("52w_low"),
                    })
                results.append(combined)
        return {"comparison": results}

    async def search_stock(self, query: str) -> Dict[str, Any]:
        """Search for stock ticker by company name via Yahoo Finance search."""
        try:
            async with httpx.AsyncClient(
                timeout=5.0,
                headers={"User-Agent": "Mozilla/5.0"},
            ) as client:
                resp = await client.get(
                    f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=5&newsCount=0"
                )
                if resp.status_code == 200:
                    quotes = resp.json().get("quotes", [])
                    results = [
                        {
                            "symbol": q["symbol"],
                            "name": q.get("shortname") or q.get("longname"),
                            "exchange": q.get("exchDisp"),
                            "type": q.get("quoteType"),
                        }
                        for q in quotes
                        if "symbol" in q
                    ]
                    return {"results": results[:5]}
        except Exception as e:
            logger.error(f"Stock search failed for '{query}': {e}")
        return {"results": []}

    async def get_market_overview(self) -> Dict[str, Any]:
        """Fetch real-time status of major market indices."""
        indices = {
            "S&P 500": "^GSPC",
            "NASDAQ": "^IXIC",
            "Dow Jones": "^DJI",
            "Russell 2000": "^RUT",
        }
        overview = {}
        for name, ticker in indices.items():
            data = await self.get_stock_price(ticker)
            if "error" not in data:
                overview[name] = {
                    "price": data.get("price"),
                    "change": data.get("change"),
                    "percent_change": data.get("percent_change"),
                }
        return overview
