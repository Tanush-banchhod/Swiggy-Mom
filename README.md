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

## Onboarding flow (7 steps)

```bash
BASE=http://localhost:8000
TOKEN=<your jwt from /auth/callback>

# 1. Nutrition goal
curl -X PUT $BASE/profile/goals \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"protein_g_daily": 150, "calorie_ceiling": 2000, "lifestyle_mode": "muscle_gain", "dietary_identity": "non_veg"}'

# 2. Allergy blocks
curl -X PUT $BASE/profile/allergies \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"ingredients": ["peanuts", "shellfish"]}'

# 3. Taste dislikes
curl -X PUT $BASE/profile/dislikes \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"ingredients": ["bitter gourd", "capsicum"]}'

# 4. Meal schedule (which Swiggy address per day)
curl -X PUT $BASE/profile/schedule \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"schedule": [{"day_of_week": 0, "address_id": "addr_office", "address_label": "Office"}, {"day_of_week": 6, "address_id": "addr_home", "address_label": "Home"}]}'

# 5. Meal windows
curl -X PUT $BASE/profile/meal-windows \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"windows": [{"meal_type": "lunch", "target_time": "13:30", "notify_minutes_before": 45}, {"meal_type": "dinner", "target_time": "20:00", "notify_minutes_before": 45}]}'
```

---

## Loom demo script (Swiggy Builders Club application)

Walk through in this order, keep under 4 minutes:

1. **`GET /health`** — show the server is running
2. **`GET /profile`** — show empty profile, explain 7 onboarding steps
3. **Profile setup** — run the 5 curl commands above (Postman works better on camera)
4. **`GET /suggestions/now`** — show the full JSON: 3 ranked suggestions with scoring breakdown, labels ("Best macro fit" etc.), and FCM notification payload
5. **`POST /orders/confirm`** — show the preview: restaurant, items, total, COD, delivery estimate
6. **`POST /orders/place`** — walk through get_food_cart → fetch_food_coupons → apply → place (explain idempotency check)
7. **`GET /reports/weekly`** — show the macro summary structure
8. **`POST /feedback/cheat-meal`** → re-run `/suggestions/now` → show health filters suspended

---

## Applying for Swiggy MCP access

1. Record the Loom demo (steps above)
2. Go to [mcp.swiggy.com/access](https://mcp.swiggy.com/access)
3. Fill in:
   - **Integration name**: Swiggy Mom
   - **Redirect URIs**: `http://localhost:8000/auth/callback` (staging), `https://yourdomain.com/auth/callback` (prod)
   - **Servers requested**: `food` (Instamart in v2)
   - **Expected volume**: ~2 suggestions/user/day, ~1 order/user/day
   - **Use case**: Proactive meal ordering agent. User sets goals once; agent handles suggestions, scoring, and order placement. 45-min pre-meal push notification with 3 macro-filtered options. Tap → order.
4. Email your Loom to builders@swiggy.in if the form doesn't have a video field

---

## Agent rules (non-negotiable)

- Never place an order without explicit user confirmation
- Always call `get_food_cart` immediately before `place_food_order`
- Never blind-retry `place_food_order` — always check `get_food_orders` first on 5xx
- Hard reject if `cart.total > ₹1000`
- COD only — filter all coupons for `requiresOnlinePayment == false`
- Allergy blocks: absolute zero, no exceptions
- Always exactly 3 suggestions — never fewer, never more

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
