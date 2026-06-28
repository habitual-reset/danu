# DANU

Personal AI assistant with reliable persistent memory. Reachable via SMS and voice; designed for background value delivery (Daily Active Non-Users).

## Quick Start

```bash
cd danu
# Python 3.12 via uv (recommended)
source ~/.local/bin/env
uv python install 3.12
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -e ".[dev]"

cp .env.example .env
alembic upgrade head

uvicorn danu.main:app --reload
```

## Run Tests

```bash
pytest
```

## Twilio SMS Setup (Live Testing)

1. Add credentials to `.env`:
   ```
   TWILIO_ACCOUNT_SID=AC...
   TWILIO_AUTH_TOKEN=...
   TWILIO_PHONE_NUMBER=+1...
   ALLOWLIST_PHONES=+1YOURNUMBER
   PUBLIC_WEBHOOK_BASE_URL=https://your-tunnel-url
   ```
2. Start a tunnel to your local server (ngrok, Cloudflare Tunnel, etc.)
3. Run the API: `uvicorn danu.main:app --reload --port 8000`
4. In Twilio Console → Phone Number → Messaging, set the webhook to:
   `https://your-tunnel-url/webhooks/twilio/sms` (HTTP POST)
5. Text your Twilio number from your allowlisted phone

## Background Worker

```bash
python -m danu.tasks.worker
```

## Compliance (Twilio A2P 10DLC)

Public policy documents for carrier registration:

- [Privacy Policy](PRIVACY.md)
- [Terms of Service](TERMS.md)

After pushing to GitHub, use the raw or blob URLs in your Twilio Trust Hub / campaign registration.

## Project Layout

- `danu/memory/` — event-sourced memory store, retrieval, consolidation
- `danu/channels/` — SMS/voice adapters (Phase 2+)
- `danu/agent/` — orchestrator and LLM integration
- `danu/tasks/` — background job queue and worker