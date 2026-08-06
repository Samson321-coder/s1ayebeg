---
title: Akeray Tekeray Bot
emoji: 🏠
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
app_port: 7860
---

# Akeray Tekeray Telegram Bot

This is a Telegram rental bot designed to run on deployment platforms like **Railway** or **Hugging Face Spaces** using Docker, and it connects to a SQLite or PostgreSQL database (e.g., Neon.tech).

## Deployment Instructions

### 1. Setup Database
- **SQLite (Default)**: Automatically used if no external database is provided.
- **PostgreSQL**: Create a project at [neon.tech](https://neon.tech) and get your connection string (e.g., `postgres://user:password@host/dbname?sslmode=require`).

### 2. Configure Environment Variables
Whether deploying to **Railway** or **Hugging Face**, configure the following environment variables (Secrets):
- `BOT_TOKEN`: Your Telegram Bot API token.
- `ADMIN_IDS`: Comma-separated list of your Telegram User IDs.
- `BOT_UPDATE_MODE`: `webhook` (recommended for Railway) or `polling`.
- `WEBHOOK_URL`: Optional on Railway if you enable a public domain; otherwise set it explicitly to your app URL.
- `WEBHOOK_SECRET`: Optional Telegram webhook `secret_token`.
- `DATABASE_URL`: Your PostgreSQL connection string (optional; SQLite is used by default).
- `DB_ENGINE`: Set to `sqlite` or `postgres`.
- `SQLITE_PATH`: Optional for SQLite, defaults to `rental_bot.db`.
- `CHANNEL_ID`: Optional Telegram channel ID for posting.
- `SUBSCRIPTION_CHANNEL`: Optional subscription channel username without `@`.
- `PERSISTENCE_PATH`: Optional persistence file for conversation state.

### 3. Deploy to Railway (Recommended)
- Connect your GitHub repository to Railway.
- Railway will automatically detect the `Dockerfile` and `PORT`.
- In **Settings → Networking**, click **Generate Domain** so the service has a public URL.
- Add the Environment Variables above in the Railway Dashboard.
  - `WEBHOOK_URL` can be omitted if a public domain is enabled — Railway sets `RAILWAY_PUBLIC_DOMAIN` and the bot uses it automatically.
  - Or set `WEBHOOK_URL` explicitly to your Railway URL (e.g. `your-app.up.railway.app`; `https://` and `/{BOT_TOKEN}` are added automatically).

### 4. Deploy to Hugging Face Space
- Create a new **Space** on Hugging Face.
- Select **Docker** as the SDK.
- Go to **Settings > Variables and secrets** and add your secrets.

## Local Development

Copy `.env.example` to `.env` and fill in the values.

**Webhook (default, matches production):** set `BOT_UPDATE_MODE=webhook` and `WEBHOOK_URL` to your public HTTPS origin (on Railway/HF this is your app URL; locally use a tunnel such as ngrok or Cloudflare Tunnel pointing at `PORT`, default `7860`).

**Polling (local alternative):** set `BOT_UPDATE_MODE=polling` and leave `WEBHOOK_URL` empty. Do not use polling with the same bot token while production is on webhook—it removes the deployed webhook.

```bash
# Create and activate virtual environment (Windows)
python -m venv .venv
.\.venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# Run the bot
python main.py
``` 

### Database Options for Local Dev
**SQLite (default)**:
```env
DB_ENGINE=sqlite
SQLITE_PATH=rental_bot.db
```

**PostgreSQL**:
```env
DB_ENGINE=postgres
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
```

## Tech Stack
- **Bot Framework**: `python-telegram-bot` (v20+)
- **Database**: PostgreSQL / SQLite 
- **AI**: Google Gemini (gemini-2.0-flash-exp)
- **Image Processing**: Pillow (Watermarking)

source .venv/Scripts/activate  