# Couple Bot

A private Telegram bot for two people (the owner and his girlfriend) to manage their shared lists: wishlists, movies, places and date ideas. You can use slash commands, or just talk to it in plain language. An LLM (Claude) works out what you want and calls the right operation.

> **Status:** phase 1 (backend: FastAPI + Postgres + REST API) is done. Phase 2 (Telegram bot) and phase 3 (Claude agent) are not built yet; the sections about them describe the plan. Items marked *(proposed)* can still change.

| Phase | Scope | State |
|---|---|---|
| 1. Backend | Scaffold, tables, services, REST API | ✅ done |
| 2. Telegram bot | aiogram webhook, slash commands, bot tables (`chat_history`, `pending_confirmations`, `processed_updates`), Vercel deploy | planned |
| 3. Agent | Claude tool-use loop over the phase 1 services, delete confirmations | planned |

## Features

| Area | What it does |
|---|---|
| **Wishlists** | Each person keeps their own wishlist, and each can see the other's. |
| **Movies** | A shared list of movies to watch. Once a movie is watched, each person can give their own grade. |
| **Places** | A shared list of places to visit. Once a place is visited, each person can give their own grade and optional short feedback. |
| **Actions** | A shared list of **date ideas**: things to do together, optionally tagged indoor/outdoor and cheap/medium/expensive. An idea is just marked done; there's no assignee, due date or review. |

Example messages (phase 3):

- *"what is her wishlist?"*
- *"add Dune 2 to our movies"*
- *"I give Dune 2 an 8"*
- *"what places haven't we visited yet?"*
- *"we want to be outside and have no money, any ideas?"*

For quick reads without the LLM there will be slash commands: `/wishlist`, `/movies`, `/places`, `/actions`.

