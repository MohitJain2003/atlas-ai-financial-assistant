# ⚡ ATLAS AI — Next-Gen Financial Analyst inside Telegram
> *Institutional-grade market intelligence, Google Workspace OAuth Single Sign-On, and 7-Model Fallback Resiliency — right in your chat.*

👤 **DEVELOPER**: **MOHIT JAIN**  
💻 **GitHub**: https://github.com/MohitJain2003/atlas-ai-financial-assistant  
🤖 **Live Telegram Bot**: https://t.me/AtlasFinanceAssistantBot  
🌐 **Live Production Backend**: https://atlas-ai-financial-assistant-f2m5.onrender.com  
🎥 **Demo Video**: [INSERT_YOUR_DEMO_VIDEO_LINK_HERE]  

---

### 💡 THE PROBLEM VS. THE ATLAS SOLUTION

| Other Hackathon Submissions | ⚡ The Atlas Advantage |
| :--- | :--- |
| ❌ Single AI API key that rate-limits or crashes | 🛡️ **7-Model AI Fallback Chain** — zero rate-limits or downtime |
| ❌ No Google login or integration | 🔑 **OAuth 2.0 Google Single Sign-On (GSign)** for Calendar & Gmail |
| ❌ Render free-tier bots that go to sleep after 15 min | ⚡ **24/7 Self-Ping Heartbeat Engine** — zero spin-down delays |
| ❌ Text-only answers with hallucinated prices | 📊 **Live Finnhub Quotes + Excel (.xlsx) portfolio parser** |

---

### 🏆 2 UNIQUE EXCLUSIVE FEATURES (UNMATCHED IN THIS HACKATHON)

#### 1. 🔑 Native Google OAuth 2.0 Single Sign-On (GSign)
Atlas features full **Google OAuth 2.0 Single Sign-On**. With a single tap on the inline **`[🔑 Connect to Google]`** button, users authorize Atlas to:
- **Google Calendar**: View upcoming schedule, check meetings, and set calendar events.
- **Gmail Inbox**: Search emails for company announcements, meeting invites, or stock alerts.
- **Google Sheets**: Analyze shared financial spreadsheets directly inside Telegram.

#### 2. 🛡️ 7-Model AI Fallback Resiliency Chain
While other bots rely on a single API key that fails under load, Atlas operates on an automated **7-Model Failover Architecture**. If one provider hits a rate limit or goes down, Atlas switches providers instantly in milliseconds:
1. **Gemini 2.0 Flash** *(Primary Real-Time Engine)*
2. **Groq Llama 3.3 70B** *(Fast Reasoning Engine)*
3. **OpenRouter Auto** *(Universal LLM Backup)*
4. **Mistral Small** *(Financial Logic Backup)*
5. **SambaNova Llama 3.3 70B** *(Ultra-High Throughput)*
6. **Cerebras gpt-oss-120b** *(Wafer-Scale Inference)*
7. **GitHub Models** *(Safety Reserve)*

---

### 🚀 MORE SUPERPOWERS THAT SET ATLAS APART

- 📊 **Multi-Format Spreadsheet & Document Parser**: Upload any **Excel (`.xlsx`)**, **CSV**, **PDF**, or **DOCX** file. Atlas parses tables, calculates cost basis, unrealized profit/loss %, and identifies top holdings.
- ⚡ **24/7 Zero-Downtime Keep-Alive Engine**: Internal 4-minute self-ping heartbeat job keeps Render active 24/7 with zero cold starts.
- 📈 **Finnhub + SEC EDGAR Institutional Research**: Live stock prices, 52-week ranges, SEC 10-K/10-Q filings, analyst price targets, and Form 4 insider transactions.
- 🎙️ **Voice Note Intelligence**: Send voice notes in Telegram — transcribed asynchronously via **Groq Whisper (`whisper-large-v3`)**.
- 🔔 **Automated Briefings & Alerts**: Daily morning briefings delivered at 8:00 AM alongside background custom price alerts.

---

### ⚙️ DETAILED TECHNICAL SUMMARY

- **Core Architecture**: Asynchronous Python 3.12 microservice powered by **FastAPI** & **Uvicorn**, integrated with `python-telegram-bot` (v21) long-polling with custom `HTTPXRequest` network timeouts.
- **AI Intelligence & Orchestration**: Custom multi-model failover manager that dynamically handles function calling, rate-limit catching (`429`), and prompt injection across **7 AI Providers**.
- **Google OAuth 2.0 GSign Stack**: Lightweight, PKCE-free authorization flow with a dedicated FastAPI callback route (`/auth/google/callback`) for token exchange, refresh management, and direct async REST calls via `httpx`.
- **Multi-Modal Document Engine**: Openpyxl/Pandas spreadsheet parser for Excel (`.xlsx`), PyPDF for document extraction, and Groq Whisper (`whisper-large-v3`) for voice transcription.
- **Financial Market Data Pipeline**: Direct integration with **Finnhub REST API**, **Alpha Vantage**, and **SEC EDGAR** for real-time stock quotes, SEC filings (10-K/10-Q), Wall Street analyst consensus, and Form 4 insider trades.
- **Background Worker & Resilience**: **APScheduler** async scheduler executing daily morning briefings (8:00 AM), 15-minute price alert monitors, and a **4-minute self-ping heartbeat job** to keep the Render container active 24/7.
- **Database & Persistence**: Async SQLAlchemy ORM managing user profiles, watchlist state, Google tokens, and price alerts.
