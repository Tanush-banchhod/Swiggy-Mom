# Swiggy Mom — Complete Project Guide
> For any developer, AI model, or reviewer picking this up cold.

---

## What this is

Swiggy Mom is a proactive meal ordering agent built on Swiggy's MCP (Model Context Protocol) APIs. It solves a specific, real problem: people who want to eat healthy don't fail because they lack willpower — they fail because they have to make a decision three times a day, every day, while tired or distracted. This agent removes that decision.

The user sets their goals once. The agent handles the rest. 45 minutes before lunch, it fires a notification with exactly 3 filtered, macro-scored options. User taps one. Order placed. Done.

---

## The core insight

Every food app today is a discovery app. Swiggy Mom is a decision app. That's the entire product difference.

- Discovery apps: "Here are 200 restaurants. What do you want?"
- Swiggy Mom: "Here are 3 things that fit your goals, your budget, your location right now. Pick one or skip."

The "mom" framing is intentional. Your mom doesn't ask what you want every meal. She knows you, she knows what's in the fridge, she knows you have a meeting at 2pm. That's the experience this agent replicates — but for Swiggy.

---

## Tech stack

| Layer | Technology |
|---|---|
| API server | Python 3.11, FastAPI (async) |
| Database | PostgreSQL 15 + pgvector |
| Cache / sessions | Redis |
| Job scheduling | APScheduler |
| Auth | OAuth 2.1 PKCE (Swiggy standard) |
| MCP servers | Swiggy Food, Swiggy Instamart |
| Notifications | Firebase Cloud Messaging (FCM) |
| Infra | Docker, AWS ECS + RDS + ElastiCache |
| Code quality | ruff, mypy strict, pytest |

---

## Project structure

```
swiggy-mom/
├── .cursorrules              ← full project context for AI models
├── .env.example
├── pyproject.toml
├── docker-compose.yml
│
├── app/
│   ├── main.py               ← FastAPI entrypoint
│   ├── config.py             ← pydantic-settings
│   ├── dependencies.py       ← DI: db, redis, mcp clients
│   │
│   ├── auth/
│   │   ├── oauth.py          ← OAuth 2.1 PKCE flow
│   │   ├── token_store.py    ← token refresh + Redis TTL
│   │   └── router.py         ← /auth/login, /auth/callback
│   │
│   ├── users/
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── router.py
│   │   └── service.py
│   │
│   ├── profiles/
│   │   ├── models.py         ← NutritionGoal, AllergyBlock,
│   │   │                        TasteDislike, LocationSchedule,
│   │   │                        MealWindow, LifestyleMode
│   │   ├── schemas.py
│   │   ├── router.py
│   │   └── service.py
│   │
│   ├── agent/
│   │   ├── orchestrator.py   ← main agent loop
│   │   ├── swiggy_client.py  ← all MCP tool calls live here
│   │   ├── scorer.py         ← protein-per-rupee + preference scoring
│   │   ├── filter_engine.py  ← allergy/dislike/rating/time filters
│   │   ├── suggestion_builder.py
│   │   └── skip_learner.py   ← passive preference learning
│   │
│   ├── scheduler/
│   │   ├── jobs.py
│   │   ├── meal_trigger.py   ← fires 45 min before meal window
│   │   └── daily_report.py
│   │
│   ├── notifications/
│   │   ├── fcm.py
│   │   └── templates.py
│   │
│   └── orders/
│       ├── cart_manager.py   ← always fetches fresh, never caches
│       ├── order_service.py  ← idempotency-safe place_food_order
│       └── tracker.py        ← post-order macro logging
│
├── migrations/               ← Alembic
├── tests/
└── docs/
    ├── ARCHITECTURE.md
    ├── MCP_TOOL_MAP.md
    └── ONBOARDING_FLOW.md
```

---

## Database schema

### `users`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| swiggy_user_id | TEXT | opaque, from OAuth |
| created_at | TIMESTAMP | |
| deleted_at | TIMESTAMP | soft delete |

### `nutrition_goals`
| Column | Type | Notes |
|---|---|---|
| user_id | UUID FK | |
| protein_g_daily | INT | e.g. 150 |
| calorie_ceiling | INT nullable | null = no limit |
| lifestyle_mode | ENUM | healthy_reset, muscle_gain, weight_loss, maintenance, no_restrictions |