Only the operations that are actually needed get built, not full CRUD for everything (see [Operations](#operations)).

**Out of scope for v1:** reminders, important dates, scheduled notifications (see [Later / ideas](#later--ideas)).

## Tech stack

| Topic | Choice |
|---|---|
| Language | Python 3.12+ |
| Tooling | uv (dependencies, `uv.lock`), mise (Python version, tasks), ruff (`select = ["ALL"]`) |
| Backend | FastAPI, plain `def` routes |
| Database | PostgreSQL 17: docker compose locally, Neon free tier in production *(proposed)* |
| ORM | **Sync SQLModel** (SQLAlchemy 2.1) with the **psycopg 3** driver |
| Migrations | Alembic, run by hand or in CI |
| Telegram library | aiogram 3.x (phase 2; the FastAPI webhook endpoint passes each update into the aiogram dispatcher, and async handlers call the sync services through `run_in_threadpool`) |
| Hosting | Vercel Hobby (free), FastAPI as a Vercel Function, bot in **webhook mode** (no long polling) |
| LLM | Claude API, model `claude-haiku-5-5` *(proposed)*, via the official `anthropic` Python SDK behind a thin, swappable wrapper (phase 3) |

**LLM billing:** a Claude Pro subscription does **not** include API access. API usage is billed separately through the Claude Console (pay-as-you-go). At this scale the cost is very low (see [Cost](#llm-cost-estimate)).

## Key design decisions

- **Layering:** router → service → repository → database. Business logic lives only in the services; REST routes, slash commands and LLM tool handlers are thin layers over them.
- **Direct tool calling.** The bot defines the tools, the model picks one, and the bot runs it by calling the services directly, not over HTTP.
- **No MCP in v1.** Later the same services could be exposed as a remote MCP server and added as a custom connector in the Claude app (that works with Pro).
- **No auth tokens; the `users` table is the allowlist.** Only two people use the app. A REST request names its user with the `X-Telegram-User-Id` header, and an unknown ID gets 401. The bot will check the sender the same way, ignoring everyone else without a reply.
- **Identity is relative.** Services take the acting user plus `me` / `partner`, never raw user IDs from input, so the REST API and the LLM tools mean the same thing. Each user record has a `partner_id`, so the app always knows who "me" and "partner" are.
- **Destructive actions** (deletes) will need explicit confirmation through Telegram inline buttons when done through the bot.

## Architecture

```
Telegram (2 users)
      │  HTTPS webhook (secret token header)             (phase 2)
      ▼
Vercel Function: FastAPI app
  ├─ POST /telegram/webhook ─► aiogram dispatcher         (phase 2)
  │       ├─ allowlist check (users table)
  │       ├─ slash commands ───────────────┐
  │       ├─ inline-button callbacks ──────┤
  │       └─ free text ─► agent loop ──────┤──► services ──► repositories ──► Postgres (Neon)
  │                         ▲   │          │
  │                         │   ▼          │
  │                    Claude API (tools)  │              (phase 3)
  └─ /api/* REST routes ───────────────────┘              (phase 1, done)
```

### Serverless constraints (Vercel)

- **No long-lived process:** no polling, no in-process scheduler, no in-memory state. Chat history and pending confirmations will be stored in Postgres.
- **Webhook handling:** process the update inside the request and **always return HTTP 200**, even after an internal error (a non-200 makes Telegram re-deliver the update). Deduplicate by `update_id` (table `processed_updates`).
- Verify the `X-Telegram-Bot-Api-Secret-Token` header against `TELEGRAM_WEBHOOK_SECRET`, which is set via `setWebhook(secret_token=...)`.
- Send `sendChatAction("typing")` before calling the LLM.
- Vercel Hobby allows up to 300 s per invocation. An agent turn should take a few seconds, but the loop is still capped at 5 tool iterations.
- **DB connections:** use Neon's **pooled** connection string. The engine uses `NullPool` and `connect_args={"prepare_threshold": None}`, which turns off psycopg's automatic prepared statements because the transaction-mode pooler doesn't support them.
- **Migrations** run locally or in CI against `DATABASE_URL`, not during the Vercel build or on startup (`RUN_MIGRATIONS_UPON_LAUNCH` is off by default).
- Vercel Hobby is for non-commercial personal use only, which fits this project.

### Request flow (free text, phase 3)

1. A Telegram update arrives. Check the secret header, dedupe `update_id`, and drop the update if `from_user.id` is not in `users`.
2. Build the system prompt: sender's name, partner's name, current date (Asia/Almaty, UTC+5), and short rules (reply in the user's language, keep answers brief, confirm before deleting).
3. Load the last ~10–20 messages of `chat_history` for this chat.
4. Call Claude with the history, the new message and the tool definitions.
5. If the response is `tool_use`, call the service as the sender (resolving `me` / `partner`), and send back a `tool_result` (compact JSON with item IDs). Errors go back as a `tool_result` with `is_error: true` instead of crashing the loop. Loop, up to 5 iterations.
6. Once the response is plain text, send it to Telegram and save the turn to `chat_history`.
7. Delete tools don't delete anything. They create a `pending_confirmation` and the bot shows inline buttons. The callback handler does the actual delete.

## Data model

Built in phase 1:

```
users
  id PK, telegram_id BIGINT UNIQUE NOT NULL, name,
  partner_id FK users NULL (SET NULL), created_at

wishlist_items
  id, owner_id FK users (CASCADE), title, link NULL, price NUMERIC NULL,
  note NULL, created_at, updated_at

movies
  id, title, year INT NULL, note NULL, added_by FK users NULL (SET NULL),
  status ENUM('to_watch','watched') DEFAULT 'to_watch', watched_at NULL,
  created_at

movie_ratings
  id, movie_id FK movies (CASCADE), user_id FK users (CASCADE),
  score SMALLINT CHECK (1..10), comment NULL, created_at, updated_at
  UNIQUE (movie_id, user_id)

places
  id, title, location NULL (city / address), link NULL (maps URL), note NULL,
  added_by FK users NULL (SET NULL),
  status ENUM('want_to_visit','visited') DEFAULT 'want_to_visit',
  visited_at NULL, created_at

place_reviews
  id, place_id FK places (CASCADE), user_id FK users (CASCADE),
  score SMALLINT CHECK (1..10), feedback TEXT NULL, created_at, updated_at
  UNIQUE (place_id, user_id)

actions                                  -- date ideas
  id, title, note NULL, created_by FK users NULL (SET NULL),
  setting ENUM('indoor','outdoor') NULL,
  price ENUM('cheap','medium','expensive') NULL,
  status ENUM('todo','done') DEFAULT 'todo', done_at NULL, created_at
```

Postgres enums store the member names (`TO_WATCH`); the API speaks the values (`to_watch`).

Coming with the bot in phase 2 *(proposed)*:

```
chat_history
  id, chat_id BIGINT, role TEXT, content JSONB, created_at

pending_confirmations
  id, user_id, action TEXT, payload JSONB, expires_at

processed_updates
  update_id BIGINT PK, created_at   -- dedupe; prune rows older than a few days
```

The two `users` rows are created with `scripts/seed_users.py`. There's no sign-up flow.

### Permission rules

- **Wishlists:** only the owner can add, edit or delete their items. The partner can only read them.
- **Movies, places, actions:** shared. Either person can add, edit or delete.
- **Ratings and reviews:** each person can only create or change their own. Both people's ratings are visible to both.
- Rating a movie automatically sets it to `watched`; reviewing a place sets it to `visited`. Marking an action `done` stamps `done_at`, and setting it back to `todo` clears it.

## Operations

### REST API (built)

All routes are under `/api` and need the `X-Telegram-User-Id` header of a known user. `/docs` and `/openapi.json` are served only when `DEBUG` is on. The REST API exists for debugging, a future Telegram Mini App, or an MCP server; the bot and the agent call the services directly.

```
GET    /health                                  (no header needed)

GET    /api/users/me                            caller and partner

GET    /api/wishlist?person=me|partner          POST   /api/wishlist
PATCH  /api/wishlist/{item_id}                  DELETE /api/wishlist/{item_id}

GET    /api/movies?status=                      POST   /api/movies
PATCH  /api/movies/{movie_id}                   DELETE /api/movies/{movie_id}
PUT    /api/movies/{movie_id}/rating            (upsert own rating)

GET    /api/places?status=                      POST   /api/places
PATCH  /api/places/{place_id}                   DELETE /api/places/{place_id}
PUT    /api/places/{place_id}/review            (upsert own review)

GET    /api/actions?status=&setting=&price=     POST   /api/actions
PATCH  /api/actions/{action_id}                 DELETE /api/actions/{action_id}
```

List filters combine with AND, and a filter left out matches everything. An action with no `setting` or `price` only shows up when that filter is left out. Lists aren't paginated (they're small).

Known caveat: Telegram IDs aren't secret, so don't serve `/api` publicly without revisiting auth. The current idea is to serve it only when `DEBUG` is on.

`POST /telegram/webhook` arrives in phase 2.

### LLM tools *(proposed, phase 3)*

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
| Actions | `list_actions` | `status?: todo\|done\|all`, `setting?: indoor\|outdoor`, `price?: cheap\|medium\|expensive` |
| | `add_action` | `title`, `note?`, `setting?`, `price?` |
| | `update_action` | `action_id`, `title?`, `note?`, `setting?`, `price?`, `status?` |
| | `delete_action` | `action_id` (needs confirmation) |

Tool descriptions should say when to use each tool (e.g. "use `list_movies` first to find the `movie_id` when the user refers to a movie by name"). Picking *which* date idea fits ("anniversary", "cozy") is the LLM's job: it lists ideas filtered by setting and price, then chooses. Since `price` matches a single value, "medium or cheaper" means listing without `price` (or calling twice).

## Configuration

Set these in a local `.env` (see `.env.example`) and later in the Vercel project settings. Never commit `.env`.

Used now:

```
DATABASE_URL=postgresql://user:password@localhost:5432/couple_bot
                                # production: Neon's *pooled* string, ...?sslmode=require
DEBUG=true                      # false in production: hides /docs and /openapi.json
RUN_MIGRATIONS_UPON_LAUNCH=false  # keep off on Vercel
# Optional: APP_VERSION, DEFAULT_PAGE_SIZE, GLOBAL_API_PREFIX (/api),
#           PLACE_MIN_SCORE, PLACE_MAX_SCORE (changing these needs a new migration)
```

Coming in phases 2 and 3 *(proposed)*:

```
TELEGRAM_BOT_TOKEN=
TELEGRAM_WEBHOOK_SECRET=        # random string, also passed to setWebhook
ANTHROPIC_API_KEY=              # from Claude Console (separate from Pro subscription)
LLM_MODEL=claude-haiku-5-5
DEFAULT_TIMEZONE=Asia/Almaty
```

There's no `ALLOWED_TELEGRAM_IDS` or `API_TOKEN`: the `users` table is the allowlist.

## Running locally

```sh
mise install                                  # Python 3.12
uv sync
cp .env.example .env
mise run db                                   # Postgres 17 on :5432 (docker compose)
mise run migrate                              # alembic upgrade head
uv run python -m scripts.seed_users \
    --user <telegram_id> <name> --user <telegram_id> <name>
mise run dev                                  # http://localhost:8000/docs
```

In `/docs`, send the `X-Telegram-User-Id` header with one of the seeded IDs.

Checks (there are no automated tests; this is a personal project):

```sh
uv run ruff check .
uv run python scripts/check_migrations.py     # migration chain stays linear
uv run alembic downgrade base && uv run alembic upgrade head
uv run alembic check                          # models match the DB
```

## Project layout

```
app/
  main.py              FastAPI app, lifespan, /health, router registration
  database.py          sync engine (NullPool, prepare_threshold=None)
  config/
    base.py            CONFIG (pydantic-settings), fastapi_config
    places_config.py   per-feature settings (place score bounds)
  common/              base classes only: Model, AbstractSchema,
                       ModelRepository, exceptions, get_session, time utils
  users/               each feature package has: models, constants,
  wishlists/           schemas, repository, service, router,
  movies/              dependencies (and utils where needed)
  places/
  actions/
alembic/               env.py, versions/
scripts/
  seed_users.py        create/update the two users and link them
  check_migrations.py  verify the migration chain is linear
docker-compose.yml     local Postgres only
mise.toml / pyproject.toml / uv.lock / alembic.ini / .env.example
```

Phases 2 and 3 add `app/bot/` (dispatcher, middleware, commands, callbacks) and `app/agent/` (loop, tools, prompts), plus `scripts/set_webhook.py`. Vercel's entrypoint is decided in phase 2; check Vercel's current FastAPI docs then.

## LLM cost estimate

Claude Haiku 5.5 costs $0.10 per million input tokens and $0.50 per million output tokens for prompts up to 100K tokens. A typical turn sends about 3–5K input tokens (system prompt + ~18 tool schemas + history) and may make 2–3 calls. That's roughly $0.001–0.002 per user message, so **about $1/month even with heavy use**. Prompt caching of the system prompt and tools can cut it further.

## Later / ideas

- **Reminders & important dates.** On Vercel Hobby, cron jobs run at most once a day, so a daily digest is possible ("today: anniversary"). Exact-time reminders would need an external pinger (e.g. a free cron service hitting a protected endpoint) or a different host.
- **MCP server:** expose the services as a remote MCP server and add it as a custom connector in the Claude app, so you can ask Claude itself "what's on her wishlist?" from a Pro subscription.
- Telegram Mini App for browsing lists visually.
- Movie metadata (posters, year) from TMDB. Map links for places.
- A "reserved" flag on wishlist items, hidden from the owner (surprise mode).
- Replace `HTTPException` in services with app-level exceptions, mapped to HTTP in routers and to tool errors in the agent.

## Open questions

- Which language(s) will you chat in? (The system prompt tells the model to reply in the user's language.)
