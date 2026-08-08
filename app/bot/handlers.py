"""
Telegram Bot Message & Document Handlers — Natural conversational interface.
Handles: text, voice notes, documents (PDF/DOCX/XLSX), and photos/images.
No slash commands, menus, or buttons — pure conversation.
"""
import os
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes
)
from telegram.constants import ParseMode

from app.config import settings
from app.database.repositories import UserRepository, DocumentRepository
from app.ai.engine import ai_engine
from app.services.document_analyzer import DocumentAnalyzerService, VoiceService

logger = logging.getLogger(__name__)

# Ensure upload directory exists
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def _send(context, chat_id: int, text: str):
    """Send a message with Markdown formatting, fallback to plain text on parse error.
    Auto-converts **double asterisks** to *single* since Telegram only supports single.
    """
    import re
    # Strip raw LLM function calling tags if any model outputs them as text
    text = re.sub(r'<function=.*?>.*?</function>', '', text)
    text = re.sub(r'<function=.*?>', '', text)
    text = re.sub(r'</function>', '', text)
    text = re.sub(r'<tool_call>.*?</tool_call>', '', text)

    # Convert **bold** → *bold* (Telegram Markdown uses single asterisk)
    text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)
    # Remove markdown headers (# Title → Title)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # Strip LLM web grounding citation numbers (e.g. now239 → now, account2 → account, messages.19 → messages.)
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'(?<=[a-zA-Z\.])\d{1,4}\b', '', text)

    # Ensure concluding follow-up questions always have a blank line gap before them for easy readability
    text = re.sub(
        r'([\.!\)])\s+((?:Would you|Do you|Should I|Want me|Shall we|Let me|How would|What else|Is there|Can I|Shall I)\b[^\n]*\?)',
        r'\1\n\n\2',
        text
    )

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    # Detect Google Auth URL in text, extract URL, and attach clean InlineKeyboardButton
    reply_markup = None
    auth_match = re.search(r'\[AUTH_LINK:(https?://[^\s\]]+)\]', text) or re.search(r'(https?://[^\s\)]+/auth/google\?telegram_id=\d+)', text)
    if auth_match:
        auth_url = auth_match.group(1)
        keyboard = [[InlineKeyboardButton("🔑 Connect to Google", url=auth_url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        # Strip out raw URL placeholder or link strings from body text
        text = re.sub(r'\[AUTH_LINK:.*?\]', '', text)
        text = re.sub(r'https?://[^\s\)]+/auth/google\?telegram_id=\d+', '', text)
        text = text.strip()

    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for idx, chunk in enumerate(chunks):
        # Attach button to final chunk
        chunk_markup = reply_markup if idx == len(chunks) - 1 else None
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=chunk,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=chunk_markup,
            )
        except Exception:
            # Fallback: strip all markdown symbols and send plain text
            plain = re.sub(r'[*_`\[\]]', '', chunk)
            await context.bot.send_message(
                chat_id=chat_id,
                text=plain,
                reply_markup=chunk_markup,
            )


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start — welcome new users OR greet returning users without resetting their profile."""
    tg_user = update.effective_user
    chat_id = update.effective_chat.id

    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")

        user = await UserRepository.get_or_create_user(
            telegram_id=tg_user.id,
            first_name=tg_user.first_name,
            last_name=tg_user.last_name,
            username=tg_user.username,
        )

        if user.is_onboarded:
            # Returning user — don't restart onboarding, just greet them
            name = tg_user.first_name or "there"
            response = await ai_engine.process_message(
                user,
                f"[SYSTEM: Returning user {name} just opened the bot with /start. "
                f"Greet them warmly in 1-2 sentences, remind them what you can do, "
                f"and ask what they'd like to know today. Do NOT ask about their role or restart onboarding.]"
            )
        else:
            # New user — start onboarding
            name = tg_user.first_name or "there"
            welcome_text = (
                f"[SYSTEM: New user {name} sent /start. Greet them warmly as {name}! "
                f"Introduce yourself as Atlas — their AI financial analyst on Telegram. "
                f"Format your response into 3 distinct sections separated by blank line gaps:\n"
                f"1. Warm intro + bulleted capabilities (Live market quotes, Earnings & SEC filings, Price alerts & Daily briefs, Voice notes & PDF document Q&A — no slash commands needed).\n"
                f"2. Separate line after a blank line gap: '💡 To sync your Google Calendar, Gmail, and Sheets, just say **connect google** anytime!'\n"
                f"3. Separate line after a blank line gap: 'What best describes your primary role (Investor, Analyst, Founder, Trader, Student), or what stocks/markets are you watching today?']"
            )
            response = await ai_engine.process_message(user, welcome_text)

        await _send(context, chat_id, response)

    except Exception as e:
        logger.error(f"Error in start_handler: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "Welcome to Atlas! 👋 I'm your AI Financial Assistant.\n\n"
                "Ask me anything about stocks, markets, earnings, SEC filings, "
                "or send a voice note / PDF document for analysis."
            )
        )
async def reset_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/reset — wipe all user data and start fresh (developer testing only)."""
    tg_user = update.effective_user
    chat_id = update.effective_chat.id
    try:
        await UserRepository.reset_user(tg_user.id)
        await context.bot.send_message(
            chat_id=chat_id,
            text="🔄 All your data has been reset. Send /start to begin as a new user!"
        )
    except Exception as e:
        logger.error(f"Error in reset_handler: {e}", exc_info=True)
        await context.bot.send_message(chat_id=chat_id, text="Reset failed. Try again.")



async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all text messages with full AI conversation and tool calling."""
    tg_user = update.effective_user
    chat_id = update.effective_chat.id
    text = update.message.text.strip() if update.message and update.message.text else ""

    if not text:
        return

    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")

        user = await UserRepository.get_or_create_user(
            telegram_id=tg_user.id,
            first_name=tg_user.first_name,
            last_name=tg_user.last_name,
            username=tg_user.username,
        )

        response = await ai_engine.process_message(user, text)
        await _send(context, chat_id, response)

    except Exception as e:
        logger.error(f"Error in text_handler: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=chat_id,
            text="I ran into a temporary issue. Please try again in a moment! 🔄"
        )


async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice notes — transcribe via Groq Whisper and process as text."""
    tg_user = update.effective_user
    chat_id = update.effective_chat.id

    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")

        voice_file = await update.message.voice.get_file()
        file_path = os.path.join(UPLOAD_DIR, f"voice_{update.message.message_id}.ogg")
        await voice_file.download_to_drive(file_path)

        transcript = await VoiceService.process_voice_message(file_path)

        if os.path.exists(file_path):
            os.remove(file_path)

        if transcript and not transcript.startswith("Sorry"):
            user = await UserRepository.get_or_create_user(
                telegram_id=tg_user.id,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
                username=tg_user.username,
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🎤 _Transcribed:_ {transcript}",
                parse_mode=ParseMode.MARKDOWN,
            )
            response = await ai_engine.process_message(user, transcript, message_type="voice")
            await _send(context, chat_id, response)
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text="Sorry, I couldn't transcribe that voice note. Could you type your question instead?"
            )

    except Exception as e:
        logger.error(f"Error in voice_handler: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=chat_id,
            text="I had trouble processing that voice note. Please try again! 🎤"
        )


async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded documents — PDF, DOCX, XLSX analysis."""
    tg_user = update.effective_user
    chat_id = update.effective_chat.id

    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")

        doc = update.message.document
        if not doc:
            return

        file_name = doc.file_name or "document"
        file_ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""

        supported = ["pdf", "docx", "doc", "xlsx", "xls", "txt", "csv"]
        if file_ext not in supported:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"I can analyze PDF, DOCX, XLSX, and TXT files. Got a {file_ext.upper()} — not supported yet."
            )
            return

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"📄 Got it! Analyzing *{file_name}*...",
            parse_mode=ParseMode.MARKDOWN,
        )

        doc_file = await doc.get_file()
        file_path = os.path.join(UPLOAD_DIR, f"doc_{update.message.message_id}_{file_name}")
        await doc_file.download_to_drive(file_path)

        analyzer = DocumentAnalyzerService()
        analysis = await analyzer.analyze_document(file_path, file_name)

        if os.path.exists(file_path):
            os.remove(file_path)

        user = await UserRepository.get_or_create_user(
            telegram_id=tg_user.id,
            first_name=tg_user.first_name,
            last_name=tg_user.last_name,
            username=tg_user.username,
        )

        # Build prompt with extracted content
        caption = update.message.caption or ""
        prompt = (
            f"The user uploaded a document: '{file_name}'\n\n"
            f"Extracted content:\n{analysis.get('text', '')[:3000]}\n\n"
            f"User's question/note: {caption or 'Please analyze and give key financial insights.'}"
        )

        response = await ai_engine.process_message(user, prompt, message_type="document")
        await _send(context, chat_id, response)

    except Exception as e:
        logger.error(f"Error in document_handler: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=chat_id,
            text="I had trouble reading that document. Please try again or use PDF/DOCX format."
        )


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photos — typically charts or screenshots for analysis."""
    tg_user = update.effective_user
    chat_id = update.effective_chat.id

    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")

        caption = update.message.caption or "Please analyze this chart or image."

        user = await UserRepository.get_or_create_user(
            telegram_id=tg_user.id,
            first_name=tg_user.first_name,
            last_name=tg_user.last_name,
            username=tg_user.username,
        )

        prompt = f"The user sent an image with note: '{caption}'. Acknowledge you received it and provide relevant financial context or ask what specific analysis they need."
        response = await ai_engine.process_message(user, prompt, message_type="image")
        await _send(context, chat_id, response)

    except Exception as e:
        logger.error(f"Error in photo_handler: {e}", exc_info=True)


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log uncaught errors and send friendly message to user if update exists."""
    logger.error(f"Uncaught Telegram Error: {context.error}", exc_info=context.error)
    if isinstance(update, Update) and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="I encountered a brief glitch processing that request. Please try again! 🔄"
            )
        except Exception:
            pass


def register_handlers(app: Application):
    """Register all message handlers with the Telegram application."""
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("reset", reset_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, document_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_error_handler(global_error_handler)
    logger.info("✅ All Telegram handlers & error handler registered")


def create_bot_app() -> Application:
    """Build and return the Telegram Application with robust HTTP timeouts & error handlers."""
    from telegram.request import HTTPXRequest
    request_obj = HTTPXRequest(
        connect_timeout=20.0,
        read_timeout=20.0,
        write_timeout=20.0,
        pool_timeout=20.0,
    )
    app = (
        Application.builder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .request(request_obj)
        .build()
    )
    register_handlers(app)
    return app
