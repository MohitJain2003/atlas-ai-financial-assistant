import asyncio
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from groq import AsyncGroq
from openai import AsyncOpenAI
from app.config import settings


async def main():
    print("Testing Groq API key...")
    try:
        g = AsyncGroq(api_key=settings.GROQ_API_KEY)
        r1 = await g.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "Say hello in 3 words"}]
        )
        print("✅ Groq Success:", r1.choices[0].message.content.strip())
    except Exception as e:
        print("❌ Groq Error:", e)

    print("\nTesting OpenRouter API key...")
    try:
        o = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1"
        )
        r2 = await o.chat.completions.create(
            model="openrouter/auto",
            messages=[{"role": "user", "content": "Say hello in 3 words"}]
        )
        print("✅ OpenRouter Success:", r2.choices[0].message.content.strip())
    except Exception as e:
        print("❌ OpenRouter Error:", e)

    print("\nTesting Mistral API key...")
    try:
        m = AsyncOpenAI(
            api_key=settings.MISTRAL_API_KEY,
            base_url="https://api.mistral.ai/v1"
        )
        r3 = await m.chat.completions.create(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": "Say hello in 3 words"}]
        )
        print("✅ Mistral Success:", r3.choices[0].message.content.strip())
    except Exception as e:
        print("❌ Mistral Error:", e)

    print("\nTesting GitHub Models API key...")
    try:
        gh = AsyncOpenAI(
            api_key=settings.GITHUB_API_KEY,
            base_url="https://models.inference.ai.azure.com"
        )
        r4 = await gh.chat.completions.create(
            model="Meta-Llama-3.1-405B-Instruct",
            messages=[{"role": "user", "content": "Say hello in 3 words"}]
        )
        print("✅ GitHub Models Success:", r4.choices[0].message.content.strip())
    except Exception as e:
        print("❌ GitHub Models Error:", e)

    print("\nTesting SambaNova API key...")
    try:
        sn = AsyncOpenAI(
            api_key=settings.SAMBANOVA_API_KEY,
            base_url="https://api.sambanova.ai/v1"
        )
        r5 = await sn.chat.completions.create(
            model="Meta-Llama-3.3-70B-Instruct",
            messages=[{"role": "user", "content": "Say hello in 3 words"}]
        )
        print("✅ SambaNova Success:", r5.choices[0].message.content.strip())
    except Exception as e:
        print("❌ SambaNova Error:", e)

    print("\nTesting Cerebras API key...")
    try:
        cb = AsyncOpenAI(
            api_key=settings.CEREBRAS_API_KEY,
            base_url="https://api.cerebras.ai/v1"
        )
        models = await cb.models.list()
        print("Cerebras Models:", [m.id for m in models.data])
        r6 = await cb.chat.completions.create(
            model=models.data[0].id,
            messages=[{"role": "user", "content": "Say hello in 3 words"}]
        )
        print("✅ Cerebras Success:", r6.choices[0].message.content.strip())
    except Exception as e:
        print("❌ Cerebras Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