### `allergy_blocks` — hard blocks, never suggested
| Column | Type |
|---|---|
| user_id | UUID FK |
| ingredient_name | TEXT |

### `taste_dislikes` — soft blocks, deprioritised
| Column | Type | Notes |
|---|---|---|
| user_id | UUID FK | |
| ingredient_name | TEXT | |
| skip_count | INT | auto-incremented by skip_learner |

### `location_schedule`
| Column | Type | Notes |
|---|---|---|
| user_id | UUID FK | |
| day_of_week | INT | 0=Mon, 6=Sun |
| address_id | TEXT | Swiggy address ID |
| address_label | TEXT | "Office", "Home" |

### `meal_windows`
| Column | Type | Notes |
|---|---|---|
| user_id | UUID FK | |
| meal_type | ENUM | lunch, dinner |
| target_time | TIME | e.g. 13:30 |
| notify_minutes_before | INT | default 45 |

### `meal_log`
| Column | Type | Notes |
|---|---|---|
| user_id | UUID FK | |
| order_id | TEXT | Swiggy order ID |
| restaurant_id | TEXT | |
| item_ids | TEXT[] | |
| protein_g | INT | estimated |
| calories | INT | estimated |
| cost_inr | INT | |
| ordered_at | TIMESTAMP | |
| was_suggested | BOOL | true if from agent |

### `suggestion_feedback`
| Column | Type | Notes |
|---|---|---|
| user_id | UUID FK | |
| session_id | UUID | one per notification fire |
| shown_items | JSONB | |
| chosen_item | TEXT nullable | |
| skipped_items | TEXT[] | |

---

## How the agent works

### Onboarding (one-time)

The user completes 7 configuration steps before the agent can fire:

1. **Nutrition goal** — daily protein target (grams), optional calorie ceiling
2. **Dietary identity** — Veg / Non-veg / Eggetarian / Vegan / Jain
3. **Allergy blocks** — hard-blocked ingredients (peanuts, gluten, shellfish, etc.)
4. **Taste dislikes** — soft-blocked ingredients (deprioritised, not removed)
5. **Meal schedule** — lunch time, dinner time, notification lead (default 45 min)
6. **Location schedule** — which address per day of week (e.g. office Mon/Tue/Fri)
7. **Lifestyle mode** — healthy reset / muscle gain / weight loss / maintenance / no restrictions

No other setup. The agent starts learning passively from order and skip behaviour after that.

---

### Suggestion flow (runs every meal window)

```
[APScheduler job fires at: target_time - notify_minutes_before]
                    |
                    v
         resolve_address_for_today()
         ← location_schedule lookup by day_of_week
         ← no prompt to user
                    |
                    v
         search_restaurants(addressId)        ← MCP: get_addresses + search_restaurants
                    |
         filter_engine.apply():
           - availabilityStatus == "OPEN"
           - rating >= user_min_rating (default 4.0)
           - estimated_delivery <= (notify_lead - 5 min)
           - within budget ceiling
                    |
                    v
         get_restaurant_menu() × top candidates ← MCP: get_restaurant_menu
                    |
         filter_engine.apply_item_filters():
           - hard zero if allergy_block ingredient present
           - penalty if taste_dislike ingredient present (0.3x)
                    |
                    v
         scorer.score_items():
           base  = protein_g / price_inr
           × preference_affinity  (order history weight)
           × variety_bonus        (0.5x if same restaurant last 2 meals)
           × weather_factor       (warm food bonus on cold/rainy days)
           × day_of_week_factor   (Fri = slightly relaxed, Mon = strict)
           - 0.5x if same dish ordered in last 7 days
                    |
                    v
         suggestion_builder.build_top_3():
           rank descending → pick top 3
           assign labels: "Best macro fit", "Your usual pick", "Budget pick"
                    |
                    v
         fcm.send_notification(user, suggestions)
           title: "Lunch in 45 min — 3 options ready"
           body:  "<item1> · <item2> · <item3>. Xg protein left today."
```

---

### Order placement flow (after user taps confirm)

