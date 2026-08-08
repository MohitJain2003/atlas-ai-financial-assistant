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
        from telegram import Update
        await bot_app.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
        )

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


from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Atlas AI — Financial Analyst Assistant</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
            body { background-color: #0b0f19; color: #f3f4f6; min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 2rem; }
            .container { max-width: 800px; width: 100%; background: rgba(17, 24, 39, 0.8); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 1.5rem; padding: 2.5rem; backdrop-filter: blur(16px); box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); text-align: center; }
            .badge { display: inline-flex; align-items: center; gap: 0.5rem; background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); color: #10b981; padding: 0.4rem 1rem; border-radius: 9999px; font-size: 0.875rem; font-weight: 600; margin-bottom: 1.5rem; }
            .dot { width: 8px; height: 8px; background-color: #10b981; border-radius: 50%; box-shadow: 0 0 8px #10b981; }
            h1 { font-size: 2.5rem; font-weight: 800; background: linear-gradient(to right, #ffffff, #9ca3af); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 1rem; }
            p.subtitle { font-size: 1.125rem; color: #9ca3af; margin-bottom: 2rem; line-height: 1.6; }
            .cta-btn { display: inline-flex; align-items: center; justify-content: center; gap: 0.75rem; background: linear-gradient(135deg, #2563eb, #1d4ed8); color: #ffffff; font-weight: 700; font-size: 1.125rem; padding: 1rem 2rem; border-radius: 0.75rem; text-decoration: none; transition: all 0.2s ease; box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.4); margin-bottom: 2.5rem; }
            .cta-btn:hover { transform: translateY(-2px); box-shadow: 0 20px 25px -5px rgba(37, 99, 235, 0.5); }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; text-align: left; }
            .card { background: rgba(31, 41, 55, 0.5); border: 1px solid rgba(255, 255, 255, 0.05); padding: 1.25rem; border-radius: 1rem; }
            .card h3 { font-size: 1rem; font-weight: 700; color: #60a5fa; margin-bottom: 0.5rem; }
            .card p { font-size: 0.875rem; color: #9ca3af; line-height: 1.4; }
            footer { margin-top: 2rem; font-size: 0.875rem; color: #6b7280; }
            footer strong { color: #e5e7eb; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="badge">
                <span class="dot"></span> 24/7 Production Backend Online
            </div>
            <h1>Atlas AI Financial Assistant</h1>
            <p class="subtitle">An institutional-grade financial analyst inside Telegram. Powered by 7-Model AI Failover, Google OAuth GSign, and Real-Time Market Data.</p>
            <a href="https://t.me/AtlasFinanceAssistantBot" target="_blank" class="cta-btn">
                <span>🤖 Open Atlas in Telegram</span>
            </a>
            <div class="grid">
                <div class="card">
                    <h3>📈 Real-Time Data</h3>
                    <p>Finnhub & Alpha Vantage quotes, 10-K filings, SEC EDGAR, & analyst targets.</p>
                </div>
                <div class="card">
                    <h3>🔑 Google OAuth GSign</h3>
                    <p>Single Sign-On for Google Calendar schedule, Gmail inbox, & Google Sheets.</p>
                </div>
                <div class="card">
                    <h3>📊 Multi-Modal Excel</h3>
                    <p>Parses Excel (.xlsx) portfolios, PDF reports, DOCX files, & CSV spreadsheets.</p>
                </div>
                <div class="card">
                    <h3>🛡️ 7-Model Failover</h3>
                    <p>Resilient AI chain across Gemini 2.0, Groq 70B, Mistral, SambaNova, & Cerebras.</p>
                </div>
            </div>
            <footer>Built & Submitted by <strong>Mohit Jain</strong></footer>
        </div>
    </body>
    </html>
    """


@app.get("/health")
async def health_check():
    return {"status": "healthy", "build": "v5.2-fix-document-extraction"}


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
