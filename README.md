---
title: Ayebeg Bot
emoji: 🏠
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
app_port: 7860
---

# 🏠 Ayebeg — Telegram Marketplace Bot

**Ayebeg** (ገበያ) is an Amharic-language Telegram bot that connects **sellers, landlords, and service providers** with **buyers, renters, and service seekers** across Ethiopia. Users can post listings, browse by category and location, submit "looking for" requests, and more — all within Telegram.

> **Live Channel:** [@gebeya_mereja_266](https://t.me/gebeya_mereja_266)

---

## ✨ Features

### For Sellers / Landlords / Service Providers
- **Post listings** with description, category, city/neighborhood, price, up to 5 photos, and contact info
- **Photo watermarking** — every uploaded photo is automatically branded with `@AkerayTekerayBot`
- **Manage listings** — view, renew, or unlist your active posts
- **View seeker requests** — browse "looking for" posts from potential buyers/renters
- **Category system** — Property: 🏠 House/Land, 🚗 Vehicle, 🛋️ Furniture, 📱 Electronics, 👗 Fashion/Beauty, 📦 Other; Service: 🔧 House, 🚗 Vehicle, 📱 Electronics, 👗 Fashion/Beauty, 📦 Other
- **30-day listing expiry** for service listings (auto-expired via daily job)

### For Buyers / Renters / Service Seekers
- **Search listings** by city, neighborhood, and category with Amharic fuzzy matching
- **Browse all listings** with paginated navigation (Next ➡️ / ⬅️ Previous)
- **Submit "Looking For" requests** — describe what you need, and providers can see your request
- **Deep linking** — share individual listings via `t.me/bot?start=view_123` links

### Admin Tools
- **Approve/Reject** listings after payment verification (screenshot or transaction ID)
- **Dashboard** (`/admin`, `/stats`) — total users, active listings by type, pending approvals
- **Pending queue** (`/admin_pending`, `/pending`) — review all listings awaiting approval
- **Broadcast** (`/broadcast`) — send a message to all registered users
- **Delete listings** directly from the listing view
- **Channel auto-posting** — approved listings are automatically posted to the Telegram channel

### General
- **Mandatory channel subscription** — users must join the channel before using the bot
- **Amharic fuzzy search** — phonetically equivalent Amharic characters are normalized (e.g., ሀ/ሃ/ሐ/ሓ/ኃ/ኀ all match)
- **Input validation** — word limits (100 words) and character limits (500 chars) on descriptions; spaces and newlines between words count toward the character limit but not the word limit
- **Conversation timeout** — sessions auto-expire after 15 minutes of inactivity
- **Persistent conversations** — state is preserved via pickle persistence across bot restarts
- **Multi-photo collage** — multiple listing photos can be viewed as a collage or individually

---

## 📂 Project Structure

```
├── main.py                 # Bot logic — handlers, conversation flows, admin commands
├── database.py             # Database layer (SQLite + PostgreSQL) with fuzzy Amharic search
├── strings.py              # All Amharic UI strings and constants
├── location_options.py     # City & neighborhood data with keyboard builders
├── watermark.py            # Photo watermarking and collage generation (Pillow)
├── miniapp/
│   └── index.html          # Telegram Mini App (Web App) frontend
├── tests/
│   ├── test_full_system.py       # End-to-end system tests
│   ├── test_enhancements.py      # Feature enhancement tests
│   ├── test_word_limit.py        # Input validation tests
│   ├── test_photo_limit.py       # Photo upload limit tests
│   └── test_location_options.py  # Location data tests
├── Dockerfile              # Docker image (python:3.10-slim)
├── Procfile                # Heroku/Railway process definition
├── runtime.txt             # Python version (3.11.9)
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
└── README.md
```

---

## 🚀 Deployment

### Prerequisites
- A **Telegram Bot Token** from [@BotFather](https://t.me/BotFather)
- Your **Telegram User ID** (for admin access)
- (Optional) A **PostgreSQL** database (e.g., [Neon.tech](https://neon.tech)); SQLite is used by default

### Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `BOT_TOKEN` | ✅ | — | Telegram Bot API token |
| `ADMIN_IDS` | ✅ | — | Comma-separated Telegram User IDs for admins |
| `BOT_UPDATE_MODE` | ❌ | `webhook` | `webhook` or `polling` |
| `WEBHOOK_URL` | ❌ | Auto-detected | Public URL for webhook (without `https://` prefix) |
| `WEBHOOK_SECRET` | ❌ | — | Optional secret token for webhook verification |
| `PORT` | ❌ | `7860` | HTTP port for webhook server |
| `DB_ENGINE` | ❌ | Auto | `sqlite` or `postgres` |
| `DATABASE_URL` | ❌ | — | PostgreSQL connection string |
| `SQLITE_PATH` | ❌ | `rental_bot.db` | Path to SQLite database file |
| `CHANNEL_ID` | ❌ | — | Telegram channel ID/username for auto-posting (e.g., `@gebeya_mereja_266`) |
| `SUBSCRIPTION_CHANNEL` | ❌ | `gebeya_mereja_266` | Channel username (without `@`) for mandatory subscription check |
| `PERSISTENCE_PATH` | ❌ | `bot_data.pickle` | Path for conversation persistence file |
| `ENV` | ❌ | — | Set to `production` to disable local debug log file |

### Deploy to Railway (Recommended)

1. Connect your GitHub repository to [Railway](https://railway.app)
2. Railway auto-detects the `Dockerfile` and builds the image
3. In **Settings → Networking**, click **Generate Domain** for a public URL
4. Add the environment variables above in the Railway Dashboard
   - `WEBHOOK_URL` can be omitted — Railway sets `RAILWAY_PUBLIC_DOMAIN` automatically
   - Or set it explicitly (e.g., `your-app.up.railway.app`; `https://` and `/{BOT_TOKEN}` are added automatically)

### Deploy to Hugging Face Spaces

1. Create a new **Space** on Hugging Face
2. Select **Docker** as the SDK
3. Go to **Settings → Variables and secrets** and add your secrets

### Deploy with Docker

```bash
docker build -t akeray-tekeray .
docker run -d --env-file .env -p 7860:7860 akeray-tekeray
```

---

## 💻 Local Development

### Setup

```bash
# Clone the repository
git clone <repo-url>
cd <repo-dir>

# Create and activate virtual environment
python -m venv .venv

# Windows
.\.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your values
```

### Running

**Polling mode (recommended for local dev):**
```env
BOT_UPDATE_MODE=polling
```
> ⚠️ Do **not** use polling while production is on webhook with the same bot token — it removes the deployed webhook.

**Webhook mode (matches production):**
```env
BOT_UPDATE_MODE=webhook
WEBHOOK_URL=<your-public-url>
```
Use a tunnel (ngrok, Cloudflare Tunnel) pointing at `PORT` (default `7860`).

```bash
python main.py
```

### Database Options

**SQLite (default):**
```env
DB_ENGINE=sqlite
SQLITE_PATH=rental_bot.db
```

**PostgreSQL:**
```env
DB_ENGINE=postgres
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
```

---

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test files
python -m pytest tests/test_full_system.py -v
python -m pytest tests/test_word_limit.py -v
python -m pytest tests/test_photo_limit.py -v
python -m pytest tests/test_location_options.py -v
python -m pytest tests/test_enhancements.py -v
```

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| **Bot Framework** | `python-telegram-bot` v22.8 (async, job-queue, webhooks) |
| **Language** | Python 3.11 |
| **Database** | PostgreSQL (production) / SQLite (local dev) |
| **Image Processing** | Pillow 12.2 — watermarking & collage generation |
| **AI** | Google Gemini (`gemini-2.0-flash-exp`) via `google-generativeai` |
| **Containerization** | Docker (`python:3.10-slim`) |
| **Deployment** | Railway, Hugging Face Spaces, or any Docker host |

---

## 🤖 Bot Commands

| Command | Access | Description |
|---|---|---|
| `/start` | All | Start the bot / return to main menu |
| `/cancel` | All | Cancel the current operation |
| `/help` | All | Show usage guide (Amharic) |
| `/admin` or `/stats` | Admin | View dashboard with user/listing statistics |
| `/admin_pending` or `/pending` | Admin | Review listings pending approval |
| `/broadcast` | Admin | Send a message to all registered users |

---

## 📝 License

This project is private. All rights reserved. 

source .venv/Scripts/activate 