```
[User taps confirm on suggestion N]
                    |
                    v
         get_food_cart()                       ← MCP: ALWAYS fetch fresh
         (never trust cached cart state)
                    |
                    v
         fetch_food_coupons()                  ← MCP
         filter: requiresOnlinePayment == false (COD only in v1)
         apply_food_coupon(best_valid_code)     ← MCP (optional)
                    |
                    v
         CONFIRM PROMPT (required, no silent orders):
           "Order <item> from <restaurant>?
            Total ₹XXX · COD · ~XX min"
           [Order] [Skip]
                    |
                    v
         if cart.total > 1000:
           reject, prompt user to reduce
                    |
                    v
         place_food_order(paymentMethod="COD") ← MCP
                    |
         on 5xx: wait 2-5s → get_food_orders() first
                 if order exists: treat as success
                 if not: retry place_food_order once
                    |
                    v
         track_food_order(orderId)             ← MCP (poll ≤ every 10s)
                    |
         on delivered:
           write meal_log entry
           update today's remaining macro counter
           dinner suggestion will use updated macros
```

---

## MCP tools used

| Tool | Server | When used |
|---|---|---|
| `get_addresses` | Food | resolve delivery address at suggestion time |
| `search_restaurants` | Food | find candidate restaurants |
| `get_restaurant_menu` | Food | fetch menu for scoring |
| `search_menu` | Food | targeted item search within a restaurant |
| `update_food_cart` | Food | add confirmed item to cart |
| `get_food_cart` | Food | always fetch fresh before any cart operation |
| `fetch_food_coupons` | Food | find valid COD coupons |
| `apply_food_coupon` | Food | apply best coupon |
| `place_food_order` | Food | place order (NOT idempotent — handle carefully) |
| `track_food_order` | Food | poll delivery status post-order |
| `get_food_orders` | Food | idempotency check after 5xx |
| `flush_food_cart` | Food | clear cart when user starts over |
| `your_go_to_items` | Instamart | quick reorder for grocery items (v2) |
| `search_products` | Instamart | find grocery products (v2) |
| `checkout` | Instamart | place grocery order (v2) |

---

## Agent rules (non-negotiable)

These rules are enforced in `orchestrator.py` and cannot be overridden by any user preference:

**Ordering safety**
- Never place an order without explicit user confirmation
- Always call `get_food_cart` immediately before `place_food_order`
- Never blind-retry `place_food_order` — always check `get_food_orders` first on 5xx
- Hard reject if `cart.total > ₹1000` (MCP v1 Builders Club cap)
- COD only — filter all coupons for `requiresOnlinePayment == false`

**Suggestion integrity**
- Always exactly 3 suggestions. Never fewer, never more.
- Never suggest the same restaurant used in the previous 2 meal sessions
- Never suggest the same dish ordered in the last 7 days
- Allergy blocks: absolute zero. No exceptions, no overrides, not even in cheat mode.
- Taste dislikes: soft penalty only. Can surface in slot 3 if nothing else qualifies.
- Cheat mode: suspends all lifestyle/macro filters for ONE meal only. Auto-resets.

**Notification timing**
- Always fire at `target_time - notify_minutes_before` (scheduler, not ad-hoc)
- Exclude restaurants where `estimated_delivery > (notify_lead - 5 min)`
- If no qualifying options: send "nothing qualifies right now" message, not a compromised suggestion

**Location**
- Resolve address from schedule using `day_of_week` — never ask the user
- Instamart only: `clear_cart` before any address switch mid-session

**Learning**
- Log every suggestion session passively — never ask user to rate meals
- 3 skips of the same dish in 30 days → auto-add to `taste_dislikes`

---

## API endpoints

```
POST   /auth/login                  ← initiate OAuth PKCE flow
GET    /auth/callback               ← OAuth redirect handler

GET    /profile                     ← full user profile
PUT    /profile/goals               ← nutrition goals
PUT    /profile/allergies           ← hard allergy blocks
PUT    /profile/dislikes            ← soft taste dislikes
PUT    /profile/schedule            ← location day schedule
PUT    /profile/meal-windows        ← meal times + notify lead
PUT    /profile/lifestyle           ← lifestyle mode

GET    /suggestions/now             ← manual trigger (debug/demo)

POST   /orders/confirm              ← place after user confirms
GET    /orders/history              ← meal log

GET    /reports/weekly              ← macro + spend summary

POST   /feedback/cheat-meal        ← activate cheat mode for next meal
POST   /feedback/skip               ← explicit skip signal
```

---

