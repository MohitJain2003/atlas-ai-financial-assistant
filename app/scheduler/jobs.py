"""
Background Jobs Scheduler — Morning briefings, evening summaries, price alerts,
proactive news monitoring, and earnings calendar notifications.
"""
import logging
from datetime import datetime, date, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot

from app.config import settings
from app.database.repositories import UserRepository, AlertRepository
from app.services.daily_briefing import DailyBriefingService
from app.services.market_data import MarketDataService
from app.services.news import NewsService
from app.services.finnhub_extended import FinnhubService

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
briefing_service = DailyBriefingService()
market_service = MarketDataService()
news_service = NewsService()
finnhub_service = FinnhubService()

# Track last seen news headlines to avoid duplicates
_seen_news_headlines: set = set()


def _get_bot():
    from telegram.request import HTTPXRequest
    request = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0)
    return Bot(token=settings.TELEGRAM_BOT_TOKEN, request=request)


async def send_morning_briefings():
    """Run every hour — send personalized morning briefing to users whose time matches."""
    if not settings.TELEGRAM_BOT_TOKEN:
        return

    now = datetime.now()
    users = await UserRepository.get_all_users_with_briefing()
    if not users:
        return

    bot = _get_bot()
    for user in users:
        user_hour = (user.briefing_time or "08:00")[:2]
        if user_hour != f"{now.hour:02d}":
            continue
        try:
            briefing = await briefing_service.generate_morning_briefing(user)
            header = f"🌅 *Good morning, {user.first_name or 'there'}!*\n\n"
            full_msg = header + briefing
            if len(full_msg) > 4000:
                for i in range(0, len(full_msg), 4000):
                    await bot.send_message(chat_id=user.telegram_id, text=full_msg[i:i+4000], parse_mode="Markdown")
            else:
                await bot.send_message(chat_id=user.telegram_id, text=full_msg, parse_mode="Markdown")
            logger.info(f"✅ Morning briefing sent to {user.telegram_id}")
        except Exception as e:
            logger.error(f"Morning briefing failed for {user.telegram_id}: {e}")


async def send_evening_summaries():
    """Run every hour — send evening market summary to users whose time matches."""
    if not settings.TELEGRAM_BOT_TOKEN:
        return

    now = datetime.now()
    users = await UserRepository.get_all_users_with_briefing()
    if not users:
        return

    bot = _get_bot()
    for user in users:
        evening_hour = (user.evening_briefing_time or "18:00")[:2]
        if evening_hour != f"{now.hour:02d}":
            continue
        try:
            # Generate evening summary
            from app.ai.models import model_chain

            market_data = await market_service.get_market_overview()
            news = await news_service.get_market_news(limit=3)
            watchlist_data = {}
            if user.watchlist:
                for ticker in user.watchlist[:5]:
                    data = await market_service.get_stock_price(ticker)
                    if "error" not in data:
                        watchlist_data[ticker] = {
                            "price": data.get("price"),
                            "change": data.get("change"),
                            "pct_change": data.get("percent_change"),
                        }

            prompt = (
                f"Generate a brief evening market wrap-up for {user.first_name or 'the user'} "
                f"(Role: {user.role or 'investor'}).\n\n"
                f"Market data: {market_data}\n"
                f"Watchlist: {watchlist_data}\n"
                f"News: {news}\n\n"
                "Keep it under 1500 chars. Cover: today's market performance, "
                "1-2 key watchlist moves, 1 key news story, and ONE thing to watch tomorrow. "
                "Format for Telegram — bold key numbers, use 📉📈 emojis."
            )
            summary = await model_chain.generate(prompt, "Generate evening wrap-up.")
            header = f"🌆 *Evening Market Wrap — {date.today().strftime('%b %d')}*\n\n"
            full_msg = header + summary
            if len(full_msg) > 4000:
                for i in range(0, len(full_msg), 4000):
                    await bot.send_message(chat_id=user.telegram_id, text=full_msg[i:i+4000], parse_mode="Markdown")
            else:
                await bot.send_message(chat_id=user.telegram_id, text=full_msg, parse_mode="Markdown")
            logger.info(f"✅ Evening summary sent to {user.telegram_id}")
        except Exception as e:
            logger.error(f"Evening summary failed for {user.telegram_id}: {e}")


