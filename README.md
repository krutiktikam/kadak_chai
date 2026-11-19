# Kadak Chai Co. - #MyChaiBreak

Campaign microsite for a fictional brand (Kadak Chai Co.). People share a short chai-break story. An AI step checks the story, tags it and writes a one-line poster caption. Approved stories get a shareable page, and the brand team reviews everything in an admin dashboard.

Built for the Ecultify Advertising LLP take-home assignment.

**Live link:** [FILL IN after deploy, or delete this line]
**Time spent:** roughly [FILL IN] hours.

## What it does

- **Landing page and form** (mobile first): name, city, email or phone, story (10-300 characters), consent checkbox. Validated in the browser and again on the server.
- **AI step:** the story is sent to an LLM, which returns JSON (decision, reason, category, caption). The JSON is validated before anything is saved. If the AI times out, errors, is rate limited, or returns something invalid, the entry is saved as `pending_review` and the user sees a neutral "under review" page, never a technical error.
- **Result page:** `/result/<public_id>` where `public_id` is a random 22-character token (not `/entry/1`). It shows only the first name and caption.
- **Admin dashboard:** `/admin`. Login, entry list, status filter, and override of the AI's decision.
- **Mock mode:** `AI_PROVIDER=mock` runs the whole app with no API key.

## Run it locally (mock mode, no API key)

Requires Python 3.13.

```bash
git clone https://github.com/krutiktikam/kadak_chai.git
cd kadak_chai
python -m venv .venv
# Windows PowerShell:  .\.venv\Scripts\Activate.ps1
# macOS / Linux:       source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # Windows PowerShell: Copy-Item .env.example .env
```

Edit `.env` and set `ADMIN_PASSWORD` and `SECRET_KEY` (the app refuses to start without them). Generate a key with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Then start the app:

```bash
uvicorn app.main:app --reload
```

- Site: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin
- Health: http://127.0.0.1:8000/health

Run the tests (offline, mock mode, isolated databases):

```bash
pytest -q
```

## Environment variables

| Variable | Required | Notes |
|---|---|---|
| `ADMIN_USERNAME` | yes | Admin login. |
| `ADMIN_PASSWORD` | yes | Admin login. Compared in constant time. |
| `SECRET_KEY` | yes | Signs the admin session cookie. |
| `AI_PROVIDER` | no | `mock` (default) or `real`. Any other value stops the app at startup. |
| `AI_BASE_URL` | for `real` | OpenAI-compatible base URL, up to `/v1`. `.env.example` has the Groq value. |
| `AI_API_KEY` | for `real` | Never commit it. Not needed in mock mode. |
| `AI_MODEL` | for `real` | `.env.example` uses `openai/gpt-oss-20b`. |
| `DATABASE_URL` | no | Default `sqlite:///./kadak.db`. A `postgres://` or `postgresql://` URL is converted for the psycopg 3 driver. |
| `COOKIE_SECURE` | no | Set `true` when served over HTTPS. |

## Mock mode

Mock mode returns raw JSON text, so it goes through the same parser and schema as real AI output. It is deterministic:

| Story contains | Result |
|---|---|
| spam words (`http`, `www.`, `buy now`, `crypto`, ...) | rejected |
| abusive words (`idiot`, `stupid`, `shut up`) | rejected |
| none of `chai`, `tea`, `kadak`, `masala`, `cutting` | rejected as off-topic |
| keywords such as `grandma`, `school` / `laughed` / `family` | approved as `nostalgic` / `funny` / `wholesome` |
| anything else with a chai word | approved as `other` |
| `mock-error` | the mock raises an error, so the entry becomes `pending_review` |
| `mock-broken` | invalid JSON, so `pending_review` |
| `mock-wrong` | valid JSON with invalid values, so `pending_review` |

A normal story without a chai-related word is rejected in mock mode. That is intentional, not a bug.

## Real AI

Tested against Groq's free tier with `openai/gpt-oss-20b`. In a 5-story end-to-end run (good, off-topic, spam, prompt-injection attempt, 300-character story) each call took 0.7-1.6 s and the model's output passed validation. The injection attempt was rejected. This is a small sample, not a guarantee. Groq model availability changes, so check the `/models` endpoint if you get `http_404`.

