# Coaching Client Log

A FastAPI + Postgres app for logging coaching call notes: one client, many sessions
over time, each with action items, a next-session date, and a copy-ready call summary.
Schema changes are managed with Alembic migrations, so future field changes don't
put existing client data at risk.

## What's here

- `app/main.py` — API routes (clients, sessions, action items, CSV export) + serves the frontend
- `app/models.py` — SQLAlchemy models: `Client`, `Session`, `ActionItem`
- `app/schemas.py` — request/response validation
- `app/database.py` — DB connection (reads `DATABASE_URL` from the environment)
- `app/templates/index.html` — the UI: client sidebar, session tabs, intake vs.
  follow-up question sets, action items, summary generator
- `migrations/` — Alembic migration history. This is what actually creates/alters
  your database tables — `main.py` no longer does this itself.
- `Procfile` / `railway.json` — tells Railway to run migrations, then start the server

## Run it locally first (recommended)

```bash
cd coaching-crm
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head        # creates local_dev.db with the current schema
uvicorn app.main:app --reload
```

Without a `DATABASE_URL` set, both Alembic and the app fall back to a local SQLite
file (`local_dev.db`). Open http://localhost:8000.

## Deploying a fresh setup to Railway

1. **Push to a git repo**, Railway deploys from it directly.
2. **In Railway**: New Project → Deploy from GitHub repo → select this repo.
3. **Add Postgres**: same project → "+ New" → Database → Add PostgreSQL. Railway
   auto-injects `DATABASE_URL` — nothing to configure.
4. Railway builds via Nixpacks, installs `requirements.txt`, and runs the start
   command in `Procfile`/`railway.json`:
   ```
   alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
   That first runs any pending migrations against your Postgres, then starts the app.
   On a brand-new database this creates all tables from scratch.

## If you already have a Railway Postgres from an earlier version of this app

Your existing database predates Alembic, so it has tables but no migration history
recorded. You have two options:

**Option A — reset (simplest, fine while client volume is low):**
1. In Railway, open your Postgres service → **Data** tab → drop the existing tables
   (or just delete and re-add the Postgres plugin for a completely clean database).
2. Push this updated code and redeploy. `alembic upgrade head` will build the schema
   from scratch on first deploy.
3. Re-enter any existing clients (should just be Ruth at this point).

**Option B — preserve existing data:**
1. Connect to your Railway Postgres (Railway gives you a connection string under the
   Postgres service → Connect tab; use `psql "<connection-string>"` or a GUI like
   TablePlus/DBeaver).
2. Manually inspect what tables/columns currently exist.
3. Tell me what's there and I'll write a migration that adapts the existing tables to
   match `app/models.py` instead of dropping them.

Given you're only a few clients in, Option A is almost certainly less work and risk
than a live data migration — but Option B is there if any of that data matters.

## Making schema changes going forward (this is the whole point of Alembic)

Whenever you want to add/remove/change a question — i.e. change something in
`app/models.py` — the workflow is:

```bash
# 1. Edit app/models.py with your changes
# 2. Generate a migration that captures the diff:
alembic revision --autogenerate -m "describe the change, e.g. add mood field to sessions"

# 3. Review the generated file in migrations/versions/ — autogenerate is good but
#    not perfect, double check it before trusting it against real data

# 4. Apply it locally to test:
alembic upgrade head

# 5. Commit the new migration file along with your model changes, push.
#    Railway will run it automatically via the start command on next deploy.
```

The key benefit: existing rows are preserved. Adding a new nullable column doesn't
touch old sessions; they just have `null` for the new field until you fill it in on
future sessions.

## Using it

- Add a client, then add a session — the first session per client shows intake
  questions, every session after that shows the follow-up/review question set
  automatically.
- Add action items during the call, tagged Client or Coach.
- **Generate summary** builds a sectioned recap (where we're at / your goals / your
  next steps / my next steps) ready to paste into an email.
- **Export CSV** in the header gives a full backup of every session at any time.

## Adding it to your phone's Home Screen

The app is set up as an installable web app (PWA) — an icon on your Home Screen that
opens full-screen, no browser bar, and the notes-photo input opens your camera directly.

**iPhone (Safari):**
1. Open your `*.up.railway.app` URL in Safari (must be Safari, not Chrome, for this to work on iOS)
2. Tap the Share icon → **Add to Home Screen** → Add

**Android (Chrome):**
1. Open the URL in Chrome
2. Tap the ⋮ menu → **Add to Home screen** (or you may see an automatic "Install app" banner)

After that, tapping the icon opens it like a normal app, and the photo upload on each
session form will offer your camera directly rather than a file browser.

## Scanning handwritten notes

Each session form has a photo upload for handwritten notes. It sends the image to
the Claude API, which reads the handwriting and extracts it into the relevant
fields for that session type (intake vs. follow-up), plus any action items it
finds, tagged by who owns each one.

**Setup required:**
1. Get an API key from https://console.anthropic.com (separate from any Claude.ai
   subscription — this is billed per-use on your Anthropic API account).
2. In Railway: your service → **Variables** → add `ANTHROPIC_API_KEY` with that key.
3. Redeploy (or it picks it up automatically on the next deploy).

**How it behaves:**
- Nothing is saved automatically — scanned fields populate the form and suggested
  action items appear in a dashed/faded state, but none of it hits the database
  until you review and click **Save session**.
- If a field isn't mentioned in the notes, it's left blank rather than guessed.
- Cost is per scan, based on Claude API pricing for image input plus a fairly
  short text response — check current rates at
  https://docs.claude.com/en/docs/about-claude/pricing before relying on it heavily.
- Messy handwriting or poor photo quality will produce messier extraction — it's
  worth treating the result as a fast first draft to correct, not a final transcript.

## Notes

- No login/auth yet — fine while only you have the URL, but worth adding before this
  holds a meaningful volume of real client data.
- Postgres on Railway is backed up by Railway itself, but it's still worth pulling a
  CSV export periodically as your own copy.