async def check_price_alerts():
    """Every 15 min — check active price alerts vs live market data."""
    alerts = await AlertRepository.get_active_alerts()
    if not alerts or not settings.TELEGRAM_BOT_TOKEN:
        return

    bot = _get_bot()
    for alert in alerts:
        if not alert.ticker:
            continue
        try:
            data = await market_service.get_stock_price(alert.ticker)
            if "error" in data:
                continue

            price = data.get("price")
            pct = data.get("percent_change", 0)
            triggered = False
            msg = ""

            if alert.alert_type == "price_above" and price >= alert.condition_value:
                triggered = True
                msg = (f"🚨 *PRICE ALERT — {alert.ticker}*\nCrossed above *${alert.condition_value}*\n"
                       f"Now: *${price}* ({pct:+.2f}%)\n_Source: {data.get('source', 'Live')}_")

            elif alert.alert_type == "price_below" and price <= alert.condition_value:
                triggered = True
                msg = (f"🚨 *PRICE ALERT — {alert.ticker}*\nDropped below *${alert.condition_value}*\n"
                       f"Now: *${price}* ({pct:+.2f}%)\n_Source: {data.get('source', 'Live')}_")

            elif alert.alert_type == "percent_change" and abs(pct) >= alert.condition_value:
                icon = "📈" if pct > 0 else "📉"
                triggered = True
                msg = (f"⚡ *VOLATILITY ALERT — {alert.ticker}*\n{icon} Moved *{pct:+.2f}%* today\n"
                       f"Current: *${price}*\n_Threshold: {alert.condition_value}%_")

            if triggered:
                await bot.send_message(chat_id=alert.telegram_id, text=msg, parse_mode="Markdown")
                await AlertRepository.trigger_alert(alert.id)
                logger.info(f"⚡ Alert {alert.id} triggered for {alert.ticker}")

        except Exception as e:
            logger.error(f"Alert check failed for {alert.ticker}: {e}")


async def monitor_watchlist_news():
    """Every 2 hours — proactively push breaking news about watchlist stocks."""
    global _seen_news_headlines
    if not settings.TELEGRAM_BOT_TOKEN:
        return

    users = await UserRepository.get_all_users_with_briefing()
    if not users:
        return

    bot = _get_bot()
    for user in users:
        if not user.watchlist:
            continue
        try:
            for ticker in user.watchlist[:5]:
                articles = await news_service.get_company_news(ticker, limit=3)
                for article in articles:
                    headline = article.get("headline", "")
                    if not headline or headline in _seen_news_headlines:
                        continue
                    _seen_news_headlines.add(headline)
                    # Keep set bounded
                    if len(_seen_news_headlines) > 1000:
                        _seen_news_headlines = set(list(_seen_news_headlines)[-500:])

                    msg = (
                        f"📰 *Breaking: {ticker}*\n"
                        f"*{headline[:120]}*\n"
                        f"_{article.get('source', '')}_ — {article.get('url', '')}"
                    )
                    await bot.send_message(chat_id=user.telegram_id, text=msg, parse_mode="Markdown",
                                           disable_web_page_preview=False)
        except Exception as e:
            logger.error(f"News monitor error for user {user.telegram_id}: {e}")


async def send_earnings_reminders():
    """Every morning at 7 AM — notify users if a watchlist stock reports earnings today or tomorrow."""
    if not settings.TELEGRAM_BOT_TOKEN:
        return

    now = datetime.now()
    if now.hour != 7:  # Only run at 7 AM
        return

    users = await UserRepository.get_all_users_with_briefing()
    if not users:
        return

    bot = _get_bot()
    today_str = date.today().isoformat()
    tomorrow_str = (date.today() + timedelta(days=1)).isoformat()

    for user in users:
        if not user.watchlist:
            continue
        try:
            reminders = []
            for ticker in user.watchlist:
                cal = await finnhub_service.get_earnings_calendar(ticker)
                for entry in cal.get("earnings_calendar", []):
                    entry_date = entry.get("date", "")
                    if entry_date in (today_str, tomorrow_str):
                        when = "today" if entry_date == today_str else "tomorrow"
                        eps_est = entry.get("eps_estimate")
                        eps_str = f" (EPS est: ${eps_est})" if eps_est else ""
                        reminders.append(f"• *{ticker}* reports earnings {when}{eps_str}")

            if reminders:
                msg = (
                    "📅 *Earnings Reminder*\n\n"
                    + "\n".join(reminders)
                    + "\n\n_Want a pre-earnings briefing? Just ask me!_"
                )
                await bot.send_message(chat_id=user.telegram_id, text=msg, parse_mode="Markdown")
                logger.info(f"📅 Earnings reminder sent to {user.telegram_id}")
        except Exception as e:
            logger.error(f"Earnings reminder error for {user.telegram_id}: {e}")


def start_scheduler():
    """Start all background jobs."""
    if scheduler.running:
        return

    # Morning briefings — hourly check, respects each user's individual time
    scheduler.add_job(send_morning_briefings, "cron", minute=0, id="morning_briefings", replace_existing=True)

    # Evening summaries — hourly check, respects each user's individual evening time
    scheduler.add_job(send_evening_summaries, "cron", minute=0, id="evening_summaries", replace_existing=True)

    # Price alert monitor — every 15 minutes
    scheduler.add_job(check_price_alerts, "interval", minutes=15, id="price_alerts", replace_existing=True)

    # Proactive news monitor — every 2 hours
    scheduler.add_job(monitor_watchlist_news, "interval", hours=2, id="news_monitor", replace_existing=True)

    # Earnings reminder — every hour (only actually sends at 7 AM)
    scheduler.add_job(send_earnings_reminders, "cron", minute=5, id="earnings_reminders", replace_existing=True)

    scheduler.start()
    logger.info(
        "⏱️ Scheduler started: Morning Briefings + Evening Summaries + "
        "Price Alerts (15min) + News Monitor (2hr) + Earnings Reminders (7AM)"
    )
