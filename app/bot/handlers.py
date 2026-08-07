"""
Telegram Bot Message & Document Handlers — Natural conversational interface.
Handles: text, voice notes, documents (PDF/DOCX), and photos/images.
No slash commands, menus, or buttons — pure conversation.
"""
import os
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes
)

from app.config import settings
from app.database.repositories import UserRepository, DocumentRepository
from app.ai.engine import ai_engine
from app.services.document_analyzer import DocumentAnalyzerService, VoiceService

logger = logging.getLogger(__name__)

# Ensure upload directory exists
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


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
            welcome_text = f"Hello {tg_user.first_name or 'there'}! I'm Atlas."
            response = await ai_engine.process_message(user, welcome_text)

        await context.bot.send_message(chat_id=chat_id, text=response)

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
        # Telegram has a 4096 char limit — split if needed
        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                await context.bot.send_message(chat_id=chat_id, text=response[i:i+4000])
        else:
            await context.bot.send_message(chat_id=chat_id, text=response)

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
            )
            response = await ai_engine.process_message(user, transcript, message_type="voice")
            reply = f'🎙️ *"{transcript}"*\n\n{response}'
            await context.bot.send_message(chat_id=chat_id, text=reply, parse_mode="Markdown")
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text="I received your voice message but couldn't transcribe it clearly. Could you type that instead?"
            )

    except Exception as e:
        logger.error(f"Error in voice_handler: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=chat_id,
            text="I had trouble processing your voice message. Please try again or type your question."
        )


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo/image messages — useful for financial charts, screenshots, etc."""
    tg_user = update.effective_user
    chat_id = update.effective_chat.id

    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")

        # Get the highest-resolution photo
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()
        file_path = os.path.join(UPLOAD_DIR, f"photo_{update.message.message_id}.jpg")
        await photo_file.download_to_drive(file_path)

        caption = update.message.caption or ""

        user = await UserRepository.get_or_create_user(
            telegram_id=tg_user.id,
            first_name=tg_user.first_name,
        )

        # Build prompt based on caption context
        if caption:
            prompt = (
                f"The user has shared a financial chart/image with this caption: '{caption}'. "
                "Acknowledge you received it and respond to their caption as best you can. "
                "Note: for full chart analysis, please describe what you see in the chart in text."
            )
        else:
            prompt = (
                "The user has shared an image (likely a financial chart, stock screenshot, or document). "
                "Acknowledge you received it and ask them to describe what they need — "
                "for example: 'What ticker is this?', 'What time period?', 'What would you like to know?'"
            )

        response = await ai_engine.process_message(user, prompt, message_type="image")

        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)

        await context.bot.send_message(chat_id=chat_id, text=response)

    except Exception as e:
        logger.error(f"Error in photo_handler: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=chat_id,
            text="I received your image! For chart analysis, please describe what you're looking at or ask a specific question about it."
        )


async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle PDF and DOCX financial document uploads for AI analysis."""
    tg_user = update.effective_user
    chat_id = update.effective_chat.id
    doc = update.message.document

    filename = doc.file_name or "document"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ("pdf", "docx", "doc", "txt", "xlsx", "xls"):
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "I support PDF, Word documents, and Excel spreadsheets (.pdf, .docx, .xlsx) for analysis. "
                "Please upload a valid financial document."
            )
        )
        return

    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"📄 Received *{filename}*. Extracting and analyzing content — this may take a few seconds...",
            parse_mode="Markdown"
        )

        file_obj = await doc.get_file()
        save_path = os.path.join(UPLOAD_DIR, f"doc_{update.message.message_id}_{filename}")
        await file_obj.download_to_drive(save_path)

        user = await UserRepository.get_or_create_user(
            telegram_id=tg_user.id,
            first_name=tg_user.first_name,
        )

        extracted_text = await DocumentAnalyzerService.extract_text(save_path, ext)

        if not extracted_text:
            await context.bot.send_message(
                chat_id=chat_id,
                text="I couldn't extract readable text from this document. It may be scanned or image-based."
            )
            return

        await DocumentRepository.save_document(
            telegram_id=tg_user.id,
            user_id=user.id,
            filename=filename,
            file_type=ext,
            file_path=save_path,
            file_size=doc.file_size,
            extracted_text=extracted_text
        )

        caption = update.message.caption or "Summarize this document. Highlight key financial metrics, risks, and important takeaways."
        analysis = await DocumentAnalyzerService.analyze_document(caption, extracted_text, filename=filename)

        response = f"📄 *Analysis: {filename}*\n\n{analysis}"

        # Split long responses
        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                await context.bot.send_message(chat_id=chat_id, text=response[i:i+4000], parse_mode="Markdown")
        else:
            await context.bot.send_message(chat_id=chat_id, text=response, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error in document_handler: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=chat_id,
            text="I had trouble analyzing this document. Please try again or ensure it's a valid PDF or Word file."
        )


def create_bot_app() -> Application:
    """Create and configure the Telegram Bot Application."""
    if not settings.TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in environment variables.")

    from telegram.request import HTTPXRequest
    request = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0)

    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).request(request).build()

    # Register handlers — order matters (most specific first)
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, document_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    return app
