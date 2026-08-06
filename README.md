# Atlas AI Financial Assistant 📈🤖

An AI-powered Financial Assistant built inside Telegram for finance professionals, analysts, founders, and investors.

> **Live Bot Username**: [@AtlasFinanceAssistantBot](https://t.me/AtlasFinanceAssistantBot)

---

## 🎯 Overview & Product Philosophy

Finance professionals spend hours every day context-switching between terminals, filings, news feeds, spreadsheets, and messaging apps. **Atlas** simplifies this workflow by acting as an experienced financial analyst available 24/7 inside Telegram through natural conversation.

### Design Principles:
- **Natural Conversation First**: No slash commands, inline buttons, or rigid menus.
- **Proactive Intelligence**: Delivers morning briefings and price alerts without being asked.
- **Why It Matters**: Explains the financial significance behind stock movements and news.
- **Multi-Modal Support**: Accepts text, voice notes (transcribed via Whisper), and PDF/DOCX financial documents.
- **Resilient AI Chain**: Powered by a 6-provider fallback chain (Gemini, Groq, OpenRouter, Mistral, SambaNova, Cerebras).

---

## ✨ Features & Capabilities

### 1. Conversational Onboarding
- Natural 5-step onboarding flow (Role → Sectors → Watchlist → Preferences → Briefing Time).
- Gradually builds user context over time. Users can skip any step anytime.

### 2. Live Market & Stock Intelligence
- Real-time stock prices, intraday changes, highs/lows, and market caps.
- Company fundamental research (P/E ratios, sector data, dividend yields).
- Multi-company comparison tool.
- Market overview (S&P 500, Nasdaq, Dow Jones).

### 3. Proactive Intelligence & Daily Briefings
- Automated morning market briefings tailored to user watchlist and role.
- Background price alert monitoring (triggers on target prices or % swings).
- Smart silence logic (avoids spamming when no meaningful events occur).

### 4. Financial Document Analysis
- Upload PDF or Word (.docx) annual reports, earnings presentations, or decks.
- Extracts financial metrics, key takeaways, and answers natural language questions about the document.

### 5. Voice Message Intelligence
- Send voice notes directly in Telegram.
- Transcribed asynchronously with Groq Whisper (`whisper-large-v3`) and processed by the AI engine.

---

## 🏗️ Architecture & Technology Stack

```
[ Telegram User ]
       │
       ▼ (Text / Voice / Document)
[ python-telegram-bot (v21) ]
       │
       ▼
[ FastAPI Backend (Python 3.12) ]
       │
       ├──► [ AI Engine & Tool Orchestrator ]
       │          │
       │          ├──► Function Calling (Stock Prices, Profiles, News)
       │          └──► Multi-Model Fallback Chain:
       │                1. Gemini 2.5 Flash
       │                2. Groq Llama 3.3 70B
       │                3. OpenRouter Auto
       │                4. Mistral Small
       │                5. SambaNova Llama 3.3 70B
       │                6. Cerebras gpt-oss-120b
       │
       ├──► [ Async SQLite Database (SQLAlchemy) ] (Users, Memory, Alerts, Docs)
       │
       └──► [ APScheduler Background Jobs ] (Morning Briefings, Price Alerts)
```

---

## 📁 Repository Structure

```
atlas-financial-assistant/
├── main.py                       # FastAPI entry point & bot polling runner
├── requirements.txt              # Dependencies
├── .env                          # Configuration & API keys
├── .env.example                  # Environment template
├── pyrightconfig.json            # VS Code Pyright configuration
│
├── app/
│   ├── config.py                 # Central settings & env loader
│   ├── bot/
│   │   └── handlers.py           # Telegram text, voice & document handlers
│   ├── ai/
│   │   ├── engine.py             # Main AI orchestrator & onboarding
│   │   ├── models.py             # Multi-model fallback chain & tool definitions
│   │   ├── memory.py             # Conversation history & context builder
│   │   └── prompts.py            # Financial analyst system prompts
│   ├── services/
│   │   ├── market_data.py        # Stock prices, profiles, comparisons
│   │   ├── news.py               # Financial news API integration
│   │   ├── daily_briefing.py     # Personalised morning briefing generator
│   │   └── document_analyzer.py  # PDF/DOCX parser & Voice Whisper transcriber
│   ├── database/
│   │   ├── connection.py         # Async SQLite engine
│   │   ├── models.py             # User, Conversation, Alert, Document ORM
│   │   └── repositories.py       # Data access layer
│   └── scheduler/
│       └── jobs.py               # APScheduler background jobs
```

---

## 🚀 Quick Start & Installation

### Prerequisites
- Python 3.11+
- Virtual environment (`venv`)

### Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd atlas-financial-assistant
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
   Copy `.env.example` to `.env` and fill in your keys:
   ```env
   TELEGRAM_BOT_TOKEN=8798953054:AAEaJbmcvCT1wxrwRQDFl3zD5MS-2-7u0i4
   GEMINI_API_KEY=your_gemini_key
   GROQ_API_KEY=your_groq_key
   OPENROUTER_API_KEY=your_openrouter_key
   MISTRAL_API_KEY=your_mistral_key
   SAMBANOVA_API_KEY=your_sambanova_key
   CEREBRAS_API_KEY=your_cerebras_key
   ```

5. **Run the Application**:
   ```bash
   python main.py
   ```

---

## 🛡️ License

Built for the **Atlas AI Financial Assistant Hackathon**.
