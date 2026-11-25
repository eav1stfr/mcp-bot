# Couple Bot

A private Telegram bot for two people (the owner and his girlfriend) to manage their shared lists: wishlists, movies, places and things to do. You can use slash commands, or just talk to it in plain language. An LLM (Claude) works out what you want and calls the right operation.

> **Status: design stage, no code yet.** Items marked *(proposed)* are defaults that can still change. Everything else has been decided by the owner.

## Features

| Area | What it does |
|---|---|
| **Wishlists** | Each person keeps their own wishlist, and each can see the other's. |
| **Movies** | A shared list of movies to watch. Once a movie is watched, each person can give their own grade. |
| **Places** | A shared list of places to visit. Once a place is visited, each person can give their own grade and optional short feedback. |
| **Actions** | A shared list of things to do (to-dos / bucket list), assigned to one person or to both together. |

Example messages:

- *"what is her wishlist?"*
- *"add Dune 2 to our movies"*
- *"I give Dune 2 an 8"*
- *"what places haven't we visited yet?"*

For quick reads without the LLM there are slash commands: `/wishlist`, `/movies`, `/places`, `/actions`.

Only the operations that are actually needed get built, not full CRUD for everything (see [Operations](#operations)).

**Out of scope for v1:** reminders, important dates, scheduled notifications (see [Later / ideas](#later--ideas)).

## Tech stack

| Topic | Choice |
|---|---|
| Language | Python 3.12+ |
| Telegram library | aiogram 3.x (async; the FastAPI webhook endpoint passes each update into the aiogram dispatcher) |
| Backend | FastAPI |
| Database | PostgreSQL on Neon free tier *(proposed)* |
| Hosting | Vercel Hobby (free), FastAPI as a Vercel Function, bot in **webhook mode** (no long polling) |
| LLM | Claude API, model `claude-haiku-5-5` *(proposed)*, via the official `anthropic` Python SDK behind a thin, swappable wrapper |
| Migrations | Alembic |

**LLM billing:** a Claude Pro subscription does **not** include API access. API usage is billed separately through the Claude Console (pay-as-you-go). At this scale the cost is very low (see [Cost](#llm-cost-estimate)).

## Key design decisions

- **Direct tool calling.** The bot defines the tools, the model picks one, and the bot runs it by calling the service layer directly, not over HTTP.
- **No MCP in v1.** Later the same services could be exposed as a remote MCP server and added as a custom connector in the Claude app (that works with Pro).
- **Access control:** an allowlist of exactly two Telegram user IDs. Everyone else is ignored without a reply.
- **Identity in tools:** the LLM never sees or produces raw user IDs. Person params are `"me" | "partner"` (plus `"together"` for actions); the bot resolves them from the sender. Each user record has a `partner_id`, so the bot always knows who "me" and "partner" are.
- **Destructive actions** (deletes) need explicit confirmation through Telegram inline buttons.
- **Business logic lives only in `services/`.** Tool handlers, slash commands and REST routes are thin layers over the services.

## Architecture

```
Telegram (2 users)
      │  HTTPS webhook (secret token header)
      ▼
Vercel Function: FastAPI app
  ├─ POST /telegram/webhook ─► aiogram dispatcher
  │       ├─ allowlist check
  │       ├─ slash commands ───────────────┐
  │       ├─ inline-button callbacks ──────┤
  │       └─ free text ─► agent loop ──────┤──► services/ ──► Postgres (Neon)
  │                         ▲   │          │
  │                         │   ▼          │
  │                    Claude API (tools)  │
  └─ /api/* REST routes (optional) ────────┘
```

### Serverless constraints (Vercel)

- **No long-lived process:** no polling, no in-process scheduler, no in-memory state. Chat history and pending confirmations are stored in Postgres.
- **Webhook handling:** process the update inside the request and **always return HTTP 200**, even after an internal error (a non-200 makes Telegram re-deliver the update). Deduplicate by `update_id` (table `processed_updates`).
- Verify the `X-Telegram-Bot-Api-Secret-Token` header against `TELEGRAM_WEBHOOK_SECRET`, which is set via `setWebhook(secret_token=...)`.
- Send `sendChatAction("typing")` before calling the LLM.
- Vercel Hobby allows up to 300 s per invocation. An agent turn should take a few seconds, but the loop is still capped at 5 tool iterations.
- **DB connections:** use Neon's **pooled** connection string. With SQLAlchemy async + asyncpg, use `NullPool` and `connect_args={"statement_cache_size": 0}`, because the pooler doesn't support prepared-statement caching.
- **Migrations** run locally or in CI against `DATABASE_URL`, not during the Vercel build.
- Vercel Hobby is for non-commercial personal use only, which fits this project.

### Request flow (free text)

1. A Telegram update arrives. Check the secret header, dedupe `update_id`, and drop the update if `from_user.id` is not on the allowlist.
2. Build the system prompt: sender's name, partner's name, current date (Asia/Almaty, UTC+5), and short rules (reply in the user's language, keep answers brief, confirm before deleting).
3. Load the last ~10–20 messages of `chat_history` for this chat.
4. Call Claude with the history, the new message and the tool definitions.
5. If the response is `tool_use`, resolve `me`/`partner`/`together` to user IDs, call the service, and send back a `tool_result` (compact JSON with item IDs). Loop, up to 5 iterations.
6. Once the response is plain text, send it to Telegram and save the turn to `chat_history`.
7. Delete tools don't delete anything. They create a `pending_confirmation` and the bot shows inline buttons. The callback handler does the actual delete.

## Data model

`users` is decided by the owner; the other tables follow from the functionality *(proposed)*.

```
users
  id            PK
  telegram_id   BIGINT UNIQUE NOT NULL
  name          TEXT NOT NULL
  partner_id    FK users.id NULL

wishlist_items
  id, owner_id FK users, title, link NULL, price NUMERIC NULL, note NULL,
  created_at, updated_at

movies
  id, title, year INT NULL, note NULL, added_by FK users,
  status ENUM('to_watch','watched') DEFAULT 'to_watch', watched_at NULL,
  created_at

movie_ratings
  id, movie_id FK movies ON DELETE CASCADE, user_id FK users,
  score SMALLINT CHECK (1..10), comment NULL, created_at, updated_at
  UNIQUE (movie_id, user_id)

places
  id, title, location NULL (city / address), link NULL (maps URL), note NULL,
  added_by FK users, status ENUM('want_to_visit','visited') DEFAULT 'want_to_visit',
  visited_at NULL, created_at

place_reviews
  id, place_id FK places ON DELETE CASCADE, user_id FK users,
  score SMALLINT CHECK (1..10), feedback TEXT NULL, created_at, updated_at
  UNIQUE (place_id, user_id)

actions
  id, title, note NULL, created_by FK users,
  assignee_id FK users NULL   -- NULL = do it together
  status ENUM('todo','done') DEFAULT 'todo', due_date DATE NULL, done_at NULL,
  created_at

chat_history
  id, chat_id BIGINT, role TEXT, content JSONB, created_at

pending_confirmations
  id, user_id, action TEXT, payload JSONB, expires_at

processed_updates
  update_id BIGINT PK, created_at   -- dedupe; prune rows older than a few days
```

The two `users` rows are seeded with a script or migration. There's no sign-up flow.

### Permission rules *(proposed)*

- **Wishlists:** only the owner can add, edit or delete their items. The partner can only read them.
- **Movies, places, actions:** shared. Either person can add, edit or delete.
- **Ratings and reviews:** each person can only create or change their own. Both people's ratings are visible to both.
- Rating a movie automatically sets it to `watched`; reviewing a place sets it to `visited`.

## Operations

### LLM tools *(proposed)*

| Area | Tool | Params |
|---|---|---|
| Wishlist | `get_wishlist` | `person: me\|partner` |
| | `add_wishlist_item` | `title`, `link?`, `price?`, `note?` (always the sender's own list) |
| | `update_wishlist_item` | `item_id`, `title?`, `link?`, `price?`, `note?` |
| | `delete_wishlist_item` | `item_id` (needs confirmation) |
| Movies | `list_movies` | `status?: to_watch\|watched\|all` (includes both ratings) |
| | `add_movie` | `title`, `year?`, `note?` |
| | `update_movie` | `movie_id`, `title?`, `status?`, `note?` |
| | `delete_movie` | `movie_id` (needs confirmation) |
| | `rate_movie` | `movie_id`, `score: 1-10`, `comment?` (sender's own rating) |
| Places | `list_places` | `status?: want_to_visit\|visited\|all` (includes both reviews) |
| | `add_place` | `title`, `location?`, `link?`, `note?` |
| | `update_place` | `place_id`, `title?`, `location?`, `link?`, `status?`, `note?` |
| | `delete_place` | `place_id` (needs confirmation) |
| | `review_place` | `place_id`, `score: 1-10`, `feedback?` (sender's own review) |
| Actions | `list_actions` | `status?: todo\|done\|all`, `assignee?: me\|partner\|together\|all` |
| | `add_action` | `title`, `note?`, `assignee?: me\|partner\|together` (default `together`), `due_date?` |
| | `update_action` | `action_id`, `title?`, `note?`, `assignee?`, `due_date?`, `status?` |
| | `delete_action` | `action_id` (needs confirmation) |

Tool descriptions should say when to use each tool (e.g. "use `list_movies` first to find the `movie_id` when the user refers to a movie by name").

### REST API *(proposed, optional in v1)*

Tools do **not** call the REST API. It exists for debugging, a future Telegram Mini App, or an MCP server. It's protected by `Authorization: Bearer $API_TOKEN`.

```
POST   /telegram/webhook                 (required)
GET    /health                           (required)

GET    /api/wishlist?user_id=            POST /api/wishlist
PATCH  /api/wishlist/{id}                DELETE /api/wishlist/{id}
GET    /api/movies?status=               POST /api/movies
PATCH  /api/movies/{id}                  DELETE /api/movies/{id}
PUT    /api/movies/{id}/rating           (upsert own rating)
GET    /api/places?status=               POST /api/places
PATCH  /api/places/{id}                  DELETE /api/places/{id}
PUT    /api/places/{id}/review           (upsert own review)
GET    /api/actions?status=&assignee=    POST /api/actions
PATCH  /api/actions/{id}                 DELETE /api/actions/{id}
```

## Configuration

Set these in the Vercel project settings and in a local `.env`. Never commit `.env`.

```
TELEGRAM_BOT_TOKEN=
TELEGRAM_WEBHOOK_SECRET=        # random string, also passed to setWebhook
ALLOWED_TELEGRAM_IDS=111111111,222222222
ANTHROPIC_API_KEY=              # from Claude Console (separate from Pro subscription)
LLM_MODEL=claude-haiku-5-5
DATABASE_URL=postgresql+asyncpg://...   # Neon *pooled* connection string
API_TOKEN=                      # for /api/* routes
DEFAULT_TIMEZONE=Asia/Almaty
```

## Project layout *(proposed)*

```
app/
  main.py              # FastAPI app: webhook route, /health, include /api routers
  config.py            # pydantic-settings
  bot/
    dispatcher.py      # aiogram Bot + Dispatcher setup
    middleware.py      # allowlist, user loading
    commands.py        # /start, /wishlist, /movies, /places, /actions
    callbacks.py       # inline-button confirmations
  agent/
    loop.py            # Claude tool-use loop
    tools.py           # tool schemas + dispatch (resolves me/partner/together)
    prompts.py         # system prompt builder
  services/            # wishlist.py, movies.py, places.py, actions.py
  api/                 # REST routers (optional)
  db/
    models.py          # SQLAlchemy 2.0 models
    session.py         # async engine (NullPool, pooled Neon URL)
migrations/            # Alembic
scripts/
  set_webhook.py       # calls Telegram setWebhook with URL + secret
  seed_users.py
tests/
vercel.json / pyproject.toml / requirements.txt
```

Check Vercel's current FastAPI docs for the expected entrypoint location and adjust the layout if needed.

## LLM cost estimate

Claude Haiku 5.5 costs $0.10 per million input tokens and $0.50 per million output tokens for prompts up to 100K tokens. A typical turn sends about 3–5K input tokens (system prompt + ~18 tool schemas + history) and may make 2–3 calls. That's roughly $0.001–0.002 per user message, so **about $1/month even with heavy use**. Prompt caching of the system prompt and tools can cut it further.

## Roadmap *(proposed)*

1. **Skeleton:** FastAPI + aiogram webhook on Vercel, allowlist, `/start`, Neon + Alembic, seeded users.
2. **Services + slash commands** for wishlists, movies, places, actions (no LLM).
3. **Agent loop** with read-only tools (`get_wishlist`, `list_*`).
4. **Write tools** + rating/review tools + delete confirmations.
5. **Polish:** chat-history trimming, error messages, tests for services and tool dispatch.

## Later / ideas

- **Reminders & important dates.** On Vercel Hobby, cron jobs run at most once a day, so a daily digest is possible ("today: anniversary"). Exact-time reminders would need an external pinger (e.g. a free cron service hitting a protected endpoint) or a different host.
- **MCP server:** expose `services/` as a remote MCP server and add it as a custom connector in the Claude app, so you can ask Claude itself "what's on her wishlist?" from a Pro subscription.
- Telegram Mini App for browsing lists visually.
- Movie metadata (posters, year) from TMDB. Map links for places.
- A "reserved" flag on wishlist items, hidden from the owner (surprise mode).

## Open questions

- Grade scale: 1–10 *(assumed)* or 1–5 / stars?
- Should place feedback be free text, or is a score enough?
- What exactly are "actions": shared bucket-list activities, chores, or both? Are due dates needed?
- Can the partner edit or delete items on the other person's wishlist? (Assumed: no, read-only.)
- Which language(s) will you chat in? (The system prompt tells the model to reply in the user's language.)
