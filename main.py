"""
Atlas Financial Assistant — Main Entry Point (FastAPI + Telegram Bot + Google OAuth)
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.config import settings
from app.database.connection import init_db
from app.bot.handlers import create_bot_app

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
)
logger = logging.getLogger(__name__)

bot_app = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB, start bot polling, register scheduler."""
    global bot_app
    logger.info("🚀 Initializing Database...")
    await init_db()

    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_BOT_TOKEN != "your_telegram_bot_token_here":
        logger.info("🤖 Starting Telegram Bot polling...")
        bot_app = create_bot_app()
        await bot_app.initialize()
        await bot_app.start()
        await bot_app.updater.start_polling()

        from app.scheduler.jobs import start_scheduler
        start_scheduler()
    else:
        logger.warning("⚠️ TELEGRAM_BOT_TOKEN not configured. Bot polling skipped.")

    yield

    if bot_app:
        logger.info("🛑 Stopping Telegram Bot...")
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()


app = FastAPI(
    title="Atlas AI Financial Assistant",
    description="AI-powered Financial Assistant — Telegram Bot Backend",
    version="2.0.0",
    lifespan=lifespan
)

# Register Google OAuth routes
from app.integrations.google_auth_routes import router as google_router
app.include_router(google_router)


@app.get("/")
async def root():
    return {
        "status": "online",
        "app": "Atlas AI Financial Assistant",
        "version": "2.0.0",
        "features": [
            "Real-time market data", "SEC filings", "Analyst ratings",
            "Insider transactions", "Economic calendar", "Earnings calendar",
            "Google Calendar", "Gmail", "Google Sheets", "Document analysis",
            "Voice messages", "Price alerts", "Daily briefings"
        ]
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "build": "v2.4-emoji-name-polish"}


@app.get("/debug/price/{ticker}")
async def debug_price(ticker: str):
    """Debug endpoint — test if financial APIs work on Render."""
    from app.services.market_data import MarketDataService
    svc = MarketDataService()
    result = await svc.get_stock_price(ticker.upper())
    return {"ticker": ticker.upper(), "result": result, "finnhub_key_set": bool(svc.finnhub_key), "alphavantage_key_set": bool(svc.alphavantage_key)}


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8000))
    reload = os.getenv("RENDER", "") == ""  # No hot-reload on Render
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=reload)
