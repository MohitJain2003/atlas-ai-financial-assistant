"""
AI Engine - Main orchestrator: tool calling, conversation memory, onboarding, and personalization.
Handles: stock data, news, SEC filings, analyst ratings, insider data, economic events,
         Google Calendar, Gmail, Google Sheets, price alerts, earnings, and more.
"""
import logging
import json
import re
from typing import Optional

from app.ai.models import model_chain
from app.ai.prompts import SYSTEM_PROMPT, ONBOARDING_PROMPT
from app.ai.memory import ConversationMemory
from app.database.models import User
from app.database.repositories import UserRepository, AlertRepository

logger = logging.getLogger(__name__)

# Lazy-loaded services
_market_service = None
_news_service = None
_sec_service = None
_finnhub_ext = None
_calendar_service = None
_gmail_service = None


def _get_services():
    global _market_service, _news_service, _sec_service, _finnhub_ext
    global _calendar_service, _gmail_service
    if _market_service is None:
        from app.services.market_data import MarketDataService
        from app.services.news import NewsService
        from app.services.sec_edgar import SECEdgarService
        from app.services.finnhub_extended import FinnhubService
        from app.integrations.google_services import GoogleCalendarService, GmailService
        _market_service = MarketDataService()
        _news_service = NewsService()
        _sec_service = SECEdgarService()
        _finnhub_ext = FinnhubService()
        _calendar_service = GoogleCalendarService()
        _gmail_service = GmailService()
    return _market_service, _news_service, _sec_service, _finnhub_ext, _calendar_service, _gmail_service


