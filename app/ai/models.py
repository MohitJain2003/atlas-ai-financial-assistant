"""
AI Models - Multi-model fallback chain for resilient AI responses.
Supports: Gemini (free) -> Groq (free) -> OpenAI (paid fallback)
"""
import logging
import json
from typing import Optional

import google.generativeai as genai
from groq import AsyncGroq
from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)


# Tool definitions for function calling
FINANCIAL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_price",
            "description": "Get the current stock price, change, and key metrics for a given ticker symbol. Use this when the user asks about a stock price, how a stock is doing, or stock performance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol (e.g., AAPL, MSFT, GOOGL, TSLA)"
                    }
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_company_profile",
            "description": "Get detailed company profile including business description, sector, market cap, and key fundamentals. Use this when the user asks about a company overview or wants to research a company.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol"
                    }
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_company_news",
            "description": "Get the latest news articles about a specific company. Use when the user asks about news or recent developments for a company.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of news articles to return (default 5)",
                        "default": 5
                    }
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_news",
            "description": "Get the latest general market and financial news. Use when the user asks about market news, what's happening in the market, or general financial news.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "News category: general, forex, crypto, merger",
                        "default": "general"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of articles to return",
                        "default": 5
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_companies",
            "description": "Compare two or more companies on key financial metrics. Use when the user asks to compare companies or stocks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tickers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of ticker symbols to compare (e.g., ['AAPL', 'MSFT'])"
                    }
                },
                "required": ["tickers"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_stock",
            "description": "Search for a stock ticker symbol by company name. Use when the user mentions a company name but not the ticker.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Company name or partial name to search for"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_overview",
            "description": "Get an overview of major market indices (S&P 500, NASDAQ, DOW). Use when the user asks about the overall market, market performance, or how the market is doing.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_earnings",
            "description": "Get earnings data for a company, including upcoming earnings date and historical EPS vs estimates. Use when user asks about earnings, earnings report, earnings calendar, or EPS.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol (e.g., AAPL, MSFT)"
                    }
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sec_filings",
            "description": "Get recent SEC filings (10-K annual reports, 10-Q quarterly reports, 8-K current reports) for a company from SEC EDGAR. Use when user asks about SEC filings, annual reports, 10-K, 10-Q, or regulatory filings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol"
                    },
                    "form_type": {
                        "type": "string",
                        "description": "Optional: filter by form type, e.g. '10-K', '10-Q', '8-K'. Leave empty for all recent filings."
                    }
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_price_alert",
            "description": "Create a price or volatility alert for a stock. Use when user says 'alert me when', 'notify me if', 'track this stock', 'tell me if price goes above/below'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol to monitor"
                    },
                    "alert_type": {
                        "type": "string",
                        "description": "Type of alert: 'price_above', 'price_below', or 'percent_change'"
                    },
                    "condition_value": {
                        "type": "string",
                        "description": "The price target or percentage threshold (as a number, e.g. '200' for $200, '5' for 5%)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Human readable description of the alert"
                    }
                },
                "required": ["ticker", "alert_type", "condition_value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_watchlist",
            "description": "Add a stock ticker symbol to the user's saved watchlist. Use when user says 'add NVDA to my watchlist', 'track TSLA', 'follow AAPL'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol to add (e.g. NVDA, TSLA, AAPL)"
                    }
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_watchlist",
            "description": "Get the user's current saved stock watchlist with live prices. Use when user says 'show my watchlist', 'what am I tracking', 'my watchlist', 'view my watchlist'.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_analyst_ratings",
            "description": "Get analyst consensus ratings, price targets, and recent upgrades/downgrades for a stock. Use when user asks about analyst ratings, buy/sell recommendations, price targets, or upgrades.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol"
                    }
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_insider_transactions",
            "description": "Get recent insider buying and selling activity for a stock from SEC Form 4 filings. Use when user asks about insider trading, insider buying/selling, or executive transactions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol"
                    }
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_economic_calendar",
            "description": "Get upcoming high-impact economic events such as FOMC meetings, CPI releases, jobs report (NFP), GDP, and other macro events. Use when user asks about economic events, macro calendar, or upcoming economic data.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_earnings_calendar",
            "description": "Get upcoming earnings report dates for a company or the broad market. Use when user asks when a company reports earnings, upcoming earnings this week, or earnings schedule.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Optional: specific stock ticker to check earnings date for. Leave empty for broad market earnings calendar."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_google_calendar",
            "description": "Get the user's upcoming Google Calendar events. Use when user asks about their schedule, upcoming meetings, 'what do I have this week', or wants to plan around meetings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Number of days ahead to fetch events (default 7)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_calendar_event",
            "description": "Create a calendar event or meeting in the user's Google Calendar. Use when user asks to schedule a meeting, set a reminder, or block time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "Title of the event"
                    },
                    "start_datetime": {
                        "type": "string",
                        "description": "Start datetime in ISO format, e.g. 2024-08-07T10:00:00"
                    },
                    "end_datetime": {
                        "type": "string",
                        "description": "End datetime in ISO format, e.g. 2024-08-07T11:00:00"
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional event description or agenda"
                    }
                },
                "required": ["summary", "start_datetime", "end_datetime"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_gmail",
            "description": "Search the user's Gmail inbox for emails about a company, topic, or person. Use when user asks to search emails, find conversations about a company, or check email threads.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Gmail search query, e.g. 'Tesla earnings', 'from:investor-relations', 'subject:quarterly report'"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of emails to return (default 5)"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_event_reminder",
            "description": "Set a reminder for an upcoming event like earnings, FOMC, CPI report, or any financial event. User can say 'remind me 1 hour before Apple earnings' or 'remind me on earnings day for Tesla'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol (e.g. AAPL, TSLA). Leave empty for macro events like FOMC."
                    },
                    "event_description": {
                        "type": "string",
                        "description": "Description of the event (e.g. 'Q3 earnings call', 'FOMC meeting', 'CPI release')"
                    },
                    "event_date": {
                        "type": "string",
                        "description": "Date of the event in YYYY-MM-DD format"
                    },
                    "advance_minutes": {
                        "type": "integer",
                        "description": "How many minutes before the event to send the reminder. 60 = 1 hour before, 1440 = 1 day before. Default: 60"
                    }
                },
                "required": ["event_description", "event_date"]
            }
        }
    },
]


