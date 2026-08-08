# Atlas AI Financial Assistant 📈🤖

An AI-powered Financial Analyst built inside Telegram for finance professionals, analysts, founders, and investors.

> **Live Telegram Bot**: [@AtlasFinanceAssistantBot](https://t.me/AtlasFinanceAssistantBot)  
> **Live Web Backend**: [https://atlas-ai-financial-assistant-f2m5.onrender.com](https://atlas-ai-financial-assistant-f2m5.onrender.com)

---

## 🎯 Overview & Product Philosophy

Finance professionals spend hours every day context-switching between terminals, SEC filings, market feeds, spreadsheets, and messaging apps. **Atlas** simplifies this workflow by acting as an experienced financial analyst available 24/7 inside Telegram through natural conversation.

### Design Principles:
- **Natural Conversation First**: No clunky slash commands or rigid menus required.
- **Proactive Intelligence**: Delivers automated morning market briefings, price alerts, and event reminders.
- **Context Over Raw Data**: Answers *"what does this mean?"* alongside real-time figures.
- **Multi-Modal Support**: Accepts text, voice notes (transcribed via Groq Whisper), and PDF, DOCX, XLSX, and CSV documents.
- **Google Workspace Integration**: Seamlessly syncs Google Calendar, Gmail, and Google Sheets via OAuth 2.0.
- **Resilient AI Chain**: Powered by a 6-provider fallback chain (Gemini 2.0, Groq Llama 3.3 70B, OpenRouter, Mistral, SambaNova, Cerebras).
- **24/7 Uptime**: Equipped with an internal self-ping heartbeat job to keep Render active 24/7.

---

## ✨ Features & Capabilities

### 1. Conversational Onboarding
- Smooth 4-step onboarding flow (Role → Sectors → Watchlist → Morning Briefing Time).
- Built-in parenthetical guidance `(e.g., tech, finance, crypto)` for effortless responses.
- Allows skipping any step anytime by typing `skip` or asking a direct stock question.

### 2. Live Market Data & Fundamental Research
- Real-time stock prices, intraday changes, 52-week ranges, and open/high/low quotes via **Finnhub** & **Alpha Vantage**.
- Fundamental company profiles (P/E ratios, profit margins, market caps, dividend yields).
- Multi-company comparison tool (`AAPL vs MSFT`).
- Global market overview (S&P 500, Nasdaq, Dow Jones).

### 3. SEC Filings & Institutional Research
- **SEC EDGAR Integration**: Instant access to 10-K annual reports, 10-Q quarterly reports, and 8-K material events.
- **Analyst Ratings**: Wall Street consensus targets (Buy/Hold/Sell breakdowns, target price ranges).
- **Insider Transactions**: Form 4 executive buy/sell tracking.
- **Earnings & Economic Calendars**: FOMC, CPI, NFP schedules & upcoming corporate earnings dates.

### 4. 🔑 Google Workspace Integration (OAuth 2.0)
- **Google Calendar**: View upcoming schedule, check meetings, and create calendar events naturally.
- **Gmail Integration**: Search inbox for company news, meeting invites, or stock alerts.
- **Google Sheets**: Analyze spreadsheets directly inside Telegram.
- Clean **`[🔑 Connect to Google]`** inline keyboard button for authorization.

### 5. 📄 Multi-Format Document & Spreadsheet Analysis
- Upload **PDF**, **Word (.docx)**, **Excel (.xlsx)**, **CSV**, or **TXT** files directly in Telegram.
- Parses financial tables, calculates cost basis, unrealized profit/loss %, and highlights top-performing assets.

### 6. 🎙️ Voice Message Intelligence
- Send Telegram voice notes recorded on your phone or desktop.
- Transcribed asynchronously with Groq Whisper (`whisper-large-v3`) and processed by the AI engine.

### 7. 🔔 Proactive Daily Briefings & Alerts
- Personalized morning market briefings delivered daily at the user's preferred time (e.g. 8:00 AM).
- Custom price alerts (`Alert me if NVDA drops below $110`).
- Event reminders (`Remind me 1hr before Apple earnings`).

---

## 🏗️ Architecture & Technology Stack

```
[ Telegram User ]
       │
       ▼ (Text / Voice / Document)
[ python-telegram-bot (v21) ] ── (Long Polling + HTTPX Timeouts)
       │
       ▼
[ FastAPI Backend (Python 3.12) ]
       │
       ├──► [ AI Engine & Tool Orchestrator ]
       │          │
       │          ├──► Real-Time Market Tools (Finnhub API, Alpha Vantage, SEC EDGAR)
       │          ├──► Google Services (Google Calendar API, Gmail API, Sheets API)
       │          └──► Multi-Model Fallback Chain:
       │                1. Gemini 2.0 Flash
       │                2. Groq Llama 3.3 70B
       │                3. OpenRouter Auto
       │                4. Mistral Small
       │                5. SambaNova Llama 3.3 70B
       │                6. Cerebras gpt-oss-120b
       │
       ├──► [ Async Database (SQLAlchemy) ] (Users, Google Tokens, Watchlists, Alerts)
       │
       └──► [ APScheduler Background Jobs ] 
                  ├──► Daily Morning Briefings
                  ├──► Price Alert Monitoring (Every 15 min)
                  └──► 24/7 Self-Ping Keep-Alive Heartbeat (Every 4 min)
```

---

## 📁 Repository Structure

```
atlas-financial-assistant/
├── main.py                       # FastAPI entry point & Telegram bot polling runner
├── requirements.txt              # Production dependencies
├── .env                          # Configuration & API credentials
├── .env.example                  # Environment template
│
├── app/
│   ├── config.py                 # Central settings & env variable loader
│   ├── bot/
│   │   └── handlers.py           # Telegram text, voice, document, & button handlers
│   ├── ai/
│   │   ├── engine.py             # Main AI engine, onboarding router, & tool execution
│   │   ├── models.py             # Multi-model fallback chain & tool schemas
│   │   ├── memory.py             # Conversation history & context builder
│   │   └── prompts.py            # Financial analyst system prompts & onboarding state
│   ├── integrations/
│   │   ├── google_services.py    # Google OAuth 2.0 PKCE-free flow, Calendar, Gmail APIs
│   │   └── google_auth_routes.py # FastAPI callback endpoint for Google OAuth
│   ├── services/
│   │   ├── market_data.py        # Stock quotes, company profiles, market overview
│   │   ├── finnhub_extended.py   # SEC EDGAR, analyst ratings, insider transactions, calendars
│   │   ├── news.py               # Financial news API integration
│   │   ├── daily_briefing.py     # Personalized morning briefing generator
│   │   └── document_analyzer.py  # PDF, DOCX, XLSX, CSV parser & Groq Whisper transcriber
│   ├── database/
│   │   ├── connection.py         # Async SQLite / PostgreSQL engine
│   │   ├── models.py             # User, Alert, Document ORM schemas
│   │   └── repositories.py       # Data access layer
│   └── scheduler/
│       └── jobs.py               # APScheduler background jobs & 4-min self-ping keep-alive
```

---

## 🚀 Quick Start & Installation

### Prerequisites
- Python 3.11+
- Virtual environment (`venv`)

### Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone https://github.com/MohitJain2003/atlas-ai-financial-assistant.git
   cd atlas-ai-financial-assistant
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   # Linux/macOS:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   Create a `.env` file from `.env.example` and set your credentials:
   ```env
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   FINNHUB_API_KEY=your_finnhub_key
   GROQ_API_KEY=your_groq_key
   GEMINI_API_KEY=your_gemini_key
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   GOOGLE_REDIRECT_URI=https://atlas-ai-financial-assistant-f2m5.onrender.com/auth/google/callback
   ```

5. **Run the Application Locally**:
   ```bash
   python main.py
   ```

---

## 🛡️ License

Built for the **Atlas AI Financial Assistant Hackathon**.
