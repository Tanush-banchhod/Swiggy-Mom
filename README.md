# Swiggy Mom

> Proactive meal ordering agent built on Swiggy's MCP APIs.

Your mom doesn't ask what you want every meal. She knows you, she knows your schedule, and she knows you have a meeting at 2pm. Swiggy Mom does the same — 45 minutes before lunch, it fires 3 macro-scored options. Tap one. Order placed.

---

## What this does

- **Proactive, not reactive** — fires suggestions at your meal time, not when you open the app
- **Macro-aware** — scores dishes by protein-per-rupee against your daily goal
- **Learns passively** — skip a dish 3 times → auto-blocked. No ratings to fill out.
- **Safe by default** — never places an order without explicit confirmation. COD only. ₹1000 cap.

---

## Tech stack

| Layer | Technology |
|---|---|
| API | Python 3.11, FastAPI async |
| Database | PostgreSQL 15 |
| Cache/sessions | Redis |
| Scheduler | APScheduler |
| Auth | OAuth 2.1 PKCE (Swiggy standard) |
| MCP servers | Swiggy Food, Swiggy Instamart (v2) |

---

## Quick start (local)

### Prerequisites
- Docker + Docker Compose
- Python 3.11+

### 1. Clone and configure

```bash
git clone https://github.com/your-org/swiggy-mom
cd swiggy-mom
cp .env.example .env
# Edit .env — add SWIGGY_CLIENT_ID and SWIGGY_CLIENT_SECRET when you get them
```

### 2. Start infrastructure

```bash
docker-compose up db redis -d
```

### 3. Install and run

```bash
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

API is live at `http://localhost:8000`
Interactive docs: `http://localhost:8000/docs`

### 4. Try the demo endpoint (no credentials needed)

```bash
curl http://localhost:8000/suggestions/now | jq
```

This runs the full suggestion pipeline with mock data — shows scoring breakdown, labels, notification payload.

---

## API reference

```
GET  /health                    ← liveness check

POST /auth/login                ← initiate OAuth PKCE (redirects to Swiggy)
GET  /auth/callback             ← OAuth redirect handler

GET  /users/me                  ← current user info

GET  /profile                   ← full profile + onboarding status
PUT  /profile/goals             ← nutrition goals (protein, calories, lifestyle)
PUT  /profile/allergies         ← hard ingredient blocks (peanuts, gluten…)
PUT  /profile/dislikes          ← soft ingredient dislikes
PUT  /profile/schedule          ← location per day of week (Home/Office)
PUT  /profile/meal-windows      ← lunch + dinner times, notify lead
PUT  /profile/lifestyle         ← lifestyle mode

GET  /suggestions/now           ← manual trigger (demo / debug)

POST /orders/confirm            ← preview order (returns confirm prompt)
POST /orders/place              ← place after user confirms
GET  /orders/history            ← meal log

GET  /reports/weekly            ← macro + spend summary

POST /feedback/cheat-meal       ← suspend macro filters for ONE meal
POST /feedback/skip             ← explicit skip signal
```

---

## Project status

| Module | Status |
|---|---|
| OAuth 2.1 PKCE | ✅ implemented |
| User profile + onboarding | ✅ implemented |
| APScheduler meal trigger | ✅ implemented |
| filter_engine + scorer | ✅ implemented |
| Suggestion builder | ✅ implemented |
| cart_manager + order_service | ✅ implemented |
| Idempotency handling | ✅ implemented |
| meal_log + tracker | ✅ implemented |
| Weekly macro report | ✅ implemented |
| FCM notifications | 🔄 in progress |
| Instamart integration | 📋 planned (v2) |
| Weather-aware scoring | 📋 planned (v2) |