async def handle_tool_call(tool_name: str, tool_args: dict, user: User = None) -> dict:
    """Execute an AI tool call and return real data."""
    market_service, news_service, sec_service, finnhub_ext, calendar_service, gmail_service = _get_services()

    try:
        # --- Market Data Tools ---
        if tool_name == "get_stock_price":
            return await market_service.get_stock_price(tool_args["ticker"])

        elif tool_name == "get_company_profile":
            return await market_service.get_company_profile(tool_args["ticker"])

        elif tool_name == "get_company_news":
            return await news_service.get_company_news(tool_args["ticker"], tool_args.get("limit", 5))

        elif tool_name == "get_market_news":
            return await news_service.get_market_news(tool_args.get("category", "general"), tool_args.get("limit", 5))

        elif tool_name == "compare_companies":
            tickers = tool_args.get("tickers", [])
            if isinstance(tickers, str):
                tickers = [t.strip() for t in tickers.split(",")]
            return await market_service.compare_companies(tickers)

        elif tool_name == "search_stock":
            return await market_service.search_stock(tool_args["query"])

        elif tool_name == "get_market_overview":
            return await market_service.get_market_overview()

        elif tool_name == "get_earnings":
            return await market_service.get_earnings(tool_args["ticker"])

        elif tool_name == "get_sec_filings":
            return await sec_service.get_recent_filings(
                tool_args["ticker"],
                tool_args.get("form_type"),
                tool_args.get("limit", 5)
            )

        # --- Alert Tools ---
        elif tool_name == "create_price_alert":
            if user:
                await AlertRepository.create_alert(
                    telegram_id=user.telegram_id,
                    user_id=user.id,
                    alert_type=tool_args.get("alert_type", "price_above"),
                    ticker=tool_args.get("ticker"),
                    condition_value=float(tool_args.get("condition_value", 0)),
                    description=tool_args.get("description", ""),
                )
                return {
                    "status": "created",
                    "message": f"✅ Alert set for {tool_args.get('ticker')} — {tool_args.get('alert_type')} {tool_args.get('condition_value')}",
                }
            return {"error": "User context required to create alert."}

        # --- Extended Finnhub Tools ---
        elif tool_name == "get_analyst_ratings":
            return await finnhub_ext.get_analyst_ratings(tool_args["ticker"])

        elif tool_name == "get_insider_transactions":
            return await finnhub_ext.get_insider_transactions(tool_args["ticker"])

        elif tool_name == "get_economic_calendar":
            return await finnhub_ext.get_economic_calendar()

        elif tool_name == "get_earnings_calendar":
            return await finnhub_ext.get_earnings_calendar(tool_args.get("ticker"))

        # --- Google Integration Tools ---
        elif tool_name == "get_google_calendar":
            if not user or not user.google_tokens:
                return {"error": "Google account not connected. Ask me to connect your Google account first."}
            events = calendar_service.get_upcoming_events(user.google_tokens, tool_args.get("days", 7))
            return {"events": events, "count": len(events)}

        elif tool_name == "create_calendar_event":
            if not user or not user.google_tokens:
                return {"error": "Google account not connected. Ask me to connect your Google account first."}
            return calendar_service.create_event(
                user.google_tokens,
                tool_args["summary"],
                tool_args["start_datetime"],
                tool_args["end_datetime"],
                tool_args.get("description", ""),
            )

        elif tool_name == "search_gmail":
            if not user or not user.google_tokens:
                return {"error": "Google account not connected. Ask me to connect your Google account first."}
            emails = gmail_service.search_emails(
                user.google_tokens,
                tool_args["query"],
                tool_args.get("max_results", 5),
            )
            return {"emails": emails, "count": len(emails)}

        elif tool_name == "set_event_reminder":
            from datetime import datetime, timedelta
            from app.database.connection import async_session
            from app.database.models import Alert as AlertModel
            event_date_str = tool_args.get("event_date", "")
            advance_minutes = int(tool_args.get("advance_minutes", 60))
            event_description = tool_args.get("event_description", "Financial Event")
            ticker = tool_args.get("ticker", "")
            try:
                event_dt = datetime.strptime(event_date_str, "%Y-%m-%d").replace(hour=9, minute=30)
                remind_at = event_dt - timedelta(minutes=advance_minutes)
                async with async_session() as session:
                    alert = AlertModel(
                        user_id=user.id,
                        telegram_id=user.telegram_id,
                        alert_type="event_reminder",
                        ticker=ticker or None,
                        description=event_description,
                        remind_at=remind_at,
                        event_date=event_date_str,
                        is_active=True,
                    )
                    session.add(alert)
                    await session.commit()
                advance_label = f"{advance_minutes} minutes" if advance_minutes < 60 else f"{advance_minutes // 60} hour(s)"
                return {
                    "success": True,
                    "message": f"Reminder set for '{event_description}' — I'll notify you {advance_label} before on {event_date_str}.",
                    "remind_at": remind_at.strftime("%Y-%m-%d %H:%M")
                }
            except ValueError:
                return {"error": "Invalid date format. Please provide date as YYYY-MM-DD."}

        else:
            return {"error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        logger.error(f"Tool '{tool_name}' failed: {e}", exc_info=True)
        return {"error": str(e)}


class AIEngine:
    """Main AI orchestrator for Atlas Financial Assistant."""

    def __init__(self):
        self.memory = ConversationMemory()

    async def process_message(self, user: User, message: str, message_type: str = "text") -> str:
        """Process a user message and return a personalized AI response."""
        if not user.is_onboarded:
            # If user asks a real financial/market question during onboarding,
            # complete onboarding silently and answer their question directly.
            # Don't make them wait — feel like an analyst, not a form.
            # Use word-boundary matching to avoid "investor" matching "invest"
            financial_patterns = [
                r"\bprice\b", r"\bstock\b", r"\bmarket\b", r"\bshare\b",
                r"\bcrypto\b", r"\bbitcoin\b", r"\bportfolio\b", r"\brevenue\b",
                r"\bchart\b", r"\bbuy\b", r"\bsell\b", r"\bnews\b",
                r"\bticker\b", r"\bnasdaq\b", r"\bdow\b", r"\bipo\b",
                r"\bdividend\b", r"\bearnings\b", r"\bfomc\b", r"\bcpi\b",
                r"\bgdp\b", r"\banalyst\b", r"\binsider\b", r"\bfiling\b",
                r"\bsec\b", r"what'?s\s+\w+\s+stock", r"how is the market",
                r"tell me about \w+", r"show me \w+", r"\btrading at\b",
                r"\bmarket cap\b", r"\bpe ratio\b", r"\bshare price\b",
            ]
            msg_lower = message.lower()
            is_financial_query = any(
                re.search(p, msg_lower) for p in financial_patterns
            )

            if is_financial_query and user.onboarding_step not in ("welcome", None):
                # Silently mark onboarding complete and answer the question
                await UserRepository.update_user(
                    user.telegram_id, is_onboarded=True, onboarding_step="complete"
                )
                user.is_onboarded = True
                response = await self._handle_conversation(user, message)
            else:
                response = await self._handle_onboarding(user, message)
        else:
            response = await self._handle_conversation(user, message)


        await self.memory.save_interaction(
            telegram_id=user.telegram_id,
            user_id=user.id,
            user_message=message,
            assistant_response=response,
            message_type=message_type,
        )
        await UserRepository.update_last_active(user.telegram_id)
        return response

    async def _handle_onboarding(self, user: User, message: str) -> str:
        """Drive conversational onboarding — one step at a time."""
        history = await self.memory.get_context(user.telegram_id, limit=10)
        pre_fetched = await self._pre_fetch_market_data(message)

        prompt = ONBOARDING_PROMPT.format(
            onboarding_step=user.onboarding_step,
            user_name=user.first_name or "there",
            previous_messages=history,
            user_message=message,
        )

        user_msg = message
        if pre_fetched:
            user_msg += (
                f"\n\n[REAL-TIME MARKET DATA — FETCHED LIVE FROM FINNHUB API:\n"
                f"{pre_fetched}\n"
                f"INSTRUCTION: Use these exact real-time numbers in your response. Cite the source.]"
            )

        async def _tool_handler(tool_name: str, tool_args: dict) -> dict:
            return await handle_tool_call(tool_name, tool_args, user=user)

        response = await model_chain.generate(prompt, user_msg, tool_handler=_tool_handler)
        await self._process_onboarding_step(user, message)
        return response

    async def _process_onboarding_step(self, user: User, message: str):
        """Parse user message and advance onboarding state machine."""
        step = user.onboarding_step
        msg_lower = message.lower().strip()
        is_skip = msg_lower in ("skip", "skip this", "next", "pass", "no", "nope")

        if step == "welcome":
            if not is_skip:
                roles = {
                    "investor": "Investor", "invest": "Investor",
                    "analyst": "Analyst", "analysis": "Analyst",
                    "founder": "Founder", "startup": "Founder",
                    "student": "Student", "learning": "Student",
                    "professional": "Finance Professional",
                    "trader": "Trader", "trading": "Trader",
                    "portfolio manager": "Portfolio Manager", "portfolio": "Portfolio Manager",
                    "researcher": "Research Analyst", "research": "Research Analyst",
                    "banker": "Investment Banker", "banking": "Investment Banker",
                    "cfo": "CFO", "ceo": "CEO", "vc": "Venture Capitalist", "venture": "Venture Capitalist",
                }
                for keyword, role in roles.items():
                    if keyword in msg_lower:
                        await UserRepository.update_user(user.telegram_id, role=role)
                        break
            await UserRepository.update_user(user.telegram_id, onboarding_step="role")

        elif step == "role":
            if not is_skip:
                sector_kws = [
                    "technology", "tech", "healthcare", "finance", "fintech", "energy",
                    "ai", "artificial intelligence", "semiconductor", "crypto", "cryptocurrency",
                    "blockchain", "banking", "real estate", "pharma", "pharmaceutical",
                    "ev", "electric vehicle", "automotive", "retail", "cloud", "saas",
                    "biotech", "aerospace", "defense", "consumer", "media", "telecom",
                    "commodities", "industrials", "utilities", "materials",
                ]
                found = list(set([s.title() for s in sector_kws if s in msg_lower]))
                if found:
                    await UserRepository.update_user(user.telegram_id, sectors=found)
            await UserRepository.update_user(user.telegram_id, onboarding_step="interests")

        elif step == "interests":
            if not is_skip:
                tickers = re.findall(r'\b[A-Z]{1,5}\b', message)
                company_map = {
                    "apple": "AAPL", "microsoft": "MSFT", "google": "GOOGL",
                    "alphabet": "GOOGL", "amazon": "AMZN", "tesla": "TSLA",
                    "nvidia": "NVDA", "meta": "META", "netflix": "NFLX",
                    "disney": "DIS", "intel": "INTC", "amd": "AMD",
                    "spotify": "SPOT", "uber": "UBER", "airbnb": "ABNB",
                    "palantir": "PLTR", "snowflake": "SNOW", "datadog": "DDOG",
                    "shopify": "SHOP", "coinbase": "COIN", "robinhood": "HOOD",
                    "jpmorgan": "JPM", "goldman": "GS", "berkshire": "BRK-B",
                }
                for name, ticker in company_map.items():
                    if name in msg_lower and ticker not in tickers:
                        tickers.append(ticker)
                if tickers:
                    await UserRepository.update_user(user.telegram_id, watchlist=list(set(tickers)))
            await UserRepository.update_user(user.telegram_id, onboarding_step="watchlist")

        elif step == "watchlist":
            if not is_skip:
                interest_map = {
                    "news": "Market News", "earnings": "Earnings", "sec": "SEC Filings",
                    "filing": "SEC Filings", "analyst": "Analyst Ratings",
                    "macro": "Macroeconomic Events", "economic": "Macroeconomic Events",
                    "ipo": "IPOs", "dividend": "Dividends", "merger": "M&A",
                    "acquisition": "M&A", "crypto": "Cryptocurrency",
                    "technical": "Technical Analysis", "insider": "Insider Transactions",
                }
                interests = list(set([
                    label for kw, label in interest_map.items() if kw in msg_lower
                ]))
                if interests:
                    await UserRepository.update_user(user.telegram_id, interests=interests)
            await UserRepository.update_user(user.telegram_id, onboarding_step="briefing")

        elif step == "briefing":
            if not is_skip:
                time_match = re.search(r'(\d{1,2})[:\.]?(\d{2})?\s*(am|pm|AM|PM)?', message)
                if time_match:
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2) or 0)
                    ampm = (time_match.group(3) or "").lower()
                    if ampm == "pm" and hour < 12:
                        hour += 12
                    elif ampm == "am" and hour == 12:
                        hour = 0
                    await UserRepository.update_user(
                        user.telegram_id,
                        briefing_time=f"{hour:02d}:{minute:02d}"
                    )
            await UserRepository.update_user(
                user.telegram_id, onboarding_step="complete", is_onboarded=True
            )

    async def _handle_conversation(self, user: User, message: str) -> str:
        """Handle a regular conversation with full tools, memory, and personalization."""

        # Check for Google connect intent
        if any(kw in message.lower() for kw in ["connect google", "link google", "google account", "connect gmail", "connect calendar"]):
            from app.config import settings
            from app.integrations.google_services import is_google_configured
            if not is_google_configured():
                return (
                    "⚠️ *Google Integration Setup Needed*\n\n"
                    "To enable Calendar, Gmail, and Sheets access:\n"
                    "1. Create an OAuth 2.0 Client ID at [Google Cloud Console](https://console.cloud.google.com/)\n"
                    "2. Add `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` to your environment variables\n"
                    "3. Set redirect URI to: `https://atlas-ai-financial-assistant-f2m5.onrender.com/auth/google/callback`"
                )
            base_url = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:8000")
            auth_link = f"{base_url}/auth/google?telegram_id={user.telegram_id}"
            return (
                f"🔗 *Connect your Google Account*\n\n"
                f"Click this link to authorize Atlas:\n{auth_link}\n\n"
                f"Once connected, I can access your:\n"
                f"📅 *Google Calendar* — view & create events\n"
                f"📧 *Gmail* — search emails about companies\n"
                f"📊 *Google Sheets* — analyze spreadsheets"
            )

        user_context = await self.memory.get_user_context(user)
        conv_history = await self.memory.get_context(user.telegram_id, limit=15)

        # Pre-fetch live market data for price/comparison/market queries
        # Injected directly into user_message so ALL models (Gemini, Groq, SambaNova, etc.)
        # get real-time Finnhub/Alpha Vantage data even if function calling fails/rate-limits.
        pre_fetched = await self._pre_fetch_market_data(message)

        system_prompt = SYSTEM_PROMPT.format(
            user_context=user_context,
            conversation_history=conv_history,
        )

        user_message = message
        if pre_fetched:
            user_message += (
                f"\n\n[REAL-TIME MARKET DATA — FETCHED LIVE FROM FINNHUB / ALPHA VANTAGE API:\n"
                f"{pre_fetched}\n"
                f"INSTRUCTION: You MUST use these exact real-time numbers in your response. "
                f"Cite the data source. DO NOT use internal training memory for prices.]"
            )

        # Onboarding guard — prevent AI from asking setup questions after onboarding
        if user.is_onboarded:
            user_message += (
                "\n\n[SYSTEM RULE: User is FULLY ONBOARDED. "
                "NEVER ask about their role, sectors, watchlist, briefing time, "
                "or any notification delivery method. "
                "Just answer the question directly.]"
            )

        async def _tool_handler(tool_name: str, tool_args: dict) -> dict:
            return await handle_tool_call(tool_name, tool_args, user=user)

        response = await model_chain.generate(
            system_prompt=system_prompt,
            user_message=user_message,
            tool_handler=_tool_handler,
        )

        # ── Safety net: if AI hallucinated a price, force-correct it ──
        # Check if this was a price query but the AI didn't use real data
        msg_lower = message.lower()
        price_keywords = ["price", "stock", "trading", "share", "worth", "how much", "what's", "what is"]
        is_price_query = any(kw in msg_lower for kw in price_keywords)

        if is_price_query and not any(src in response.lower() for src in ["finnhub", "alpha vantage", "yahoo finance", "per "]):
            # AI likely hallucinated — fetch real data and re-generate
            market_service, _, _, _, _, _ = _get_services()
            company_map = {
                "apple": "AAPL", "microsoft": "MSFT", "google": "GOOGL", "alphabet": "GOOGL",
                "amazon": "AMZN", "tesla": "TSLA", "nvidia": "NVDA", "meta": "META",
                "netflix": "NFLX", "uber": "UBER", "reliance": "RELIANCE.NS",
                "tata": "TCS.NS", "infosys": "INFY.NS", "tcs": "TCS.NS",
                "hdfc": "HDFCBANK.NS", "sbi": "SBIN.NS",
            }
            ticker = None
            for name, t in company_map.items():
                if name in msg_lower:
                    ticker = t
                    break
            if not ticker:
                ticker_match = re.search(r'\b([A-Z]{2,5})\b', message)
                if ticker_match:
                    ticker = ticker_match.group(1)

            if ticker:
                try:
                    data = await market_service.get_stock_price(ticker)
                    if "error" not in data:
                        # Re-generate with forced real data
                        forced_message = (
                            f"User asked: {message}\n\n"
                            f"HERE IS THE REAL-TIME DATA — use ONLY these numbers:\n"
                            f"Ticker: {data.get('ticker')} | Price: ${data.get('price')} | "
                            f"Change: {data.get('change')} ({data.get('percent_change')}%) | "
                            f"Open: ${data.get('open', 'N/A')} | High: ${data.get('high', 'N/A')} | "
                            f"Low: ${data.get('low', 'N/A')} | "
                            f"52W High: ${data.get('week_52_high', 'N/A')} | "
                            f"52W Low: ${data.get('week_52_low', 'N/A')} | "
                            f"Source: {data.get('source', 'Finnhub')}\n\n"
                            f"Format a concise response with these exact numbers. Cite the source."
                        )
                        if user.is_onboarded:
                            forced_message += (
                                "\n\n[SYSTEM RULE: User is FULLY ONBOARDED. "
                                "Do NOT ask any onboarding or setup questions.]"
                            )
                        response = await model_chain.generate(
                            system_prompt=system_prompt,
                            user_message=forced_message,
                            tool_handler=None,  # No tools — just format the data
                        )
                except Exception as e:
                    logger.warning(f"Safety net re-fetch failed: {e}")

        await self._check_for_watchlist_updates(user, message)
        return response

    async def _pre_fetch_market_data(self, message: str) -> str:
        """Pre-fetch live data for price/market queries so AI always has real numbers."""
        msg_lower = message.lower()
        results = []
        market_service, news_service, _, _, _, _ = _get_services()

        # Detect stock price queries
        price_keywords = ["price", "trading", "stock", "share", "worth", "value", "how much", "what is", "what's"]
        is_price_query = any(kw in msg_lower for kw in price_keywords)

        if is_price_query:
            # Known company → ticker mapping
            company_map = {
                "apple": "AAPL", "microsoft": "MSFT", "google": "GOOGL", "alphabet": "GOOGL",
                "amazon": "AMZN", "tesla": "TSLA", "nvidia": "NVDA", "meta": "META", "facebook": "META",
                "netflix": "NFLX", "uber": "UBER", "lyft": "LYFT", "airbnb": "ABNB",
                "palantir": "PLTR", "amd": "AMD", "intel": "INTC", "disney": "DIS",
                "spotify": "SPOT", "coinbase": "COIN", "robinhood": "HOOD", "snowflake": "SNOW",
                "shopify": "SHOP", "square": "SQ", "block": "SQ", "paypal": "PYPL",
                "jpmorgan": "JPM", "goldman": "GS", "berkshire": "BRK-B", "bank of america": "BAC",
                "boeing": "BA", "walmart": "WMT", "costco": "COST", "nike": "NKE",
                "starbucks": "SBUX", "mcdonalds": "MCD", "mcdonald": "MCD", "visa": "V",
                "mastercard": "MA", "salesforce": "CRM", "oracle": "ORCL", "adobe": "ADBE",
                "ibm": "IBM", "sony": "SONY", "broadcom": "AVGO", "qualcomm": "QCOM",
                "reliance": "RELIANCE.NS", "tata": "TCS.NS", "infosys": "INFY.NS",
                "wipro": "WIPRO.NS", "tcs": "TCS.NS", "hdfc": "HDFCBANK.NS", "sbi": "SBIN.NS",
                "icici": "ICICIBANK.NS", "samsung": "005930.KS", "alibaba": "BABA", "baidu": "BIDU",
            }
            ticker_to_fetch = None
            for name, ticker in company_map.items():
                if name in msg_lower:
                    ticker_to_fetch = ticker
                    break

            # Also check for direct tickers (e.g. AAPL, TSLA, PLTR, NVDA, MSFT)
            if not ticker_to_fetch:
                words = re.findall(r'\b([A-Za-z]{2,5})\b', message)
                ignore = {"WHAT", "WHATS", "STOCK", "PRICE", "HOW", "MUCH", "SHOW", "TELL", "SHARE", "ABOUT", "GIVE", "TODAY", "YOUR", "THIS"}
                for w in words:
                    if w.upper() not in ignore:
                        ticker_to_fetch = w.upper()
                        break

            if ticker_to_fetch:
                try:
                    data = await market_service.get_stock_price(ticker_to_fetch)
                    if "error" not in data:
                        results.append(
                            f"Stock: {ticker_to_fetch} ({data.get('company_name', ticker_to_fetch)}) | "
                            f"Price: ${data.get('price', 'N/A')} | "
                            f"Change: ${data.get('change', 0)} ({data.get('percent_change', 0)}%) | "
                            f"Open: ${data.get('open', 'N/A')} | High: ${data.get('high', 'N/A')} | Low: ${data.get('low', 'N/A')} | "
                            f"52W High: ${data.get('week_52_high', 'N/A')} | 52W Low: ${data.get('week_52_low', 'N/A')} | "
                            f"Source: {data.get('source', 'Finnhub API')}"
                        )
                except Exception:
                    pass

        # Detect market overview queries
        market_keywords = ["market", "s&p", "nasdaq", "dow", "indices", "index", "nifty", "sensex"]
        if any(kw in msg_lower for kw in market_keywords) and "price" not in msg_lower:
            try:
                overview = await market_service.get_market_overview()
                if overview and "error" not in overview:
                    results.append(f"Market Overview: {json.dumps(overview)}")
            except Exception:
                pass

        # Detect comparison queries — fetch all mentioned companies
        compare_keywords = ["compare", "vs", "versus", "difference between", "better than", "against"]
        if any(kw in msg_lower for kw in compare_keywords):
            company_map = {
                "apple": "AAPL", "microsoft": "MSFT", "google": "GOOGL",
                "amazon": "AMZN", "tesla": "TSLA", "nvidia": "NVDA", "meta": "META",
                "netflix": "NFLX", "uber": "UBER", "reliance": "RELIANCE.NS",
                "infosys": "INFY.NS", "tcs": "TCS.NS", "hdfc": "HDFCBANK.NS",
                "samsung": "005930.KS", "alibaba": "BABA",
            }
            fetched_tickers = set()
            for name, ticker in company_map.items():
                if name in msg_lower and ticker not in fetched_tickers:
                    try:
                        data = await market_service.get_stock_price(ticker)
                        if "error" not in data:
                            results.append(
                                f"Stock: {ticker} | Price: ${data.get('price', 'N/A')} | "
                                f"Change: {data.get('change_percent', 'N/A')}% | "
                                f"52W High: {data.get('week_52_high', 'N/A')} | "
                                f"52W Low: {data.get('week_52_low', 'N/A')}"
                            )
                            fetched_tickers.add(ticker)
                    except Exception:
                        pass

        return "\n".join(results) if results else ""


    async def _check_for_watchlist_updates(self, user: User, message: str):
        """Auto-update watchlist when user mentions tracking or removing stocks."""
        msg_lower = message.lower()
        add_kws = ["track", "watch", "follow", "monitor", "add to watchlist", "add to my watchlist"]
        remove_kws = ["stop tracking", "unwatch", "unfollow", "remove from watchlist"]

        tickers = re.findall(r'\b[A-Z]{1,5}\b', message)
        company_map = {
            "apple": "AAPL", "microsoft": "MSFT", "google": "GOOGL",
            "amazon": "AMZN", "tesla": "TSLA", "nvidia": "NVDA", "meta": "META",
            "netflix": "NFLX", "uber": "UBER",
        }
        for name, ticker in company_map.items():
            if name in msg_lower:
                tickers.append(ticker)

        if any(kw in msg_lower for kw in add_kws) and tickers:
            updated = list(set((user.watchlist or []) + tickers))
            await UserRepository.update_user(user.telegram_id, watchlist=updated)

        elif any(kw in msg_lower for kw in remove_kws) and tickers and user.watchlist:
            updated = [t for t in user.watchlist if t not in tickers]
            await UserRepository.update_user(user.telegram_id, watchlist=updated)


# Global singleton
ai_engine = AIEngine()