## Swiggy MCP v1 known limitations

Handle all of these gracefully in code — don't surface them as errors to the user:

| Limitation | Handling |
|---|---|
| COD only, no online payment | filter all coupons for `requiresOnlinePayment == false` |
| ₹1000 cart cap | hard-check before confirm prompt |
| No refresh tokens | re-run OAuth on 401, token Redis TTL = 4.9 days |
| `error.code` not populated | branch on `error.message` string + HTTP status |
| `place_food_order` not idempotent | always `get_food_orders` check on 5xx |
| Food cart is per-restaurant | warn user before switching restaurant (cart flush) |
| No scheduled delivery | agent times the order — cannot pre-schedule |
| Rate limiting: upstream shed not 429 | treat `UPSTREAM_ERROR` as retriable |

---

## Feature flags

Control phased rollout via environment variables:

```env
FEATURE_INSTAMART=false           # v1: Food only
FEATURE_WEATHER_SCORING=false     # enable when weather API wired
FEATURE_WEEKLY_REPORT=true
FEATURE_CHEAT_MODE=true
FEATURE_VARIETY_ENFORCEMENT=true
FEATURE_SKIP_LEARNING=true
```

---

## What Swiggy gets from this

This isn't just a Swiggy wrapper — it changes the ordering pattern for users in a way that benefits Swiggy commercially:

- Habit orders (2x daily) vs occasional orders
- Near-zero browse-and-abandon sessions (no discovery phase)
- Unique behavioural + nutrition signal Swiggy doesn't have from regular app usage
- Surfaces restaurants to users who would never have found them organically (scorer rewards nearby, underrated options)

---

## Loom demo script

When recording the demo for Swiggy Builders Club approval, walk through in this order:

1. **Onboarding** — show the 7 profile setup steps via Postman or a simple UI. Set protein = 150g, allergy = peanuts, meal window = 1:30pm, location = office Mon/Tue/Fri.

2. **Manual suggestion trigger** — hit `GET /suggestions/now` to skip waiting for the scheduler. Show the JSON response with 3 scored items, their labels, and the scoring breakdown.

3. **Notification preview** — show what the FCM payload looks like, or simulate the notification in terminal output.

4. **Order confirm flow** — hit `POST /orders/confirm` with suggestion #1. Walk through: `get_food_cart` → `fetch_food_coupons` → `apply_coupon` → confirm payload shown → `place_food_order` → order ID returned.

5. **Meal log** — show the `meal_log` entry created, with protein and calories recorded.

6. **Weekly report** — hit `GET /reports/weekly` and show the macro summary output.

7. **Cheat mode** — `POST /feedback/cheat-meal`, re-trigger suggestions, show health filters suspended. Then show auto-reset after next meal order.

Keep the demo under 4 minutes. Focus on the agent loop, not the infrastructure.

---

## Environment variables

```env
SWIGGY_CLIENT_ID=
SWIGGY_CLIENT_SECRET=
SWIGGY_REDIRECT_URI=http://localhost:8000/auth/callback
SWIGGY_FOOD_MCP_URL=https://mcp.swiggy.com/food
SWIGGY_INSTAMART_MCP_URL=https://mcp.swiggy.com/im

DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/swiggymom
REDIS_URL=redis://localhost:6379/0

FCM_SERVER_KEY=
WEATHER_API_KEY=

ENVIRONMENT=development
LOG_LEVEL=INFO
SENTRY_DSN=

FEATURE_INSTAMART=false
FEATURE_WEATHER_SCORING=false
FEATURE_WEEKLY_REPORT=true
FEATURE_CHEAT_MODE=true
FEATURE_VARIETY_ENFORCEMENT=true
FEATURE_SKIP_LEARNING=true
```

---

## Project status

| Module | Status |
|---|---|
| OAuth 2.1 PKCE | implemented |
| User profile + onboarding | implemented |
| APScheduler meal trigger | implemented |
| filter_engine + scorer | implemented |
| Suggestion builder | implemented |
| cart_manager + order_service | implemented |
| Idempotency handling | implemented |
| FCM notifications | in progress |
| meal_log + tracker | implemented |
| Weekly macro report | implemented |
| Instamart integration | planned (v2) |
| Weather-aware scoring | planned (v2) |
| Frontend UI | out of scope v1 (API-first) |