## Decisions and why

- **FastAPI + Jinja2 + SQLAlchemy, no frontend framework.** Small, readable, and server-side validation is the source of truth. Vanilla JS only for the character counter and client checks.
- **Safety comes from schema validation, not from the prompt.** The story is untrusted. The prompt asks the model to treat it as data, but the guarantee is the Pydantic model: enums, caption of 1-12 words, and a reason required on rejection. Anything else becomes `pending_review`.
- **Parser errors carry only a short code** (`empty_response`, `invalid_json`, `not_an_object`, `invalid_values`), raised with `from None`. Pydantic's messages and exception chains include the offending input, so story text could otherwise end up in logs. A test checks the rendered traceback.
- **`status` vs `ai_decision`.** `ai_decision` records what the AI said and is never changed. `status` is what the site does and is what an admin override changes (with `admin_override = true`).
- **`id` vs `public_id`.** The integer id is internal and admin-only. Public URLs use a random token.
- **Admin security.** Credentials from env vars, constant-time comparison, signed `HttpOnly` / `SameSite=Lax` session cookie (Starlette `SessionMiddleware`, 8-hour limit), in-memory login limiter (5 failures per IP, 15 minutes), CSRF token on the override form, and a single router-level guard so a new admin route cannot forget the login check. The `back` field after an override is checked against a fixed list to avoid open redirects.
- **No SQL migrations.** Tables are created at startup. Fine for this size, but a schema change would need a migration tool.
- **Synchronous HTTP call to the AI** with a 10-second timeout. FastAPI runs normal `def` routes in a thread pool, which is enough at this scale.

## Assumptions

- Phone numbers are Indian mobiles only (10 digits starting 6-9, optional `+91` or `0`). Email uses a simple regex.
- Story length is 10-300 characters, counted with Python `len`.
- A result page is shown for any existing `public_id`, but non-approved entries show only a generic notice (no caption, story, reason or error). The URL is unguessable, and the submitter needs to see what happened. Missing or numeric ids return 404.
- Approving an entry that has no caption, or that the AI rejected, requires the admin to type a 1-12 word caption. That caption is stored in the `ai_caption` column, which is a naming compromise.
- Approved entries are published immediately, without a human check. The admin can take any entry down afterwards.
- The admin dashboard shows the newest 100 entries per filter. Times are UTC.

## Known limits / not finished

- **Prompt injection is reduced, not eliminated.** A cleverly worded story could get a bad but well-formed caption approved. The 12-word cap, HTML escaping and the admin override limit the damage.
- **Login limiter is in memory.** It resets on restart and is not shared across workers. Behind a proxy, `request.client.host` may be the proxy's address unless the server is configured to trust forwarded headers.
- **Logout cannot revoke a copied cookie.** The session is stateless and stays valid until it expires.
- **No rate limit on `/submit` and no duplicate-contact blocking yet.** [UPDATE this line if you build them.]
- **Not built:** CSV export, category filter in admin, Open Graph tags, Hindi toggle, Docker. [UPDATE if you build any.]
- **Deployment:** [FILL IN: deployed on ... / not deployed].
- Tests cover parsing, validation, the AI fallback, public privacy, XSS escaping, login, CSRF and overrides. There are no browser-level tests.

## Project layout

```
app/
  main.py          public routes: /, /submit, /result/{public_id}, /health
  admin.py         login, logout, dashboard, override
  config.py        reads all env vars in one place
  db.py            engine and session
  models.py        Entry table
  security.py      credential check, login limiter, CSRF check
  validation.py    server-side input validation and normalisation
  ai/              analyze_story(), provider client, mock, response parser and schema
  templates/       Jinja2 (auto-escaped)
  static/          CSS and small JS
tests/             pytest suite
AI_USAGE.md        how AI was used, with mistakes caught
AI_SESSIONS.json   index of AI sessions
ai-logs/           exported AI chats (keys redacted)
```

## AI usage

See `AI_USAGE.md` and `AI_SESSIONS.json`.
