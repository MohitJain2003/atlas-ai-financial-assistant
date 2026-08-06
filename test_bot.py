import asyncio
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import telegram
from app.config import settings


from telegram.request import HTTPXRequest

async def main():
    request = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0)
    bot = telegram.Bot(token=settings.TELEGRAM_BOT_TOKEN, request=request)
    me = await bot.get_me()
    print("✅ TELEGRAM BOT CONNECTED SUCCESSFULLY!")
    print(f"🤖 Bot Name: {me.first_name}")
    print(f"🔗 Bot Username: @{me.username}")
    print(f"🆔 Bot ID: {me.id}")

if __name__ == "__main__":
    asyncio.run(main())