# Convert tools to Gemini format
GEMINI_TOOLS = []
for tool in FINANCIAL_TOOLS:
    func = tool["function"]
    props = {}
    for k, v in func["parameters"].get("properties", {}).items():
        if v.get("type") == "array":
            props[k] = genai.protos.Schema(
                type=genai.protos.Type.ARRAY,
                description=v.get("description", ""),
                items=genai.protos.Schema(type=genai.protos.Type.STRING)
            )
        elif v.get("type") == "integer":
            props[k] = genai.protos.Schema(
                type=genai.protos.Type.INTEGER,
                description=v.get("description", "")
            )
        else:
            props[k] = genai.protos.Schema(
                type=genai.protos.Type.STRING,
                description=v.get("description", "")
            )

    GEMINI_TOOLS.append(genai.protos.Tool(
        function_declarations=[
            genai.protos.FunctionDeclaration(
                name=func["name"],
                description=func["description"],
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties=props,
                    required=func["parameters"].get("required", []),
                )
            )
        ]
    ))


class AIModelChain:
    """Multi-model fallback chain for resilient AI responses."""

    def __init__(self):
        self.models = []
        self._init_models()

    def _init_models(self):
        """Initialize available models based on API keys."""
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.models.append("gemini")
            logger.info("✅ Gemini model initialized")

        if settings.GROQ_API_KEY:
            self.groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
            self.models.append("groq")
            logger.info("✅ Groq model initialized")

        if settings.OPENAI_API_KEY:
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self.models.append("openai")
            logger.info("✅ OpenAI model initialized")

        if settings.GITHUB_API_KEY:
            self.github_client = AsyncOpenAI(
                api_key=settings.GITHUB_API_KEY,
                base_url="https://models.inference.ai.azure.com"
            )
            self.models.append("github")
            logger.info("✅ GitHub Models initialized")

        if settings.OPENROUTER_API_KEY:
            self.openrouter_client = AsyncOpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1"
            )
            self.models.append("openrouter")
            logger.info("✅ OpenRouter model initialized")

        if settings.MISTRAL_API_KEY:
            self.mistral_client = AsyncOpenAI(
                api_key=settings.MISTRAL_API_KEY,
                base_url="https://api.mistral.ai/v1"
            )
            self.models.append("mistral")
            logger.info("✅ Mistral model initialized")

        if settings.SAMBANOVA_API_KEY:
            self.sambanova_client = AsyncOpenAI(
                api_key=settings.SAMBANOVA_API_KEY,
                base_url="https://api.sambanova.ai/v1"
            )
            self.models.append("sambanova")
            logger.info("✅ SambaNova model initialized")

        if settings.CEREBRAS_API_KEY:
            self.cerebras_client = AsyncOpenAI(
                api_key=settings.CEREBRAS_API_KEY,
                base_url="https://api.cerebras.ai/v1"
            )
            self.models.append("cerebras")
            logger.info("✅ Cerebras model initialized")

        if not self.models:
            logger.error("❌ No AI models configured! Add at least one API key.")

    async def generate(self, system_prompt: str, user_message: str,
                       tool_handler=None) -> str:
        """Generate a response using the fallback chain."""
        for model_name in self.models:
            try:
                if model_name == "gemini":
                    return await self._generate_gemini(system_prompt, user_message, tool_handler)
                elif model_name == "groq":
                    return await self._generate_groq(system_prompt, user_message, tool_handler)
                elif model_name == "openai":
                    return await self._generate_openai(system_prompt, user_message, tool_handler)
                elif model_name == "github":
                    return await self._generate_github(system_prompt, user_message, tool_handler)
                elif model_name == "openrouter":
                    return await self._generate_openrouter(system_prompt, user_message, tool_handler)
                elif model_name == "mistral":
                    return await self._generate_mistral(system_prompt, user_message, tool_handler)
                elif model_name == "sambanova":
                    return await self._generate_sambanova(system_prompt, user_message, tool_handler)
                elif model_name == "cerebras":
                    return await self._generate_cerebras(system_prompt, user_message, tool_handler)
            except Exception as e:
                logger.warning(f"⚠️ {model_name} failed: {e}. Trying next model...")
                continue

        return "I'm having trouble connecting to my AI services right now. Please try again in a moment. 🔄"

    async def _generate_gemini(self, system_prompt: str, user_message: str,
                                tool_handler=None) -> str:
        """Generate response using Google Gemini."""
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=system_prompt,
            tools=GEMINI_TOOLS if tool_handler else None,
        )

        chat = model.start_chat()
        response = await chat.send_message_async(
            user_message,
            generation_config=genai.GenerationConfig(
                temperature=0.7,
                max_output_tokens=2000,
            ),
        )

        # Handle function calls
        if tool_handler and response.candidates:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        fc = part.function_call
                        tool_name = fc.name
                        tool_args = dict(fc.args) if fc.args else {}

                        logger.info(f"🔧 Gemini calling tool: {tool_name}({tool_args})")
                        tool_result = await tool_handler(tool_name, tool_args)

                        # Send function response back into chat
                        response2 = await chat.send_message_async(
                            {
                                "role": "function",
                                "parts": [{
                                    "function_response": {
                                        "name": tool_name,
                                        "response": {"result": json.dumps(tool_result)}
                                    }
                                }]
                            }
                        )
                        return response2.text

        return response.text

    async def _generate_groq(self, system_prompt: str, user_message: str,
                              tool_handler=None) -> str:
        """Generate response using Groq (Llama)."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        response = await self.groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            tools=FINANCIAL_TOOLS if tool_handler else None,
            temperature=0.7,
            max_tokens=2000,
        )

        choice = response.choices[0]

        # Handle tool calls
        if tool_handler and choice.message.tool_calls:
            tool_results = []
            for tc in choice.message.tool_calls:
                tool_name = tc.function.name
                tool_args = json.loads(tc.function.arguments)
                logger.info(f"🔧 Groq calling tool: {tool_name}({tool_args})")
                result = await tool_handler(tool_name, tool_args)
                tool_results.append({
                    "tool_call_id": tc.id,
                    "role": "tool",
                    "content": json.dumps(result),
                })

            # Send results back for final response
            messages.append(choice.message)
            messages.extend(tool_results)
            response2 = await self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
            )
            return response2.choices[0].message.content

        return choice.message.content

    async def _generate_openai(self, system_prompt: str, user_message: str,
                                tool_handler=None) -> str:
        """Generate response using OpenAI."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        response = await self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=FINANCIAL_TOOLS if tool_handler else None,
            temperature=0.7,
            max_tokens=2000,
        )

        choice = response.choices[0]

        # Handle tool calls
        if tool_handler and choice.message.tool_calls:
            tool_results = []
            for tc in choice.message.tool_calls:
                tool_name = tc.function.name
                tool_args = json.loads(tc.function.arguments)
                logger.info(f"🔧 OpenAI calling tool: {tool_name}({tool_args})")
                result = await tool_handler(tool_name, tool_args)
                tool_results.append({
                    "tool_call_id": tc.id,
                    "role": "tool",
                    "content": json.dumps(result),
                })

            messages.append(choice.message)
            messages.extend(tool_results)
            response2 = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
            )
            return response2.choices[0].message.content

        return choice.message.content

    async def _generate_github(self, system_prompt: str, user_message: str,
                               tool_handler=None) -> str:
        """Generate response using GitHub Models (OpenAI-compatible via Azure inference)."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        response = await self.github_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=FINANCIAL_TOOLS if tool_handler else None,
            temperature=0.7,
            max_tokens=2000,
        )

        choice = response.choices[0]

        # Handle tool calls
        if tool_handler and choice.message.tool_calls:
            tool_results = []
            for tc in choice.message.tool_calls:
                import json as _json
                tool_name = tc.function.name
                tool_args = _json.loads(tc.function.arguments)
                logger.info(f"🔧 GitHub Models calling tool: {tool_name}({tool_args})")
                result = await tool_handler(tool_name, tool_args)
                tool_results.append({
                    "tool_call_id": tc.id,
                    "role": "tool",
                    "content": _json.dumps(result),
                })

            messages.append(choice.message)
            messages.extend(tool_results)
            response2 = await self.github_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
            )
            return response2.choices[0].message.content

        return choice.message.content

    async def _generate_openrouter(self, system_prompt: str, user_message: str,
                                   tool_handler=None) -> str:
        """Generate response using OpenRouter."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        response = await self.openrouter_client.chat.completions.create(
            model="openrouter/auto",
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
        )

        return response.choices[0].message.content

    async def _generate_mistral(self, system_prompt: str, user_message: str,
                                tool_handler=None) -> str:
        """Generate response using Mistral AI."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        response = await self.mistral_client.chat.completions.create(
            model="mistral-small-latest",
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
        )
        return response.choices[0].message.content

    async def _generate_sambanova(self, system_prompt: str, user_message: str,
                                  tool_handler=None) -> str:
        """Generate response using SambaNova Cloud."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        response = await self.sambanova_client.chat.completions.create(
            model="Meta-Llama-3.3-70B-Instruct",
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
        )
        return response.choices[0].message.content

    async def _generate_cerebras(self, system_prompt: str, user_message: str,
                                 tool_handler=None) -> str:
        """Generate response using Cerebras Cloud."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        response = await self.cerebras_client.chat.completions.create(
            model="gpt-oss-120b",
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
        )
        return response.choices[0].message.content

    async def transcribe_voice(self, audio_file_path: str) -> str:
        """Transcribe voice message using Groq Whisper."""
        if "groq" in self.models:
            try:
                with open(audio_file_path, "rb") as audio:
                    transcription = await self.groq_client.audio.transcriptions.create(
                        file=("audio.ogg", audio),
                        model="whisper-large-v3",
                        language="en",
                    )
                return transcription.text
            except Exception as e:
                logger.error(f"Voice transcription failed: {e}")

        return None


# Global model chain instance
model_chain = AIModelChain()
