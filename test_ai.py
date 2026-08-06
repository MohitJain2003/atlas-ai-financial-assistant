import asyncio
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.database.connection import init_db
from app.ai.engine import ai_engine
from app.database.repositories import UserRepository


async def main():
    await init_db()
    user = await UserRepository.get_or_create_user(telegram_id=12345, first_name="FinanceUser")
    await UserRepository.update_user(12345, is_onboarded=True)
    
    # Reload user
    user = await UserRepository.get_user(12345)
    
    print("Testing AI Engine query...")
    response = await ai_engine.process_message(user, "What is the stock price of Apple (AAPL)?")
    print("\n--- AI RESPONSE ---")
    print(response)

if __name__ == "__main__":
    asyncio.run(main())
