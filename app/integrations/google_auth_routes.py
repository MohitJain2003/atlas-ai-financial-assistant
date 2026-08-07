"""
Google OAuth FastAPI Routes — Handles the OAuth2 callback flow.
Users are redirected here after authorizing Atlas to access their Google account.
"""
import logging
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.integrations.google_services import exchange_code_for_tokens, is_google_configured
from app.database.repositories import UserRepository
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/auth/google")
async def google_auth_start(telegram_id: int):
    """Redirect user to Google OAuth consent screen."""
    if not is_google_configured():
        return HTMLResponse("""
            <html><body style="font-family:sans-serif;padding:40px;text-align:center">
            <h2>⚠️ Google integration not configured</h2>
            <p>Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to your .env file.</p>
            </body></html>
        """)

    from app.integrations.google_services import get_auth_url
    auth_url = get_auth_url(telegram_id)
    return HTMLResponse(f"""
        <html><body style="font-family:sans-serif;padding:40px;text-align:center;background:#0f0f23;color:white">
        <h2 style="color:#4ade80">🔗 Atlas — Connect Google Account</h2>
        <p>Click the button below to grant Atlas access to your Google Calendar, Gmail, and Sheets.</p>
        <a href="{auth_url}" style="display:inline-block;margin-top:20px;padding:14px 28px;background:#4285F4;color:white;border-radius:8px;text-decoration:none;font-weight:bold;font-size:16px">
            🔑 Connect with Google
        </a>
        <p style="margin-top:20px;color:#999;font-size:12px">
            Atlas only reads data — it never modifies your emails or deletes calendar events.
        </p>
        </body></html>
    """)


@router.get("/auth/google/callback")
async def google_auth_callback(request: Request, code: str = None, state: str = None, error: str = None):
    """Handle Google OAuth2 callback after user authorization."""
    if error:
        return HTMLResponse(f"""
            <html><body style="font-family:sans-serif;padding:40px;text-align:center">
            <h2>❌ Authorization Failed</h2>
            <p>Error: {error}</p>
            <p>Please try connecting again from Telegram.</p>
            </body></html>
        """)

    if not code or not state:
        return HTMLResponse("<html><body><h2>❌ Invalid callback — missing code or state.</h2></body></html>")

    try:
        telegram_id = int(state)
        from app.integrations.google_services import exchange_code_for_tokens_async
        token_data, error_detail = await exchange_code_for_tokens_async(code, state, authorization_response=str(request.url))

        if not token_data:
            return HTMLResponse(f"""
                <html><body style="font-family:sans-serif;padding:40px;text-align:center;background:#0f0f23;color:white">
                <h2 style="color:#ef4444">❌ Google Token Exchange Error</h2>
                <p style="color:#f87171;font-family:monospace;background:#1e1e38;padding:12px;border-radius:8px;max-width:800px;margin:20px auto;word-break:break-all">{error_detail}</p>
                <p style="color:#999;font-size:14px">Please return to Telegram and click <b>Connect Google</b> to try again with a fresh session.</p>
                </body></html>
            """)

        # Save tokens to user record in database
        await UserRepository.update_user(telegram_id, google_tokens=token_data)

        # Send confirmation in Telegram
        if settings.TELEGRAM_BOT_TOKEN:
            try:
                from telegram import Bot
                from telegram.request import HTTPXRequest
                request_obj = HTTPXRequest(connect_timeout=15.0, read_timeout=15.0)
                bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, request=request_obj)
                await bot.send_message(
                    chat_id=telegram_id,
                    text=(
                        "✅ *Google Account Connected!*\n\n"
                        "I can now access your:\n"
                        "📅 *Google Calendar* — view upcoming events, create meetings\n"
                        "📧 *Gmail* — search and summarize emails about companies\n"
                        "📊 *Google Sheets* — analyze your financial spreadsheets\n\n"
                        "Just ask me naturally — e.g. _'What meetings do I have this week?'_ "
                        "or _'Search my emails about Tesla'_"
                    ),
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Failed to send Telegram confirmation: {e}")

        return HTMLResponse("""
            <html><body style="font-family:sans-serif;padding:40px;text-align:center;background:#0f0f23;color:white">
            <h2 style="color:#4ade80">✅ Google Account Connected!</h2>
            <p>You can now close this tab and return to Telegram.</p>
            <p style="color:#999">Atlas has access to your Calendar, Gmail, and Sheets.</p>
            </body></html>
        """)

    except Exception as e:
        logger.error(f"OAuth callback error: {e}", exc_info=True)
        return HTMLResponse(f"""
            <html><body style="font-family:sans-serif;padding:40px;text-align:center">
            <h2>❌ Something went wrong</h2>
            <p>{str(e)}</p>
            <p>Please try again from Telegram.</p>
            </body></html>
        """)
